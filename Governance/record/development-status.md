# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-22  
**当前版本**: v4.45（TDL-S3-019：S3e 跨窗口收口完成）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S3/S3b/S3c/S3d/S3e 与 S4/S3ar 已收口完成：当前聚焦 S4b 参数校准闭环**

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

## 本次同步（2026-02-22，TDL-S3-019：S3e 跨窗口收口）

1. 跨窗口实跑（生产口径）：
   - `eq validation --trade-date 20260210/20260211/20260212/20260213 --threshold-mode regime --wfa dual-window --export-run-manifest` 全部成功。
2. 跨窗口结论：
   - 四窗均 `status=ok`、`final_gate=WARN`、`go_nogo=GO`。
   - `selected_weight_plan` 稳定为 `vp_balanced_v1`（4/4）。
   - `vote_detail` 一致：`factor_gate_raw=FAIL` 经中性状态软化后 `factor_gate=WARN`，符合 S3e 软门语义。
3. 证据固化：
   - `artifacts/spiral-s3e/20260213/s3e_cross_window_summary.json`
   - `artifacts/spiral-s3e/20260213/s3e_cross_window_summary.md`
   - `artifacts/spiral-s3e/20260213/cross_window/*`
4. 文档收口：
   - `Governance/specs/spiral-s3e/requirements.md` -> `completed`
   - `Governance/specs/spiral-s3e/review.md` -> `completed`
   - `Governance/specs/spiral-s3e/final.md` -> `completed`
5. 目标测试：
   - `pytest tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py tests/unit/algorithms/validation/test_decay_proxy_contract.py tests/unit/pipeline/test_cli_entrypoint.py::test_main_validation_command_wires_to_pipeline tests/unit/pipeline/test_cli_entrypoint.py::test_main_validation_runs_s3e_mode -q` -> `6 passed`

---

## 本次同步（2026-02-22，TDL-S3-018：S3d 跨窗口收口）

1. adaptive 阈值跨窗口复核：
   - `eq mss --date 20260210/20260211/20260212/20260213 --threshold-mode adaptive` 全部通过（`gate_result=PASS`）。
2. future_returns probe 跨窗口复核：
   - 成功窗口：`20260119-20260213`、`20260126-20260213`、`20260203-20260213`、`20260206-20260213`。
   - 结论分布：`PASS_POSITIVE_SPREAD x2`、`WARN_NEGATIVE_SPREAD x1`、`WARN_FLAT_SPREAD x1`。
   - 边界窗口：`20260210-20260213`（`P1/future_returns_series_missing`，样本不足，不作为主结论窗口）。
3. 证据固化：
   - `artifacts/spiral-s3d/20260213/s3d_cross_window_summary.json`
   - `artifacts/spiral-s3d/20260213/s3d_cross_window_summary.md`
   - `artifacts/spiral-s3d/20260213/cross_window/*`
4. 文档收口：
   - `Governance/specs/spiral-s3d/requirements.md` -> `completed`
   - `Governance/specs/spiral-s3d/review.md` -> `completed`
   - `Governance/specs/spiral-s3d/final.md` -> `completed`
5. 目标测试：
   - `pytest tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_supports_s3d_threshold_mode tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_probe_supports_future_returns_source -q` -> `5 passed`

---

## 本次同步（2026-02-22，TDL-S3-017：S3 跨窗口收口）

1. 跨窗口汇总固化（复用 W1~W4）：
   - `artifacts/spiral-s3/20260213/s3_cross_window_summary.json`
   - `artifacts/spiral-s3/20260213/s3_cross_window_summary.md`
   - 结论：`all_windows_go=true`，桥接检查均为 `PASS`。
2. 语义口径更新：
   - `S3a fetch_progress` 覆盖不足时，若本地 `raw_trade_cal + raw_daily` 已覆盖窗口，S3 消费降级为 `WARN`，不再误判 `P0`。
