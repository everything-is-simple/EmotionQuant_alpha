# SOS — 系统代码与核心设计的差异急救方案（PAS篇）

**创建日期**: 2026-02-27
**状态**: 待审阅
**涉及设计**: `docs/design/core-algorithms/pas/` (v3.2.0)
**涉及代码**: `src/algorithms/pas/pipeline.py`

---

## 1. 背景

对 PAS（Price Action Signals）核心算法的设计文档与实际代码实现进行逐行对照审计后，发现 **15 项实质性偏差**。代码模块注释仍保留早期概念命名（momentum/volume/pattern），表明代码可能基于更早版本实现后，未完成与 v3.2.0 设计的全面对齐。

## 2. 偏差严重度分布

| 严重度 | 数量 | 含义 |
|--------|------|------|
| 🔴 P0 | 8 项 | 算法语义偏差 — 因子公式/权重/组件与设计不一致，直接影响评分结果 |
| 🟠 P1 | 2 项 | 数据源缺失 — 关键输入表未读取，用近似替代，影响准确性 |
| 🟡 P2 | 3 项 | 输出模型偏差 — 字段缺失/表未实现，影响下游消费与审计 |
| 🔵 P3 | 2 项 | 文档/基线 — 注释不匹配、baseline 机制未落地 |

## 3. 总体决策方向

### 核心判断：以设计为准，修订代码

理由：
1. 设计文档经过 **14 轮 review**（v3.0.0 → v3.2.0），逐项解决了铁律合规、量纲一致性、边界条件等问题
2. 设计中的因子体系（bull_gene/structure/behavior）有明确的**宏观方向互斥归属**和**验收口径**
3. 代码的因子命名（momentum/volume/pattern）、权重、组件均偏离设计，属于**未完成对齐**而非有意的设计变更

### 保留代码中的合理优化

代码中的以下工程实现应予保留：
- 向量化计算架构（pivot-based rolling，消除 groupby 瓶颈）
- `_vec_zscore` / `_vec_consecutive_at_end` 等高效辅助函数
- DuckDB 持久化流程与 artifact 产出机制

### 修复策略

采用 **分批修复** 策略，按依赖关系排序：

```
第一批 (P0-前置): 数据源补齐 → 才能正确计算因子
第二批 (P0-核心): 三因子公式/权重/组件对齐
第三批 (P1+P2):   输出模型补全 + 中间表字段
第四批 (P3):       文档注释 + baseline 机制
```

## 4. 文件索引

| 文件 | 内容 |
|------|------|
| [诊断清单.md](./诊断清单.md) | 15 项偏差的完整诊断（设计原文 vs 代码实际 vs 影响分析） |
| [急救方案.md](./急救方案.md) | 逐项修复方案、代码改动要点、依赖关系、风险评估 |

## 5. 关联文档

- 设计原文: `docs/design/core-algorithms/pas/pas-algorithm.md` (v3.2.0)
- 设计数据模型: `docs/design/core-algorithms/pas/pas-data-models.md` (v3.2.0)
- 设计信息流: `docs/design/core-algorithms/pas/pas-information-flow.md` (v3.2.0)
- 设计 API: `docs/design/core-algorithms/pas/pas-api.md` (v4.0.0)
- 实现代码: `src/algorithms/pas/pipeline.py`
