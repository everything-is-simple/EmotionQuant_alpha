# S3e 执行卡（v0.2）

**状态**: Active（2026-02-21 已解除 CLI 阻断）  
**更新时间**: 2026-02-21  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3e（Validation 生产校准闭环）

---

## 0. 现状对齐（2026-02-21）

- CLI 阻断已解除：`eq validation` 子命令（`--threshold-mode/--wfa/--export-run-manifest`）已落地。
- 对应合同测试已补齐：`test_factor_future_returns_alignment_contract.py`、`test_weight_validation_dual_window_contract.py`、`test_validation_oos_metrics_contract.py`。
- 核心算法修复已落地：`decay_5d` 代理改为与 `|IC|` 单调正向关系，避免强信号被反向判定 FAIL（`test_decay_proxy_contract.py`）。
- 当前进入执行态，待窗口级实证证据收口后再评估 Completed。

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
