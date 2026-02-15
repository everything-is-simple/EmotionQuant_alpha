# S2a Requirements（6A A1/A2）

**Spiral**: S2a  
**状态**: completed  
**最后更新**: 2026-02-15

## 1. A1 Align

- 主目标: 完成 IRS + PAS + Validation 最小闭环，支持 `eq recommend --date {trade_date} --mode mss_irs_pas --with-validation`。
- In Scope:
  - 实现 `eq recommend --date {trade_date} --mode mss_irs_pas --with-validation` 可执行路径
  - 产出并落库 `irs_industry_daily`
  - 产出并落库 `stock_pas_daily`
  - 产出并落库 `validation_gate_decision`
  - 验证 `validation_gate_decision.contract_version = "nc-v1"`
  - 失败门禁确保 `validation_prescription` 非空
  - 补齐 S2a 目标测试（IRS/PAS/Validation）
- Out Scope:
  - S2b 集成推荐输出（`integrated_recommendation`）
  - 真实 SW 行业映射、真实收益口径校准
  - Validation 完整因子有效性与权重计划迭代

## 2. A2 Architect

- CP Slice: `CP-03`, `CP-04`, `CP-10`（3 个 Slice）
- 跨模块契约:
  - 输入:
    - `industry_snapshot`（IRS 最小输入）
    - `raw_daily`（PAS 最小输入）
    - `mss_panorama`（Validation 追溯输入）
  - 输出:
    - `irs_industry_daily`（至少 1 条）
    - `stock_pas_daily`（至少 1 条）
    - `validation_gate_decision`（至少 1 条）
  - 命名/契约约束:
    - `contract_version = "nc-v1"`
    - `risk_reward_ratio` 作为执行边界字段保留
    - `pas_direction` 使用 `bullish/bearish/neutral`
- 失败策略:
  - 任一上游输入缺失判定 `P0`，阻断收口
  - Gate=FAIL 时必须写 `validation_prescription`

## 3. 本圈最小证据定义

- run:
  - `python -m src.pipeline.main --env-file none recommend --date 20260218 --mode mss_irs_pas --with-validation`
- test:
  - `python -m pytest -q tests/unit/config/test_dependency_manifest.py`
  - `python -m pytest -q tests/unit/algorithms/irs/test_irs_contract.py tests/unit/algorithms/pas/test_pas_contract.py tests/unit/integration/test_validation_gate_contract.py`
- artifact:
  - `Governance/specs/spiral-s2a/irs_industry_daily_sample.parquet`
  - `Governance/specs/spiral-s2a/stock_pas_daily_sample.parquet`
  - `Governance/specs/spiral-s2a/validation_gate_decision_sample.parquet`
  - `Governance/specs/spiral-s2a/error_manifest_sample.json`
- review/final:
  - `Governance/specs/spiral-s2a/review.md`
  - `Governance/specs/spiral-s2a/final.md`
