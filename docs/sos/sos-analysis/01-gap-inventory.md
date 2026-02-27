# 01 — 差异清单（Analysis 篇）

**对比范围**:
- 设计文档：`docs/design/core-infrastructure/analysis/` 下 4 个文件
- 代码：`src/analysis/pipeline.py`, `src/analysis/benchmark_comparison.py`, `src/backtest/pipeline.py`

**标记规则**: 🔴 根本性偏离（功能缺失/逻辑错误） | 🟡 次要偏离（可延后/低风险）

---

## GAP-A01 🔴 绩效指标计算完全缺失 — 全部硬编码 0.0

**设计**: analysis-algorithm.md §2 + §7 (`compute_performance_metrics`)
- 从 equity_curve 逐步计算：daily_returns → total_return → annual_return → max_drawdown → volatility → sharpe_ratio → sortino_ratio → calmar_ratio
- 从 trades 计算：win_rate → profit_factor → avg_holding_days
- 完整的异常处理口径（std=0→Sharpe置0、无交易→全部置0 等）

**代码**: `src/analysis/pipeline.py:325-343`
- ab_benchmark 路径直接从 `backtest_results` 表读取 total_return/max_drawdown/win_rate/total_trades
- **annual_return = 0.0**（硬编码）
- **volatility = 0.0**（硬编码）
- **sharpe_ratio = 0.0**（硬编码）
- **sortino_ratio = 0.0**（硬编码）
- **calmar_ratio = 0.0**（硬编码）
- **profit_factor = 0.0**（硬编码）
- **avg_holding_days = 0.0**（硬编码）

**根因**: Backtest 未将 equity_curve 持久化到 DuckDB（仅在内存中用于 max_drawdown 计算），Analysis 层无法获取净值序列做独立计算。

---

## GAP-A02 🔴 CP-08 最小可运行闭环未落地

**设计**: analysis-algorithm.md §1.1 (`run_minimal`)
- 定义了完整的最小闭环：`compute_metrics → attribute_signals → generate_daily_report → persist/export`
- 返回 `AnalysisRunResult(state, saved_tables, exported_files)`

**代码**: `src/analysis/pipeline.py:158-689` (`run_analysis`)
- 实际实现的是 3 个独立子任务（ab_benchmark / deviation / attribution），并非设计中的 4 步串行流程
- 缺失 `generate_daily_report` 步骤
- 缺失日报持久化与文件导出
- 没有 `compute_metrics` 从 equity_curve 独立计算绩效的逻辑

**差异性质**: 代码实现了 S3b 阶段性目标（A/B对比 + 偏差 + 归因），但与设计中的「最小闭环」定义不一致。设计的闭环是端到端的（绩效→归因→日报→落库→导出），代码是面向子任务的。

---

## GAP-A03 🔴 日报生成功能完全缺失

**设计**: analysis-algorithm.md §6 (`generate_daily_report` + `render_report`)
- 日报包含：市场概况（MSS温度/周期/趋势）、行业轮动（Top5/轮入轮出）、信号统计（信号数/成交数/拒绝数）、绩效摘要、Top推荐列表、风险摘要
- Markdown 模板渲染系统
- 落库到 `daily_report` 表

**代码**: 完全不存在
- 没有 `generate_daily_report()` 函数
- 没有读取 `mss_panorama` / `irs_industry_daily` / `stock_pas_daily` 的逻辑
- 没有 `daily_report` 表的创建和写入
- 没有 Markdown 模板系统

---

## GAP-A04 🔴 风险分析功能完全缺失

**设计**: analysis-algorithm.md §5
- §5.1 风险等级分布：基于 neutrality 的三级分布（low/medium/high）+ 变化率 + 拐点检测 + risk_regime
- §5.2 行业集中度风险：HHI 计算 + max_concentration + top_industry

**代码**: 完全不存在
- 没有 `calculate_risk_distribution()` 函数
- 没有 `analyze_concentration()` 函数
- 没有读取 `positions` 表的逻辑

---

## GAP-A05 🔴 数据模型类全部缺失

**设计**: analysis-data-models.md §1-§5
- 定义了 14 个 dataclass：PerformanceMetrics, DailyReport, SignalAttribution, LiveBacktestDeviation, DailyReportData, MarketOverview, IndustryRotation, SignalStats, PerformanceSummary, RecommendationSummary, RiskSummary, TemperatureTrendData, IndustryRadarData, ScoreDistributionData
- 定义了 2 个枚举：MetricType, ReportType

**代码**: `src/analysis/pipeline.py`
- 仅有 1 个 dataclass：`AnalysisRunResult`（结果容器）
- 所有中间数据使用 `dict` 和 `pd.DataFrame`
- 没有任何设计文档中定义的业务模型

