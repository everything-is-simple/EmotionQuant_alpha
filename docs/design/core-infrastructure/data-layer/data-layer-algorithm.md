# Data Layer 数据管线设计

**版本**: v3.1.6（重构版）
**最后更新**: 2026-02-19
**状态**: 设计修订完成（对齐 MSS/IRS/PAS/Integration；含质量门禁闭环）

---

## 实现状态（仓库现状）

- 当前仓库 `src/data/` 仍以骨架实现为主（`fetcher.py`、`repositories/*`）。
- L1 八类原始接口已接入统一采集链路（`daily/daily_basic/limit_list_d/index_daily/index_member/index_classify/stock_basic/trade_cal`）。
- 已实现低频节流策略：`index_member/stock_basic` 按月快照、`index_classify` 按半年度快照，避免批量回填时重复消耗配额。
- 已落地最小契约：`src/data/models/snapshots.py` 补齐 `data_quality/stale_days/source_trade_date` 字段与约束。
- 已落地质量门禁原型：`src/data/quality_gate.py`（覆盖率、`stale_days`、跨日一致性前置检查）。
- 已验证现实风险：生产回填阶段出现过 DuckDB 文件锁冲突，需纳入采集层非功能门禁（锁等待/重试/锁持有者记录）。
- 已落地双通道 TuShare 采集策略：`primary` + `fallback`（主路失败自动切换兜底）。
- 已落地限速策略：支持全局限速（`TUSHARE_RATE_LIMIT_PER_MIN`）与通道独立限速（`TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN`、`TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN`）。
- AKShare/BaoStock 仅保留为最终底牌路线图预留，当前版本未实装（避免设计-实现漂移）。
- 本文档为权威设计规格，接口/流程继续按本规格迭代落地。

---

## 1. 设计概述

### 1.1 核心定位

Data Layer是EmotionQuant系统的数据基础设施层，负责：

1. **数据采集**：从TuShare API获取A股原始数据
2. **数据加工**：清洗、聚合、派生计算
3. **数据存储**：分层存储（L1-L4）
4. **数据调度**：每日定时更新

### 1.2 四层分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer 四层架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  L1 Raw（原始层）                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TuShare API → Parquet文件                              │   │
│  │  API: daily / daily_basic / limit_list_d / index_daily  │   │
│  │       index_member / index_classify / stock_basic / trade_cal │   │
│  │  Raw: raw_daily / raw_daily_basic / raw_limit_list / raw_index_daily │   │
│  │       raw_index_member / raw_index_classify / raw_stock_basic / raw_trade_cal │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↓                                      │
│  L2 Processed（处理层）                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  聚合计算 → DuckDB（单库优先，阈值触发分库）            │   │
│  │  market_snapshot / industry_snapshot / stock_gene_cache│   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↓                                      │
│  L3 Runtime（运行层）                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  算法输出 → DuckDB（单库优先，阈值触发分库）            │   │
│  │  mss_panorama / irs_industry_daily / stock_pas_daily   │   │
│  │  integrated_recommendation / pas_breadth_daily          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↓                                      │
│  L4 Analysis（分析层）                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  分析产出 → DuckDB（单库优先，阈值触发分库）            │   │
│  │  daily_report / performance_metrics / signal_attribution│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Ops/Metadata（非L1-L4）                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  system_config / data_version_log / task_execution_log  │   │
│  │  data_quality_report                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 1.3 职责边界（验收用）

- **数据层职责**：仅负责原始数据采集与聚合（count/ratio/rolling），不做因子打分与 Z-Score 归一化。
- **算法层职责**：MSS/IRS/PAS 负责 count→ratio→zscore 的评分与归一化；Integration 仅做融合与门控。
- **派生允许**：可提供必要的聚合/派生表（如 `pas_breadth_daily`），但必须来源于上游输出字段，避免跨层重复计算。

## 2. L1 原始数据采集

### 2.1 数据源策略：双 TuShare 主备（当前实现）+ 多源底牌（路线图预留）

