# S2c Requirements（6A A1/A2）

**Spiral**: S2c  
**状态**: completed  
**最后更新**: 2026-02-17

## 1. A1 Align

- 主目标: 完成 S2c 收口清障，解决证据冲突并建立 release/debug 证据隔离，形成可审计单一正式口径。
- In Scope（本轮已执行）:
  - `evidence_lane` 参数接入 `eq recommend`，支持 `release/debug` 两条证据车道。
  - S2c 产物分流：`artifacts/spiral-s2c/{trade_date}`（release）与 `artifacts/spiral-s2c-debug/{trade_date}`（debug）。
  - 新增 release 证据同步脚本：`scripts/quality/sync_s2c_release_artifacts.py`，同步前校验 PASS/GO 与样例行数。
  - 补齐 S2c 收口文档：`s2c_semantics_traceability_matrix.md`、`s2c_algorithm_closeout.md`。
- Out Scope（本轮未完成）:
  - S3/S4 回测交易链路。
  - S3a ENH-10 功能实现。

## 2. A2 Architect

- CP Slice:
  - 当前子步: `CP-10 + CP-05`（证据口径收口与桥接证据治理）
  - 承接基线: `CP-02 + CP-03 + CP-04 + CP-10 + CP-05`（核心语义与桥接硬门禁）
- 跨模块契约:
  - 输入:
    - `industry_snapshot`（IRS 语义字段 + 质量字段）
    - `stock_gene_cache`（PAS 语义字段）
    - `mss_panorama`、`validation_gate_decision`、`validation_weight_plan`
  - 输出:
    - `irs_industry_daily` + `irs_factor_intermediate`
    - `stock_pas_daily` + `pas_factor_intermediate`
    - `validation_factor_report` / `validation_weight_report` / `validation_gate_decision` / `validation_weight_plan` / `validation_run_manifest`
  - 命名/边界约束:
    - `contract_version = "nc-v1"`
    - `risk_reward_ratio >= 1.0`
    - `rotation_status in {IN, OUT, HOLD}`
    - `direction in {bullish, bearish, neutral}`
    - `quality_flag in {normal, cold_start, stale}`
    - 正式收口证据只认 `evidence_lane=release`
- 失败策略:
  - 输入数据缺失或契约字段非法：`FAIL + NO_GO`。
  - `final_gate=FAIL` 必阻断，不允许降级放行到 S3a/S3。

## 3. 本圈最小证据定义（当前子步）

- run:
  - `python -m src.pipeline.main --env-file artifacts/spiral-s2c/20260218/.env.s2c.demo recommend --date 20260218 --mode integrated --with-validation-bridge --evidence-lane release`
  - `python -m scripts.quality.sync_s2c_release_artifacts --trade-date 20260218`
- test:
  - `python -m pytest tests/unit/pipeline/test_recommend_evidence_lane.py -q`
  - `python -m pytest tests/unit/scripts/test_sync_s2c_release_artifacts.py -q`
  - `python -m pytest tests/unit/algorithms/irs/test_irs_full_semantics_contract.py -q`
  - `python -m pytest tests/unit/algorithms/pas/test_pas_full_semantics_contract.py -q`
  - `python -m pytest tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py -q`
  - `python -m pytest tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py -q`
  - `python -m pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q`
  - `python -m pytest tests/unit/integration/test_validation_weight_plan_bridge.py -q`
  - `python -m pytest tests/unit/integration/test_algorithm_semantics_regression.py -q`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s2c/{trade_date}/irs_factor_intermediate_sample.parquet`
  - `artifacts/spiral-s2c/{trade_date}/pas_factor_intermediate_sample.parquet`
  - `artifacts/spiral-s2c/{trade_date}/validation_factor_report_sample.parquet`
  - `artifacts/spiral-s2c/{trade_date}/validation_weight_report_sample.parquet`
  - `artifacts/spiral-s2c/{trade_date}/validation_weight_plan_sample.parquet`
  - `artifacts/spiral-s2c/{trade_date}/validation_run_manifest_sample.json`
  - `artifacts/spiral-s2c/{trade_date}/s2c_semantics_traceability_matrix.md`
  - `artifacts/spiral-s2c/{trade_date}/s2c_algorithm_closeout.md`
