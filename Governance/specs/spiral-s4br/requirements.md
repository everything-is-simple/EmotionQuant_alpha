# S4br Requirements（6A A1/A2）

**Spiral**: S4br  
**状态**: completed  
**最后更新**: 2026-02-23

## 1. A1 Align

- 主目标: 固化 S4br 修复子圈执行能力，保证极端防御 FAIL 场景可“只修不扩”并返回 S4b 重验。
- In Scope:
  - 支持 `eq stress --scenario all --date {trade_date} --repair s4br`
  - 输出 `s4br_patch_note.md` 与 `s4br_delta_report.md`
  - 保留 S4b 原有压力产物契约不变
- Out Scope:
  - 新增压力场景模型
  - 改写 S4b 基础防御语义

## 2. A2 Architect

- CP Slice: `CP-07 + CP-09`（修复子圈，1 Slice）
- 关联执行卡: `Governance/SpiralRoadmap/execution-cards/S4BR-EXECUTION-CARD.md`
- 跨模块契约:
  - 输入:
    - `positions`
    - `live_backtest_deviation`
  - 输出:
    - `artifacts/spiral-s4br/{trade_date}/s4br_patch_note.md`
    - `artifacts/spiral-s4br/{trade_date}/s4br_delta_report.md`
    - `artifacts/spiral-s4br/{trade_date}/gate_report.md`
    - `artifacts/spiral-s4br/{trade_date}/consumption.md`
  - 边界:
    - `contract_version = "nc-v1"`
    - 仅允许 `repair = s4br`

## 3. 本圈最小证据定义

- run:
  - `eq --env-file artifacts/spiral-s4b/20260213/closeout_env/.env.s4b.cross_window stress --scenario all --date 20260213 --repair s4br`
- test:
  - `pytest tests/unit/trading/test_stress_limit_down_chain.py -q`
  - `pytest tests/unit/trading/test_stress_liquidity_dryup.py -q`
  - `pytest tests/unit/trading/test_deleveraging_policy_contract.py -q`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s4br/20260213/extreme_defense_report.md`
  - `artifacts/spiral-s4br/20260213/deleveraging_policy_snapshot.json`
  - `artifacts/spiral-s4br/20260213/stress_trade_replay.csv`
  - `artifacts/spiral-s4br/20260213/s4br_patch_note.md`
  - `artifacts/spiral-s4br/20260213/s4br_delta_report.md`
  - `artifacts/spiral-s4br/20260213/consumption.md`
  - `artifacts/spiral-s4br/20260213/gate_report.md`

