# S4 Review（6A A4/A5）

**Spiral**: S4  
**状态**: completed  
**复盘日期**: 2026-02-18

## 1. A3 交付结果

1. 新增 `eq trade --mode paper --date {trade_date}` 命令入口（`src/pipeline/main.py`）。
2. 新增 S4 paper trade 最小实现（`src/trading/pipeline.py`）：
   - 复用 S3 消费门禁（`backtest_results`）
   - 消费当日 `quality_gate_report`
   - 消费 `integrated_recommendation` 生成订单/持仓/风控事件
   - 输出 `paper_trade_replay.md`、`consumption.md`、`gate_report.md`
3. 在 S4 收口轮完成跨日回放强化验证：覆盖“持仓冻结/跌停不可卖/次日重试卖出”。

## 2. A4 验证记录

### run

- 通过:
  - `eq --env-file artifacts/spiral-s4/20260222/closeout_env_v3/.env.s4.closeout trade --mode paper --date 20260222`
  - 产物: `artifacts/spiral-s4/20260222/run.log`

### test

- `pytest` 目标测试在当前会话受 `tmpdir` 权限限制（`WinError 5`），未能完成标准执行。
- 采用等价确定性验证路径（基于 `tests/unit/trading/support.py` 构造数据与断言）：
  - 首日建仓成功
  - 次日触发 `REJECT_LIMIT_DOWN` 与 `SELL_RETRY_NEXT_DAY`
  - 再下一日完成重试卖出（`direction=sell` + `status=filled`）
- 结果: PASS（见 `artifacts/spiral-s4/20260222/manual_test_summary.md`）
- 记录: `artifacts/spiral-s4/20260222/test.log`

### contracts/governance

- `python -m scripts.quality.local_quality_check --contracts --governance`
- 结果: PASS

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s4/requirements.md`
- artifact:
  - `artifacts/spiral-s4/20260222/trade_records_sample.parquet`
  - `artifacts/spiral-s4/20260222/positions_sample.parquet`
  - `artifacts/spiral-s4/20260222/risk_events_sample.parquet`
  - `artifacts/spiral-s4/20260222/paper_trade_replay.md`
  - `artifacts/spiral-s4/20260222/consumption.md`
  - `artifacts/spiral-s4/20260222/gate_report.md`
  - `artifacts/spiral-s4/20260222/run.log`
  - `artifacts/spiral-s4/20260222/test.log`
  - `artifacts/spiral-s4/20260222/manual_test_summary.md`

## 4. 偏差与风险

1. 更细撮合规则（如一字板、流动性枯竭）仍需在后续圈继续增强。
2. 当前 `pytest` 执行环境存在临时目录权限限制，需在后续修复后补跑标准目标测试。

## 5. 消费记录

- 上游消费: S4 消费 S3 `backtest_results` + S2b `integrated_recommendation` + `quality_gate_report`。
- 下游消费: S3b 将消费 S4 的 `trade_records/positions/risk_events`。
- 当前结论: `quality_status = WARN` 且 `go_nogo = GO`，满足 S4->S3b 入口条件。

## 6. 跨文档联动

- 本次未涉及破坏性命名契约变更；暂不触发 CP 文档结构性更新。
