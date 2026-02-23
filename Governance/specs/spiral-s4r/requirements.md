# S4r Requirements（6A A1/A2）

**Spiral**: S4r  
**状态**: completed  
**最后更新**: 2026-02-23

## 1. A1 Align

- 主目标: 在不扩展交易功能的前提下，落地 `S4r` 修复子圈并形成可审计 patch/delta 证据链。
- In Scope:
  - 支持 `eq trade --mode paper --date {trade_date} --repair s4r`
  - 输出 `s4r_patch_note.md` 与 `s4r_delta_report.md`
  - 保持 S4 原有订单/持仓/风控产物契约不变
  - 修复历史 `trade_records` 旧 schema 写入阻断（缺列自动补齐）
- Out Scope:
  - 新增交易策略
  - 变更 S4 交易语义（T+1、涨跌停、RR 门槛）

## 2. A2 Architect

- CP Slice: `CP-07 + CP-09`（修复子圈，1 Slice）
- 关联执行卡: `Governance/SpiralRoadmap/S4R-EXECUTION-CARD.md`
- 跨模块契约:
  - 输入:
    - `backtest_results`
    - `quality_gate_report`
    - `integrated_recommendation`
  - 输出:
    - `artifacts/spiral-s4r/{trade_date}/s4r_patch_note.md`
    - `artifacts/spiral-s4r/{trade_date}/s4r_delta_report.md`
    - `artifacts/spiral-s4r/{trade_date}/gate_report.md`
    - `artifacts/spiral-s4r/{trade_date}/consumption.md`
  - 边界:
    - `contract_version = "nc-v1"`
    - `risk_reward_ratio >= 1.0`

## 3. 本圈最小证据定义

- run:
  - `eq --env-file artifacts/spiral-s4b/20260213/closeout_env/.env.s4b.cross_window trade --mode paper --date 20260213 --repair s4r`
- test:
  - `pytest tests/unit/trading/test_order_pipeline_contract.py -q`
  - `pytest tests/unit/trading/test_risk_guard_contract.py -q`
  - `pytest tests/unit/trading/test_backtest_status_schema_compat_contract.py -q`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s4r/20260213/trade_records_sample.parquet`
  - `artifacts/spiral-s4r/20260213/positions_sample.parquet`
  - `artifacts/spiral-s4r/20260213/risk_events_sample.parquet`
  - `artifacts/spiral-s4r/20260213/paper_trade_replay.md`
  - `artifacts/spiral-s4r/20260213/s4r_patch_note.md`
  - `artifacts/spiral-s4r/20260213/s4r_delta_report.md`
  - `artifacts/spiral-s4r/20260213/consumption.md`
  - `artifacts/spiral-s4r/20260213/gate_report.md`

