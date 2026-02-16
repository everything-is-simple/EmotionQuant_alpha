# EmotionQuant ROADMAP 总览（Spiral 闭环主控）

**版本**: v7.1.0  
**最后更新**: 2026-02-16  
**适用对象**: 个人开发、个人使用

---

## 1. 这份文档管什么

本文件是路线图唯一主控入口，回答 4 个问题：

1. 下一圈做什么（目标）
2. 这一圈怎么判定完成（闭环证据）
3. 需要碰哪些能力包（CP）
4. 本圈最少要同步哪些文档（同步契约）

> 决策口径：先保闭环，再扩范围。禁止“看起来完成、实际不可运行”。

---

## 2. 术语统一（去线性）

- Spiral：一圈开发周期，默认 7 天。
- CP（Capability Pack）：能力包。现有 `CP-*.md` 文件名保留，仅作兼容。
- Slice：能力包中的最小可交付切片（1 天内可完成）。
- 闭环证据：`run + test + artifact + review + sync` 五件套。

---

## 3. 执行铁则（个人版）

1. 一圈只允许 1 个主目标。
2. 一圈只取 1-3 个 Slice。
3. 任何 Slice 超过 1 天必须继续拆分。
4. 缺少任一闭环证据不得收口。
5. 如遇阻塞，优先缩圈，不做跨圈并行扩张。

---

## 4. Spiral 主路线（S0-S6）

| Spiral | 主目标 | 推荐 CP 组合 | 最小闭环证据 |
|---|---|---|---|
| S0 | 数据最小闭环 | CP-01 | 1 条可运行命令 + 1 个自动化测试 + 1 个数据产物 |
| S1 | MSS 闭环 | CP-01, CP-02 | 当日温度/周期可复现 + 结果文件 |
| S2 | 信号生成闭环 | CP-03, CP-04, CP-10, CP-05 | TopN 推荐 + 集成输出可追溯 |
| S3 | 回测闭环 | CP-10, CP-06, CP-09 | 基线回测报告 + 指标摘要 |
| S4 | 纸上交易闭环 | CP-07, CP-09 | 订单/持仓/风控日志可重放 |
| S5 | 展示闭环 | CP-08, CP-09 | GUI 可启动 + 日报导出 |
| S6 | 稳定化闭环 | CP-10, CP-07, CP-09 | 重跑一致性 + 债务清偿记录 |

> 说明：上表 CP 组合是父圈视图中的能力包覆盖范围，不等同于单圈 Slice 数。  
> S2 涉及 CP-03/CP-04/CP-10/CP-05，执行时需拆分为 S2a/S2b 子圈，确保每子圈仍满足“1-3 个 Slice”约束。

### 4.1 实战扩展微圈（可选但一旦启用必须收口）

| Spiral | 主目标 | 对应增强 | 插入位置 | 最小闭环证据 |
|---|---|---|---|---|
| S3a | 数据采集增强闭环 | ENH-10（分批+断点续传+多线程） | S2 后、S3 前 | `fetch_progress` + 吞吐对比 + 恢复演练记录 |
| S7a | 自动调度闭环 | ENH-11（每日自动下载+开机自启） | S6 后 | 调度安装记录 + 最近执行历史 + 交易日去重验证 |

> 约束：S3a/S7a 不改变 CP 主路线语义，只交付执行层与运维层增强能力。

### 4.2 当前执行状态快照（2026-02-16）

| 微圈 | 目标 | 状态 | 证据入口 |
|---|---|---|---|
| S0a | 统一入口与配置注入可用 | ✅ completed | `Governance/specs/spiral-s0a/final.md` |
| S0b | L1 采集入库闭环 | ✅ completed | `Governance/specs/spiral-s0b/final.md` |
| S0c | L2 快照与失败链路闭环 | ✅ completed | `Governance/specs/spiral-s0c/final.md` |
| S1a | MSS 最小评分可跑 | ✅ completed | `Governance/specs/spiral-s1a/final.md` |
| S1b | MSS 消费验证闭环 | ✅ completed | `Governance/specs/spiral-s1b/final.md` |
| S2a | IRS + PAS + Validation 最小闭环 | ✅ completed | `Governance/specs/spiral-s2a/final.md` |
| S2b | MSS+IRS+PAS 集成推荐闭环 | ✅ completed | `Governance/specs/spiral-s2b/final.md` |
| S3a | ENH-10 数据采集增强闭环 | 🟡 planned | `Governance/specs/spiral-s3a/final.md` |
| S3 | 回测闭环 | 📋 planned | 待创建 `Governance/specs/spiral-s3/*` |

---

## 5. CP 映射（兼容旧文件名）

