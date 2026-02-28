# MSS（市场情绪系统）— SOS 审计总览

**范围**: `src/algorithms/mss/` 全部代码 vs `docs/design/core-algorithms/mss/` 全部设计文档
**总差异**: 12 项（P0×3 / P1×2 / P2×2 / P3×5）

---

## 核心结论

**MSS 的核心算法公式实现完全正确。** 六因子计算、温度合成、Z-Score 归一化、周期状态机、趋势判定的代码与设计一致（13/13 公式核对通过）。

问题集中在两个方面：
1. **`mss-information-flow.md` 严重滞后** — 三处 P0 级矛盾（趋势判定写成冷启动版本、异常处理与安全约束冲突、组件图描绘了不存在的 OOP 架构）
2. **防御性机制不完整** — Z-Score baseline 永远硬编码、输入验证远松于设计约束

## 影响链

```
MSS 核心算法 ✅ 正确
  但 information-flow 文档可能误导后续开发
  且 Z-Score baseline 硬编码 → 长期统计偏移风险
  且 输入验证松 → 脏数据静默通过
```

MSS 本身的计算逻辑可信，但其输入来自数据层（有 5 项 P0 错误），因此 MSS 的输出在数据层修复前不可信。

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 12 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估与影响分析
- [03-remediation-plan.md](03-remediation-plan.md) — 完整修复方案
