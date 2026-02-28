# Trading 模块 — 修复方案

> 原则: AD-01 设计为权威 | AD-05 统一模块结构 | 不接受双轨并行

---

## 1. 架构目标

重建后 Trading 与 Backtest **必须共享**以下服务层，彻底消除三角脱节：

```
src/shared/
├── execution_model.py    ← fill_probability, fill_ratio, impact_cost, liquidity_tier
├── fee_calculator.py     ← 佣金 + 印花税 + 过户费（统一基准）
├── signal_filter.py      ← 统一过滤规则（设计黑名单方案）
└── risk_checker.py       ← 6 项风控检查完整实现
```

Trading 和 Backtest 各自仅包含差异逻辑（执行通道、结果持久化方式），
核心算法逻辑从共享层导入，不允许各自维护副本。

---

## 2. 分批修复任务

### 第一批：P0 致命 — 资金安全底线

#### FIX-01 共享成交模型 (T-09, B-01)

从 `backtest/pipeline.py` 提取 `_estimate_fill()` + `_estimate_impact_cost()` +
`_resolve_liquidity_tier()` + `_is_one_word_board()` + `_is_liquidity_dryup()` 至
`shared/execution_model.py`。

Trading `try_execute_buy()` 必须调用共享成交模型：
- fill_probability < 0.35 → reject
- filled_shares = order_shares × fill_ratio
- total_cost += impact_cost

流动性分层按设计改为百分位方案 (p70/p30)，废弃绝对阈值。

#### FIX-02 统一信号过滤 (T-06, B-02)

`shared/signal_filter.py` 实现设计标准：
```
1. final_score >= min_final_score (55)
2. recommendation ∉ {AVOID, SELL}
3. opportunity_grade != "D"（需确认上游是否有该字段）
4. risk_reward_ratio >= 1.0
5. direction: bullish→buy, bearish→sell, neutral→skip
```

废弃 Trading 的 fallback 模式和 Backtest 的白名单模式。

#### FIX-03 信号字段补齐 (T-05)

`_read_signals()` 补读完整 18 字段。前置于 FIX-04/FIX-05。
- 立即需要: `stop`, `target`, `neutrality`, `opportunity_grade`
- 同批补齐: `integration_mode`, `mss_score`, `irs_score`, `pas_score`, `stock_name`

#### FIX-04 完整风控检查 (T-08, B-03)

`shared/risk_checker.py` 实现设计 6 项全部风控：

| # | 检查 | 当前状态 |
|---|------|----------|
| 0 | Regime 阈值 | 新增 — 依赖 MSS temperature |
| 1 | 资金充足 | Trading ✅ 保留 |
| 2 | 单股仓位 ≤20% | 修正 — 含已有持仓+新买入 |
| 2.5 | 行业集中度 ≤30% | 新增 |
| 3 | 总仓位 ≤80% | Trading ✅ / Backtest 补齐 |
| 4 | T+1 | 保留 |
| 5 | 涨跌停 | 保留 |

额外纳入 Backtest 的合理超额检查：一字板拦截、流动性枯竭拦截。

#### FIX-05 v2.0 信号验证 (T-07)

按设计实现 neutrality-based 风险分级：
```
neutrality ≤ 0.3 → position_adjustment = 1.0
neutrality ≤ 0.6 → position_adjustment = 0.8
neutrality >  0.6 → position_adjustment = 0.6
```

Trading 和 Backtest 均应用此调整。

#### FIX-06 条件平仓替代 T+1 全卖 (T-10, B-07)

**这是最大的策略变更**。替换 T+1 无条件全卖为设计的持仓管理体系：
- 止损: `pct_loss <= -8%` 触发
- 止盈: 达到 `target_price`
- 最大回撤: `drawdown >= 15%` 触发限制
- 日终: 市值/回撤检查

前置: FIX-03（需要 stop/target 字段）。

#### FIX-07 Backtest 总仓位上限 (B-03)

Backtest 买入循环增加 `max_total_position` 检查，与 Trading 一致。
重建后由 `shared/risk_checker.py` 统一提供，此为临时修复。

---

### 第二批：P1 严重 — 数据完整性

#### FIX-08 trade_records 字段对齐 (T-02)

Trading TRADE_RECORD_COLUMNS 补齐 11 个缺失字段（随 FIX-01 成交模型落地自然产出
`fill_probability`, `fill_ratio`, `liquidity_tier`, `impact_cost_bps`, `slippage`）。

代码独有的 5 个字段（`t1_restriction_hit` 等）纳入设计文档。

