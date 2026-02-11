# EmotionQuant 全文档批判性审查 — 第 4 轮

**审查人**: Warp (Claude Opus)
**日期**: 2026-02-11
**轮次**: R4
**范围**: `docs/`（system-overview.md + module-index.md + naming-conventions.md）+ `docs/design/` READMEs（design/ + core-algorithms/ + core-infrastructure/ + enhancements/）= 7 个活跃文件
**累计**: R1 6 + R2 6 + R3 6（已修复）+ 本轮 1 = **19 项**

---

## 审查方法

逐文件精读 7 个文件，与以下权威源交叉对比：

- `docs/design/core-algorithms/` 各模块算法设计（冻结区）
- `Governance/steering/系统铁律.md` / `CORE-PRINCIPLES.md`
- R2 已修复的 CP 契约（CP-01/04/05/10 输入输出表名）
- 命名规范与 DDL 表名一致性

---

## 发现汇总

| ID | 优先级 | 文件 | 位置 | 问题 |
|---|---|---|---|---|
| P3-R4-01 | P3 | core-algorithms/README.md | L146 | "MMSS" 拼写错误，应为 "MSS" |

---

## 问题详述

### P3-R4-01 — core-algorithms/README.md "MMSS" 拼写错误

**位置**: `docs/design/core-algorithms/README.md` line 146

**当前**: `1. **情绪优先**：MMSS 是主信号来源，其他系统必须与情绪周期对齐`

**问题**: 系统名称为 "MSS"（Market Sentiment System），"MMSS" 是拼写错误。

**修复建议**: `MMSS` → `MSS`。

---

## 无问题确认（Clean Pass）

### system-overview.md ✅
- §3 八层架构完整（Data/Signal/Validation/Integration/Backtest/Trading/Analysis/GUI）
- §4.1 L2 含 `stock_gene_cache`（R25 已修复）
- §4 L3 含 `validation_gate_decision` + `validation_weight_plan`（R29 已修复）
- §5 回测引擎选型策略完整（Qlib 主选 + 向量化基线 + backtrader 兼容）
- §8 文档导航路径全部正确（含 SpiralRoadmap/draft/ 和 enhancements/ 主计划）

### module-index.md ✅
- §1 模块树结构与实际目录一致（core-algorithms 含 validation, core-infrastructure 不含）
- §2.4 Validation 路径 `docs/design/core-algorithms/validation/` 正确
- §2.5 Integration 输出描述含 Gate + 权重方案
- §5 CP-10 → Validation 映射正确

### naming-conventions.md ✅
- §1 七阶段+unknown 周期定义完整（R26 已修复）
- §5.1 推荐等级与 integration-algorithm.md §5 一致
- §8.2/8.3 Validation 五张表名与 DDL 完全一致（R30 已修复）：`validation_gate_decision`, `validation_weight_plan`, `validation_factor_report`, `validation_weight_report`, `validation_run_manifest`
- §9.3 `stock_code` / `ts_code` 内外统一规范完整（R27 已修复）

### docs/design/README.md ✅
- 三层结构（核心算法 / 核心基础设施 / 外挂增强）描述清晰
- 边界规则 4 条与 CORE-PRINCIPLES 一致

### core-algorithms/README.md ✅（除 P3-R4-01 拼写）
- 5 个模块完整、文件清单完整（5×4=20 个设计文档）
- §3.3 PAS 输入为 `stock_gene_cache (L2)` + `raw_daily (L1)`，与 CP-01/CP-04 契约一致
- §3.5 Integration 输入含 `validation_weight_plan`（与 R2-02 修复对齐）
- §4.2 算法链路流程图正确
- §5 冻结区/允许/禁止规则完整

### core-infrastructure/README.md ✅
- 5 个模块完整、文件清单完整
- §3.1 Data Layer 输出含 8 张 L1 表 + 3 张 L2 表（含 `stock_gene_cache`）
- §3.3 Trading 输入含 `validation_gate_decision`
- §4.3 核心算法与基础设施边界定义清晰
- §5.2 允许替换数据源/回测引擎/GUI 框架，禁止实现交易逻辑

### enhancements/README.md ✅
- 4 份正式文档全部存在且路径正确
- ENH-01~09 概览表与主计划一致
- 主从关系（执行口径 = 主计划，选型论证 = 输入，草稿 = 参考）清晰
- 外挂允许/禁止操作目录明确

---

## 统计

| 优先级 | 数量 | 编号 |
|--------|------|------|
| P3 | 1 | R4-01 |
| **合计** | **1** | |

**累计（R1-R4）**: 6 + 6 + 6 + 1 = **19 项**（R1-R3 全部已修复）

---

## 下一轮预告

R5 将检查 `docs/design/enhancements/` 正式文档（eq-improvement-plan-core-frozen.md + enhancement-selection-analysis + scheduler-orchestration-design + monitoring-alerting-design），共 4 个文件。
