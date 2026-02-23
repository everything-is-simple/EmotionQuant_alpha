# ROADMAP Capability Pack CP-06｜Backtest（回测）

**文件名**: `CP-06-backtest.md`  
**版本**: v6.0.1  
> ⚠️ 历史说明（2026-02-13）
> 本文件为线性阶段能力包留档，仅供回顾历史，不作为当前路线图执行入口。
> 当前执行入口：`Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`。
> 除历史纠错外，不再作为迭代依赖。
---

## 1. 定位

构建可复现、可对比、可审计的回测闭环。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `integrated_recommendation` | CP-05 | `contract_version="nc-v1"` 且字段完整；`risk_reward_ratio` 可解析 | 版本不兼容或字段缺失 P0 阻断 |
| `raw_daily` / `raw_trade_cal` | CP-01 | 可读取 | P0 |
| `validation_gate_decision` | CP-10 | Gate 非 FAIL（或显式 WARN）且可追溯 | FAIL 阻断 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `backtest_results` | CP-09/治理 | 指标完整 |
| `backtest_trade_records` | CP-09 | 记录可追溯 |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP06-S1 | S3 | 基线回测器 | 回测报告 + 测试 |
| CP06-S2 | S4 | 乐观/基线/保守三档 | 敏感性报告 |
| CP06-S3 | S5 | 与纸上交易偏差对齐 | 偏差报告 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-05 集成信号可用
- CP-10 Gate 非 FAIL
- A 股交易规则已配置
- 契约版本兼容：`contract_version = "nc-v1"`

### 4.2 Exit

- 回测命令可复现
- T+1 与涨跌停规则有自动化测试
- 执行前已应用 `risk_reward_ratio >= 1.0` 过滤
- 输出可被 CP-09 消费

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 信号与行情日期错位 | P0 | 阻断 |
| 个别标的无数据 | P1 | 跳过并标记 |
| 指标计算异常 | P1 | 记录并降级 |
| `contract_version` 不兼容 | P0 | `backtest_state=blocked_contract_mismatch` 并阻断 |

---

## 6. 何时更新本文件

1. 回测输入/输出契约变化
2. 交易规则口径变化
3. 评估指标变化
4. 降级策略变化
5. `contract_version` 或 `risk_reward_ratio` 执行边界变化

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v6.0.1 | 2026-02-14 | 补齐 Backtest 执行边界：前置 `contract_version=nc-v1` 兼容检查；显式 `risk_reward_ratio >= 1.0` 过滤；新增版本不兼容阻断语义 |



