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
- `artifacts/spiral-s2a/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `irs_industry_daily/stock_pas_daily/validation_gate_decision` 与对应 `*-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2a/review.md`
- 必填结论：
  - 三张输出表当日是否都 `> 0`
  - `validation_gate_decision.contract_version` 是否为 `nc-v1`
  - `selected_weight_plan/fallback_plan/position_cap_ratio/tradability_pass_ratio/impact_cost_bps/candidate_exec_pass` 是否齐全
  - FAIL 场景是否包含 `validation_prescription`
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

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

---

## 历史债务状态（2026-02-27 清零同步）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

