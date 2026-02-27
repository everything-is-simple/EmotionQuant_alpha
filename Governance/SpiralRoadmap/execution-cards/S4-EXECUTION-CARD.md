# S4 执行卡（v0.3）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-25  
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

**RejectReason 核心路径覆盖**（对齐 `trading-data-models.md` §6.5）：
至少覆盖 `REJECT_LIMIT_UP`、`REJECT_T1_FROZEN`、`REJECT_MAX_POSITION`、`REJECT_NO_CASH` 四条核心拒单路径，每条至少 1 个测试用例命中。

**TradingState 全覆盖**：
`normal/warn_data_fallback/blocked_gate_fail/blocked_untradable` 四种状态至少各出现 1 次。

---

## 4. artifact

- `artifacts/spiral-s4/{trade_date}/trade_records_sample.parquet`
- `artifacts/spiral-s4/{trade_date}/positions_sample.parquet`
- `artifacts/spiral-s4/{trade_date}/risk_events_sample.parquet`
- `artifacts/spiral-s4/{trade_date}/paper_trade_replay.md`
- `artifacts/spiral-s4/{trade_date}/consumption.md`
- `artifacts/spiral-s4/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `trade_records/positions/t1_frozen` 与 `trading-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s4/review.md`
- 必填结论：
  - 订单到持仓变更链路是否可完整回放
  - 跌停不可卖、次日重试等关键边界是否可验证
  - S3 输入消费证据是否完整且可审计
  - RejectReason 4 核心拒单路径是否全覆盖
  - TradingState 4 值是否全覆盖
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s4/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `gate = FAIL` 或回放链路断裂：状态置 `blocked`，进入 `S4r` 修复子圈，不推进 S3b。
- 若契约/治理检查失败：先修复并补齐回归证据，再重跑 S4 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

---

## 历史债务状态（2026-02-27 清零同步）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

（2026-02-18）

- 已完成 S4 收口：`artifacts/spiral-s4/20260222/` 形成完整 run/test/artifact 证据链，`quality_status=WARN`、`go_nogo=GO`。
- 已验证跨日持仓关键边界：跌停不可卖阻断与次日重试卖出可回放。
- 下一步：进入 S3b（收益归因验证闭环）。



