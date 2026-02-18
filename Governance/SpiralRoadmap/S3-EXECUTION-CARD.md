# S3 执行卡（v0.2）

**状态**: Active  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3（回测闭环）

---

## 1. 目标

- 完成 `S3` 回测闭环：Qlib 主线 + 本地口径可对照。
- 固化 `integrated_recommendation` 到回测执行的可审计消费链路。
- 产出可复核的回测结果与 A/B/C 指标摘要，作为 S4 纸上交易参数来源。

---

## 2. run

```bash
eq backtest --engine {engine} --start {start} --end {end}
```

---

## 3. test

```bash
pytest tests/unit/backtest/test_backtest_contract.py -q
pytest tests/unit/backtest/test_validation_integration_bridge.py -q
pytest tests/unit/backtest/test_backtest_reproducibility.py -q
pytest tests/unit/backtest/test_backtest_core_algorithm_coverage_gate.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3/{trade_date}/backtest_results.parquet`
- `artifacts/spiral-s3/{trade_date}/backtest_trade_records.parquet`
- `artifacts/spiral-s3/{trade_date}/ab_metric_summary.md`
- `artifacts/spiral-s3/{trade_date}/consumption.md`
- `artifacts/spiral-s3/{trade_date}/gate_report.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3/review.md`
- 必填结论：
  - `validation_weight_plan` 桥接链路是否可追溯
  - A/B/C 对照是否形成稳定基线结论
  - 回测结果是否可稳定复现（同窗口重复执行差异在可接受范围内）

---

## 6. sync

- `Governance/specs/spiral-s3/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 `gate = FAIL` 或桥接链路不可审计：状态置 `blocked`，进入 `S3r` 修复子圈，不推进 S4。
- 若契约/治理检查失败：先修复并补齐回归证据，再重跑 S3 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
- 核心算法设计基线：`docs/design/core-algorithms/`

---

## 9. 本轮进度（2026-02-18）

- 已进入 `in_progress`，并完成多交易日回放与板块化涨跌停阈值（10%/20%/5%）落地。
- 已补齐“完整核心算法+本地库”回测门禁：S3 对 `mss_score/irs_score/pas_score` 三因子完整性与 `mss_panorama/irs_industry_daily/stock_pas_daily` 窗口覆盖进行硬校验，并在 `consumption.md`/`gate_report.md` 输出 DuckDB 覆盖证据。
- 下一步：继续补齐更细撮合规则与可回放证据，推进 S3 收口。
