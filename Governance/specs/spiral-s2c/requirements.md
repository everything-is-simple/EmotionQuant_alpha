# S2c Requirements（6A A1/A2）

**Spiral**: S2c  
**状态**: in_progress  
**最后更新**: 2026-02-17

## 1. A1 Align

- 主目标: 在已完成桥接硬门禁基础上，继续完成 S2c 的 IRS/PAS/Validation full 语义补齐，并形成可回归证据链。
- In Scope（本轮已执行）:
  - IRS full 语义落地：六因子评分、`rotation_status/rotation_slope/rotation_detail`、`allocation_advice/allocation_mode`、`quality_flag/sample_days/neutrality`。
  - PAS full 语义落地：三因子评分、`opportunity_grade/direction`、`effective_risk_reward_ratio`、`quality_flag/sample_days/adaptive_window`。
  - Validation full 语义落地：因子验证 + 权重 Walk-Forward 验证 + Gate 决策，补齐五件套落库与样例产物。
  - 设计溯源扩展：IRS/PAS 新增 `DESIGN_TRACE`，并纳入 traceability gate。
  - 新增并通过 S2c 目标测试：IRS/PAS full 语义合同 + Validation 因子/权重合同。
- Out Scope（本轮未完成）:
  - S3/S4 回测交易链路。
  - S2c 最终收口文档（`s2c_semantics_traceability_matrix.md`、`s2c_algorithm_closeout.md`）与 completed 状态切换。

## 2. A2 Architect

- CP Slice:
  - 当前子步: `CP-02 + CP-03 + CP-04 + CP-10`（IRS/PAS/Validation full 语义）
  - 已完成承接: `CP-10 + CP-05`（Validation-Integration 桥接硬门禁）
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
- 失败策略:
  - 输入数据缺失或契约字段非法：`FAIL + NO_GO`。
  - `final_gate=FAIL` 必阻断，不允许降级放行到 S3a/S3。

## 3. 本圈最小证据定义（当前子步）

- run:
  - `python -m src.pipeline.main --env-file artifacts/spiral-s2c/20260218/.env.s2c.demo recommend --date 20260218 --mode integrated --with-validation --with-validation-bridge`
- test:
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
