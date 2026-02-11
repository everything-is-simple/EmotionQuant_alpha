# EmotionQuant 全文档批判性审查 — 第 2 轮

**审查人**: Warp (Claude Opus)
**日期**: 2026-02-11
**轮次**: R2
**范围**: `Governance/Capability/` 12 个活跃文件（SPIRAL-CP-OVERVIEW + SPIRAL-TASK-TEMPLATE + CP-01~CP-10）× 与设计文档交叉一致性
**累计**: R1 6 项（已修复）+ 本轮 6 项 = **12 项**

---

## 审查方法

逐文件精读 Capability 目录全部 12 个活跃文件，与以下权威源交叉对比：

- `docs/design/core-algorithms/` 各模块算法设计（冻结区）
- `docs/design/core-algorithms/validation/factor-weight-validation-data-models.md`（Validation DDL 权威）
- `docs/design/core-algorithms/README.md`（核心算法 README，模块职责与输入输出）
- `Governance/steering/6A-WORKFLOW.md`（同步清单权威）

重点检查：CP 输入输出契约与设计文档对齐、表名一致性、同步清单匹配。

---

## 发现汇总

| ID | 优先级 | 文件 | 位置 | 问题 |
|---|---|---|---|---|
| P2-R2-01 | P2 | CP-10-validation.md | §2.2 (lines 27-32) | 输出仅列 3 张表，设计定义 5 张（缺 validation_weight_plan + validation_run_manifest） |
| P2-R2-02 | P2 | CP-05-integration.md | §2.1 (lines 19-24) | 输入缺 validation_weight_plan：Integration 需要权重桥接对象，不仅是 Gate 决策 |
| P2-R2-03 | P2 | CP-10 / CP-09 | §2.2 / §2.1 | 表名 word-order 与 DDL 不一致：CP 用 `factor_validation_report`，DDL 用 `validation_factor_report` |
| P2-R2-04 | P2 | SPIRAL-TASK-TEMPLATE.md | §7 (lines 66-70) | 同步清单缺 `SPIRAL-CP-OVERVIEW.md`；误含 `review.md`（属 A5 产物，非 A6 同步） |
| P2-R2-05 | P2 | CP-01-data-layer.md | §2.2 (lines 26-30) | 输出缺 `stock_gene_cache`（L2），core-algorithms README 明确列为 PAS 输入 |
| P3-R2-06 | P3 | CP-01-data-layer.md | §2.2 (line 28) | `raw_*` 消费方列表缺 CP-10（Validation 明确依赖 CP-01 的 future_returns / trade_calendar） |

---

## 问题详述

### P2-R2-01 — CP-10 输出遗漏 2 张表

**位置**: `Governance/Capability/CP-10-validation.md` §2.2 lines 27-32

**当前**: 输出表 3 行：
- `factor_validation_report`
- `weight_validation_report`
- `validation_gate_decision`

**问题**: Validation 设计文档 `factor-weight-validation-data-models.md` 定义了 5 个核心数据模型（§1.2-§1.6），其中 2 个未在 CP 输出中列出：
1. `ValidationWeightPlan`（§1.5）→ DuckDB 表 `validation_weight_plan`：Validation→Integration 的权重桥接对象，Integration 需按 `(trade_date, plan_id)` 解析权重
2. `ValidationRunManifest`（§1.6）→ DuckDB 表 `validation_run_manifest`：运行记录，治理审计依赖

**修复建议**: §2.2 输出表补充 2 行：

```
| `validation_weight_plan` | CP-05 | 权重桥接可解析 |
| `validation_run_manifest` | 治理 | 运行记录可审计 |
```

---

### P2-R2-02 — CP-05 输入缺权重桥接

**位置**: `Governance/Capability/CP-05-integration.md` §2.1 lines 19-24

**当前**: 输入来自 CP-10 的仅 `validation_gate_decision`。

**问题**: Integration 算法设计 §3.1 `resolve_gate_and_weights()` 需要 `ValidationGateDecision.selected_weight_plan` 来定位 `validation_weight_plan` 表中的权重方案。CP-05 输入应显式列出 `validation_weight_plan`，否则契约不完整。

**修复建议**: §2.1 表格增加一行：

```
| `validation_weight_plan` | CP-10 | 对应 plan_id 可解析 | P0 |
```

---

### P2-R2-03 — CP-10 / CP-09 表名 word-order 与 DDL 不一致

**位置**:
- `CP-10-validation.md` §2.2 lines 30-31
- `CP-09-analysis.md` §2.1 line 23

**当前**: CPs 使用 `factor_validation_report` / `weight_validation_report`。

