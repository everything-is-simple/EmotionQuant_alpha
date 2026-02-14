# EmotionQuant 治理结构与目录规范（Spiral 版）

**版本**: v3.5.1  
**最后更新**: 2026-02-14

---

## 1. 治理目录

- `docs/design/core-algorithms/`：核心算法设计（MSS/IRS/PAS/Validation/Integration）
- `docs/design/core-infrastructure/`：核心基础设施设计（Data/Backtest/Trading/GUI/Analysis）
- `docs/design/enhancements/`：外挂增强设计与主计划入口
- `Governance/Capability/`：Spiral 主路线与能力包（CP）
- `Governance/SpiralRoadmap/`：系统实现路线与跨圈依赖桥梁
- `Governance/steering/`：铁律、原则、流程
- `Governance/steering/TRD.md`：技术需求与选型权威口径（技术源头）
- `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`：跨文档变更联动模板
- `Governance/record/`：状态、债务、复用资产
- `Governance/specs/spiral-s*/`：每圈 specs 与复盘
- `Governance/Capability/archive-legacy-linear-v4-20260207/`：线性旧版只读归档

---

## 2. 单一事实源（SoT）

| 场景 | 唯一权威文件 |
|---|---|
| 核心算法设计看哪里 | `docs/design/core-algorithms/` |
| 核心基础设施设计看哪里 | `docs/design/core-infrastructure/` |
| 本圈做什么 | `Governance/Capability/SPIRAL-CP-OVERVIEW.md` |
| 能力契约是什么 | `Governance/Capability/CP-*.md`（CP） |
| 任务如何写 | `Governance/Capability/SPIRAL-TASK-TEMPLATE.md` |
| 新系统按圈怎么推进 | `Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md` |
| 跨圈依赖与外挂排布看哪里 | `Governance/SpiralRoadmap/DEPENDENCY-MAP.md` |
| 6A 工作流如何执行 | `Governance/steering/6A-WORKFLOW.md` |
| 技术需求与选型看哪里 | `Governance/steering/TRD.md` |
| 改进行动主计划看哪里 | `docs/design/enhancements/eq-improvement-plan-core-frozen.md` |
| 不可违反什么 | `Governance/steering/系统铁律.md` |
| 核心原则看哪里 | `Governance/steering/CORE-PRINCIPLES.md` |
| 跨文档联动怎么做 | `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md` |
| 命名规范看哪里 | `docs/naming-conventions.md` |
| 系统总览看哪里 | `docs/system-overview.md` |
| 模块索引看哪里 | `docs/module-index.md` |

---

## 3. 每圈最小同步

每圈收口强制更新 5 项：

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

CP 文档仅在契约变化时更新。

---

## 4. .claude 资产处理原则

- `.claude/` 保留为历史工具资产，不作为当前强制流程。
- 可复用内容迁移方向：
  - 命令级检查逻辑 -> `Governance/steering/`
  - 规则类约束 -> `Governance/steering/系统铁律.md`
  - 经验模板 -> `Governance/Capability/SPIRAL-TASK-TEMPLATE.md`

---

## 5. 归档策略

1. 路线模型代际变化必须归档（如线性 -> 螺旋）。
2. 归档目录命名：`archive-{model}-{version}-{date}`。
3. 归档目录只读，不再迭代。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v3.5.1 | 2026-02-14 | 修复 R33（review-011）：治理目录与 SoT 矩阵新增“跨文档变更联动模板”入口 |
| v3.5.0 | 2026-02-12 | 新增 TRD 作为技术源头 SoT；SpiralRoadmap 入口由 `draft/` 收敛到 `VORTEX-EVOLUTION-ROADMAP.md`，并补充 `DEPENDENCY-MAP.md` 入口 |
| v3.4.1 | 2026-02-11 | 修复 R1：收敛 SpiralRoadmap 表述为候选草稿；SoT 补充核心原则/命名规范/系统总览/模块索引；修正 .claude 迁移列表缩进 |
| v3.4.0 | 2026-02-11 | 补充设计目录三层结构与 SoT 映射（核心算法/核心基础设施/外挂增强） |
| v3.3.0 | 2026-02-10 | 新增 `Governance/SpiralRoadmap/` 作为与 `Capability` 同级的新系统实现路线目录，并补充 SoT 入口 |
| v3.2.0 | 2026-02-10 | 统一 6A 权威入口路径为 `Governance/steering/6A-WORKFLOW.md`，同步修正 SoT 与迁移指引 |
| v3.1.0 | 2026-02-10 | SoT 增加改进行动主计划入口；工作流 SoT 统一到合并后的 `6A-WORKFLOW.md` |
| v3.0.0 | 2026-02-07 | 增加单一事实源矩阵与 .claude 资产迁移原则 |
| v2.0.0 | 2026-02-07 | Spiral 治理结构初稿 |