#### FIX-09 positions 字段对齐 (T-03, T-15)

补齐 `cost_amount`, `unrealized_pnl`, `unrealized_pnl_pct`, `signal_id`,
`stop_price`, `target_price`。

**存储模型决策**: 统一为按 `trade_date` 分快照方案（代码方案），
设计文档同步修改，废弃 `stock_code UNIQUE` 方案。

#### FIX-10 费用计算统一 (B-06)

`shared/fee_calculator.py` 确定统一标准：
- 基础: 设计公式（佣金 max(5, amount×0.0003) + 过户费 amount×0.00002 + 印花税卖出 0.1%）
- 决策点: Backtest 的 S/M/L 费用分档是否保留？若保留则纳入设计文档。
- 冲击成本由 `execution_model.py` 独立计算，不混入费用。

#### FIX-11 Gate 机制统一 (T-14)

将代码的双重门禁（backtest_results + quality_gate_report）正式纳入设计文档。
统一 API 接口。

#### FIX-12 订单状态机扩展 (T-11)

纸上交易阶段最低实现 4 态: `pending → filled / rejected / cancelled`。
`partially_filled` 和 `submitted` 留至真实交易所对接时。

---

### 第三批：P2 中度 — 规范性

#### FIX-13 t1_frozen 设计对齐 (T-04)

设计文档同步为 `can_sell_date` 内联方案，标记 t1_frozen 独立表为废弃。
代码方案更简洁且已验证。

#### FIX-14 枚举类定义 (T-12)

定义 7 个枚举类（`OrderStatus`, `OrderType`, `Direction`, `RiskLevel`,
`RejectReason`, `TradingState`, `ExecutionMode`），替换硬编码字符串。

#### FIX-15 risk_events 纳入设计 (T-13)

在 `trading-data-models.md` 补充 risk_events DDL 定义。

#### FIX-16 RejectReason 统一 (T-16, B-05)

统一命名: `REJECT_NO_OPEN_PRICE` → `REJECT_NO_MARKET_PRICE`。
新增: `REJECT_ONE_WORD_BOARD`, `REJECT_LIQUIDITY_DRYUP`。

#### FIX-17 fill_ratio 公式修正 (B-09)

补入 `capacity_ratio` 变量:
```
fill_ratio = clip(1.0 - 0.5*queue_ratio - 0.5*capacity_ratio, 0, 1)
```

#### FIX-18 Backtest 成交数据写入记录 (B-04)

将内部计算的 `fill_probability`, `fill_ratio`, `liquidity_tier`, `impact_cost_bps`
写入 BACKTEST_TRADE_COLUMNS。

---

### 第四批：P3 轻度

#### FIX-19 设计文档状态更新 (T-01)

3 个文档的「实现状态」章节全部更新。

#### FIX-20 Backtest 超额实现入设计 (B-10)

一字板检测、流动性枯竭检测、冲击成本乘数 → 正式写入 `trading-algorithm.md`。

---

## 3. 开放决策点

以下决策需在重建启动前确认：

| # | 决策 | 影响范围 |
|---|------|----------|
| D-1 | `opportunity_grade` 字段上游是否产出？ | FIX-02 过滤规则 |
| D-2 | T+1 全卖是临时简化还是正式策略？ | FIX-06 整体改动量 |
| D-3 | 费用分档 (S/M/L) 保留还是去掉？ | FIX-10 费用模块 |
| D-4 | Backtest 是否也走 v2.0 neutrality 验证？ | FIX-05 作用域 |
| D-5 | Regime 阈值的上游数据（MSS temperature）何时可用？ | FIX-04 #0 |
| D-6 | 流动性分层用百分位还是绝对阈值？ | FIX-01 + B-08 |

---

## 4. 依赖关系

```
FIX-03 (信号字段)
  ├→ FIX-02 (过滤，需 opportunity_grade)
  ├→ FIX-05 (v2.0 验证，需 neutrality)
  └→ FIX-06 (条件平仓，需 stop/target)

FIX-01 (成交模型)
  └→ FIX-08 (trade_records 字段，依赖成交模型输出)
     └→ FIX-18 (Backtest 写入记录)

FIX-04 (风控)
  └→ FIX-07 (Backtest 总仓位，风控的子集)

FIX-10 (费用统一)
  → 独立，可并行
```

**关键路径**: FIX-03 → FIX-06（信号字段 → 条件平仓）决定了 Trading 模块能否脱离
"T+1 全卖"模式，是重建的最核心路径。
