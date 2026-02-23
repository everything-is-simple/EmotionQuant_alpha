# EmotionQuant 实战螺旋路线手册（S0-S7a）

**状态**: Active  
**更新时间**: 2026-02-23  
**用途**: 给出可直接执行的多路线方案，避免“提案遗忘”。

---

## 0. Reborn 总则（2026-02-23 新增）

1. 路线 A/B/C 只是工程编排方式，不改变三大螺旋出口门禁。
2. 螺旋1未通过（Canary），不得宣称“策略有效”。
3. 螺旋2未通过（Full），S5 开发可继续，但不得宣称“可实战/生产就绪”。
4. 每圈必须同步 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`，没有看板结论视为未闭环。
5. 本文与 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 冲突时，以 VORTEX 为准。

---

## 1. 适用原则

1. 所有路线必须遵守 `Governance/steering/系统铁律.md` 与 `Governance/steering/6A-WORKFLOW.md`。
2. 每圈必须有 `run/test/artifact/review/sync` 五件套。
3. 一旦启用 ENH-10/ENH-11，必须作为独立圈收口，不允许“顺手做了不留证据”。
4. S2 及后续圈默认启用契约门禁：`python -m scripts.quality.local_quality_check --contracts --governance`。
5. 阶段级门禁与产物定义统一引用：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`。
6. S2b 后必须先完成 S2c（核心算法深化），未通过不得进入 S3a/S3。

---

## 2. 三套可执行路线

### 路线 A（推荐，平衡实战）

> 目标：先完成信号可用，再补数据效率，再推进回测/交易/展示，最后补自动运维。

| 顺序 | Spiral | 主目标 | 预算 |
|---|---|---|---:|
| 1 | S0a/S0b/S0c | 入口+L1+L2 数据闭环 | 8d |
| 2 | S1a/S1b | MSS 评分与消费验证 | 5d |
| 3 | S2a/S2b/S2c/(S2r) | MSS+IRS+PAS+Validation 集成推荐 + 算法语义收口 | 9-12d |
| 4 | S3a | ENH-10 分批+断点续传+多线程 | 2.5d |
| 5 | S3 | 回测闭环（Qlib+本地口径） | 4d |
| 6 | S4 | 纸上交易闭环 | 4d |
| 7 | S3ar | 采集稳定性修复圈（双 TuShare 主备 + 锁恢复） | 1-2d |
| 8 | S3b | 收益归因验证（A/B/C + 实盘-回测偏差） | 2d |
| 9 | S3c | 行业语义校准（SW31 映射 + IRS 全覆盖门禁） | 2d |
| 10 | S3d | MSS 自适应校准（adaptive 阈值 + probe 真实收益） | 2d |
| 11 | S3e | Validation 生产校准（future_returns + 双窗口 WFA） | 2d |
| 12 | S4b | 极端防御专项（连续跌停/流动性枯竭） | 2d |
| 13 | S5 | GUI 与日报导出闭环 | 3d |
| 14 | S6 | 稳定化与一致性重跑 | 3d |
| 15 | S7a | ENH-11 自动调度与开机自启 | 1.5d |

适用场景：你要尽快进入“可跑、可测、可复盘、可日更”的实战节奏。

### 路线 B（稳健，风险优先）

> 目标：先把质量门和交易一致性打牢，再上自动化能力。

| 顺序 | Spiral | 主目标 | 预算 |
|---|---|---|---:|
| 1 | S0a/S0b/S0c | 数据基础闭环 | 8d |
| 2 | S1a/S1b | MSS 闭环 | 5d |
| 3 | S2a/S2b/S2c/S2r | 信号集成+算法收口+故障修复演练 | 9-12d |
| 4 | S3a | ENH-10 数据效率增强 | 2.5d |
| 5 | S3 | 回测闭环 | 4d |
| 6 | S4 | 纸上交易闭环 | 4d |
| 7 | S3ar | 采集稳定性修复圈（双 TuShare 主备 + 锁恢复） | 1-2d |
| 8 | S3b | 收益归因验证（A/B/C + 实盘-回测偏差） | 2d |
| 9 | S3c | 行业语义校准（SW31 映射 + IRS 全覆盖门禁） | 2d |
| 10 | S3d | MSS 自适应校准（adaptive 阈值 + probe 真实收益） | 2d |
| 11 | S3e | Validation 生产校准（future_returns + 双窗口 WFA） | 2d |
| 12 | S4b | 极端防御专项（连续跌停/流动性枯竭） | 2d |
| 13 | S6 | 稳定化提前执行（先稳后展） | 3d |
| 14 | S5 | 展示闭环 | 3d |
| 15 | S7a | ENH-11 自动调度 | 1.5d |

适用场景：你更看重“误触发风险最小化”，接受稍慢上线。

