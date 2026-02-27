# S3r 执行卡（v0.2）

**状态**: Implemented（工程完成） + Code-Revalidated（通过）  
**重验口径**: 本卡"工程完成"不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-25  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3r（回测修复子圈）

---

## 0. 现状对齐（2026-02-21）

- `eq backtest --repair s3r` 已接入 CLI 与回测流水线。
- 当前为条件触发圈：仅当 S3 `gate=FAIL` 时进入执行与收口。

## 代码级重验（2026-02-27）

- [x] run 冒烟通过（见统一审计汇总）
- [x] test 契约通过（见统一审计汇总）
- [x] 功能检查正常（见统一审计汇总）
- 结论：`通过`
- 证据：`artifacts/spiral-allcards/revalidation/20260227_125427/execution_cards_code_audit_summary.md`

## 1. 目标

- 条件触发圈：当 S3 `gate = FAIL` 时启动。
- 仅修复阻断项，不扩功能，恢复回测门禁为 `PASS/WARN`。
- 固化“修复前后收益与风险差异”证据，返回 S3 重验。

---

## 2. run

```bash
eq backtest --engine {engine} --start {start} --end {end} --repair s3r
```

---

## 3. test

```bash
pytest tests/unit/backtest/test_backtest_contract.py -q
pytest tests/unit/backtest/test_backtest_reproducibility.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3r/{trade_date}/s3r_patch_note.md`
- `artifacts/spiral-s3r/{trade_date}/s3r_delta_report.md`
- `artifacts/spiral-s3r/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s3r/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3r/review.md`
- 必填结论：
  - 阻断根因是否定位清楚并修复
  - 修复前后关键指标差异是否可解释
  - 返回 S3 重验是否通过
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s3r/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若修复后仍 `FAIL`：保持 `blocked`，仅允许在 S3r 继续修复，不得跳转 S4。
- 若定位到阶段A输入契约异常（含桥接缺失）：按门禁回退 S2c 修复后再返回。

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

- 条件触发圈，当前未触发。
- 已完成实现前置：`--repair s3r` 可执行，且可产出 `s3r_patch_note/s3r_delta_report`。

