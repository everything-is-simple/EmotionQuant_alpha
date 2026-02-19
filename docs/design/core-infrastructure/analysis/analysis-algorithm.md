# Analysis 核心算法

**版本**: v3.2.0（重构版）
**最后更新**: 2026-02-14
**状态**: 设计完成（闭环口径补齐；S3b 最小实现已落地，持续增强中）

---

## 实现状态（仓库现状）

- `src/analysis/pipeline.py` 已落地最小实现：A/B/C 对照、实盘-回测偏差分解、归因摘要与标准产物输出。
- 本文档为闭环设计口径；实现阶段需以此为准并同步更新记录。

---

## 1. 算法定位

Analysis层负责对回测与实盘结果进行复盘分析，核心职责：

1. **绩效分析**：计算收益率、风险指标、交易统计
2. **信号评估**：评估MSS/IRS/PAS信号的有效性与贡献度
3. **报告输出**：生成日报/周报级别的分析摘要
4. **闭环落地**：执行 `compute_metrics -> attribute_signals -> generate_daily_report -> persist/export`

**重要约束**：遵循系统铁律，不引入技术指标计算；Analysis 仅消费 L3 算法输出与回测/实盘结果，产出 L4 分析指标与报告，不替代 L3 算法。

**外部库边界**：不得以 quantstats/empyrical 等第三方库替代 Analysis 模块，可在实现阶段作为内部计算工具使用（不改变输出口径）。

**输出规范**：报告与导出统一落盘 `.reports/analysis/`，文件名使用 `{YYYYMMDD_HHMMSS}` 时间戳。

**口径一致**：日报/周报/月报共享同一指标计算与异常处理规则。

**输入/输出**：
- 输入：`mss_panorama`、`irs_industry_daily`、`stock_pas_daily`、`integrated_recommendation`；`trade_records` / `backtest_trade_records`、`backtest_results`（含 equity_curve）、`positions`
- 输出：`performance_metrics`、`signal_attribution`、`daily_report`、`live_backtest_deviation`、`analysis_dashboard_snapshot`（含周报/月报汇总）及 `.reports/analysis/` 下的报告文件

### 1.1 CP-08 最小可运行闭环（P0）

```
输入: trade_date, start_date, end_date
输出: AnalysisRunResult(state, saved_tables, exported_files)

def run_minimal(trade_date, start_date, end_date):
    # 1) 绩效计算 + 落库
    metrics = compute_metrics(start_date, end_date)
    repo.save_performance_metrics(metrics)

    # 2) 信号归因（稳健口径）+ 落库
    attribution = attribute_signals(
        trade_date=trade_date,
        trim_quantile=0.05,     # 去极值：双尾 5%
        min_sample_count=20
    )
    repo.save_signal_attribution(attribution)

    # 3) 日报构建 + 落库
    report = generate_daily_report(trade_date)
    repo.save_daily_report(report)

    # 4) 文件导出（标准目录）
    md_path = export_to_file(render_markdown(report), "daily_report", "md")
    csv_metrics = export_metrics_csv(metrics, "performance_metrics")
    csv_attr = export_signal_attribution_csv(attribution, "signal_attribution")
    dashboard_json = export_dashboard_snapshot(trade_date)

    return AnalysisRunResult(
        state="completed",
        saved_tables=["performance_metrics", "signal_attribution", "daily_report"],
        exported_files=[md_path, csv_metrics, csv_attr, dashboard_json]
    )
```

---

## 2. 绩效指标计算

### 2.1 收益率计算

```
输入: equity_curve (净值序列)
输出: total_return, annual_return, daily_returns

# 日收益率
r_t = equity[t] / equity[t-1] - 1

# 总收益率
total_return = equity[-1] / equity[0] - 1

# 年化收益率 (假设252个交易日)
N = len(equity_curve) - 1
annual_return = (equity[-1] / equity[0]) ** (252 / N) - 1 if N > 0 else 0
```

### 2.2 风险指标计算

```
输入: daily_returns, equity_curve
输出: max_drawdown, volatility

# 最大回撤
peak = running_max(equity_curve)
drawdown = (equity - peak) / peak
max_drawdown = min(drawdown)  # 负值

# 年化波动率
volatility = std(daily_returns) × sqrt(252)
```

### 2.3 风险调整收益指标