**差异性质**: 代码采用「无模型」的过程式风格，数据通过 dict 传递。设计定义了完整的类型体系。analysis-api.md §1 已标注「OOP 接口为未来扩展口径」，但基本业务模型的缺失会影响数据一致性校验。

---

## GAP-A06 🔴 偏差归因中信号偏差计算方式与设计不一致

**设计**: analysis-algorithm.md §4.3 (`decompose_live_backtest_deviation`)
- `signal_deviation = mean(live.forward_return_5d) - mean(bt.forward_return_5d)` — 用 5 日前瞻收益衡量选股差异

**代码**: `src/analysis/pipeline.py:410-412`
```python
signal_deviation = round((live_signal_mean - bt_signal_mean) / 100.0, 8)
```
- 使用 `final_score` 差值除以 100 作为信号偏差代理
- 这是一个 **评分差** 而非 **收益差**，语义完全不同

**差异性质**: 设计用「实际前瞻收益」衡量信号质量差异（结果导向），代码用「评分差」衡量（过程导向）。两者的物理单位和业务含义不同。

---

## GAP-A07 🔴 equity_curve 跨模块断裂（Backtest → Analysis）

**设计**: analysis-algorithm.md §2 + analysis-data-models.md §4.2
- Analysis 期望从 `backtest_results` 获取 `equity_curve` 字段
- 绩效指标的所有计算都基于 equity_curve

**代码**: `src/backtest/pipeline.py:1017,1492`
- Backtest 在内存中维护 `equity_curve: list[float]`
- 用于计算 max_drawdown 和 daily_return_distribution
- **但未将 equity_curve 写入 backtest_results 表或任何持久化存储**
- `backtest_results` 表仅存储汇总指标（total_return, max_drawdown, win_rate 等）

**影响**: Analysis 层即使实现了完整的绩效计算逻辑，也无法获取原始 equity_curve 数据。这是一个阻塞性的跨模块缺口。

---

## GAP-A08 🔴 回测交易记录缺少费用明细字段

**设计**: analysis-data-models.md §4.2
- `trade_records` / `backtest_trade_records` 应含：`commission`, `slippage`, `impact_cost_bps`

**代码**: `src/backtest/pipeline.py:109-133` (BACKTEST_TRADE_COLUMNS)
- backtest_trade_records 列为：backtest_id, trade_date, signal_date, execute_date, stock_code, direction, filled_price, shares, amount, pnl, pnl_pct, recommendation, final_score, risk_reward_ratio, integration_mode, weight_plan_id, status, reject_reason, t1_restriction_hit, limit_guard_result, session_guard_result, contract_version, created_at
- **不含** commission, slippage, impact_cost_bps, stamp_tax, transfer_fee 逐笔字段
- 费用在回测循环内存中计算，最终只汇总到 `backtest_results` 的 `commission_total/stamp_tax_total/impact_cost_total`

**影响**:
1. Analysis 偏差归因中 `bt_cost_rate` 被硬编码为 0.0（pipeline.py:417），因为无法从 backtest_trade_records 获取逐笔费用
2. 无法做逐笔费用归因分析

---

## GAP-A09 🔴 Dashboard 快照输出缺失

**设计**: analysis-algorithm.md §6.3 (`build_dashboard_snapshot`)
- 产出 `analysis_dashboard_snapshot` JSON，包含：summary（绩效摘要）、attribution（归因方法与结果）、risk（高风险变化率与拐点）、deviation（总偏差与主导项）
- 供 GUI 与治理看板复用

**代码**: 完全不存在
- 没有 `build_dashboard_snapshot()` 函数
- 没有 JSON 快照输出

---

## GAP-A10 🔴 CSV 导出功能缺失

**设计**: analysis-algorithm.md §1.1
- `export_metrics_csv(metrics, "performance_metrics")` → CSV 文件
- `export_signal_attribution_csv(attribution, "signal_attribution")` → CSV 文件
- analysis-information-flow.md §5.2 输出关系图中明确标注 CSV Exports

**代码**: 仅有 JSON 和 Markdown 导出
- attribution_summary → JSON
- ab_benchmark_report / deviation_report / gate_report → Markdown
- **无 CSV 导出**

---

## GAP-A11 🔴 L3 算法输出表的直读完全缺失

**设计**: analysis-information-flow.md §2 + §5.1
- 日报生成流程需要直接读取：`mss_panorama`（温度/周期/趋势）、`irs_industry_daily`（行业评分/轮动）、`stock_pas_daily`（个股评分）

**代码**: `src/analysis/pipeline.py`
- 仅读取：`backtest_results`、`trade_records`、`backtest_trade_records`、`integrated_recommendation`
- **不读取** mss_panorama / irs_industry_daily / stock_pas_daily

