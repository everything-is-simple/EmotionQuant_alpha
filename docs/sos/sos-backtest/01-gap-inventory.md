# 01 — 差异清单（Backtest 篇）

**对比范围**:
- 设计文档：`docs/design/core-infrastructure/backtest/` 下 6 个文件
- 代码：`src/backtest/pipeline.py`, `src/config/config.py`, `src/models/enums.py`

**标记规则**: 🔴 根本性偏离（功能缺失/逻辑错误） | 🟡 次要偏离（可延后/低风险）

---

## GAP-B01 🔴 卖出逻辑——T+1 后无条件清仓 vs 条件触发退出

**设计**: backtest-algorithm.md §4.8-§4.9
- 持仓卖出仅在三种条件下触发：止损（`stop_loss_pct`）、止盈（`take_profit_pct`）、时限平仓（`max_holding_days`）
- 优先级：`stop_loss > take_profit > time_exit`
- 每日收盘后扫描：`drawdown_from_cost = (close - cost_price) / cost_price`
- 卖出信号在 signal_date 生成，execute_date 执行
- 若 execute_date 跌停/停牌，信号顺延到下一可成交日

**代码**: `src/backtest/pipeline.py:1102-1185`
```python
for stock_code, pos in list(positions.items()):
    can_sell_date = str(pos.get("can_sell_date", replay_day))
    if replay_day < can_sell_date:
        continue
    # ← 无任何条件判断，直接进入卖出撮合
```
- 只要 `replay_day >= can_sell_date`（T+1 解锁），**无条件卖出全部持仓**
- 没有止损/止盈/持仓天数的任何判断逻辑
- 没有卖出顺延机制

**本质**: 整个回测退化为"买入→次日即卖"的超短线策略，与设计中的持仓管理策略完全相反。

---

## GAP-B02 🔴 max_drawdown 公式错误

**设计**: backtest-algorithm.md §5.2
```
drawdown_t = (equity_t - peak_t) / peak_t
max_drawdown = min(drawdown_t)
```
标准最大回撤：从峰值逐日追踪到谷值的最大跌幅。

**代码**: `src/backtest/pipeline.py:1520-1522`
```python
max_equity = max(equity_curve) if equity_curve else initial_cash
min_equity = min(equity_curve) if equity_curve else initial_cash
max_drawdown = round((max_equity - min_equity) / max(1.0, max_equity), 8)
```
这是 `(全局最高 - 全局最低) / 全局最高`。反例：曲线 `[80, 100, 120, 90]`，设计= `-25%`（从120跌到90），代码= `33.3%`（把初始80也算进范围）。

---

## GAP-B03 🔴 total_return 口径偏差（已实现PnL vs 期末权益）

**设计**: backtest-algorithm.md §5.1
```
total_return = (equity_end - equity_start) / equity_start
```
基于期末总权益（含未平仓持仓市值）。

**代码**: `src/backtest/pipeline.py:1513-1514`
```python
total_pnl = float(sell_frame["pnl"].sum()) if not sell_frame.empty else 0.0
total_return = round(total_pnl / max(1.0, initial_cash), 8)
```
仅统计已卖出交易的实现盈亏。如果回测结束时仍持有股票，这些持仓的浮动盈亏完全被忽略。

---

## GAP-B04 🔴 信号过滤严重缺失（4层只实现1层）

**设计**: backtest-algorithm.md §3.1 Step 2
四层过滤：
1. `final_score < config.min_final_score` → 跳过
2. `recommendation` 等级 < `config.min_recommendation` → 按等级排序跳过（STRONG_BUY>BUY>HOLD>SELL>AVOID）
3. `direction == "neutral"` → 跳过（与 Trading 对齐）
4. `risk_reward_ratio < 1.0` → 跳过（RR<1 软过滤）

**代码**: `src/backtest/pipeline.py:1085-1091`
```python
_filtered["_rec"] = _filtered["recommendation"].astype(str).str.strip().str.upper()
_filtered["_ps"] = pd.to_numeric(_filtered["position_size"], errors="coerce").fillna(0.0)
_filtered = _filtered[
    _filtered["_rec"].isin(LONG_ENTRY_RECOMMENDATIONS) & (_filtered["_ps"] > 0.0)
]
```

