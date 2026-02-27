# Backtest Pipeline 代码 vs Trading 核心设计 差异清单

**审计范围**:
- 代码: `src/backtest/pipeline.py` (~1700行)
- 设计: `docs/design/core-infrastructure/trading/` 下全部4个文档
- 对比基准: 同时对比 `src/trading/pipeline.py` 的实现一致性

**审计日期**: 2026-02-27

---

## 前提说明

Backtest 和 Trading 虽然是两个独立模块，但 Trading 核心设计文档中定义的算法、A股约束、成交模型、费用计算规则同时约束两者。本文档审计的是 backtest 代码对 trading 设计中"共享规则"的遵从程度，以及 backtest 与 trading 两套代码之间的一致性。

---

## 差异一：Backtest 反而比 Trading 更接近设计 🟠 P1（系统性问题）

### 关键发现

Trading 设计中定义的成交可行性模型，Trading 代码完全未实现，但 Backtest 代码已实现：

| 设计要求 | Trading 代码 | Backtest 代码 |
|----------|-------------|--------------|
| fill_probability 估计 | ❌ 无 | ✅ `_estimate_fill()` 行749-764 |
| fill_ratio 计算 | ❌ 无 | ✅ `_estimate_fill()` 行763 |
| liquidity_tier 分层 | ❌ 无 | ✅ `_resolve_liquidity_tier()` 行689-694 |
| impact_cost 冲击成本 | ❌ 无 | ✅ `_estimate_impact_cost()` 行729-746 |
| MIN_FILL_PROBABILITY 阈值拦截 | ❌ 无 | ✅ 常量0.35 行48，检查行1344 |
| 一字板检测 | ❌ 无 | ✅ `_is_one_word_board()` 行675-686 |
| 流动性枯竭检测 | ❌ 无 | ✅ `_is_liquidity_dryup()` 行707-713 |
| 费用分档 (S/M/L) | ❌ 无 | ✅ `_resolve_fee_tier()` 行716-722 |

**问题**: 同一个设计文档约束下的两个代码模块，执行模型严重不对称。Trading 用的是"开盘价全额成交"，Backtest 用的是"部分成交 + 冲击成本"，会导致 Backtest 绩效与 Trading 实际交易的预期之间存在系统性偏差。

---

## 差异二：Backtest 信号过滤策略与 Trading 设计/代码均不同 🟠 P1

### 设计 (trading-algorithm.md §2.1)
```
1. final_score >= 55
2. recommendation not in {AVOID, SELL}
3. opportunity_grade != "D"
4. risk_reward_ratio >= 1.0
```

### Trading 代码
```
strict: final_score >= 55 AND recommendation ∉ {SELL, AVOID} AND rr >= 1.0 AND direction != bearish
fallback: rr >= 1.0 AND recommendation ∉ {SELL, AVOID}
```

### Backtest 代码 (行1086-1091)
```
recommendation in {STRONG_BUY, BUY} AND position_size > 0
```

### 差异
- Backtest 只看 `recommendation` 是否为 `STRONG_BUY/BUY`，**不检查** `final_score`、`risk_reward_ratio`、`opportunity_grade`
- 入口过滤完全不同：Backtest 用白名单（仅 BUY/STRONG_BUY），Trading 设计用黑名单（排除 AVOID/SELL/D级）
- 这意味着 Backtest 可能放进 Trading 会拒绝的信号，反之亦然

---

## 差异三：Backtest 缺少部分 Trading 风控检查 🟠 P1

| 风控项 | 设计要求 | Trading 代码 | Backtest 代码 |
|--------|----------|-------------|--------------|
| 资金充足检查 | ✅ | ✅ | ✅ (行1426-1427) |
| 单股仓位上限 | ✅ | ❌ | ✅ (通过 max_position_pct 行1337) |
| 行业集中度 | ✅ | ❌ | ❌ |
| 总仓位上限 | ✅ | ✅ | ❌ (无 max_total_position 检查) |
| T+1 限制 | ✅ | ✅ | ✅ (行1104-1106 can_sell_date) |
| 涨跌停 | ✅ | ✅ | ✅ (行1264/1115) |
| 流动性枯竭 | — | ❌ | ✅ (行1296) |
| 一字板 | — | ❌ | ✅ (行1232) |

**交叉缺失**:
- Backtest 没有总仓位上限检查（Trading 有）
- Trading 没有流动性枯竭/一字板检查（Backtest 有）
- 两者都没有行业集中度检查

---

## 差异四：Backtest 的 trade_records 字段与 Trading 设计不对齐 🟡 P2

