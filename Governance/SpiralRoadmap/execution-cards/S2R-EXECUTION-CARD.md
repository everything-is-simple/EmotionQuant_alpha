# S2r 执行卡（v0.2）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S2r（质量门失败修复子圈）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，S2 失败修复子圈具备可执行与可追溯能力。
- 证据锚点：`src/pipeline/recommend.py`、`src/pipeline/main.py`、`tests/unit/integration/test_quality_gate_contract.py`。
- 关键确认：`--repair s2r` 已可运行，修复产物 `s2r_patch_note/s2r_delta_report` 与 `integration_mode`、桥接链路均可审计。

---

## 1. 目标

- 触发条件：S2b `quality_gate_report.status = FAIL`。
- 只修不扩，恢复到 `PASS/WARN` 可推进状态。
- 产出修复证据：`s2r_patch_note` 与 `s2r_delta_report`。
- 修复后必须保持可追溯：`integration_mode`、`weight_plan_id`、`quality_gate_status` 与修复前后一致性可审计。

---

## 2. run

```bash
eq recommend --date {trade_date} --mode integrated --repair s2r
eq recommend --date {trade_date} --mode integrated --integration-mode {top_down|bottom_up|dual_verify|complementary} --repair s2r
```

---

## 3. test

```bash
pytest tests/unit/integration/test_validation_gate_contract.py -q
pytest tests/unit/integration/test_quality_gate_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s2r/{trade_date}/s2r_patch_note.md`
- `artifacts/spiral-s2r/{trade_date}/s2r_delta_report.md`
- `artifacts/spiral-s2r/{trade_date}/quality_gate_report.md`
- `artifacts/spiral-s2r/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验修复后产物与 `integration-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2r/review.md`
- 必填结论：
  - 修复前后差异是否可追溯
  - `quality_gate_report.status` 是否恢复到 `PASS/WARN`
  - 修复后 `integration_mode` 与桥接链路是否仍可审计
  - 是否满足回到 S2b 重验条件
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s2r/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若修复后仍 FAIL：保持 `blocked`，继续留在 S2r，不允许推进后续圈。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2r 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- Integration 设计：`docs/design/core-algorithms/integration/integration-algorithm.md`

---

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

