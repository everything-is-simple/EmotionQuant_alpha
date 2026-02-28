# 数据层 — 修复方案

所有 14 项差异的完整修复方案。按修复顺序排列。

---

## 批次一：前置依赖清理

### DATA-P1-2 修复：SimulatedTuShareClient 补齐字段

**目标文件**: `src/data/fetcher.py` (SimulatedTuShareClient._daily)

在模拟数据生成中补齐 pre_close, change, pct_chg：
```
pre_close = open_price * random(0.95, 1.05)  # 模拟前收盘
change = close_price - pre_close
pct_chg = round(change / pre_close * 100, 4)
```

### DATA-P1-3 修复：统一 limit 字段名

**目标文件**: `src/data/fetcher.py`, `src/data/l2_pipeline.py`

1. SimulatedTuShareClient: `"limit_type": "U"` → `"limit": "U"`
2. l2_pipeline.py: `"limit_type" in limit_rows.columns` → `"limit" in limit_rows.columns`
3. 所有引用 `limit_type` 的地方统一为 `limit`

---

## 批次二：P0 核心逻辑修复

### DATA-P0-1 修复：rise/fall 计算口径

**目标文件**: `src/data/l2_pipeline.py`

将 `_build_market_snapshot()` 中的涨跌判断从日内变化改为日间变化：

```python
# 优先使用 TuShare 提供的 pct_chg
if "pct_chg" in working.columns:
    pct = working["pct_chg"]  # 单位：百分数（5.0 表示 5%）
elif "pre_close" in working.columns:
    pct = (working["close"] - working["pre_close"]) / working["pre_close"].replace(0, pd.NA) * 100
    pct = pct.fillna(0.0)
else:
    # 最后回退，标记 data_quality=degraded
    pct = (working["close"] - working["open"]) / working["open"].replace(0, pd.NA) * 100
    pct = pct.fillna(0.0)

rise_count = int((pct > 0).sum())
fall_count = int((pct < 0).sum())
flat_count = int((pct.abs() <= flat_threshold_pct).sum())  # flat_threshold 也要改为百分数单位
```

同步修复 `_build_industry_snapshot_sw31()` 和 `_build_industry_snapshot_all()` 中的同类逻辑。

### DATA-P0-2 修复：strong_up/down 阈值

**目标文件**: `src/data/l2_pipeline.py`

```python
# 修正阈值为 5%（pct_chg 单位是百分数）
strong_up_count = int((pct >= 5.0).sum())
strong_down_count = int((pct <= -5.0).sum())
```

### DATA-P0-3 修复：touched_limit_up 补炸板

**目标文件**: `src/data/l2_pipeline.py`

```python
if not limit_rows.empty and "limit" in limit_rows.columns:
    limit_col = limit_rows["limit"].astype(str)
    limit_up_count = int((limit_col == "U").sum())
    limit_down_count = int((limit_col == "D").sum())
    broken_limit_up_count = int((limit_col == "Z").sum())
    touched_limit_up = limit_up_count + broken_limit_up_count
```

### DATA-P0-4 修复：amount_volatility 时间序列偏离率

**目标文件**: `src/data/l2_pipeline.py`

```python
def _calc_amount_volatility(today_total_amount: float, config) -> float:
    """计算成交额相对 20 日均值的偏离率"""
    # 读取近 20 日的 market_snapshot
    recent_snapshots = _load_recent_market_snapshots(n_days=20, config=config)
    if len(recent_snapshots) < 2:
        return 0.0  # 冷启动，标记 data_quality=cold_start
    ma20_amount = sum(s.total_amount for s in recent_snapshots) / len(recent_snapshots)
    if ma20_amount == 0:
        return 0.0
    return (today_total_amount - ma20_amount) / ma20_amount
```

需要新增 `_load_recent_market_snapshots()` 函数，从 DuckDB 查询历史 market_snapshot 的 total_amount 字段。

### DATA-P0-5 修复：行业估值聚合

**目标文件**: `src/data/l2_pipeline.py`

