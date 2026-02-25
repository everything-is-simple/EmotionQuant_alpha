# S6 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S6（稳定化闭环）

---

## 1. 目标

- 通过全链路重跑一致性验证，形成阶段C稳定基线。
- 输出推荐/回测/交易/分析关键链路一致性报告。
- 完成阶段债务清偿记录与残留债务延期说明。

---

## 2. run

```bash
eq run-all --start {start} --end {end}
```

---

## 3. test

```bash
pytest tests/unit/integration/test_full_chain_contract.py -q
pytest tests/unit/integration/test_replay_reproducibility.py -q
pytest tests/unit/scripts/test_design_freeze_guard.py -q
```

---

## 4. artifact

- `artifacts/spiral-s6/{trade_date}/consistency_replay_report.md`
- `artifacts/spiral-s6/{trade_date}/run_all_diff_report.md`
- `artifacts/spiral-s6/{trade_date}/debt_settlement_log.md`
- `artifacts/spiral-s6/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s6/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s6/review.md`
- 必填结论：
  - 同窗口重跑一致性是否满足阈值
  - 关键链路差异是否可解释并完成记录
  - 债务清偿与延期记录是否完整

---

## 6. sync

- `Governance/specs/spiral-s6/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S6r` 修复子圈，不推进 S7a。
- 若发现展示口径输入异常：回退 S5 修复后再返回 S6。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-20）

- 计划中，前置依赖为 S5 `PASS/WARN`。
