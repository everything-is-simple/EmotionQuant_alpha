# S4r 执行卡（v0.1）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S4r（纸上交易修复子圈）

---

## 1. 目标

- 条件触发圈：当 S4 `gate = FAIL` 时启动。
- 仅修复交易闭环阻断项，不扩功能。
- 形成“修复前后成交与风险差异”证据，并返回 S4 重验。

---

## 2. run

```bash
eq trade --mode paper --date {trade_date} --repair s4r
```

---

## 3. test

```bash
pytest tests/unit/trading/test_order_pipeline_contract.py -q
pytest tests/unit/trading/test_risk_guard_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s4r/{trade_date}/s4r_patch_note.md`
- `artifacts/spiral-s4r/{trade_date}/s4r_delta_report.md`
- `artifacts/spiral-s4r/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s4r/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s4r/review.md`
- 必填结论：
  - 阻断项是否全部消除
  - 修复前后执行偏差是否可解释
  - 返回 S4 重验是否通过

---

## 6. sync

- `Governance/specs/spiral-s4r/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若修复后仍 `FAIL`：保持 `blocked`，仅允许在 S4r 继续修复，不得推进 S3b/S4b。
- 若定位到上游 S3 输入异常：先回 S3/S3r 修复后再返回。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-18）

- 条件触发圈，当前未触发。


