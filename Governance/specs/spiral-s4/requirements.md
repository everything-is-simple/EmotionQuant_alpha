# S4 Requirements（6A A1/A2）

**Spiral**: S4  
**状态**: completed  
**最后更新**: 2026-02-18

## 1. A1 Align

- 主目标: 完成 S4 纸上交易闭环收口，交付跨日持仓生命周期与跌停不可卖次日重试可回放证据。
- In Scope:
  - 实现 `eq trade --mode paper --date {trade_date}`
  - 强制消费 S3 `backtest_results` 门禁（`quality_status in {PASS,WARN}` + `go_nogo=GO`）
  - 强制消费当日 `quality_gate_report`（`status != FAIL`）
  - 基于 `integrated_recommendation` 生成最小订单/持仓/风控事件
  - 输出交易产物：`trade_records_sample.parquet`、`positions_sample.parquet`、`risk_events_sample.parquet`
  - 输出证据链：`paper_trade_replay.md`、`consumption.md`、`gate_report.md`
  - 覆盖跨日边界：`持仓冻结 -> 跌停阻断 -> 次日重试`
- Out Scope:
  - S3b 收益归因三分解
  - S4b 极端防御专项
  - 券商实盘接入与撮合回报消费

## 2. A2 Architect

- CP Slice: `CP-07 + CP-09`（1-2 Slice）
- 跨模块契约:
  - 输入:
    - `backtest_results`
    - `quality_gate_report`
    - `integrated_recommendation`
    - `raw_daily`
    - `raw_trade_cal`
  - 输出:
    - `trade_records`
    - `positions`
    - `risk_events`
    - `paper_trade_replay.md`
    - `consumption.md`
    - `gate_report.md`
  - 命名/边界约束:
    - `contract_version = "nc-v1"`
    - `risk_reward_ratio >= 1.0`
    - T+1 字段可追溯：`can_sell_date`、`is_frozen`
- 失败策略:
  - S3 回测门禁未通过：`P0` 阻断
  - 当日质量门为 `FAIL`：`P0` 阻断
  - 信号为空/契约版本不匹配：`P0` 阻断

## 3. 本圈最小证据定义

- run:
  - `eq --env-file artifacts/spiral-s4/20260222/closeout_env_v3/.env.s4.closeout trade --mode paper --date 20260222`
- test:
  - `manual deterministic assertions`（与 `tests/unit/trading/*` 目标断言等价）
  - `artifacts/spiral-s4/20260222/manual_test_summary.md`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s4/20260222/trade_records_sample.parquet`
  - `artifacts/spiral-s4/20260222/positions_sample.parquet`
  - `artifacts/spiral-s4/20260222/risk_events_sample.parquet`
  - `artifacts/spiral-s4/20260222/paper_trade_replay.md`
  - `artifacts/spiral-s4/20260222/consumption.md`
  - `artifacts/spiral-s4/20260222/gate_report.md`
  - `artifacts/spiral-s4/20260222/run.log`
  - `artifacts/spiral-s4/20260222/test.log`
- review/final:
  - `Governance/specs/spiral-s4/review.md`
  - `Governance/specs/spiral-s4/final.md`
