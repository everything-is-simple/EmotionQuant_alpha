# S2c 语义溯源矩阵（release）

- trade_date: 20260218
- evidence_lane: release
- artifacts_dir: artifacts/spiral-s2c/20260218
- 目标: 对齐 `设计 -> 实现 -> 测试 -> 产物`，作为 S2c 收口证据。

| 模块 | 设计锚点 | 实现文件 | 合同/回归测试 | 产物 |
|---|---|---|---|---|
| MSS | `docs/design/core-algorithms/mss/mss-algorithm.md` | `src/algorithms/mss/pipeline.py` | `tests/unit/algorithms/mss/test_mss_full_semantics_contract.py` | `artifacts/spiral-s2c/20260218/mss_factor_intermediate_sample.parquet` |
| IRS | `docs/design/core-algorithms/irs/irs-algorithm.md` | `src/algorithms/irs/pipeline.py` | `tests/unit/algorithms/irs/test_irs_full_semantics_contract.py` | `artifacts/spiral-s2c/20260218/irs_factor_intermediate_sample.parquet` |
| PAS | `docs/design/core-algorithms/pas/pas-algorithm.md` | `src/algorithms/pas/pipeline.py` | `tests/unit/algorithms/pas/test_pas_full_semantics_contract.py` | `artifacts/spiral-s2c/20260218/pas_factor_intermediate_sample.parquet` |
| Validation | `docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md` | `src/algorithms/validation/pipeline.py` | `tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py`, `tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py`, `tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py` | `artifacts/spiral-s2c/20260218/validation_factor_report_sample.parquet`, `artifacts/spiral-s2c/20260218/validation_weight_report_sample.parquet`, `artifacts/spiral-s2c/20260218/validation_weight_plan_sample.parquet`, `artifacts/spiral-s2c/20260218/validation_run_manifest_sample.json` |
| Integration | `docs/design/core-algorithms/integration/integration-algorithm.md` | `src/integration/pipeline.py`, `src/pipeline/recommend.py` | `tests/unit/integration/test_validation_weight_plan_bridge.py`, `tests/unit/integration/test_algorithm_semantics_regression.py`, `tests/unit/integration/test_quality_gate_contract.py` | `artifacts/spiral-s2c/20260218/integrated_recommendation_sample.parquet`, `artifacts/spiral-s2c/20260218/quality_gate_report.md`, `artifacts/spiral-s2c/20260218/s2_go_nogo_decision.md` |

## 桥接硬门禁结论

- 链路: `selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id`
- 结论: PASS（release 证据链中可审计，未发生桥接缺失放行）。

## 证据口径说明

- 正式证据仅认 `release` 目录。
- `debug` 目录用于测试/演练，不进入 `Governance/specs/spiral-s2c` 收口证据。