**问题**: DDL 权威定义（`factor-weight-validation-data-models.md` §3.1-§3.2）表名为：
- `validation_factor_report`（DDL line 175）
- `validation_weight_report`（DDL line 200+）

word-order 不同：`factor_validation_*` vs `validation_factor_*`。DDL 为权威。

**修复建议**: CP-10 §2.2 和 CP-09 §2.1 统一改为 `validation_factor_report` / `validation_weight_report`。

---

### P2-R2-04 — SPIRAL-TASK-TEMPLATE §7 同步清单不匹配

**位置**: `Governance/Capability/SPIRAL-TASK-TEMPLATE.md` §7 lines 66-70

**当前**:
```
- [ ] review.md 已更新
- [ ] final.md 已更新
- [ ] development-status.md 已更新
- [ ] debts.md 已更新（如有）
- [ ] reusable-assets.md 已更新（如有）
```

**问题**:
1. `review.md` 是 A5 Archive 阶段产物，不属于 A6 Advance 同步项
2. 缺少 `SPIRAL-CP-OVERVIEW.md`（6A-WORKFLOW §A6 第 5 项）

**修复建议**:
```
- [ ] final.md 已更新
- [ ] development-status.md 已更新
- [ ] debts.md 已更新（如有）
- [ ] reusable-assets.md 已更新（如有）
- [ ] SPIRAL-CP-OVERVIEW.md 已更新
```

（`review.md` 可移至 §6 验收门禁或 §5 执行命令之后，作为 A5 产物检查项。）

---

### P2-R2-05 — CP-01 输出缺 stock_gene_cache

**位置**: `Governance/Capability/CP-01-data-layer.md` §2.2 lines 26-30

**当前**: 输出仅列 `raw_*`、`market_snapshot`、`industry_snapshot`。

**问题**: `docs/design/core-algorithms/README.md` §3.3 明确：PAS 输入为 `stock_gene_cache (L2)` + `raw_daily (L1)`。`stock_gene_cache` 是 Data Layer 作为 L2 输出的关键特征表（`system-overview.md` §4.1 L2 定义亦含此表），但 CP-01 输出契约未列出。

**修复建议**: §2.2 输出表补充：

```
| `stock_gene_cache` | CP-04 | 字段完整 |
```

---

### P3-R2-06 — CP-01 raw_* 消费方缺 CP-10

**位置**: `Governance/Capability/CP-01-data-layer.md` §2.2 line 28

**当前**: `raw_* parquet` 消费方列 `CP-02/03/04/06/07`。

**问题**: CP-10 §2.1 明确列出 `future_returns | CP-01` 和 `prices / trade_calendar | CP-01`，CP-10 确实消费 CP-01 raw 数据，但未被列为消费方。

**修复建议**: 消费方改为 `CP-02/03/04/06/07/10`。

---

## 无问题确认（Clean Pass）

- **SPIRAL-CP-OVERVIEW §4 主路线 S0-S6**: CP 组合与模块依赖链一致 ✅
- **SPIRAL-CP-OVERVIEW §5 CP 映射表**: 10 个 CP 文件名全部正确对应 ✅
- **SPIRAL-CP-OVERVIEW §7 最小同步**: 5 项与 6A-WORKFLOW/CORE-PRINCIPLES/GOVERNANCE-STRUCTURE 一致 ✅
- **CP-02/03/04 Exit Gate 铁律引用**: 均含"单指标不得独立决策"检查 ✅
- **CP-05 Validation Gate 前置**: Entry Gate 含"验证 Gate 非 FAIL"✅
- **CP-06/07 A 股规则**: 均含 T+1/涨跌停检查 ✅
- **CP-08 GUI 只读**: 定位明确为展示，不执行算法 ✅
- **CP 文件结构一致性**: 全部 10 个 CP 统一 6 节结构（定位/契约/Slice/Gate/风险/更新条件）✅
- **归档说明**: SPIRAL-CP-OVERVIEW §9 指向正确归档路径 ✅

---

## 统计

| 优先级 | 数量 | 编号 |
|--------|------|------|
| P2 | 5 | R2-01, R2-02, R2-03, R2-04, R2-05 |
| P3 | 1 | R2-06 |
| **合计** | **6** | |

**累计（R1-R2）**: 6 + 6 = **12 项**（R1 全部已修复）

---

## 下一轮预告

R3 将检查 `Governance/record/`（development-status.md + debts.md + reusable-assets.md）+ `Governance/specs/spiral-s0/`（requirements.md + review.md + final.md）+ `Governance/SpiralRoadmap/draft/`，共约 8 个文件。
