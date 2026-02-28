# Reborn 第二螺旋：Full 闭环（Plan B）

**螺旋编号**: Reborn-Spiral-2  
**更新时间**: 2026-02-25  
**周期**: 3-4个月  
**定位**: 全历史数据与完整校准闭环，不允许“局部通过即宣告完成”

---

## 1. 螺旋目标

1. 在全市场与16年历史窗口验证策略稳健性。
2. 完成从归因到校准到极端防御的完整证据链。
3. 产出可审计 `GO/NO_GO`，作为进入生产螺旋的唯一依据。

---

## 2. 设计文档绑定（字段级）

| 设计域 | 文档目录 | 关键验证字段 |
|---|---|---|
| Data | `data-layer/data-layer-data-models.md` | 16年落库、`fetch_progress.json`、幂等写入 |
| Backtest | `backtest/backtest-data-models.md` | 多窗口 `backtest_results`、`backtest-test-cases.md` >=19条核心用例 |
| Trading | `trading/trading-data-models.md` | `RejectReason` 4核心路径、`TradingState` 4值、`risk_reward_ratio` |
| Analysis | `analysis/analysis-data-models.md` | `dominant_component`、`attribution_method`、`PerformanceMetrics` 7+4指标 |
| IRS | `irs/irs-data-models.md` | `industry_snapshot` 31行业、`market_amount_total/style_bucket` |
| MSS | `mss/mss-data-models.md` | `T30/T45/T60/T75` 自适应阈值、`top_bottom_spread_5d` |
| Validation | `validation/validation-data-models.md` | `factor_gate_raw`、`selected_weight_plan`、`oos_return/max_drawdown/sharpe/tradability_pass_ratio` |
| Integration | `integration/integration-data-models.md` | `integration_state` 5值、消费链持续有效 |

---

## 3. 微圈体系与 Plan A 映射

| PB 微圈 | 名称 | 对应 Plan A | 前置 | 核心产出 |
|---|---|---|---|---|
| PB-2.1 | 采集扩窗 | S3a/S3ar | 螺旋1 GO | 16年落库 + 采集稳定性证据 |
| PB-2.2 | 完整回测与归因 | S3/S4/S3b | PB-2.1 GO | 多窗口回测 + A/B/C + 完整归因 |
| PB-2.3 | 行业校准 | S3c | PB-2.2 GO | SW31 全覆盖 + IRS 输入校准 |
| PB-2.4 | MSS/Validation 校准 | S3d/S3e | PB-2.3 GO | adaptive 阈值 + 双窗口 WFA + factor_gate_raw 健康 |
| PB-2.5 | 极端防御 | S4b | PB-2.4 GO | 防御参数可追溯 + 压力场景回放 |

---

## 4. PB-2.1 采集扩窗合同

- **主目标**：16年数据落库 + 采集稳定性可审计。
- **Plan A 对应**：S3a/S3ar
- **ENH**：ENH-10
- `run`：`eq fetch-batch --start 20080101 --end 20241231 --batch-size 365 --workers 3` + `eq fetch-retry`
- `test`：`tests/unit/data/test_fetch_batch_contract.py tests/unit/data/test_fetch_resume_contract.py tests/unit/data/test_fetcher_contract.py`
- 门禁：
  - 数据窗口 `2008-01-01 ~ 2024-12-31`，覆盖率 >=99%。
  - `fetch_progress.json` 可追溯，含 `last_success_batch_id`。
  - 主/兆底独立限速可验证，切换记录可审计。
  - DuckDB 锁冲突可恢复，幂等写入必须成立。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`fetch_progress.json`、`fetch_retry_report.md`、`throughput_benchmark.md`
- 消费：PB-2.2 记录“回测窗口所用数据已通过采集稳定性门禁”。

---

## 5. PB-2.2 完整回测与归因合同

- **主目标**：多窗口回测 + A/B/C 对照 + 完整归因可回答收益来源。
- **Plan A 对应**：S3/S4/S3b
- **ENH**：ENH-04(Backtest)/06/09
- `run`：
  - `eq backtest --engine {engine} --start {start} --end {end}`（多窗口：1y/3y/5y + 牛熊段）
  - `eq trade --mode paper --date {trade_date}`
  - `eq analysis --start {start} --end {end} --ab-benchmark`
  - `eq analysis --date {trade_date} --deviation live-backtest`
- 门禁：
  - 多窗口回测可复现，收益曲线 + 交易记录齐备。
  - `backtest-test-cases.md` >=19条核心用例通过。
  - A/B/C 对照结果齐备（情绪主线/基线/对照）。
  - `signal_deviation/execution_deviation/cost_deviation` 三分解齐备。
  - 形成“收益来源结论”（信号主导或执行主导）。
  - `dominant_component≠'none'` 比例 >=50%。
  - `RejectReason` 至少覆盖 `REJECT_LIMIT_UP/REJECT_T1_FROZEN/REJECT_MAX_POSITION/REJECT_NO_CASH`。
  - `TradingState` 4值至少各出现 1次。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`backtest_results.parquet`、`trade_records_sample.parquet`、`ab_benchmark_report.md`、`attribution_summary.json`
- 消费：PB-2.3 记录“行业校准所用窗口与归因结论已固化”。

---

## 6. PB-2.3 行业校准合同

- **主目标**：SW31 全行业覆盖 + IRS 输入字段校准。
- **Plan A 对应**：S3c
- **ENH**：ENH-04(IRS)
- `run`：
  - `eq run --date {trade_date} --to-l2 --strict-sw31`
  - `eq irs --date {trade_date} --require-sw31`
