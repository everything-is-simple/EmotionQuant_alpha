# S4b Review（6A A4/A5）

**Spiral**: S4b  
**状态**: completed  
**复盘日期**: 2026-02-22

- 当前状态: 已完成跨窗口压力实跑与证据收口。
- 本轮完成:
  - 新增 `eq stress` CLI 与执行管线（含 `--repair s4br` 路径）。
  - 已完成四窗串行实跑：`20260210/20260211/20260212/20260213`。
  - 已完成 `trade + stress(limit_down_chain/liquidity_dryup)` 双场景闭环。

## 跨窗口实跑结果

- 汇总证据:
  - `artifacts/spiral-s4b/20260213/s4b_cross_window_summary.json`
  - `artifacts/spiral-s4b/20260213/s4b_cross_window_summary.md`
  - `artifacts/spiral-s4b/20260213/cross_window/*`
- 核心结论:
  - `all_trade_go=true`
  - `all_analysis_go=true`
  - `all_stress_go=true`
  - `stress_gate_distribution={'WARN': 8}`
  - `analysis_quality_distribution={'WARN': 4}`
  - `stress_policy_source_distribution={'live_backtest_deviation': 8}`
  - `stress_dominant_component_distribution={'signal': 8}`

## 质量与门禁

- 目标测试:
  - `pytest -q tests/unit/trading tests/unit/pipeline/test_cli_entrypoint.py::test_main_stress_command_wires_to_pipeline` -> `10 passed`
- 治理门禁:
  - `python -m scripts.quality.local_quality_check --contracts --governance` -> PASS

## 补充修复

- 已完成 `TDL-S4B-004`：将 `analysis --deviation live-backtest` 的“单侧样本缺失”从 `P1 error` 调整为 warning（`WARN/GO` 非阻断）。
- 回归测试：`tests/unit/analysis/test_live_backtest_deviation_contract.py::test_live_backtest_deviation_backtest_side_empty_is_warn_not_fail`。