| CP | 能力 | 文件 |
|---|---|---|
| CP-01 | Data Layer | `Governance/Capability/CP-01-data-layer.md` |
| CP-02 | MSS | `Governance/Capability/CP-02-mss.md` |
| CP-03 | IRS | `Governance/Capability/CP-03-irs.md` |
| CP-04 | PAS | `Governance/Capability/CP-04-pas.md` |
| CP-05 | Integration | `Governance/Capability/CP-05-integration.md` |
| CP-06 | Backtest | `Governance/Capability/CP-06-backtest.md` |
| CP-07 | Trading | `Governance/Capability/CP-07-trading.md` |
| CP-08 | GUI | `Governance/Capability/CP-08-gui.md` |
| CP-09 | Analysis | `Governance/Capability/CP-09-analysis.md` |
| CP-10 | Validation | `Governance/Capability/CP-10-validation.md` |

---

## 6. 全局边界（所有 Spiral 生效）

### 6.1 输入边界

- 主流程只读本地数据。
- 远端数据必须先落地再进入主流程。

### 6.2 输出边界

- CP-05 输出必须可被 CP-06/07/08/09 复用。
- 分析报告必须可追溯到输入数据和参数。
- S2-S6 执行链路必须统一 `contract_version = "nc-v1"`。
- 执行层统一门槛：`risk_reward_ratio >= 1.0`（`=1.0` 可执行，`<1.0` 必须过滤）。

### 6.3 错误分级

| 级别 | 定义 | 处理 |
|---|---|---|
| P0 | 核心输入缺失、规则冲突、合规违规 | 阻断 |
| P1 | 局部数据缺失、局部计算失败 | 降级 + 标记 |
| P2 | 非关键异常 | 重试 + 记录 |

### 6.4 质量门禁

- S2-S6 收口前必须通过：`python -m scripts.quality.local_quality_check --contracts --governance`
- CI 需通过：`.github/workflows/quality-gates.yml`

---

## 7. 每圈最小同步契约（降负担）

每圈收口只强制更新以下 5 处：

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/Capability/SPIRAL-CP-OVERVIEW.md`（只更新当圈状态）

能力包文档（CP）仅在“契约变化”时更新，不要求每圈都改。

补充要求：

- 若本圈涉及命名契约、治理口径、Gate 规则，A4 前必须附上 `local_quality_check --contracts --governance` 结果。

---

## 8. 什么时候必须改 CP 文档

满足任一条件时，必须更新对应 CP 文件：

1. 输入字段变化
2. 输出字段变化
3. 错误处理策略变化
4. DoD 门禁变化
5. 上下游依赖变化
6. `contract_version`/`risk_reward_ratio` 等执行边界变化

---

## 9. 归档说明

- 线性旧版：`Governance/Capability/archive-legacy-linear-v4-20260207/`
- 该目录只读，不再继续演进。

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v7.1.0 | 2026-02-16 | 下一圈切换为 S3a（ENH-10）并创建 `spiral-s3a` 证据入口；S3 顺延为 S3a 后继圈 |
| v7.0.0 | 2026-02-15 | 同步 S2b 按 6A 完成收口证据；状态推进到 S3 planned |
| v6.9.0 | 2026-02-15 | 同步 S2a 按 6A 完成收口证据；状态推进到 S2b planned |
| v6.8.0 | 2026-02-15 | 同步 S1b 按 6A 完成收口证据；状态推进到 S2a planned |
| v6.7.0 | 2026-02-15 | 同步 S1a 按 6A 完成收口证据；状态推进到 S1b planned |
| v6.6.0 | 2026-02-15 | 同步 S0c 按 6A 完成收口证据；状态推进到 S1a planned |
| v6.5.0 | 2026-02-15 | 同步 S0a/S0b 按 6A 完成收口证据；新增当前微圈执行状态快照（S0c 作为下一圈） |
| v6.4.0 | 2026-02-14 | 补齐执行边界：统一 `contract_version=nc-v1` 与 `risk_reward_ratio >= 1.0`；新增 S2-S6 本地/CI 质量门禁口径（`--contracts --governance`） |
| v6.3.0 | 2026-02-13 | 纳入实战扩展微圈：新增 S3a（ENH-10）与 S7a（ENH-11）口径，明确启用后必须按五件套收口 |
| v6.2.0 | 2026-02-12 | 对齐 SpiralRoadmap：S6 口径改为 CP-10/CP-07/CP-09；补充 S2“父圈视图 + 子圈拆分”说明，消除与 1-3 Slice 约束歧义 |
| v6.1.0 | 2026-02-07 | 增加 CP-10 Validation；S2/S3 显式引入验证闭环 |
| v6.0.0 | 2026-02-07 | 重构为 Spiral 主控文档；引入 CP 术语；明确个人开发降负担同步契约 |
| v5.1.0 | 2026-02-07 | Spiral 路线与边界约束基线 |



