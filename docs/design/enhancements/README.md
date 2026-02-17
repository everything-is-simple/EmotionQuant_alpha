# 外挂增强设计目录

**最后更新**: 2026-02-17  
**状态**: 设计完成（代码未落地）

---

## 1. 目录定位

本目录存放 EmotionQuant 外挂增强设计文档，包含执行主计划、外挂选型论证以及历史草稿。

外挂增强的唯一存在价值：**服务核心算法链路**。如果一个外挂不能让核心链路跑得更稳、验得更准、坏了更容易定位，那就不该做。

---

## 2. 完整文件清单

### 2.1 正式文档（4 份，权威口径）

- **`eq-improvement-plan-core-frozen.md`**：执行主计划（唯一执行基线）  
  包含：冻结边界、技术基线、外挂白名单（ENH-01~11）、S0-S6 + 扩展微圈 S3a/S7a 实施路线、闭环模板

- **`enhancement-selection-analysis_claude-opus-max_20260210.md`**：外挂系统权威设计（选型论证输入）  
  包含：ENH-01~09 逐项裁决、工时估算、阶段排布、明确排除清单

- **`scheduler-orchestration-design.md`**：调度与编排设计（ENH-01 统一运行入口详设）  
  包含：DAG 任务依赖、数据就绪检查点、盘后/盘前调度窗口、重试与补偿策略

- **`monitoring-alerting-design.md`**：监控与告警设计（ENH-02/03 运维增强）  
  包含：全层监控范围、P0/P1/P2 告警级别、升级规则、失败重试策略

### 2.2 历史草稿（drafts/，仅供参考，不可作为权威引用）

- `drafts/对标开源A股量化系统批判_20260209_150147.md`
- `drafts/对标开源A股量化系统批判_修订版_20260209.md`
- `drafts/对标批判响应行动计划_20260209_233929.md`
- `drafts/EmotionQuant_行动计划_采纳批判建议_20260209_2341.md`

---

## 3. ENH 外挂概览（ENH-01~11）

| ENH | 名称 | 裁决 | 阶段 |
|-----|------|------|------|
| ENH-01 | 统一运行入口 CLI | 必留 | S0 |
| ENH-02 | 数据预检与限流 | 必留 | S0 |
| ENH-03 | 失败产物协议 | 必留 | S0+S4 |
| ENH-04 | 适配层契约测试 | 必留（分批） | S0-S4 |
| ENH-05 | 金丝雀数据包 | 必留 | S0 |
| ENH-06 | A/B/C 对照看板 | S3 最小版 | S3 |
| ENH-07 | L4 产物标准化 | 延后 | S5 |
| ENH-08 | 设计冻结检查 | S0 骨架+S6 全量 | S0+S6 |
| ENH-09 | Qlib 适配层 | 必留 | S3 |
| ENH-10 | 数据采集增强 | 必留 | S3a |
| ENH-11 | 定时调度器 | 必留 | S7a |

---

## 4. 使用指南

### 4.1 阅读顺序

1. **先读主计划**：`eq-improvement-plan-core-frozen.md`（了解做什么、怎么做、什么不能动）
2. **再读选型论证**：`enhancement-selection-analysis_claude-opus-max_20260210.md`（了解为什么这么做）
3. **需要溯源时**：查看 `drafts/` 与 `.reports/` 历史材料

### 4.2 主从关系

- **执行口径**：以主计划 `eq-improvement-plan-core-frozen.md` 为准
- **选型论证**：`enhancement-selection-analysis` 仅作论证输入，不单独构成执行入口
- **草稿**：`drafts/` 只能参考，不可作为权威引用

### 4.3 变更规则

1. 新一轮优化必须回写正式文档并补充变更记录
2. 不新增同类平行“正式主计划”
3. 临时草稿存入 `drafts/`，成熟后合并到正式文档

---

## 5. 边界说明

### 5.1 外挂允许操作的目录

`src/pipeline/`、`src/adapters/`、`tests/contracts/`、`tests/canary/`、`scripts/quality/`

### 5.2 外挂禁止事项

1. 修改 `docs/design/core-algorithms/**` 核心算法语义
2. 修改 `docs/design/core-infrastructure/**` 基础设施契约
3. 将技术指标对照结果接入交易触发链

---

## 6. 参考资料

- 系统总览：`docs/system-overview.md`
- 核心算法设计：`docs/design/core-algorithms/`
- 核心基础设施设计：`docs/design/core-infrastructure/`
- 系统铁律：`Governance/steering/系统铁律.md`