```
输入: daily_returns, risk_free_rate=0.015
输出: sharpe_ratio, sortino_ratio, calmar_ratio

# 夏普比率
daily_rf = risk_free_rate / 252
sharpe_ratio = sqrt(252) × (mean(r) - daily_rf) / std(r)

# 索提诺比率 (仅考虑下行波动)
downside_deviations = [min(r - daily_rf, 0) for r in daily_returns]
downside_std = sqrt(mean([x**2 for x in downside_deviations])) if downside_deviations else 0
sortino_ratio = sqrt(252) × (mean(r) - daily_rf) / downside_std if downside_std > 0 else 0

# 卡玛比率
calmar_ratio = annual_return / abs(max_drawdown)
```

### 2.4 交易统计指标

```
输入: trades (交易记录列表)
输出: win_rate, profit_factor, avg_holding_days

# 无交易
if len(trades) == 0:
    win_rate = 0
    profit_factor = 0
    avg_holding_days = 0
else:
    # 胜率
    winning_trades = [t for t in trades if t.pnl > 0]
    win_rate = len(winning_trades) / len(trades)

    # 盈亏比
    total_profit = sum(t.pnl for t in trades if t.pnl > 0)
    total_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    # 平均持仓天数（使用预计算字段）
    holding_days = [t.hold_days for t in trades]
    avg_holding_days = mean(holding_days) if holding_days else 0
```

---

## 3. 信号有效性评估

### 3.1 信号命中率

```
输入: signals, price_data, forward_days=5
输出: hit_rate, avg_forward_return

# 统计信号后N日收益
for signal in signals:
    entry = price_data[signal.date][signal.stock_code]
    future_price = price_data[signal.date + forward_days][signal.stock_code]
    if entry is None or future_price is None:
        continue
    forward_return = (future_price - entry) / entry

    if signal.direction == "bullish" and forward_return > 0:
        hit_count += 1
    elif signal.direction == "bearish" and forward_return < 0:
        hit_count += 1

hit_rate = hit_count / len(signals)
avg_forward_return = mean(forward_returns)
```

### 3.2 信号延迟偏差

```
输入: signals, trades
输出: avg_delay, avg_price_deviation

for signal in signals:
    trade = find_trade(trades, signal.stock_code, signal.date)
    if trade:
        # 执行延迟（天数）
        delay = (trade.trade_date - signal.date).days
        # 价格偏差
        price_deviation = (trade.filled_price - signal.entry) / signal.entry
        delays.append(delay)
        deviations.append(price_deviation)

avg_delay = mean(delays)
avg_price_deviation = mean(deviations)
```

---

## 4. 信号归因算法

### 4.1 MSS/IRS/PAS贡献度计算

```
输入: trade_date
输出: mss_attribution, irs_attribution, pas_attribution, sample_count

def attribute_signals(trade_date, trim_quantile=0.05, min_sample_count=20):
    # 获取当日推荐和成交
    recs = repo.get_integrated_recommendation(trade_date)
    is_backtest = repo.is_backtest_context(trade_date)
    trades = (
        repo.get_backtest_trade_records(trade_date)
        if is_backtest else
        repo.get_trade_records(trade_date)
    )

    # 筛选已成交的推荐
    filled = {t.stock_code: t for t in trades if t.status == "filled"}

    mss_contrib = []
    irs_contrib = []
    pas_contrib = []

    for rec in recs:
        if rec.stock_code not in filled:
            continue

        trade = filled[rec.stock_code]
        exec_price = trade.filled_price if hasattr(trade, "filled_price") else trade.price
        # 计算执行偏差（成交价相对建议入场价）；非真实交易盈亏
        execution_deviation = (exec_price - rec.entry) / rec.entry if rec.entry and rec.entry > 0 else 0

        # 加权贡献度 = 信号评分 × 执行偏差（评估信号执行质量）
        mss_contrib.append(rec.mss_score * execution_deviation)
        irs_contrib.append(rec.irs_score * execution_deviation)
        pas_contrib.append(rec.pas_score * execution_deviation)

    raw_sample_count = len(mss_contrib)
    if raw_sample_count < min_sample_count:
        # 冷启动样本不足：降级到原始均值，避免过度截尾
        mss_robust = mss_contrib
        irs_robust = irs_contrib
        pas_robust = pas_contrib
        method = "mean_fallback_small_sample"
    else:
        # 稳健口径：双尾分位截尾（去极值）
        mss_robust = trim_by_quantile(mss_contrib, lower=trim_quantile, upper=1-trim_quantile)
        irs_robust = trim_by_quantile(irs_contrib, lower=trim_quantile, upper=1-trim_quantile)
        pas_robust = trim_by_quantile(pas_contrib, lower=trim_quantile, upper=1-trim_quantile)
        method = f"trimmed_mean_q{trim_quantile:.2f}"

    return {
        "mss_attribution": sum(mss_robust) / max(len(mss_robust), 1),
        "irs_attribution": sum(irs_robust) / max(len(irs_robust), 1),
        "pas_attribution": sum(pas_robust) / max(len(pas_robust), 1),
        "sample_count": len(mss_robust),
        "raw_sample_count": raw_sample_count,
        "trimmed_sample_count": len(mss_robust),
        "trim_ratio": 1 - (len(mss_robust) / max(raw_sample_count, 1)),
        "attribution_method": method
    }
```

