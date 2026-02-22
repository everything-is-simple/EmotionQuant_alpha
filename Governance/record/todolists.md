# todolists（辅助执行清单）

**最后更新**: 2026-02-22  
**定位**: 辅助清单（不替代 SoT，不覆盖现有路线图/执行卡/6A）

---

## 0. 约束声明（防冲突）

1. 本文件仅记录“代码实况核对 + 执行决议 + 下一步待办”。
2. 本文件不替代以下权威入口：
   - `Governance/Capability/SPIRAL-CP-OVERVIEW.md`（路线图/状态 SoT）
   - `Governance/steering/6A-WORKFLOW.md`（6A 执行 SoT）
   - `docs/system-overview.md`（架构 SoT）
   - `Governance/SpiralRoadmap/*-EXECUTION-CARD.md`（圈级执行合同 SoT）
3. 若本文件与 SoT 冲突，以 SoT 为准；本文件必须在下一次 sync 中修正。

---

## 1. 本轮已确认决议（来自代码实况）

1. 主干实现已覆盖 `S0A~S4` 主链，CLI 入口已接通（`run/mss/irs/pas/mss-probe/recommend/fetch-batch/fetch-status/fetch-retry/backtest/trade/analysis/validation`）。
2. 全量测试当前实况：`174 passed / 0 failed`（`TDL-S3-001`~`TDL-S3-014` 主线回归已覆盖）。
3. 当前主阻塞已从“语义冲突”切换为“窗口消费前置条件”：
   - `S3` 的硬阻塞是 `fetch_progress_range_not_cover_backtest_window`（`S3a` 消费契约），不是 `S3b` 算法本身。
   - `backtest/analysis` 并发会触发 DuckDB 文件锁；同一库写入必须串行执行。
   - 以上两项已完成修复/固化：全窗口 `fetch-batch(20260102~20260213)` 可复跑通过，`S3` 与 `S3b` 均恢复 `GO`。
4. `S4b` 已完成跨窗口实跑证据（`trade + stress` 四窗）与参数来源消费闭环；`S4BR/S4R/S5/S5R/S6/S6R/S7A/S7AR` 仍暂无实质实现与覆盖。

---

## 2. 入口对齐矩阵（AGENTS/设计/路线/执行卡/代码）

| 维度 | 权威入口 | 当前对齐结论 |
|---|---|---|
| Agent 执行约束 | `AGENTS.md` | 已按“Spiral + 6A + SoT 入口”执行；本清单仅辅助 |
| 6A 工作流 | `Governance/steering/6A-WORKFLOW.md` | 各圈 run/test/artifact/review/sync 口径已采用 |
| 系统架构 | `docs/system-overview.md` | 八层架构对应代码目录已存在（`src/data..src/gui`） |
| 路线图状态 | `Governance/Capability/SPIRAL-CP-OVERVIEW.md` | 与当前主状态基本一致：`S3/S3b/S3c/S3d/S3e in_progress`，`S3r planned` |
| 执行卡合同 | `Governance/SpiralRoadmap/S3*.md` | 多数已落地；但仍有“窗口证据收口/文档同步漂移”未清零 |
| 代码入口 | `src/pipeline/main.py` | 子命令路由已齐备；S3 断言冲突已解并补充交易日守卫 |

---

## 3. S3 系列执行卡逐项核对（重点：未完成项）

## 3.1 S3

- 卡状态：`Completed`（2026-02-22，cross-window 收口）
- 代码/测试证据：
  - 回测主链存在且可执行：`src/backtest/pipeline.py`
  - 关键测试存在：`tests/unit/backtest/*`
  - CLI 断言冲突已清理：`tests/unit/pipeline/test_cli_entrypoint.py` 已与“无交易窗口 WARN/GO”语义对齐
- 未完成项（必须显式标识）：
  - [x] 处理 `total_trades > 0` 断言与“无交易窗口 WARN/GO”语义冲突（`TDL-S3-001` 已完成）
  - [x] 补齐“更细撮合规则”收口项（`TDL-S3-009` 已完成）
  - [x] 补齐“更完整绩效指标 + 成本/滑点模型”收口项（`TDL-S3-010` + `TDL-S3-011` 已完成）
  - [x] `S3 final` 从 `in_progress/PARTIAL_PASS` 进入 `completed`（跨窗口汇总已固化）

