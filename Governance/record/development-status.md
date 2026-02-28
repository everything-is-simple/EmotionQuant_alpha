# EmotionQuant 开发状态

**最后更新**: 2026-02-28  
**当前版本**: v5.0（R0-R9 重建路线图启用）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前体系

**⚠️ 2026-02-28 体系切换**：本项目已从 Spiral 渐进模型切换到 R0-R9 重建路线图体系。

### 权威文档 (SoT)

| 文档 | 路径 | 用途 |
|---|---|---|
| 重建路线图 | `docs/roadmap.md` | R0-R9 十阶段路线图，覆盖全部 183 项 SOS 偏差 |
| 执行卡 | `docs/cards/` | 61 张执行卡（10 个文件），每张卡有明确的输入/输出/验收标准 |
| SOS 审计 | `docs/sos/` | 11 模块标准化审计报告，记录全部设计-实现偏差 |
| 技术债登记 | `Governance/record/debts.md` | 当前技术债清单（2026-02-27 已清零） |

### 旧体系归档

| 旧文档 | 归档位置 | 原因 |
|---|---|---|
| Spiral Roadmap（planA/B + 30+ 执行卡） | `Governance/archive/archive-spiral-roadmap-v5-20260228/` | SOS 审计发现大量偏差，被 R0-R9 路线图取代 |
| Spiral Specs（spiral-s0a ~ s5） | `Governance/archive/archive-spiral-specs-v5-20260228/` | 粒度不匹配新路线图，证据链与代码不一致 |
| 旧执行/选型/债务计划 | `Governance/archive/archive-old-plans-v5-20260228/` | 被新路线图和执行卡内嵌步骤取代 |
| Capability v8 | `Governance/archive/archive-capability-v8-20260223/` | CP-01~CP-10 已被新路线图覆盖 |
| Legacy Linear v4 | `Governance/archive/archive-legacy-linear-v4-20260207/` | 最早期线性阶段模型 |

---

## R0-R9 阶段总览

| 阶段 | 名称 | 卡数 | 预估工期 | 状态 |
|---|---|---|---|---|
| R0 | 项目基础与开发环境 | 5 | 3-4d | 📋 待开始 |
| R1 | 数据层重建 | 6 | 5-7d | 📋 待开始 |
| R2 | MSS 模块重建 | 4 | 4-5d | 📋 待开始 |
| R3 | IRS + PAS 模块重建 | 8 | 12-15d | 📋 待开始 |
| R4 | 验证与集成重建 | 7 | 10-12d | 📋 待开始 |
| R5 | 回测引擎重建 | 9 | 12-14d | 📋 待开始 |
| R6 | 交易模块重建 | 5 | 7-8d | 📋 待开始 |
| R7 | 分析与调度重建 | 5 | 6-8d | 📋 待开始 |
| R8 | GUI 模块重建 | 6 | 8-10d | 📋 待开始 |
| R9 | 增强与收尾 | 6 | 7-10d | 📋 待开始 |
| **合计** | | **61** | **75-93d** | |

详见 `docs/roadmap.md` 与 `docs/cards/README.md`。

---

## 风险提示

1. R0-R9 路线图基于 SOS 审计全覆盖 183 项偏差设计，执行过程中可能发现新问题需动态调整
2. 旧 Spiral 执行中累积的代码（src/）仍为当前代码基线，R0-R9 是在此基础上重建
3. 技术债已于 2026-02-27 清零，但重建过程中可能产生新债务

---

## Spiral 历史执行记录（已归档，仅供参考）

旧 Spiral 体系（S0a ~ S7a）的完整执行轨迹已保存在本文件的 git 历史中。
查看方式：`git --no-pager log --oneline -20 -- Governance/record/development-status.md`

### 关键里程碑摘要

- 2026-02-15: S0a~S2b 完成，6A 证据归档
- 2026-02-17: S2c 收口，S3a 启动
- 2026-02-20: S3ar 锁恢复完成
- 2026-02-22: S3~S3e 全链路收口，S4/S4b/S4br 完成
- 2026-02-23: S5 GUI 最小闭环启动
- 2026-02-25~27: 设计-代码对齐审计（卡A/B/C），债务清零
- 2026-02-28: **切换到 R0-R9 重建路线图**

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-28 | v5.0 | 体系切换：从 Spiral 渐进模型切换到 R0-R9 重建路线图；归档旧 SpiralRoadmap/specs/计划文档；精简开发状态文档 |
| 2026-02-27 | v4.57 | S3AR 解阻 + 全实现卡复检全绿（Spiral 最终版本） |
