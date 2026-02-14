# Analysis 数据模型

**版本**: v3.2.0（重构版）
**最后更新**: 2026-02-14
**状态**: 设计完成（闭环口径补齐；代码待实现）

---

Analysis 数据模型用于承载 **L4 分析结果与报告**，输入来自 L3 算法输出与回测/实盘结果；不引入第三方库替代模型定义。

## 1. 核心数据结构

### 1.1 PerformanceMetrics（绩效指标）

```python
@dataclass
class PerformanceMetrics:
    """绩效指标"""
    metric_date: str              # 指标日期 (YYYYMMDD)
    # 收益指标
    total_return: float           # 总收益率
    annual_return: float          # 年化收益率
    # 风险指标
    max_drawdown: float           # 最大回撤（负值）
    volatility: float             # 年化波动率
    # 风险调整收益
    sharpe_ratio: float           # 夏普比率
    sortino_ratio: float          # 索提诺比率
    calmar_ratio: float           # 卡玛比率
    # 交易统计
    win_rate: float               # 胜率 [0-1]
    profit_factor: float          # 盈亏比
    total_trades: int             # 总交易次数
    avg_holding_days: float       # 平均持仓天数
    created_at: datetime          # 创建时间
```

字段计算公式：
| 字段 | 公式 | 说明 |
|------|------|------|
| total_return | equity_end / equity_start - 1 | 总收益率 |
| annual_return | (1 + total_return)^(252/N) - 1 | 年化收益率 |
| max_drawdown | min((equity - peak) / peak) | 最大回撤 |
| volatility | std(r) × sqrt(252) | 年化波动率 |
| sharpe_ratio | sqrt(252) × (mean(r) - rf/252) / std(r) | 夏普比率 |
| sortino_ratio | sqrt(252) × (mean(r) - rf/252) / sqrt(mean(min(r-rf/252,0)^2)) | 索提诺比率 |
| calmar_ratio | annual_return / abs(max_drawdown) | 卡玛比率 |
| win_rate | 盈利交易数 / 总交易数 | 胜率 |
| profit_factor | 总盈利 / 总亏损 | 盈亏比 |

### 1.2 DailyReport（日报）

```python
@dataclass
class DailyReport:
    """日度分析报告"""
    report_date: str              # 报告日期
    # 市场概况
    market_temperature: float     # MSS温度
    cycle: str                    # 周期阶段
    trend: str                    # 趋势方向
    position_advice: str          # 仓位建议
    # 信号统计
    signal_count: int             # 信号数
    filled_count: int             # 成交数
    reject_count: int             # 拒绝数
    # 有效性指标
    hit_rate: float               # 命中率
    avg_return_5d: float          # 5日平均收益
    avg_holding_days: float       # 平均持仓天数
    # 绩效指标
    total_return: float           # 总收益率
    max_drawdown: float           # 最大回撤
    sharpe_ratio: float           # 夏普比率
    win_rate: float               # 胜率
    # 详情
    top_recommendations: List[dict]  # Top N推荐（JSON）
    risk_summary: dict            # 风险摘要（JSON）
    created_at: datetime          # 创建时间
```

### 1.3 SignalAttribution（信号归因）

```python
@dataclass
class SignalAttribution:
    """信号归因结果"""
    trade_date: str               # 交易日期
    mss_attribution: float        # MSS贡献度
    irs_attribution: float        # IRS贡献度
    pas_attribution: float        # PAS贡献度
    sample_count: int             # 截尾后样本数
    raw_sample_count: int         # 截尾前样本数
    trimmed_sample_count: int     # 截尾后样本数（冗余留存便于审计）
    trim_ratio: float             # 截尾比例
    attribution_method: str       # 归因方法（如 trimmed_mean_q0.05 / mean_fallback_small_sample）
    created_at: datetime          # 创建时间
```

### 1.4 LiveBacktestDeviation（实盘-回测偏差归因）

```python
@dataclass
class LiveBacktestDeviation:
    """实盘-回测偏差拆解"""
    trade_date: str               # 交易日期
    signal_deviation: float       # 信号偏差（选股/打分）
    execution_deviation: float    # 成交偏差（成交相对 entry）
    cost_deviation: float         # 成本偏差（佣金+滑点+冲击）
    total_deviation: float        # 总偏差
    dominant_component: str       # 主导偏差项（signal/execution/cost）
    created_at: datetime          # 创建时间
```