| 优先级 | 数据源 | 用途 | 状态 | 备注 |
|------|------|------|------|------|
| P0 主源 | `TuShare`（10000 网关） | 全量 L1 八类接口 | 已实现 | 通过 `TUSHARE_PRIMARY_*` 配置；覆盖更全 |
| P1 兜底 | `TuShare`（5000 官方） | 主路失败时兜底 | 已实现 | 通过 `TUSHARE_FALLBACK_*` 配置；响应更快 |
| P2 预留 | `AKShare` | 最后底牌 | 未实现（路线图） | 仅做未来底牌，不进入当前主流程 |
| P3 预留 | `BaoStock` | 最后底牌 | 未实现（路线图） | 仅做未来底牌，不进入当前主流程 |

> 设计约束：无论来自哪个通道/数据源，入库前必须归一化到统一字段口径（`ts_code/stock_code/trade_date/open/high/low/close/vol/amount`），禁止在 L2/L3 感知“源差异”。

### 2.1.1 L1 八类逻辑接口（统一口径）

| 逻辑接口 | 用途 | 更新频率 |
|------|------|----------|
| `daily` | 个股日线行情 | 每日 |
| `daily_basic` | 换手率、市值 | 每日 |
| `limit_list_d` | 涨跌停列表 | 每日 |
| `index_daily` | 基准指数日线 | 每日 |
| `index_member` | 行业成分股 | 月度 |
| `index_classify` | 申万行业分类 | 半年/年度（低频） |
| `stock_basic` | 股票基础信息 | 月度 |
| `trade_cal` | 交易日历 | 年度 |

### 2.2 采集策略

```python
class TuShareDataFetcher:
    """
    TuShare数据获取器
    
    限流策略：
    - 全局限流：TUSHARE_RATE_LIMIT_PER_MIN（默认120次/分钟）
    - 通道独立限流：PRIMARY/FALLBACK 可单独配置（0=继承全局）
    - 指数退避重试：最多3次
    - 并发下载：4线程
    """
    
    def fetch_daily(self, trade_date: str) -> pd.DataFrame:
        """
        获取日线数据
        
        存储：${DATA_PATH}/parquet/daily/{trade_date}.parquet
        """
        pass
    
    def fetch_limit_list(self, trade_date: str) -> pd.DataFrame:
        """
        获取涨跌停列表（limit_list_d）
        
        存储：${DATA_PATH}/parquet/limit_list/{trade_date}.parquet（raw_limit_list）
        """
        pass
```

### 2.3 存储格式

```
${DATA_PATH}/parquet/
├── daily/                     # raw_daily
│   └── {trade_date}.parquet   # 按日期分区
├── daily_basic/               # raw_daily_basic
├── limit_list/                # raw_limit_list（limit_list_d）
├── index_daily/               # raw_index_daily
├── index_member/              # raw_index_member
├── index_classify/            # raw_index_classify
├── stock_basic/               # raw_stock_basic
└── trade_cal/                 # raw_trade_cal
```

**TuShare接口-目录-逻辑表名映射**：

| TuShare 接口 | 目录名 | 逻辑表名 | 说明 |
|-------------|--------|---------|------|
| `daily` | `daily/` | `raw_daily` | 日线行情 |
| `daily_basic` | `daily_basic/` | `raw_daily_basic` | 日线基础 |
| `limit_list_d` | `limit_list/` | `raw_limit_list` | 涨跌停列表 |
| `index_daily` | `index_daily/` | `raw_index_daily` | 指数日线 |
| `index_member` | `index_member/` | `raw_index_member` | 行业成分 |
| `index_classify` | `index_classify/` | `raw_index_classify` | 行业分类 |
| `stock_basic` | `stock_basic/` | `raw_stock_basic` | 股票基础 |
| `trade_cal` | `trade_cal/` | `raw_trade_cal` | 交易日历 |

### 2.4 源切换与锁恢复策略（P0）

1. 当前源切换顺序（已实现）：`TuShare Primary -> TuShare Fallback`。
2. 预留底牌顺序（未实现）：`... -> AKShare -> BaoStock`。
3. 切换触发：鉴权失败、限流、网络超时、空结果异常（非停牌/非休市）之一成立。
4. DuckDB 写入锁：必须执行“有限等待 + 重试 + 锁持有者记录”，重试失败才可标记批次失败（锁恢复细节仍在 S3ar 中）。
5. 证据要求：当前必须保留 `fetch_progress.json` / `fetch_retry_report.md` / `throughput_benchmark.md`。
6. 一致性要求：同一批次内不同通道/源返回字段必须完成映射与类型校验，不通过则阻断入库。

