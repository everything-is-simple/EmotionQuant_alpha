# EmotionQuant VORTEX 演进路线图（Plan A SoT）

**状态**: Active（Rebaseline）  
**更新时间**: 2026-02-26  
**定位**: Plan A 唯一能力状态 SoT（业务与工程双视图）

---

## 1. 口径说明

1. 本文是 Plan A 的唯一状态源；其余路线文档均为执行细化。
2. 本次修订将路线从“线性任务视角”切换为“双视图”：
   - 业务价值视图：三大螺旋是否闭环。
   - 工程实现视图：S0-S7 圈位实现进度。
3. 若业务视图与工程视图冲突，以业务视图门禁优先。
4. 相关文件：
   - `Governance/SpiralRoadmap/planA/planA-ENHANCEMENT.md`
   - `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`
   - `Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
   - `docs/design/core-algorithms/`
   - `docs/design/core-infrastructure/`
   - `docs/design/enhancements/eq-improvement-plan-core-frozen.md`

---

## 2. 业务价值视图（三大螺旋）

| 螺旋 | 目标 | 对应圈位 | 当前状态 | 进入下一螺旋硬条件 |
|---|---|---|---|---|
| 螺旋1 Canary | 本地数据+核心算法+简回测+最小归因闭环 | S0a-S2c + S3(min) + S3b(min) | in_progress | canary 数据覆盖、端到端可复现、归因可解释、看板 GO |
| 螺旋2 Full | 16年数据+完整回测+完整归因+校准闭环 | S3a-S4b | planned | 全历史落库、多窗口回测、A/B/C+偏差归因、参数来源可追溯 |
| 螺旋3 Production | 展示稳定化+调度运维+生产就绪评审 | S5-S7a | planned | S6 稳定基线、S7a 可观测可恢复、生产评审 GO |
| 螺旋3.5 Pre-Live | 实盘预演（零真实下单）与故障恢复演练 | S7a 后预演圈 | planned | 连续20交易日无P0、偏差受控、预演评审 GO |

说明：任何螺旋未通过出口门禁，不得宣称“可实战”。

---

## 3. 工程实现视图（S 圈位 / Spiral 进度看板）

| 圈位 | 名称 | 实现状态 | 业务验证状态 | 下一动作 |
|---|---|---|---|---|
| S0a-S0c | 入口/L1/L2 | implemented | revalidate_required | 对齐 canary-5y 数据窗口并重验（最低2020-2024） |
| S1a-S1b | MSS 评分/消费 | implemented | revalidate_required | 与真实本地数据重跑 probe |
| S2a-S2c | 多算法/集成/桥接 | implemented | revalidate_required | 在 canary 数据窗口完成端到端联调 |
| S3a/S3ar | 采集增强/稳定性 | implemented | partial | 先满足螺旋1数据门禁，再扩至16年 |
| S3 | 回测闭环 | implemented | partial | 继续推进螺旋1业务门禁重验与窗口扩展 |
| S4 | 纸上交易 | implemented | partial | 衔接 S3 回测参数并重放验证 |
| S3b | 收益归因 | implemented | partial | 持续提升归因稳定性与可解释性 |
| S3c/S3d/S3e | 行业/自适应/生产校准 | implemented | partial | 已完成工程实现，按螺旋2门禁继续业务重验 |
| S4b | 极端防御 | implemented | partial | 已具备跨窗口证据，继续按螺旋2门禁重验 |
| S5/S6/S7a | 展示/稳定化/调度 | S5=active; S6/S7a=planned | pending | S5 持续收口；S6/S7a 仍按螺旋2出口条件推进 |
| S3.5 | Pre-Live 预演 | planned | pending | 仅在螺旋3出口后推进，作为实盘前最后门禁 |

---

## 4. P0 阻断矩阵（必须先清）

| 阻断项 | 级别 | 当前判定 | 清除条件 |
|---|---|---|---|
| 本地历史数据未形成可用窗口 | P0 | open | canary-5y（最低2020-2024）覆盖>=99%，并有质量报告 |
| 端到端回测证据不足 | P0 | open | 同窗 run/backtest/analysis 全链路成功并留档 |
| 归因无法回答收益来源 | P0 | open | 至少完成 signal/execution/cost 三分解 |
| 归因无对比基准 | P0 | open | 完成 MSS vs 随机、MSS vs 技术基线 对比并可解释 |
| 业务成果不可见 | P0 | open | `PLANA-BUSINESS-SCOREBOARD.md` 每圈更新并给 GO/NO_GO |
| 实盘前无预演门禁 | P0 | open | 螺旋3.5 连续20交易日预演通过 |

---

## 5. 关键推进约束

1. S2b/S2c FAIL 只能进入 S2r，禁止跳过。
2. S2c -> S3 必须通过：
   - `python -m scripts.quality.local_quality_check --contracts --governance`
   - `selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id` 桥接硬门禁。
3. S3b 必须消费 S3+S4 真实执行结果，不允许只用回测推断。
4. S3c -> S3d -> S3e -> S4b 按顺序推进，不允许并跳；`S3c/S3d/S3e` 准备与实验工作可并行，但收口与宣告必须串行。
5. S5/S6/S7a 在螺旋2出口前不得宣称阶段完成。
6. 螺旋3完成后，必须先通过螺旋3.5（Pre-Live）才允许进入任何真实资金实盘。
7. 每圈收口前必须通过防跑偏门禁：
   - `python -m scripts.quality.local_quality_check --contracts --governance`
   - `tests/unit/scripts/test_contract_behavior_regression.py`
8. 每个螺旋收口评审必须给出“设计对齐结论”（core-algorithms/core-infrastructure/enhancements），缺失则判定 `NO_GO`。

---

## 6. 最小证据清单（每圈）

1. `run.log`
2. `test.log`
3. `gate_report.md`（**必须包含 §Design-Alignment-Fields 小节**：逐字段校验该圈核心产物表与 `docs/design/**/data-models.md` 的字段名、类型、枚举值范围一致性）
4. `consumption.md`
5. `review.md`
6. `sync_checklist.md`
7. `PLANA-BUSINESS-SCOREBOARD.md` 对应指标更新

---

## 7. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.4 | 2026-02-26 | 状态同步修订：工程视图对齐执行卡与开发状态；S3/S3b/S3c/S3d/S3e/S4b 更新为 implemented，S5 更新为 active |
| v2.3 | 2026-02-25 | 堵最大缺口：gate_report 强制包含 §Design-Alignment-Fields（字段级设计校验），闭合设计到执行的断裂点 |
| v2.2 | 2026-02-24 | 增加设计基线绑定：VORTEX 显式挂接 `docs/design/**` 与 `eq-improvement-plan-core-frozen.md`，并将"设计对齐结论"设为螺旋收口硬门禁 |
| v2.1 | 2026-02-23 | 与 Plan B 同步精度：canary 升级为5y最低窗口、新增归因对比 P0、S3c/S3d/S3e 双档执行口径（准备并行/收口串行）、新增螺旋3.5 Pre-Live |
| v2.0 | 2026-02-23 | 按 Reborn 方法重写 SoT：新增业务/工程双视图、P0 阻断矩阵、成果可见强制看板与阶段推进硬约束 |
| v1.6 | 2026-02-20 | 进度看板新增 `S3c/S3d/S3e`，关键顺序约束升级为 `S3b->S3c->S3d->S3e->S4b` |
