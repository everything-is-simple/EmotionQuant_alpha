# C3 🔴 calculator.py 估值因子硬编码 0.5/0.5，忽略 style_bucket

## 问题定位

- **设计文件**: `docs/design/core-algorithms/irs/irs-algorithm.md` §3.4 (line 194-198)
- **正确实现**: `src/algorithms/irs/pipeline.py` (line 496-501)
- **问题代码**: `src/algorithms/irs/calculator.py` (line 189-192)

## 差异描述

### 设计规定 + pipeline.py 正确实现

生命周期映射表：

| style_bucket | w_pe | w_pb |
|---|---|---|
| growth | 0.35 | 0.65 |
| balanced | 0.50 | 0.50 |
| value | 0.65 | 0.35 |

pipeline.py 正确读取 style_bucket 并使用 STYLE_WEIGHTS：
```python
# pipeline.py:496-501
style_bucket = str(item.get("style_bucket", "balanced") or "balanced").strip().lower()
w_pe, w_pb = STYLE_WEIGHTS.get(style_bucket, STYLE_WEIGHTS["balanced"])
valuation_raw_series = w_pe * (-pe_series) + w_pb * (-pb_series)
```

### calculator.py 的 bug

```python
# calculator.py:189-192
pe_series = pd.to_numeric(industry_hist["industry_pe_ttm"], errors="coerce").fillna(0.0)
pb_series = pd.to_numeric(industry_hist["industry_pb"], errors="coerce").fillna(0.0)
valuation_raw_series = 0.5 * (-pe_series) + 0.5 * (-pb_series)
```

硬编码 0.5/0.5，完全忽略 style_bucket。所有行业不论成长/价值/均衡风格，
估值权重完全相同。

## 根因

calculator.py 是 TD-DA-001 从 pipeline.py 抽取的副本。抽取时遗漏了：
1. `STYLE_WEIGHTS` 常量的引入
2. `style_bucket` 字段的读取
3. 动态权重查找逻辑

## 修复方案（唯一方案）

### 在 calculator.py 中对齐 pipeline.py 的逻辑

```python
# calculator.py — 在 import 区域增加 STYLE_WEIGHTS 引用
from src.algorithms.irs.pipeline import (
    ...,
    STYLE_WEIGHTS,  # 新增
)

# calculator.py — 替换 line 189-192
style_bucket = str(item.get("style_bucket", "balanced") or "balanced").strip().lower()
w_pe, w_pb = STYLE_WEIGHTS.get(style_bucket, STYLE_WEIGHTS["balanced"])
pe_series = pd.to_numeric(industry_hist["industry_pe_ttm"], errors="coerce").fillna(0.0)
pb_series = pd.to_numeric(industry_hist["industry_pb"], errors="coerce").fillna(0.0)
valuation_raw_series = w_pe * (-pe_series) + w_pb * (-pb_series)
```

**注意**：此修复要在 C1 修复之后进行。如果 C1 选择方案 A（先z后合再z），
则 calculator.py 也需要跟随 pipeline.py 采用新的归一化路径。

## 影响

- calculator.py 当前为"非主链调用路径"（irs-api.md §实现状态所述）
- 但作为 TD-DA-001 试点，预期会逐步替代 pipeline.py 中的直接计算
- 如果不修复，未来切换到 calculator 路径时会导致评分回退

## 风险

低。calculator.py 当前非主链，修复不影响生产流程。但必须修，否则成为定时炸弹。
