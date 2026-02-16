# S2c 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-16  
**阶段**: 阶段A（S0-S2c）  
**微圈**: S2c（核心算法深化：权重桥接 + 语义收口）

---

## 1. 目标

- 完成核心算法链路深化收口：MSS/IRS/PAS/Validation/Integration 语义对齐。
- 把 `validation_weight_plan` 桥接升级为硬门禁，阻断无桥接放行。
- 形成“核心算法完成 DoD”所需关键证据。

---

## 2. run

```bash
eq recommend --date {trade_date} --mode integrated --with-validation-bridge
```

---

## 3. test

```bash
pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q
pytest tests/unit/integration/test_validation_weight_plan_bridge.py -q
pytest tests/unit/integration/test_algorithm_semantics_regression.py -q
```

---

## 4. artifact

- `artifacts/spiral-s2c/{trade_date}/validation_factor_report_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/validation_weight_report_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/validation_weight_plan_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/s2c_algorithm_closeout.md`
- `artifacts/spiral-s2c/{trade_date}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2c/review.md`
- 必填结论：
  - `selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id` 是否全链路一致
  - Gate=FAIL 是否阻断、Gate=PASS/WARN 是否按契约放行
  - `contract_version=nc-v1` 与 `risk_reward_ratio>=1.0` 执行边界是否一致

---

## 6. sync

- `Governance/specs/spiral-s2c/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若桥接链路缺失或不一致：状态置 `blocked`，不得推进 S3a/S3，必须进入 S2r。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2c 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
