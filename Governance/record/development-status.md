# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-22  
**当前版本**: v4.29（S3b Option2 扩窗 20 日完成：Backtest WARN/GO + Analysis PASS/GO）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S3/S3b/S3c/S3d/S3e 执行中，S4 与 S3ar 已收口完成：S3b 已完成 20 日扩窗证据，当前聚焦清零剩余 2 个 S3e 因子门失败日**

- S0a（统一入口与配置注入）: 已完成并补齐 6A 证据链。
- S0b（L1 采集入库闭环）: 已完成并补齐 6A 证据链。
- S0c（L2 快照与失败链路）: 已完成并补齐 6A 证据链。
- S1a（MSS 最小评分可跑）: 已完成并补齐 6A 证据链。
- S1b（MSS 消费验证闭环）: 已完成并补齐 6A 证据链。
- S2a（IRS + PAS + Validation 最小闭环）: 已完成并补齐 6A 证据链。
- S2b（MSS+IRS+PAS 集成推荐闭环）: 已完成并补齐 6A 证据链。
- S2c（核心算法深化闭环）: 已完成并收口（含证据冲突清障、release/debug 分流、closeout 文档补齐与同步）。
- S2r（质量门失败修复子圈）: 规格与修复产物合同已归档，可在 FAIL 场景下直接触发。

---

## 本次同步（2026-02-22，S3b Option2 扩窗 20 日）

1. 按 `Option2` 完成缺失链路补齐：
   - 对缺失日串行执行 `run --to-l2 --strict-sw31 -> mss -> irs --require-sw31 -> pas`，补齐 15 天。
   - 产物：`artifacts/spiral-s3b/20260213/option2_refill_20d_results.json`（15/15 成功）。
2. 完成 20 日信号补齐与残留识别：
   - 通过 `recommend --mode integrated --with-validation-bridge` 快速补齐后，剩余失败日收敛为 2 天（`20260126`、`20260202`，`factor_validation_fail`）。
   - 产物：`artifacts/spiral-s3b/20260213/option2_signal_fill_20d_results.json`。
3. 完成 20 日回测与分析收口证据：
   - `eq backtest --engine local_vectorized --start 20260119 --end 20260213` => `quality_status=WARN`, `go_nogo=GO`, `total_trades=36`, `consumed_signal_rows=288`。
   - `eq analysis --start 20260119 --end 20260213 --ab-benchmark` => `quality_status=PASS`, `go_nogo=GO`，结论 `A_not_dominant`。
4. 固化本轮汇总：
   - `artifacts/spiral-s3b/20260213/option2_closure_summary.json`。
5. 回归验证：
   - `pytest` 定向回归通过（4 passed）：S3e 软门契约、CLI `pas` 路由、validation 参数透传、S3e 默认模式透传。

---

## 本次同步（2026-02-21，S3 固定窗口阻断解锁）

1. 回测语义修订：
   - `src/backtest/pipeline.py` 将“无可开仓信号窗口”从 `P0` 阻断改为 `WARN/GO`，输出 `no_long_entry_signal_in_window` 警告并保留审计字段。
   - 回测仅消费多头开仓信号（`recommendation in {BUY, STRONG_BUY}` 且 `position_size > 0`），避免 `SELL/HOLD` 被误当作买入候选。
2. 分析语义修订：
   - `src/analysis/pipeline.py` 对“live/backtest 同时无成交样本”输出 N/A 警告（`WARN/GO`），不再硬失败。
   - 归因无样本时输出 `attribution_method=na_no_filled_trade`，保证产物合同完整。
3. 集成持久化兼容修订：
   - `src/integration/pipeline.py` 增强 `integrated_recommendation` 旧表类型修复，自动将 `position_size` 等关键数值列迁移为 `DOUBLE`，避免整型截断。
4. 固定窗口复跑结论（`20260210-20260213`）：
   - `eq backtest` => `quality_status=WARN`, `go_nogo=GO`, `total_trades=0`，`gate_report` 含 `no_long_entry_signal_in_window`。
   - `eq analysis --ab-benchmark --deviation --attribution-summary` => `quality_status=WARN`, `go_nogo=GO`，无 P0/P1 错误，仅 N/A 警告。
