# Spiral S5 Requirements

## 状态
- in_progress

## 主目标
- 建立 S5 GUI 最小闭环：`eq gui` 可运行，`eq gui --export daily-report` 可导出并可审计。

## In Scope（本圈）
1. 新增 `eq gui` 子命令并接入统一入口。
2. 实现 `daily-report` 导出最小链路（`daily_report_sample.md`、`gui_export_manifest.json`、`gate_report.md`、`consumption.md`）。
3. 补齐最小合同测试：
   - `tests/unit/gui/test_gui_launch_contract.py`
   - `tests/unit/gui/test_gui_readonly_contract.py`
   - `tests/unit/analysis/test_daily_report_export_contract.py`

## Out Scope（本圈不做）
1. 不实现完整 Streamlit 页面布局与截图自动化（`gui_snapshot.png` 延后到 S5 后续切片）。
2. 不引入新的外部依赖或前端框架改造。
3. 不推进 S6/S7a 功能实现。

## 验收标准
1. 运行命令可成功：
   - `eq gui --date {trade_date}`
   - `eq gui --date {trade_date} --export daily-report`
2. 目标测试通过。
3. 导出产物在 `artifacts/spiral-s5/{trade_date}/` 落盘且字段可复核。
