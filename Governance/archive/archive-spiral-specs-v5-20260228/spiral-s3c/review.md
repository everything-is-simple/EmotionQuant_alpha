# S3c Review（6A A4/A5）

**Spiral**: S3c  
**状态**: completed  
**复盘日期**: 2026-02-22

- 本轮窗口：`20260210`、`20260211`、`20260212`、`20260213`
- Run：
  - `eq run --date {trade_date} --to-l2 --strict-sw31`（四窗）全部成功，`industry_snapshot_count=31`。
  - `eq irs --date {trade_date} --require-sw31`（四窗）全部成功，`irs_industry_count=31`，`gate_status=PASS`，`go_nogo=GO`。
- Test：
  - `tests/unit/data/test_industry_snapshot_sw31_contract.py` 通过。
  - `tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py` 通过。
  - `tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline` 通过。
- Artifact：
  - `artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.json`
  - `artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.md`
  - `artifacts/spiral-s3c/20260213/cross_window/20260210/*`
  - `artifacts/spiral-s3c/20260213/cross_window/20260211/*`
  - `artifacts/spiral-s3c/20260213/cross_window/20260212/*`
  - `artifacts/spiral-s3c/20260213/cross_window/20260213/*`

## 结论

- SW31 映射：跨窗口全部通过（31 行业，未出现 `ALL` 主流程输入）。
- IRS 全覆盖：跨窗口全部通过（`output_industry_count=31`，`allocation_missing_count=0`）。
- 当前圈状态：`completed`（S3b 已完成，且 S3c 跨窗口复核与证据链已闭环）。