5. 回归验证：
   - `pytest tests/unit/backtest -q` 通过（13 passed）
   - `pytest tests/unit/analysis -q` 通过（6 passed）
   - `pytest tests/unit/integration/test_integration_contract.py -q` 通过（4 passed）
   - `python -m scripts.quality.local_quality_check --contracts --governance` 通过

---

## 本次同步（2026-02-21，S3c 启动与契约补齐）

1. 启动 S3c 实跑窗口 `20260219`：
   - `eq run --date 20260219 --to-l2 --strict-sw31` 通过（`industry_snapshot_count=31`）。
   - `eq irs --date 20260219 --require-sw31` 通过（`irs_industry_count=31`，`gate_status=PASS`）。
2. 补齐 S3c 产物契约：
   - `src/pipeline/main.py` 在 `s3c_irs` 路径新增 `gate_report.md` 与 `consumption.md` 输出。
   - CLI payload 新增 `gate_report_path/consumption_path/gate_status/go_nogo`。
3. 提升 `run --to-l2` 稳定性：
   - `src/data/l2_pipeline.py` 将 `init_quality_context` 异常改为受控回退，避免初始化阶段直接抛栈中断。
4. 目标测试通过：
   - `tests/unit/data/test_industry_snapshot_sw31_contract.py`
   - `tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py`
   - `tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline`
5. 治理门禁通过：
   - `python -m scripts.quality.local_quality_check --contracts --governance`。

---

## 本次同步（2026-02-21，S3/S3e 核心阻断修复）

1. 修复历史库 schema 兼容阻断：
   - `src/backtest/pipeline.py`：`_persist` 支持旧表自动补列并按交集列写入，避免 `backtest_results` 列数不匹配崩溃。
   - `src/trading/pipeline.py`：兼容旧 `backtest_results` 与 `trade_records` 缺列场景，避免 `quality_status/trade_id` 缺失触发 Binder 异常。
2. 修复 Validation 核心算法口径：
   - `src/algorithms/validation/pipeline.py` 将 `decay_5d` 代理改为随 `|IC|` 单调上升，消除“强信号反向 FAIL”。
   - 新增测试 `tests/unit/algorithms/validation/test_decay_proxy_contract.py`，并通过 `pytest tests/unit/algorithms/validation -q`（9 passed）。
3. S3b 实跑证据更新：
   - 固定窗口 `20260210-20260213`：`S3 backtest` 不再崩溃，但仍因 `backtest_trade_records_empty` 阻断。
   - 可交易窗口 `20260218-20260219`：`eq analysis` 三项产物齐备，`quality_status=WARN`、`go_nogo=GO`（见 `artifacts/spiral-s3b/20260219/*`）。

---

## 本次同步（2026-02-21，S3b 入口兼容收口）

1. 修复 `eq` 入口包发现配置：`pyproject.toml` 从 `where=["src"]` 调整为 `where=["."] + include=["src*"]`，确保安装后可定位 `src` 顶层包。
2. 新增打包契约测试：`tests/unit/config/test_dependency_manifest.py` 增补 `eq` 入口与 `setuptools` 包发现断言，防止回归到 `ModuleNotFoundError: src`。
3. 实测验证通过：从非仓库目录执行 `G:\EmotionQuant-alpha\.venv\Scripts\eq.cmd --help` 成功。
4. 债务口径同步：清偿 `TD-S3B-016`，S3b 执行卡命令“可直接复跑”一致性风险解除。

---

## 本次同步（2026-02-21，S3d/S3e 阻断修复）

1. 落地 MSS CLI 参数契约：`eq mss --threshold-mode` 与 `eq mss-probe --return-series-source` 可执行。
2. 落地 Validation 独立入口：`eq validation --trade-date --threshold-mode --wfa --export-run-manifest` 可执行。
3. 落地对应合同测试：S3d 两条 + S3e 三条，并通过回归。
4. 执行卡状态同步：`S3D-EXECUTION-CARD.md`、`S3E-EXECUTION-CARD.md` 切换为 `Active`。
5. 债务口径同步：清偿 TD-S3-017（CLI 阻断）、TD-S1-007（MSS 固定阈值债务）、TD-S1-008（温度差代理收益债务）。

---

## 本次同步（2026-02-21，S3 审计对齐）

