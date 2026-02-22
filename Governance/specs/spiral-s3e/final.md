# S3e Final（6A 收口）

**Spiral**: S3e  
**状态**: completed  
**收口日期**: 2026-02-22

- 收口结论:
  - Validation 生产口径跨窗口（`20260210/11/12/13`）全部通过执行：
    - `status=ok`
    - `final_gate=WARN`
    - `go_nogo=GO`
    - `selected_weight_plan=vp_balanced_v1`
  - `future_returns` 对齐、`dual-window` 投票与 OOS 指标报告均已稳定落盘。

## 收口证据

1. 总览：
   - `artifacts/spiral-s3e/20260213/s3e_cross_window_summary.json`
   - `artifacts/spiral-s3e/20260213/s3e_cross_window_summary.md`
2. 窗口级快照：
   - `artifacts/spiral-s3e/20260213/cross_window/20260210/*`
   - `artifacts/spiral-s3e/20260213/cross_window/20260211/*`
   - `artifacts/spiral-s3e/20260213/cross_window/20260212/*`
   - `artifacts/spiral-s3e/20260213/cross_window/20260213/*`

## 测试与门禁

- `pytest tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py tests/unit/algorithms/validation/test_decay_proxy_contract.py tests/unit/pipeline/test_cli_entrypoint.py::test_main_validation_command_wires_to_pipeline tests/unit/pipeline/test_cli_entrypoint.py::test_main_validation_runs_s3e_mode -q` -> `6 passed`
- `python -m scripts.quality.local_quality_check --contracts --governance` -> PASS
