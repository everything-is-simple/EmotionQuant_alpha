# S3d Final（6A 收口）

**Spiral**: S3d  
**状态**: completed  
**收口日期**: 2026-02-22

- 收口结论:
  - Adaptive 阈值跨窗口（`20260210/11/12/13`）全部 `PASS`。
  - future_returns probe 跨窗口（4 组）均成功落盘并可解释：
    - `PASS_POSITIVE_SPREAD` 2 组
    - `WARN_NEGATIVE_SPREAD` 1 组
    - `WARN_FLAT_SPREAD` 1 组
  - 短窗口边界（`20260210-20260213`）样本不足 `P1` 已固化为非阻断边界证据。

## 收口证据

1. 总览：
   - `artifacts/spiral-s3d/20260213/s3d_cross_window_summary.json`
   - `artifacts/spiral-s3d/20260213/s3d_cross_window_summary.md`
2. 窗口级快照：
   - `artifacts/spiral-s3d/20260213/cross_window/adaptive_20260210/*`
   - `artifacts/spiral-s3d/20260213/cross_window/adaptive_20260211/*`
   - `artifacts/spiral-s3d/20260213/cross_window/adaptive_20260212/*`
   - `artifacts/spiral-s3d/20260213/cross_window/adaptive_20260213/*`
   - `artifacts/spiral-s3d/20260213/cross_window/probe_20260119_20260213/*`
   - `artifacts/spiral-s3d/20260213/cross_window/probe_20260126_20260213/*`
   - `artifacts/spiral-s3d/20260213/cross_window/probe_20260203_20260213/*`
   - `artifacts/spiral-s3d/20260213/cross_window/probe_20260206_20260213/*`
   - `artifacts/spiral-s3d/20260213/cross_window/boundary_20260210_20260213/*`

## 测试与门禁

- `pytest tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_supports_s3d_threshold_mode tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_probe_supports_future_returns_source -q` -> `5 passed`
- `python -m scripts.quality.local_quality_check --contracts --governance` -> PASS