- 门禁：
  - `industry_snapshot` 当日记录数 =31，不得出现 `industry_code=ALL`。
  - `industry_snapshot` 必须包含 `market_amount_total/style_bucket` 与质量字段。
  - `allocation_advice` 覆盖 31 行业，无空档。
  - MVP：31行业覆盖齐全，允许可解释 WARN。
  - FULL：近3窗口稳定覆盖，告警闭环。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`industry_snapshot_sw31_sample.parquet`、`irs_allocation_coverage_report.md`、`sw_mapping_audit.md`
- 消费：PB-2.4 记录“MSS 自适应所需行业输入已校准”。

---

## 7. PB-2.4 MSS/Validation 校准合同

- **主目标**：MSS adaptive 校准 + Validation 生产校准 + 双窗口 WFA。
- **Plan A 对应**：S3d/S3e
- **ENH**：ENH-04(MSS/Validation)
- `run`：
  - `eq mss --date {trade_date} --threshold-mode adaptive`
  - `eq mss-probe --start {start} --end {end} --return-series-source future_returns`
  - `eq validation --trade-date {trade_date} --threshold-mode regime --wfa dual-window`
  - `eq validation --trade-date {trade_date} --export-run-manifest`
- 门禁（S3d）：
  - 周期阈值 `T30/T45/T60/T75`，样本不足自动回退固定阈值。
  - 趋势判定 `EMA + slope + trend_band`，异常兆底可用。
  - `top_bottom_spread_5d` 基于真实收益序列，禁止未来函数。
  - MVP：自适应可运行，样本不足可回退。FULL：关键窗口无负 spread，probe 可复跑。
- 门禁（S3e）：
  - 因子验证 `factor_series × future_returns` 按 `trade_date, stock_code` 对齐，禁止未来函数。
  - 双窗口投票 + `oos_return/max_drawdown/sharpe/turnover/impact_cost_bps/tradability_pass_ratio`。
  - `selected_weight_plan` 必须由投票可审计产生。
  - **factor_gate_raw=FAIL 升级策略**：
    - FAIL 比例 >50%：回 S3d 检查 MSS adaptive。
    - 连续 ≥2 窗口 FAIL 但 neutral_regime 软化通过：必须产出审计报告。
    - FULL 口径要求不得 FAIL 但当前全 FAIL：螺旋2不得宣称生产就绪，状态锁定 `WARN_PENDING_RESOLUTION`。
  - MVP：`final_gate` 不得 FAIL。FULL：`factor_gate_raw` 不得 FAIL + OOS 达标。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`mss_regime_thresholds_snapshot.json`、`mss_probe_return_series_report.md`、`validation_factor_report_sample.parquet`、`validation_oos_calibration_report.md`、`neutral_regime_audit_report.md`（条件产出）
- 消费：PB-2.5 记录“极端防御参数来自 S3b 归因 + S3e 校准联合证据”。

---

## 8. PB-2.5 极端防御合同

- **主目标**：连续跌停、流动性枯竭场景的极端防御闭环。
- **Plan A 对应**：S4b
- **ENH**：ENH-04(Trading)
- `run`：
  - `eq stress --scenario limit_down_chain --date {trade_date}`
  - `eq stress --scenario liquidity_dryup --date {trade_date}`
- 门禁：
  - 组合级应急降杠杆触发链可执行且可重放。
  - 连续不可成交场景下次日重试与仓位封顶可验证。
  - 防御参数来源可追溯到 `S3b 归因 + S3e Validation 生产校准`（禁止人工拍值）。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`extreme_defense_report.md`、`deleveraging_policy_snapshot.json`、`stress_trade_replay.csv`
- 消费：螺旋2 收口评审。

---

## 9. S3c/S3d/S3e 双档量化门禁（汇总）

| 圈位 | MVP（最小可用） | FULL（完整生产口径） |
|---|---|---|
| S3c | 31行业覆盖齐全，允许可解释 WARN | 近3窗口稳定覆盖，告警闭环 |
| S3d | 自适应可运行，样本不足可回退固定阈值 | 关键窗口无负 spread，probe 可复跑 |
| S3e | `final_gate` 不得 FAIL；`factor_gate_raw=FAIL` 仅允 neutral_regime 软化且必须审计 | `factor_gate_raw` 不得 FAIL，OOS 达标，`selected_weight_plan` 全链可追 |

补充：准备可并行，收口串行 `S3c -> S3d -> S3e`。未达 MVP 不得进 S4b；未达 FULL 不得宣称生产就绪。

---

## 10. 螺旋2门禁汇总

### 10.1 入口门禁

- 螺旋1 `GO`
- `validation_weight_plan` 桥接链稳定

### 10.2 出口门禁

- [ ] PB-2.1~PB-2.5 各微圈 gate 均 PASS/WARN
- [ ] 16年数据落库并通过质量检查
- [ ] 多窗口回测与 A/B/C 对照齐备
- [ ] 完整归因可回答收益来源
- [ ] S3c/S3d/S3e MVP/FULL 均通过
- [ ] S4b 参数可追溯到 S3b+S3e
- [ ] `PLAN-B-READINESS-SCOREBOARD.md` 更新并给 `GO/NO_GO`

---

## 11. 失败处理

1. 微圈 gate 未通过：仅允许在当前微圈范围修复。
2. 螺旋2 出口任一项未通过：`NO_GO`，不得推进螺旋3。
3. 校准链连续卡住：允许回到对应微圈重验，不得跳微圈宣告完成。

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.0 | 2026-02-25 | 堵最大缺口：拆分为 PB-2.1~PB-2.5 微圈执行合同；设计绑定到字段级；增加 factor_gate_raw 升级策略、RejectReason/TradingState 覆盖、backtest-test-cases 核心用例、微圈间消费链 |
| v2.2 | 2026-02-24 | 重写为设计绑定执行合同 |
| v2.1 | 2026-02-23 | 新增双档量化门禁 |