| 层 | 条件 | 代码状态 |
|----|------|----------|
| 1 | `final_score < 55.0` | ❌ config 有 `backtest_min_final_score=55.0` 但未使用 |
| 2 | recommendation 等级 | ⚠️ 硬编码 `{STRONG_BUY, BUY}` 无等级排序 |
| 3 | `direction == "neutral"` | ❌ 完全未实现 |
| 4 | `risk_reward_ratio < 1.0` | ❌ 误实现为全局P0 error（pipeline.py:979-981），阻断整个回测而非单信号过滤 |

---

## GAP-B05 🔴 Validation Gate 粒度错误（全局阻断 vs 逐日跳过）

**设计**: backtest-algorithm.md §3.1 Step 0
```
gate = get_validation_gate_decision(signal_date)
if gate.final_gate == "FAIL":
    set_backtest_state("blocked_gate_fail")
    return []  # 仅跳过当日信号
```
逐日检查：当日 FAIL 跳过当日，其余日正常运行。

**代码**: `src/backtest/pipeline.py:995-997`
```python
quality_status, go_nogo, quality_message = _to_quality_status(gate_frame)
if quality_status == "FAIL":
    add_error("P0", "quality_gate", quality_message)
```
全局检查：gate_frame 中**任何一天** FAIL → 整个回测标记为 P0 error → 停止所有交易。

---

## GAP-B06 🔴 仓位计算基数错误（cash vs equity）

**设计**: backtest-algorithm.md §3.4
```
target_cash = equity × min(signal.position_size, max_position_pct)
shares = floor(target_cash / signal.entry / 100) × 100
```
`equity = cash + 持仓市值`。

**代码**: `src/backtest/pipeline.py:1336-1339`
```python
capped_position = max(0.0, min(max_position_pct, position_size))
raw_shares = int((cash * capped_position) / filled_price)
shares = (raw_shares // 100) * 100
```
仅用 `cash`（不含持仓市值）。买入越多 cash 越小，后续标的仓位被不断压缩。

---

## GAP-B07 🔴 核心绩效指标全部缺失

**设计**: backtest-algorithm.md §5.1-§5.3 + backtest-data-models.md §1.6 `BacktestMetrics`
明确要求：`annual_return`, `volatility`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `profit_factor`, `avg_trade`, `avg_win`, `avg_loss`, `max_win`, `max_loss`, `fill_rate`

**代码**: `src/backtest/pipeline.py` BACKTEST_RESULT_COLUMNS
- ❌ `annual_return` — 未计算
- ❌ `volatility` — 未计算
- ❌ `sharpe_ratio` — 未计算
- ❌ `sortino_ratio` — 未计算
- ❌ `calmar_ratio` — 未计算
- ❌ `profit_factor` — 未计算
- ❌ `avg_trade/avg_win/avg_loss/max_win/max_loss` — 未计算
- ❌ `fill_rate` — 未计算

代码替代了另一组指标（`daily_return_mean/std/skew/p05/p95`, `turnover_mean/std/cv`, `cost_bps`, `impact_cost_ratio`），这些在设计中不存在。

---

## GAP-B08 🔴 max_positions 约束缺失

**设计**: backtest-algorithm.md §3.4 + backtest-data-models.md §1.1
`max_positions` 限制最大同时持仓数（默认 10）。

**代码**: `src/config/config.py:207`
Config 中有 `backtest_max_positions: int = 10`，但回测循环中 **从未使用**。只检查了 `stock_code in positions`（防重复），不限制总持仓数量。

---

## GAP-B09 🔴 成交价无滑点

**设计**: backtest-algorithm.md §4.2
```
成交价：开盘价 ± 滑点
- auction：开盘价 ± 滑点
```

**代码**:
- 卖出 (`pipeline.py:1119`): `filled_price = float(price.get("open", 0.0))`
- 买入 (`pipeline.py:1329`): `filled_price = float(price.get("open", 0.0))`

直接用原始开盘价，滑点 `config.backtest_slippage_value` 仅体现在 `_estimate_impact_cost` 的独立费用项中，不影响 `filled_price`。

---

## GAP-B10 🔴 回测模式（TD/BU）支持缺失

**设计**: backtest-algorithm.md §2-§3.2
- 支持 `top_down / bottom_up / dual_verify / complementary` 四种模式
- BU 模式需查询 `pas_breadth_daily.pas_sa_ratio` 做活跃度门控
- 活跃度不足时回退 TD 信号并标记 `warn_mode_fallback`
- 模式切换策略：`config_fixed / regime_driven / hybrid_weight`

