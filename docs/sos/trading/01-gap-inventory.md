# Trading 模块 — 偏差清单

> 审计日期 2026-02-27 | 设计基准 trading v3.3 + api v4.0

---

## A. Trading Pipeline → 设计偏差 (16 项)

### T-01 设计文档实现状态过时 `P3`

`trading-algorithm.md`、`trading-data-models.md`、`trading-information-flow.md` 三个文档的
「实现状态」仍写着 `src/trading/ 仅有 __init__.py 占位`，实际 `pipeline.py` 已 1 225 行。
仅 `trading-api.md` v4.0.0 已更新。

### T-02 trade_records 字段严重不对齐 `P1`

设计 28 字段 vs 代码 21 字段。

**设计有、代码无 (11)**:

| 字段 | 设计用途 | 级别 |
|------|----------|------|
| `stock_name` | 人工审阅 | P2 |
| `slippage` | 滑点金额 | P1 |
| `fill_probability` | 可成交概率 | P0 |
| `fill_ratio` | 成交比例 | P0 |
| `liquidity_tier` | 流动性分层 L1/L2/L3 | P0 |
| `impact_cost_bps` | 冲击成本 | P1 |
| `trading_state` | 执行状态机 | P1 |
| `execution_mode` | 执行模式 | P2 |
| `slice_seq` | 分批序号 | P2 |
| `signal_id` | 信号溯源 | P1 |
| `updated_at` | 更新时间 | P2 |

**代码有、设计无 (5)**: `t1_restriction_hit`, `limit_guard_result`, `session_guard_result`,
`risk_reward_ratio`, `contract_version` — 均为合理扩展，应纳入设计。

### T-03 positions 字段严重不对齐 `P1`

设计 20 字段 vs 代码 12 字段。

**设计有、代码无 (10)**: `id`, `stock_name`, `direction`, `cost_amount`, `unrealized_pnl`,
`unrealized_pnl_pct`, `signal_id`, `stop_price`, `target_price`, `updated_at`

**存储模型根本分歧**: 设计用 `stock_code UNIQUE` 做最新快照，代码用 `trade_date` 做每日快照。

### T-04 t1_frozen 独立表未实现 `P0`

设计定义独立表（复合主键 `stock_code, buy_date`），代码通过 positions 字典 `can_sell_date` 内联。
DuckDB 中无 t1_frozen 表。

### T-05 信号字段严重不足 `P0`

设计要求从 `integrated_recommendation` 读取 18 字段，代码 `_read_signals` (行274-302) 仅读 10 字段。

**缺失 8 字段**:
- `stop` / `target` — 无法执行止损止盈（设计 §2.1 步骤 3 的 fallback 公式 `stop = entry * (1-pct)` 无从触发）
- `opportunity_grade` — 设计 §2.1 步骤 2 的 `grade=="D"` 过滤完全缺失
- `integration_mode` — 设计要求透传到 TradeSignal
- `neutrality` — v2.0 验证核心输入
- `mss_score` / `irs_score` / `pas_score` — 追溯用

### T-06 信号过滤逻辑不一致 `P1`

| 条件 | 设计 | 代码 |
|------|------|------|
| `final_score >= 55` | ✅ | ✅ (strict) |
| `recommendation ∉ {AVOID,SELL}` | ✅ | ✅ |
| `opportunity_grade != "D"` | ✅ | ❌ 缺失 |
| `risk_reward_ratio >= 1.0` | ✅ | ✅ |
| `direction` 映射 | bearish→sell | bearish→**直接丢弃** |
| fallback 兜底模式 | ❌ 无此概念 | ✅ 代码独创 |

代码额外发明了 strict+fallback 双模式；设计中 bearish 应生成卖出信号而非丢弃。

### T-07 信号质量验证 v2.0 完全缺失 `P0`

设计 (§4) 定义的 neutrality 风险分级 + position_adjustment 仓位缩减机制完全不存在。
无 `ValidationResult`、无 neutrality 读取、无 risk_level 分级。

### T-08 风控检查 6 项仅实现 3 项 `P0`

| # | 检查项 | 代码状态 |
|---|--------|----------|
| 0 | Regime 阈值解析 | ❌ 完全缺失 |
| 1 | 资金充足检查 | ✅ 行928 |
| 2 | 单股仓位上限 (20%) | ❌ 仅限买入金额占比，不含已有持仓 |
| 2.5 | 行业集中度 (30%) | ❌ 完全缺失 |
| 3 | 总仓位上限 (80%) | ✅ 行902-918 |
| 4 | T+1 限制 | ✅ can_sell_date |
| 5 | 涨跌停检查 | ✅ 行852/725 |

### T-09 成交可行性模型完全缺失 `P0`

设计要求:
```
fill_probability = clip(1.0 - queue_ratio, 0, 1)
fill_ratio = clip(1.0 - 0.5*queue - 0.5*capacity, 0, 1)
liquidity_tier: L1(p70)/L2(p30)/L3
impact_cost_bps: 8/18/35
min_fill_probability < 0.35 → reject
```

代码: `filled_price = price.get("open")`，无任何成交建模。
Backtest 已实现 `_estimate_fill()` + `_estimate_impact_cost()` 但 Trading 未复用。

### T-10 止损/止盈/回撤检查完全缺失 `P0`

设计要求止损 `pct_loss <= -8%`、止盈 `target_price`、最大回撤 `drawdown >= 15%`。
代码: T+1 解锁后无条件全卖，无任何持仓管理逻辑。

### T-11 订单状态机简化 `P1`

设计 6 态 `pending→submitted→partially_filled→filled/cancelled/rejected`。
代码仅 `filled` 或 `rejected` 两种最终态。

