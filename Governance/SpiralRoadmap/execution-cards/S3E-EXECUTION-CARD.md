# S3e 执行卡（v0.3）

**状态**: Implemented（工程完成） + Code-Revalidated（通过）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-25  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3e（Validation 生产校准闭环）

---

## 0. 现状对齐（2026-02-21）

- CLI 阻断已解除：`eq validation` 子命令（`--threshold-mode/--wfa/--export-run-manifest`）已落地。
- 对应合同测试已补齐：`test_factor_future_returns_alignment_contract.py`、`test_weight_validation_dual_window_contract.py`、`test_validation_oos_metrics_contract.py`。
- 核心算法修复已落地：`decay_5d` 代理改为与 `|IC|` 单调正向关系，避免强信号被反向判定 FAIL（`test_decay_proxy_contract.py`）。
- 当前进入执行态，待窗口级实证证据收口后再评估 Completed。

## 代码级重验（2026-02-27）

- [x] run 冒烟通过（见统一审计汇总）
- [x] test 契约通过（见统一审计汇总）
- [x] 功能检查正常（见统一审计汇总）
- 结论：`通过`
- 证据：`artifacts/spiral-allcards/revalidation/20260227_125427/execution_cards_code_audit_summary.md`

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
- `artifacts/spiral-s3e/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `validation_gate_decision/validation_weight_plan` 与 `validation-data-models.md` 一致性）
- `artifacts/spiral-s3e/{trade_date}/neutral_regime_audit_report.md`（条件产出：连续 ≥2 窗口 FAIL 且 neutral_regime 软化通过时必须产出）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3e/review.md`
- 必填结论：
  - future_returns 对齐与防未来函数约束是否成立
  - 双窗口投票与 OOS/成本/可成交性指标是否齐备
  - `selected_weight_plan` 是否可追溯到投票证据
  - `factor_gate_raw` 健康度是否检查（FAIL 比例是否在可接受范围内）
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s3e/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 Validation 生产口径门禁未通过：状态置 `blocked`，留在 S3e 修复，不推进 S4b。
- 若定位到 MSS 口径不一致：回退 S3d 修复后重验。
- **factor_gate_raw=FAIL 升级策略**（3 路径）：
  1. 扩窗后 FAIL 比例仍 >50%：必须回到 S3d 重检 MSS adaptive 参数，不得直接进入 S4b。
  2. 连续 ≥2 窗口 FAIL 但 neutral_regime 软化通过：必须产出 `neutral_regime_audit_report.md`，说明软化合理性。
  3. FULL 口径要求 factor_gate_raw 不得 FAIL 但当前全 FAIL：S3e 锁定为 `WARN_PENDING_RESOLUTION`，螺旋2 不得宣称生产就绪。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 历史债务消化（审计插入 2026-02-26）

| 来源 | 描述 | 审计结论 |
|---|---|---|
| TD-S0-002 | Validation 生产级真实收益口径与统计校准 | 已完成：`src/algorithms/validation/calibration.py::calibrate_ic_baseline()` 与 `tests/unit/algorithms/validation/test_calibration_baseline_contract.py` 已覆盖，移出阻断项。 |
| TD-DA-011 | Integration 双模式语义冲突对 Validation 消费的传导风险 | 仍待处理：S3e 重验时需校验 dual_verify/complementary 语义一致性，避免 Gate 解释链漂移。 |


