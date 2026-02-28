# S3c Final（6A 收口）

**Spiral**: S3c  
**状态**: completed  
**收口日期**: 2026-02-22

- 跨窗口复核（非单窗口）已完成，窗口集：
  - `20260210`
  - `20260211`
  - `20260212`
  - `20260213`
- 跨窗口结论：
  - `eq run --to-l2 --strict-sw31`：四窗均 `industry_snapshot_count=31`。
  - `eq irs --require-sw31`：四窗均 `irs_industry_count=31`，`gate_status=PASS`，`go_nogo=GO`。
  - `all_sw31_coverage_pass=true`，满足 S3c 收口门禁。

## 收口证据
1. 总览：
   - `artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.json`
   - `artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.md`
2. 窗口级快照（防覆盖）：
   - `artifacts/spiral-s3c/20260213/cross_window/20260210/*`
   - `artifacts/spiral-s3c/20260213/cross_window/20260211/*`
   - `artifacts/spiral-s3c/20260213/cross_window/20260212/*`
   - `artifacts/spiral-s3c/20260213/cross_window/20260213/*`

## 质量门
1. 目标测试通过：
   - `tests/unit/data/test_industry_snapshot_sw31_contract.py`
   - `tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py`
   - `tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline`
2. 治理检查通过：
   - `python -m scripts.quality.local_quality_check --contracts --governance`