1. 代码层补齐 S3r 修复入口：`eq backtest --repair s3r` 已接入 CLI 与回测流水线，并可产出 `s3r_patch_note/s3r_delta_report`。
2. 修订 S3 路线/执行卡命令漂移：S3c 口径统一为 `eq run --to-l2 --strict-sw31`（移除无效 `--stage l2`）。
3. 同步状态口径：`S3A-EXECUTION-CARD.md` 与 `S3AR-EXECUTION-CARD.md` 切换为 `Completed`，与 specs/主控状态一致。
4. 补齐阶段B计划圈 specs 骨架：新增 `spiral-s3r/s3c/s3d/s3e` 的 `requirements/review/final`，消除执行卡引用路径缺失。
5. 当时未完成项记录：S3d（adaptive/probe CLI）与 S3e（`eq validation` 入口）曾为计划圈阻断项（该项已在 v4.24 清偿）。

---

## 本次同步（2026-02-21，S0-S2r 规格/记录一致性复核）

1. 补齐 `Governance/specs/spiral-s2r/` 规格档案（`requirements/review/final`），消除“执行卡存在但 specs 缺位”。
2. 修订 `spiral-s2b` 规格口径，从“最小实现”升级为“完全版语义”：四模式集成 + 推荐数量硬约束。
3. 修订 `spiral-s2c` 规格口径，补记 MSS `mss_rank/mss_percentile` 契约落库与 Integration 完整语义复核结论。
4. 复核结果：`S0-S2r` 路线图、执行卡、specs、record 四层文档与现有代码实现一致。
5. 治理门禁复核通过：`python -m scripts.quality.local_quality_check --contracts --governance`。

---

## 本次同步（2026-02-21，S0c-R1 门禁收口）

1. 收口 S0c 严格门禁与测试契约：修复 `duckdb_not_found` 语义回归，并保持 `data_readiness_gate` 持久化。
2. SW31 严格门禁可复跑通过：`run --to-l2 --strict-sw31` 产出 `industry_snapshot_count=31`。
3. 新增并通过两条合同测试：`test_data_readiness_persistence_contract.py`、`test_flat_threshold_config_contract.py`。
4. S0c 目标测试回归通过：`pytest -q ...`（18 passed）。
5. 治理门禁通过：`python -m scripts.quality.local_quality_check --contracts --governance`。
6. 全量单测回归通过：`python -m pytest -q`（126 passed）。

---

## 本次同步（2026-02-20，S3ar Slice-1~3）

1. Slice-1：新增 `tests/unit/data/conftest.py`，隔离 `TUSHARE_*` 与路径类宿主环境变量，恢复 data unit 稳定性。
2. Slice-2：在 `src/data/repositories/base.py` 落地 DuckDB 锁恢复（重试等待 + PID 提取 + 耗尽异常）；`src/data/l1_pipeline.py` 新增 `lock_holder_pid/retry_attempts/wait_seconds_total` 审计字段输出。
3. Slice-3：在 L1 落地 `trade_date` 维度覆盖写入（先删后插），补齐幂等写入合同测试 `tests/unit/data/test_duckdb_lock_recovery_contract.py`。
4. 关键门禁通过：
   - `pytest -q tests/unit/data/test_duckdb_lock_recovery_contract.py`
   - `pytest -q tests/unit/data/test_fetch_retry_contract.py tests/unit/data/test_fetcher_contract.py tests/unit/config/test_config_defaults.py`
   - `python -m scripts.quality.local_quality_check --contracts --governance`
5. S3ar 状态由 `in_progress` 切换为 `completed`：实网窗口 run/artifact 证据已补齐并完成 A6 同步。

## 本次同步（2026-02-20，S3ar 收口）

1. 完成实网 run 证据补齐：主/兜底 token check 与双通道限速压测产物归档至 `artifacts/token-checks/`。
2. 完成实网采集窗口证据补齐：`artifacts/spiral-s3a/20260213/fetch_progress.json`、`fetch_retry_report.md`、`throughput_benchmark.md`。
3. 更新并收口 `Governance/specs/spiral-s3ar/review.md` 与 `Governance/specs/spiral-s3ar/final.md`，状态切换为 `completed`。
4. 完成最小同步 5 项：`final/development-status/debts/reusable-assets/SPIRAL-CP-OVERVIEW`。
5. 下一圈切换到 S3b：固定窗口 `20260210-20260213` 执行 `ab-benchmark`、`deviation`、`attribution-summary` 三条分析链路。

---

## 已完成（2026-02-15）

