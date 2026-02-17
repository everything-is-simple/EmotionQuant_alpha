# S3 Review（6A A4/A5）

**Spiral**: S3  
**状态**: in_progress  
**复盘日期**: 2026-02-17（进行中）

## 1. A3 交付结果

1. 新增 `eq backtest` 命令入口（`src/pipeline/main.py`）。
2. 新增回测最小实现（`src/backtest/pipeline.py`）：
   - S3a `fetch_progress` 消费门禁
   - Quality Gate 消费门禁
   - Validation-Integration 桥接门禁
   - 多交易日回放（交易日历驱动）与 T+1 执行映射
   - 涨停买入拒绝、跌停卖出阻断、费用与权益曲线追踪
   - 回测最小产物输出（results/trade_records/A-B-C 摘要）
3. 新增 S3 目标测试 4 条 + CLI 回归 1 条。

## 2. A4 验证记录

### run

- 通过:
  - `eq backtest --engine qlib --start 20260218 --end 20260220`

### test

- `python -m pytest tests/unit/backtest/test_backtest_contract.py tests/unit/backtest/test_validation_integration_bridge.py tests/unit/backtest/test_backtest_reproducibility.py tests/unit/backtest/test_backtest_t1_limit_rules.py tests/unit/pipeline/test_cli_entrypoint.py::test_main_backtest_runs_with_s3a_consumption -q`
- 结果: PASS（5 passed）

### contracts/governance

- `python -m scripts.quality.local_quality_check --contracts --governance`
- 结果: PASS

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s3/requirements.md`
- artifact:
  - `artifacts/spiral-s3/{trade_date}/backtest_results.parquet`
  - `artifacts/spiral-s3/{trade_date}/backtest_trade_records.parquet`
  - `artifacts/spiral-s3/{trade_date}/ab_metric_summary.md`
  - `artifacts/spiral-s3/{trade_date}/consumption.md`
  - `artifacts/spiral-s3/{trade_date}/gate_report.md`

## 4. 偏差与风险

1. 多交易日回放与 T+1/涨跌停最小执行细节已落地，但板块化涨跌停阈值（10%/20%/5%）仍待补齐。
2. 更完整绩效指标与交易成本/滑点建模仍待补齐。

## 5. 消费记录

- 上游消费: S3 消费 S3a 采集进度产物（`fetch_progress`）。
- 下游消费: S4 将消费 S3 回测结果与参数结论。
- 当前结论: 消费链路已打通，满足“先消费再推进”约束。

## 6. 跨文档联动

- 本次未涉及破坏性命名契约变更；暂不触发 CP 文档结构性更新。
