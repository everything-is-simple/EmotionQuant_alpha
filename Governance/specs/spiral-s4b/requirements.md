# S4b Requirements（6A A1/A2）

**Spiral**: S4b  
**状态**: completed  
**最后更新**: 2026-02-22

## A1 Align

- 主目标: 完成极端防御专项闭环，验证 `limit_down_chain` 与 `liquidity_dryup` 两类压力场景下的去杠杆行为与可回放证据。
- In Scope:
  - `eq stress --scenario {limit_down_chain|liquidity_dryup|all} --date {trade_date}`
  - `eq stress --scenario all --date {trade_date} --repair s4br`（条件触发入口）
  - 固化 `extreme_defense_report / deleveraging_policy_snapshot / stress_trade_replay / consumption / gate_report`
- Out Scope:
  - S5 监控层实现
  - GUI 可视化实现

## A2 Architect

- 关联执行卡: `Governance/SpiralRoadmap/execution-cards/S4B-EXECUTION-CARD.md`
- 依赖输入:
  - `trade_records` / `positions`（S4 纸上交易）
  - `live_backtest_deviation`（S3b 偏差分解输入）
- 输出产物:
  - `artifacts/spiral-s4b/{trade_date}/extreme_defense_report.md`
  - `artifacts/spiral-s4b/{trade_date}/deleveraging_policy_snapshot.json`
  - `artifacts/spiral-s4b/{trade_date}/stress_trade_replay.csv`
  - `artifacts/spiral-s4b/{trade_date}/consumption.md`
  - `artifacts/spiral-s4b/{trade_date}/gate_report.md`
- 目标测试:
  - `tests/unit/trading/test_stress_limit_down_chain.py`
  - `tests/unit/trading/test_stress_liquidity_dryup.py`
  - `tests/unit/trading/test_deleveraging_policy_contract.py`
  - `tests/unit/pipeline/test_cli_entrypoint.py::test_main_stress_command_wires_to_pipeline`
