# S4b Final（6A 收口）

**Spiral**: S4b  
**状态**: completed  
**收口日期**: 2026-02-22

## 收口结论

- `S4b` 极端防御专项已完成最小闭环并通过跨窗口实跑验证。
- 两类场景（`limit_down_chain`、`liquidity_dryup`）在四个交易日窗口均给出可重放产物与可审计门状态。
- 防御参数来源已可追溯到 S3b 偏差表（`live_backtest_deviation`）。
- 偏差单侧样本缺失语义已修复为 `WARN/GO`（`TDL-S4B-004`），跨窗口 `analysis` 不再误判 `FAIL`。

## 收口证据

1. 总览:
   - `artifacts/spiral-s4b/20260213/s4b_cross_window_summary.json`
   - `artifacts/spiral-s4b/20260213/s4b_cross_window_summary.md`
2. 实跑清单:
   - `artifacts/spiral-s4b/20260213/s4b_run_manifest.json`
   - `artifacts/spiral-s4b/20260213/s4b_run_manifest_analysis_stress.json`
3. 窗口快照:
   - `artifacts/spiral-s4b/20260213/cross_window/backtest_*.json`
   - `artifacts/spiral-s4b/20260213/cross_window/trade_*.json`
   - `artifacts/spiral-s4b/20260213/cross_window/stress_*.json`
   - `artifacts/spiral-s4b/20260213/cross_window/analysis_deviation_*.json`

## 测试与门禁

- `pytest -q tests/unit/trading tests/unit/pipeline/test_cli_entrypoint.py::test_main_stress_command_wires_to_pipeline` -> `10 passed`
- `python -m scripts.quality.local_quality_check --contracts --governance` -> PASS

## 后续动作

- 若后续 S4b 出现 `gate=FAIL`，按执行卡进入 `S4br` 修复子圈，不直接推进 S5。
