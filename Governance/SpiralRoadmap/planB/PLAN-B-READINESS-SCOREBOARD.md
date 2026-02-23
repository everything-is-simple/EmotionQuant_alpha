# Plan B 业务就绪看板（同精度版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-23  
**状态**: Active  
**用途**: Plan B 三螺旋+预演圈的业务可见性与 GO/NO_GO 判定

---

## 1. 总览

| 螺旋 | 状态 | 结论 |
|---|---|---|
| 螺旋1（Canary） | planned | pending |
| 螺旋2（Full） | planned | pending |
| 螺旋3（Production） | planned | pending |
| 螺旋3.5（Pre-Live） | planned | pending |

---

## 2. 螺旋1评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 数据窗口 | 最低2020-2024（理想2019-2024） | pending | blocked |
| 数据覆盖率 | >=99% | pending | blocked |
| 端到端同窗 | run+backtest+analysis成功 | pending | blocked |
| 归因三分解 | signal/execution/cost | pending | blocked |
| MSS vs 随机 | 超额收益>5% | pending | blocked |
| MSS vs 技术基线 | 超额收益>3% | pending | blocked |
| 螺旋结论 | GO/NO_GO | pending | blocked |

---

## 3. 螺旋2评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 全历史数据 | 2008-2024完整落库 | pending | planned |
| 多窗口回测 | 1y/3y/5y + 牛熊段 | pending | planned |
| 完整归因 | A/B/C + 偏差分解 | pending | planned |
| S3c/S3d/S3e MVP | 无FAIL，WARN可解释 | pending | planned |
| S3c/S3d/S3e FULL | 生产口径完整通过 | pending | planned |
| 螺旋结论 | GO/NO_GO | pending | planned |

---

## 4. 螺旋3评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 生产监控 | 可观测可告警可追溯 | pending | planned |
| 调度恢复 | 失败重试与恢复可演练 | pending | planned |
| 生产评审 | GO/NO_GO | pending | planned |

---

## 5. 螺旋3.5评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 连续预演交易日 | >=20交易日 | pending | planned |
| 预演P0事故 | 0 | pending | planned |
| 偏差复盘 | 每日 signal/execution/cost | pending | planned |
| 故障恢复演练 | 至少1次通过 | pending | planned |
| 预演评审 | GO/NO_GO | pending | planned |

---

## 6. 更新规则

1. 每个微圈收口必须更新本看板。
2. 任一核心指标 blocked 时，不得宣称螺旋完成。
3. 未通过螺旋3.5 `GO` 时，禁止进入真实资金实盘。