## 3.2 S3a

- 卡状态：`Completed`
- 代码/测试证据：分批/续传/重试链路与测试均已存在
- 发现的执行卡-实现偏差（非阻塞，需修文档）：
  - [x] 已修正执行卡 artifact 清单：移除 `quality_gate_report.md`，并补充 `_state/fetch_progress.json` 与采集三件套一致口径。

## 3.3 S3ar

- 卡状态：`Completed`
- 代码/测试证据：主备通道、锁恢复、幂等测试已落地
- 收口补记：
  - [ ] `artifacts/spiral-s3ar/` 目录未作为常规产物目录使用（当前证据分布在 `artifacts/spiral-s3a/*` 与 `artifacts/token-checks/*`），需在卡片或 review 明确“证据目录分流”

## 3.4 S3b

- 卡状态：`Completed`（2026-02-22，跨窗口复核收口）
- 代码/测试证据：analysis 最小闭环已落地，测试存在
- 硬前置条件（代码口径）：
  - [x] `ab_benchmark` 依赖 `backtest_results` 且窗口内必须存在目标回测行；否则 `P0/backtest_results_not_found_in_window`。
  - [x] `deviation/attribution` 依赖表存在：`trade_records`、`backtest_trade_records`、`integrated_recommendation`；缺表即 `P0`。
  - [x] 若存在表但当日无成交样本，则降级为 `WARN`（`deviation_not_applicable_no_filled_trade` / `attribution_not_applicable_no_filled_trade`），不阻断 `GO`。
- 未完成项（执行卡/规格层面）：
  - [x] 窗口级归因证据收口（跨窗口 `W1~W4`，证据已固化到 `artifacts/spiral-s3b/20260213/cross_window/*`）
  - [x] `signal/execution/cost` 三分解结论稳定性复核（跨窗口分布稳定：`dominant_component=none`，并已记录样本边界）
- 关键一致性漂移（必须处理）：
  - [x] 已完成事实口径统一：`Governance/specs/spiral-s3b/final.md`、`Governance/record/development-status.md`、`Governance/record/debts.md` 已同步为 `remaining_failures=0`、`integrated_days=20`（证据：`artifacts/spiral-s3b/20260213/s3e_targeted_clearance_summary.json`）。

## 3.5 S3c

- 卡状态：`Completed`（2026-02-22，跨窗口复核收口）
- 代码/测试证据：`--strict-sw31` + `irs --require-sw31` 与测试已落地
- 未完成项：
  - [x] 从“单窗口通过（20260219）”升级到“跨窗口稳定性复核并收口”
  - [x] 与 S3b 节奏对齐后将 `spiral-s3c/final.md` 从 `in_progress` 推进

## 3.6 S3d

- 卡状态：`Completed`（2026-02-22，跨窗口复核收口）
- 代码/测试证据：CLI 参数、adaptive、future_returns probe 合同测试已存在
- 未完成项：
  - [x] 窗口级 run/test/artifact/review/sync 五件套收口（跨窗口总览与快照证据已固化）
  - [x] `future_returns` 实跑证据已补齐并固化：`artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md`

## 3.7 S3e

- 卡状态：`Completed`（2026-02-22，跨窗口复核收口）
- 代码/测试证据：validation 子命令、dual-window、OOS、run_manifest 已落地
- 未完成项：
  - [x] 窗口级证据收口与 `final.md` 由 `in_progress` 转完成
  - [x] 与 S3b 的“残留 FAIL 是否清零”口径统一（同 3.4，已同步 `remaining_failures=0`）

## 3.8 S3r

- 卡状态：`Planned`（条件触发）
- 代码/测试证据：`eq backtest --repair s3r` 已可执行
- 未完成项：
  - [ ] 未触发即不执行；仅在 S3 gate=FAIL 时进入
  - [ ] 一旦触发需补齐 `s3r_patch_note/s3r_delta_report/review/final`

---

## 4. 下一步执行顺序（与现有路线图不冲突）

