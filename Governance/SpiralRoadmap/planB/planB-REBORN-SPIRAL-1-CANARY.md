# Reborn 第一螺旋：Canary 闭环（Plan B）

**螺旋编号**: Reborn-Spiral-1  
**更新时间**: 2026-02-25  
**周期**: 2-3个月  
**定位**: 最小可用闭环，不追求全量，只验证“情绪主线能跑通且可解释”

---

## 1. 螺旋目标

1. 在本地数据上跑通 `数据 -> 算法 -> 回测 -> 归因`。
2. 用可审计证据回答“做成了吗、效果如何、能否进入下一螺旋”。
3. 输出 `GO/NO_GO`，不允许“工程完成但业务未知”。

---

## 2. 设计文档绑定（字段级）

| 设计域 | 文档目录 | 关键验证字段 |
|---|---|---|
| Data | `data-layer/data-layer-data-models.md` | `raw_daily.{open,high,low,close,vol,amount}`、`raw_trade_cal.is_open`、`market_snapshot.{temperature,vol_ratio}` |
| MSS | `mss/mss-data-models.md` | `mss_panorama.{temperature,cycle,trend,mss_rank,mss_percentile,trend_quality_score}`、MssCycle 8枚举 |
| IRS | `irs/irs-data-models.md` | `irs_industry_daily.{industry_code,industry_score,rotation_status,allocation_advice}`、SW31 覆盖 |
| PAS | `pas/pas-data-models.md` | `stock_pas_daily.{opportunity_score,direction,neutrality,risk_reward_ratio,entry,stop,target}` |
| Validation | `validation/validation-data-models.md` | `validation_gate_decision.{final_gate,factor_gate_raw,contract_version}`、`validation_weight_plan.{plan_id}` |
| Integration | `integration/integration-data-models.md` | `integrated_recommendation.{weight_plan_id,integration_mode}`、4模式×硬约束 |
| Backtest | `backtest/backtest-data-models.md` | `backtest_results.{total_return,sharpe,max_drawdown}`、`backtest_trade_records` |
| Analysis | `analysis/analysis-data-models.md` | `signal_deviation/execution_deviation/cost_deviation`、`dominant_component` |

---

## 3. 微圈体系与 Plan A 映射

| PB 微圈 | 名称 | 对应 Plan A | 前置 | 核心产出 |
|---|---|---|---|---|
| PB-1.1 | 数据闭环 | S0a-S0c | 无 | L1/L2 落库可用 + 覆盖率门禁 |
| PB-1.2 | 算法闭环 | S1a-S2c | PB-1.1 GO | MSS/IRS/PAS/Validation/Integration 产物齐备 |
| PB-1.3 | 最小回测闭环 | S3(min) | PB-1.2 GO | 回测结果 + 交易记录可复现 |
| PB-1.4 | 最小归因闭环 | S3b(min) | PB-1.3 GO | 三分解 + 双对比 + GO/NO_GO |

---

## 4. PB-1.1 数据闭环合同

- **主目标**：本地 L1/L2 数据落库，覆盖率 >=99%，交易日历可用。
- **Plan A 对应**：S0a/S0b/S0c
- **ENH**：ENH-01/02/03/04(Data)/05/08(骨架)
- `run`：`eq run --date {trade_date} --source tushare`
- `test`：`python -m scripts.quality.local_quality_check --contracts --governance`
- 门禁：
  - 数据窗口最低 `2020-01-01 ~ 2024-12-31`，覆盖率 >=99%。
  - `raw_daily` 字段与 `data-layer-data-models.md` DDL 一一对应（字段名、类型、精度）。
  - `raw_trade_cal.is_open` 可用且与 TuShare 官方交易日历一致。
  - `market_snapshot`、`industry_snapshot` L2 表可产出且记录数 >0。
  - `Config.from_env()` 路径注入可用，无硬编码。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`raw_daily_sample.parquet`、`market_snapshot_sample.parquet`、`data_readiness_gate.md`
- 消费：PB-1.2 记录“算法输入数据已通过数据门禁”。

---

## 5. PB-1.2 算法闭环合同

- **主目标**：MSS/IRS/PAS/Validation/Integration 产物齐备且符合契约。
- **Plan A 对应**：S1a/S1b/S2a/S2b/S2c
- **ENH**：ENH-04(MSS/IRS/PAS/Validation/Integration)
- `run`：`eq run --date {trade_date} --full-pipeline --validate-each-step`
- `test`：契约测试套件（`tests/unit/algorithms/ + tests/unit/integration/`）
- 门禁：
  - `mss_panorama` 含 `temperature/cycle/trend/mss_rank/mss_percentile/trend_quality_score`，MssCycle 8枚举值可触发。
  - `irs_industry_daily` 记录数 >=31（SW31 全覆盖）。
  - `stock_pas_daily` 含 `opportunity_score/direction/neutrality/risk_reward_ratio`，PasDirection 3枚举值可触发。
  - `validation_gate_decision.final_gate` 不得缺失，`contract_version = "nc-v1"`。
  - `validation_weight_plan` 桥接链可追溯：`selected_weight_plan -> plan_id -> integrated_recommendation.weight_plan_id`。
  - `integrated_recommendation` 4模式可审计，硬约束（每日最多20条、行业最多5条）硬运行。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`mss_panorama_sample.parquet`、`integrated_recommendation_sample.parquet`、`validation_gate_report.md`
