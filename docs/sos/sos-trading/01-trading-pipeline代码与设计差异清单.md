# Trading Pipeline 代码 vs 核心设计 差异清单

**审计范围**:
- 代码: `src/trading/pipeline.py` (1225行)
- 设计: `docs/design/core-infrastructure/trading/` 下全部4个文档

**审计日期**: 2026-02-27

---

## 严重程度说明

- 🔴 P0-CRITICAL: 设计明确要求但代码完全缺失，影响核心功能正确性
- 🟠 P1-MAJOR: 设计定义了但代码大幅简化或偏离，影响风控/数据完整性
- 🟡 P2-MINOR: 字段缺失或命名差异，不影响功能但影响数据一致性
- 🔵 P3-NOTE: 设计文档自身过时需同步更新

---

## 差异一：设计文档「实现状态」严重过时 🔵 P3

### 问题
`trading-algorithm.md`、`trading-data-models.md`、`trading-information-flow.md` 三个文档的「实现状态」章节（各文档§行9-12）仍然写着：

> "src/trading/ 当前仅有 __init__.py 占位；交易/风控实现尚未落地。"

但实际上 `src/trading/pipeline.py` 已有1225行完整的纸上交易实现。

### 影响
仅 `trading-api.md` v4.0.0 已更新（ARCH-DECISION-001），其余3个文档的状态描述与代码严重不符。

---

## 差异二：trade_records 表字段严重不对齐 🟠 P1

### 设计定义 (trading-data-models.md §4.1)

28个字段:
`trade_id`, `trade_date`, `stock_code`, **`stock_name`**, `industry_code`, `direction`, `order_type`, `price`, `shares`, `amount`, `commission`, `stamp_tax`, `transfer_fee`, **`slippage`**, `total_fee`, `status`, **`fill_probability`**, **`fill_ratio`**, **`liquidity_tier`**, **`impact_cost_bps`**, `reject_reason`, **`trading_state`**, **`execution_mode`**, **`slice_seq`**, **`signal_id`**, `created_at`, **`updated_at`**

### 代码实际 (pipeline.py TRADE_RECORD_COLUMNS, 行46-68)

21个字段:
`trade_id`, `trade_date`, `stock_code`, `industry_code`, `direction`, `order_type`, `price`, `shares`, `amount`, `commission`, `stamp_tax`, `transfer_fee`, `total_fee`, `status`, `reject_reason`, **`t1_restriction_hit`**, **`limit_guard_result`**, **`session_guard_result`**, **`risk_reward_ratio`**, **`contract_version`**, `created_at`

### 差异对照

**设计有、代码无（11个字段缺失）:**

| 缺失字段 | 设计用途 | 严重程度 |
|-----------|----------|----------|
| `stock_name` | 股票名称，便于人工审阅 | 🟡 P2 |
| `slippage` | 滑点金额 | 🟠 P1 |
| `fill_probability` | 可成交概率 [0-1] | 🔴 P0 |
| `fill_ratio` | 成交比例 [0-1] | 🔴 P0 |
| `liquidity_tier` | 流动性分层 L1/L2/L3 | 🔴 P0 |
| `impact_cost_bps` | 冲击成本 bps | 🟠 P1 |
| `trading_state` | 执行状态机 normal/blocked_* | 🟠 P1 |
| `execution_mode` | 执行模式 auction_single/sliced | 🟡 P2 |
| `slice_seq` | 分批执行序号 | 🟡 P2 |
| `signal_id` | 关联信号ID，无法追溯来源 | 🟠 P1 |
| `updated_at` | 更新时间 | 🟡 P2 |

**代码有、设计无（5个字段多余）:**

| 多余字段 | 代码用途 | 处置建议 |
|-----------|----------|----------|
| `t1_restriction_hit` | T+1限制命中标记 | 可纳入设计 |
| `limit_guard_result` | 涨跌停检查结果 | 可纳入设计 |
| `session_guard_result` | 行情数据检查 | 可纳入设计 |
| `risk_reward_ratio` | 风险收益比 | 可纳入设计 |
| `contract_version` | 契约版本 | 应纳入设计 |

---

## 差异三：positions 表字段严重不对齐 🟠 P1

### 设计定义 (trading-data-models.md §4.2)

20个字段（含 id 自增主键）

### 代码实际 (pipeline.py POSITION_COLUMNS, 行70-83)

12个字段

### 差异对照

**设计有、代码无（10个字段缺失）:**

| 缺失字段 | 设计用途 | 严重程度 |
|-----------|----------|----------|
| `id` | 自增主键 | 🟡 P2 |
| `stock_name` | 股票名称 | 🟡 P2 |
| `direction` | 持仓方向（默认 long） | 🟡 P2 |
| `cost_amount` | 成本金额 = shares × cost_price | 🟠 P1 |
| `unrealized_pnl` | 未实现盈亏 | 🟠 P1 |
| `unrealized_pnl_pct` | 盈亏比例 | 🟠 P1 |
| `signal_id` | 关联信号ID | 🟠 P1 |
| `stop_price` | 止损价 | 🟠 P1 |
| `target_price` | 目标价 | 🟠 P1 |
| `updated_at` | 更新时间 | 🟡 P2 |

