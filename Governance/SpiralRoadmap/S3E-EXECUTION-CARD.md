# S3e 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3e（Validation 生产校准闭环）

---

## 0. 现状对齐（2026-02-21）

- 本卡为计划圈，尚未进入执行态。
- 进入执行前必须补齐独立入口：`eq validation` 子命令（含 `--threshold-mode/--wfa/--export-run-manifest`）。
- 在 `eq validation` 与对应合同测试落地前，S3e 不得标记 `in_progress/completed`。

## 1. 目标

- 因子验证切换到 `factor_series × future_returns` 生产口径。
- 权重验证落地双窗口 Walk-Forward 投票与 OOS 指标集。
- 固化 `selected_weight_plan` 可审计选择链，作为 S4b 前置输入。

---

## 2. run

```bash
eq validation --trade-date {trade_date} --threshold-mode regime --wfa dual-window
eq validation --trade-date {trade_date} --export-run-manifest
```

---

## 3. test

```bash
pytest tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py -q
pytest tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py -q
pytest tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3e/{trade_date}/validation_factor_report_sample.parquet`
- `artifacts/spiral-s3e/{trade_date}/validation_weight_report_sample.parquet`
- `artifacts/spiral-s3e/{trade_date}/validation_run_manifest_sample.json`
- `artifacts/spiral-s3e/{trade_date}/validation_oos_calibration_report.md`
- `artifacts/spiral-s3e/{trade_date}/consumption.md`
- `artifacts/spiral-s3e/{trade_date}/gate_report.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3e/review.md`
- 必填结论：
  - future_returns 对齐与防未来函数约束是否成立
  - 双窗口投票与 OOS/成本/可成交性指标是否齐备
  - `selected_weight_plan` 是否可追溯到投票证据

---

## 6. sync

- `Governance/specs/spiral-s3e/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 Validation 生产口径门禁未通过：状态置 `blocked`，留在 S3e 修复，不推进 S4b。
- 若定位到 MSS 口径不一致：回退 S3d 修复后重验。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