1. `S3`：已完成 `final/review` 收口；后续仅在交易执行语义变更时重开修复子圈。
2. `S3b`：已完成跨窗口归因稳定性复核与收口，后续仅在新增 live filled 样本时按同框架重跑复核。
3. `S3c`：已完成跨窗口稳定性复核并收口。
4. `S3d`：已完成跨窗口证据并收口；后续仅在 return series 定义变化时重开。
5. `S3e`：已完成生产校准窗口证据并收口。
6. `S4b`：已完成跨窗口实跑证据收口（四窗 `GO`）；下一步转入 `S4BR/S4R` 条件触发验证与 S5 监控层实装。
7. `S3r`：仅条件触发（S3 FAIL 时插入，不单独抢占主线）。
8. `S4BR -> S4R -> S5 -> S5R -> S6 -> S6R -> S7A -> S7AR`：按主路线继续。

---

## 5. 立即待办（可直接执行）

- [x] TDL-S3-001：修复 `test_main_backtest_runs_with_s3a_consumption` 的断言冲突（保持与“无交易窗口 WARN/GO”语义一致）。
- [x] TDL-S3-002：补一条明确契约测试，覆盖“`GO/WARN + total_trades=0` 合法”场景，防止回归。
- [x] TDL-S3-003：核对并统一 `S3b` 文档口径（`18/20` vs `20/20`），同步 `development-status/debts/spiral-s3b final`。
- [x] TDL-S3-004：补跑并固化 `S3d` 的 `mss_probe_return_series_report.md` 实跑证据。
- [x] TDL-S3-005：修正 `S3a` 执行卡 artifact 列表与实际产物口径不一致问题。
- [x] TDL-S3-006：完成一次 S3~S3e 全链路 `run/test/artifact/review/sync` 对账并归档。
- [x] TDL-S3-007：清理 `20260218/20260219` 非交易日污染，建立 canary 有效交易日守卫并替换测试硬编码日期。
- [x] TDL-S3-008：修复 `SimulatedTuShareClient.trade_cal` 离线语义（不能默认 `is_open=1`），并补一条“法定闭市日不应判定为开市”的契约测试。
- [x] TDL-S3-009：补齐 S3 更细撮合规则（一字板/流动性枯竭）并新增对应回测契约测试（已落地 `REJECT_ONE_WORD_BOARD` + `REJECT_LIQUIDITY_DRYUP`）。
- [x] TDL-S3-010：补齐 S3 更完整绩效指标（回撤、收益分布、换手稳定性）并落库/产物化。
- [x] TDL-S3-011：补齐 S3 成本/滑点模型细化（分层费率与冲击成本）并完成回归对账。
- [x] TDL-S3-012：修复 S3 质量门与信号日期错位问题（仅对存在 `integrated_recommendation` 的日期判定 `quality_gate`，缺门禁日期仍按 P0 拦截），并补回归测试。
- [x] TDL-S3-013：修复 `fetch-batch` 窗口交易日历加载语义（按窗口一次性读取 `trade_cal`，只跑开市日；真实链路强制串行写库），并将 CLI 默认 `batch-size` 调整为 `30`。
- [x] TDL-S3-014：修复 `fetch_progress` 缩窗导致的 S3 误阻断（当本地 L1 已覆盖窗口时，`fetch_progress` 未覆盖降级为 WARN，不再 P0 阻断）。
- [x] TDL-S3-015：完成 S3b 跨窗口（W1~W4）三分解稳定性复核与收口，固化窗口级快照证据并更新 `spiral-s3b/final` 为 `completed`。
- [x] TDL-S3-016：完成 S3c 跨窗口（20260210/11/12/13）SW31 语义与 IRS 覆盖稳定性复核，并更新 `spiral-s3c/final`、`spiral-s3c/review` 为 `completed`。
- [x] TDL-S3-017：完成 S3 跨窗口（W1~W4）run/test/artifact/review/sync 收口，并更新 `spiral-s3/requirements`、`spiral-s3/review`、`spiral-s3/final` 为 completed 口径。
- [x] TDL-S3-018：完成 S3d 跨窗口（adaptive + future_returns probe）复核收口，并更新 `spiral-s3d/requirements`、`spiral-s3d/review`、`spiral-s3d/final` 为 completed。
- [x] TDL-S3-019：完成 S3e 跨窗口（20260210/11/12/13）Validation 生产口径复核收口，并更新 `spiral-s3e/requirements`、`spiral-s3e/review`、`spiral-s3e/final` 为 completed。
- [x] TDL-S4B-001：新增 `eq stress` CLI 子命令与 `src/stress/pipeline.py`，支持 `limit_down_chain/liquidity_dryup/all` 与 `--repair s4br`，并生成执行卡要求产物（`extreme_defense_report/deleveraging_policy_snapshot/stress_trade_replay/consumption/gate_report`）。
- [x] TDL-S4B-002：新增 S4b 三条交易层契约测试（`test_stress_limit_down_chain`、`test_stress_liquidity_dryup`、`test_deleveraging_policy_contract`）与 1 条 CLI 接线测试（`test_main_stress_command_wires_to_pipeline`）。
- [x] TDL-S4B-003：执行 S4b 跨窗口实跑（`20260210/11/12/13`）并固化汇总证据到 `artifacts/spiral-s4b/20260213/cross_window/*`，并补齐 `Governance/specs/spiral-s4b` 收口文档。
- [x] TDL-S4B-004：清理 `analysis --deviation` 的“单侧样本缺失即 FAIL”语义，改为 `WARN/GO` 非阻断，并补回归测试与四窗复跑验证。
- [x] TDL-OPS-TUSHARE-001：新增 `scripts/data/check_tushare_dual_tokens.py`（显式读取 `.env`，一次校验 `primary/fallback` 两路 key），并在 `docs/reference/tushare/tushare-channel-policy.md` 固化“`--token-env` 不会主动加载 `.env`”的误判根因与推荐命令。

