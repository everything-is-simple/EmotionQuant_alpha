# S2b Requirements（6A A1/A2）

**Spiral**: S2b  
**状态**: completed  
**最后更新**: 2026-02-21

## 1. A1 Align

- 主目标: 完成 MSS+IRS+PAS 集成推荐完全版闭环，支持四模式集成与推荐硬约束。
- In Scope:
  - 实现 `integrated` 模式推荐路径并落库 `integrated_recommendation`
  - 生成并落库 `quality_gate_report`，输出 `PASS/WARN/FAIL`
  - 强制执行 `contract_version = "nc-v1"` 兼容检查
  - 执行边界 `risk_reward_ratio >= 1.0` 过滤
  - 集成模式覆盖并可追溯：`top_down/bottom_up/dual_verify/complementary`
  - 推荐数量硬约束：每日最多 `20`、单行业最多 `5`
  - 集成输出补齐 A 股可追溯字段：`t1_restriction_hit`、`limit_guard_result`、`session_guard_result`
  - 产出 S2b 证据产物：`integrated_recommendation_sample.parquet`、`quality_gate_report.md`、`s2_go_nogo_decision.md`
  - 补齐 S2b 目标测试（Integration/Quality Gate/CLI）
- Out Scope:
  - S3 回测引擎实现与执行层下单链路

## 2. A2 Architect

- CP Slice: `CP-05`（1 个 Slice）
- 跨模块契约:
  - 输入:
    - `mss_panorama`（MSS）
    - `irs_industry_daily`（IRS）
    - `stock_pas_daily`（PAS）
    - `validation_gate_decision`（Validation Gate）
  - 输出:
    - `integrated_recommendation`
    - `quality_gate_report`
    - `s2_go_nogo_decision.md`（证据）
  - 命名/契约约束:
    - `contract_version = "nc-v1"`
    - `pas_direction` 使用 `bullish/bearish/neutral`
    - `risk_reward_ratio` 为执行边界字段，`<1.0` 必须过滤
    - `integration_mode in {top_down,bottom_up,dual_verify,complementary}`
    - 推荐硬约束：每日 `<=20`、单行业 `<=5`
- 失败策略:
  - `validation_gate_decision.final_gate = FAIL` 时，质量门必须 `status=FAIL` 且 `go_nogo=NO_GO`
  - 输入缺失或契约版本不兼容判定 `P0`，阻断 S2b 收口

## 3. 本圈最小证据定义

- run:
  - `python -m src.pipeline.main --env-file .tmp/.env.s2b.artifacts recommend --date 20260218 --mode integrated --integration-mode top_down`
  - `python -m src.pipeline.main --env-file .tmp/.env.s2b.artifacts recommend --date 20260218 --mode integrated --integration-mode bottom_up`
  - `python -m src.pipeline.main --env-file .tmp/.env.s2b.artifacts recommend --date 20260218 --mode integrated --integration-mode dual_verify`
  - `python -m src.pipeline.main --env-file .tmp/.env.s2b.artifacts recommend --date 20260218 --mode integrated --integration-mode complementary`
- test:
  - `python -m pytest -q tests/unit/config/test_env_docs_alignment.py`
  - `python -m pytest -q tests/unit/integration/test_integration_contract.py tests/unit/integration/test_quality_gate_contract.py`
  - `python -m pytest -q tests/unit/integration/test_algorithm_semantics_regression.py`
  - `python -m pytest -q tests/unit/pipeline/test_cli_entrypoint.py`
- artifact:
  - `Governance/specs/spiral-s2b/integrated_recommendation_sample.parquet`
  - `Governance/specs/spiral-s2b/quality_gate_report.md`
  - `Governance/specs/spiral-s2b/s2_go_nogo_decision.md`
  - `Governance/specs/spiral-s2b/error_manifest_sample.json`
- review/final:
  - `Governance/specs/spiral-s2b/review.md`
  - `Governance/specs/spiral-s2b/final.md`