### 4.2 行业轮动命中率

```
输入: irs_signals, trade_results
输出: rotation_hit_rate

# IRS预测 vs 实际行业表现
for date, irs_data in irs_signals:
    # IRS预测的Top行业
    predicted_top = {i.industry_code for i in irs_data if i.rotation_status == "IN"}

    # 实际表现最好的行业
    actual_returns = calculate_industry_returns(date, forward_days=5)
    actual_top = {i for i, r in actual_returns.items() if r > median(actual_returns.values())}

    # 命中 = 预测与实际交集
    hit = len(predicted_top & actual_top) / len(predicted_top) if predicted_top else 0
    hits.append(hit)

rotation_hit_rate = mean(hits)
```

### 4.3 实盘-回测偏差归因（P1）

```
输入: trade_date
输出: signal_deviation, execution_deviation, cost_deviation, total_deviation

def decompose_live_backtest_deviation(trade_date):
    # 同日双口径对比：实盘与回测必须共享同一推荐池（按 stock_code 对齐）
    live = repo.get_live_recommendation_outcome(trade_date)
    bt = repo.get_backtest_recommendation_outcome(trade_date)

    # 信号偏差：推荐池本身收益差（选股/打分层）
    signal_deviation = mean(live.forward_return_5d) - mean(bt.forward_return_5d)

    # 成交偏差：执行偏差差值（成交价相对 entry）
    execution_deviation = mean(live.execution_deviation) - mean(bt.execution_deviation)

    # 成本偏差：佣金+滑点+冲击成本差值
    live_cost_rate = mean(live.commission_rate + live.slippage_rate + live.impact_cost_rate)
    bt_cost_rate = mean(bt.commission_rate + bt.slippage_rate + bt.impact_cost_rate)
    cost_deviation = live_cost_rate - bt_cost_rate

    total_deviation = signal_deviation + execution_deviation - cost_deviation
    dominant_component = argmax_abs({
        "signal": signal_deviation,
        "execution": execution_deviation,
        "cost": cost_deviation
    })

    return {
        "signal_deviation": signal_deviation,
        "execution_deviation": execution_deviation,
        "cost_deviation": cost_deviation,
        "total_deviation": total_deviation,
        "dominant_component": dominant_component
    }
```

---

## 5. 风险分析算法

### 5.1 风险等级分布

```
输入: recommendations
输出: risk_distribution

# 基于 ValidationResult.risk_level + neutrality 统计
risk_counts = {"low": 0, "medium": 0, "high": 0}

# 基于 neutrality 分级（越低越极端）
for rec in recommendations:
    if rec.neutrality <= 0.3:
        risk_counts["low"] += 1   # 中性度低→信号极端→低风险
    elif rec.neutrality <= 0.6:
        risk_counts["medium"] += 1
    else:
        risk_counts["high"] += 1  # 中性度高→信号不明确→高风险

total = sum(risk_counts.values())
prev = repo.get_previous_risk_summary()
high_risk_change_rate = (
    (risk_counts["high"] - prev.high_risk_count) / max(prev.high_risk_count, 1)
    if prev else 0
)
low_risk_change_rate = (
    (risk_counts["low"] - prev.low_risk_count) / max(prev.low_risk_count, 1)
    if prev else 0
)
risk_turning_point = (
    "risk_up_turn"
    if high_risk_change_rate > 0.2 and low_risk_change_rate < -0.1
    else "risk_down_turn"
    if high_risk_change_rate < -0.2 and low_risk_change_rate > 0.1
    else "none"
)
risk_regime = (
    "risk_on"
    if risk_counts["low"] >= risk_counts["high"] * 1.5
    else "risk_off"
    if risk_counts["high"] >= risk_counts["low"] * 1.5
    else "neutral"
)

risk_distribution = {
    "low_risk_count": risk_counts["low"],
    "medium_risk_count": risk_counts["medium"],
    "high_risk_count": risk_counts["high"],
    "low_pct": risk_counts["low"] / total,
    "medium_pct": risk_counts["medium"] / total,
    "high_pct": risk_counts["high"] / total,
    "high_risk_change_rate": high_risk_change_rate,
    "low_risk_change_rate": low_risk_change_rate,
    "risk_turning_point": risk_turning_point,
    "risk_regime": risk_regime
}
```

