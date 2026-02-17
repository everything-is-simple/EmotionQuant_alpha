# S2c Requirements（6A A1/A2）

**Spiral**: S2c  
**状态**: in_progress  
**最后更新**: 2026-02-17

## 1. A1 Align

- 主目标: 完成 S2c「桥接硬门禁 + 语义收口」双目标中的首个 P0 子目标，并锁定后续 full 语义补齐路径。
- In Scope（本次已执行）:
  - Validation 输出增加 `selected_weight_plan`，并持久化 `validation_weight_plan`。
  - Integration 增加 `--with-validation-bridge` 桥接硬门禁。
  - 桥接链路一致性落库与验证：`selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id`。
  - Gate 语义回归：`final_gate=FAIL` 必阻断，`mss_cycle=unknown` 正向高分回退到 `HOLD`。
  - 目标测试补齐并通过：`test_weight_plan_bridge_contract.py`、`test_validation_weight_plan_bridge.py`、`test_algorithm_semantics_regression.py`。
  - MSS 语义补齐起步：`ratio -> zscore -> [0,100]`、`total_stocks<=0` 回退 50 分、新增 `mss_factor_intermediate_sample.parquet` 产物与合同测试。
  - 设计溯源机制：核心模块新增 `DESIGN_TRACE` 标记，并纳入本地质量门禁自动检查。
- Out Scope（本次未完成）:
  - MSS/IRS/PAS/Validation full 语义实现（六因子/三因子/Walk-Forward）。
  - Validation 五件套中 `validation_factor_report`、`validation_weight_report`、`validation_run_manifest` 的当日真实产出。
  - S2c 最终收口（A5/A6 completed）。

## 2. A2 Architect

- CP Slice:
  - 当前子步: `CP-10 + CP-05`（Validation-Integration 桥接硬门禁）
  - 下一子步: `CP-02 + CP-03 + CP-04 + CP-10 + CP-05`（full 语义补齐）
- 跨模块契约:
  - 输入:
    - `validation_gate_decision.final_gate/selected_weight_plan/contract_version`
    - `validation_weight_plan.plan_id/w_mss/w_irs/w_pas/contract_version`
    - `mss_panorama`、`irs_industry_daily`、`stock_pas_daily`
  - 输出:
    - `integrated_recommendation.weight_plan_id/w_mss/w_irs/w_pas`
    - `quality_gate_report.status/go_nogo/message`
  - 命名/边界约束:
    - `contract_version = "nc-v1"`
    - `risk_reward_ratio >= 1.0`
    - 桥接缺失/不一致必须 `FAIL + NO_GO`
- 失败策略:
  - `selected_weight_plan` 缺失、`plan_id` 不可解析、权重非法（和偏差/负值）统一阻断。
  - `final_gate=FAIL` 直接阻断，不允许降级放行到 S3a/S3。

## 3. 本圈最小证据定义（当前子步）

- run:
  - `python -m src.pipeline.main --env-file artifacts/spiral-s2c/20260218/.env.s2c.demo recommend --date 20260218 --mode integrated --with-validation --with-validation-bridge`
- test:
  - `python -m pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q`
  - `python -m pytest tests/unit/integration/test_validation_weight_plan_bridge.py -q`
  - `python -m pytest tests/unit/integration/test_algorithm_semantics_regression.py -q`
  - `python -m pytest tests/unit/integration/test_validation_gate_contract.py tests/unit/integration/test_integration_contract.py tests/unit/integration/test_quality_gate_contract.py -q`
  - `python -m pytest tests/unit/algorithms/mss/test_mss_engine.py tests/unit/algorithms/mss/test_mss_contract.py tests/unit/algorithms/mss/test_mss_full_semantics_contract.py -q`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `Governance/specs/spiral-s2c/mss_factor_intermediate_sample.parquet`
  - `Governance/specs/spiral-s2c/validation_weight_plan_sample.parquet`
  - `Governance/specs/spiral-s2c/validation_gate_decision_sample.parquet`
  - `Governance/specs/spiral-s2c/integrated_recommendation_sample.parquet`
  - `Governance/specs/spiral-s2c/quality_gate_report.md`
  - `Governance/specs/spiral-s2c/s2_go_nogo_decision.md`
  - `Governance/specs/spiral-s2c/run.log`
