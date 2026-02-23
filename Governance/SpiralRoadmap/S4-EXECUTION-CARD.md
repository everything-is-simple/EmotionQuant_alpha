# S4 执行卡（v0.2）

**状态**: Completed  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S4（纸上交易闭环）

---

## 1. 目标

- 打通 `signal -> order -> position -> risk` 纸上交易可回放闭环。
- 严格落实 A 股执行约束（T+1、涨跌停、交易时段）和 `risk_reward_ratio >= 1.0` 门槛。
- 形成可被 S3b 消费的真实执行证据链。

---

## 2. run

```bash
eq trade --mode paper --date {trade_date}
```

---

## 3. test

```bash
pytest tests/unit/trading/test_order_pipeline_contract.py -q
pytest tests/unit/trading/test_position_lifecycle_contract.py -q
pytest tests/unit/trading/test_risk_guard_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s4/{trade_date}/trade_records_sample.parquet`
- `artifacts/spiral-s4/{trade_date}/positions_sample.parquet`
- `artifacts/spiral-s4/{trade_date}/risk_events_sample.parquet`
- `artifacts/spiral-s4/{trade_date}/paper_trade_replay.md`
- `artifacts/spiral-s4/{trade_date}/consumption.md`
- `artifacts/spiral-s4/{trade_date}/gate_report.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s4/review.md`
- 必填结论：
  - 订单到持仓变更链路是否可完整回放
  - 跌停不可卖、次日重试等关键边界是否可验证
  - S3 输入消费证据是否完整且可审计

---

## 6. sync

- `Governance/specs/spiral-s4/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 `gate = FAIL` 或回放链路断裂：状态置 `blocked`，进入 `S4r` 修复子圈，不推进 S3b。
- 若契约/治理检查失败：先修复并补齐回归证据，再重跑 S4 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-18）

- 已完成 S4 收口：`artifacts/spiral-s4/20260222/` 形成完整 run/test/artifact 证据链，`quality_status=WARN`、`go_nogo=GO`。
- 已验证跨日持仓关键边界：跌停不可卖阻断与次日重试卖出可回放。
- 下一步：进入 S3b（收益归因验证闭环）。
