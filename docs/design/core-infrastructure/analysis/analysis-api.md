# Analysis API 接口

**版本**: v4.0.0
**最后更新**: 2026-02-26
**状态**: Pipeline 模式已落地（Python 模块/CLI）

---

## 实现状态（仓库现状）

- **现行架构**：过程式 Pipeline + DuckDB 直写。主入口 `run_analysis()`（`src/analysis/pipeline.py:145`），CLI 由 `eq analysis` 触发。
- 已实现三项子任务：A/B 基准对比 (`--ab-benchmark`)、实盘-回测偏差归因 (`--deviation live-backtest`)、归因汇总 (`--attribution-summary`)。
- Analysis 层产出 L4 分析指标与报告，不替代 L3 算法；仅消费 L3 算法输出与回测/实盘结果。
- 设计中的 OOP 结构（AnalysisEngine/PerformanceAnalyzer/SignalAttributor/RiskReporter/ReportWriter/Visualizer）为未来扩展口径，详见附录 A。
- 架构决策 ARCH-DECISION-001：选项 B（文档对齐代码）。

**外部库边界**：不得以 quantstats/empyrical 等第三方库替代 Analysis 模块，可作为内部计算工具使用（不改变输出口径）。

**输入依赖**：`mss_panorama`、`irs_industry_daily`、`stock_pas_daily`、`integrated_recommendation`；`trade_records` / `backtest_trade_records`、`backtest_results`（含 equity_curve）、`positions`。

---

## 1. Pipeline 接口

### 1.1 Pipeline 编排入口

```python
def run_analysis(
    *,
    config: Config,
    start_date: str = "",
    end_date: str = "",
    trade_date: str = "",
    run_ab_benchmark: bool = False,
    deviation_mode: str = "",
    run_attribution_summary: bool = False,
) -> AnalysisRunResult:
    """
    Analysis Pipeline 入口（src/analysis/pipeline.py:145）

    职责：
    1. 至少选一项子任务（ab-benchmark / deviation / attribution-summary）
    2. A/B 基准对比：需 start_date + end_date，读取 backtest_results 计算绩效指标
    3. 偏差归因：需 trade_date + deviation_mode="live-backtest"，拆解信号/执行/费用偏差
    4. 归因汇总：需 trade_date，计算 MSS/IRS/PAS 贡献并持久化
    5. 持久化到 DuckDB (performance_metrics / live_backtest_deviation / signal_attribution)
    6. 产出 artifacts (ab_benchmark_report.md / live_backtest_deviation_report.md / attribution_summary.json / gate_report.md)

    Args:
        config: Config 实例
        start_date: A/B 基准开始日期（YYYYMMDD）
        end_date: A/B 基准结束日期（YYYYMMDD）
        trade_date: 偏差归因/归因汇总日期（YYYYMMDD）
        run_ab_benchmark: 是否执行 A/B 基准对比
        deviation_mode: 偏差模式（"" 或 "live-backtest"）
        run_attribution_summary: 是否执行归因汇总

    Returns:
        AnalysisRunResult（frozen dataclass）
    Raises:
        ValueError: 无子任务 / 参数缺失 / 不支持的 deviation_mode
    """
```

### 1.2 返回类型

```python
@dataclass(frozen=True)
class AnalysisRunResult:
    trade_date: str
    start_date: str
    end_date: str
    artifacts_dir: Path
    ab_benchmark_report_path: Path
    live_backtest_deviation_report_path: Path
    attribution_summary_path: Path
    consumption_path: Path
    gate_report_path: Path
    error_manifest_path: Path
    quality_status: str           # PASS / WARN / FAIL
    go_nogo: str                  # GO / NO_GO
    has_error: bool
```

### 1.3 DuckDB 持久化表

- `performance_metrics`：metric_date / total_return / annual_return / max_drawdown / volatility / sharpe_ratio / sortino_ratio / calmar_ratio / win_rate / profit_factor / total_trades / avg_holding_days / created_at
- `live_backtest_deviation`：trade_date / signal_deviation / execution_deviation / cost_deviation / total_deviation / dominant_component / created_at
- `signal_attribution`：trade_date / mss_attribution / irs_attribution / pas_attribution / sample_count / raw_sample_count / trimmed_sample_count / trim_ratio / attribution_method / created_at

---

## 2. 调用示例

```python
from src.config.config import Config
from src.analysis.pipeline import run_analysis

config = Config.from_env()

# A/B 基准对比
result = run_analysis(
    config=config,
    start_date="20260101",
    end_date="20260131",
    run_ab_benchmark=True,
)
print(result.quality_status)  # PASS / WARN / FAIL

# 实盘-回测偏差归因
result = run_analysis(
    config=config,
    trade_date="20260131",
    deviation_mode="live-backtest",
)

# 归因汇总
result = run_analysis(
    config=config,
    trade_date="20260131",
    run_attribution_summary=True,
)
```

---

## 3. 产物路径

所有产物输出到 `artifacts/spiral-s3b/{anchor_date}/`：

- `ab_benchmark_report.md` — A/B 基准对比报告
- `live_backtest_deviation_report.md` — 实盘-回测偏差归因报告
- `attribution_summary.json` — 归因汇总 JSON
- `gate_report.md` — 质量门禁报告
- `consumption.md` — 资源消耗记录
- `error_manifest.json` — 错误清单

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.0 | 2026-02-26 | ARCH-DECISION-001：接口定义改为反映实际 Pipeline 模式（`run_analysis`）；OOP 接口移入附录 A；更正实现状态 |
| v3.2.0 | 2026-02-14 | 闭环修订：新增 `AnalysisEngine.run_minimal`、偏差归因、风险趋势、看板快照 |
| v3.1.5 | 2026-02-12 | 路径整理 |
| v3.1.0 | 2026-02-04 | 对齐边界/依赖与报告落盘规范 |
| v3.0.0 | 2026-01-31 | 重构版 |

---

## 附录 A：OOP 接口（未来扩展口径）

以下 OOP 接口为规划口径，当前未落地。若未来需要拆分为独立模块，可参考以下设计：

- `AnalysisEngine`：最小闭环编排 (`run_minimal`)
- `PerformanceAnalyzer`：绩效指标计算 (compute_metrics / calculate_daily_returns / calculate_max_drawdown / calculate_risk_metrics / calculate_trade_stats)
- `SignalAttributor`：信号归因 (attribute_signals / attribute_period / calculate_hit_rate / calculate_rotation_hit_rate / decompose_live_backtest_deviation)
- `RiskReporter`：风险报告 (analyze_risk_distribution / analyze_concentration / analyze_drawdown_periods / analyze_risk_trend)
- `ReportWriter`：报告输出 (generate_daily_report / render_markdown / export_to_file / export_metrics_csv / export_dashboard_snapshot)
- `Visualizer`：可视化 (build_temperature_trend / build_industry_radar / build_score_distribution)

完整接口定义见 v3.2.0 历史版本。

---

**关联文档**：
- 核心算法：[analysis-algorithm.md](./analysis-algorithm.md)
- 数据模型：[analysis-data-models.md](./analysis-data-models.md)
- 信息流：[analysis-information-flow.md](./analysis-information-flow.md)
- 架构决策：[ARCH-DECISION-001](../../../Governance/record/ARCH-DECISION-001-pipeline-vs-oop.md)


