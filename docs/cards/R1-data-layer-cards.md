# R1 数据层重建 — 执行卡

**阶段目标**：修复 14 项 SOS 偏差，L1/L2 数据完全可信。
**总工期**：5-7 天
**前置条件**：R0 完成
**SOS 覆盖**：docs/sos/data-layer 全部 14 项

---

## CARD-R1.1: 修复 P0-1~P0-3（快照统计错误）

**工作量**：1.5 天
**优先级**：P0（cascade 根因，污染全链路）
**SOS 映射**：DATA-P0-1, DATA-P0-2, DATA-P0-3

### 交付物

- [ ] 修复 `src/data/l2_pipeline.py` rise_count / fall_count 计算
  - **错误**：`(close - open) / open`（日内涨跌幅）
  - **正确**：`pct_chg`（日间涨跌幅，基于 pre_close）
  - 位置：L100-116
- [ ] 修复 strong_up / strong_down 阈值
  - **错误**：3% (0.03)
  - **正确**：5% (0.05)
  - 位置：L117-118
- [ ] 修复 touched_limit_up 缺失炸板统计
  - **错误**：`touched_limit_up = limit_up_count`（仅封板 U）
  - **正确**：`touched_limit_up = limit_up_count + limit_break_count`（U + Z）
  - 位置：L121
  - 需补充 `limit_break_count` 计算逻辑（从 raw_limit_list 读取 Z 类型）

### 验收标准

1. 跳空高开 5% 后微跌 0.1% 的标的：设计判涨（4.9%），代码判涨（而非判跌）
2. pct_chg = 4.5% 的标的：不计入 strong_up（而非计入）
3. 涨停板炸板（Z 类型）计入 touched_limit_up

### 技术要点

- `pct_chg` 来自 raw_daily 表的 `pct_chg` 字段，需确保 SimulatedTuShareClient 也返回此字段
- 炸板数据从 `raw_limit_list` 读取 `limit = 'Z'` 的记录

---

## CARD-R1.2: 修复 P0-4~P0-5（快照聚合错误）

**工作量**：1.5 天
**优先级**：P0（MSS/IRS 输入错误）
**SOS 映射**：DATA-P0-4, DATA-P0-5

### 交付物

- [ ] 修复 amount_volatility 算法
  - **错误**：全市场成交额横截面标准差 `std(amount)`
  - **正确**：个股成交额相对 20 日均值的偏离率 `(amount - ma20) / ma20`，再取全市场中位数
  - 位置：`l2_pipeline.py:123`
  - 需增加滚动窗口 20 日均值计算
- [ ] 修复行业估值聚合（PE/PB）五步全错
  - **错误**：`replace(0, NA) → mean()`
  - **正确**：过滤(>0, ≤1000) → Winsorize(1%-99%) → 中位数 → 样本<8沿用前值
  - 位置：`l2_pipeline.py:449-455`
  - 需增加前值缓存机制（读 DuckDB industry_snapshot 表的 t-1 值）

### 验收标准

1. amount_volatility 为市场活跃度偏离率（0-1 之间），而非绝对标准差（亿级）
2. 行业 PE 异常值（0 / >1000）被过滤，极值被 Winsorize 缩尾
3. 样本不足 8 只的行业使用前一日值，而非 0

### 技术要点

- Winsorize 使用 `scipy.stats.mstats.winsorize` 或手动实现百分位裁剪
- 前值回退需处理首日冷启动（无历史数据时返回全市场中位数）

---

## CARD-R1.3: 修复 P1-1~P1-2（缺失字段与防御）

**工作量**：1 天
**优先级**：P1（功能完整性）
**SOS 映射**：DATA-P1-1, DATA-P1-2, DATA-P1-3

### 交付物

- [ ] 补齐 8 个快照字段的真实计算
  - `new_100d_high_count` / `new_100d_low_count`：需读取 100 日历史 high/low
  - `continuous_limit_up_2d` / `continuous_limit_up_3d_plus`：需读取 raw_limit_list 多日数据
  - `continuous_new_high_2d_plus`：需多日新高判断
  - `high_open_low_close_count` / `low_open_high_close_count`：十字星形态
  - `yesterday_limit_up_today_avg_pct`：昨日涨停板今日平均涨幅
  - 位置：`l2_pipeline.py` 中 `_build_market_snapshot()`
- [ ] SimulatedTuShareClient 补齐 pre_close / change / pct_chg
  - 位置：`src/data/fetcher.py` SimulatedTuShareClient._daily()
  - 确保模拟环境与真实 TuShare 字段对齐
- [ ] 修复 limit vs limit_type 字段名不一致
  - 统一为 `limit`（与 TuShare API 一致）
  - 位置：`fetcher.py:164`, `l2_pipeline.py:104-106`

