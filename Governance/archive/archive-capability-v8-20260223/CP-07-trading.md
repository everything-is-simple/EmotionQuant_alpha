# ROADMAP Capability Pack CP-07｜Trading（交易与风控）

**文件名**: `CP-07-trading.md`  
**版本**: v6.0.1  
> ✅ 当前口径（2026-02-23）
> 本文件为当前有效能力契约（CP），用于定义输入/输出/门禁/回退。
> 本文件不承担路线主控；执行以运行事实与执行卡证据为准。
> 执行入口：`Governance/SpiralRoadmap/planA/EXECUTION-CARDS-INDEX.md` 与 `Governance/record/development-status.md`。
---

## 1. 定位

形成纸上交易闭环：信号 -> 订单 -> 持仓 -> 风控。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `integrated_recommendation` | CP-05 | 当日信号可用；`contract_version="nc-v1"`；`risk_reward_ratio` 可解析 | P0 |
| `raw_daily` / `raw_trade_cal` | CP-01 | 行情与交易日可用 | P0 |
| `validation_gate_decision` | CP-10 | Gate 非 FAIL（或显式 WARN）且可追溯 | FAIL 阻断 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `trade_records` | CP-09 | 生命周期完整 |
| `positions` | CP-08/09 | 持仓可追溯 |
| `risk_events` | 治理 | 触发原因清晰 |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP07-S1 | S4 | 纸上交易最小闭环 | 交易日志 + 测试 |
| CP07-S2 | S4/S5 | 风控规则接入 | 风控测试 |
| CP07-S3 | S6 | 异常恢复与稳定性 | 演练报告 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-05 信号可用
- CP-10 Gate 非 FAIL
- A 股规则可检查
- 契约版本兼容：`contract_version = "nc-v1"`

### 4.2 Exit

- 订单状态可重放
- 风控结果可审计
- 执行前已应用 `risk_reward_ratio >= 1.0` 过滤
- 与 CP-06 回测口径可对齐

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 非交易日下单 | P0 | 阻断 |
| 风控规则冲突 | P0 | 采用更严格规则 |
| 开盘无法成交 | P1 | 保持待执行并记录 |
| `contract_version` 不兼容 | P0 | `trading_state=blocked_contract_mismatch` 并阻断 |

---

## 6. 何时更新本文件

1. 交易状态机变化
2. 风控规则变化
3. 输出日志结构变化
4. 回测对齐口径变化
5. `contract_version` 或 `risk_reward_ratio` 执行边界变化

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v6.0.1 | 2026-02-14 | 补齐 Trading 执行边界：前置 `contract_version=nc-v1` 检查；显式 `risk_reward_ratio >= 1.0` 过滤；新增版本不兼容阻断语义 |



