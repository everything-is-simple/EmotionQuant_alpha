# S6r 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S6r（稳定化修复子圈）

---

## 1. 目标

- 条件触发圈：当 S6 `gate = FAIL` 时启动。
- 仅修复稳定化门禁阻断项，不扩功能。
- 形成修复前后重跑差异证据，并返回 S6 重验。

---

## 2. run

```bash
eq run-all --start {start} --end {end} --repair s6r
```

---

## 3. test

```bash
pytest tests/unit/integration/test_replay_reproducibility.py -q
pytest tests/unit/scripts/test_design_freeze_guard.py -q
```

---

## 4. artifact

- `artifacts/spiral-s6r/{trade_date}/s6r_patch_note.md`
- `artifacts/spiral-s6r/{trade_date}/s6r_delta_report.md`
- `artifacts/spiral-s6r/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s6r/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s6r/review.md`
- 必填结论：
  - 稳定化阻断项是否全部清除
  - 修复前后重跑差异是否可解释
  - 返回 S6 重验是否通过

---

## 6. sync

- `Governance/specs/spiral-s6r/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若修复后仍 `FAIL`：保持 `blocked`，仅允许在 S6r 继续修复，不得推进 S7a。
- 若定位到上游 S5 展示输入异常：回退 S5 修复后再返回。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-20）

- 条件触发圈，当前未触发。
