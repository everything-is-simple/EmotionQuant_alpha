# Reborn 第三螺旋：Production 闭环（Plan B）

**螺旋编号**: Reborn-Spiral-3  
**更新时间**: 2026-02-25  
**周期**: 2-3个月（+ 螺旋3.5 预演）  
**定位**: 生产运行闭环，目标是“可运维、可回放、可审计”，不是口头实盘就绪

---

## 1. 螺旋目标

1. 完成 S5-S7a 的生产化闭环。
2. 通过螺旋3.5 预演门禁后才允许进入真实资金。
3. 维持与 `docs/design/core-infrastructure/*` 一致，不新增脱轨架构。

---

## 2. 设计文档绑定（字段级）

| 设计域 | 文档目录 | 关键验证字段 |
|---|---|---|
| GUI | `gui/gui-data-models.md` | `DashboardData.freshness`、`FreshnessLevel`(3态)、`FilterConfig.source`(3值)、`pnl_color`(红涨绿跌) |
| Analysis | `analysis/analysis-data-models.md` | `daily_report` L4 可追溯、`PerformanceMetrics` |
| Trading | `trading/trading-data-models.md` | 风控事件、执行日志可回放 |
| Data Layer | `data-layer/data-layer-data-models.md` | 调度后落库一致性 |
| Enhancements | `eq-improvement-plan-core-frozen.md` | ENH-01/07/08/11 收口 |

---

## 3. 微圈体系与 Plan A 映射

| PB 微圈 | 名称 | 对应 Plan A | 前置 | 核心产出 |
|---|---|---|---|---|
| PB-3.1 | 展示闭环 | S5 | 螺旋2 GO | GUI 只读消费 + 日报导出 |
| PB-3.2 | 稳定化闭环 | S6 | PB-3.1 GO | 全链路重跑一致 + 债务清偿 |
| PB-3.3 | 调度闭环 | S7a | PB-3.2 GO | 调度可审计 + 幂等去重 |
| PB-3.4 | Pre-Live 预演 | 螺旋3.5 | PB-3.3 GO | 20日零下单预演通过 |

---

## 4. PB-3.1 展示闭环合同

- **主目标**：GUI 可启动、只读展示、日报可导出。
- **Plan A 对应**：S5
- **ENH**：ENH-01/07
- `run`：
  - `eq gui --date {trade_date}`
  - `eq gui --date {trade_date} --export daily-report`
- `test`：`tests/unit/gui/test_gui_launch_contract.py tests/unit/gui/test_gui_readonly_contract.py tests/unit/analysis/test_daily_report_export_contract.py`
- 门禁：
  - GUI 启动成功，且不在页面层执行算法计算。
  - `daily_report` 导出成功，可追溯到 L1/L2/L3 输入与参数。
  - 展示口径与螺旋2归因/防御参数一致。
  - **FreshnessMeta 验证**：`DashboardData.freshness` 徽标可渲染，`FreshnessLevel`（`fresh/stale_soon/stale`）三态可触发。
  - **FilterConfig 来源追溯**：`FilterConfig.source` 可审计（`env_default/user_override/session_override`）。
  - **A 股红涨绿跌**：`pnl_color` >0 红 / <0 绿 / =0 灰。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`gui_snapshot.png`、`daily_report_sample.md`、`gui_export_manifest.json`
- 消费：PB-3.2 记录“稳定化重跑基于 S5 统一展示口径”。

---

## 5. PB-3.2 稳定化闭环合同

- **主目标**：全链路重跑一致性 + 债务清偿。
- **Plan A 对应**：S6
- **ENH**：ENH-08(全量)
- `run`：`eq run-all --start {start} --end {end}`
- `test`：`tests/unit/integration/test_full_chain_contract.py tests/unit/integration/test_replay_reproducibility.py tests/unit/scripts/test_design_freeze_guard.py`
- 门禁：
  - 同窗口重跑关键产物一致（或差异在阈值内并有解释）。
  - 债务清偿记录完成，残留债务有明确延期原因。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`consistency_replay_report.md`、`run_all_diff_report.md`、`debt_settlement_log.md`
- 消费：PB-3.3 记录“调度上线依赖 S6 稳定基线”。

---

## 6. PB-3.3 调度闭环合同

- **主目标**：每日自动调度可安装、可观测、可去重。
- **Plan A 对应**：S7a
- **ENH**：ENH-11
- `run`：
  - `eq scheduler install`
  - `eq scheduler status`
  - `eq scheduler run-once`
- `test`：`tests/unit/pipeline/test_scheduler_install_contract.py tests/unit/pipeline/test_scheduler_calendar_idempotency.py tests/unit/pipeline/test_scheduler_run_history_contract.py`
- 门禁：
  - 调度安装与状态查询可用。
  - 非交易日自动跳过，交易日重复任务幂等去重。
  - 失败重试、运行历史、最近结果可审计。
  - 调度层不改业务语义，仅做编排与运维增强。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`scheduler_status.json`、`scheduler_run_history.md`、`scheduler_bootstrap_checklist.md`
- 消费：PB-3.4 记录“预演基于 S7a 调度基线”。

---

## 7. PB-3.4 Pre-Live 预演合同

- **主目标**：连续20交易日零真实下单预演，证明系统可以安全进入生产。
- **Plan A 对应**：螺旋3.5
- **ENH**：无
- `run`：`eq run-all --date {trade_date} --mode preview`（连续20日）
- 门禁：
  - 连续 >=20 个交易日零真实下单预演。
  - 每日偏差复盘：`signal_deviation/execution_deviation/cost_deviation`。
  - 至少 1 次故障恢复演练通过。
  - 预演期间 0 个 P0 事故。
  - 偏差受控（signal_deviation/execution_deviation 均值 <5%）。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`preview_daily_report_*.md`、`preview_deviation_summary.json`、`fault_recovery_drill_report.md`
- 消费：螺旋3 收口评审。

---

## 8. 螺旋3门禁汇总

### 8.1 入口门禁

- 螺旋2 `GO`
- 关键 P0 阻断项已清除

### 8.2 出口门禁（进入真实资金前）

- [ ] PB-3.1~PB-3.4 各微圈 gate 均 PASS/WARN
- [ ] S5/S6/S7a 闭环证据齐备
- [ ] 螺旋3.5 全项通过
- [ ] 预演评审给出 `GO`
- [ ] `PLAN-B-READINESS-SCOREBOARD.md` 更新完成

---

## 9. 失败处理

1. 微圈 gate 未通过：仅允许在当前微圈范围修复。
2. 螺旋3 出口任一项未通过：判定 `NO_GO`。
3. 螺旋3.5 未通过：禁止真实资金。
4. 连续两轮 `NO_GO`：必须回溯螺旋2输入假设。

---

## 10. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.0 | 2026-02-25 | 堵最大缺口：拆分为 PB-3.1~PB-3.4 微圈执行合同；设计绑定到字段级；增加 FreshnessMeta/FilterConfig/pnl_color 验证、偏差受控阈值、微圈间消费链 |
| v2.1 | 2026-02-24 | 重写为生产闭环执行合同 |
| v2.0 | 2026-02-23 | 同精度版 |
