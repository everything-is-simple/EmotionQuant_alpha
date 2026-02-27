# S4b 执行卡（v0.1）

**状态**: Implemented（工程完成） + Code-Revalidated（通过）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S4b（极端防御专项闭环）

---

## 代码级重验（2026-02-27）

- [x] run 冒烟通过（见统一审计汇总）
- [x] test 契约通过（见统一审计汇总）
- [x] 功能检查正常（见统一审计汇总）
- 结论：`通过`
- 证据：`artifacts/spiral-allcards/revalidation/20260227_125427/execution_cards_code_audit_summary.md`

## 1. 目标

- 覆盖连续跌停与流动性枯竭压力场景，验证应急降杠杆策略。
- 固化“防御参数来源于 S3b 归因结论”的可追溯链路。
- 输出可复核压力回放产物，为阶段C提供防御基线。

---

## 2. run

```bash
eq stress --scenario limit_down_chain --date {trade_date}
eq stress --scenario liquidity_dryup --date {trade_date}
```

---

## 3. test

```bash
pytest tests/unit/trading/test_stress_limit_down_chain.py -q
pytest tests/unit/trading/test_stress_liquidity_dryup.py -q
pytest tests/unit/trading/test_deleveraging_policy_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s4b/{trade_date}/extreme_defense_report.md`
- `artifacts/spiral-s4b/{trade_date}/deleveraging_policy_snapshot.json`
- `artifacts/spiral-s4b/{trade_date}/stress_trade_replay.csv`
- `artifacts/spiral-s4b/{trade_date}/consumption.md`
- `artifacts/spiral-s4b/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s4b/review.md`
- 必填结论：
  - 压力场景下防御链路是否稳定触发并可重放
  - 次日重试与仓位封顶逻辑是否符合预期
  - 参数来源是否可追溯到 S3b 归因结论
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s4b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S4br` 修复子圈，不推进 S5。
- 若归因参数来源不可审计：回退 S3b 补齐归因证据后再返回。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

---

## 历史债务状态（2026-02-27 清零同步）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

（2026-02-18）

- 计划中，前置依赖为 S3b `PASS/WARN`。



