# 数据层（Data Layer）— SOS 审计总览

**范围**: `src/data/` 全部代码 vs `docs/design/core-infrastructure/data-layer/` 四份设计文档
**总差异**: 14 项（P0×5 / P1×5 / P2×4）

---

## 核心矛盾

数据层是全系统的基底。5 项 P0 逻辑错误意味着 **L2 快照数据从源头就是错的**，后续所有算法（MSS/IRS/PAS）都在用失真的输入做计算。

关键错误：
- **涨跌计算口径错误**：用日内涨跌替代日间涨跌（`(close-open)/open` vs `pct_chg`）
- **大涨/大跌阈值错误**：3% vs 设计要求的 5%
- **行业估值聚合全部错误**：mean 替代 median，无 Winsorize，无样本不足回退
- **amount_volatility 语义错误**：横截面标准差 vs 时间序列偏离率
- **touched_limit_up 遗漏炸板统计**

## 影响链

```
L2 快照计算错误（P0 #1~#5）
  ↓
market_snapshot / industry_snapshot 数据失真
  ↓
MSS 温度 / IRS 行业评分 / PAS 基因库 → 全部受污染
  ↓
整条链路不可信
```

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 14 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估与影响分析
- [03-remediation-plan.md](03-remediation-plan.md) — 完整修复方案
