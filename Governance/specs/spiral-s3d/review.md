# S3d Review（6A A4/A5）

**Spiral**: S3d  
**状态**: in_progress  
**复盘日期**: 2026-02-22（A4 阶段）

- 当前状态: CLI 阻断已解除，窗口级实跑证据补齐中。
- 本轮完成:
  - `eq mss --threshold-mode` 与 `eq mss-probe --return-series-source` 已落地。
  - 已完成一次 `future_returns` 实跑补证：
    - 命令：`python -m src.pipeline.main --env-file .env mss-probe --start 20260119 --end 20260213 --return-series-source future_returns`
    - 结果：`event=s3d_mss_probe`，`status=ok`，`conclusion=PASS_POSITIVE_SPREAD`，`top_bottom_spread_5d=0.0120704975`
    - 产物：`artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md`
    - 配套：`artifacts/spiral-s3d/20260119_20260213/gate_report.md`、`artifacts/spiral-s3d/20260119_20260213/consumption.md`、`artifacts/spiral-s3d/20260119_20260213/error_manifest_sample.json`
  - 定向测试通过：
    - `pytest -q tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py`
    - `pytest -q tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_probe_supports_future_returns_source`
- 尚未收口:
  - 仍需补齐 S3d 其余窗口 run/test/artifact/review/sync 五件套证据，之后再切换 `final` 为 completed。