---

## 3. L2 数据加工处理

### 3.1 市场快照聚合

```python
def process_market_snapshot(trade_date: str, config: DataLayerConfig) -> MarketSnapshot:
    """
    聚合市场快照数据
    
    输入：L1原始数据（daily + limit_list）
    输出：market_snapshot表
    
    计算字段：
    - total_stocks: 有效股票总数
    - rise_count: 上涨家数（pct_chg > 0）
    - fall_count: 下跌家数（pct_chg < 0）
    - flat_count: 平盘家数（abs(pct_chg) <= flat_threshold）
    - strong_up_count: 大涨家数（pct_chg > 5%）
    - strong_down_count: 大跌家数（pct_chg < -5%）
    - limit_up_count: 涨停家数
    - limit_down_count: 跌停家数
    - touched_limit_up: 曾涨停（含炸板）家数
    - new_100d_high_count: 100日新高数
    - new_100d_low_count: 100日新低数
    - continuous_limit_up_2d: 连续2日涨停
    - continuous_limit_up_3d_plus: 连续3+日涨停
    - continuous_new_high_2d_plus: 连续2日+新高
    - high_open_low_close_count: 高开低走计数
    - low_open_high_close_count: 低开高走计数
    - pct_chg_std: 全市场涨跌幅标准差
    - amount_volatility: 成交额相对20日均值的波动率
    - yesterday_limit_up_today_avg_pct: 昨涨停今平均涨幅
    """
    # 1. 读取日线数据
    daily = pd.read_parquet(f"daily/{trade_date}.parquet")
    
    # 2. 计算涨跌家数
    flat_threshold = config.flat_threshold  # 默认 0.5（单位：%）
    rise_count = len(daily[daily['pct_chg'] > 0])
    fall_count = len(daily[daily['pct_chg'] < 0])
    flat_count = len(daily[daily['pct_chg'].abs() <= flat_threshold])
    
    # 3. 读取涨跌停数据
    limit_list = pd.read_parquet(f"limit_list/{trade_date}.parquet")
    limit_up_count = len(limit_list[limit_list['limit'] == 'U'])
    limit_down_count = len(limit_list[limit_list['limit'] == 'D'])
    touched_limit_up = len(limit_list[limit_list['limit'].isin(['U', 'Z'])])
    
    # 4. 计算100日新高/新低
    # 需要读取近100日数据进行比较
    
    # 5. 返回聚合结果
    return MarketSnapshot(...)
```

### 3.2 行业快照聚合