1. 完成 S2b 开发与验证：`eq recommend --date {trade_date} --mode integrated`，输出 `integrated_recommendation` 与 `quality_gate_report`。
2. 新增 S2b 合同测试：`test_integration_contract.py`、`test_quality_gate_contract.py`；并补 CLI `integrated` 路径回归。
3. 归档 S2b 样例证据到 `Governance/specs/spiral-s2b`。
4. 重跑关键门禁并通过：env baseline、S2b 目标测试、contracts/governance、防跑偏回归测试。

## 本次同步（2026-02-17，S3a 收口）

1. S3a 接入真实 TuShare 客户端：`src/data/fetcher.py` 新增 real client 适配，支持 token 驱动真实链路。
2. S3a 吞吐报告从公式估算升级为实测统计：`src/data/fetch_batch_pipeline.py` 输出 `measured_wall_seconds`、`effective_batches_per_sec` 与逐批细节。
3. S3a 失败恢复从“状态直接改写”升级为“失败批次真实重跑”：`run_fetch_retry` 现执行重拉并回写恢复结果。
4. 兼容真实非交易日语义：`src/data/l1_pipeline.py` 新增 `trade_cal_is_open` 判定，闭市日不再误报 `raw_daily_empty`。
5. 全量回归通过：`python -m pytest -q`（96 passed）；治理门禁通过：`python -m scripts.quality.local_quality_check --contracts --governance`。

## 本次同步（2026-02-18，S3 核心算法全量消费门禁）

1. S3 回测新增核心算法全量消费硬门禁：`src/backtest/pipeline.py` 对 `mss_score/irs_score/pas_score` 完整性执行阻断校验。
2. S3 回测新增窗口覆盖校验：窗口内 `mss_panorama/irs_industry_daily/stock_pas_daily` 任一为 0 时阻断收口。
3. S3 证据链增强：`consumption.md` 与 `gate_report.md` 新增 DuckDB 路径与核心表覆盖统计，支持审计复核。
4. 新增 S3 回归测试：`tests/unit/backtest/test_backtest_core_algorithm_coverage_gate.py`，覆盖“字段空值阻断/核心表缺失阻断/正常覆盖通过”。
5. 同步执行卡与路线合同：`S3-EXECUTION-CARD.md`、`SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md` 已纳入新门禁与测试清单。

## 本次同步（2026-02-18，S4 收口）

1. 完成 S4 收口实跑：`eq --env-file artifacts/spiral-s4/20260222/closeout_env_v3/.env.s4.closeout trade --mode paper --date 20260222`，产出 `quality_status=WARN`、`go_nogo=GO`。
2. 完成交叉日持仓生命周期验证：在收口环境中复现“首日建仓 -> 次日跌停阻断（`REJECT_LIMIT_DOWN`）-> 再下一日重试卖出（`SELL_RETRY_NEXT_DAY`）”完整链路。
3. S4 证据链补齐：`artifacts/spiral-s4/20260222/` 下新增 `run.log`、`test.log`、`manual_test_summary.md`，并同步标准产物 `trade_records/positions/risk_events/paper_trade_replay/consumption/gate_report`。
4. 治理门禁复核通过：`python -m scripts.quality.local_quality_check --contracts --governance`。
5. 完成 A6 最小同步：更新 `spiral-s4 final/review/requirements`、`development-status`、`debts`、`reusable-assets`、`SPIRAL-CP-OVERVIEW`。

## 本次同步（2026-02-19，S3b 最小执行入口）

1. S3b 最小执行入口已落地：`src/analysis/pipeline.py` + `eq analysis`（`src/pipeline/main.py`）。
2. 新增 S3b 三类产物输出：`ab_benchmark_report.md`、`live_backtest_deviation_report.md`、`attribution_summary.json`，并统一生成 `consumption.md/gate_report.md/error_manifest`。
3. 新增 S3b 合同测试：`tests/unit/analysis/test_ab_benchmark_contract.py`、`tests/unit/analysis/test_live_backtest_deviation_contract.py`、`tests/unit/analysis/test_attribution_summary_contract.py`。
4. 新增 CLI 绑定测试：`tests/unit/pipeline/test_cli_entrypoint.py::test_main_analysis_command_wires_to_pipeline`。
5. 治理门禁复核通过：`python -m scripts.quality.local_quality_check --contracts --governance`。

## 本次同步（2026-02-17，S3 板块化涨跌停阈值）

