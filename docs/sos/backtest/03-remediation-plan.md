# 03 — 急救修复方案（Backtest 篇）

## 修复策略总原则

鉴于差异的广度和深度，建议采用**"代码向设计对齐，设计承认阶段性现实"**的折中策略：

1. **代码必须修的**：交易逻辑错误、公式错误、信号过滤缺失、Gate 粒度错误 → 代码修向设计
2. **设计可以降级标注的**：完整 OOP 架构、全量 dataclass/枚举、多引擎适配 → 设计标注 `[MVP-DEFERRED]`
3. **双向对齐的**：表结构（以设计为准统一命名，代码有价值的额外字段反哺设计）、代码中的增强功能（S3/S3R, bridge, 流动性枯竭检测等）反哺设计

---

## 第一批：P0 紧急修复（预计工时：1-2 天）

### FIX-B01: 重写卖出逻辑为条件触发退出 (GAP-B01)

**问题**: T+1 解锁后无条件卖出全部持仓

**代码修改**: `src/backtest/pipeline.py` 卖出循环（~1102-1185）

**修复思路**:

1. 在 `positions` dict 中增加字段：
```python
positions[stock_code] = {
    # ... 现有字段 ...
    "cost_price": filled_price,          # [新增] 成本价
    "buy_trade_date": replay_day,        # [新增] 买入交易日
    "active_holding_days": 0,            # [新增] 有效持仓天数（停牌不计）
}
```

2. 将卖出循环拆为两阶段：**盘后风控扫描** + **次日执行**
```
# 阶段 1: 每日盘后扫描，生成卖出信号（不立即执行）
pending_sell_signals: dict[str, dict] = {}  # stock_code → sell_signal

for stock_code, pos in positions.items():
    price = price_lookup.get((replay_day, stock_code))
    if not price:
        continue  # 停牌：不计入 holding_days，不触发风控
    close_price = float(price.get("close", 0.0))
    if close_price <= 0:
        continue

    # 更新有效持仓天数
    pos["active_holding_days"] += 1

    cost_price = float(pos.get("cost_price", 0.0))
    if cost_price <= 0:
        continue

    pnl_from_cost = (close_price - cost_price) / cost_price
    holding_days = int(pos.get("active_holding_days", 0))

    # 条件判断（按优先级）
    reason = None
    if pnl_from_cost <= -config.backtest_stop_loss_pct:
        reason = "stop_loss"
    elif pnl_from_cost >= config.backtest_take_profit_pct:
        reason = "take_profit"
    elif holding_days >= config.backtest_max_holding_days:
        reason = "time_exit"

    if reason:
        pending_sell_signals[stock_code] = {"reason": reason, "signal_date": replay_day}

# 阶段 2: 次日执行（在 execute_date 处理 pending_sell_signals）
```

3. 在回放主循环中，每个 replay_day 先处理上一日的 pending_sell_signals（作为卖出执行），再生成新信号

4. 卖出失败（跌停/停牌）时保留 pending_sell_signals 顺延到下一交易日

**验证**: 运行回测后检查 trade_records 中 `direction=sell` 的记录，确认 hold_days > 1

---

### FIX-B02: 修正 max_drawdown 公式 (GAP-B02)

**代码修改**: `src/backtest/pipeline.py:1520-1522`

```python
# 当前代码
max_equity = max(equity_curve) if equity_curve else initial_cash
min_equity = min(equity_curve) if equity_curve else initial_cash
max_drawdown = round((max_equity - min_equity) / max(1.0, max_equity), 8)

# 修复为
peak = equity_curve[0] if equity_curve else initial_cash
max_drawdown = 0.0
for equity in equity_curve:
    if equity > peak:
        peak = equity
    drawdown = (equity - peak) / peak if peak > 0 else 0.0
    if drawdown < max_drawdown:
        max_drawdown = drawdown
max_drawdown = round(abs(max_drawdown), 8)
```

**验证**: 用已知权益曲线 `[100, 120, 90, 110]` 检查输出为 0.25 而非 0.25（碰巧一样），再用 `[80, 120, 90, 110]` 检查输出为 0.25 而非 0.333。

---

### FIX-B03: 修正 total_return 为权益口径 (GAP-B03)

**代码修改**: `src/backtest/pipeline.py:1513-1514`