Backtest 使用 `BACKTEST_TRADE_COLUMNS` (行109-133):
```
backtest_id, trade_date, signal_date, execute_date, stock_code, direction,
filled_price, shares, amount, pnl, pnl_pct, recommendation, final_score,
risk_reward_ratio, integration_mode, weight_plan_id, status, reject_reason,
t1_restriction_hit, limit_guard_result, session_guard_result,
contract_version, created_at
```

与 Trading 设计的 `trade_records` DDL 对比:

**Backtest 有但 Trading 设计无:**
- `backtest_id`: Backtest 特有，合理
- `signal_date` / `execute_date`: Backtest 区分信号日和执行日（T+1），设计无此概念
- `pnl` / `pnl_pct`: Backtest 特有的盈亏字段
- `recommendation` / `final_score` / `integration_mode` / `weight_plan_id`: 回写信号来源元数据

**Trading 设计有但 Backtest 无:**
- `stock_name`, `order_type`, `slippage`, `total_fee` (Backtest 不计算单条 total_fee)
- `fill_probability`, `fill_ratio`, `liquidity_tier`, `impact_cost_bps` (Backtest 内部计算了但**没写入记录**)
- `trading_state`, `execution_mode`, `slice_seq`, `signal_id`, `updated_at`

---

## 差异五：Backtest 的 reject_reason 扩展了设计枚举 🟡 P2

设计枚举 `RejectReason` (trading-data-models.md §6.5) 有11个值。

Backtest 实际使用的 reject_reason:
- `REJECT_NO_MARKET_PRICE` — 不在设计枚举（设计用 `REJECT_NO_OPEN_PRICE`）
- `REJECT_ONE_WORD_BOARD` — **完全不在设计中**（Backtest 独创）
- `REJECT_LIQUIDITY_DRYUP` — **完全不在设计中**（Backtest 独创）
- `REJECT_LIMIT_UP` ✓
- `REJECT_LOW_FILL_PROB` ✓
- `REJECT_ZERO_FILL` ✓

---

## 差异六：费用计算模型不一致（Trading vs Backtest）🟠 P1

### 设计统一标准 (trading-algorithm.md §5.3)
```
买入费用 = max(金额 × 0.0003, 5) + 金额 × 0.00002
卖出费用 = 金额 × 0.001 + max(金额 × 0.0003, 5) + 金额 × 0.00002
```

### Trading 代码 (pipeline.py 行658-668)
```python
commission = max(min_commission, amount * commission_rate)  # 标准
stamp_tax = amount * stamp_duty_rate if sell                # 标准
transfer_fee = amount * transfer_fee_rate                   # 标准
# 无 impact_cost / fee_tier
```

### Backtest 代码 (pipeline.py 行1055-1070)
```python
fee_tier_label, fee_tier_multiplier = _resolve_fee_tier(amount)
commission = max(min_commission, amount * commission_rate * fee_tier_multiplier)  # 有分档乘数!
stamp_tax = amount * stamp_duty_rate if sell
transfer_fee = amount * transfer_fee_rate
# 额外加 impact_cost
```

### 差异
1. **Backtest 有费用分档**（S/M/L tier，小额×1.15/中额×1.0/大额×0.9），Trading 没有 → 同一笔交易在两个模块费用不同
2. **Backtest 有冲击成本**（impact_cost_total），Trading 没有 → Backtest 费用更高
3. 设计中没有定义"费用分档"概念，这是 Backtest 独创

---

## 差异七：持仓卖出策略根本不同 🔴 P0

### Trading 代码
- T+1 解锁后**立即无条件卖出所有持仓** (行989-993)
- 没有止损/止盈/目标价判断，不管盈亏全卖

### Backtest 代码
- T+1 解锁后**立即无条件卖出** (行1102-1106)
- 同样没有止损/止盈判断

### 设计要求
- 止损: `pct_loss <= -8%` 时触发
- 止盈: 有 `target_price`
- 最大回撤: `drawdown >= 15%` 时限制

### 结论
Trading 和 Backtest 两套代码行为一致（都是 T+1 无条件平仓），但都偏离了设计。设计要求的是**持仓管理 + 条件平仓**，不是"买入→次日全卖"的日内交替模式。

---

## 差异八：Backtest 的成交量/流动性数据使用与设计不一致 🟡 P2

### 设计 (trading-algorithm.md §5.2)
```
liquidity_tier 基于百分位:
- vol >= p70 → L1, impact_cost_bps = 8
- vol >= p30 → L2, impact_cost_bps = 18
- else → L3, impact_cost_bps = 35
```

