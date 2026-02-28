# PAS（个股机会系统）— SOS 审计总览

**范围**: `src/algorithms/pas/pipeline.py` vs `docs/design/core-algorithms/pas/` 设计文档 v3.2.0
**总差异**: 15 项（P0×8 / P1×2 / P2×3 / P3×2）

---

## 核心矛盾

**PAS 是全系统偏差最严重的模块。** 三因子公式全部偏离设计，需要完整重写因子计算逻辑。

代码模块注释仍保留早期概念命名（momentum/volume/pattern），表明代码基于更早版本实现后从未与 v3.2.0 设计对齐。

关键偏差：
1. **牛股基因因子**：子权重错误（0.4/0.4/0.2 应为 0.4/0.3/0.3），max_pct_chg 计算方式完全不同
2. **结构位置因子**：缺失 trend_continuity_ratio（设计 30% 权重的核心组件蒸发），权重从 0.4/0.3/0.3 变为 0.7/0.0/0.3
3. **行为确认因子**：三个组件中两个被替换（limit_up_flag → trend_comp, pct_chg ±20% → ±10%），权重全改
4. **volume_quality** 从三子组件复合退化为简单量比
5. **breakout_ref** 不随自适应窗口变化，120 日窗口参考价缺失

## 影响链

```
三因子公式全错
  → pas_score 不可信
  → opportunity_grade 不可信
  → Integration 层的个股推荐不可信
  → Backtest 回测的个股选择不可信
```

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 15 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估
- [03-remediation-plan.md](03-remediation-plan.md) — 完整修复方案