1. S3 回测执行层落地板块化涨跌停阈值判定：主板 10% / 创业板与科创板 20% / ST 5%（`src/backtest/pipeline.py`）。
2. 涨跌停识别从“开盘=最高/最低”的最小近似，升级为“前收盘 + 板块阈值”判定，并保留缺失前收时的兼容降级。
3. 新增并通过板块阈值回归测试：`tests/unit/backtest/test_backtest_board_limit_thresholds.py`。
4. 同步改造并通过现有 S3 回归：`tests/unit/backtest/test_backtest_t1_limit_rules.py`（按主板 +10% 口径造数）。
5. S3 关键 backtest 冒烟回归通过（7 passed）：contract / bridge / reproducibility / T+1&limit / board-limit-thresholds。

## 上次同步（2026-02-17，S3 扩展 + S4 启动）

1. S3 回测从单日最小口径扩展到多交易日完整回放：`src/backtest/pipeline.py` 按交易日历执行 `signal_date -> execute_date(T+1)`。
2. S3 新增执行细节：补齐涨停买入拒绝、跌停卖出阻断、持仓 T+1 可卖日约束、成交费用与权益曲线跟踪。
3. 新增并通过 S3 扩展测试：`tests/unit/backtest/test_backtest_t1_limit_rules.py`，验证多日窗口与 T+1/涨跌停行为。
4. 启动 S4 paper trade：新增 `eq trade --mode paper --date {trade_date}`（`src/pipeline/main.py` + `src/trading/pipeline.py`）。
5. S4 复用 S3 consumption/gate 证据链：强制消费 `backtest_results` + `quality_gate_report`，输出 `consumption.md` 与 `gate_report.md`。
6. 新增并通过 S4 目标测试：`tests/unit/trading/test_order_pipeline_contract.py`、`tests/unit/trading/test_position_lifecycle_contract.py`、`tests/unit/trading/test_risk_guard_contract.py`，并通过 CLI 回归 `test_main_trade_runs_paper_mode`。
7. `contracts/governance` 门禁通过：`python -m scripts.quality.local_quality_check --contracts --governance`。

## 上次同步（2026-02-17，S3a 启动）

1. 启动 S3a（ENH-10）A3：新增 `eq fetch-batch`、`eq fetch-status`、`eq fetch-retry` 三个命令入口（`src/pipeline/main.py`）。
2. 新增 S3a 采集增强最小实现：`src/data/fetch_batch_pipeline.py`，支持分批、断点续传、失败重试及产物固化。
3. 新增并通过 S3a 合同测试：`test_fetch_batch_contract.py`、`test_fetch_resume_contract.py`、`test_fetch_retry_contract.py`；并通过 CLI 回归 `test_main_fetch_batch_status_and_retry`。
4. `contracts/governance` 本地门禁通过：`python -m scripts.quality.local_quality_check --contracts --governance`。
5. 更新 `Governance/specs/spiral-s3a/*` 状态为 `in_progress`，启动持续复盘。

## 上次同步（2026-02-17，S2c 收口）

1. 完成 IRS full 语义实现：`src/algorithms/irs/pipeline.py` 已补齐六因子、`rotation_status/rotation_slope/rotation_detail`、`allocation_advice`、`quality_flag/sample_days/neutrality`，并输出 `irs_factor_intermediate_sample.parquet`。
2. 完成 PAS full 语义实现：`src/algorithms/pas/pipeline.py` 已补齐三因子、`effective_risk_reward_ratio`、`direction/opportunity_grade`、`quality_flag/sample_days/adaptive_window`，并输出 `pas_factor_intermediate_sample.parquet`。
3. 完成 Validation full 语义实现：`src/algorithms/validation/pipeline.py` 已补齐因子验证、权重 Walk-Forward、Gate 决策与五件套产物链路。
4. 新增并通过 S2c 目标测试：`test_irs_full_semantics_contract.py`、`test_pas_full_semantics_contract.py`、`test_factor_validation_metrics_contract.py`、`test_weight_validation_walk_forward_contract.py`，并联同桥接回归共 `10 passed`。
5. `contracts/governance` 本地门禁通过：`python -m scripts.quality.local_quality_check --contracts --governance`。
6. 扩展设计溯源检查：`scripts/quality/design_traceability_check.py` 纳入 IRS/PAS 模块。
7. 完成 S2c 收口清障：新增 `evidence_lane`（release/debug）并将 S2c 正式证据统一到 release 车道。
8. 新增同步脚本 `scripts/quality/sync_s2c_release_artifacts.py`，同步前校验 PASS/GO 与样例行数。
9. 补齐并归档 S2c 收口文档：`s2c_semantics_traceability_matrix.md`、`s2c_algorithm_closeout.md`。