### 5.2 行业集中度风险

```
输入: positions
输出: industry_concentration

# 计算各行业持仓占比
industry_values = defaultdict(float)
total_value = sum(p.market_value for p in positions)

for position in positions:
    industry_values[position.industry_code] += position.market_value

# 计算赫芬达尔指数 (HHI)
hhi = sum((v / total_value) ** 2 for v in industry_values.values())

# 最大行业占比
max_concentration = max(v / total_value for v in industry_values.values())
# 最大行业代码
top_industry = max(industry_values, key=industry_values.get)

return {
    "hhi": hhi,
    "max_concentration": max_concentration,
    "industry_count": len(industry_values),
    "top_industry": top_industry
}
```

---

## 6. 日报生成算法

### 6.1 日报数据汇总

```
输入: report_date
输出: DailyReportData

def generate_daily_report(report_date):
    # 1. 市场概况
    mss = repo.get_mss_panorama(report_date)
    market_overview = {
        "temperature": mss.temperature,
        "cycle": mss.cycle,
        "trend": mss.trend,
        "position_advice": mss.position_advice
    }

    # 2. 行业轮动
    irs = repo.get_irs_industry_daily(report_date)
    top_industries = sorted(irs, key=lambda x: x.rank)[:5]
    industry_rotation = {
        "top5": [(i.industry_name, i.industry_score) for i in top_industries],
        "in_count": sum(1 for i in irs if i.rotation_status == "IN"),
        "out_count": sum(1 for i in irs if i.rotation_status == "OUT")
    }

    # 3. 信号与成交
    signals = repo.get_integrated_recommendation(report_date)
    is_backtest = repo.is_backtest_context(report_date)
    trades = (
        repo.get_backtest_trade_records(report_date)
        if is_backtest else
        repo.get_trade_records(report_date)
    )
    signal_stats = {
        "signal_count": len(signals),
        "filled_count": sum(1 for t in trades if t.status == "filled"),
        "reject_count": sum(1 for t in trades if t.status == "rejected")
    }

    # 4. 绩效摘要
    metrics = repo.get_performance_metrics(report_date)
    performance = {
        "total_return": metrics.total_return,
        "max_drawdown": metrics.max_drawdown,
        "sharpe_ratio": metrics.sharpe_ratio,
        "win_rate": metrics.win_rate
    }

    # 5. 推荐列表
    top_recommendations = signals[:10]

    # 6. 风险提示
    risk_summary = calculate_risk_distribution(signals)

    return DailyReportData(
        report_date=report_date,
        market_overview=market_overview,
        industry_rotation=industry_rotation,
        signal_stats=signal_stats,
        performance=performance,
        top_recommendations=top_recommendations,
        risk_summary=risk_summary
    )
```

### 6.2 Markdown渲染

```
输入: DailyReportData, template
输出: markdown_content

def render_report(data, template="daily_report"):
    template = load_template(template)

    # 替换变量
    content = template.replace("{{report_date}}", data.report_date)
    content = content.replace("{{market_temperature}}", str(data.market_overview["temperature"]))
    content = content.replace("{{industry_rotation_top5}}", format_top5(data.industry_rotation["top5"]))
    # ... 其他字段

    # 渲染推荐表格
    table = render_recommendation_table(data.top_recommendations)
    content = content.replace("{{top_recommendations_table}}", table)

    return content
```

### 6.3 GUI/治理对接快照（P2）

```
输入: report_date, metrics, attribution, risk_summary, deviation
输出: analysis_dashboard_snapshot

def build_dashboard_snapshot(report_date, metrics, attribution, risk_summary, deviation):
    # 单一快照供 GUI 与治理看板复用，避免二次手工汇总
    return {
        "report_date": report_date,
        "analysis_state": "ok",
        "summary": {
            "total_return": metrics.total_return,
            "max_drawdown": metrics.max_drawdown,
            "sharpe_ratio": metrics.sharpe_ratio,
            "win_rate": metrics.win_rate
        },
        "attribution": {
            "mss_attribution": attribution.mss_attribution,
            "irs_attribution": attribution.irs_attribution,
            "pas_attribution": attribution.pas_attribution,
            "sample_count": attribution.sample_count,
            "attribution_method": attribution.attribution_method
        },
        "risk": {
            "high_risk_pct": risk_summary.high_risk_pct,
            "high_risk_change_rate": risk_summary.high_risk_change_rate,
            "risk_turning_point": risk_summary.risk_turning_point
        },
        "deviation": {
            "total_deviation": deviation.total_deviation,
            "dominant_component": deviation.dominant_component
        }
    }
```

