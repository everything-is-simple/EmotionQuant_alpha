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

## 3. 三螺旋结构（递进 + 微圈体系）

| 螺旋 | 目标 | PB 微圈 | 对应 Plan A 圈位 | 退出门禁 |
|---|---|---|---|---|
| 螺旋1 Canary | 证明最小可用闭环成立 | PB-1.1~PB-1.4 | S0-S2 + S3(min) + S3b(min) | GO/NO_GO |
| 螺旋2 Full | 证明全历史与完整校准闭环成立 | PB-2.1~PB-2.5 | S3a-S4b | GO/NO_GO |
| 螺旋3 Production | 证明生产运维闭环成立 | PB-3.1~PB-3.4 | S5-S7a + 螺旋3.5 | GO/NO_GO |

PB 微圈主链：`PB-1.1 → PB-1.2 → PB-1.3 → PB-1.4 → PB-2.1 → PB-2.2 → PB-2.3 → PB-2.4 → PB-2.5 → PB-3.1 → PB-3.2 → PB-3.3 → PB-3.4`

---

## 4. ENH 显式映射（对齐 `eq-improvement-plan-core-frozen.md` §4）

| PB 微圈 | 消费 ENH | 说明 |
|---|---|---|
| PB-1.1 | ENH-01/02/03/04(Data)/05/08(骨架) | 数据最小闭环 + 预检守卫 + 失败产物 |
| PB-1.2 | ENH-04(MSS/IRS/PAS/Validation/Integration) | 算法与集成契约测试 |
| PB-1.3 | ENH-04(Backtest)/06/09 | 回测契约 + A/B/C 对照 + Qlib 适配 |
| PB-1.4 | ENH-06 | 最小归因 + 对比归因 |
| PB-2.1 | ENH-10 | 采集增强（分批+断点+多线程） |
| PB-2.2 | ENH-04(Backtest)/06/09 | 多窗口回测 + 完整归因 |
| PB-2.3 | ENH-04(IRS) | SW31 行业语义校准 |
| PB-2.4 | ENH-04(MSS/Validation) | MSS adaptive + Validation 生产校准 |
| PB-2.5 | ENH-04(Trading) | 极端防御参数可追溯 |
| PB-3.1 | ENH-01/07 | 统一入口 + L4 产物标准化 |
| PB-3.2 | ENH-08(全量) | 设计冻结检查 + 全链路重跑 |
| PB-3.3 | ENH-11 | 定时调度器 |
| PB-3.4 | — | Pre-Live 预演（无 ENH 依赖） |

---

## 5. 文档优先级（Plan B 口径）

| 级别 | 文档 | 冲突时以此为准 |
|---|---|---|
| L0 | `eq-improvement-plan-core-frozen.md` | 主计划唯一入口 |
| L1 | `VORTEX-EVOLUTION-ROADMAP.md`（Plan A SoT） | 状态口径参考 |
| L2 | `Governance/steering/系统铁律.md` + `CORE-PRINCIPLES.md` | 制度红线 |
| L3 | `docs/design/**` | 设计基线（字段/枚举/阈值） |
| L4 | 本文件 + 螺旋子文档 | 执行层 |

---

## 6. 同精度硬约束（与 Plan A 对齐）

1. Canary 数据窗口最低 `2020-01-01 ~ 2024-12-31`，理想 `2019-01-01 ~ 2026-02-13`。
2. 归因必须同时包含：
   - `signal/execution/cost` 三分解
   - `MSS vs 随机基准`
   - `MSS vs 技术基线（MA/RSI/MACD）`
3. `S3c/S3d/S3e` 必须执行 `MVP` 与 `FULL` 双档门禁。
4. `S3c/S3d/S3e` 允许准备并行，收口宣告必须 `S3c -> S3d -> S3e` 串行。
5. 螺旋3结束后必须通过螺旋3.5：连续20交易日零真实下单预演。

---

## 7. 与 Plan A 的关系

1. Plan A 仍是主线；Plan B 是同精度备线，不是降级线。
2. Plan B 启动后仍复用现有圈位与执行卡，不重写全系统。
3. Plan B 的产物与状态同步要求与 Plan A 一致，避免双轨漂移。
4. 每个 PB 微圈标注对应 Plan A S-编号，便于双线交叉参考。

---

## 8. WARN 升级与失败处理策略

| 场景 | 处理规则 |
|---|---|
| 微圈 gate=NO_GO | 不得推进下一微圈，仅允许在当前微圈范围修复 |
| 螺旋 GO/NO_GO | 任一出口项未通过，判定 NO_GO，不得推进下一螺旋 |
| WARN 持续 ≥2 个评审周期 | 必须产出 WARN 根因分析报告，不得继续忽略 |
| `factor_gate_raw=FAIL` 软化通过 | 必须产出 `neutral_regime 依赖审计报告`，不得在生产口径忽略 |
| `dominant_component='none'` 持续 | 必须扩窗或调整归因方法，不得宣称归因完成 |
| 连续两轮螺旋 NO_GO | 必须重估输入数据质量与算法契约，不得强行跳过 |

---

## 9. 四类失控风险防线（针对 Plan A 旧问题）

| 旧问题 | Plan B 防线 |
|---|---|
| 数据断层 | PB-1.1 强制 `fetch-batch/fetch-retry/data-quality-check` + 覆盖率门禁 |
| 模块孤立 | 每微圈强制端到端同窗 `run/test/artifact/gate` |
| 成果不可见 | 每螺旋看板更新 + `GO/NO_GO` 强制结论 |
| 回测缺失 | PB-1.3 最小回测 + PB-2.2 多窗口完整回测与归因硬门禁 |

---

## 10. 配套文件

- `Governance/SpiralRoadmap/planB/PLAN-B-DEPENDENCY-MAP.md`
- `Governance/SpiralRoadmap/planB/PLAN-B-EXECUTION-CHECKLIST.md`
- `Governance/SpiralRoadmap/planB/PLAN-B-READINESS-SCOREBOARD.md`
- `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-1-CANARY.md`
- `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-2-FULL.md`
- `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-3-PRODUCTION.md`

---

## 11. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v4.0 | 2026-02-25 | 堵最大缺口：新增 PB 微圈体系主链、ENH 显式映射、文档优先级、WARN 升级策略；补建 PLAN-B-DEPENDENCY-MAP.md 链接 |
| v3.2 | 2026-02-24 | 新增“Plan A 四类失控风险防线”映射，确保 Plan B 作为同精度应急方案直接对焦旧问题 |
| v3.1 | 2026-02-24 | 按“实事求是+螺旋闭环”重构总览：绑定 `docs/design/**`，固化三螺旋递进与同精度硬约束 |
| v3.0 | 2026-02-24 | 真螺旋版 |
| v2.0 | 2026-02-23 | 实事求是版 |