```python
# 当前代码
total_pnl = float(sell_frame["pnl"].sum()) if not sell_frame.empty else 0.0
total_return = round(total_pnl / max(1.0, initial_cash), 8)

# 修复为
equity_end = equity_curve[-1] if equity_curve else initial_cash
total_return = round((equity_end - initial_cash) / max(1.0, initial_cash), 8)
```

**验证**: 构造一个回测结束时仍有未平仓持仓的场景，确认 total_return 包含浮动盈亏。

---

### FIX-B04: 补齐信号过滤 4 层 (GAP-B04)

**代码修改**: `src/backtest/pipeline.py:1085-1091` + `979-981`

**步骤 1**: 将 RR<1 从全局阻断改为 warning
```python
# 当前代码 (979-981)
rr_filtered = integrated_frame[integrated_frame["risk_reward_ratio"] < 1.0]
if not rr_filtered.empty:
    add_error("P0", "contract", "integrated_recommendation_rr_below_threshold")

# 修复为
rr_filtered = integrated_frame[integrated_frame["risk_reward_ratio"] < 1.0]
if not rr_filtered.empty:
    add_warning("integrated_recommendation_rr_below_threshold_count=" + str(len(rr_filtered)))
```

**步骤 2**: 补齐 4 层过滤
```python
RECOMMENDATION_RANK = {"AVOID": 0, "SELL": 1, "HOLD": 2, "BUY": 3, "STRONG_BUY": 4}
MIN_RECOMMENDATION_RANK = RECOMMENDATION_RANK.get("BUY", 3)  # 默认 BUY 及以上

_filtered = integrated_frame.copy()
_filtered["_rec"] = _filtered["recommendation"].astype(str).str.strip().str.upper()
_filtered["_ps"] = pd.to_numeric(_filtered["position_size"], errors="coerce").fillna(0.0)
_filtered["_fs"] = pd.to_numeric(_filtered["final_score"], errors="coerce").fillna(0.0)
_filtered["_rr"] = pd.to_numeric(_filtered["risk_reward_ratio"], errors="coerce").fillna(0.0)

# 层 1: min_final_score
_filtered = _filtered[_filtered["_fs"] >= float(config.backtest_min_final_score)]
# 层 2: min_recommendation (等级排序)
_filtered = _filtered[_filtered["_rec"].map(RECOMMENDATION_RANK).fillna(-1) >= MIN_RECOMMENDATION_RANK]
# 层 3: direction != neutral (需先确认列存在)
if "direction" in _filtered.columns:
    _filtered = _filtered[_filtered["direction"].astype(str).str.strip().str.lower() != "neutral"]
# 层 4: risk_reward_ratio >= 1.0
_filtered = _filtered[_filtered["_rr"] >= 1.0]
# 层 5 (保留): position_size > 0
_filtered = _filtered[_filtered["_ps"] > 0.0]
```

**验证**: 构造含 `direction=neutral` 和 `risk_reward_ratio=0.8` 的测试数据，确认它们被过滤而不是阻断整个回测。

---

### FIX-B05: Gate 逻辑改为逐日跳过 (GAP-B05)

**代码修改**: `src/backtest/pipeline.py:988-997` + 信号分组逻辑

**步骤 1**: 构建按日 Gate 查询表
```python
gate_by_date: dict[str, str] = {}
if not gate_frame.empty and "trade_date" in gate_frame.columns:
    for row in gate_frame.itertuples(index=False):
        date = str(getattr(row, "trade_date", "")).strip()
        status = str(getattr(row, "status", "PASS")).strip().upper()
        if date:
            gate_by_date[date] = status
```

**步骤 2**: 将全局 FAIL 阻断改为 warning
```python
# 当前代码
if quality_status == "FAIL":
    add_error("P0", "quality_gate", quality_message)

# 修复为
if quality_status == "FAIL":
    add_warning(f"quality_gate_has_fail_dates: {quality_message}")
```

**步骤 3**: 在信号按日分组时，跳过 FAIL 日的信号
```python
for record in _filtered.to_dict("records"):
    signal_date = str(record.get("trade_date", ""))
    # [新增] 逐日 Gate 检查
    if gate_by_date.get(signal_date, "PASS") == "FAIL":
        # 跳过当日信号，记录 blocked_gate_fail
        continue
    execute_date = _next_trade_day(replay_days, signal_date)
    # ... 正常处理 ...
```