3. 文档收口：
   - `Governance/specs/spiral-s3/requirements.md` -> `completed`
   - `Governance/specs/spiral-s3/review.md` -> `completed`
   - `Governance/specs/spiral-s3/final.md` -> `completed`

---

## 本次同步（2026-02-22，TDL-S3-016：S3c 跨窗口 SW31 复核收口）

1. 跨窗口实跑（串行）：
   - `eq run --date {trade_date} --to-l2 --strict-sw31`，窗口：`20260210/20260211/20260212/20260213`。
   - `eq irs --date {trade_date} --require-sw31`，同窗口。
2. 跨窗口结论：
   - 四窗均满足 `industry_snapshot_count=31`。
   - 四窗均满足 `irs_industry_count=31`、`gate_status=PASS`、`go_nogo=GO`。
   - 汇总结论：`all_sw31_coverage_pass=true`。
3. 证据固化：
   - `artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.json`
   - `artifacts/spiral-s3c/20260213/s3c_cross_window_sw31_summary.md`
   - `artifacts/spiral-s3c/20260213/cross_window/*`
4. 文档收口：
   - `Governance/specs/spiral-s3c/final.md` -> `completed`
   - `Governance/specs/spiral-s3c/review.md` -> `completed`
5. 目标测试：
   - `pytest tests/unit/data/test_industry_snapshot_sw31_contract.py tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline -q` -> `4 passed`

---

## 本次同步（2026-02-22，TDL-S3-012/013/014：S3/S3b 解锁与 S3a 语义修复）

1. S3 阻塞根因修复：
   - `src/backtest/pipeline.py` 新增 `quality_gate` 与信号日期对齐过滤，避免“无信号历史 FAIL”误阻断当前窗口。
   - 保留硬约束：若存在 `integrated_recommendation` 但缺对应 `quality_gate_report`，仍按 P0 拦截（`quality_gate_missing_for_integrated_signal_dates`）。
2. S3a 抓取语义与吞吐修复：
   - `src/data/fetch_batch_pipeline.py` 改为窗口级一次性读取 `trade_cal`，仅对开市日执行采集。
   - 真实链路写库固定 `workers=1`，避免多进程并发写 DuckDB 造成锁冲突。
   - `src/pipeline/main.py` 将 `fetch-batch` 默认 `batch-size` 调整为 `30`。
3. S3 消费兜底修复（TDL-S3-014）：
   - `src/backtest/pipeline.py` 在 `fetch_progress` 未覆盖窗口时新增本地覆盖兜底：若 `raw_trade_cal + raw_daily` 在窗口内已覆盖，降级为 `WARN`（不再 `P0` 阻断）。
   - 新增测试：`tests/unit/backtest/test_backtest_contract.py::test_backtest_uses_local_l1_coverage_when_fetch_progress_range_is_narrow`。
4. 实跑验证（canary 窗口 `20260102~20260213`）：
   - `fetch-batch` 完成：`status=completed`，`total_batches=2`，`workers=1`。
   - `backtest` 完成：`bridge_check_status=PASS`，`quality_status=WARN`，`go_nogo=GO`，`total_trades=36`。
   - `analysis --ab-benchmark --deviation live-backtest --attribution-summary` 完成：`quality_status=WARN`，`go_nogo=GO`。
5. 质量验证：
   - `pytest -q` => `174 passed, 0 failed`。
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。

---

## 本次同步（2026-02-22，TDL-S3-011：成本/滑点模型细化）

1. 成本模型升级：
   - `src/backtest/pipeline.py` 新增分层费率模型（`S/M/L` notional tier），佣金按 tier multiplier 计算。
   - 新增冲击成本模型：基于 `liquidity_tier(L1/L2/L3)` + `queue_pressure` + `backtest_slippage_value` 计算 `impact_cost`。