### Backtest 代码 (_resolve_liquidity_tier, 行689-694)
```python
if volume >= 1_000_000: return "L1"
if volume >= 200_000:   return "L2"
return "L3"
```

使用**绝对阈值**（100万/20万），而非设计中的**百分位**（p70/p30）。这意味着：
- 设计的分层是相对的（自适应市场），代码是固定的
- 两者在不同市场环境下结果可能大幅不同

---

## 差异九：fill_ratio 公式偏差 🟡 P2

### 设计 (trading-algorithm.md §5.2)
```
capacity_ratio = min(order_shares / max(vol * queue_participation_rate, 1), 1.0)
fill_ratio = clip(1.0 - 0.5 * queue_ratio - 0.5 * capacity_ratio, 0.0, 1.0)
```
其中 `queue_ratio` 和 `capacity_ratio` 是两个独立变量。

### Backtest 代码 (_estimate_fill, 行749-764)
```python
queue_capacity = max(1.0, volume * QUEUE_PARTICIPATION_RATE)
queue_ratio = min(1.0, float(order_shares) / queue_capacity)
fill_ratio = _clip(1.0 - 0.50 * queue_ratio, 0.0, 1.0)
```

只用了 `queue_ratio` 一个变量，**缺少 `capacity_ratio`**。设计公式是 `1.0 - 0.5*queue - 0.5*capacity`，代码只做了 `1.0 - 0.5*queue`。这会导致 fill_ratio 系统性偏高。

---

## 差异十：Backtest 特有的检查在 Trading 设计中无对应 🟡 P2

Backtest 独有的检查（设计中无、Trading 代码也无）:

1. **一字板检测** (`_is_one_word_board`): 开盘=最高=最低 → reject REJECT_ONE_WORD_BOARD
2. **流动性枯竭** (`_is_liquidity_dryup`): vol < 5万股 或 amount < 150万 → reject REJECT_LIQUIDITY_DRYUP
3. **费用分档** (`_resolve_fee_tier`): 小额(≤10万)加收15%佣金，大额(≥50万)打9折
4. **冲击成本乘数** (`IMPACT_MULTIPLIER_BY_LIQUIDITY_TIER`): L1×0.7, L2×1.0, L3×1.5

这些是 Backtest 对设计的"超额实现"，但由于没有反映在设计文档中，也没有同步到 Trading 代码中，造成了三方脱节。

---

## 差异总结：Trading vs Backtest 代码一致性矩阵

| 功能模块 | Trading 代码 | Backtest 代码 | 设计要求 | 三方一致？ |
|----------|-------------|--------------|----------|-----------|
| 信号过滤 | strict+fallback | STRONG_BUY/BUY白名单 | 黑名单排除 | ❌ 三方各异 |
| 涨跌停检查 | ✅ | ✅ | ✅ | ✅ 一致 |
| 涨跌停比率 | 主板10%/GEM20%/ST5% | 同 | 同 | ✅ 一致 |
| T+1处理 | can_sell_date | can_sell_date | t1_frozen表 | ⚠️ 代码一致但偏离设计 |
| 费用计算 | 标准费率 | 分档费率+冲击成本 | 标准费率 | ❌ Backtest偏离 |
| 成交模型 | 全额成交 | 部分成交 | 部分成交 | ❌ Trading偏离 |
| 流动性检测 | 无 | 有 | 无(注) | ⚠️ Backtest超额 |
| 持仓管理 | T+1全卖 | T+1全卖 | 条件平仓 | ⚠️ 代码一致但偏离设计 |
| 总仓位上限 | 有 | 无 | 有 | ❌ Backtest缺失 |
| 行业集中度 | 无 | 无 | 有 | ❌ 双缺失 |

**注**: 流动性枯竭检测在 trading-algorithm.md 中没有明确要求，但 trading-api.md §1.3 提到了涨跌停规则，信息流文档也未涉及。

---

## 核心结论

1. **Trading 和 Backtest 的成交模型不对称**：Backtest 用部分成交+冲击成本，Trading 用全额成交。这会导致 Backtest 的绩效评估无法准确反映 Trading 的实际执行效果。
2. **信号过滤策略完全不同**：可能导致 Backtest 回测的是 Trading 不会执行的信号组合。
3. **费用计算基准不同**：Backtest 费用更高（有分档+冲击），Trading 费用更低。
4. **Backtest 有大量"超额实现"未同步回设计和 Trading**：一字板、流动性枯竭、费用分档等。
