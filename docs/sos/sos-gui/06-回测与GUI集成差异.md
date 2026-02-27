# 06 回测与 GUI 集成差异

**对比来源**:
- GUI 设计: gui-data-models.md §1.8 AnalysisPageData / §1.9 BacktestSummaryDisplay
- GUI 代码: src/gui/data_service.py `_map_backtest()` / `_map_performance()`
- 回测代码: src/backtest/pipeline.py `BACKTEST_RESULT_COLUMNS` / `run_backtest()`

---

## 一、BacktestSummaryDisplay 字段映射问题

### GUI 读取的字段 vs 回测写入的字段

GUI `_map_backtest()` (data_service.py:626-643) 从 `backtest_results` 表读取：

| GUI 读取字段 | 回测写入列 | 匹配状态 | 问题描述 |
|-------------|-----------|----------|----------|
| `backtest_name` | **不存在** | ❌ | 回测写 `backtest_id`（如 "BT_20260101_20260131_local_vectorized"），无 `backtest_name` 列。GUI 读到空字符串 |
| `start_date` | `start_date` | ✅ | |
| `end_date` | `end_date` | ✅ | |
| `total_return` | `total_return` | ✅ | |
| `annual_return` | **不存在** | ❌ | 回测不计算年化收益率。GUI 读到 0.0 |
| `max_drawdown` | `max_drawdown` | ✅ | |
| `sharpe_ratio` | **不存在** | ❌ | 回测不计算夏普比率（仅在 performance_metrics 表？但 backtest_results 无此列）。GUI 读到 0.0 |
| `total_trades` | `total_trades` | ✅ | |
| `win_rate` | `win_rate` | ✅ | |

### 影响

Analysis 页面的回测摘要部分将显示：
- backtest_name = ""（空白，无法识别是哪次回测）
- annual_return_pct = "0.0%"（永远显示 0，误导用户）
- sharpe_ratio = 0.0（永远显示 0，关键指标缺失）

---

## 二、PerformanceMetricsDisplay 字段映射问题

GUI `_map_performance()` (data_service.py:604-624) 从 `performance_metrics` 表读取：

| GUI 读取字段 | 回测是否写入此表 | 状态 |
|-------------|-----------------|------|
| `total_return` | ❓ | 回测只写 `backtest_results` 表，`performance_metrics` 表的来源不明确 |
| `annual_return` | ❓ | 同上 |
| `max_drawdown` | ❓ | 同上 |
| `sharpe_ratio` | ❓ | 同上 |
| `sortino_ratio` | ❓ | 同上 |
| `calmar_ratio` | ❓ | 同上 |
| `win_rate` | ❓ | 同上 |
| `profit_factor` | ❓ | 同上 |

### 关键问题

**`performance_metrics` 表的生产者是谁？**

- 回测代码 (`backtest/pipeline.py`) 写入 `backtest_results` 和 `backtest_trade_records` 两个表
- 回测代码**不写** `performance_metrics` 表
- GUI 设计中 `performance_metrics` 被列为 Analysis 页面的输入数据表（gui-data-models.md §5.1）
- 但在搜索整个 src 目录后，未找到任何代码写入 `performance_metrics` 表

**结论**: `performance_metrics` 表可能来自 Analysis 模块（src/analysis/），需要检查。如果 Analysis 模块也未写入此表，则 GUI 的绩效指标将全部显示为 0。

---

## 三、回测输出中有但 GUI 未消费的字段

回测 `backtest_results` 表含有丰富的指标，但 GUI Analysis 页面未消费：

| 回测输出字段 | GUI 是否使用 | 价值评估 |
|-------------|-------------|----------|
| `max_drawdown_days` | ❌ | 高（回撤天数是重要指标） |
| `daily_return_mean` | ❌ | 高 |
| `daily_return_std` | ❌ | 高 |
| `daily_return_p05` / `p95` | ❌ | 中 |
| `daily_return_skew` | ❌ | 中 |
| `turnover_mean` / `std` / `cv` | ❌ | 中 |
| `commission_total` | ❌ | 高（交易成本展示） |
| `stamp_tax_total` | ❌ | 中 |
| `impact_cost_total` | ❌ | 高 |
| `total_fee` | ❌ | 高 |
| `cost_bps` | ❌ | 高（基点成本） |
| `impact_cost_ratio` | ❌ | 中 |
| `bridge_check_status` | ❌ | 低 |

### 建议

GUI Analysis 页面可以大幅丰富展示内容，直接从 `backtest_results` 读取更多指标（无需额外计算）。

---

## 四、backtest_trade_records 表与 Trading 页面

### GUI Trading 页面数据来源

GUI Trading 页面从 `trade_records` 和 `positions` 表读取数据。

### 回测写入的表

回测写入 `backtest_trade_records` 表（注意：不是 `trade_records`）。

| GUI 读表 | 回测写表 | 关系 |
|----------|----------|------|
| `trade_records` | `backtest_trade_records` | ❓ 不同表名 |
| `positions` | 无（回测不写 positions 表） | ❌ |

### 问题

- 如果 Trading 页面期望展示回测产生的交易记录，需要从 `backtest_trade_records` 读取而非 `trade_records`
- 但根据设计，Trading 页面可能面向的是实盘/模拟盘交易记录，而非回测记录
- 这需要明确：Trading 页面的数据来源是实盘还是回测？

---

## 五、daily_report 表

### GUI 读取

Analysis 页面从 `daily_report` 表读取 `content` 字段。

### 回测是否生产

回测代码不写入 `daily_report` 表。它只写 artifacts 目录下的 MD 文件。

### 问题

`daily_report` 表的生产者不明确。可能是 Analysis 模块或 GUI 自身（app.py 的 export_mode="daily-report" 生成 MD 文件到 artifacts 目录，但不写入 DB 表）。

---

## 六、急救方案

### P0 — 立即修复

| 问题 | 方案 |
|------|------|
| `backtest_name` 字段不存在 | 方案A: 在 `_map_backtest` 中用 `backtest_id` 替代。方案B: 回测代码新增 `backtest_name` 列 |
| `annual_return` 字段不存在 | 方案A: 在 GUI 中从 `total_return` + `start/end_date` 推算年化。方案B: 回测代码补充计算 |
| `sharpe_ratio` 不在 backtest_results | 方案A: 在 GUI 中从 `daily_return_mean/std` 推算。方案B: 回测代码补充计算 |

### P1 — 短期补充

| 问题 | 方案 |
|------|------|
| `performance_metrics` 表生产者缺失 | 确认 Analysis 模块是否负责写入，若否则需新增写入逻辑 |
| 回测指标未消费 | 丰富 Analysis 页面，展示 cost_bps, drawdown_days 等 |

### P2 — 后续澄清

| 问题 | 方案 |
|------|------|
| Trading 页面数据来源 | 明确是实盘/模拟盘还是回测 |
| daily_report 表来源 | 明确生产者并补齐写入逻辑 |
| backtest_trade_records vs trade_records | 明确两个表的关系和使用场景 |
