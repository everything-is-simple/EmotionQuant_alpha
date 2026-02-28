# IRS — 修复方案

---

## 批次一：归一化路径修复（C1 + C2）

C1 和 C2 是同一类问题，必须一起决策。方案：**代码向设计对齐**。

### IRS-C1 修复：估值因子 — 先 z 后合再 z

**目标文件**: `src/algorithms/irs/pipeline.py`, `calculator.py`

```python
# 替换 pipeline.py:498-533
# Step 1: PE 和 PB 各自独立 z-score
pe_score, pe_mean, pe_std = _score_with_history(
    value=float((-pe_series).iloc[-1]),
    history_series=-pe_series,
    baseline_map=baseline_map,
    baseline_key="irs_valuation_pe_raw",
)
pb_score, pb_mean, pb_std = _score_with_history(
    value=float((-pb_series).iloc[-1]),
    history_series=-pb_series,
    baseline_map=baseline_map,
    baseline_key="irs_valuation_pb_raw",
)
# Step 2: 按 style_bucket 权重加权组合
valuation_raw = w_pe * pe_score + w_pb * pb_score
# Step 3: 对组合结果再做 z-score（需构造历史 valuation_raw 序列）
valuation_score, val_mean, val_std = _score_with_history(
    value=valuation_raw,
    history_series=...,  # 历史 PE/PB score 的加权组合序列
    baseline_map=baseline_map,
    baseline_key="irs_valuation_raw",
)
```

需新增 baseline_key: `irs_valuation_pe_raw`, `irs_valuation_pb_raw`

### IRS-C2 修复：龙头因子 — 先 z 后合（无最终 z）

**目标文件**: `src/algorithms/irs/pipeline.py`, `calculator.py`

```python
# 替换 pipeline.py:503-538
# Step 1: 两个子因子各自 z-score
leader_pct_score, _, _ = _score_with_history(
    value=float(top5_pct_avg.iloc[-1]),
    history_series=top5_pct_avg,
    baseline_map=baseline_map,
    baseline_key="irs_leader_pct_avg",
)
leader_limit_score, _, _ = _score_with_history(
    value=float(top5_limit_ratio.iloc[-1]),
    history_series=top5_limit_ratio,
    baseline_map=baseline_map,
    baseline_key="irs_leader_limit_ratio",
)
# Step 2: 加权组合即为最终 leader_score（0-100凸组合，无需再 z-score）
leader_score = 0.6 * leader_pct_score + 0.4 * leader_limit_score
```

需新增 baseline_key: `irs_leader_pct_avg`, `irs_leader_limit_ratio`

---

## 批次二：calculator.py 对齐（C3 + M3）

### IRS-C3 修复：补 style_bucket 权重逻辑

**目标文件**: `src/algorithms/irs/calculator.py`

```python
# 引入 STYLE_WEIGHTS
from src.algorithms.irs.pipeline import STYLE_WEIGHTS

# 替换 calculator.py:189-192
style_bucket = str(item.get("style_bucket", "balanced") or "balanced").strip().lower()
w_pe, w_pb = STYLE_WEIGHTS.get(style_bucket, STYLE_WEIGHTS["balanced"])
# 然后用 C1 修复后的新归一化路径
```

### IRS-M3 修复：补 stale_days 判断

**目标文件**: `src/algorithms/irs/calculator.py`

```python
# 替换 calculator.py:262
stale_days = int(float(item.get("stale_days", 0) or 0))
quality_flag = "stale" if stale_days > 0 else ("cold_start" if sample_days < 60 else "normal")
```

---

## 批次三：数据源修复（M1 + M2）

### IRS-M1 修复：设计文档向代码对齐

**目标文件**: `docs/design/core-algorithms/irs/irs-algorithm.md` §3.6

修改设计为代码的实际方案：
```
数据来源：industry_snapshot（L2）
daily_limit_up_ratio = limit_up_count / stock_count
daily_new_high_ratio = new_100d_high_count / stock_count
gene_raw = 0.6 × EWM(daily_limit_up_ratio, decay=0.9) + 0.4 × EWM(daily_new_high_ratio, decay=0.9)
gene_score = normalize_zscore(gene_raw)
```

标注：后续可升级为方案 C（在 industry_snapshot 中预计算 3 年累计字段）。

### IRS-M2 修复：优先读 snapshot 字段

**目标文件**: `src/algorithms/irs/pipeline.py`

```python
# 优先从 snapshot 读 market_amount_total
if "market_amount_total" in history.columns:
    mat_by_date = history.groupby("trade_date")["market_amount_total"].first().to_dict()
    # 对缺失值回退到行业汇总
    fallback = history[history["industry_code"] != "ALL"].groupby("trade_date")["industry_amount"].sum().to_dict()
    market_amount_by_date = {dt: (mat_by_date[dt] if pd.notna(mat_by_date.get(dt)) and float(mat_by_date[dt]) > 0 else fallback.get(dt, 0.0)) for dt in set(list(mat_by_date.keys()) + list(fallback.keys()))}
else:
    market_amount_by_date = history[history["industry_code"] != "ALL"].groupby("trade_date")["industry_amount"].sum().to_dict()
```

---

## 批次四：轻度修复（m1 + m2）

### IRS-m1 修复：处理多余输出列

1. `recommendation` — **移除**。下游统一使用 `allocation_advice`。
2. `irs_score` — 在设计 DDL 中标注为兼容别名，等同 `industry_score`。
3. `data_quality/stale_days/source_trade_date/contract_version` — 在设计 DDL 中补充定义。

### IRS-m2 修复：docstring

```python
# pipeline.py:9 改为
#   6. gene_score — 基因（涨停率 + 新高率）
```

---

## OOP 重建目标结构

```
src/algorithms/irs/
├── pipeline.py      # 编排入口
├── service.py       # IrsService（对外接口）
├── engine.py        # IrsEngine（六因子计算 + 轮动状态机）
├── models.py        # IrsIndustrySnapshot, IrsIndustryDaily
├── repository.py    # IrsRepository（DuckDB 读写）
└── calculator.py    # 删除或合并到 engine.py（消除副本漂移问题）
```
