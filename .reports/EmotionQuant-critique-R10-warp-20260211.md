# EmotionQuant 文档检查报告 — R10

**检查工具**: Warp (claude 4.6 opus max)
**检查时间**: 2026-02-11
**检查范围**: `docs/design/core-algorithms/pas/`（4 文件）+ `docs/design/core-algorithms/integration/`（4 文件）= 8 文件
**累计轮次**: R1–R10（R1–R9 已修复 37 项）

---

## 检查范围

| # | 文件 | 结果 |
|---|------|------|
| 1 | pas/pas-algorithm.md | ✅ Clean Pass |
| 2 | pas/pas-api.md | ✅ Clean Pass |
| 3 | pas/pas-data-models.md | ✅ Clean Pass |
| 4 | pas/pas-information-flow.md | ✅ Clean Pass |
| 5 | integration/integration-algorithm.md | ✅ Clean Pass |
| 6 | integration/integration-api.md | ⚠️ 见 P3-R10-04 |
| 7 | integration/integration-data-models.md | ⚠️ 见 P2-R10-02 |
| 8 | integration/integration-information-flow.md | ⚠️ 见 P2-R10-01, P2-R10-03 |

---

## 问题清单

### P2-R10-01 | integration-information-flow.md §2.7：中性度公式使用简单平均而非加权

**位置**: integration-information-flow.md §2.7 综合中性度计算

**现状**:
```text
neutrality = (mss_neut + irs_neut + pas_neut) / 3
```

**算法定义**（integration-algorithm.md §7.1）:
```text
neutrality = (mss_neut × w_mss + irs_neut × w_irs + pas_neut × w_pas)
          × consistency_factor
          × mss_neutrality_risk_factor
```

信息流使用 `/3` 简单平均，遗漏了：(a) 权重三元组加权 `× w_mss/w_irs/w_pas`，(b) 一致性系数，(c) MSS风险因子。

**修复方案**: 对齐为加权公式 `mss_neut × w_mss + irs_neut × w_irs + pas_neut × w_pas`，并加上 `× consistency_factor × mss_neutrality_risk_factor`。

---

### P2-R10-02 | integration-data-models.md L319：验证模块链接路径错误

**位置**: integration-data-models.md §关联文档 L319

**现状**: `[factor-weight-validation-data-models.md](../../validation/factor-weight-validation-data-models.md)`

**问题**: integration-data-models.md 位于 `core-algorithms/integration/`，Validation 位于 `core-algorithms/validation/`，相对路径应为 `../validation/` 而非 `../../validation/`。

**修复方案**: 改为 `[factor-weight-validation-data-models.md](../validation/factor-weight-validation-data-models.md)`。

---

### P2-R10-03 | integration-information-flow.md §2.6：缺少 `mss_cycle=unknown` → HOLD 降级规则

**位置**: integration-information-flow.md §2.6 Step 6 信号生成

**现状**: 仅列出标准映射（STRONG_BUY/BUY/HOLD/SELL/AVOID），未包含 `mss_cycle=unknown` 时的降级规则。

**算法定义**（integration-algorithm.md §5.1 补充规则）:
> 当 `mss_cycle = unknown` 时，推荐等级强制降级为 `HOLD`（观察模式，不产生积极买入信号）。

**修复方案**: 在 §2.6 映射规则后补充：
```text
if mss_cycle == "unknown" and recommendation in {"STRONG_BUY", "BUY"}:
    recommendation = "HOLD"
```

---

### P3-R10-04 | integration-api.md §2.2/§2.3：节编号顺序不合理

**位置**: integration-api.md §2

**现状**: §2.3 数据仓库接口 排在 §2.2 Validation 桥接调用约定 之前（原文 §2.3 在 §2.2 上方）。

**问题**: 数据仓库接口（CRUD）应在桥接调用之前定义，当前顺序导致读者先看到依赖项（桥接）再看到基础接口（仓库）。

**修复方案**: 交换 §2.2 和 §2.3 的位置，使仓库接口先于桥接约定。

---

## 统计

| 等级 | 本轮 | 累计 (R1–R10) |
|------|------|---------------|
| P1 | 0 | 1 |
| P2 | 3 | 19 |
| P3 | 1 | 20 |
| **合计** | **4 项** | **41 项** |

---

## Clean Pass 确认（5 / 8 文件）

**PAS 全部通过**：
- pas-algorithm.md ✅ — 三因子体系完整，铁律合规声明到位，Z-Score 统一
- pas-api.md ✅
- pas-data-models.md ✅
- pas-information-flow.md ✅

**Integration 部分通过**：
- integration-algorithm.md ✅ — Gate 前置、协同约束、双模式设计完整

---

## 交叉验证确认

- PAS 三因子权重（20%+50%+30%=100%）在 algorithm/data-models/info-flow 一致 ✓
- PAS `stock_gene_cache` (L2) + `raw_daily` (L1) 输入与 Data Layer 对齐 ✓
- Integration `WeightPlan` 类型（integration-data-models.md §2.5）与 Validation API `resolve_weight_plan()` 返回类型一致 ✓
- Integration `IntegratedRecommendation` DDL 与 Data Layer `integrated_recommendation` DDL 字段完全对齐 ✓

---

## 下一轮预告

**R11** 预计范围: `docs/design/core-algorithms/validation/`（4 文件）