**代码有、设计无:**

| 多余字段 | 代码用途 |
|-----------|----------|
| `trade_date` | 快照日期（设计用 stock_code UNIQUE，不按日分快照） |
| `contract_version` | 契约版本 |

> **设计分歧**: 设计中 positions 表用 `stock_code UNIQUE` 做最新快照，但代码用 `trade_date` 做每日快照。这是根本性的存储模型差异。

---

## 差异四：t1_frozen 表完全未实现 🔴 P0

### 设计定义 (trading-data-models.md §4.3)

独立表，复合主键 `(stock_code, buy_date)`:
- `stock_code`, `buy_date`, `frozen_shares`

### 代码实现

**完全不存在**。代码通过 positions 字典中的 `can_sell_date` 字段内联处理 T+1。没有独立的 t1_frozen 表被创建或写入 DuckDB。

---

## 差异五：信号读取字段严重不足 🔴 P0

### 设计要求 (trading-algorithm.md §2.1)

从 `integrated_recommendation` 读取:
`trade_date`, `stock_code`, `stock_name`, `industry_code`, `final_score`, `position_size`, `risk_reward_ratio`, `recommendation`, `direction`, `entry`, **`stop`**, **`target`**, **`opportunity_grade`**, **`integration_mode`**, **`neutrality`**, **`mss_score`**, **`irs_score`**, **`pas_score`**

### 代码实际 (_read_signals, 行274-302)

仅读取10个字段:
`trade_date`, `stock_code`, `industry_code`, `final_score`, `position_size`, `risk_reward_ratio`, `recommendation`, `direction`, `entry`, `contract_version`

### 缺失字段影响

| 缺失字段 | 影响 |
|-----------|------|
| `stop` / `target` | 无法计算止损止盈价，设计§2.1步骤3的 `stop = row.stop or entry * (1 - stop_loss_pct)` 逻辑无法执行 |
| `opportunity_grade` | 设计§2.1步骤2的 `opportunity_grade == "D"` 过滤逻辑完全缺失 |
| `integration_mode` | 设计要求透传到 TradeSignal，代码完全缺失 |
| `neutrality` | 信号质量验证(v2.0)的核心输入，代码完全缺失 |
| `mss_score/irs_score/pas_score` | 设计要求纳入 TradeSignal，代码完全缺失 |

---

## 差异六：信号过滤逻辑不一致 🟠 P1

### 设计 (trading-algorithm.md §2.1 步骤2-3)

```
过滤条件（串联AND）:
1. final_score >= min_final_score (55)
2. recommendation not in {AVOID, SELL}
3. opportunity_grade != "D"
4. risk_reward_ratio >= 1.0
5. direction映射: bullish→buy, bearish→sell, neutral→hold(过滤)
```

### 代码 (pipeline.py 行995-1043)

```
strict_candidates:
1. final_score >= min_score
2. recommendation not in {SELL, AVOID}
3. risk_reward_ratio >= 1.0
4. direction != "bearish"  ← 额外过滤

fallback_candidates (全新逻辑):
1. risk_reward_ratio >= 1.0
2. recommendation not in {SELL, AVOID}
→ 仅在 strict 全部未成交时启用
```

### 差异点
1. 代码完全**缺少** `opportunity_grade == "D"` 过滤
2. 代码额外过滤了 `direction != "bearish"`（设计中 bearish 映射为 sell，不是直接过滤）
3. 代码额外发明了 **fallback 兜底模式**（设计中无此概念）
4. 设计中 `bearish → sell` 应生成卖出信号，代码直接丢弃了 bearish 信号

---

## 差异七：信号质量验证 v2.0 完全缺失 🔴 P0

### 设计 (trading-algorithm.md §4)

```python
# 基于 neutrality 的风险分级:
neutrality <= 0.3 → risk_level = "low",    position_adjustment = 1.0
neutrality <= 0.6 → risk_level = "medium", position_adjustment = 0.8
neutrality >  0.6 → risk_level = "high",   position_adjustment = 0.6

# 仓位调整:
adjusted_size = signal.position_size × validation.position_adjustment
```

### 代码实现

**完全不存在**。代码无 `ValidationResult` 结构，无 neutrality 读取，无 risk_level 分级，无 position_adjustment 计算。

---

## 差异八：风控检查严重不完整 🔴 P0

### 设计 (trading-algorithm.md §3.1) — 6项风控检查

| 序号 | 检查项 | 代码状态 |
|------|--------|----------|
| 0 | Regime 阈值解析 (fixed/regime) | ❌ 完全缺失 |
| 1 | 资金充足性检查 (买单) | ✅ 有（行928-929） |
| 2 | 单股仓位上限 (max_position_ratio 20%) | ❌ 完全缺失 |
| 2.5 | 行业集中度上限 (max_industry_ratio 30%) | ❌ 完全缺失 |
| 3 | 总仓位上限 (max_total_position 80%) | ✅ 有（行902-918） |
| 4 | T+1 限制 (卖单) | ✅ 有（行990-993 via can_sell_date） |
| 5 | 涨跌停检查 | ✅ 有（买涨停行852，卖跌停行725） |

