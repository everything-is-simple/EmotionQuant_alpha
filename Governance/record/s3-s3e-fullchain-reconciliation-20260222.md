# S3~S3e 全链路对账归档（run/test/artifact/review/sync）

**归档日期**: 2026-02-22  
**范围**: `S3` / `S3b` / `S3c` / `S3d` / `S3e`  
**目的**: 执行一次跨圈链路对账，形成可追溯证据，不替代各圈 `final/review` 的收口判定。

---

## 1. run 对账

### 1.1 S3d

- `python -m src.pipeline.main --env-file .env mss --date 20260219 --threshold-mode adaptive`
  - 结果: `event=s3d_mss`, `status=ok`
  - 产物: `artifacts/spiral-s3d/20260219/mss_regime_thresholds_snapshot.json`
- `python -m src.pipeline.main --env-file .env mss-probe --start 20260119 --end 20260213 --return-series-source future_returns`
  - 结果: `event=s3d_mss_probe`, `status=ok`, `conclusion=PASS_POSITIVE_SPREAD`
  - 产物: `artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md`

### 1.2 S3c

- `python -m src.pipeline.main --env-file .env irs --date 20260219 --require-sw31`
  - 结果: `event=s3c_irs`, `gate_status=PASS`, `go_nogo=GO`
  - 产物: `artifacts/spiral-s3c/20260219/gate_report.md`

### 1.3 S3e

- `python -m src.pipeline.main --env-file .env validation --trade-date 20260219 --threshold-mode regime --wfa dual-window --export-run-manifest`
  - 结果: `event=s3e_validation`, `final_gate=WARN`, `go_nogo=GO`
  - 产物: `artifacts/spiral-s3e/20260219/validation_run_manifest_sample.json`

### 1.4 S3

- 首次复核:
  - `python -m src.pipeline.main --env-file .env backtest --engine qlib --start 20260218 --end 20260219`
  - 结果: `quality_status=FAIL`, `go_nogo=NO_GO`, `bridge_check_status=FAIL`, `consumed_signal_rows=0`
- 修复性补跑（对账内记录，不改变圈位）:
  - 补跑 `mss/irs/pas/recommend(integrated)` 后重试
  - `python -m src.pipeline.main --env-file .env backtest --engine qlib --start 20260219 --end 20260219`
  - 结果: `quality_status=WARN`, `go_nogo=GO`, `bridge_check_status=PASS`, `consumed_signal_rows=20`, `total_trades=0`
  - 产物: `artifacts/spiral-s3/20260219/gate_report.md`

### 1.5 S3b

- `python -m src.pipeline.main --env-file .env analysis --start 20260219 --end 20260219 --ab-benchmark`
- `python -m src.pipeline.main --env-file .env analysis --date 20260219 --deviation live-backtest`
- `python -m src.pipeline.main --env-file .env analysis --date 20260219 --attribution-summary`
  - 结果: 三条命令均 `status=ok`，`go_nogo=GO`（其中 attribution 为 `quality_status=WARN`）
  - 产物: `artifacts/spiral-s3b/20260219/ab_benchmark_report.md`

---

## 2. test 对账

- 执行命令:
```bash
pytest -q tests/unit/backtest tests/unit/analysis \
  tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py \
  tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py \
  tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py \
  tests/unit/data/test_industry_snapshot_sw31_contract.py \
  tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py \
  tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py \
  tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py \
  tests/unit/algorithms/validation/test_decay_proxy_contract.py \
  tests/unit/pipeline/test_cli_entrypoint.py::test_main_backtest_runs_with_s3a_consumption \
  tests/unit/pipeline/test_cli_entrypoint.py::test_main_analysis_command_wires_to_pipeline \
  tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_probe_supports_future_returns_source \
  tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline \
  tests/unit/pipeline/test_cli_entrypoint.py::test_main_validation_command_wires_to_pipeline
```
- 结果: `34 passed, 2 warnings`

---

## 3. artifact 对账

- 对账脚本校验了 S3~S3e 共 22 个关键产物路径，结果全部 `OK`（文件存在且非零长度）。
- 关键锚点:
  - `artifacts/spiral-s3/20260219/backtest_results.parquet`
  - `artifacts/spiral-s3b/20260219/attribution_summary.json`
  - `artifacts/spiral-s3c/20260219/irs_allocation_coverage_report.md`
  - `artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md`
  - `artifacts/spiral-s3e/20260219/validation_oos_calibration_report.md`

---

## 4. review/final 对账

- `Governance/specs/spiral-s3/{requirements,review,final}.md` 存在，状态 `in_progress`
- `Governance/specs/spiral-s3b/{requirements,review,final}.md` 存在，状态 `in_progress`
- `Governance/specs/spiral-s3c/{requirements,review,final}.md` 存在，状态 `in_progress`
- `Governance/specs/spiral-s3d/{requirements,review,final}.md` 存在，状态 `in_progress`
- `Governance/specs/spiral-s3e/{requirements,review,final}.md` 存在，状态 `in_progress`

---

## 5. sync 对账结论

- 本次完成了 `S3~S3e` 的一次 run/test/artifact/review/sync 全链路对账与归档。
- 本次结论是“**对账完成**”，不是“**圈位全部收口**”。
- 仍待后续圈内收口项:
  - `S3`: 需要继续清理窗口级 `bridge_check_status=FAIL` 场景（如 `20260218-20260219` 首次复核）。
  - `S3b`: `signal/execution/cost` 三分解稳定性复核与 review/final 收口。
  - `S3c/S3d/S3e`: 多窗口 run/test/artifact/review/sync 证据补齐后再切 `completed`。