2. 成本指标落库：
   - `backtest_results` 新增 `commission_total/stamp_tax_total/transfer_fee_total/impact_cost_total/total_fee/cost_bps/impact_cost_ratio`。
   - `performance_metrics_report.md` 新增 `Cost & Slippage` 分节与 tier 计数审计字段。
3. 契约测试补齐：
   - 新增 `tests/unit/backtest/test_backtest_cost_model_contract.py`（费率分层、流动性冲击、排队压力三条合同）。
   - 更新 `tests/unit/backtest/test_backtest_contract.py` 与 `tests/unit/backtest/test_backtest_schema_compat_contract.py` 校验新成本字段。
4. 验证结果：
   - `pytest -q tests/unit/backtest` => `18 passed`。
   - `pytest -q` => `170 passed, 0 failed`。
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。

---

## 本次同步（2026-02-22，TDL-S3-010：绩效指标补齐）

1. 回测结果落库增强：
   - `src/backtest/pipeline.py` 的 `backtest_results` 新增 `max_drawdown_days`、`daily_return_mean/std/p05/p95/skew`、`turnover_mean/std/cv`。
   - 保持旧表兼容：通过 `_persist` 自动补列完成 schema 演进。
2. 绩效产物补齐：
   - 新增 `performance_metrics_report.md`（路径：`artifacts/spiral-s3/{end_date}/performance_metrics_report.md`）。
   - 报告包含回撤持续、收益分布、换手稳定性三组指标。
3. CLI 兼容增强：
   - `src/pipeline/main.py` 为 `performance_metrics_report_path` 增加可选输出，兼容旧 mock 返回对象。
4. 契约与回归：
   - 更新 `tests/unit/backtest/test_backtest_contract.py`（校验新报告存在与新字段落库）。
   - 更新 `tests/unit/backtest/test_backtest_schema_compat_contract.py`（校验旧 schema 升级时新增指标列）。
5. 验证结果：
   - `pytest -q tests/unit/backtest tests/unit/pipeline/test_cli_entrypoint.py` => `38 passed`。
   - `pytest -q` => `167 passed, 0 failed`。
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。

---

## 本次同步（2026-02-22，TDL-S3-009：细撮合规则补齐-第二步）

1. 回测成交语义继续增强：
   - `src/backtest/pipeline.py` 新增流动性枯竭显式拒单路径，拒单原因固定为 `REJECT_LIQUIDITY_DRYUP`。
   - 新增审计计数 `liquidity_dryup_blocked_count`，并写入 `gate_report` 与质量消息片段。
   - 保留并隔离 `REJECT_LOW_FILL_PROB`：当不属于流动性枯竭但排队成交概率不足时触发，避免语义混淆。
2. 契约测试补齐：
   - 更新 `tests/unit/backtest/test_backtest_t1_limit_rules.py::test_backtest_rejects_buy_when_liquidity_dryup`，改为断言 `REJECT_LIQUIDITY_DRYUP`。
   - 新增 `tests/unit/backtest/test_backtest_t1_limit_rules.py::test_backtest_rejects_buy_when_low_fill_probability`，锁定低成交概率拒单路径。
3. 验证结果：
   - `pytest -q tests/unit/backtest tests/unit/data/test_fetcher_contract.py` => `25 passed`。
   - `pytest -q` => `167 passed, 0 failed`。
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。
4. 状态说明：
   - `TDL-S3-009` 已完成（“一字板 + 流动性枯竭”细撮合规则均已落地并有契约测试覆盖）。

---

## 本次同步（2026-02-22，TDL-S3-009：细撮合规则补齐-第一步）

1. 回测成交语义增强（S3 未收口项推进）：
   - `src/backtest/pipeline.py` 新增一字板显式拒单路径，拒单原因固定为 `REJECT_ONE_WORD_BOARD`。
   - 新增审计计数 `one_word_board_blocked_count`，并写入 `gate_report` 与质量消息片段，支持窗口级审计。
