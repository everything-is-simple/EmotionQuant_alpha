# S3d Review（6A A4/A5）

**Spiral**: S3d  
**状态**: completed  
**复盘日期**: 2026-02-22（A4 阶段）

- 当前状态: 已完成窗口级实跑证据闭环并收口。
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
## 跨窗口补证（2026-02-22）

- Adaptive 阈值窗口（4 日）：
  - `20260210/20260211/20260212/20260213` 均 `gate_result=PASS`，`mss_panorama_count=1`。
- future_returns probe 窗口（4 组）：
  - `20260119-20260213`: `PASS_POSITIVE_SPREAD`
  - `20260126-20260213`: `PASS_POSITIVE_SPREAD`
  - `20260203-20260213`: `WARN_NEGATIVE_SPREAD`
  - `20260206-20260213`: `WARN_FLAT_SPREAD`
- 边界样本（记录不阻断）：
  - `20260210-20260213` 出现 `P1/future_returns_series_missing`，已固化为短窗口样本不足边界。
- 汇总证据：
  - `artifacts/spiral-s3d/20260213/s3d_cross_window_summary.json`
  - `artifacts/spiral-s3d/20260213/s3d_cross_window_summary.md`
  - `artifacts/spiral-s3d/20260213/cross_window/*`

## 结论

- S3d 主目标（adaptive 阈值 + future_returns probe）已完成跨窗口 run/test/artifact/review/sync 闭环，可标记 completed。
