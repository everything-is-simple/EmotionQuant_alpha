# S5r 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S5r（展示修复子圈）

---

## 1. 目标

- 条件触发圈：当 S5 `gate = FAIL` 时启动。
- 仅修复展示闭环阻断项，不扩功能。
- 形成修复前后展示与导出差异证据，并返回 S5 重验。

---

## 2. run

```bash
eq gui --date {trade_date} --repair s5r
```

---

## 3. test

```bash
pytest tests/unit/gui/test_gui_launch_contract.py -q
pytest tests/unit/analysis/test_daily_report_export_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s5r/{trade_date}/s5r_patch_note.md`
- `artifacts/spiral-s5r/{trade_date}/s5r_delta_report.md`
- `artifacts/spiral-s5r/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s5r/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s5r/review.md`
- 必填结论：
  - 展示闭环阻断项是否全部消除
  - 修复前后展示与导出差异是否可解释
  - 返回 S5 重验是否通过
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s5r/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若修复后仍 `FAIL`：保持 `blocked`，仅允许在 S5r 继续修复，不得推进 S6。
- 若定位到上游 S4b 参数消费异常：回退 S4b 修复后再返回。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
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

（2026-02-20）

- 条件触发圈，当前未触发。

