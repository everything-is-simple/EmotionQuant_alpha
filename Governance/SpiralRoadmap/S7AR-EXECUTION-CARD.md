# S7ar 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S7ar（调度修复子圈）

---

## 1. 目标

- 条件触发圈：当 S7a `gate = FAIL` 时启动。
- 仅修复调度阻断项，不扩功能。
- 形成修复前后调度稳定性差异证据，并返回 S7a 重验。

---

## 2. run

```bash
eq scheduler run-once --repair s7ar
```

---

## 3. test

```bash
pytest tests/unit/pipeline/test_scheduler_calendar_idempotency.py -q
pytest tests/unit/pipeline/test_scheduler_run_history_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s7ar/{trade_date}/s7ar_patch_note.md`
- `artifacts/spiral-s7ar/{trade_date}/s7ar_delta_report.md`
- `artifacts/spiral-s7ar/{trade_date}/gate_report.md`
- `artifacts/spiral-s7ar/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s7ar/review.md`
- 必填结论：
  - 调度阻断项是否全部清除
  - 修复前后稳定性差异是否可解释
  - 返回 S7a 重验是否通过

---

## 6. sync

- `Governance/specs/spiral-s7ar/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若修复后仍 `FAIL`：保持 `blocked`，仅允许在 S7ar 继续修复，不得推进 release。
- 若定位到 S6 稳定性前置异常：回退 S6 修复后再返回。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-20）

- 条件触发圈，当前未触发。