```python
def process_industry_snapshot(
    trade_date: str,
    config: DataLayerConfig
) -> List[IndustrySnapshot]:
    """
    聚合31个申万一级行业快照
    
    输入：L1原始数据 + index_member映射 + index_daily（行业指数）
    输出：industry_snapshot表（31条记录）
    
    聚合方式：
    1. 通过index_member获取行业-股票映射
    2. 按行业聚合daily/daily_basic数据
    3. 计算行业级别统计指标（涨跌家数、涨跌停、新高新低、行业涨跌幅、行业成交额/换手、估值、Top5涨幅/涨停）
    """
    # 1. 获取行业成分映射
    members = load_index_member()
    flat_threshold = config.flat_threshold  # 默认 0.5（单位：%）
    
    # 2. 按行业聚合
    snapshots = []
    for industry_code in SW_INDUSTRIES:
        stocks = members[members['index_code'] == industry_code]['con_code']
        # 命名与数据源对齐：daily / daily_basic / index_daily
        industry_daily = daily[daily['ts_code'].isin(stocks)]
        industry_daily_basic = daily_basic[daily_basic['ts_code'].isin(stocks)]
        industry_index_daily = index_daily[index_daily['ts_code'] == industry_code]
        valid_pe = industry_daily_basic['pe_ttm']
        valid_pe = valid_pe[(valid_pe > 0) & (valid_pe <= 1000)]
        valid_pb = industry_daily_basic['pb']
        valid_pb = valid_pb[valid_pb > 0]
        if len(valid_pe) >= 8 and len(valid_pb) >= 8:
            pe_q01, pe_q99 = valid_pe.quantile([0.01, 0.99])
            pb_q01, pb_q99 = valid_pb.quantile([0.01, 0.99])
            industry_pe_ttm = valid_pe.clip(lower=pe_q01, upper=pe_q99).median()
            industry_pb = valid_pb.clip(lower=pb_q01, upper=pb_q99).median()
        else:
            industry_pe_ttm = load_prev_industry_value(industry_code, "industry_pe_ttm")
            industry_pb = load_prev_industry_value(industry_code, "industry_pb")
        
        snapshot = IndustrySnapshot(
            industry_code=industry_code,
            stock_count=len(industry_daily),
            rise_count=len(industry_daily[industry_daily['pct_chg'] > 0]),
            fall_count=len(industry_daily[industry_daily['pct_chg'] < 0]),
            flat_count=len(industry_daily[industry_daily['pct_chg'].abs() <= flat_threshold]),
            industry_close=float(industry_index_daily['close'].iloc[0]),
            industry_pct_chg=float(industry_index_daily['pct_chg'].iloc[0]),
            industry_amount=industry_daily['amount'].sum(),
            industry_turnover=industry_daily_basic['turnover_rate'].mean(),
            industry_pe_ttm=industry_pe_ttm,
            industry_pb=industry_pb,
            limit_up_count=calc_limit_up_count(industry_daily, limit_list),
            limit_down_count=calc_limit_down_count(industry_daily, limit_list),
            new_100d_high_count=calc_new_high_count(industry_daily),
            new_100d_low_count=calc_new_low_count(industry_daily),
            top5_codes=calc_top5_codes(industry_daily),
            top5_pct_chg=calc_top5_pct_chg(industry_daily),
            top5_limit_up=calc_top5_limit_up(industry_daily, limit_list),
            yesterday_limit_up_today_avg_pct=calc_yesterday_limit_up_today_avg_pct(
                industry_daily, limit_list
            ),
            # ... 其他字段
        )
        snapshots.append(snapshot)
    
    return snapshots
```

### 3.3 牛股基因缓存

```python
def process_stock_gene_cache(trade_date: str) -> int:
    """
    按交易日增量更新 stock_gene_cache
    
    更新频率：每日增量更新
    缓存有效期：30天未交易则清理
    
    计算内容：
    - 涨停历史（近1年）
    - 新高历史（近1年）
    - 近120日涨停次数 / 近60日新高次数
    - 历史最大涨幅（max_pct_chg_history）
    - 涨停后表现
    - 爆发力指标
    - 时间衰减因子

    Returns:
        int: 成功更新的股票数量（失败记录跳过但记录日志）

    异常处理：
    - 单股票计算失败：记录 warning，跳过当前股票并继续
    - 数据源缺失：抛出 DataFetchError，交由调度器统一重试/告警
    """
    updated = 0
    for stock_code in get_active_stock_list(trade_date):
        try:
            # 1. 计算涨停数据
            limit_up_count_1y = count_limit_up_1y(stock_code)
            max_continuous_board = calc_max_continuous_board(stock_code)

            # 2. 计算新高数据
            new_high_count_1y = count_new_high_1y(stock_code)

            # 3. 计算爆发力
            explosive_score = calc_explosive_score(stock_code)

            # 4. 计算时间衰减
            time_decay = calc_time_decay(stock_code)

            upsert_stock_gene_cache(stock_code, ...)
            updated += 1
        except SingleStockComputeError as e:
            logger.warning(f"skip stock {stock_code}: {e}")
            continue

    return updated
```

---

## 4. L3 算法输出存储

> **说明**：以下 SQL 为**逻辑DDL**，实际落库以 DuckDB（单库优先，阈值触发分库）为主。

### 4.1 MSS输出 → mss_panorama