**代码**: `src/backtest/pipeline.py`
- 完全没有模式处理
- 不读取 `integration_mode` 做过滤
- 不查询 `pas_breadth_daily`
- 所有 `integrated_recommendation` 信号不分模式统一消费

---

## GAP-B11 🔴 成交概率模型不一致

**设计**: backtest-algorithm.md §4.2
```
fill_probability = limit_lock_factor × (0.45 × queue_factor + 0.55 × participation_factor)
queue_factor = clip(volume_auction / max(order_amount, 1), 0, 1)
participation_factor = clip(volume_day / max(free_float_shares, 1) / turnover_ref, 0, 1)
```

**代码**: `src/backtest/pipeline.py:749-764` (`_estimate_fill`)
```python
queue_ratio = min(1.0, float(order_shares) / queue_capacity)
fill_probability = _clip(1.0 - queue_ratio, 0.0, 1.0)
```
简化为 `1 - queue_ratio`，没有 `participation_factor`，没有加权 `0.45/0.55`，没有 `limit_lock_factor`。

---

## GAP-B12 🔴 停牌处理缺失

**设计**: backtest-algorithm.md §4.1
- 停牌日不成交、不计入可卖天数，持仓顺延
- §4.8：停牌日不计入 `max_holding_days`

**代码**: `src/backtest/pipeline.py`
- 没有显式停牌检测。`price_lookup.get()` 返回 `None` 时仅跳过（`missing_price_exit_count += 1`）
- 无法区分"停牌"和"数据缺失"
- 没有持仓天数的挂起逻辑

---

## GAP-B13 🟡 架构完全不同（OOP vs 单函数）

**设计**: backtest-api.md §1.1-§1.8
定义了完整 OOP 架构：`BacktestRunner`, `QlibEngine`, `LocalVectorizedEngine`, `BacktraderCompatEngine`, `IntegrationSignalProvider`, `ExecutionPolicy`, `ExecutionFeasibilityModel`, `FeeModel`, `LiquidityCostModel`, `OrderSequencer`, `BacktestRepository`, `BacktraderDataAdapter`, `QlibDataAdapter`

**代码**: `src/backtest/pipeline.py`
单一 `run_backtest()` 函数约 1800 行，无类定义。仅有一个 `BacktestRunResult` dataclass。

**差异性质**: 代码采用过程式风格。backtest-api.md §1.2 标注 "OOP 接口为未来扩展口径"。

---

## GAP-B14 🟡 7 个 dataclass 全部缺失

**设计**: backtest-data-models.md §1.1-§1.7
定义了: `BacktestConfig`, `AShareFeeConfig`, `BacktestSignal`, `BacktestTrade`, `Position`, `EquityPoint`, `BacktestMetrics`, `BacktestResult`

**代码**: 仅有 `BacktestRunResult`（内容完全不同）。所有中间数据使用 raw dict。

---

## GAP-B15 🟡 7 个枚举定义缺失

**设计**: backtest-data-models.md §3.1-§3.7
定义了: `OrderType`, `TradeStatus`, `FilledReason`, `SignalSource`, `BacktestMode`, `EngineType`, `BacktestState`

**代码**: `src/models/enums.py` 已有 `RecommendationGrade`/`GateDecision`，但 backtest 未使用任何枚举。全部用字符串常量（如 `SUPPORTED_ENGINE = {"qlib", "local_vectorized", "backtrader_compat"}`）。

---

## GAP-B16 🟡 backtest_trade_records 表结构严重偏离

**设计DDL**: backtest-data-models.md §2.1（27个字段）
**代码**: pipeline.py `BACKTEST_TRADE_COLUMNS`（23个字段），仅约10个重合。

**设计有、代码无**: `trade_id`, `stock_name`, `order_type`, `signal_price`, `commission`, `stamp_tax`, `transfer_fee`, `slippage`, `impact_cost_bps`, `total_fee`, `fill_probability`, `queue_ratio`, `liquidity_tier`, `backtest_state`, `filled_time`, `filled_reason`, `hold_days`, `signal_score`, `signal_source`, `signal_id`

**代码有、设计无**: `trade_date`, `reject_reason`, `t1_restriction_hit`, `limit_guard_result`, `session_guard_result`, `weight_plan_id`, `contract_version`

---

## GAP-B17 🟡 backtest_results 表结构严重偏离