**根因**: 日报生成功能未实现（GAP-A03），因此不需要这些输入。但设计中这些是 Analysis 层的核心输入依赖。

---

## GAP-A12 🔴 持仓天数字段缺失（hold_days）

**设计**: analysis-algorithm.md §2.4
- `avg_holding_days = mean([t.hold_days for t in trades])` — 每笔交易需有 `hold_days` 字段

**代码**: `src/backtest/pipeline.py` (BACKTEST_TRADE_COLUMNS)
- backtest_trade_records 不含 `hold_days` 字段
- 买卖配对后的持仓天数未计算也未持久化
- Analysis 中 avg_holding_days 硬编码为 0.0

---

## GAP-A13 🟡 API 签名差异（多出 benchmark_mode 参数）

**设计**: analysis-api.md §1.1
- `run_analysis(*, config, start_date, end_date, trade_date, run_ab_benchmark, deviation_mode, run_attribution_summary)` — 7 个参数

**代码**: `src/analysis/pipeline.py:158-168`
- `run_analysis(*, config, start_date, end_date, trade_date, run_ab_benchmark, benchmark_mode, deviation_mode, run_attribution_summary)` — 8 个参数
- 多出 `benchmark_mode` 参数，用于控制是否运行完整基准对比（benchmark_comparison.py）

**影响**: 低。这是实现层的增强，不破坏设计口径。但设计文档应同步更新。

---

## GAP-A14 🟡 产物路径差异

**设计**: analysis-algorithm.md §1
- 报告落盘 `.reports/analysis/`，文件名使用 `{YYYYMMDD_HHMMSS}` 时间戳

**代码**: `src/analysis/pipeline.py:201`
- 产物输出到 `artifacts/spiral-s3b/{anchor_date}/`
- 文件名不使用时间戳（固定名如 `ab_benchmark_report.md`）

**注**: analysis-api.md §3 已更新为 `artifacts/spiral-s3b/{anchor_date}/`，与代码一致。但 analysis-algorithm.md §1 仍为旧路径。算法文档与 API 文档自相矛盾。

---

## GAP-A15 🟡 回测偏差中 bt_cost_rate 硬编码为 0

**设计**: analysis-algorithm.md §4.3
- `bt_cost_rate = mean(bt.commission_rate + bt.slippage_rate + bt.impact_cost_rate)` — 从回测成交记录计算

**代码**: `src/analysis/pipeline.py:417`
```python
bt_cost_rate = 0.0
```
- 直接硬编码为 0.0

**根因**: backtest_trade_records 不含逐笔费用字段（GAP-A08 的下游影响）。

---

## GAP-A16 🟡 Markdown 渲染简化

**设计**: analysis-algorithm.md §6.2
- 模板系统：`load_template(template)` → `template.replace("{{variable}}", value)` → 完整渲染

**代码**: `src/analysis/pipeline.py`
- 直接拼接字符串列表 → `_write_markdown(path, lines)`
- 无模板加载机制

**影响**: 低。当前功能可满足需求，模板系统是可选增强。

---

## 汇总对照表

| GAP ID | 严重度 | 设计文档 | 代码位置 | 差异类型 |
|--------|--------|----------|----------|----------|
| A01 | 🔴 | algorithm §2,§7 | pipeline.py:325-343 | 功能硬编码占位 |
| A02 | 🔴 | algorithm §1.1 | pipeline.py:158-689 | 流程架构不一致 |
| A03 | 🔴 | algorithm §6 | 完全缺失 | 功能缺失 |
| A04 | 🔴 | algorithm §5 | 完全缺失 | 功能缺失 |
| A05 | 🔴 | data-models §1-§5 | 完全缺失 | 模型缺失 |
| A06 | 🔴 | algorithm §4.3 | pipeline.py:410-412 | 计算逻辑偏差 |
| A07 | 🔴 | data-models §4.2 | backtest/pipeline.py | 跨模块数据断裂 |
| A08 | 🔴 | data-models §4.2 | backtest/pipeline.py:109-133 | 字段缺失 |
| A09 | 🔴 | algorithm §6.3 | 完全缺失 | 功能缺失 |
| A10 | 🔴 | algorithm §1.1 | 完全缺失 | 导出缺失 |
| A11 | 🔴 | info-flow §2,§5.1 | pipeline.py | 输入依赖缺失 |
| A12 | 🔴 | algorithm §2.4 | backtest/pipeline.py | 字段缺失 |
| A13 | 🟡 | api §1.1 | pipeline.py:158-168 | 参数多出 |
| A14 | 🟡 | algorithm §1 vs api §3 | pipeline.py:201 | 路径不一致 |
| A15 | 🟡 | algorithm §4.3 | pipeline.py:417 | 硬编码占位 |
| A16 | 🟡 | algorithm §6.2 | pipeline.py | 简化实现 |