- 消费：PB-1.3 记录“回测输入信号已通过算法闭环门禁”。

---

## 6. PB-1.3 最小回测闭环合同

- **主目标**：Canary 窗口回测可复现，收益曲线 + 交易记录可产出。
- **Plan A 对应**：S3(min)
- **ENH**：ENH-04(Backtest)/06/09
- `run`：`eq backtest --engine {engine} --start {start} --end {end}`
- `test`：`tests/unit/backtest/test_backtest_contract.py tests/unit/backtest/test_backtest_reproducibility.py`
- 门禁：
  - `backtest_results` 与 `backtest_trade_records` 均可产出且记录数 >0。
  - 输入消费链可追溯到 `integrated_recommendation`，`contract_version = "nc-v1"`。
  - 核心算法全量消费可审计：`mss_score/irs_score/pas_score` 不得缺失。
  - T+1 规则、涨跌停阈值、费用模型与 `backtest-test-cases.md` §1/§2/§4 一致。
  - A/B/C 对照指标摘要可产出。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`backtest_results.parquet`、`backtest_trade_records.parquet`、`ab_metric_summary.md`
- 消费：PB-1.4 记录“归因基于可复现回测结果”。

---

## 7. PB-1.4 最小归因闭环合同

- **主目标**：用可审计证据回答“收益来自哪里，情绪主线是否负责”。
- **Plan A 对应**：S3b(min)
- **ENH**：ENH-06
- `run`：
  - `eq analysis --start {start} --end {end} --ab-benchmark`
  - `eq analysis --date {trade_date} --deviation live-backtest`
- `test`：`tests/unit/analysis/test_ab_benchmark_contract.py tests/unit/analysis/test_live_backtest_deviation_contract.py`
- 门禁：
  - `signal_deviation/execution_deviation/cost_deviation` 三分解齐备。
  - `MSS vs 随机基准` 超额收益 >5%。
  - `MSS vs 技术基线（MA/RSI/MACD）` 超额收益 >3%。
  - 明确回答“去掉 MSS 后收益/风险变化”。
  - `dominant_component` 不得全窗口为 `'none'`（若 <=50% 为 none，WARN 但允许推进）。
  - `attribution_method` 小样本应自动 fallback 到 `mean_fallback_small_sample`。
  - 夏普 >1.0 / 最大回撤 <20% / 胜率 >50%。
  - **字段级设计对齐**：`gate_report.md` 必须包含 §Design-Alignment-Fields。
- 产物：`ab_benchmark_report.md`、`live_backtest_deviation_report.md`、`attribution_summary.json`
- 消费：螺旋1 收口评审。

---

## 8. 螺旋1门禁汇总

### 8.1 入口门禁

- 本地路径与 DuckDB 可读写（`Config.from_env()`）
- TuShare 采集可运行且重试机制可用

### 8.2 出口门禁（PB-1.4 完成后）

- [ ] PB-1.1~PB-1.4 各微圈 gate 均 PASS/WARN
- [ ] 覆盖率 >=99%
- [ ] 同窗 `eq run` + `eq backtest` + `eq analysis` 成功
- [ ] 最小归因：`signal/execution/cost`
- [ ] 对比归因：`MSS vs 随机` 与 `MSS vs 技术基线`
- [ ] 明确回答“去掉 MSS 后收益/风险变化”
- [ ] `PLAN-B-READINESS-SCOREBOARD.md` 更新并给 `GO/NO_GO`

---

## 9. 失败处理

1. 微圈 gate 未通过：仅允许在当前微圈范围修复，不得推进下一微圈。
2. 螺旋1 出口任一项未通过：判定 `NO_GO`，不得推进螺旋2。
3. 连续两轮 `NO_GO`：必须重估输入数据质量与算法契约。

---

## 10. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.0 | 2026-02-25 | 堵最大缺口：拆分为 PB-1.1~PB-1.4 微圈执行合同；设计绑定从目录级下沉到字段级；增加 gate_report 字段校验、归因量化阈值、微圈间消费链 |
| v2.1 | 2026-02-24 | 重写为设计绑定执行合同，删除伪代码式描述 |
| v2.0 | 2026-02-23 | 同精度增强版 |
