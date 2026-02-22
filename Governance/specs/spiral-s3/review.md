# S3 Review（6A A4/A5）

**Spiral**: S3  
**状态**: completed  
**复盘日期**: 2026-02-22

## 1. A3 交付结果

1. 新增 `eq backtest` 命令入口（`src/pipeline/main.py`）。
2. 新增回测最小实现（`src/backtest/pipeline.py`）：
   - S3a `fetch_progress` 消费门禁
   - Quality Gate 消费门禁
   - Validation-Integration 桥接门禁
   - 多交易日回放（交易日历驱动）与 T+1 执行映射
   - 涨停买入拒绝、跌停卖出阻断、费用与权益曲线追踪
   - 板块化涨跌停阈值：主板 10% / 创业板与科创板 20% / ST 5%
   - 回测最小产物输出（results/trade_records/A-B-C 摘要）
3. 新增 S3 目标测试 5 条（含板块化阈值回归）+ CLI 回归 1 条。

## 2. A4 验证记录

### run（跨窗口）

- 通过:
  - `eq backtest --engine qlib --start 20260102 --end 20260213`
  - `eq backtest --engine qlib --start 20260119 --end 20260213`
  - `eq backtest --engine qlib --start 20260210 --end 20260213`
  - `eq backtest --engine qlib --start 20260212 --end 20260213`
- 结论:
  - 四窗均 `quality_status=WARN`、`go_nogo=GO`、`bridge_check_status=PASS`
  - `fetch_progress` 缩窗场景在本地 L1 覆盖下已降级 WARN，不再误阻断

### test

- `python -m pytest tests/unit/backtest/test_backtest_contract.py tests/unit/backtest/test_validation_integration_bridge.py tests/unit/backtest/test_backtest_reproducibility.py tests/unit/backtest/test_backtest_t1_limit_rules.py tests/unit/backtest/test_backtest_board_limit_thresholds.py -q`
- 结果: PASS（7 passed）

### contracts/governance

- `python -m scripts.quality.local_quality_check --contracts --governance`
- 结果: PASS

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s3/requirements.md`
- artifact:
  - `artifacts/spiral-s3/{trade_date}/backtest_results.parquet`
  - `artifacts/spiral-s3/{trade_date}/backtest_trade_records.parquet`
  - `artifacts/spiral-s3/{trade_date}/ab_metric_summary.md`
  - `artifacts/spiral-s3/{trade_date}/performance_metrics_report.md`
  - `artifacts/spiral-s3/{trade_date}/consumption.md`
  - `artifacts/spiral-s3/{trade_date}/gate_report.md`
  - `artifacts/spiral-s3/20260213/s3_cross_window_summary.json`
  - `artifacts/spiral-s3/20260213/s3_cross_window_summary.md`

## 4. 偏差与风险

1. 无 `P0` 残留阻断；当前主要风险为短窗口无交易样本时只输出 `WARN`，该语义已被契约测试锁定。
2. DuckDB 文件锁对并行命令敏感，实际执行需保持串行（已固化为执行约束）。

## 5. 消费记录

- 上游消费: S3 消费 S3a 采集进度产物（`fetch_progress`）。
- 下游消费: S4 将消费 S3 回测结果与参数结论。
- 当前结论: 消费链路已打通且通过跨窗口复核，满足 S3 收口条件。

## 6. 跨文档联动

- 本次未涉及破坏性命名契约变更；暂不触发 CP 文档结构性更新。