---

## 2. 报告数据结构

### 2.1 DailyReportData（日报数据）

```python
@dataclass
class DailyReportData:
    """日报生成数据"""
    report_date: str
    # 市场概况
    market_overview: MarketOverview
    # 行业轮动
    industry_rotation: IndustryRotation
    # 信号统计
    signal_stats: SignalStats
    # 绩效摘要
    performance: PerformanceSummary
    # 推荐列表
    top_recommendations: List[RecommendationSummary]
    # 风险提示
    risk_summary: RiskSummary
    created_at: datetime = None   # 创建时间（可选，落库时可由 DB 默认生成）
```

### 2.2 MarketOverview（市场概况）

```python
@dataclass
class MarketOverview:
    """市场概况"""
    temperature: float            # 温度 [0-100]
    temperature_level: str        # 等级 (high/medium/cool/low)
    cycle: str                    # 周期 (emergence/fermentation/acceleration/divergence/climax/diffusion/recession/unknown)
    cycle_label: str              # 中文标签
    trend: str                    # 趋势 (up/down/sideways)
    position_advice: str          # 仓位建议
```

### 2.3 IndustryRotation（行业轮动）

```python
@dataclass
class IndustryRotation:
    """行业轮动摘要"""
    top5: List[Tuple[str, float]] # Top5行业 [(名称, 评分), ...]
    in_count: int                 # 轮入行业数
    out_count: int                # 轮出行业数
```

### 2.4 SignalStats（信号统计）

```python
@dataclass
class SignalStats:
    """信号统计"""
    signal_count: int             # 总信号数
    filled_count: int             # 已成交数
    reject_count: int             # 被拒绝数
    pending_count: int            # 待处理数
    fill_rate: float              # 成交率
```

### 2.5 PerformanceSummary（绩效摘要）

```python
@dataclass
class PerformanceSummary:
    """绩效摘要"""
    total_return: float           # 总收益率
    total_return_pct: str         # 格式化："+15.2%"
    max_drawdown: float           # 最大回撤
    max_drawdown_pct: str         # 格式化："-8.5%"
    sharpe_ratio: float           # 夏普比率
    win_rate: float               # 胜率
    win_rate_pct: str             # 格式化："65.3%"
```

### 2.6 RecommendationSummary（推荐摘要）

```python
@dataclass
class RecommendationSummary:
    """推荐摘要（日报用）"""
    rank: int                     # 排名
    stock_code: str               # 股票代码
    stock_name: str               # 股票名称
    industry_name: str            # 行业名称
    final_score: float            # 综合评分
    position_size: float          # 建议仓位
    entry: float                  # 入场价
    stop: float                   # 止损价
    target: float                 # 目标价
    recommendation: str           # 推荐等级
```

### 2.7 RiskSummary（风险摘要）

```python
@dataclass
class RiskSummary:
    """风险摘要"""
    low_risk_count: int           # 低风险数
    medium_risk_count: int        # 中风险数
    high_risk_count: int          # 高风险数
    low_risk_pct: float           # 低风险占比
    medium_risk_pct: float        # 中风险占比
    high_risk_pct: float          # 高风险占比
    high_risk_change_rate: float  # 高风险变化率（相对前一日）
    low_risk_change_rate: float   # 低风险变化率（相对前一日）
    risk_turning_point: str       # 风险拐点（risk_up_turn/risk_down_turn/none）
    risk_regime: str              # 风险状态（risk_on/risk_off/neutral）
    risk_alert: str               # 风险提示文案
```

---

## 3. 数据库表结构

> 以下为 **MySQL 风格逻辑DDL（伪代码）**，用于表达字段与约束语义，**不可直接在 DuckDB 执行**。  
> DuckDB 落地时请改写为 `CREATE TABLE ...` + `CREATE INDEX ...`，字段注释改为独立文档或 `COMMENT ON` 形式。

### 3.1 daily_report 表（L4分析库）