```sql
-- MSS全景表
CREATE TABLE mss_panorama (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期',
    
    -- 核心输出
    temperature DECIMAL(8,4) COMMENT '市场温度 0-100',
    cycle VARCHAR(20) COMMENT '周期 emergence/fermentation/acceleration/divergence/climax/diffusion/recession',
    trend VARCHAR(20) COMMENT '趋势 up/down/sideways',
    position_advice VARCHAR(20) COMMENT '仓位建议',
    
    -- 因子得分
    market_coefficient DECIMAL(8,4) COMMENT '大盘系数',
    profit_effect DECIMAL(8,4) COMMENT '赚钱效应',
    loss_effect DECIMAL(8,4) COMMENT '亏钱效应',
    continuity_factor DECIMAL(8,4) COMMENT '连续性因子',
    extreme_factor DECIMAL(8,4) COMMENT '极端因子',
    volatility_factor DECIMAL(8,4) COMMENT '波动因子',
    
    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '中性度 0-1',
    rank INTEGER COMMENT '历史排名',
    percentile DECIMAL(8,4) COMMENT '百分位排名 0-100',

    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_trade_date (trade_date)
);
```

### 4.2 IRS输出 → irs_industry_daily

```sql
-- IRS行业评分表
CREATE TABLE irs_industry_daily (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期',
    industry_code VARCHAR(10) COMMENT '行业代码',
    industry_name VARCHAR(50) COMMENT '行业名称',

    -- 核心输出
    industry_score DECIMAL(8,4) COMMENT '行业评分 0-100',
    rank INTEGER COMMENT '行业排名 1-31',
    rotation_status VARCHAR(20) COMMENT '轮动状态 IN/OUT/HOLD',
    rotation_detail VARCHAR(50) COMMENT '轮动详情',
    allocation_advice VARCHAR(20) COMMENT '配置建议 超配/标配/减配/回避',

    -- 因子得分
    relative_strength DECIMAL(8,4) COMMENT '相对强度',
    continuity_factor DECIMAL(8,4) COMMENT '连续性因子',
    capital_flow DECIMAL(8,4) COMMENT '资金流向',
    valuation DECIMAL(8,4) COMMENT '估值因子',
    leader_score DECIMAL(8,4) COMMENT '龙头因子',
    gene_score DECIMAL(8,4) COMMENT '行业基因库',

    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '中性度 0-1',

    UNIQUE KEY uk_trade_date_industry (trade_date, industry_code)
);
```

### 4.3 PAS输出 → stock_pas_daily

```sql
-- PAS每日评分表
CREATE TABLE stock_pas_daily (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8),
    stock_code VARCHAR(20),
    stock_name VARCHAR(50),
    industry_code VARCHAR(10),
    opportunity_score DECIMAL(8,4),    -- 机会评分 0-100
    opportunity_grade VARCHAR(10),     -- S/A/B/C/D
    direction VARCHAR(10),             -- bullish/bearish/neutral
    risk_reward_ratio DECIMAL(8,4),
    bull_gene_score DECIMAL(8,4),
    structure_score DECIMAL(8,4),
    behavior_score DECIMAL(8,4),
    neutrality DECIMAL(8,4),
    entry DECIMAL(12,4),
    stop DECIMAL(12,4),
    target DECIMAL(12,4),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code)
);
```

### 4.4 集成输出 → integrated_recommendation

```sql
-- 三三制集成推荐表
CREATE TABLE integrated_recommendation (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    industry_code VARCHAR(10) COMMENT '行业代码',
    industry_name VARCHAR(50) COMMENT '行业名称',

    -- 三系统输入评分
    mss_score DECIMAL(8,4) COMMENT 'MSS评分',
    irs_score DECIMAL(8,4) COMMENT 'IRS评分',
    pas_score DECIMAL(8,4) COMMENT 'PAS评分',

    -- 集成输出
    final_score DECIMAL(8,4) COMMENT '综合评分 0-100',
    direction VARCHAR(20) COMMENT '综合方向',
    integration_mode VARCHAR(20) COMMENT '集成模式 top_down/bottom_up/dual_verify/complementary',
    weight_plan_id VARCHAR(40) COMMENT '权重方案ID baseline/candidate',
    validation_gate VARCHAR(10) COMMENT '验证门禁 PASS/WARN/FAIL',
    recommendation VARCHAR(20) COMMENT '推荐等级 STRONG_BUY/BUY/HOLD/SELL/AVOID',
    position_size DECIMAL(8,4) COMMENT '建议仓位 0-1',

    -- 交易参考
    entry DECIMAL(12,4) COMMENT '入场价',
    stop DECIMAL(12,4) COMMENT '止损价',
    target DECIMAL(12,4) COMMENT '目标价',
    risk_reward_ratio DECIMAL(8,4) COMMENT '风险收益比',

    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '中性度 0-1',

    UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code)
);
```
### 4.5 PAS广度聚合 → pas_breadth_daily（BU入口，派生）

