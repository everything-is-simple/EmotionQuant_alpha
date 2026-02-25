# Plan A 业务价值看板（强制更新）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-24  
**用途**: 回答“做成了吗？做得怎么样？”

---

## 1. 当前螺旋状态总览

| 螺旋 | 状态 | 最近评审日 | 结论 |
|---|---|---|---|
| 螺旋1（Canary） | in_progress | 2026-02-23 | 继续推进 |
| 螺旋2（Full） | planned | - | 等待螺旋1出口 |
| 螺旋3（Production） | planned | - | 等待螺旋2出口 |
| 螺旋3.5（Pre-Live） | planned | - | 等待螺旋3出口 |

---

## 2. 螺旋 1（Canary）评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 本地数据窗口 | 最低 2020-01-01 ~ 2024-12-31（理想 2019-01-01 ~ 2026-02-13） | pending | blocked |
| 数据覆盖率 | >=99% | pending | blocked |
| 端到端可运行 | run+backtest+analysis 同窗成功 | pending | blocked |
| 简回测产物 | 收益曲线+交易记录 | pending | blocked |
| 最小归因产物 | signal/execution/cost 三分解 | pending | blocked |
| MSS vs 随机基准超额收益 | >5% | pending | blocked |
| MSS vs 技术基线超额收益 | >3% | pending | blocked |
| 风险收益基线 | 夏普>1.0 / 最大回撤<20% / 胜率>50% | pending | blocked |
| 归因质量 | dominant_component≠'none'比例 >=50%（S3b 扩窗后） | pending | blocked |
| 归因方法合理性 | attribution_method 小样本自动 fallback 到 mean_fallback_small_sample | pending | blocked |
| 螺旋结论 | GO/NO_GO | pending | blocked |

---

## 3. 螺旋 2（Full）评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 历史数据窗口 | 2008-01-01 ~ 2024-12-31 | pending | planned |
| 多窗口回测 | 1y/3y/5y + 牛熊段 | pending | planned |
| 完整归因 | A/B/C + 偏差分解 | pending | planned |
| S3c/S3d/S3e MVP门禁 | 无 FAIL 且 WARN 可解释 | pending | planned |
| S3c/S3d/S3e FULL门禁 | 生产口径完整校准 | pending | planned |
| 行业与算法校准 | SW31 + MSS adaptive + Validation 生产校准 | pending | planned |
| factor_gate_raw 健康度 | FAIL比例 <=50%（扩窗后）；FULL口径不得FAIL | pending | planned |
| backtest-test-cases 覆盖 | >=19条核心用例通过 | pending | planned |
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

## 5. 螺旋 3.5（Pre-Live）评分卡

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 连续预演交易日 | >=20 个交易日 | pending | planned |
| 预演期P0事故 | 0 | pending | planned |
| 偏差复盘完整度 | 每日 signal/execution/cost | pending | planned |
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
| core-infrastructure/gui | 只读展示口径一致 + FreshnessMeta/FilterConfig 验证 | pending |

---

## 7. 更新规则

1. 每个微圈收口必须更新本文件。
2. 若任一核心指标是 `blocked`，不得宣称“阶段完成”。
3. 该看板与 `Governance/record/development-status.md` 同步更新，出现冲突以本文件的 `GO/NO_GO` 结论为准并在复盘中解释。
4. 任一设计对齐检查未完成，不得给出螺旋最终 `GO`。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.2 | 2026-02-25 | 堵缺口：螺旋1新增归因质量/方法合理性指标，螺旋2新增 factor_gate_raw 健康度/backtest-test-cases 覆盖，GUI 设计对齐检查补充 FreshnessMeta |
| v1.1 | 2026-02-24 | 增加 `docs/design` 设计对齐检查，提升与 Plan B 同精度门禁口径 |
| v1.0 | 2026-02-23 | 首版看板：三螺旋+Pre-Live 评分卡 |
