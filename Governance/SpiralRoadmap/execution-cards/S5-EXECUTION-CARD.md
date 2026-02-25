# S5 执行卡（v0.3）

**状态**: Active  
**更新时间**: 2026-02-25  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S5（展示闭环）

---

## 1. 目标

- GUI 可启动并保持只读展示，不在页面层执行算法计算。
- 日报导出可用，且输入可追溯到 L1/L2/L3 与参数快照。
- 固化阶段B参数消费口径，为 S6 稳定化重跑提供展示基线。

## 0. 现状对齐（2026-02-23）

- `eq gui` 子命令已落地，`daily-report` 导出链路与基础合同测试已打通。
- 当前处于 S5 最小闭环实现阶段，待补齐页面层截图证据后评估 `Completed`。

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
pytest tests/unit/gui/test_freshness_meta_contract.py -q
pytest tests/unit/gui/test_filter_config_contract.py -q
pytest tests/unit/gui/test_pnl_color_contract.py -q
```

**FreshnessMeta 验证**（对齐 `gui-data-models.md` v3.2.0）：`DashboardData.freshness` 徽标可渲染，`FreshnessLevel`（`fresh/stale_soon/stale`）三态可触发。
**FilterConfig 来源追溯**：`FilterConfig.source` 可审计（`env_default/user_override/session_override`），Dashboard 显示 `active_filter_badges`。
**A 股红涨绿跌**：`pnl_color` 验证 >0 红 / <0 绿 / =0 灰，与 `gui-data-models.md` §5.2 一致。

---

## 4. artifact

- `artifacts/spiral-s5/{trade_date}/gui_snapshot.png`
- `artifacts/spiral-s5/{trade_date}/daily_report_sample.md`
- `artifacts/spiral-s5/{trade_date}/gui_export_manifest.json`
- `artifacts/spiral-s5/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 GUI 核心 dataclass 与 `gui-data-models.md` 一致性）
- `artifacts/spiral-s5/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s5/review.md`
- 必填结论：
  - GUI 启动与只读约束是否稳定成立
  - `daily_report` 导出链路是否完整可追溯
  - 展示参数是否与 S4b 防御基线一致且无手工覆盖
  - FreshnessMeta 三态是否可触发
  - FilterConfig 来源追溯是否可审计
  - pnl_color 红涨绿跌是否与 gui-data-models §5.2 一致
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s5/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S5r` 修复子圈，不推进 S6。
- 若发现阶段B归因/防御参数失真：回退 S4b 重校准后再返回 S5。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-20）

- 计划中，前置依赖为 S4b `PASS/WARN`。