**缺失的3项风控**:
- 单股仓位上限: 代码仅用 `max_position_pct` 限制买入金额占比，不检查现有持仓+新买入的总占比
- 行业集中度: 完全无行业层面的仓位约束
- Regime 阈值: 不感知市场温度/波动率调节风控参数

---

## 差异九：成交可行性模型完全缺失 🔴 P0

### 设计 (trading-algorithm.md §5.1-5.2)

```
ExecutionFeasibilityModel:
- fill_probability = clip(1.0 - queue_ratio, 0, 1)
- fill_ratio = clip(1.0 - 0.5*queue_ratio - 0.5*capacity_ratio, 0, 1)
- liquidity_tier: L1(p70) / L2(p30) / L3
- impact_cost_bps: 8(L1) / 18(L2) / 35(L3)
- min_fill_probability < 0.35 → reject
```

### 代码实现

**完全不存在**。Trading pipeline 使用简单的"开盘价全额成交"模型:
- `filled_price = price.get("open")` (行891)
- 无 fill_probability / fill_ratio 计算
- 无 liquidity_tier 分层
- 无 impact_cost / slippage 计算

> **对比**: `src/backtest/pipeline.py` 已完整实现 `_estimate_fill()` 和 `_estimate_impact_cost()`，但 trading pipeline 没有复用这些逻辑。

---

## 差异十：止损/止盈/最大回撤检查完全缺失 🔴 P0

### 设计

- 止损检查 (trading-algorithm.md §3.4): `pct_loss <= -8%` → 触发止损卖出
- 最大回撤检查 (trading-algorithm.md §3.5): `drawdown >= 15%` → 触发限制
- 信息流日终处理 (trading-information-flow.md §2.1 步骤9-10): 止损止盈监控 + 日终市值/回撤检查

### 代码实现

**全部不存在**。代码无止损逻辑、无止盈逻辑、无回撤检查。持仓只在 T+1 解锁后无条件全部卖出。

---

## 差异十一：订单状态机简化 🟠 P1

### 设计 (trading-algorithm.md §7)

6种状态: `pending → submitted → partially_filled → filled / cancelled / rejected`

### 代码

仅2种最终状态: `filled` 或 `rejected`。
无 `pending`、`submitted`、`partially_filled`、`cancelled` 中间状态。

---

## 差异十二：数据模型枚举未实现 🟡 P2

### 设计 (trading-data-models.md §6)

定义了7个枚举类: `OrderStatus`, `OrderType`, `Direction`, `RiskLevel`, `RejectReason`, `TradingState`, `ExecutionMode`

### 代码

无枚举定义，全部使用硬编码字符串。

设计中 `RejectReason` 有11个值，代码中实际使用的 reject_reason 有:
- `REJECT_NO_MARKET_PRICE` — 不在设计枚举中（设计用 `REJECT_NO_OPEN_PRICE`）
- `REJECT_LIMIT_UP` ✓
- `REJECT_LIMIT_DOWN` ✓
- `REJECT_MAX_TOTAL_POSITION` ✓
- 其余设计中的 `REJECT_NO_CASH`, `REJECT_MAX_POSITION`, `REJECT_MAX_INDUSTRY`, `REJECT_T1_FROZEN`, `REJECT_LOW_FILL_PROB`, `REJECT_ZERO_FILL` — 代码中无对应逻辑

---

## 差异十三：risk_events 表设计文档完全无覆盖 🟡 P2

代码中 `risk_events` 表被大量使用（写入风控事件到 DuckDB），但 `trading-data-models.md` 中完全没有这张表的 DDL 定义。

代码中使用的字段: `trade_date`, `stock_code`, `event_type`, `severity`, `message`, `contract_version`, `created_at`

---

## 差异十四：Gate 机制差异 🟠 P1

### 设计 (trading-algorithm.md §2.1)

```
gate = get_validation_gate_decision(trade_date)
if gate.final_gate == "FAIL": 阻断
if gate.contract_version != "nc-v1": 阻断
```

### 代码

- 回测门禁: `_read_s3_backtest_status()` — 读取 backtest_results 表，检查 quality_status + go_nogo
- 质量门禁: `_read_quality_gate_status()` — 读取 quality_gate_report 表
- 契约版本检查: 读取 signal 的 contract_version 列

代码实现了**双重门禁**（回测 + 质量），设计仅描述了单一 validation_gate_decision。功能更丰富但模型不对齐。

---

## 差异总结统计

| 严重程度 | 数量 | 说明 |
|----------|------|------|
| 🔴 P0-CRITICAL | 6 | 信号字段缺失、v2.0验证缺失、风控不完整、成交模型缺失、止损缺失、t1_frozen缺失 |
| 🟠 P1-MAJOR | 5 | trade_records字段、positions字段、信号过滤偏离、订单状态机简化、Gate模型差异 |
| 🟡 P2-MINOR | 4 | 枚举未实现、risk_events无设计、字段命名差异、updated_at缺失 |
| 🔵 P3-NOTE | 1 | 3个设计文档实现状态过时 |

**总计: 16项差异**