**设计DDL**: backtest-data-models.md §2.3

**设计有、代码无**: `backtest_name`, `integration_mode`, `initial_cash`, `final_value`, `annual_return`, `volatility`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `profit_factor`, `avg_trade/win/loss`, `max_win/loss`, `fill_rate`, `limit_up_rejected`, `auction_failed`, `config_params(JSON)`, `equity_curve(JSON)`, `trades_detail(JSON)`

**代码有、设计无**: `engine`(非`engine_type`), `quality_status`, `go_nogo`, `consumed_signal_rows`, `max_drawdown_days`, `daily_return_*`, `turnover_*`, `cost_bps`, `impact_cost_ratio`, `source_fetch_*`, `bridge_check_status`

---

## GAP-B18 🟡 BacktestState 状态机未实现

**设计**: backtest-data-models.md §3.7
每个信号/交易应标记 `backtest_state`: `normal / warn_data_fallback / warn_mode_fallback / blocked_gate_fail / blocked_contract_mismatch / blocked_untradable`

**代码**: 使用 errors/warnings 列表做全局状态追踪，无逐信号/逐交易的状态标记。

---

## GAP-B19 🟡 代码含设计未涉及的概念

代码中存在但设计未覆盖的功能：

| 概念 | 位置 | 描述 |
|------|------|------|
| S3/S3R Spiral 修复模式 | `run_backtest` `repair` 参数 | S3R 模式下生成 patch_note + delta_report |
| validation_weight_plan bridge | `_read_bridge_check` | 验证 integrated_recommendation 与 validation_weight_plan 的桥接 |
| A/B/C metric proxy 对比 | `ab_metric_summary` | 用 MSS/IRS/PAS 评分偏移估算基准收益 |
| quality_status / go_nogo | 全局门禁 | 与 quality_gate_report 联动的通过/阻断判定 |
| fee_tier (S/M/L) | `_resolve_fee_tier` | 按成交额分档调整佣金乘数 |
| 流动性枯竭检测 | `_is_liquidity_dryup` | volume < 5万股 or amount < 150万 → 拒单 |
| 一字板检测 | `_is_one_word_board` | open ≈ high ≈ low → 不可买入 |

---

## 汇总对照表

| GAP ID | 严重度 | 设计文档 | 代码位置 | 差异类型 |
|--------|--------|----------|----------|----------|
| B01 | 🔴 | algorithm §4.8-§4.9 | pipeline.py:1102-1185 | 逻辑反转 |
| B02 | 🔴 | algorithm §5.2 | pipeline.py:1520-1522 | 公式错误 |
| B03 | 🔴 | algorithm §5.1 | pipeline.py:1513-1514 | 口径偏差 |
| B04 | 🔴 | algorithm §3.1 Step 2 | pipeline.py:1085-1091 | 功能缺失 |
| B05 | 🔴 | algorithm §3.1 Step 0 | pipeline.py:995-997 | 粒度错误 |
| B06 | 🔴 | algorithm §3.4 | pipeline.py:1336-1339 | 基数错误 |
| B07 | 🔴 | algorithm §5, data-models §1.6 | 整体 | 功能缺失 |
| B08 | 🔴 | algorithm §3.4 | 整体 | 约束缺失 |
| B09 | 🔴 | algorithm §4.2 | pipeline.py:1119,1329 | 功能缺失 |
| B10 | 🔴 | algorithm §2-§3.2 | 整体 | 功能缺失 |
| B11 | 🔴 | algorithm §4.2 | pipeline.py:749-764 | 模型不一致 |
| B12 | 🔴 | algorithm §4.1,§4.8 | 整体 | 功能缺失 |
| B13 | 🟡 | api §1.1-§1.8 | 整体 | 架构偏离 |
| B14 | 🟡 | data-models §1.1-§1.7 | 整体 | 模型缺失 |
| B15 | 🟡 | data-models §3.1-§3.7 | 整体 | 枚举缺失 |
| B16 | 🟡 | data-models §2.1 | BACKTEST_TRADE_COLUMNS | 表结构偏离 |
| B17 | 🟡 | data-models §2.3 | BACKTEST_RESULT_COLUMNS | 表结构偏离 |
| B18 | 🟡 | data-models §3.7 | 整体 | 状态机缺失 |
| B19 | 🟡 | — | 整体 | 设计未覆盖 |
