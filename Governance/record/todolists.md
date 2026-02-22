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
2. 全量测试当前实况：`170 passed / 0 failed`（`TDL-S3-001`、`TDL-S3-007`、`TDL-S3-008`、`TDL-S3-009`、`TDL-S3-010`、`TDL-S3-011` 已完成）。
3. 当前主阻塞是“语义冲突”而非链路断裂：
   - 回测只接收 `BUY/STRONG_BUY` 入场（`src/backtest/pipeline.py`）。
   - 当前集成推荐在部分窗口可全为 `HOLD`（`src/integration/pipeline.py` 分档）。
   - 结果是 `GO/WARN` 但 `total_trades=0`，与单测断言冲突。
4. `S4B` 之后（`S4BR/S4R/S5/S5R/S6/S6R/S7A/S7AR`）暂无实质实现入口与测试覆盖。

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

- 卡状态：`Active`（未完成）
- 代码/测试证据：
  - 回测主链存在且可执行：`src/backtest/pipeline.py`
  - 关键测试存在：`tests/unit/backtest/*`
  - CLI 断言冲突已清理：`tests/unit/pipeline/test_cli_entrypoint.py` 已与“无交易窗口 WARN/GO”语义对齐
- 未完成项（必须显式标识）：
  - [x] 处理 `total_trades > 0` 断言与“无交易窗口 WARN/GO”语义冲突（`TDL-S3-001` 已完成）
  - [x] 补齐“更细撮合规则”收口项（`TDL-S3-009` 已完成）
  - [x] 补齐“更完整绩效指标 + 成本/滑点模型”收口项（`TDL-S3-010` + `TDL-S3-011` 已完成）
  - [ ] `S3 final` 从 `in_progress/PARTIAL_PASS` 进入可收口状态

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

- 卡状态：`Active`
- 代码/测试证据：analysis 最小闭环已落地，测试存在
- 未完成项（执行卡/规格层面）：
  - [ ] 窗口级归因证据收口（卡片明确未 completed）
  - [ ] `signal/execution/cost` 三分解结论稳定性复核（不仅单窗口）
- 关键一致性漂移（必须处理）：
  - [x] 已完成事实口径统一：`Governance/specs/spiral-s3b/final.md`、`Governance/record/development-status.md`、`Governance/record/debts.md` 已同步为 `remaining_failures=0`、`integrated_days=20`（证据：`artifacts/spiral-s3b/20260213/s3e_targeted_clearance_summary.json`）。

## 3.5 S3c

- 卡状态：`Active`
- 代码/测试证据：`--strict-sw31` + `irs --require-sw31` 与测试已落地
- 未完成项：
  - [ ] 从“单窗口通过（20260219）”升级到“跨窗口稳定性复核并收口”
  - [ ] 与 S3b 节奏对齐后将 `spiral-s3c/final.md` 从 `in_progress` 推进

## 3.6 S3d

- 卡状态：`Active`
- 代码/测试证据：CLI 参数、adaptive、future_returns probe 合同测试已存在
- 未完成项：
  - [ ] 窗口级 run/test/artifact/review/sync 五件套收口（当前仅“CLI阻断解除”）
  - [x] `future_returns` 实跑证据已补齐并固化：`artifacts/spiral-s3d/20260119_20260213/mss_probe_return_series_report.md`

## 3.7 S3e

- 卡状态：`Active`
- 代码/测试证据：validation 子命令、dual-window、OOS、run_manifest 已落地
- 未完成项：
  - [ ] 窗口级证据收口与 `final.md` 由 `in_progress` 转完成
  - [x] 与 S3b 的“残留 FAIL 是否清零”口径统一（同 3.4，已同步 `remaining_failures=0`）

## 3.8 S3r

- 卡状态：`Planned`（条件触发）
- 代码/测试证据：`eq backtest --repair s3r` 已可执行
- 未完成项：
  - [ ] 未触发即不执行；仅在 S3 gate=FAIL 时进入
  - [ ] 一旦触发需补齐 `s3r_patch_note/s3r_delta_report/review/final`

---

## 4. 下一步执行顺序（与现有路线图不冲突）

1. `S3`：推进未收口条目（细撮合规则、绩效指标、成本/滑点）并保持“有效交易日前置校验”。
2. `S3b`：完成口径统一与窗口级归因收口（含 20/20 覆盖事实同步）。
3. `S3c`：完成跨窗口稳定性复核并收口。
4. `S3d`：补齐 probe 真实收益窗口证据并收口。
5. `S3e`：补齐生产校准窗口证据并收口。
6. `S4b`：以上三圈收口后再进入防御参数校准。
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