```sql
-- PAS广度聚合表（由 stock_pas_daily 聚合）
CREATE TABLE pas_breadth_daily (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期',
    scope VARCHAR(20) COMMENT 'market/industry',
    industry_code VARCHAR(10) COMMENT '行业代码（scope=industry时）',
    industry_name VARCHAR(50) COMMENT '行业名称',

    -- 市场广度
    pas_sa_count INTEGER COMMENT 'S/A数量',
    pas_sa_ratio DECIMAL(8,4) COMMENT 'S/A占比',
    pas_grade_distribution JSON COMMENT 'S/A/B/C/D分布',

    -- 行业广度
    industry_sa_count INTEGER COMMENT '行业内S/A数量',
    industry_sa_ratio DECIMAL(8,4) COMMENT '行业内S/A占比',
    industry_top_k_concentration DECIMAL(8,4) COMMENT 'TopK行业S/A集中度',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_trade_date_scope_industry (trade_date, scope, industry_code)
);
```

---

## 5. L4 分析层（由 Analysis 模块产出）

L4 为业务分析层，表结构详见 [analysis-data-models.md](../analysis/analysis-data-models.md)。

| 表名 | 说明 |
|------|------|
| daily_report | 日度分析报告 |
| performance_metrics | 绩效指标 |
| signal_attribution | 信号归因 |

---

## 6. 运维/元数据管理（非L1-L4）

> 运维表结构详见 [data-layer-data-models.md](./data-layer-data-models.md)。

### 6.1 数据版本记录

```sql
CREATE TABLE data_version_log (
    id INTEGER PRIMARY KEY,
    data_type VARCHAR(50),     -- daily/limit_list/...
    trade_date VARCHAR(8),
    record_count INTEGER,
    status VARCHAR(20),        -- SUCCESS/FAILED
    created_at DATETIME
);
```

### 6.2 任务执行日志

```sql
CREATE TABLE task_execution_log (
    id INTEGER PRIMARY KEY,
    task_name VARCHAR(50),
    trade_date VARCHAR(8),
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds REAL,
    status VARCHAR(20),
    error_message TEXT
);
```

---

## 7. 每日调度流程

### 7.1 调度时间表

| 时间段 | 任务 | 说明 |
|--------|------|------|
| 15:30-16:10 | 拉取基础数据 | daily/daily_basic/limit_list |
| 16:10-16:20 | 拉取基准指数 | index_daily |
| 16:20-16:30 | 校验行业映射 | index_member/index_classify |
| 16:30-17:00 | 快照聚合 | market_snapshot/industry_snapshot/stock_gene_cache |
| 17:00-17:15 | 算法输出 | MSS/IRS/PAS |
| 17:15-17:20 | Validation Gate | validation_gate_decision + selected_weight_plan |
| 17:20-17:40 | 集成与质量检查 | integrated_recommendation + pas_breadth_daily + 质量报告 |
| 11:35 / 14:30（可选） | 盘中增量快照 | intraday_incremental_snapshot（仅观测，不进入主交易流水线） |

### 7.2 调度器实现

