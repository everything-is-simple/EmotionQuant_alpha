# S2r 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S2r（质量门失败修复子圈）

---

## 1. 目标

- 触发条件：S2b `quality_gate_report.status = FAIL`。
- 只修不扩，恢复到 `PASS/WARN` 可推进状态。
- 产出修复证据：`s2r_patch_note` 与 `s2r_delta_report`。

---

## 2. run

```bash
eq recommend --date {trade_date} --mode integrated --repair s2r
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

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2r/review.md`
- 必填结论：
  - 修复前后差异是否可追溯
  - `quality_gate_report.status` 是否恢复到 `PASS/WARN`
  - 是否满足回到 S2b 重验条件

---

## 6. sync

- `Governance/specs/spiral-s2r/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若修复后仍 FAIL：保持 `blocked`，继续留在 S2r，不允许推进后续圈。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2r 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