2. 契约测试补齐：
   - 新增 `tests/unit/backtest/test_backtest_t1_limit_rules.py::test_backtest_rejects_buy_when_one_word_board`。
   - 覆盖“买入执行日一字板 -> 拒单”与 gate 报告字段存在性。
3. 验证结果：
   - `pytest -q tests/unit/backtest tests/unit/data/test_fetcher_contract.py` => `24 passed`。
   - `pytest -q` => `166 passed, 0 failed`。
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。
4. 状态说明：
   - 该同步为 `TDL-S3-009` 第一阶段；第二阶段已补齐流动性枯竭细化并完成收口。

---

## 本次同步（2026-02-22，TDL-S3-008：离线 trade_cal 语义修复）

1. 根因修复：
   - `src/data/fetcher.py` 的 `SimulatedTuShareClient.trade_cal` 已从“默认 `is_open=1`”改为按日期判定。
   - 新增离线判定逻辑：周末闭市 + 法定闭市日集合（含 `20260218/20260219`）闭市。
   - `trade_cal` 返回从单日固定记录升级为 `start_date~end_date` 区间逐日记录。
2. 契约测试补齐：
   - 新增 `tests/unit/data/test_fetcher_contract.py::test_simulated_trade_cal_marks_lunar_new_year_closure_days_as_closed`。
   - 锁定 `20260218/20260219 => is_open=0`，并保留 `20260212/20260213 => is_open=1` 作为对照。
3. 验证结果：
   - `pytest -q tests/unit/data` => `38 passed`。
   - `pytest -q` => `166 passed, 0 failed`。
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。

---

## 本次同步（2026-02-22，TDL-S3-007：S3 窗口级桥接失败场景清理）

1. 完成非交易日实况核对并定位污染源：
   - 实网交易日历确认 `20260218/20260219` 为闭市日（`is_open=0`）。
   - 本地 `raw_trade_cal` 存在 `is_open=1` 污染记录，已明确为后续修复关注点。
2. 建立“有效交易日前置校验”金丝雀基线：
   - 新增 `tests/fixtures/canary/a_share_open_trade_days_20260102_20260213.json`（`open_day_count=30`）。
   - 新增 `tests/unit/trade_day_guard.py`：`latest_open_trade_days`、`assert_all_valid_trade_days`。
   - 新增 `tests/unit/test_trade_day_guard_contract.py` 守卫契约测试（含无效日反例断言）。
3. 清理测试硬编码无效交易日：
   - 将 `tests/unit` 中 `20260218/20260219`（除守卫反例）统一替换到 canary 有效窗口；
   - 对 S3/S4 关键链路测试补充“先校验有效交易日”的前置断言。
