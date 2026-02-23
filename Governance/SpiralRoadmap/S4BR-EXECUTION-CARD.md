# S4br 执行卡（v0.1）

**状态**: Completed  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S4br（极端防御修复子圈）

---

## 1. 目标

- 条件触发圈：当 S4b `gate = FAIL` 时启动。
- 仅修复极端防御阻断项，不扩功能。
- 形成修复前后压力场景回撤差异证据，返回 S4b 重验。

---

## 2. run

```bash
eq stress --scenario all --date {trade_date} --repair s4br
```

---

## 3. test

```bash
pytest tests/unit/trading/test_stress_limit_down_chain.py -q
pytest tests/unit/trading/test_stress_liquidity_dryup.py -q
```

---

## 4. artifact

- `artifacts/spiral-s4br/{trade_date}/s4br_patch_note.md`
- `artifacts/spiral-s4br/{trade_date}/s4br_delta_report.md`
- `artifacts/spiral-s4br/{trade_date}/gate_report.md`
- `artifacts/spiral-s4br/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s4br/review.md`
- 必填结论：
  - 防御阻断项是否全部清除
  - 修复前后回撤差异是否可解释
  - 返回 S4b 重验是否通过

---

## 6. sync

- `Governance/specs/spiral-s4br/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若修复后仍 `FAIL`：保持 `blocked`，仅允许在 S4br 继续修复，不得推进 S5。
- 若归因参数来源缺失：回退 S3b 补齐证据后再返回。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-18）

- 条件触发圈，当前未触发。