```python
class DailyPipelineScheduler:
    """
    每日数据流水线调度器
    
    执行时间：T日 15:30后
    失败重试：最多3次，每次间隔5分钟
    """
    
    def run(self, trade_date: str):
        # Step 0: 数据准备门禁（覆盖率/stale_days/跨日一致性）
        gate = self.readiness_checker.check(trade_date)
        if not gate.is_ready:
            self.alerting.notify_blocked(gate)
            return

        # Step 1: 数据下载
        self.fetcher.fetch_all(trade_date)
        
        # Step 2: 数据加工
        self.processor.process_market_snapshot(trade_date, self.config)
        self.processor.process_industry_snapshot(trade_date, self.config)
        self.processor.process_stock_gene_cache(trade_date)
        
        # Step 3: 算法执行
        self.executor.run_mss(trade_date)
        self.executor.run_irs(trade_date)
        self.executor.run_pas(trade_date)
        self.executor.run_validation_gate(trade_date)
        self.executor.run_pas_breadth(trade_date)
        self.executor.run_integration(trade_date)
        
        # Step 4: 元数据记录
        self.metadata.log_version(trade_date)
        self.metadata.generate_quality_report(trade_date)

    def run_intraday_incremental(self, trade_date: str, hhmm: str):
        """
        可选盘中增量：仅更新观测层，不触发 MSS/IRS/PAS/Integration 主流程。
        """
        self.fetcher.fetch_intraday_incremental(trade_date, hhmm=hhmm)
        self.processor.process_intraday_snapshot(trade_date, hhmm=hhmm)
```

---

## 8. 数据质量保障

### 8.1 质量检查项

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| 数据覆盖率 | ≥ 95% | 当日成交股票覆盖率 |
| 空值率 | ≤ 1% | 关键字段空值比例 |
| 日期连续性 | ≥ 99% | 交易日历连续覆盖 |
| 评分范围 | 0-100 | MSS/IRS/PAS输出范围 |

### 8.2 回填机制

```python
def backfill(table_name: str, start_date: str, end_date: str):
    """
    数据回填
    
    1. 备份现有数据
    2. 重新从TuShare获取
    3. 验证一致性
    4. 如失败则回滚
    """
    pass
```

### 8.3 质量门禁自动化（P0）

```python
from src.data.quality_gate import evaluate_data_quality_gate

decision = evaluate_data_quality_gate(
    trade_date="20260214",
    coverage_ratio=0.963,
    source_trade_dates={"daily": "20260214", "limit_list": "20260214"},
    quality_by_dataset={"daily": "normal", "limit_list": "normal"},
    stale_days_by_dataset={"daily": 0, "limit_list": 0},
)

# status ∈ {ready, degraded, blocked}
# blocked: 覆盖率不足 / stale_days > 3 / 跨日混用
```

### 8.4 降级策略分级（P1）

| 数据类型 | 轻度降级（继续） | 重度降级（阻断） | 影响面 |
|----------|------------------|------------------|--------|
| `daily` / `daily_basic` | `stale_days <= 1` | `stale_days > 1` | 全市场 |
| `limit_list` | `stale_days <= 1` | `stale_days > 1` | 情绪极值统计 |
| `index_member` / `index_classify` | `stale_days <= 20` | `stale_days > 20` | 行业映射 |
| `stock_basic` / `trade_cal` | `stale_days <= 5` | `stale_days > 5` | 基础口径 |

> 统一规则：任一核心输入触发“重度降级”即 `status=blocked`；轻度降级下透传 `data_quality/stale_days/source_trade_date`。

### 8.5 非功能门禁（P0）

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| DuckDB 锁等待时长 | 单次 <= 30s | 超阈值必须记录锁持有进程并进入重试 |
| 批次重试上限 | <= 3 次 | 超上限标记失败并产出失败证据 |
| 切源次数 | 单批次 <= 2 次 | 超限进入 `WARN/blocked` 并触发人工复核 |
| 幂等写入 | 100% | 重试不得造成重复写入 |

---

## 9. 验收与验证（可执行口径）

### 9.1 数据就绪性

- L1 必备数据：`daily` / `daily_basic` / `limit_list_d` / `index_daily` / `index_member` / `index_classify` / `stock_basic` / `trade_cal` 完整可用。
- 覆盖率：当日成交股票覆盖率 ≥ 95%。
- 时效性：L1 数据日期必须等于最近交易日。
- 一致性：同一 trade_date 的 L1/L2/L3 记录一致（不能跨日混用）。
- 可追溯：每个批次需保留数据源链路（主源/兜底切换记录）与锁冲突恢复记录。

### 9.2 量纲一致性

- L2 仅输出 **count/ratio/rolling**，所有计数 ≥ 0，比例 ∈ [0,1]。
- L3 评分字段 ∈ [0,100]；neutrality ∈ [0,1]；position_size ∈ [0,1]。
- 数据层不得进行 Z-Score 或评分映射（由 MSS/IRS/PAS 负责）。

