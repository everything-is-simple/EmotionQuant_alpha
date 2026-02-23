# Plan A 业务价值看板（强制更新）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-23  
**用途**: 回答“做成了吗？做得怎么样？”

---

## 1. 当前螺旋状态总览

| 螺旋 | 状态 | 最近评审日 | 结论 |
|---|---|---|---|
| 螺旋1（Canary） | in_progress | 2026-02-23 | 继续推进 |
| 螺旋2（Full） | planned | - | 等待螺旋1出口 |
| 螺旋3（Production） | planned | - | 等待螺旋2出口 |

---

## 2. 螺旋 1（Canary）评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 本地数据窗口 | 2022-01-01 ~ 2024-12-31 | pending | blocked |
| 数据覆盖率 | >=99% | pending | blocked |
| 端到端可运行 | run+backtest+analysis 同窗成功 | pending | blocked |
| 简回测产物 | 收益曲线+交易记录 | pending | blocked |
| 最小归因产物 | signal/execution/cost 三分解 | pending | blocked |
| 螺旋结论 | GO/NO_GO | pending | blocked |

---

## 3. 螺旋 2（Full）评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 历史数据窗口 | 2008-01-01 ~ 2024-12-31 | pending | planned |
| 多窗口回测 | 1y/3y/5y + 牛熊段 | pending | planned |
| 完整归因 | A/B/C + 偏差分解 | pending | planned |
| 行业与算法校准 | SW31 + MSS adaptive + Validation 生产校准 | pending | planned |
| 螺旋结论 | GO/NO_GO | pending | planned |

---

## 4. 螺旋 3（Production）评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| GUI/日报 | 只读消费 L3 真实产物 | pending | planned |
| 全链路一致性 | run-all 重跑一致 | pending | planned |
| 自动调度 | 安装+运行历史+失败重试可审计 | pending | planned |
| 生产就绪评估 | GO/NO_GO 报告 | pending | planned |

---

## 5. 更新规则

1. 每个微圈收口必须更新本文件。
2. 若任一核心指标是 `blocked`，不得宣称“阶段完成”。
3. 该看板与 `Governance/record/development-status.md` 同步更新，出现冲突以本文件的 `GO/NO_GO` 结论为准并在复盘中解释。