**验证**: 构造一个窗口内 Day1=FAIL, Day2=PASS 的场景，确认 Day1 信号被跳过、Day2 信号正常执行。

---

### FIX-B06: 仓位基数改为 equity (GAP-B06)

**代码修改**: `src/backtest/pipeline.py:1336-1339`

在买入循环前计算当日 equity：
```python
# [新增] 在每日买入阶段前计算当前权益
current_equity = cash
for _sc, _pos in positions.items():
    _px = price_lookup.get((replay_day, _sc), {})
    _close = float(_px.get("close", 0.0) or _pos.get("buy_price", 0.0) or 0.0)
    current_equity += _close * int(_pos.get("shares", 0))

# 修改仓位计算
# 当前: raw_shares = int((cash * capped_position) / filled_price)
# 修复为:
raw_shares = int((current_equity * capped_position) / filled_price)
```

**同时增加资金检查**: 确保 `required_cash <= cash`（现有逻辑已有此检查）。

---

## 第二批：P1 功能补齐（预计工时：2-3 天）

### FIX-B07: 绩效指标补齐 + equity_curve 持久化 (GAP-B07)

**与 Analysis 篇 GAP-A07 合并修复**

**步骤 1**: equity_curve 持久化
- 在 `BACKTEST_RESULT_COLUMNS` 新增 `equity_curve` 列
- 在 result_frame 构建时写入 `json.dumps(equity_curve)`

**步骤 2**: 新增 `_compute_performance_metrics()` 函数
```python
def _compute_performance_metrics(
    equity_curve: list[float],
    trade_frame: pd.DataFrame,
    risk_free_rate: float,
) -> dict[str, float]:
    # daily_returns
    series = pd.Series(equity_curve, dtype=float)
    daily_returns = series.pct_change().dropna()
    N = len(daily_returns)
    if N == 0:
        return {k: 0.0 for k in [...]}

    # total_return (已在 FIX-B03 修正)
    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
    annual_return = (1 + total_return) ** (252 / max(N, 1)) - 1

    # volatility
    volatility = float(daily_returns.std()) * (252 ** 0.5)

    # sharpe
    rf_daily = risk_free_rate / 252
    excess = daily_returns - rf_daily
    sharpe = (252 ** 0.5) * float(excess.mean()) / float(excess.std()) if excess.std() > 0 else 0.0

    # sortino
    downside = excess.clip(upper=0.0)
    downside_dev = (downside ** 2).mean() ** 0.5
    sortino = (252 ** 0.5) * float(excess.mean()) / downside_dev if downside_dev > 0 else 0.0

    # max_drawdown (已在 FIX-B02 修正)
    # calmar
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    # trade stats
    sells = trade_frame[(trade_frame["direction"] == "sell") & (trade_frame["status"] == "filled")]
    wins = sells[sells["pnl"] > 0]
    losses = sells[sells["pnl"] < 0]
    win_rate = len(wins) / len(sells) if len(sells) > 0 else 0.0
    profit_factor = abs(wins["pnl"].sum() / losses["pnl"].sum()) if len(losses) > 0 and losses["pnl"].sum() != 0 else 0.0
    # ...
```

**步骤 3**: 在 `BACKTEST_RESULT_COLUMNS` 和 result_frame 中补齐所有指标字段

**覆盖 GAP**: B07 + Analysis A07

---

### FIX-B08: max_positions 约束 (GAP-B08)

**代码修改**: `src/backtest/pipeline.py` 买入循环入口

```python
# 在 for signal in signals_by_execute_date.get(replay_day, []) 循环内，开头增加:
if len(positions) >= int(config.backtest_max_positions):
    break
```

---

### FIX-B09: 成交价加入滑点 (GAP-B09)

**代码修改**: `src/backtest/pipeline.py`

买入 (~1329):
```python
# 当前: filled_price = float(price.get("open", 0.0))
# 修复为:
open_price = float(price.get("open", 0.0))
filled_price = open_price * (1.0 + float(config.backtest_slippage_value))
```

卖出 (~1119):
```python
# 当前: filled_price = float(price.get("open", 0.0))
# 修复为:
open_price = float(price.get("open", 0.0))
filled_price = open_price * (1.0 - float(config.backtest_slippage_value))
```

保留 `_estimate_impact_cost` 作为额外的流动性冲击成本（两者并行）。

---

### FIX-B10: 回测模式过滤 (GAP-B10)

