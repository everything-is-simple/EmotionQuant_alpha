# Validation（因子与权重验证）— SOS 审计总览

**范围**: `src/algorithms/validation/pipeline.py` + `calibration.py` vs `docs/design/core-algorithms/validation/` v2.2.0
**总差异**: 13 项（致命×11 / 次要×2）

---

## 核心矛盾

> 设计是一个 **多因子截面验证 + 真实双窗口 WFA 回测** 系统；
> 代码是一个 **启发式相关系数代理 + 公式估算** 的简化评估。
> **架构级断裂**，不是微调可修复的偏差。

关键断裂：
1. **因子名零重叠**：设计定义 15 个因子（MSS×6 + IRS×6 + PAS×3），代码使用 4 个完全不同的自造因子名
2. **IC 语义错误**：设计要求"因子 vs 未来收益"截面 IC，代码计算的是"IRS 分数 vs PAS 分数"的相关性
3. **ICIR 公式错误**：设计 `mean_ic / std(ic)`，代码 `abs(IC) * sqrt(N)`
4. **WFA 纸上谈兵**：设计要求真实 OOS 回测，代码用启发式公式估算 expected_return/max_drawdown
5. **Regime 分类反转**：hot_or_volatile vs hot_stable 语义完全相反

## 影响链

```
Validation Gate 不可信
  → 可能放行错误权重，也可能错误阻断正确权重
  → Integration 使用的权重缺乏可靠验证
  → 整个推荐系统的权重基础不可信
```

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 13 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估
- [03-remediation-plan.md](03-remediation-plan.md) — 完整修复方案