```sql
CREATE TABLE daily_report (
    report_date VARCHAR(8) PRIMARY KEY,
    market_temperature DECIMAL(8,4),
    cycle VARCHAR(20),
    trend VARCHAR(20),
    position_advice VARCHAR(50),
    signal_count INT,
    filled_count INT,
    reject_count INT,
    hit_rate DECIMAL(8,4),
    avg_return_5d DECIMAL(8,4),
    avg_holding_days DECIMAL(8,2),
    total_return DECIMAL(10,4),
    max_drawdown DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    top_recommendations JSON,
    risk_summary JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

索引：
- PRIMARY KEY: report_date

### 3.2 performance_metrics 表（L4分析库）

```sql
CREATE TABLE performance_metrics (
    metric_date VARCHAR(8) PRIMARY KEY,
    total_return DECIMAL(10,4),
    annual_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    volatility DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    calmar_ratio DECIMAL(10,4),
    win_rate DECIMAL(8,4),
    profit_factor DECIMAL(10,4),
    total_trades INT,
    avg_holding_days DECIMAL(8,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 signal_attribution 表（L4分析库）

```sql
CREATE TABLE signal_attribution (
    trade_date VARCHAR(8) PRIMARY KEY,
    mss_attribution DECIMAL(10,6),
    irs_attribution DECIMAL(10,6),
    pas_attribution DECIMAL(10,6),
    sample_count INT,
    raw_sample_count INT,
    trimmed_sample_count INT,
    trim_ratio DECIMAL(8,4),
    attribution_method VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 live_backtest_deviation 表（L4分析库）

```sql
CREATE TABLE live_backtest_deviation (
    trade_date VARCHAR(8) PRIMARY KEY,
    signal_deviation DECIMAL(10,6),
    execution_deviation DECIMAL(10,6),
    cost_deviation DECIMAL(10,6),
    total_deviation DECIMAL(10,6),
    dominant_component VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 输入数据依赖

### 4.1 L3算法输出

| 数据表 | 用途 | 关键字段 |
|--------|------|----------|
| mss_panorama | 市场温度、周期、趋势 | temperature, cycle, trend |
| irs_industry_daily | 行业评分、轮动状态 | industry_code, industry_score, rotation_status |
| stock_pas_daily | 个股评分、方向 | stock_code, opportunity_score, direction |
| integrated_recommendation | 集成推荐与归因基准 | stock_code, mss_score, irs_score, pas_score, entry |

### 4.2 L3运行时数据

| 数据表 | 用途 | 关键字段 |
|--------|------|----------|
| trade_records | 交易记录（实盘分析场景） | stock_code, filled_price/price, status, commission, slippage, impact_cost_bps |
| positions | 持仓数据 | stock_code, industry_code, market_value |
| backtest_trade_records | 回测成交记录（回测分析场景） | stock_code, filled_price/price, status, commission, slippage, impact_cost_bps |
| backtest_results | 回测结果（含 equity_curve） | equity_curve |

---

## 5. 可视化数据结构

### 5.1 TemperatureTrendData（温度趋势图）

```python
@dataclass
class TemperatureTrendData:
    """温度趋势图数据"""
    x_axis: List[str]             # 日期序列
    y_axis: List[float]           # 温度序列
    cycle_markers: List[dict]     # 周期标记点
    advice_zones: List[dict]      # 仓位建议区域
```

### 5.2 IndustryRadarData（行业雷达图）

```python
@dataclass
class IndustryRadarData:
    """行业轮动雷达图数据"""
    industries: List[str]         # 行业名称
    scores: List[float]           # 行业评分
    status: List[str]             # 轮动状态
    highlight_indices: List[int]  # IN行业索引
```

### 5.3 ScoreDistributionData（评分分布图）

```python
@dataclass
class ScoreDistributionData:
    """PAS评分分布图数据"""
    bins: List[float]             # 分数区间
    counts: List[int]             # 各区间数量
    industry_breakdown: dict      # 按行业分组
```

---

## 6. 报告模板数据

### 6.1 日报模板字段

| 模板变量 | 数据来源 | 类型 |
|----------|----------|------|
| {{report_date}} | DailyReport.report_date | str |
| {{market_temperature}} | DailyReport.market_temperature | float |
| {{cycle}} | DailyReport.cycle | str |
| {{industry_rotation_top5}} | IndustryRotation.top5 | List |
| {{signal_count}} | SignalStats.signal_count | int |
| {{filled_count}} | SignalStats.filled_count | int |
| {{reject_count}} | SignalStats.reject_count | int |
| {{hit_rate}} | DailyReport.hit_rate | float |
| {{total_return}} | PerformanceSummary.total_return_pct | str |
| {{max_drawdown}} | PerformanceSummary.max_drawdown_pct | str |
| {{sharpe_ratio}} | PerformanceSummary.sharpe_ratio | float |
| {{win_rate}} | PerformanceSummary.win_rate_pct | str |
| {{top_recommendations_table}} | List[RecommendationSummary] | table |
| {{risk_summary}} | RiskSummary.risk_alert | str |

### 6.2 看板快照字段（GUI/治理共用）

| 字段 | 类型 | 说明 |
|------|------|------|
| report_date | str | 报告日期 |
| analysis_state | str | 分析状态（ok/warn_data_fallback/partial_skipped） |
| summary.total_return | float | 总收益率 |
| summary.max_drawdown | float | 最大回撤 |
| attribution.attribution_method | str | 归因方法 |
| risk.high_risk_change_rate | float | 高风险变化率 |
| risk.risk_turning_point | str | 风险拐点 |
| deviation.total_deviation | float | 实盘-回测总偏差 |
| deviation.dominant_component | str | 主导偏差项 |

---

## 7. 枚举定义

### 7.1 MetricType（指标类型）

```python
class MetricType(Enum):
    RETURN = "return"           # 收益类
    RISK = "risk"               # 风险类
    RISK_ADJUSTED = "risk_adj"  # 风险调整收益类
    TRADE_STAT = "trade_stat"   # 交易统计类
```

### 7.2 ReportType（报告类型）

```python
class ReportType(Enum):
    DAILY = "daily"             # 日报
    WEEKLY = "weekly"           # 周报
    MONTHLY = "monthly"         # 月报
    BACKTEST = "backtest"       # 回测报告
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.0 | 2026-02-14 | 闭环修订：`SignalAttribution` 补齐稳健归因字段（raw/trimmed/trim_ratio/method）；新增 `LiveBacktestDeviation` 数据结构与 DDL；`RiskSummary` 补齐变化率/拐点/状态字段；输入依赖补齐成本字段；新增看板快照字段规范 |
| v3.1.7 | 2026-02-12 | 修复 R16：temperature_level 改为 4 级并补齐 cycle 的 unknown；删除 IndustryRotation.strong_count（无算法来源）；统一 IndustryRadarData 索引注释为 IN |
| v3.1.6 | 2026-02-09 | 修复 R28：`DailyReport` dataclass 补齐 `total_return` 字段，与 `daily_report` DDL 一致 |
| v3.1.5 | 2026-02-09 | 修复 R21：`DailyReportData` 补齐 `created_at`；`daily_report` DDL 增加 `total_return`；输入依赖表补齐归因所需 `integrated_recommendation.entry` 与成交价关键字段 |
| v3.1.4 | 2026-02-08 | 修复 R15：`PerformanceMetrics` 数据类与 `performance_metrics` DDL 补齐 `volatility` 字段 |
| v3.1.3 | 2026-02-08 | 修复 R11：Sortino 分母符号统一为下行偏差 RMS（Downside Deviation），与 Backtest 口径一致 |
| v3.1.2 | 2026-02-08 | 修复 R10：Sharpe/Sortino 公式补入 `rf`（与 Backtest 统一） |
| v3.1.1 | 2026-02-07 | 修复 P2：DDL 明确标注为 DuckDB 不可直接执行的逻辑伪代码 |
| v3.1.0 | 2026-02-04 | 对齐边界与回测依赖口径 |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型定义 |
| v2.1.0 | 2026-01-23 | 增加信号归因数据结构 |
| v2.0.0 | 2026-01-20 | 初始版本 |

---

**关联文档**：
- 核心算法：[analysis-algorithm.md](./analysis-algorithm.md)
- API接口：[analysis-api.md](./analysis-api.md)
- 信息流：[analysis-information-flow.md](./analysis-information-flow.md)