**代码修改**: `src/backtest/pipeline.py`

**步骤 1**: `run_backtest()` 增加 `integration_mode` 参数（默认 `"top_down"`）
**步骤 2**: 信号读取 SQL 增加 `WHERE integration_mode = ?` 过滤
**步骤 3**: BU 模式占位（读取 `pas_breadth_daily`，活跃度不足回退 TD）

---

### FIX-B11: 逐笔费用 + hold_days 持久化 (GAP-B16 部分 + Analysis A08/A12)

**与 Analysis 篇 GAP-A08/A12 合并修复**

在 `BACKTEST_TRADE_COLUMNS` 中新增:
`commission`, `stamp_tax`, `transfer_fee`, `impact_cost`, `total_fee_per_trade`, `hold_days`, `stock_name`, `signal_id`

在 trade_rows 构建中填充实际值（当前这些值已在内存中计算，只需写入 dict）。

**覆盖 GAP**: B16（部分）+ Analysis A08, A12, A15

---

## 第三批：P2 精细化 + 表结构对齐（预计工时：1-2 天）

### FIX-B12: 停牌处理 (GAP-B12)

1. 增加显式停牌检测：`volume == 0 and amount == 0` → 视为停牌
2. 停牌日 `active_holding_days` 不递增
3. 停牌日卖出信号（pending_sell_signals）保留并顺延

### FIX-B13: 成交概率模型对齐 (GAP-B11)

将 `_estimate_fill()` 改为设计中的加权模型（需额外 `free_float_shares` 输入）。可先用合理默认值。

### FIX-B14: 表结构命名对齐 (GAP-B16/B17)

**原则**: 字段名以设计DDL为准，代码有价值的额外字段保留并反哺设计。

| 表 | 重命名 | 补齐 | 反哺设计 |
|----|--------|------|----------|
| backtest_trade_records | — | `trade_id`, `stock_name`, `order_type`, `signal_price`, `fill_probability`, `queue_ratio`, `liquidity_tier`, `backtest_state`, `filled_reason`, `hold_days`, `signal_score`, `signal_source`, `signal_id` | `reject_reason`, `t1_restriction_hit`, `limit_guard_result`, `session_guard_result`, `weight_plan_id`, `contract_version` |
| backtest_results | `engine` → `engine_type` | `backtest_name`, `integration_mode`, `initial_cash`, `final_value`, `annual_return`, `volatility`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `equity_curve(JSON)` | `quality_status`, `go_nogo`, `consumed_signal_rows`, `daily_return_*`, `turnover_*`, `cost_bps`, `impact_cost_ratio`, `source_fetch_*`, `bridge_check_status` |

---

## 第四批：P3 收尾 + 设计文档修订（预计工时：0.5-1 天）

### FIX-B15: 设计文档修订

| 文档 | 修订内容 |
|------|----------|
| `backtest-algorithm.md` | §4 补充一字板检测、流动性枯竭检测；§6 补充 quality_status/go_nogo 门禁语义 |
| `backtest-api.md` | §1 标注 OOP 架构为 `[TARGET]`，当前为过程式 `[MVP]`；补充 S3/S3R 修复模式接口 |
| `backtest-data-models.md` | §2.1/§2.3 补齐代码有价值的额外字段；§3 标注枚举为 `[TARGET]` |
| `backtest-information-flow.md` | §3 补充 quality_gate_report / validation_weight_plan bridge 数据流 |

### FIX-B16: BacktestState 状态机（可选）

在 trade_rows 中增加 `backtest_state` 字段，对应每笔交易的状态标记。可与 FIX-B14 合并。

### FIX-B17: 代码增强反哺设计 (GAP-B19)

将代码中有价值的增强功能（S3/S3R, bridge, fee_tier, 流动性枯竭, 一字板）正式纳入设计文档。

---

## 修复顺序与依赖关系