---

## 7. 完整绩效计算流程

```
输入: start_date, end_date, equity_curve, trades
输出: PerformanceMetrics

def compute_performance_metrics(start_date, end_date, equity_curve, trades):
    # 1. 收益计算
    daily_returns = calculate_daily_returns(equity_curve)
    total_return = equity_curve[-1] / equity_curve[0] - 1
    N = len(daily_returns)
    annual_return = (1 + total_return) ** (252 / N) - 1 if N > 0 else 0

    # 2. 风险计算
    max_drawdown = calculate_max_drawdown(equity_curve)
    volatility = std(daily_returns) * sqrt(252)

    # 3. 风险调整收益
    risk_free_rate = 0.015  # 默认与 BacktestConfig 口径一致
    daily_rf = risk_free_rate / 252
    mean_return = mean(daily_returns)
    std_return = std(daily_returns)
    sharpe = sqrt(252) * (mean_return - daily_rf) / std_return if std_return > 0 else 0

    downside_deviations = [min(r - daily_rf, 0) for r in daily_returns]
    downside_std = sqrt(mean([x**2 for x in downside_deviations])) if downside_deviations else 0
    sortino = sqrt(252) * (mean_return - daily_rf) / downside_std if downside_std > 0 else 0

    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # 4. 交易统计
    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl < 0]
    win_rate = len(winning) / len(trades) if trades else 0

    if not trades:
        win_rate = 0
        profit_factor = 0
        avg_holding = 0
    else:
        total_profit = sum(t.pnl for t in winning)
        total_loss = abs(sum(t.pnl for t in losing))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        avg_holding = mean([t.hold_days for t in trades])

    return PerformanceMetrics(
        metric_date=end_date,
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=len(trades),
        avg_holding_days=avg_holding
    )
```

---

## 8. 异常与缺失处理口径

- **数据缺失**：关键输入缺失则跳过该项计算并标记 `analysis_state="warn_data_fallback"`（不引入跨层回填）
- **净值序列不足**：`equity_curve` 为空或长度不足时跳过绩效计算
- **无交易**：`win_rate = 0`，`profit_factor = 0`，`avg_holding_days = 0`
- **分母为 0**：`std=0` 则 Sharpe/Sortino 置 0；`max_drawdown=0` 则 Calmar 置 0
- **无亏损交易**：`total_loss=0` 且存在交易时 `profit_factor = +inf`

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.0 | 2026-02-14 | 闭环修订：补齐 `run_minimal` 最小链路；归因升级为分位截尾稳健均值；新增实盘-回测偏差分解与前瞻风险字段；新增 GUI/治理快照输出；异常状态统一为 `analysis_state` |
| v3.1.6 | 2026-02-09 | 修复 R21：Sortino 下行分母变量改名为 `downside_deviations/downside_std`；归因与日报流程补齐实盘/回测成交分支；行业集中度补充 `top_industry` 输出 |
| v3.1.5 | 2026-02-08 | 修复 R14：§4.1 将 `pnl_pct` 更名为 `execution_deviation` 并明确语义为执行偏差（非交易盈亏） |
| v3.1.4 | 2026-02-08 | 修复 R12：年化收益率样本数改为 `len(equity_curve)-1`；持仓天数字段统一为 `hold_days`；归因成交价兼容 `filled_price/price` |
| v3.1.3 | 2026-02-08 | 修复 R11：Sortino 分母从 `std(下行收益)` 统一为下行偏差 RMS（`sqrt(mean(min(r-mar,0)^2))`） |
| v3.1.2 | 2026-02-08 | 修复 R10：风险调整收益公式补入 `risk_free_rate`（Sharpe/Sortino 与 Backtest 统一） |
| v3.1.1 | 2026-02-05 | 更新系统铁律表述 |
| v3.1.0 | 2026-02-04 | 对齐边界/依赖/输出规范与异常口径 |
| v3.0.0 | 2026-01-31 | 重构版：统一算法描述 |
| v2.1.0 | 2026-01-23 | 增加信号归因算法 |
| v2.0.0 | 2026-01-20 | 初始版本 |

---

**关联文档**：
- 数据模型：[analysis-data-models.md](./analysis-data-models.md)
- API接口：[analysis-api.md](./analysis-api.md)
- 信息流：[analysis-information-flow.md](./analysis-information-flow.md)


