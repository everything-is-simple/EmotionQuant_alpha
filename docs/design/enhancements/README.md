# 外挂增强设计目录

**最后更新**: 2026-02-28  
**状态**: 部分归档（执行口径已迁移至 R0-R9 路线图）

---

## 1. 目录定位

本目录存放 EmotionQuant 外挂增强相关的设计文档（例如调度、监控）。

> **当前执行口径**：以 `docs/roadmap.md` (R0-R9) + `docs/cards/` 为准。
> 旧的执行主计划 / 选型论证 / 债务清偿计划已归档至 `Governance/archive/archive-old-plans-v5-20260228/`。

---

## 2. 当前有效文件（仍在使用）

- **`scheduler-orchestration-design.md`**：调度与编排设计（对应 R7 阶段）  
  包含：DAG 任务依赖、数据就绪检查点、盘后/盘前调度窗口、重试与补偿策略

- **`monitoring-alerting-design.md`**：监控与告警设计（对应 R9 阶段）  
  包含：全层监控范围、P0/P1/P2 告警级别、升级规则、失败重试策略

### 历史草稿（drafts/，仅供参考）

- `drafts/对标开源A股量化系统批判_20260209_150147.md`
- `drafts/对标开源A股量化系统批判_修订版_20260209.md`
- `drafts/对标批判响应行动计划_20260209_233929.md`
- `drafts/EmotionQuant_行动计划_采纳批判建议_20260209_2341.md`

---

## 3. 已归档文件（2026-02-28）

以下文件已移至 `Governance/archive/archive-old-plans-v5-20260228/`（原因：被新的路线图/执行卡取代，且原文存在大量不一致/错误口径）：

- `eq-improvement-plan-core-frozen.md` — 旧执行主计划（已被 `docs/roadmap.md` 取代）
- `enhancement-selection-analysis_claude-opus-max_20260210.md` — 旧选型论证（结论已融入执行卡）
- `debt-clearance-plan-v1.md` — 旧债务清偿计划（已被 R0-R9 卡内嵌步骤取代）

---

## 4. 边界说明

### 4.1 外挂允许操作的目录

`src/pipeline/`、`src/adapters/`、`tests/contracts/`、`tests/canary/`、`scripts/quality/`

### 4.2 外挂禁止事项

1. 修改 `docs/design/core-algorithms/**` 核心算法语义
2. 修改 `docs/design/core-infrastructure/**` 基础设施契约
3. 将技术指标对照结果接入交易触发链

---

## 5. 参考资料

- 重建路线图：`docs/roadmap.md`
- 执行卡：`docs/cards/`
- SOS 审计：`docs/sos/`
- 系统总览：`docs/system-overview.md`
- 核心算法设计：`docs/design/core-algorithms/`
- 核心基础设施设计：`docs/design/core-infrastructure/`
- 系统铁律：`Governance/steering/系统铁律.md`