---

## Spiral 进度看板

| Spiral | 目标 | 状态 | 备注 |
|---|---|---|---|
| S0a | 统一入口与配置注入可用 | ✅ 已完成 | 6A 证据已归档 |
| S0b | L1 采集入库闭环 | ✅ 已完成 | 6A 证据已归档 |
| S0c | L2 快照与失败链路闭环 | ✅ 已完成 | 6A 证据已归档 |
| S1a | MSS 最小评分可跑 | ✅ 已完成 | 6A 证据已归档 |
| S1b | MSS 消费验证闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2a | IRS + PAS + Validation 最小闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2b | MSS+IRS+PAS 集成推荐闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2c | 核心算法深化闭环（权重桥接 + 语义收口） | ✅ 已完成 | release 证据统一、closeout 文档补齐、A6 同步完成 |
| S2r | 质量门失败修复子圈 | ✅ 已完成 | specs 档案与执行卡对齐，`--repair s2r` 可直接触发 |
| S3a | ENH-10 数据采集增强闭环 | ✅ 已完成 | 已接入真实 TuShare 客户端，实测吞吐与失败恢复证据齐备 |
| S3 | 回测闭环 | 🔄 进行中 | 已扩展多交易日回放并落地板块化涨跌停阈值 |
| S4 | 纸上交易闭环 | ✅ 已完成 | 完成跨日持仓回放与跌停次日重试证据闭环，`go_nogo=GO` |
| S3ar | 采集稳定性修复圈（双 TuShare 主备 + 锁恢复，AK/Bao 预留） | ✅ 已完成 | run/test/artifact/review/sync 五件套闭合，允许推进 S3b |
| S3r | 回测修复子圈（条件触发） | 📋 未开始 | 修复命令已落地（`backtest --repair s3r`），待 FAIL 场景触发 |
| S3b | 收益归因验证专项圈 | 🔄 进行中 | 已完成 20 日扩窗证据（backtest WARN/GO + analysis PASS/GO），剩余 2 个 factor_validation_fail 日期待 S3e 清零 |
| S3c | 行业语义校准专项圈（SW31 映射 + IRS 全覆盖门禁） | 🔄 进行中 | `20260219` 窗口已通过 SW31/IRS 门禁并补齐 `gate/consumption` 产物，待与 S3b 固定窗口节奏对齐后收口 |
| S3d | MSS 自适应校准专项圈（adaptive 阈值 + probe 真实收益） | 🔄 进行中 | CLI 阻断已解除，进入窗口级证据收口 |
| S3e | Validation 生产校准专项圈（future_returns + 双窗口 WFA） | 🔄 进行中 | CLI 阻断已解除，进入窗口级证据收口 |
| S4b | 极端防御专项圈 | 📋 未开始 | 依赖 S3e 收口结论输入防御参数 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4b 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |
| S7a | ENH-11 自动调度闭环 | 📋 未开始 | 依赖 S6 完成 |

---

## 下一步（S3b/S3c -> S3d/S3e）

1. 在 `S3e` 优先清零剩余两天 `factor_validation_fail`（`20260126`、`20260202`），再回到 `S3b` 复跑 20 日闭环确认 `20/20` 覆盖。
2. 固化固定窗口 N/A 警告口径到 `spiral-s3b/review/final`（避免再次误判为阻断）。
3. 基于 `20260219` 已有 S3c 证据，补跑固定窗口并完成 `spiral-s3c final` 收口。
4. 在 S3c 语义校准收口后，对 S3d/S3e 执行窗口级实证并固化 `review/final`。
5. 仅当 S3d/S3e 完成窗口证据收口后，再进入 S4b（极端防御）。

---

## 风险提示