```
第一批 P0 (Day 1-2):
  FIX-B02 (max_drawdown) ← 无依赖，最先修（10min）
  FIX-B03 (total_return) ← 无依赖（10min）
  FIX-B04 (信号过滤)    ← 无依赖（30min）
  FIX-B05 (Gate逐日)    ← 无依赖（45min）
  FIX-B06 (仓位基数)    ← 无依赖（20min）
  FIX-B01 (卖出逻辑)    ← 依赖 B06 完成后再改回放循环（1.5h）

第二批 P1 (Day 3-4):
  FIX-B08 (max_positions) ← 无依赖（10min）
  FIX-B09 (滑点)         ← 无依赖（10min）
  FIX-B10 (模式过滤)     ← 无依赖（1h）
  FIX-B07 (绩效指标)     ← 依赖 B02, B03（1.5h）
  FIX-B11 (逐笔费用)     ← 依赖 B01（1h）

第三批 P2 (Day 5-6):
  FIX-B12 (停牌)         ← 依赖 B01（30min）
  FIX-B13 (成交概率)     ← 无依赖（45min）
  FIX-B14 (表结构对齐)   ← 依赖 B07, B11（1.5h）

第四批 P3 (Day 7):
  FIX-B15 (设计文档)     ← 依赖全部代码修复
  FIX-B16 (状态机)       ← 可选
  FIX-B17 (反哺设计)     ← 可选
```

---

## 测试策略

| 修复项 | 需要新增/修改的测试 |
|--------|-------------------|
| FIX-B01 | `test_sell_only_on_stop_loss_trigger`, `test_sell_only_on_take_profit_trigger`, `test_sell_on_max_holding_days`, `test_sell_priority_stoploss_over_takeprofit`, `test_sell_deferred_on_limit_down` |
| FIX-B02 | `test_max_drawdown_from_peak` — 用 `[80,120,90,110]` 验证结果为 0.25 |
| FIX-B03 | `test_total_return_includes_unrealized_pnl` |
| FIX-B04 | `test_filter_min_final_score`, `test_filter_neutral_direction`, `test_rr_below_1_filters_signal_not_blocks_backtest` |
| FIX-B05 | `test_gate_fail_skips_day_not_blocks_all` |
| FIX-B06 | `test_position_size_based_on_equity_not_cash` |
| FIX-B07 | `test_sharpe_ratio_matches_manual_calculation`, `test_sortino_downside_deviation` |
| FIX-B08 | `test_max_positions_limit_enforced` |
| FIX-B09 | `test_buy_price_includes_slippage`, `test_sell_price_includes_slippage` |

---

## 工作量估算汇总

| 批次 | 内容 | 估算 | 覆盖 GAP |
|------|------|------|----------|
| FIX-B01 | 卖出逻辑重写 | 1.5h | B01 |
| FIX-B02 | max_drawdown 修正 | 10min | B02 |
| FIX-B03 | total_return 修正 | 10min | B03 |
| FIX-B04 | 信号过滤补齐 | 30min | B04 |
| FIX-B05 | Gate 逐日化 | 45min | B05 |
| FIX-B06 | 仓位基数修正 | 20min | B06 |
| FIX-B07 | 绩效指标 + equity_curve 持久化 | 1.5h | B07 + Analysis A07 |
| FIX-B08 | max_positions | 10min | B08 |
| FIX-B09 | 滑点 | 10min | B09 |
| FIX-B10 | 模式过滤 | 1h | B10 |
| FIX-B11 | 逐笔费用 + hold_days | 1h | B16(部分) + Analysis A08/A12/A15 |
| FIX-B12 | 停牌处理 | 30min | B12 |
| FIX-B13 | 成交概率模型 | 45min | B11 |
| FIX-B14 | 表结构对齐 | 1.5h | B16/B17 |
| FIX-B15 | 设计文档修订 | 1h | B19 + 各文档 |
| FIX-B16 | 状态机(可选) | 30min | B18 |
| **总计** | | **~11-13h** | **全部 19 项** |

---

## 风险提示

1. **已有回测产物需要重跑**: P0 修复会根本改变交易行为和绩效数字。所有已落库的 `backtest_results` / `backtest_trade_records` 应标记为废弃并重新生成。

2. **Spiral S3 执行卡需同步调整**: 当前 S3 的 artifact 验收标准（`quality_status`/`go_nogo`）可能依赖 Gate 全局阻断行为。FIX-B05 后 Gate 改为逐日跳过，需确认 S3 gate 逻辑是否需要适配。

3. **Analysis 篇联动修复**: FIX-B07 和 FIX-B11 直接解除 Analysis 篇 GAP-A01/A07/A08/A12/A15 的阻塞。建议与 Analysis 篇第一批修复同步执行。

4. **测试覆盖**: 当前无回测模块的单元测试。P0 修复后建议至少补齐 `backtest-test-cases.md` 中 §1-§6 的核心用例。
