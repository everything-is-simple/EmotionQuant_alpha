# 数据层 — 差异清单

共 14 项差异，按严重程度分组。

---

## P0 逻辑错误（5 项）

### DATA-P0-1：rise_count / fall_count 计算口径错误

- **设计**: `pct_chg`（日间涨跌幅，基于 pre_close），见 data-layer-algorithm.md §3.1
- **代码**: `(close - open) / open`（日内涨跌幅）
- **位置**: `src/data/l2_pipeline.py:100-116`
- **实锤**: 跳空高开 5% 后微跌时，设计判涨，代码判跌。rise/fall 统计系统性失真。

### DATA-P0-2：strong_up / strong_down 阈值错误

- **设计**: 大涨 `pct_chg > 5%`，大跌 `pct_chg < -5%`，见 data-layer-algorithm.md §3.1
- **代码**: 阈值用的 3%（0.03）
- **位置**: `src/data/l2_pipeline.py:117-118`
- **实锤**: `strong_up_count=int((pct >= 0.03).sum())` — 明确写的 0.03
- **叠加**: 即使改为 5%，基数 pct 也是错的（见 P0-1）

### DATA-P0-3：touched_limit_up 缺失炸板（Z）统计

- **设计**: `touched_limit_up` = 封板(U) + 炸板(Z)，见 data-layer-data-models.md §3.1
- **代码**: `touched_limit_up = limit_up_count`（仅 U）
- **位置**: `src/data/l2_pipeline.py:121`
- **实锤**: 直接赋值 `touched_limit_up=limit_up_count`，完全遗漏 Z 类型

### DATA-P0-4：amount_volatility 算法错误

- **设计**: 成交额相对 20 日均值的偏离率 `(amount - ma20) / ma20`，见 data-layer-data-models.md §3.1
- **代码**: 当日全市场成交额的横截面标准差 `std(ddof=0)`
- **位置**: `src/data/l2_pipeline.py:123`
- **实锤**: `amount_volatility=float(working["amount"].std(ddof=0))` — 完全不同的统计量

### DATA-P0-5：行业估值聚合口径错误（PE/PB）

- **设计**: 过滤(>0, ≤1000) → Winsorize(1%-99%) → 中位数 → 样本<8沿用前值，见 data-layer-algorithm.md §3.2
- **代码**: 替换0为NA → 取均值 → 无前值回退
- **位置**: `src/data/l2_pipeline.py:449-455`
- **实锤**: `industry_pe_ttm = float(basic_subset["pe_ttm"].replace(0.0, pd.NA).mean() or 0.0)` — 五步全错

---

## P1 功能与命名（5 项）

### DATA-P1-1：8 个快照字段始终为 0（stub 未实现）

- **设计**: new_100d_high_count, new_100d_low_count, continuous_limit_up_2d, continuous_limit_up_3d_plus, continuous_new_high_2d_plus, high_open_low_close_count, low_open_high_close_count, yesterday_limit_up_today_avg_pct
- **代码**: 全部始终返回 0
- **位置**: `src/data/l2_pipeline.py` 中 `_build_market_snapshot()`
- **原因**: 部分需要历史数据（100日/多日），部分需要 pre_close（修 P0-1 后可做）

### DATA-P1-2：SimulatedTuShareClient 缺少 pre_close / change / pct_chg

- **设计**: raw_daily 字段列表含 pre_close, change, pct_chg，见 data-layer-data-models.md §2.1
- **代码**: SimulatedTuShareClient._daily() 返回中缺失这 3 个字段
- **位置**: `src/data/fetcher.py` SimulatedTuShareClient
- **后果**: P0-1 修复的前置依赖。模拟环境下无法测试真实计算路径。

### DATA-P1-3：涨跌停字段名 limit vs limit_type（生产隐患）

- **设计**: 字段名 `limit`（与 TuShare API 一致），见 data-layer-data-models.md §2.3
- **代码**: 使用 `limit_type`
- **位置**: `src/data/fetcher.py:164`, `src/data/l2_pipeline.py:104-106`
- **后果**: 模拟环境正常，**真实 TuShare 环境下字段匹配不上**，涨跌停统计全部为 0

### DATA-P1-4：TradeCalendar 字段名 cal_date vs trade_date

- **设计**: `cal_date`，见 data-layer-data-models.md §2.8
- **代码**: `trade_date`，在 `_normalize_fields()` 中做了重命名
- **位置**: `src/data/models/entities.py:29`, `src/data/fetcher.py:340-343`
- **性质**: 有意的标准化行为，需要设计文档反向对齐

### DATA-P1-5：IndustrySnapshot 代码多出字段（market_amount_total / style_bucket）

- **设计**: 不存在这两个字段
- **代码**: `market_amount_total: float`, `style_bucket: str`
- **位置**: `src/data/models/snapshots.py:126-127`
- **性质**: 合理的超额实现（行业成交额占比、风格分桶），需反向补入设计

---

## P2 路径与结构（4 项）

### DATA-P2-1：Parquet 存储路径多了 l1/l2 层级

- **设计**: `${DATA_PATH}/parquet/daily/{date}.parquet`
- **代码**: `${parquet_path}/l1/raw_daily/{date}.parquet`（多了 `/l1/`，名改为 `raw_daily`）
- **位置**: `src/data/repositories/base.py:142`, `src/data/l2_pipeline.py:708`
- **性质**: 代码的分层路径更清晰，建议设计反向对齐

### DATA-P2-2：Ops 表存储在主库而非独立 ops.duckdb

- **设计**: ops 表放在独立的 `ops.duckdb`，见 data-layer-api.md §11.2
- **代码**: 与业务表共用 `emotionquant.duckdb`
- **位置**: `src/data/l1_pipeline.py:226`
- **性质**: 当前数据量下单库合理。设计文档需补充"分库触发阈值"说明。

### DATA-P2-3：trade_cal 拉取范围（单日 vs 年度）

- **设计**: 按年度拉取完整交易日历，见 data-layer-algorithm.md §2.1.1
- **代码**: 每次只拉单日
- **位置**: `src/data/repositories/trade_calendars.py:24-27`
- **后果**: 浪费 API 配额，无法判断未来日期是否为交易日

### DATA-P2-4：API 模块路径（规划 vs 实际）

- **设计**: 规划了 `services/tushare_client`, `services/data_fetcher`, `repositories/MarketSnapshotRepo` 等
- **代码**: 实际为 `fetcher.py`（紧凑组织）, L2/L3 仓储未实现
- **性质**: 设计 API 文档已注明"多数为规划接口"。OOP 重建时按设计路径实现。