1. S0c 已升级为 SW31 严格门禁口径；后续风险转移为 S3c 的 IRS 全覆盖门禁与窗口回跑一致性。
2. 真实采集链路已接入，仍需持续观测长窗口吞吐与限频稳定性。
3. 若 `validation_weight_plan` 桥接链路缺失或不可审计，必须阻断 S2c->S3a/S3/S4 迁移。
4. 在 S3c/S3d/S3e 完成前，不得以“阶段B已推进”替代“核心算法 full 实现完成”结论。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-22 | v4.29 | 完成 S3b Option2 扩窗 20 日：补齐 15 天链路、回测 `WARN/GO`（36 trades）、分析 `PASS/GO`（A_not_dominant），并定位残留 2 天 `factor_validation_fail` 进入 S3e 清零 |
| 2026-02-21 | v4.28 | S3 固定窗口解锁：回测“无可开仓信号”改 WARN 语义；S3b 在双侧无成交样本场景输出 N/A 警告（WARN/GO）；补齐 integration 旧表数值列类型修复 |
| 2026-02-21 | v4.27 | S3c 启动：`20260219` 窗口通过 SW31/IRS 门禁；补齐 `s3c_irs` 的 `gate_report/consumption` 契约；`run --to-l2` 初始化异常改为受控回退 |
| 2026-02-21 | v4.26 | S3/S3e 核心阻断修复：回测/交易历史 schema 兼容落地；Validation `decay_5d` 口径改为单调正向并补测试；S3b 固定窗口仍因无成交记录阻断 |
| 2026-02-21 | v4.25 | S3b 入口兼容收口：修复 `pyproject` 包发现配置并补齐契约测试，仓库外目录执行 `eq --help` 成功，清偿 TD-S3B-016 |
| 2026-02-21 | v4.24 | S3d/S3e 阻断修复：落地 `eq validation` 与 MSS CLI 参数契约，补齐 5 条目标合同测试，执行卡切换为 Active |
| 2026-02-21 | v4.23 | S3 审计对齐：落地 `backtest --repair s3r`，修正 S3c 命令口径，补齐 `spiral-s3r/s3c/s3d/s3e` specs 骨架并同步执行卡状态 |
| 2026-02-21 | v4.22 | 补齐 `spiral-s2r` specs 档案并重审 `spiral-s2b/s2c` 规格口径，完成 S0-S2r 路线图/执行卡/specs/record 四层一致性复核 |
| 2026-02-21 | v4.21 | S0c-R1 收口：修复 strict 门禁语义与旧断言漂移，补齐 `data_readiness` 持久化/`flat_threshold` 契约测试，S0c 目标回归与治理门禁通过 |
| 2026-02-20 | v4.20 | 主控路线对齐：进度看板新增 `S3c/S3d/S3e`，并将 `S4b` 依赖从 `S3b` 修订为 `S3e`；下一步改为 `S3b->S3c->S3d->S3e` |
| 2026-02-20 | v4.19 | 修订主控一致性：进度看板显式补齐 S3b/S4b，且将 S5 前置依赖从 S4 修正为 S4b，消除阶段B/阶段C圈序漂移 |
| 2026-02-20 | v4.18 | S3ar 收口完成：补齐主/兜底 token check 与独立限速压测实网证据，更新 review/final 与最小同步 5 项，状态切换为 `completed`，下一圈进入 S3b |
| 2026-02-20 | v4.17 | S3ar Slice-1~3 完成：data unit 环境隔离、DuckDB 锁恢复审计字段落地、`trade_date` 幂等覆盖写入与合同测试补齐 |
| 2026-02-19 | v4.16 | S3b 最小执行入口落地：新增 `eq analysis`、`src/analysis/pipeline.py` 与 3 条 analysis 合同测试；阶段B由“仅文档可执行”升级为“命令/测试可执行” |
| 2026-02-19 | v4.15 | S3ar 口径修订为“双 TuShare 主备 + 独立限速 + 锁恢复”，并将 AKShare/BaoStock 调整为最后底牌预留（当前圈不实装） |
| 2026-02-19 | v4.14 | 调整下一圈顺序为 `S3ar -> S3b`：新增采集稳定性修复圈（多源兜底 + DuckDB 锁恢复）作为归因前置门禁 |
| 2026-02-18 | v4.13 | S4 收口完成：以 `artifacts/spiral-s4/20260222` 形成 run/test/artifact 证据链，验证跨日持仓与跌停次日重试，`quality_status=WARN` 且 `go_nogo=GO`，下一圈切换 S3b |
| 2026-02-18 | v4.12 | S3 新增核心算法全量消费门禁：`mss/irs/pas` 三因子完整性与核心表窗口覆盖硬校验；新增 `test_backtest_core_algorithm_coverage_gate.py`；同步执行卡与路线合同 |
| 2026-02-17 | v4.11 | S3a 收口：接入真实 TuShare 客户端、落地实测吞吐报告、失败批次真实重跑恢复；全量测试 96 passed + contracts/governance PASS |
| 2026-02-17 | v4.10 | S3 落地板块化涨跌停阈值（10%/20%/5%），新增并通过 `test_backtest_board_limit_thresholds.py`，并完成 S3 backtest 关键回归 7 passed |
| 2026-02-17 | v4.9 | S3 扩展到多交易日回放并补齐 T+1/涨跌停执行细节；启动 S4 `eq trade --mode paper`，接入 S3 consumption/gate 证据链与交易合同测试 |
| 2026-02-17 | v4.8 | S3 消费侧对接落地：新增 `eq backtest` 与 `src/backtest/pipeline.py`，接入 S3a `fetch_progress` 门禁与桥接校验，新增 3 条 backtest 测试与 1 条 CLI 回归 |
| 2026-02-17 | v4.7 | S3a 启动执行：落地 `fetch-batch/fetch-status/fetch-retry` 命令与采集增强最小实现，新增 3 条 S3a 合同测试与 1 条 CLI 回归并通过 |
| 2026-02-17 | v4.6 | S2c 收口完成：清理 PASS/FAIL 证据冲突，新增 `evidence_lane` 双车道与 release 同步脚本，补齐 closeout 文档并完成 A6 同步 |
| 2026-02-17 | v4.5 | S2c 继续推进：完成 IRS/PAS/Validation full 语义实现与合同测试（10 passed），并通过 contracts/governance 门禁 |
| 2026-02-17 | v4.4 | S2c 继续推进：新增 MSS full 语义起步测试与中间产物；接入 `DESIGN_TRACE` + traceability 自动检查，降低“实现-设计”漂移风险 |
| 2026-02-17 | v4.3 | S2c 进入执行中：完成 `validation_weight_plan` 桥接硬门禁与目标回归（6 passed）+ S2a/S2b 回归（4 passed）；新增 `Governance/specs/spiral-s2c/*` 阶段证据 |
| 2026-02-16 | v4.2 | 明确 S2c 下一步为三段 P0 顺序；补齐 Integration 为核心算法 full 语义必选模块，并将门禁测试表述升级为 Integration + Validation 联合合同测试 |
| 2026-02-16 | v4.1 | 新增 S2c 算法深化圈并切换当前状态为 S2c 准备；落地 `validation_weight_plan` 桥接硬门禁与核心算法独立 DoD 口径 |
| 2026-02-16 | v4.0 | 同步阶段C执行合同（S5-S7a）入口与状态口径，补齐路线索引 |
| 2026-02-16 | v3.9 | 新建 S3a 执行卡与 `spiral-s3a` 证据骨架，状态从 S3 准备切换为 S3a 准备 |
| 2026-02-15 | v3.8 | 完成 S2b 开发与 6A 收口，状态推进到 S3 准备 |
| 2026-02-15 | v3.7 | 完成 S2a 开发与 6A 收口，状态推进到 S2b 待执行 |
| 2026-02-15 | v3.6 | 完成 S1b 开发与 6A 收口，状态推进到 S2a 待执行 |
| 2026-02-15 | v3.5 | 完成 S1a 开发与 6A 收口，状态推进到 S1b 待执行 |
| 2026-02-15 | v3.4 | 完成 S0c 开发与 6A 收口，状态推进到 S1a 待执行 |
| 2026-02-15 | v3.3 | 回补 S0a/S0b 的 6A 收口证据，并把状态推进到 S0c 待执行 |
| 2026-02-14 | v3.2 | 同步闭环修订：补齐 `contract_version=nc-v1` / `risk_reward_ratio>=1.0` 执行边界与 contracts/governance 门禁口径 |
| 2026-02-07 | v3.1 | 统一 CP 术语与最小同步契约；重写 ROADMAP/Workflow/Steering 关键文档 |
| 2026-02-07 | v3.0 | 切换到 Spiral 状态看板；更新仓库地址为 GitHub；定义 S0 进出门禁 |
| 2026-02-06 | v2.3 | 线性 Phase 状态（归档口径） |