### T-12 数据模型枚举未实现 `P2`

设计 7 个枚举类全部使用硬编码字符串替代。`RejectReason` 设计 11 值，
代码仅对应 3 个 (`LIMIT_UP`, `LIMIT_DOWN`, `MAX_TOTAL_POSITION`)。

### T-13 risk_events 表无设计覆盖 `P2`

代码写入 DuckDB 的 `risk_events`（7 字段）在 `trading-data-models.md` 中完全未定义。

### T-14 Gate 机制差异 `P1`

设计: 单一 `get_validation_gate_decision()`。
代码: 双重门禁 (`backtest_results` + `quality_gate_report`)。功能更丰富但模型不对齐。

### T-15 positions 存储模型分歧 `P1`

设计 `stock_code UNIQUE` (最新快照) vs 代码 `trade_date` (每日快照)。
根本性的存储语义差异。

### T-16 RejectReason 命名差异 `P2`

代码用 `REJECT_NO_MARKET_PRICE`，设计用 `REJECT_NO_OPEN_PRICE`。

---

## B. Backtest Pipeline → 设计偏差 (10 项)

### B-01 成交模型不对称（系统性） `P1`

Trading 全额成交 vs Backtest 部分成交+冲击成本。同一设计约束下两套代码执行模型完全不同，
导致 Backtest 绩效评估无法准确反映 Trading 实际效果。

### B-02 信号过滤策略三方各异 `P1`

| 来源 | 策略 |
|------|------|
| 设计 | 黑名单: `recommendation ∉ {AVOID,SELL}` + `grade!="D"` + `score≥55` + `rr≥1.0` |
| Trading | strict(黑名单变体) + fallback(宽松) |
| Backtest | 白名单: `recommendation ∈ {STRONG_BUY,BUY}` + `position_size>0` |

Backtest 不检查 `final_score`、`risk_reward_ratio`、`opportunity_grade`。

### B-03 风控检查交叉缺失 `P1`

| 检查项 | Trading | Backtest |
|--------|:---:|:---:|
| 总仓位上限 | ✅ | ❌ |
| 流动性枯竭 | ❌ | ✅ |
| 一字板检测 | ❌ | ✅ |
| 行业集中度 | ❌ | ❌ |

### B-04 trade_records 字段不对齐 `P2`

Backtest 有 `backtest_id`/`signal_date`/`execute_date`/`pnl` 等特有字段（合理），
但内部计算了 `fill_probability`/`fill_ratio`/`liquidity_tier`/`impact_cost_bps` 却**未写入记录**。

### B-05 RejectReason 扩展未同步 `P2`

Backtest 独创 `REJECT_ONE_WORD_BOARD`、`REJECT_LIQUIDITY_DRYUP`，不在设计枚举中。
`REJECT_NO_MARKET_PRICE` 与设计 `REJECT_NO_OPEN_PRICE` 命名冲突。

### B-06 费用计算不一致 `P1`

Backtest 有 S/M/L 费用分档 (×1.15/×1.0/×0.9) + 冲击成本，Trading 和设计均无此概念。
同一笔交易在两模块费用不同。

### B-07 持仓卖出策略一致但均偏离设计 `P0`

Trading 和 Backtest 代码行为一致：T+1 无条件全卖。
设计要求条件平仓（止损 -8%、止盈 target、回撤 15%）。

### B-08 流动性分层用绝对阈值非百分位 `P2`

设计: `vol>=p70→L1, vol>=p30→L2, else→L3`（自适应）。
代码: `vol>=100万→L1, vol>=20万→L2`（固定阈值）。不同市场环境结果大幅不同。

### B-09 fill_ratio 公式缺 capacity_ratio `P2`

设计: `fill_ratio = 1.0 - 0.5*queue_ratio - 0.5*capacity_ratio`
代码: `fill_ratio = 1.0 - 0.5*queue_ratio`
缺少 capacity_ratio 导致 fill_ratio 系统性偏高。

### B-10 超额实现未同步回设计 `P2`

Backtest 独有的一字板检测、流动性枯竭检测、费用分档、冲击成本乘数均未反映在设计文档中，
也未同步到 Trading 代码，造成三方脱节。

---

## C. 三方一致性矩阵

| 功能模块 | Trading 代码 | Backtest 代码 | 设计要求 | 一致？ |
|----------|:---:|:---:|:---:|:---:|
| 信号过滤 | strict+fallback | STRONG_BUY/BUY | 黑名单排除 | ❌ 三方各异 |
| 涨跌停检查 | ✅ | ✅ | ✅ | ✅ |
| 涨跌停比率 | 主板10%/GEM20%/ST5% | 同 | 同 | ✅ |
| T+1 处理 | can_sell_date | can_sell_date | t1_frozen 独立表 | ⚠️ 代码一致但偏离设计 |
| 费用计算 | 标准费率 | 分档+冲击成本 | 标准费率 | ❌ Backtest 偏离 |
| 成交模型 | 全额成交 | 部分成交 | 部分成交 | ❌ Trading 偏离 |
| 流动性检测 | 无 | 有 | 无(注) | ⚠️ Backtest 超额 |
| 持仓管理 | T+1 全卖 | T+1 全卖 | 条件平仓 | ⚠️ 代码一致但偏离设计 |
| 总仓位上限 | ✅ | ❌ | ✅ | ❌ Backtest 缺失 |
| 行业集中度 | ❌ | ❌ | ✅ | ❌ 双缺失 |
| 单股仓位上限 | ❌(不完整) | ✅ | ✅ | ❌ Trading 缺失 |