```python
def _aggregate_industry_valuation(basic_subset: pd.DataFrame, industry_code: str, config) -> tuple:
    """严格按设计实现四步估值聚合"""
    # Step 1: 过滤
    valid_pe = basic_subset["pe_ttm"][(basic_subset["pe_ttm"] > 0) & (basic_subset["pe_ttm"] <= 1000)]
    valid_pb = basic_subset["pb"][basic_subset["pb"] > 0]

    # Step 2+3: Winsorize + 中位数（PE）
    if len(valid_pe) >= 8:
        q01, q99 = valid_pe.quantile([0.01, 0.99])
        industry_pe_ttm = float(valid_pe.clip(lower=q01, upper=q99).median())
    else:
        industry_pe_ttm = _load_prev_industry_value(industry_code, "industry_pe_ttm", config)

    # Step 2+3: Winsorize + 中位数（PB）
    if len(valid_pb) >= 8:
        q01, q99 = valid_pb.quantile([0.01, 0.99])
        industry_pb = float(valid_pb.clip(lower=q01, upper=q99).median())
    else:
        industry_pb = _load_prev_industry_value(industry_code, "industry_pb", config)

    return industry_pe_ttm, industry_pb
```

需要新增 `_load_prev_industry_value()` 函数，从 DuckDB 查询该行业上一交易日的估值。

---

## 批次三：功能补齐

### DATA-P1-1 修复：8 个 stub=0 字段

分两阶段：

**阶段 A（修完 P0-1 后可立即做）**：
- `high_open_low_close_count`: `open > pre_close * 1.02 and close < open * 0.94`
- `low_open_high_close_count`: 反向条件
- `yesterday_limit_up_today_avg_pct`: 读前一交易日 raw_limit_list 中的涨停股，计算今日平均 pct_chg

**阶段 B（需历史数据积累后）**：
- `new_100d_high_count`: 读 100 日 raw_daily 历史，比较 close vs max(close, 100d)
- `new_100d_low_count`: 同理
- `continuous_limit_up_2d` / `continuous_limit_up_3d_plus`: 读多日 limit_list
- `continuous_new_high_2d_plus`: 读多日计算结果

### DATA-P1-4 修复：设计文档对齐 trade_date

**目标文件**: `docs/design/core-infrastructure/data-layer/data-layer-data-models.md`

将 raw_trade_cal 表定义中的 `cal_date` 更新为 `trade_date`，与代码和其他表统一。

### DATA-P1-5 修复：反向补入 style_bucket / market_amount_total

**目标文件**: 设计文档三处
1. `data-layer-data-models.md` §3.2 — 新增字段定义
2. `data-layer-algorithm.md` §3.2 — 补充 style_bucket 计算逻辑
3. `data-layer-information-flow.md` — 补充数据流向

---

## 批次四：路径与结构优化

### DATA-P2-1：更新设计文档存储路径

反向更新设计文档，认可代码的 `/l1/`、`/l2/` 分层路径和 `raw_daily` 命名。

### DATA-P2-2：补充分库策略说明

在设计文档中补充：当前阶段 ops 表与业务表共用主库，待主库体积超过阈值时触发分库。

### DATA-P2-3：trade_cal 改为年度拉取

修改 `src/data/repositories/trade_calendars.py`，首次使用时拉取全年，后续命中本地缓存。

### DATA-P2-4：OOP 重建时解决

模块路径重组在 OOP 重建阶段（路线图 R1）按设计路径实现，当前不单独处理。

---

## OOP 重建目标结构

重建完成后，数据层模块应遵循设计的标准结构：

```
src/data/
├── pipeline.py          # 编排入口（L1 + L2 + L3 流水线调度）
├── service.py           # DataService（对外服务接口）
├── engine.py            # DataProcessor（L2 清洗/聚合引擎）
├── models.py            # 数据模型（MarketSnapshot, IndustrySnapshot, StockGene 等）
├── repository.py        # 仓储层（DuckDB + Parquet 读写）
├── clients/
│   ├── tushare_client.py   # TuShareClient（真实 + 模拟）
│   └── data_fetcher.py     # DataFetcher（重试 + 节流 + 缓存）
└── utils/
    └── code_converter.py   # 代码转换工具
```
