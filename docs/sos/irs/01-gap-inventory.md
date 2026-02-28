# IRS — 差异清单

共 8 项差异。

---

## 致命（3 项）

### IRS-C1：估值因子归一化路径不一致

- **设计**: 先 z-score(-PE) → 先 z-score(-PB) → 按 style_bucket 权重加权 → 再 z-score，见 irs-algorithm.md §3.4 (行 177-179)
- **代码**: 原始 -PE 和 -PB 按权重直接加权 → 对组合结果做一次 z-score
- **位置**: `src/algorithms/irs/pipeline.py:498-533`, `calculator.py:189-224`
- **实锤**: `valuation_raw_series = w_pe * (-pe_series) + w_pb * (-pb_series)` — PE(10-100) 和 PB(1-10) 未经标准化直接相加，PE 主导结果

### IRS-C2：龙头因子归一化路径不一致

- **设计**: 先 z-score(leader_avg_pct) → 先 z-score(leader_limit_up_ratio) → 0.6/0.4 加权（无最终 z-score），见 irs-algorithm.md §3.5 (行 238-239)
- **代码**: 原始值 0.6/0.4 加权 → 对组合结果做 z-score
- **位置**: `src/algorithms/irs/pipeline.py:503-538`, `calculator.py:194-230`
- **实锤**: `leader_raw_series = 0.6 * top5_pct_avg + 0.4 * top5_limit_ratio` — 涨幅均值(连续)和涨停比率(离散)量纲不同

### IRS-C3：calculator.py 估值权重硬编码 0.5/0.5

- **设计+pipeline.py**: 按 style_bucket 查表（growth: 0.35/0.65, balanced: 0.50/0.50, value: 0.65/0.35）
- **calculator.py**: 硬编码 `0.5 * (-pe_series) + 0.5 * (-pb_series)`
- **位置**: `calculator.py:189-192`
- **根因**: TD-DA-001 抽取时遗漏了 STYLE_WEIGHTS 常量和 style_bucket 读取逻辑

---

## 中度（3 项）

### IRS-M1：基因库因子数据源语义偏差

- **设计**: 从 raw_daily + raw_limit_list 统计 3 年滚动窗口累计涨停/新高数，见 irs-algorithm.md §3.6 (行 254-268)
- **代码**: 使用 industry_snapshot 中的当日涨停/新高数，做 EWM(decay=0.9)
- **位置**: `pipeline.py:508-514`
- **差异本质**: 设计刻画"历史惯性"（3年累计），代码刻画"近期惯性"（日度 EWM 衰减）。在熊市/震荡市中差异显著。

### IRS-M2：market_amount_total 来源不一致

- **设计**: 从 industry_snapshot 的 `market_amount_total` 字段直读，见 irs-data-models.md §2.1
- **代码**: 自行 `groupby("trade_date")["industry_amount"].sum()`
- **位置**: `pipeline.py:406-410, 460-461`
- **风险**: 可能重复计算"ALL"聚合行；31行业汇总 ≠ 全市场成交额（未分类股票遗漏）

### IRS-M3：calculator.py quality_flag 缺少 stale_days 判断

- **设计+pipeline.py**: `stale_days > 0` → "stale"；`sample_days < 60` → "cold_start"；否则 "normal"
- **calculator.py**: 只检查 sample_days，跳过 stale_days
- **位置**: `calculator.py:262`
- **根因**: TD-DA-001 抽取遗漏

---

## 轻度（2 项）

### IRS-m1：代码输出了设计中不存在的列

- 额外字段：`irs_score`（industry_score 重复）、`recommendation`（硬编码阈值映射，无设计依据）、`data_quality/stale_days/source_trade_date`（snapshot 透传）、`contract_version`
- **位置**: `pipeline.py:713-741`
- **最大隐患**: `recommendation`（STRONG_BUY/BUY/HOLD/SELL/AVOID）与设计的 `allocation_advice`（超配/标配/减配/回避）语义冲突

### IRS-m2：gene_score docstring 提及不存在的"强势率"

- **位置**: `pipeline.py:9`
- **实际**: gene_score 只有涨停率 + 新高率两个子因子，无"强势率"