### 验收标准

1. 8 个字段不再始终为 0，使用真实历史数据计算
2. SimulatedTuShareClient 返回的 DataFrame 含 pre_close / change / pct_chg
3. 模拟环境与真实环境 limit 字段名一致，涨跌停统计不为 0

---

## CARD-R1.4: 修复 P1-4~P2 路径结构偏差

**工作量**：0.5 天
**优先级**：P2（规范性）
**SOS 映射**：DATA-P1-4, DATA-P1-5, DATA-P2-1~P2-4

### 交付物

- [ ] 字段命名对齐
  - TradeCalendar: `trade_date` → `cal_date`（或更新设计文档接受 `trade_date`）
  - IndustrySnapshot: 补充 `market_amount_total` / `style_bucket` 到设计文档
- [ ] Parquet 路径规范
  - 确认使用 `${parquet_path}/l1/raw_daily/{date}.parquet` 结构
  - 更新设计文档 data-layer-api.md §11.1 路径定义
- [ ] Ops 表存储策略
  - 当前单库 `emotionquant.duckdb` 可接受
  - 在设计文档补充"分库触发阈值"说明（如 ops 表 >100MB 时拆分）
- [ ] trade_cal 拉取优化
  - 改为按年度拉取完整交易日历（而非每次只拉单日）
  - 位置：`repositories/trade_calendars.py:24-27`

### 验收标准

1. 字段命名在代码和设计文档间一致（或明确标注差异原因）
2. trade_cal API 调用次数从每日 N 次降为每年 1 次
3. Parquet 文件按 l1/l2 分层存储

---

## CARD-R1.5: 补充 DataService OOP 门面

**工作量**：1 天
**优先级**：P1（架构对齐）
**前置依赖**：CARD-R0.1

### 交付物

- [ ] 创建 `src/data/service.py`
  - `DataService(BaseService)` 类
  - 构造函数注入 `config: Config`, `repository: DataRepository`
  - 方法：
    - `fetch_and_persist(trade_date: str) -> DataRunResult`
    - `get_market_snapshot(trade_date: str) -> MarketSnapshot`
    - `get_industry_snapshot(trade_date: str) -> pd.DataFrame`
    - `get_stock_gene_cache(trade_date: str) -> pd.DataFrame`
- [ ] 重构 `l1_pipeline.py` 和 `l2_pipeline.py`
  - 将业务逻辑抽取到 DataService
  - pipeline.py 仅保留编排代码（加载配置 → 调用 service → 持久化结果 → 输出日志）

### 验收标准

1. `DataService` 可被其他模块（MSS/IRS/PAS）导入使用
2. `l1_pipeline.py` 和 `l2_pipeline.py` 代码行数减少 50%+
3. 单元测试可 mock `DataRepository` 独立测试 service 逻辑

---

## CARD-R1.6: 契约测试 + 验证报告

**工作量**：1.5 天
**优先级**：P1（质量闭环）
**前置依赖**：CARD-R1.1~R1.5

### 交付物

- [ ] 契约测试 `tests/contracts/test_data_layer.py`
  - 检查 `market_snapshot` 表 28 字段完整性
  - 检查 `industry_snapshot` 表 PE/PB 值在合理范围（0-1000，中位数非零）
  - 检查 `stock_gene_cache` 表与 raw_daily 数据一致性
- [ ] 3 个交易日快照验证报告
  - 选择 3 个代表性交易日（如 2024-01-15 / 2024-06-30 / 2024-12-31）
  - 逐字段比对快照输出与设计公式
  - 输出验证报告：`artifacts/r1-validation-report.md`
  - 格式：每个字段一行，含 [实际值 / 预期值 / 偏差 / 判定]

### 验收标准

1. 契约测试在 3 个交易日上全部通过
2. 验证报告显示 14 项 P0/P1/P2 偏差全部修复
3. rise_count / fall_count / touched_limit_up / amount_volatility / industry_pe_ttm 五个关键字段 100% 正确

### 技术要点

- 契约测试使用 `pytest-dataframe` 或 `pandera` 做 schema 验证
- 验证报告可用 Markdown 表格 + 自动化脚本生成

---

## R1 阶段验收总览

完成以上 6 张卡后，需满足：

1. **P0 偏差清零**：5 项快照计算错误全部修复，MSS/IRS/PAS 输入数据可信
2. **P1 功能补齐**：8 个占位字段实现，SimulatedTuShareClient 字段对齐
3. **P2 规范达标**：路径/字段命名/API 调用优化完成
4. **OOP 架构**：DataService 门面可用，pipeline 仅做编排
5. **质量闭环**：契约测试通过 + 3 日验证报告无偏差

**下一步**：进入 R2 MSS 重建（12 项偏差，代码 OOP 化 + 文档修正）。