4. 验证结果：
   - 全量测试：`pytest -q` => `164 passed, 0 failed`。
   - 治理门禁：`python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS。

---

## 本次同步（2026-02-22，S3b Option2 扩窗 20 日）

1. 按 `Option2` 完成缺失链路补齐：
   - 对缺失日串行执行 `run --to-l2 --strict-sw31 -> mss -> irs --require-sw31 -> pas`，补齐 15 天。
   - 产物：`artifacts/spiral-s3b/20260213/option2_refill_20d_results.json`（15/15 成功）。
2. 完成 20 日信号补齐与残留识别：
   - 通过 `recommend --mode integrated --with-validation-bridge` 快速补齐后，初次收敛为 2 天（`20260126`、`20260202`，`factor_validation_fail`）；该残留已在后续 `TDL-S3-003` 同步中清零。
   - 产物：`artifacts/spiral-s3b/20260213/option2_signal_fill_20d_results.json`。
3. 完成 20 日回测与分析收口证据：
   - `eq backtest --engine local_vectorized --start 20260119 --end 20260213` => `quality_status=WARN`, `go_nogo=GO`, `total_trades=36`, `consumed_signal_rows=288`。
   - `eq analysis --start 20260119 --end 20260213 --ab-benchmark` => `quality_status=PASS`, `go_nogo=GO`，结论 `A_not_dominant`。
4. 固化本轮汇总：
   - `artifacts/spiral-s3b/20260213/option2_closure_summary.json`。
5. 回归验证：
   - `pytest` 定向回归通过（4 passed）：S3e 软门契约、CLI `pas` 路由、validation 参数透传、S3e 默认模式透传。

---

## 本次同步（2026-02-22，TDL-S3-003：S3b 口径统一）

1. 证据核对完成：
   - `artifacts/spiral-s3b/20260213/s3e_targeted_clearance_summary.json` 已记录 `remaining_failures=0`、`integrated_days=20`、`missing_days=0`。
2. 同步修订完成：
   - `Governance/specs/spiral-s3b/final.md` 从“`18/20` + 残留 2 天 FAIL”更新为“`20/20` + `remaining_failures=0`”。
   - `Governance/record/debts.md` 清偿 `TD-S3E-020` 并移出当前债务清单。
3. 当前圈位结论：
   - S3b 继续 `in_progress`，剩余收口项为“三分解结论稳定性复核 + review/final 同步”，不再包含 `factor_validation_fail` 清零阻塞。

---

## 本次同步（2026-02-22，TDL-S3-004：S3d probe 实跑补证）

1. 完成实跑补证：
   - 执行命令：`python -m src.pipeline.main --env-file .env mss-probe --start 20260119 --end 20260213 --return-series-source future_returns`。
   - 结果：`event=s3d_mss_probe`，`status=ok`，`conclusion=PASS_POSITIVE_SPREAD`，`top_bottom_spread_5d=0.0120704975`。
2. 固化产物：
   - `artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md`
   - `artifacts/spiral-s3d/20260119_20260213/gate_report.md`
   - `artifacts/spiral-s3d/20260119_20260213/consumption.md`
   - `artifacts/spiral-s3d/20260119_20260213/error_manifest_sample.json`
3. 定向回归：
   - `pytest -q tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py`
   - `pytest -q tests/unit/pipeline/test_cli_entrypoint.py::test_main_mss_probe_supports_future_returns_source`

---

## 本次同步（2026-02-22，TDL-S3-005：S3a artifact 清单对齐）

1. 修订执行卡：`Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md`
   - 移除错误产物：`artifacts/spiral-s3a/{trade_date}/quality_gate_report.md`
   - 补充真实续传游标：`artifacts/spiral-s3a/_state/fetch_progress.json`
   - 保持 S3a 三件套产物不变：`fetch_progress` / `throughput_benchmark` / `fetch_retry_report`
2. 对齐结论：
   - S3a 执行卡 artifact 口径与 `src/data/fetch_batch_pipeline.py` 实际落盘逻辑一致。
   - 本次为文档口径修订，不改变圈位状态与代码行为。

---

## 本次同步（2026-02-22，TDL-S3-006：S3~S3e 全链路对账归档）

1. 已完成一次 S3~S3e 全链路 `run/test/artifact/review/sync` 对账并归档：
   - 归档文件：`Governance/record/s3-s3e-fullchain-reconciliation-20260222.md`
2. run 对账结论：
   - `S3d/S3c/S3e/S3b` 目标命令可执行并产物齐备。
   - `S3 backtest` 在 `20260218-20260219` 首次复核出现 `bridge_check_status=FAIL`（`consumed_signal_rows=0`），补跑后在 `20260219-20260219` 复核通过（`WARN/GO`）。
3. test 对账结论：
   - 目标测试集合执行结果：`34 passed`（含 S3~S3e 的 backtest/analysis/irs/mss/validation/CLI 关键用例）。
4. 口径说明：
   - 本次“对账归档完成”不等于“圈位全部收口完成”；S3/S3b/S3c/S3d/S3e 仍按各自 `final/review` 保持 `in_progress` 直到窗口级证据闭环完成。

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
| S3b | 收益归因验证专项圈 | 🔄 进行中 | 已完成 20 日扩窗证据并确认 `20/20` 覆盖（`remaining_failures=0`）；待完成三分解稳定性复核与收口同步 |
| S3c | 行业语义校准专项圈（SW31 映射 + IRS 全覆盖门禁） | 🔄 进行中 | `20260219` 窗口已通过 SW31/IRS 门禁并补齐 `gate/consumption` 产物，待与 S3b 固定窗口节奏对齐后收口 |
| S3d | MSS 自适应校准专项圈（adaptive 阈值 + probe 真实收益） | 🔄 进行中 | 已补齐 `future_returns` probe 实跑证据，待完成剩余窗口五件套收口 |
| S3e | Validation 生产校准专项圈（future_returns + 双窗口 WFA） | 🔄 进行中 | CLI 阻断已解除，进入窗口级证据收口 |
| S4b | 极端防御专项圈 | 📋 未开始 | 依赖 S3e 收口结论输入防御参数 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4b 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |
| S7a | ENH-11 自动调度闭环 | 📋 未开始 | 依赖 S6 完成 |

---

## 下一步（S3b/S3c/S3d/S3e）

1. 在 S3b 固化 `20/20` 覆盖与 N/A 警告语义到 `spiral-s3b/review/final`，完成窗口级归因稳定性复核。
2. 基于 `20260219` 已有 S3c 证据，补跑固定窗口并完成 `spiral-s3c final` 收口。
3. 对 S3d/S3e 执行窗口级实证并固化 `review/final`。
4. 仅当 S3d/S3e 完成窗口证据收口后，再进入 S4b（极端防御）。

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
| 2026-02-22 | v4.39 | 完成 TDL-S3-011：回测落地分层费率与冲击成本模型，新增成本指标落库与成本契约测试，验证全量 `170 passed` |
| 2026-02-22 | v4.38 | 完成 TDL-S3-010：回测新增收益分布/换手稳定性指标落库与 `performance_metrics_report.md` 产物，兼容 CLI 输出并验证全量 `167 passed` |
| 2026-02-22 | v4.37 | 完成 TDL-S3-009 第二步：回测新增 `REJECT_LIQUIDITY_DRYUP` 与审计计数，补齐低成交概率独立拒单回归，验证全量 `167 passed` |
| 2026-02-22 | v4.36 | 启动 TDL-S3-009：回测新增一字板显式拒单与审计计数，补齐对应契约测试并验证全量 `166 passed` |
| 2026-02-22 | v4.35 | 执行 TDL-S3-008：修复离线 `trade_cal` 默认开市语义，新增法定闭市日契约测试并验证全量 `165 passed` |
| 2026-02-22 | v4.34 | 执行 TDL-S3-007：完成 S3 窗口级桥接失败场景清理，建立 canary 有效交易日守卫（`20260102-20260213`）并清理测试硬编码无效日期；全量回归 `164 passed` |
| 2026-02-22 | v4.33 | 执行 TDL-S3-006：完成 S3~S3e 一次 `run/test/artifact/review/sync` 全链路对账并归档（`Governance/record/s3-s3e-fullchain-reconciliation-20260222.md`） |
| 2026-02-22 | v4.32 | 执行 TDL-S3-005：修正 `S3A-EXECUTION-CARD` artifact 清单（移除 `quality_gate_report.md`，补充 `_state/fetch_progress.json`），与 S3a 实际产物对齐 |
| 2026-02-22 | v4.31 | 执行 TDL-S3-004：补跑并固化 S3d `mss_probe_return_series_report` 实跑证据（`20260119_20260213`），并通过 S3d 目标测试回归 |
| 2026-02-22 | v4.30 | 执行 TDL-S3-003：统一 S3b 口径为 `20/20` 覆盖、`remaining_failures=0`；同步修订 `spiral-s3b final` 与 `debts`，并将 S3b 剩余项收敛为“稳定性复核 + 收口同步” |
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
