# S6 执行卡（v1.0）

**状态**: Planned  
**更新时间**: 2026-02-26  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S6（稳定化闭环：全链路重跑一致性 + 债务清偿）

---

## 1. 目标

- 通过全链路重跑一致性验证（分链路分级阈值），形成阶段C稳定基线。
- 输出推荐/回测/门禁关键链路一致性报告。
- 完成阶段债务清偿记录与残留债务延期说明。

---

## 2. Scope（本圈必须/禁止）

- In Scope：`eq run-all` 全链路重跑、ConsistencyChecker 一致性检查器（三链路三阈值）、债务清偿日志、gate_report §Design-Alignment-Fields。
- Out Scope：新功能开发、核心算法语义修改、盘中增量流程。

---

## 3. 模块级补齐任务（全部必做）

| 模块 | 必须补齐 | 设计依据 | 验收要点 |
|---|---|---|---|
| FullChainReplay | `eq run-all --start {start} --end {end}` 子命令，按日期窗口串行执行 L1→L2→Signal→Validation→Integration→Backtest→Analysis 全链路，产出 artifacts | `docs/design/enhancements/eq-improvement-plan-core-frozen.md` ENH-08 | 同窗口重跑两次，一致性检查通过 |
| ConsistencyChecker | 三链路分级一致性验证器：① 门禁链路 `validation_gate_decision.final_gate` 完全一致（否则 FAIL）；② 评分链路 `integrated_recommendation.final_score` 差异 <1e-6（否则 WARN）；③ 收益链路 `backtest_results.total_return` 差异 <1e-4（否则 WARN） | 所有 L3/L4 表 DDL 与对应 `*-data-models.md` | WARN 必须 review.md 可解释；不可解释 → FAIL |
| DebtSettlement | 阶段债务清偿日志：读取 `Governance/record/debts.md`，逐条标注 resolved/deferred/wontfix，产出 `debt_settlement_log.md` | `Governance/steering/6A-WORKFLOW.md` §8 跨文档变更联动 | 每条债务有明确结论；残留债务有延期原因与预期落位 |

---

## 4. run

**baseline**（圈前健康检查）：

```bash
pytest tests/unit/integration -q
python -m scripts.quality.local_quality_check --contracts --governance
```

**target**（本圈收口必须成立）：

```bash
eq run-all --start {start} --end {end}
```

---

## 5. test

**baseline**（已存在）：

```bash
pytest tests/unit/integration/test_integration_contract.py -q
pytest tests/unit/scripts/test_contract_behavior_regression.py -q
pytest tests/unit/scripts/test_governance_consistency_check.py -q
```

**target**（本圈必须补齐并执行）：

```bash
pytest tests/unit/integration/test_full_chain_contract.py -q
pytest tests/unit/integration/test_replay_reproducibility.py -q
pytest tests/unit/scripts/test_design_freeze_guard.py -q
```

验证要点：

- **门禁链路**：`final_gate` 完全一致（categorical，不允许差异）。
- **评分链路**：`final_score` 差异 < 1e-6。
- **收益链路**：`total_return` 差异 < 1e-4。

---

## 6. artifact

- `artifacts/spiral-s6/{end_date}/consistency_replay_report.md`
- `artifacts/spiral-s6/{end_date}/run_all_diff_report.md`
- `artifacts/spiral-s6/{end_date}/debt_settlement_log.md`
- `artifacts/spiral-s6/{end_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s6/{end_date}/consumption.md`

---

## 7. review

- 复盘文件：`Governance/specs/spiral-s6/review.md`
- 必填结论：
  - 同窗口重跑三链路一致性是否满足阈值
  - WARN 链路差异是否可解释并完成记录
  - 债务清偿与延期记录是否完整
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 8. 硬门禁

- 门禁链路（`final_gate`）不一致，S6 不得标记 `completed`。
- WARN 链路差异不可解释，状态必须置 `blocked`。
- 债务清偿日志缺失或残留债务无延期说明，不得推进 S7a。
- `python -m scripts.quality.local_quality_check --contracts --governance` 未通过时，只允许进入 S6r 修复圈。

---

## 9. sync

- `Governance/specs/spiral-s6/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 10. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S6r` 修复子圈，不推进 S7a。
- 若发现展示口径输入异常：回退 S5 修复后再返回 S6。

---

## 11. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`
- 改进行动计划：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`（ENH-08 设计冻结检查）
- 6A 工作流：`Governance/steering/6A-WORKFLOW.md`（§8 跨文档变更联动）

---

## 12. 历史债务消化（审计插入 2026-02-26）

| 来源 | 描述 | 审计结论 |
|---|---|---|
| TD-DA-009 | Enum 设计-实现对齐缺口 | 仍待清偿：src/models/enums.py 与 docs/design/*-data-models.md 仍有类名/成员偏差，S6 必须给出对齐结果（实现对齐或设计修订）。 |
| TD-DA-010 | Calculator/Repository 与设计 API 差距 | 仍待清偿：MSS/IRS 仅完成试点薄封装，方法数量与签名未覆盖设计口径，S6 必须给出“继续实现”或“文档降阶”决策。 |
| TD-DA-011 | Integration 双模式语义冲突 | 仍待清偿：dual_verify/complementary 在代码与设计的共识因子、字段落库和权重语义存在差异，S6 必须完成对齐并补测试。 |
| TD-ARCH-001 | OOP 设计与 Pipeline 实现并存 | 已决策：执行 ARCH-DECISION-001（文档对齐代码）；S6 负责防止新增口径漂移。 |

---

## 13. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-02-26 | 升级至 S2c 同精度：新增 Scope、模块级补齐任务表（3模块）、硬门禁、质量检查命令、设计文档交叉引用；一致性阈值量化（三链路分级）；run/test 改为 baseline+target 双层 |
| v0.1+audit | 2026-02-26 | 新增 §9 历史债务消化审计（4条） |
| v0.1 | 2026-02-20 | 首版执行卡 |

---

## 14. 本轮进度（2026-02-26）

- ? `eq run-all --date {date}` CLI 子命令已落地（全链路串行 + 二次重跑一致性检查）。
- ? `src/pipeline/consistency.py` ConsistencyChecker 已实现（三层阈值：gate 精确 / score <1e-6 / return <1e-4）。
- ? 3 个 target 测试文件已创建，31 条测试全部通过（test_full_chain_contract / test_replay_reproducibility / test_design_freeze_guard）。
- 待完成：端到端 artifact 产出、债务清偿日志、review/sync 闭环。
