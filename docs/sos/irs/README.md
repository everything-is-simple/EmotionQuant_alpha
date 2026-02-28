# IRS（行业轮动系统）— SOS 审计总览

**范围**: `src/algorithms/irs/pipeline.py` + `calculator.py` vs `docs/design/core-algorithms/irs/` 设计文档
**总差异**: 8 项（致命×3 / 中度×3 / 轻度×2）

---

## 核心矛盾

两大类问题：

### 1. 归一化路径分歧（C1, C2）— 数学不等价

设计要求"先 Z-Score 后加权组合"（先标准化到同一尺度再组合），代码实现为"先加权组合后 Z-Score"。

对于估值因子：PE（量级 10-100）和 PB（量级 1-10）直接加权时，PE 因量纲大而主导结果，PB 的权重形同虚设。style_bucket 的差异化权重也因此失效。

对于龙头因子：涨幅均值（连续值 -10%~+10%）和涨停比率（离散值 0/0.2/0.4/...）量纲不同，先合后 z 让离散跳变主导分布形态。

### 2. calculator.py 副本漂移（C3, M3）

`calculator.py` 是 pipeline.py 的 TD-DA-001 试点抽取副本，但抽取时丢失了 style_bucket 映射和 stale_days 判断。

## 影响链

```
归一化路径错误（C1, C2）
  → 六因子中的估值因子和龙头因子得分失真
  → industry_score 不可靠
  → Integration 层的行业推荐不可信
```

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 8 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估
- [03-remediation-plan.md](03-remediation-plan.md) — 完整修复方案
