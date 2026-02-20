# S5 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S5（展示闭环）

---

## 1. 目标

- GUI 可启动并保持只读展示，不在页面层执行算法计算。
- 日报导出可用，且输入可追溯到 L1/L2/L3 与参数快照。
- 固化阶段B参数消费口径，为 S6 稳定化重跑提供展示基线。

---

## 2. run

```bash
eq gui --date {trade_date}
eq gui --date {trade_date} --export daily-report
```

---

## 3. test

```bash
pytest tests/unit/gui/test_gui_launch_contract.py -q
pytest tests/unit/gui/test_gui_readonly_contract.py -q
pytest tests/unit/analysis/test_daily_report_export_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s5/{trade_date}/gui_snapshot.png`
- `artifacts/spiral-s5/{trade_date}/daily_report_sample.md`
- `artifacts/spiral-s5/{trade_date}/gui_export_manifest.json`
- `artifacts/spiral-s5/{trade_date}/gate_report.md`
- `artifacts/spiral-s5/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s5/review.md`
- 必填结论：
  - GUI 启动与只读约束是否稳定成立
  - `daily_report` 导出链路是否完整可追溯
  - 展示参数是否与 S4b 防御基线一致且无手工覆盖

---

## 6. sync

- `Governance/specs/spiral-s5/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S5r` 修复子圈，不推进 S6。
- 若发现阶段B归因/防御参数失真：回退 S4b 重校准后再返回 S5。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-20）

- 计划中，前置依赖为 S4b `PASS/WARN`。
