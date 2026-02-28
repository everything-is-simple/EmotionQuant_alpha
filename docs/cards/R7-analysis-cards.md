# R7 Analysis 重建 — 执行卡

**阶段目标**：从"硬编码 0"到真实绩效计算 + 信号归因 + 日报。
**总工期**：6-8 天
**前置条件**：R5 完成（依赖 equity_curve + 逐笔费用持久化）
**SOS 覆盖**：docs/sos/analysis 全部 16 项

---

## CARD-R7.1: 绩效指标计算（从 equity_curve）

**工作量**：1.5 天
**优先级**：P0（全部硬编码 0.0）
**SOS 映射**：GAP-A01, GAP-A07, GAP-A08, GAP-A12, GAP-A15

### 交付物

- [ ] 从 equity_curve 计算完整绩效指标
  - 读取 R5 持久化的 equity_curve 表
  - daily_returns = `(equity_t - equity_{t-1}) / equity_{t-1}`
  - total_return = `(equity_end - equity_start) / equity_start`
  - annual_return = `(1 + total_return) ^ (252/days) - 1`
  - max_drawdown = 峰谷追踪（复用 R5 逻辑）
  - volatility = `std(daily_returns) * sqrt(252)`
  - sharpe_ratio = `(annual_return - rf) / volatility`（std=0 → Sharpe=0）
  - sortino_ratio = `(annual_return - rf) / downside_deviation`
  - calmar_ratio = `annual_return / abs(max_drawdown)`（drawdown=0 → Calmar=0）
- [ ] 从 trade_records 计算交易指标
  - win_rate = `count(pnl > 0) / total_trades`（无交易 → 0）
  - profit_factor = `sum(wins) / abs(sum(losses))`（无亏损 → inf → cap 99.99）
  - avg_holding_days = `mean(hold_days)`（使用 R5 持久化的 hold_days 字段）
- [ ] bt_cost_rate 真实计算 (A15)
  - 从 backtest_trade_records 读取逐笔 commission + slippage + impact_cost
  - `bt_cost_rate = mean(total_fee / amount)`
  - 删除硬编码 `bt_cost_rate = 0.0`

### 验收标准

1. 7 项绩效指标全部非零（有交易数据时）
2. sharpe/sortino/calmar 与手算一致
3. avg_holding_days 反映实际持仓天数（非 0.0）
4. bt_cost_rate 反映实际费用率（非 0.0）

### 技术要点

- equity_curve 可能跨越非交易日，需按 trade_cal 过滤
- 异常处理：std=0 → Sharpe=0, no trades → 全部置 0, no losses → profit_factor cap

---

## CARD-R7.2: 信号归因 + 偏差分析

**工作量**：1.5 天
**优先级**：P0
**SOS 映射**：GAP-A02, GAP-A06

### 交付物

- [ ] 信号归因修正 (A06)
  - **正确**：`signal_deviation = mean(live.forward_return_5d) - mean(bt.forward_return_5d)`
  - 删除 `(live_signal_mean - bt_signal_mean) / 100.0`（评分差代理）
  - forward_return_5d 从 raw_daily 读取 T+5 收益率
  - 按 stock_code 配对 live 和 backtest 信号
- [ ] 偏差分解
  - signal_deviation：选股差异（forward_return 差值）
  - execution_deviation：执行差异（fill_rate / slippage 差值）
  - cost_deviation：费用差异（live_cost_rate - bt_cost_rate）
  - timing_deviation：择时差异（残差项）
- [ ] CP-08 最小闭环对齐 (A02)
  - 实现 `run_minimal()` 流程：
    1. `compute_metrics()` — 从 equity_curve
    2. `attribute_signals()` — 信号归因
    3. `generate_daily_report()` — 日报（CARD-R7.3）
    4. `persist_and_export()` — 落库 + 导出
  - 返回 `AnalysisRunResult(state, saved_tables, exported_files)`

### 验收标准

1. signal_deviation 使用 forward_return_5d（非 final_score 差值）
2. 四项偏差之和 ≈ total_deviation
3. run_minimal() 四步串行可完整执行

---

## CARD-R7.3: 日报生成 + 风险分析

**工作量**：1.5 天
**优先级**：P0（功能完全缺失）
**SOS 映射**：GAP-A03, GAP-A04, GAP-A09, GAP-A10, GAP-A11

### 交付物

- [ ] 日报生成 (A03)
  - 读取 L3 算法输出：mss_panorama（温度/周期/趋势）、irs_industry_daily（行业评分/轮动）、stock_pas_daily（个股评分）
  - 日报内容：
    - 市场概况：MSS 温度 + 周期状态 + 趋势方向
    - 行业轮动：Top5 行业 + 轮入/轮出
    - 信号统计：信号数 / 成交数 / 拒绝数
    - 绩效摘要：今日收益 / 累计收益 / 最大回撤
    - Top 推荐列表：Top10 推荐标的 + 评分 + 等级
    - 风险摘要：neutrality 分布 + 行业集中度
  - Markdown 模板渲染：`load_template() → replace("{{var}}", value)`
  - 落库到 `daily_report` 表
