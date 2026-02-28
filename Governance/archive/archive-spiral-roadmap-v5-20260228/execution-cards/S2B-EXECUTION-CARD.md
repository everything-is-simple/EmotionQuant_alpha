# S2b 执行卡（v0.2）

**状态**: Implemented（工程完成） + Code-Revalidated（通过）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S2b（MSS+IRS+PAS 集成推荐）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，集成推荐层达到完整版并可用于实战。
- 证据锚点：`src/integration/pipeline.py`、`src/pipeline/main.py`、`tests/unit/integration/test_integration_contract.py`、`tests/unit/integration/test_quality_gate_contract.py`。
- 关键确认：Integration 四模式、推荐硬约束（每日<=20/行业<=5）、`risk_reward_ratio >= 1.0` 与质量门闭环已生效。

---

## 代码级重验（2026-02-27）

- [x] run 冒烟通过（见统一审计汇总）
- [x] test 契约通过（见统一审计汇总）
- [x] 功能检查正常（见统一审计汇总）
- 结论：`通过`
- 证据：`artifacts/spiral-allcards/revalidation/20260227_125427/execution_cards_code_audit_summary.md`

## 1. 目标

- 打通集成推荐闭环，稳定产出 `integrated_recommendation`。
- 产出质量门结论 `quality_gate_report` 与 `s2_go_nogo_decision`。
- 固化执行边界：`contract_version = "nc-v1"`、`risk_reward_ratio >= 1.0`。
- 落地四种集成模式：`top_down/bottom_up/dual_verify/complementary`。
- 强制推荐硬约束：每日最多 `20`、单行业最多 `5`。

---

## 2. run

```bash
eq recommend --date {trade_date} --mode integrated --integration-mode top_down
eq recommend --date {trade_date} --mode integrated --integration-mode bottom_up
eq recommend --date {trade_date} --mode integrated --integration-mode dual_verify
eq recommend --date {trade_date} --mode integrated --integration-mode complementary
```

---

## 3. test

```bash
pytest tests/unit/integration/test_integration_contract.py -q
pytest tests/unit/integration/test_quality_gate_contract.py -q
pytest tests/unit/pipeline/test_cli_entrypoint.py -q
```

---

## 4. artifact

- `artifacts/spiral-s2b/{trade_date}/integrated_recommendation_sample.parquet`
- `artifacts/spiral-s2b/{trade_date}/quality_gate_report.md`
- `artifacts/spiral-s2b/{trade_date}/s2_go_nogo_decision.md`
- `artifacts/spiral-s2b/{trade_date}/error_manifest_sample.json`
- `artifacts/spiral-s2b/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `integrated_recommendation` 与 `integration-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2b/review.md`
- 必填结论：
  - `integrated_recommendation` 当日是否 `> 0`
  - `integration_mode` 是否可追溯且仅取 `{top_down,bottom_up,dual_verify,complementary}`
  - 推荐数量约束是否生效（每日<=20、单行业<=5）
  - `quality_gate_report.status` 是否为 `PASS/WARN`
  - A 股可追溯字段是否齐备：`t1_restriction_hit`、`limit_guard_result`、`session_guard_result`
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s2b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若质量门为 FAIL：状态置 `blocked`，不得推进 S3a/S3，必须进入 S2r。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2b 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- Integration 设计：`docs/design/core-algorithms/integration/integration-algorithm.md`

---

## 历史债务状态（2026-02-27 清零同步）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