### 路线 C（激进，速度优先）

> 目标：最快拿到可运转主链，接受后续返工概率上升。

| 顺序 | Spiral | 主目标 | 预算 |
|---|---|---|---:|
| 1 | S0a+S0b | 入口+L1 同圈完成 | 5d |
| 2 | S0c+S1a | L2+MSS 同圈完成 | 4d |
| 3 | S1b+S2a | MSS 消费验证 + IRS/PAS/Validation | 5d |
| 4 | S2b+S2c/(S2r) | 集成推荐收口 + 算法桥接收口 | 4-5d |
| 5 | S3a | ENH-10 | 2.5d |
| 6 | S3+S4 | 回测与纸上交易并行推进 | 6d |
| 7 | S3ar | 采集稳定性修复圈（双 TuShare 主备 + 锁恢复） | 1-2d |
| 8 | S3b | 归因验证 | 2d |
| 9 | S3c+S3d | 行业语义 + MSS 自适应并圈校准 | 3-4d |
| 10 | S3e | Validation 生产校准 | 2d |
| 11 | S4b+S5 | 极端防御与展示并圈推进 | 4-5d |
| 12 | S6+S7a | 稳定化与自动调度 | 4d |

适用场景：你明确要快速迭代并愿意承担并圈复杂度。

---

## 3. 每圈统一门禁（实战必过）

1. `run`：命令可重复执行且参数可追溯。
2. `test`：至少 1 条自动化测试；涉及数据契约/交易路径必须加契约测试。
3. `artifact`：至少 1 个结构化产物 + 1 份结论报告。
4. `review`：偏差、风险、降级方案写入 `review.md`。
5. `sync`：完成 5 文件最小同步。
6. `A股规则`：涉及推荐/交易必须检查 T+1、涨跌停、交易时段、申万行业映射。
7. `contracts`：S2/S3/S4/S5 必须保证 `contract_version=nc-v1` 兼容口径与 RR 执行门槛一致（`risk_reward_ratio >= 1.0`）。
8. `anti-drift`：每圈收口前必须通过 `python -m scripts.quality.local_quality_check --contracts --governance` 与 `tests/unit/scripts/test_contract_behavior_regression.py`，防止实现篡改设计语义。
9. `bridge-hard-gate`：S2 出口与 S3 入口必须通过 `selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id` 桥接校验，缺失即阻断推进。
10. `sw31-gate`：S3c 收口必须满足 `industry_snapshot` 当日 31 行业覆盖（禁止 `industry_code=ALL` 单条聚合替代）。
11. `mss-adaptive-gate`：S3d 收口必须满足 `threshold_mode=adaptive`（含冷启动回退）与 probe 真实收益口径。
12. `validation-oos-gate`：S3e 收口必须满足 `factor_series × future_returns` 对齐、双窗口 WFA 投票与 OOS/冲击成本/可成交性指标齐备。

---

## 4. ENH-10 / ENH-11 / 专项圈 固化执行合同

### S3a（ENH-10）必交付

- 命令：
  - `eq fetch-batch --start {start} --end {end} --batch-size 365 --workers 3`
  - `eq fetch-status`
  - `eq fetch-retry`
- 门禁：
  - 支持断点续传（中断后可继续）。
  - 多线程吞吐显著优于单线程（报告给出实测值）。
  - 失败批次有重试记录。
- 产物：
  - `fetch_progress.json`
  - `throughput_benchmark.md`
  - `fetch_retry_report.md`

### S7a（ENH-11）必交付

- 命令：
  - `eq scheduler install`
  - `eq scheduler status`
  - `eq scheduler run-once`
- 门禁：
  - 16:00 调度触发可验证。
  - 非交易日自动跳过。
  - 当日重复下载被去重阻断。
- 产物：
  - `scheduler_status.json`
  - `scheduler_run_history.md`
  - `scheduler_bootstrap_checklist.md`

### S3b（收益归因验证）必交付

- 命令：
  - `eq analysis --start {start} --end {end} --ab-benchmark`
  - `eq analysis --date {trade_date} --deviation live-backtest`
- 门禁：
  - 必须有 A/B/C 对照结果（情绪主线/基线/对照）。
  - 必须有 `signal_deviation/execution_deviation/cost_deviation` 三分解。
  - 必须形成“收益来源结论”：信号主导或执行主导。
- 产物：
  - `ab_benchmark_report.md`
  - `live_backtest_deviation_report.md`
  - `attribution_summary.json`

### S3c（行业语义校准）必交付

- 命令：
  - `eq run --date {trade_date} --stage l2 --strict-sw31`
  - `eq irs --date {trade_date} --require-sw31`
- 门禁：
  - `industry_snapshot` 当日必须为 31 条申万一级行业记录。
  - `allocation_advice` 必须覆盖 31 行业（无空档）。
  - 禁止 `industry_code=ALL` 作为主流程行业输入。
