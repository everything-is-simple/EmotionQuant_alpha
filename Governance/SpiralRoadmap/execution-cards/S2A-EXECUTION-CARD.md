# S2a 执行卡（v0.2）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S2a（IRS + PAS + Validation）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，IRS/PAS/Validation 三模块按核心设计落地并可联动执行。
- 证据锚点：`src/algorithms/irs/pipeline.py`、`src/algorithms/pas/pipeline.py`、`src/algorithms/validation/pipeline.py`、`tests/unit/algorithms/irs/test_irs_contract.py`、`tests/unit/algorithms/pas/test_pas_contract.py`、`tests/unit/integration/test_validation_gate_contract.py`、`tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py`。
- 关键确认：Validation 执行字段与 `contract_version=nc-v1` 约束已稳定输出。

---

## 1. 目标

- 打通 `IRS + PAS + Validation` 最小闭环。
- 产出并落库 `irs_industry_daily`、`stock_pas_daily`、`validation_gate_decision`。
- 固化 `contract_version = "nc-v1"` 与 FAIL 处方语义。
- Validation 执行语义字段必须可追溯：`selected_weight_plan/fallback_plan/position_cap_ratio/tradability_pass_ratio/impact_cost_bps/candidate_exec_pass`。

---

## 2. run

```bash
eq recommend --date {trade_date} --mode mss_irs_pas --with-validation
```

---

## 3. test

```bash
pytest tests/unit/algorithms/irs/test_irs_contract.py -q
pytest tests/unit/algorithms/pas/test_pas_contract.py -q
pytest tests/unit/integration/test_validation_gate_contract.py -q
pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s2a/{trade_date}/irs_industry_daily_sample.parquet`
- `artifacts/spiral-s2a/{trade_date}/stock_pas_daily_sample.parquet`
- `artifacts/spiral-s2a/{trade_date}/validation_gate_decision_sample.parquet`
- `artifacts/spiral-s2a/{trade_date}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2a/review.md`
- 必填结论：
  - 三张输出表当日是否都 `> 0`
  - `validation_gate_decision.contract_version` 是否为 `nc-v1`
  - `selected_weight_plan/fallback_plan/position_cap_ratio/tradability_pass_ratio/impact_cost_bps/candidate_exec_pass` 是否齐全
  - FAIL 场景是否包含 `validation_prescription`

---

## 6. sync

- `Governance/specs/spiral-s2a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若任一输出缺失或契约不兼容：状态置 `blocked`，仅修复 S2a，不推进 S2b。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2a 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- Validation 设计：`docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md`