### 9.3 边界与互斥

- L2 不直接输出因子得分；L3 仅记录算法输出，不二次归一化。
- `pas_breadth_daily` 仅允许由 `stock_pas_daily` 聚合，禁止引入跨层新因子。

### 9.4 最小闭环验收（CP-10）

1. `pytest tests/unit/data/models/test_model_contract_alignment.py tests/unit/data/models/test_snapshots.py tests/unit/data/test_quality_gate.py`
2. `python -m src.data.quality_gate`（若提供 CLI 时）或在调度中调用 `evaluate_data_quality_gate()`
3. 验收标准：
   - 模型字段包含 `data_quality/stale_days/source_trade_date`
   - `stale_days > 3` 能触发阻断
   - 跨日混用（source date 不一致）能触发阻断

---

## 10. 可选盘中增量层（P1）

- 新增逻辑层：`intraday_incremental_snapshot`（分钟级或半小时级）。
- 作用范围：仅提供 GUI/Analysis 观测，不直接驱动交易信号。
- 开关控制：`system_config.enable_intraday_incremental`（默认 `false`）。
- 防污染约束：盘后主流程仍以 EOD L1 原始数据为唯一事实源。

---

## 11. 分库触发与回迁策略（P2）

- 触发条件（任一满足）：
  - 主库体积 > 120GB
  - 单次查询 p95 > 2.0s 且持续 5 个交易日
  - 日写入记录 > 3000 万
- 执行动作：
  - 按年分库（`emotionquant_YYYY.duckdb`）
  - 保持 `query_cross_year()` 透明聚合能力
- 回迁策略：
  - 当近 90 日查询 p95 < 1.0s 且总量回落，可合并回单库
  - 回迁前后需执行“行数一致 + 校验和一致 + 抽样字段一致”三重校验

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.6 | 2026-02-19 | 对齐实现：明确当前为“双 TuShare 主备”（10000 网关主、5000 官方兜底）；AKShare/BaoStock 调整为路线图预留；补充全局+通道独立限速口径 |
| v3.1.5 | 2026-02-19 | 新增“主源+兜底”策略（TuShare->AKShare->BaoStock）；补充 DuckDB 锁恢复与非功能门禁；统一 L1 八类逻辑接口口径与切源证据要求 |
| v3.1.4 | 2026-02-14 | 修复 R32（review-010）：补齐 `src/data/models` 质量字段契约落地说明；新增 `src/data/quality_gate.py` 门禁自动化口径（覆盖率/`stale_days`/跨日一致性）；补充降级分级、可选盘中增量层、分库触发与回迁策略 |
| v3.1.3 | 2026-02-09 | 修复 R23：补充 TuShare 接口-目录-逻辑表名映射；`process_industry_snapshot` 增加 `config.flat_threshold`；补充 `stock_gene_cache` 返回值与异常处理语义 |
| v3.1.2 | 2026-02-08 | 修复 R14：行业估值聚合改为过滤+Winsorize+median；`stock_pas_daily` DDL 补 `id`；`integrated_recommendation` DDL 补 `weight_plan_id/validation_gate` 且 `stock_code` 统一 `VARCHAR(20)`；调度流程补 `stock_gene_cache` 与 Validation Gate；`flat_count` 阈值改为 `config.flat_threshold` |
| v3.1.1 | 2026-02-05 | PAS相关字段命名口径对齐（max_pct_chg_history 等） |
| v3.1.0 | 2026-02-04 | 对齐 MSS/IRS/PAS/Integration：补充行业快照/集成字段、PAS广度派生表与验收口径 |
| v3.0.1 | 2026-02-04 | market_snapshot 聚合口径补齐：新增强涨跌、连续新高、极端行为、波动字段，供 MSS v3.1.0 使用 |
| v3.0.0 | 2026-01-31 | 重构版：统一四层架构、明确调度流程 |

---

**关联文档**：
- 数据模型：[data-layer-data-models.md](./data-layer-data-models.md)
- API接口：[data-layer-api.md](./data-layer-api.md)
- 信息流：[data-layer-information-flow.md](./data-layer-information-flow.md)