- [ ] 风险分析 (A04)
  - neutrality 三级分布：low(≥0.7) / medium(0.4-0.7) / high(<0.4)
  - 变化率 + 拐点检测
  - risk_regime 判定
  - HHI 行业集中度：`sum((weight_i)^2)`
  - max_concentration + top_industry
- [ ] Dashboard 快照 JSON (A09)
  - 输出 `analysis_dashboard_snapshot` JSON：summary + attribution + risk + deviation
  - 供 GUI 和 Governance 看板消费
- [ ] CSV 导出 (A10)
  - `export_metrics_csv(metrics, "performance_metrics")` → CSV
  - `export_signal_attribution_csv(attribution, "signal_attribution")` → CSV
- [ ] L3 数据源接入 (A11)
  - 新增 SQL 读取 mss_panorama / irs_industry_daily / stock_pas_daily

### 验收标准

1. 日报 Markdown 包含 6 个板块
2. daily_report 表有数据
3. Dashboard JSON 可被 GUI 解析
4. CSV 文件可被 Excel 打开
5. HHI 计算正确（等权 10 行业 = 0.10）

### 技术要点

- Markdown 模板放在 `src/analysis/templates/` 目录
- Dashboard JSON schema 需与 GUI(R8) 预先对齐
- HHI = Σ(w_i²)，完全集中=1.0，完全分散=1/N

---

## CARD-R7.4: 数据模型 + OOP 层

**工作量**：1 天
**优先级**：P1
**SOS 映射**：GAP-A05, GAP-A13, GAP-A14, GAP-A16

### 交付物

- [ ] 14 个 dataclass 实现 (A05)
  - PerformanceMetrics, DailyReport, SignalAttribution, LiveBacktestDeviation
  - DailyReportData, MarketOverview, IndustryRotation, SignalStats
  - PerformanceSummary, RecommendationSummary, RiskSummary
  - TemperatureTrendData, IndustryRadarData, ScoreDistributionData
- [ ] 2 个枚举：MetricType, ReportType
- [ ] `src/analysis/service.py` — AnalysisService
  - 构造函数注入 config, repository
  - 方法：`run_analysis()`, `compute_metrics()`, `attribute_signals()`, `generate_report()`, `export()`
- [ ] `src/analysis/engine.py` — AnalysisEngine
  - 纯计算：绩效指标 + 归因 + 风险分析
- [ ] `src/analysis/repository.py` — AnalysisRepository
  - 读写 performance_metrics, daily_report, signal_attribution 表
- [ ] `src/analysis/reports/daily_report.py` — 日报生成器
- [ ] 产物路径统一 (A14)
  - 对齐为 `artifacts/analysis/{trade_date}/`
  - 更新 analysis-algorithm.md 路径描述

### 验收标准

1. 14 个 dataclass 全部可实例化
2. AnalysisService.run_analysis() 串行执行完整流程
3. pipeline.py 仅做编排

---

## CARD-R7.5: 指标验证 + 契约测试

**工作量**：1 天
**优先级**：P1（质量闭环）
**前置依赖**：CARD-R7.1~R7.4

### 交付物

- [ ] 对 R5 回测结果运行 Analysis
  - 检查绩效指标全部非零
  - 检查 sharpe/sortino/calmar 与 R5 输出一致
  - 检查信号归因：四项偏差之和 ≈ total_deviation
- [ ] 日报内容验证
  - 检查 MSS 温度与 mss_panorama 一致
  - 检查 Top5 行业与 irs_industry_daily 一致
  - 检查信号数与 integrated_recommendation 行数一致
- [ ] 契约测试
  - performance_metrics 表字段完整性
  - daily_report 表非空
  - Dashboard JSON schema 验证
- [ ] 验证报告
  - 输出：`artifacts/r7-validation-report.md`
  - 覆盖绩效指标 + 归因 + 日报 + 风险

### 验收标准

1. 所有绩效指标非零且与手算一致
2. 日报 6 个板块内容正确
3. Dashboard JSON 可解析
4. 端到端：Backtest(R5) → Analysis(R7) 无异常

---

## R7 阶段验收总览

完成以上 5 张卡后，需满足：

1. **绩效非零**：7 项指标全部真实计算（非硬编码 0）
2. **信号归因**：使用 forward_return_5d 而非评分差值
3. **日报完整**：6 板块 Markdown + 落库 + CSV 导出
4. **风险分析**：neutrality 分布 + HHI 行业集中度
5. **Dashboard**：JSON 快照供 GUI 消费
6. **OOP 架构**：AnalysisService + AnalysisEngine 可用
7. **质量闭环**：指标验证 + 日报验证 + 契约测试

**下一步**：进入 R8 GUI 重建（4 层架构完全重建）。
