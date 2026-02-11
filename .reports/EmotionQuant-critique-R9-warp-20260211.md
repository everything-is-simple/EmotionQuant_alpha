# EmotionQuant 文档检查报告 — R9

**检查工具**: Warp (claude 4.6 opus max)
**检查时间**: 2026-02-11
**检查范围**: `docs/design/core-algorithms/mss/`（4 文件）+ `docs/design/core-algorithms/irs/`（4 文件）= 8 文件
**累计轮次**: R1–R9（R1–R8 已修复 34 项）

---

## 检查范围

| # | 文件 | 结果 |
|---|------|------|
| 1 | mss/mss-algorithm.md | ✅ Clean Pass |
| 2 | mss/mss-api.md | ✅ Clean Pass |
| 3 | mss/mss-data-models.md | ✅ Clean Pass |
| 4 | mss/mss-information-flow.md | ✅ Clean Pass |
| 5 | irs/irs-algorithm.md | ⚠️ 见 P2-R9-02, P3-R9-03 |
| 6 | irs/irs-api.md | ✅ Clean Pass |
| 7 | irs/irs-data-models.md | ✅ Clean Pass |
| 8 | irs/irs-information-flow.md | ⚠️ 见 P2-R9-01 |

---

## 问题清单

### P2-R9-01 | irs-information-flow.md §Step 4：公式与算法文档不对齐

**位置**: irs-information-flow.md §Step 4 增强因子计算

三处与 irs-algorithm.md 公式不一致：

1. **连续性因子**：`net_new_high` → 应为 `net_new_high_ratio`（算法统一用 `_ratio` 后缀）
2. **龙头因子**：
   - `leader_limit_ratio` → 应为 `leader_limit_up_ratio`（统一 `_ratio` 后缀）
   - `normalize()` / `scale()` → 应统一为 `normalize_zscore()`（与算法层 Z-Score 规范一致）
3. **行业基因库**：
   - `history_limit_up` / `history_new_high` 缺少 ratio 转换步骤
   - 缺少 `gene_raw` 中间变量和 `normalize_zscore(gene_raw)` 最终映射

**修复方案**: 对齐 irs-algorithm.md §3.2/§3.5/§3.6 的公式命名与归一化方法。

---

### P2-R9-02 | irs-algorithm.md §8.1：残留 `valuation_smooth` 参数

**位置**: irs-algorithm.md §8.1 参数配置表

参数表中仍保留 `valuation_smooth = 0.3`（估值平滑系数），但当前估值因子 §3.4 公式为：

```text
valuation_raw = -industry_pe_ttm
valuation_score = normalize_zscore(valuation_raw)
```

不使用任何平滑系数。`valuation_smooth` 属于历史版本残留。

**修复方案**: 从参数表中移除 `valuation_smooth` 行。

---

### P3-R9-03 | irs-algorithm.md §3.2：`net_new_high` 命名不一致

**位置**: irs-algorithm.md §3.2 连续性因子定义

- L126: `net_new_high = new_high_ratio - new_low_ratio` — 缺少 `_ratio` 后缀
- L131: `Σ(net_new_high, window=5)` — 同上

该变量由两个 ratio 相减得到，结果本身也是 ratio，应命名为 `net_new_high_ratio`，与 `rise_ratio`/`fall_ratio`/`new_high_ratio`/`new_low_ratio` 命名体系一致。

**修复方案**: `net_new_high` → `net_new_high_ratio`（定义行和公式引用行均需更新）。

---

## 统计

| 等级 | 本轮 | 累计 (R1–R9) |
|------|------|--------------|
| P1 | 0 | 1 |
| P2 | 2 | 16 |
| P3 | 1 | 19 |
| **合计** | **3 项** | **37 项** |

---

## Clean Pass 确认（6 / 8 文件）

**MSS 全部通过**：
- mss-algorithm.md ✅ — 六因子体系完整，互斥边界清晰，Z-Score 归一化统一
- mss-api.md ✅
- mss-data-models.md ✅
- mss-information-flow.md ✅

**IRS 部分通过**：
- irs-api.md ✅
- irs-data-models.md ✅

---

## 交叉验证确认

- MSS 六因子权重（85%基础+15%增强）在 algorithm/data-models/info-flow 三文件一致 ✓
- IRS 六因子权重（25%+20%+20%+15%+12%+8%=100%）三文件一致 ✓
- 两模块 `neutrality` 语义（0=极端, 1=中性）与 Integration 口径对齐 ✓
- 两模块 `normalize_zscore()` 映射规则（[-3σ,+3σ]→[0,100]）一致 ✓

---

## 下一轮预告

**R10** 预计范围: `docs/design/core-algorithms/pas/`（4 文件）+ `integration/`（4 文件）= 8 文件
