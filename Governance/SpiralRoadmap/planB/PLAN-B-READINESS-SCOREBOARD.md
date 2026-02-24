# Plan B 业务就绪看板（设计绑定版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-24  
**状态**: Active  
**用途**: Plan B 螺旋闭环的业务判定面板（唯一 GO/NO_GO 载体）

---

## 1. 螺旋总览

| 螺旋 | 对应圈位 | 状态 | 结论 |
|---|---|---|---|
| 螺旋1 Canary | S0-S2 + S3(min) + S3b(min) | planned | pending |
| 螺旋2 Full | S3a-S4b | planned | pending |
| 螺旋3 Production | S5-S7a | planned | pending |
| 螺旋3.5 Pre-Live | 螺旋3后预演 | planned | pending |

---

## 2. 螺旋1评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 数据窗口 | 最低 2020-2024（理想 2019-01-01~2026-02-13） | pending | blocked |
| 数据覆盖率 | >=99% | pending | blocked |
| 端到端同窗 | run/backtest/analysis 同窗成功 | pending | blocked |
| 最小归因 | signal/execution/cost | pending | blocked |
| MSS vs 随机 | 有量化超额结论 | pending | blocked |
| MSS vs 技术基线 | 有量化超额结论 | pending | blocked |
| 螺旋结论 | GO/NO_GO | pending | blocked |

---

## 3. 螺旋2评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 历史数据窗口 | 2008-01-01 ~ 2024-12-31 | pending | planned |
| 多窗口回测 | 1y/3y/5y + 牛熊段 | pending | planned |
| 完整归因 | A/B/C + 偏差分解 | pending | planned |
| S3c/S3d/S3e MVP | 无 FAIL，WARN 可解释 | pending | planned |
| S3c/S3d/S3e FULL | 生产口径完整通过 | pending | planned |
| S4b 参数追溯 | 来源可追溯（S3b+S3e） | pending | planned |
| 螺旋结论 | GO/NO_GO | pending | planned |

---

## 4. 螺旋3评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| GUI消费口径 | 只读消费真实产物 | pending | planned |
| 全链路一致性 | run-all 重跑一致 | pending | planned |
| 调度可审计 | install/status/history/retry 可追溯 | pending | planned |
| 螺旋结论 | GO/NO_GO | pending | planned |

---

## 5. 螺旋3.5评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 连续预演交易日 | >=20 交易日 | pending | planned |
| 预演P0事故 | 0 | pending | planned |
| 偏差复盘 | 每日 signal/execution/cost | pending | planned |
| 故障恢复演练 | 至少1次通过 | pending | planned |
| 预演结论 | GO/NO_GO | pending | planned |

---

## 6. 设计对齐检查（docs/design）

| 设计域 | 检查项 | 状态 |
|---|---|---|
| core-algorithms/mss | `mss_panorama` 字段与语义一致 | pending |
| core-algorithms/irs | SW31 门禁与行业覆盖一致 | pending |
| core-algorithms/pas | PAS 输出字段一致 | pending |
| core-algorithms/validation | `validation_weight_plan` 桥接一致 | pending |
| core-algorithms/integration | 四模式与硬约束一致 | pending |
| core-infrastructure/data-layer | L1-L4 依赖与落库口径一致 | pending |
| core-infrastructure/backtest | 回测口径与主线引擎一致 | pending |
| core-infrastructure/trading | A股规则与风控口径一致 | pending |
| core-infrastructure/analysis | 归因链路与偏差分解一致 | pending |
| core-infrastructure/gui | 只读展示口径一致 | pending |

---

## 7. 更新规则

1. 每个微圈收口后必须更新本看板。
2. 任一 P0 指标 `blocked` 时，不得宣称螺旋完成。
3. 任一设计对齐检查为 `pending`，不得给出最终生产 `GO`。
4. 未通过螺旋3.5 `GO`，禁止真实资金实盘。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.1 | 2026-02-24 | 改为设计绑定业务看板：增加 docs/design 对齐检查与螺旋闭环口径 |
| v2.0 | 2026-02-23 | 实事求是版 |
