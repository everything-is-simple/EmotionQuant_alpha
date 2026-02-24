# EmotionQuant Plan B 螺旋闭环总览（设计绑定版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-24  
**状态**: Active（Plan A 失败时可立即切换）  
**定位**: Plan B 总入口，定义螺旋开发与检验迭代的硬约束

---

## 1. 初衷与边界

Plan B 只解决一件事：避免再次走成“任务串行而非螺旋闭环”。

1. 每个螺旋都必须端到端闭环：`数据 -> 算法 -> 回测/交易 -> 归因 -> 评审`。
2. 每个螺旋都必须有迭代检验：`run/test/artifact/review/sync + GO/NO_GO`。
3. 螺旋间必须递进：上一螺旋不 `GO`，下一螺旋不得宣告推进。
4. Plan B 不允许脱离现有代码与设计文档另起炉灶。

---

## 2. 设计基线（强绑定）

Plan B 必须与以下权威设计保持一致，不得降级或替换语义：

1. `docs/design/core-algorithms/`：MSS/IRS/PAS/Validation/Integration
2. `docs/design/core-infrastructure/`：Data/Backtest/Trading/Analysis/GUI
3. `docs/design/enhancements/eq-improvement-plan-core-frozen.md`
4. `Governance/steering/系统铁律.md`
5. `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`（状态口径参考）

---

## 3. 三螺旋结构（递进）

| 螺旋 | 目标 | 对应圈位 | 核心闭环产出 | 退出门禁 |
|---|---|---|---|---|
| 螺旋1 Canary | 证明最小可用闭环成立 | S0-S2 + S3(min) + S3b(min) | canary窗口、端到端同窗、最小归因+对比归因 | GO/NO_GO |
| 螺旋2 Full | 证明全历史与完整校准闭环成立 | S3a-S4b | 16年落库、多窗口回测、完整归因、S3c/S3d/S3e校准 | GO/NO_GO |
| 螺旋3 Production | 证明生产运维闭环成立 | S5-S7a + 螺旋3.5 | GUI只读消费、全链路重跑、调度可审计、Pre-Live预演 | GO/NO_GO |

---

## 4. 同精度硬约束（与 Plan A 对齐）

1. Canary 数据窗口最低 `2020-01-01 ~ 2024-12-31`，理想 `2019-01-01 ~ 2026-02-13`。
2. 归因必须同时包含：
   - `signal/execution/cost` 三分解
   - `MSS vs 随机基准`
   - `MSS vs 技术基线（MA/RSI/MACD）`
3. `S3c/S3d/S3e` 必须执行 `MVP` 与 `FULL` 双档门禁。
4. `S3c/S3d/S3e` 允许准备并行，收口宣告必须 `S3c -> S3d -> S3e` 串行。
5. 螺旋3结束后必须通过螺旋3.5：连续20交易日零真实下单预演。

---

## 5. 与 Plan A 的关系

1. Plan A 仍是主线；Plan B 是同精度备线，不是降级线。
2. Plan B 启动后仍复用现有圈位与执行卡，不重写全系统。
3. Plan B 的产物与状态同步要求与 Plan A 一致，避免双轨漂移。

---

## 6. 四类失控风险防线（针对 Plan A 旧问题）

| 旧问题 | Plan B 防线 |
|---|---|
| 数据断层 | 螺旋1强制 `fetch-batch/fetch-retry/data-quality-check` + 覆盖率门禁 |
| 模块孤立 | 每螺旋强制端到端同窗 `run/backtest/analysis` |
| 成果不可见 | 每螺旋看板更新 + `GO/NO_GO` 强制结论 |
| 回测缺失 | 螺旋1最小回测 + 螺旋2多窗口完整回测与归因硬门禁 |

---

## 7. 配套文件

- `Governance/SpiralRoadmap/planB/PLAN-B-EXECUTION-CHECKLIST.md`
- `Governance/SpiralRoadmap/planB/PLAN-B-READINESS-SCOREBOARD.md`
- `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-1-CANARY.md`
- `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-2-FULL.md`
- `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-3-PRODUCTION.md`

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.2 | 2026-02-24 | 新增“Plan A 四类失控风险防线”映射，确保 Plan B 作为同精度应急方案直接对焦旧问题 |
| v3.1 | 2026-02-24 | 按“实事求是+螺旋闭环”重构总览：绑定 `docs/design/**`，固化三螺旋递进与同精度硬约束 |
| v3.0 | 2026-02-24 | 真螺旋版 |
| v2.0 | 2026-02-23 | 实事求是版 |
