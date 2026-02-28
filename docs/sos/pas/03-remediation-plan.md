# PAS — 修复方案

总体方向：以设计 v3.2.0 为准，修订代码；保留代码中的向量化工程架构。

---

## 修复依赖关系

```
P1-01 (raw_daily_basic) ──┬──→ P0-06 (volume_quality 完整三子组件)
P1-02 (raw_limit_list)  ──┤
                           ├──→ P0-05 (行为因子 limit_up_flag)
                           └──→ P0-01 + P0-02 (牛股基因修正)

P0-03 + P0-04 (结构因子 trend) ←→ P0-05 (行为因子移除 trend)
P0-07 + P0-08 (breakout 窗口化) ──→ 结构因子完整

全部 P0 完成后 → P2 输出补全 → P3 文档
```

---

## 批次一：数据源补齐

### PAS-P1-01：读取 raw_daily_basic

**目标文件**: `pipeline.py:179-202`（数据加载区）

在 DuckDB 查询中 JOIN raw_daily_basic，提取 turnover_rate 字段。用真实值替换 `amount/(close×10000)` 近似。降级策略：表不存在时回退到近似并标记 quality_flag。

### PAS-P1-02：读取 raw_limit_list

**目标文件**: `pipeline.py:179-202`

新增 raw_limit_list 查询（当日 + 历史 120 日），构建 is_limit_up / is_touched_limit_up / limit_up_count_120d。降级策略：表不存在时回退到价格推断。

---

## 批次二：三因子公式对齐

### PAS-P0-01 + P0-02：牛股基因修正

**目标**: `pipeline.py:289-292`

```python
# 修正 max_pct_chg：去掉 /0.30 天花板
wmaxpct = wpct.clip(lower=0.0).rolling(120, min_periods=1).max()

# 修正权重：0.4/0.3/0.3
wbg = 0.4 * wlur + 0.3 * wnhr + 0.3 * wmaxpct
```

### PAS-P0-03 + P0-04：结构因子恢复 trend_continuity_ratio

**目标**: `pipeline.py:306-311`

```python
# 构建趋势延续宽表
w_trend = {}
for _w in (20, 60, 120):
    _tw = max(10, min(40, round(_w / 3)))
    w_trend[_w] = wuf.rolling(_tw, min_periods=1).mean().clip(0.0, 1.0)

# 修正结构因子公式
for _w in (20, 60, 120):
    w_str[_w] = 0.4 * _pos + 0.3 * w_trend[_w] + 0.3 * _bs  # _bs 来自 P0-07/08 修复
```

### PAS-P0-05：行为因子恢复设计组件

**目标**: `pipeline.py:435-436`

```python
# 移除 trend_comp，引入 limit_up_flag（来自 P1-02）
_lu_flag = np.where(_is_lu_real, 1.0, np.where(_is_tlu_real, 0.7, 0.0))

# 修正 pct_chg_norm 范围为 ±20%
wpcomp = ((wpct + 0.20) / 0.40).clip(0.0, 1.0)

# 修正权重
_beh_raw = 0.4 * _vq + 0.3 * wpcomp + 0.3 * _lu_flag
```

### PAS-P0-06：volume_quality 恢复完整计算

**目标**: `pipeline.py:314-315`

```python
_vol_ratio_norm = (wv / _wva_safe / 3.0).clip(0.0, 1.0)
_turnover_norm = (turnover_rate_wide / 12.0).clip(0.0, 1.0)  # 来自 P1-01
_intraday_retention = ((wc - wl) / (wh - wl).clip(lower=EPS)).clip(0.0, 1.0)
wvq = (0.60 * _vol_ratio_norm + 0.25 * _turnover_norm + 0.15 * _intraday_retention).clip(0.0, 1.0)
```

### PAS-P0-07 + P0-08：breakout 窗口化 + 简化

**目标**: `pipeline.py:295-303`

```python
# 新增 120d prev high
wh120p = whs1.rolling(120, min_periods=1).max()
w_breakout_ref = {20: wh20p, 60: wh60p, 120: wh120p}

# 在结构因子循环中用窗口对应的 ref
for _w in (20, 60, 120):
    _br = w_breakout_ref[_w]
    _bs = (wc - _br) / _br.abs().clip(lower=EPS)  # 简单比率，不做 clip
```

---

## 批次三：输出模型补全

### PAS-P2-01：主表补齐字段

stock_name（从 raw_stock_basic）、industry_code（同）、entry/stop/target（代码已计算，补写入 frame）

### PAS-P2-02：因子中间表补齐

在 factor_frame 构造中补齐剩余 12 个字段（第二批修复后变量已可用）

### PAS-P2-03：实现 pas_opportunity_log

读取前一交易日 stock_pas_daily 获取 prev_grade，比较确定 grade_change，写入日志表

---

## 批次四：文档与基线

### PAS-P3-01：更新 docstring

将 momentum/volume/pattern 改为 bull_gene/structure/behavior

### PAS-P3-02：落地 baseline parquet

每日计算完成后将三因子 mean/std 写入 `${DATA_PATH}/config/pas_zscore_baseline.parquet`

---

## OOP 重建目标结构

```
src/algorithms/pas/
├── pipeline.py      # 编排入口
├── service.py       # PasService
├── engine.py        # PasEngine（三因子计算 + 方向 + 等级 + 风险收益）
├── models.py        # StockPasDaily, PasFactorIntermediate, PasOpportunityLog
├── repository.py    # PasRepository
└── baseline.py      # Z-Score baseline 管理
```

保留向量化计算架构（pivot-based rolling, _vec_zscore, _vec_consecutive_at_end）。