---

## 6. 变更记录

- 2026-02-22：首次创建。用于固化“代码实况结论 + S3 系列未收口项 + 下一步顺序”。
- 2026-02-22：完成 `TDL-S3-001`。已将 CLI 回测测试从强制 `total_trades > 0` 调整为契约一致断言（允许 `0`，并在 `0` 时校验 `no_long_entry_signal_in_window` 告警证据）；验证结果：`pytest -q` 全量 `164 passed`。
- 2026-02-22：完成 `TDL-S3-002`。新增 CLI 显式契约测试：`WARN + GO + total_trades=0` 返回码仍为 `0` 且输出为 `s3_backtest`，用于防止“无交易窗口”语义回归。
- 2026-02-22：完成 `TDL-S3-003`。已将 S3b 口径统一为 `20/20` 覆盖与 `remaining_failures=0`，并同步 `spiral-s3b final`、`development-status`、`debts`。
- 2026-02-22：完成 `TDL-S3-004`。已执行 `mss-probe --return-series-source future_returns` 实跑补证，产出 `artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md` 与配套 gate/consumption/error_manifest，并通过 2 条 S3d 目标测试。
- 2026-02-22：完成 `TDL-S3-005`。已修订 `S3A-EXECUTION-CARD` 的 artifact 清单，移除错误的 `quality_gate_report.md`，并补充 `_state/fetch_progress.json` 实际续传游标口径。
- 2026-02-22：完成 `TDL-S3-006`。已完成一次 S3~S3e `run/test/artifact/review/sync` 对账并归档，归档文件：`Governance/record/s3-s3e-fullchain-reconciliation-20260222.md`。
- 2026-02-22：完成 `TDL-S3-007`。已新增 canary 交易日基线 `tests/fixtures/canary/a_share_open_trade_days_20260102_20260213.json` 与守卫工具 `tests/unit/trade_day_guard.py`；并将测试中的 `20260218/20260219` 统一替换为有效交易日窗口，仅在守卫反例测试中保留无效日断言。
- 2026-02-22：完成 `TDL-S3-008`。`src/data/fetcher.py` 的 `SimulatedTuShareClient.trade_cal` 已由“默认开市”改为“周末+法定闭市日判定”，并新增 `tests/unit/data/test_fetcher_contract.py::test_simulated_trade_cal_marks_lunar_new_year_closure_days_as_closed`；验证结果：`pytest -q` 全量 `167 passed`。
- 2026-02-22：完成 `TDL-S3-009`。`src/backtest/pipeline.py` 已补齐一字板与流动性枯竭显式拒单（`REJECT_ONE_WORD_BOARD`、`REJECT_LIQUIDITY_DRYUP`）与审计计数（`one_word_board_blocked_count`、`liquidity_dryup_blocked_count`），并新增回归测试 `test_backtest_rejects_buy_when_one_word_board`、`test_backtest_rejects_buy_when_low_fill_probability`。
- 2026-02-22：完成 `TDL-S3-010`。`src/backtest/pipeline.py` 已新增绩效指标落库字段（`max_drawdown_days`、`daily_return_*`、`turnover_*`）与产物 `performance_metrics_report.md`；并通过 backtest/CLI 回归与全量测试（`167 passed`）。
- 2026-02-22：完成 `TDL-S3-011`。`src/backtest/pipeline.py` 已新增分层费率（`S/M/L`）与冲击成本模型（按 `liquidity_tier + queue_pressure`），并将 `commission/stamp/transfer/impact/total_fee/cost_bps` 落库到 `backtest_results`；新增 `tests/unit/backtest/test_backtest_cost_model_contract.py`，验证结果：全量 `170 passed`。
- 2026-02-22：完成 `TDL-S3-012`。`src/backtest/pipeline.py` 新增 `quality_gate` 按信号日期过滤逻辑（避免无信号历史 FAIL 误阻断当前窗口），同时保留“信号日期缺门禁即 P0”契约；新增 `tests/unit/backtest/test_backtest_contract.py::test_backtest_ignores_gate_fail_for_dates_without_integrated_signals`，并实跑 `backtest 20260102~20260213` 恢复 `bridge_check_status=PASS / go_nogo=GO / total_trades=36`。
- 2026-02-22：完成 `TDL-S3-013`。`src/data/fetch_batch_pipeline.py` 改为窗口级一次性读取 `trade_cal` 并仅执行开市日采集，真实链路写库固定 `workers=1`；`src/pipeline/main.py` 将 `fetch-batch` 默认 `batch-size` 下调到 `30` 并补 CLI 契约测试。新增实测速率脚本 `scripts/data/benchmark_tushare_l1_channels_window.py`（含中文注释），实测 `20260101~20260213`：`primary` 约 `38~57 calls/min`，`fallback` 约 `197~206 calls/min`。
- 2026-02-22：完成 `TDL-S3-014`。`src/backtest/pipeline.py` 对 `s3a_consumption` 新增“本地 L1 覆盖兜底”语义：当 `fetch_progress` 状态/窗口不满足，但 `raw_trade_cal + raw_daily` 在目标窗口存在覆盖时，改为 `WARN`（`fetch_progress_*_but_local_l1_covered`）而非 `P0`；新增契约测试 `tests/unit/backtest/test_backtest_contract.py::test_backtest_uses_local_l1_coverage_when_fetch_progress_range_is_narrow`。验证：`pytest -q` 全量 `174 passed`。
- 2026-02-22：完成 `TDL-S3-015`。已串行复跑四个窗口（`W1:20260102-20260213`、`W2:20260119-20260213`、`W3:20260210-20260213`、`W4:20260212-20260213`）的 `backtest + analysis(AB+deviation+attribution)`，四窗均 `GO`；结论分布稳定：`A_not_dominant=4`、`dominant_component=none=4`。已固化总览与快照证据：`artifacts/spiral-s3b/20260213/s3b_cross_window_stability_summary.{json,md}`、`artifacts/spiral-s3b/20260213/cross_window/*`，并将 `Governance/specs/spiral-s3b/final.md` 更新为 `completed`。
- 2026-02-22：完成 `TDL-S3-016`。已串行复跑四个交易日（`20260210/20260211/20260212/20260213`）的 `run --to-l2 --strict-sw31 + irs --require-sw31`，四窗均满足 `industry_snapshot_count=31`、`irs_industry_count=31`、`gate_status=PASS`、`go_nogo=GO`。证据已固化：`artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.{json,md}` 与 `artifacts/spiral-s3c/20260213/cross_window/*`；`Governance/specs/spiral-s3c/final.md`、`Governance/specs/spiral-s3c/review.md` 已更新为 `completed`。
- 2026-02-22：完成 `TDL-S3-017`。已基于 `W1~W4` 快照固化 S3 跨窗口汇总：`artifacts/spiral-s3/20260213/s3_cross_window_summary.{json,md}`（`all_windows_go=true`），并同步 `Governance/specs/spiral-s3/requirements.md`、`Governance/specs/spiral-s3/review.md`、`Governance/specs/spiral-s3/final.md` 为 completed 口径（含 `fetch_progress` 本地覆盖兜底语义）。
- 2026-02-22：完成 `TDL-S3-018`。已串行完成 S3d 跨窗口复核：adaptive 日期窗 `20260210/11/12/13` 全部 `gate_result=PASS`；future_returns probe 窗口 `20260119-20260213`、`20260126-20260213`、`20260203-20260213`、`20260206-20260213` 均成功落盘并可解释（结论分布：2x positive / 1x negative warn / 1x flat warn）。边界 `20260210-20260213` 的 `P1/future_returns_series_missing` 已固化为短窗样本不足证据。已落盘：`artifacts/spiral-s3d/20260213/s3d_cross_window_summary.{json,md}` 与 `artifacts/spiral-s3d/20260213/cross_window/*`；并同步 `Governance/specs/spiral-s3d/requirements.md`、`Governance/specs/spiral-s3d/review.md`、`Governance/specs/spiral-s3d/final.md` 为 completed。
- 2026-02-22：完成 `TDL-S3-019`。已串行复跑四个交易日（`20260210/20260211/20260212/20260213`）`eq validation --trade-date {trade_date} --threshold-mode regime --wfa dual-window --export-run-manifest`，四窗均 `status=ok`、`final_gate=WARN`、`go_nogo=GO`、`selected_weight_plan=vp_balanced_v1`。已固化总览与快照证据：`artifacts/spiral-s3e/20260213/s3e_cross_window_summary.{json,md}` 与 `artifacts/spiral-s3e/20260213/cross_window/*`；并同步 `Governance/specs/spiral-s3e/requirements.md`、`Governance/specs/spiral-s3e/review.md`、`Governance/specs/spiral-s3e/final.md` 为 completed。
- 2026-02-22：完成 `TDL-S4B-001` + `TDL-S4B-002`。已新增 `src/stress/pipeline.py` 与 `eq stress` CLI 路由（`limit_down_chain/liquidity_dryup/all` + `--repair s4br`），落地执行卡要求的 5 类产物，并补齐 3 条 S4b 契约测试 + 1 条 CLI 接线测试。验证结果：`pytest -q tests/unit/trading tests/unit/pipeline/test_cli_entrypoint.py::test_main_stress_command_wires_to_pipeline` => `10 passed`。
- 2026-02-22：完成 `TDL-S4B-003`。已在隔离数据环境（`artifacts/spiral-s4b/20260213/eq_data_tdl_s4b_003_isolated`）串行复跑四窗 `trade + stress`，并固化总览证据：`artifacts/spiral-s4b/20260213/s4b_cross_window_summary.{json,md}` 与 `artifacts/spiral-s4b/20260213/cross_window/*`。结论：`all_trade_go=true`、`all_stress_go=true`、`stress_gate_distribution={'WARN':8}`，且 `stress_policy_source_distribution={'live_backtest_deviation':8}`（参数来源已可追溯到 S3b 偏差表）。
- 2026-02-22：完成 `TDL-S4B-004`。`src/analysis/pipeline.py` 已将 `live-backtest deviation` 的单侧样本缺失从 `P1 error` 调整为 `warning`（`WARN/GO`），并新增回归测试 `tests/unit/analysis/test_live_backtest_deviation_contract.py::test_live_backtest_deviation_backtest_side_empty_is_warn_not_fail`。四窗复跑后 `analysis_status_distribution={'ok':4}`、`analysis_quality_distribution={'WARN':4}`，S4b 汇总证据已刷新。
- 2026-02-22：完成 `TDL-OPS-TUSHARE-001`。新增双通道 key 基线脚本 `scripts/data/check_tushare_dual_tokens.py`，固定命令：`python scripts/data/check_tushare_dual_tokens.py --env-file .env --channels both`。并在 `docs/reference/tushare/tushare-channel-policy.md` 明确：`check_tushare_l1_token.py --token-env ...` 不会自动加载 `.env`，若 shell 未导入环境变量会回退 docs token 文件，从而造成兜底 key 误判。
