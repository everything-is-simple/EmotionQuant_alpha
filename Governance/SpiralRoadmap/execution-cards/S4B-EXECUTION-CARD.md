# S4b 执行卡（v0.1）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S4b（极端防御专项闭环）

---

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

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

（2026-02-18）

- 计划中，前置依赖为 S3b `PASS/WARN`。