- 产物：
  - `industry_snapshot_sw31_sample.parquet`
  - `irs_allocation_coverage_report.md`
  - `sw_mapping_audit.md`

### S3d（MSS 自适应校准）必交付

- 命令：
  - `eq mss --date {trade_date} --threshold-mode adaptive`
  - `eq mss-probe --start {start} --end {end} --return-series-source future_returns`
- 门禁：
  - 周期阈值必须支持 `T30/T45/T60/T75` 分位阈值，且历史样本不足时回退固定阈值。
  - 趋势判定必须采用 `EMA + slope + trend_band` 抗抖口径。
  - Probe 的 `top_bottom_spread_5d` 必须基于真实收益序列（非温度差代理）。
- 产物：
  - `mss_regime_thresholds_snapshot.json`
  - `mss_probe_return_series_report.md`
  - `mss_adaptive_regression.md`

### S3e（Validation 生产校准）必交付

- 命令：
  - `eq validation --trade-date {trade_date} --threshold-mode regime --wfa dual-window`
  - `eq validation --trade-date {trade_date} --export-run-manifest`
- 门禁：
  - 因子验证必须满足 `factor_series` 与 `future_returns` 按 `trade_date, stock_code` 对齐。
  - 权重验证必须包含双窗口投票与 `oos_return/max_drawdown/sharpe/turnover/impact_cost_bps/tradability_pass_ratio`。
  - `selected_weight_plan` 必须来自可审计投票结果，不得使用启发式硬替代。
- 产物：
  - `validation_factor_report_sample.parquet`
  - `validation_weight_report_sample.parquet`
  - `validation_run_manifest_sample.json`
  - `validation_oos_calibration_report.md`

### S4b（极端防御专项）必交付

- 命令：
  - `eq stress --scenario limit_down_chain --date {trade_date}`
  - `eq stress --scenario liquidity_dryup --date {trade_date}`
- 门禁：
  - 必须验证组合级应急降杠杆触发链可执行。
  - 必须验证连续不可成交场景下的次日重试与仓位封顶逻辑。
  - 必须输出防御参数来源（来自 S3b 归因 + S3e Validation 生产校准，而非人工拍值）。
- 产物：
  - `extreme_defense_report.md`
  - `deleveraging_policy_snapshot.json`
  - `stress_trade_replay.csv`

---

## 5. 防遗忘机制（强制）

1. 任何启用的路线圈，必须在 `Governance/record/development-status.md` 写状态（planned/in_progress/blocked/completed）。
2. ENH-10/11 未完成时，不得在状态记录中标记“自动化数据链路完成”。
3. 若连续 2 圈未推进 ENH-10/11，必须在 `Governance/record/debts.md` 新增债务条目与延期原因。

---

## 6. 默认执行建议

- 默认采用 **路线 A（推荐）**。
- 只有在你明确要求“风险优先”或“速度优先”时，才切换到路线 B/C。
- 路线切换时必须在 `Governance/specs/spiral-s{N}/final.md` 记录切换原因与影响范围。

---

## 7. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.7 | 2026-02-23 | 新增 Reborn 总则：路线选择不改变三大螺旋出口门禁，加入业务看板强制同步与“螺旋2未过不得宣称生产就绪”约束 |
| v1.6 | 2026-02-20 | 三路线新增核心实现深度圈 `S3c/S3d/S3e`，并将 `S4b` 前置依赖升级为“归因 + 算法生产校准双来源”；统一新增 `sw31/mss-adaptive/validation-oos` 三道门禁 |
| v1.5 | 2026-02-19 | 修订三路线时序：统一插入 S3ar（双 TuShare 主备 + 锁恢复）作为 S3b 前置门禁，避免 `S4->S3b` 口径漂移 |
| v1.4 | 2026-02-16 | 三路线统一插入 S2c（S2b->S3a）；新增 `validation_weight_plan` 桥接硬门禁；路线B时序对齐阶段B合同（S3a 在 S3 前） |
| v1.3 | 2026-02-15 | 适用原则新增阶段模板联动规则，要求路线执行同步遵守阶段A/B/C门禁与产物定义 |
| v1.2 | 2026-02-15 | 三套路线全部纳入 S3b（收益归因）与 S4b（极端防御）；统一门禁新增 anti-drift 强制检查；执行合同扩展到 ENH+专项圈 |
| v1.1 | 2026-02-14 | 每圈原则与统一门禁补充契约检查（`--contracts --governance`）；新增执行口径约束（`contract_version=nc-v1`、`risk_reward_ratio >= 1.0`） |
| v1.0 | 2026-02-13 | 首次发布：给出三套完整实战路线，固化 ENH-10/11，加入防遗忘机制 |
