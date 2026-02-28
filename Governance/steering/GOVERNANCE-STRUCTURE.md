# EmotionQuant 治理结构与目录规范（R0-R9 对齐）

**版本**: v4.0.0  
**最后更新**: 2026-02-28

---

## 1. 治理目录

- `docs/roadmap.md`：R0-R9 全系统重建路线图（当前权威）
- `docs/cards/`：61 张执行卡（R0-R9 细粒度实施计划）
- `docs/sos/`：11 模块 SOS 审计报告（183 项偏差，R0-R9 依据）
- `docs/design/core-algorithms/`：核心算法设计（MSS/IRS/PAS/Validation/Integration）
- `docs/design/core-infrastructure/`：核心基础设施设计（Data/Backtest/Trading/GUI/Analysis）
- `docs/design/enhancements/`：外挂增强设计
- `Governance/steering/`：铁律、原则、流程
- `Governance/steering/TRD.md`：技术需求与选型权威口径（技术源头）
- `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`：跨文档变更联动模板
- `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`：命名契约变更联动模板
- `Governance/record/`：状态、债务、复用资产
- `Governance/specs/`：已清空（Spiral 阶段 specs 已归档）
- `Governance/archive/`：只读归档（含 legacy-linear-v4、capability-v8、spiral-roadmap-v5、spiral-specs-v5、old-plans-v5）

---

## 2. 单一事实源（SoT）

| 场景 | 唯一权威文件 |
|---|---|
| 重建路线图与依赖关系 | `docs/roadmap.md`（R0-R9） |
| 执行卡集中入口 | `docs/cards/README.md`（61 张卡） |
| SOS 审计与偏差清单 | `docs/sos/`（11 模块） |
| 核心算法设计 | `docs/design/core-algorithms/` |
| 核心基础设施设计 | `docs/design/core-infrastructure/` |
| 外挂增强设计 | `docs/design/enhancements/` |
| 任务如何写 | `Governance/steering/SPIRAL-TASK-TEMPLATE.md` |
| 6A 工作流如何执行 | `Governance/steering/6A-WORKFLOW.md` |
| 技术需求与选型 | `Governance/steering/TRD.md` |
| 不可违反什么 | `Governance/steering/系统铁律.md` |
| 核心原则 | `Governance/steering/CORE-PRINCIPLES.md` |
| 跨文档联动怎么做 | `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md` |
| 命名规范 | `docs/naming-conventions.md` |
| 命名契约 Schema | `docs/naming-contracts.schema.json` |
| 命名契约术语与联动模板 | `docs/naming-contracts-glossary.md` + `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` |
| 系统总览 | `docs/system-overview.md` |
| 模块索引 | `docs/module-index.md` |
| 开发状态 | `Governance/record/development-status.md` |
| 技术债登记 | `Governance/record/debts.md` |

---

## 3. 每阶段最小同步

每个 R 阶段收口强制更新 4 项：

1. `Governance/record/development-status.md`
2. `Governance/record/debts.md`
3. `docs/roadmap.md` 对应阶段状态
4. `docs/cards/` 对应卡片勾选

设计文档仅在实现与设计冲突时同步修正。

---

## 4. 工具与历史资产处理原则

- `.claude/` 保留为历史工具资产，不作为当前强制流程。
- 可复用内容已迁移至 `Governance/steering/`。

---

## 5. 归档策略

1. 路线模型代际变化必须归档（如线性 -> 螺旋）。
2. 归档目录命名：`archive-{model}-{version}-{date}`。
3. 归档目录只读，不再迭代。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v4.0.0 | 2026-02-28 | 体系切换：SoT 矩阵、治理目录、同步规则全面对齐 R0-R9 重建路线图；归档旧 SpiralRoadmap/specs/CP 引用 |
| v3.6.0 | 2026-02-23 | 对齐 SpiralRoadmap 重组（Spiral 最终版本） |
