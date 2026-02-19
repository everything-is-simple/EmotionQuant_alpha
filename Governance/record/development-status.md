# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-19  
**当前版本**: v4.15（S3ar 口径修订：先收口双 TuShare 主备与 DuckDB 锁恢复，AK/Bao 预留）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S3 执行中，S4 已收口完成：下一圈先执行 S3ar（采集稳定性修复），再进入 S3b 收益归因验证闭环**

- S0a（统一入口与配置注入）: 已完成并补齐 6A 证据链。
- S0b（L1 采集入库闭环）: 已完成并补齐 6A 证据链。
- S0c（L2 快照与失败链路）: 已完成并补齐 6A 证据链。
- S1a（MSS 最小评分可跑）: 已完成并补齐 6A 证据链。
- S1b（MSS 消费验证闭环）: 已完成并补齐 6A 证据链。
- S2a（IRS + PAS + Validation 最小闭环）: 已完成并补齐 6A 证据链。
- S2b（MSS+IRS+PAS 集成推荐闭环）: 已完成并补齐 6A 证据链。
- S2c（核心算法深化闭环）: 已完成并收口（含证据冲突清障、release/debug 分流、closeout 文档补齐与同步）。

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
| S3a | ENH-10 数据采集增强闭环 | ✅ 已完成 | 已接入真实 TuShare 客户端，实测吞吐与失败恢复证据齐备 |
| S3 | 回测闭环 | 🔄 进行中 | 已扩展多交易日回放并落地板块化涨跌停阈值 |
| S4 | 纸上交易闭环 | ✅ 已完成 | 完成跨日持仓回放与跌停次日重试证据闭环，`go_nogo=GO` |
| S3ar | 采集稳定性修复圈（双 TuShare 主备 + 锁恢复，AK/Bao 预留） | 🔄 进行中 | 修复历史回填阻断项，确保归因窗口数据可复现 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |
| S7a | ENH-11 自动调度闭环 | 📋 未开始 | 依赖 S6 完成 |

---

## 下一步（S3ar -> S3b）

1. 先完成 S3ar：落地双 TuShare 主备链路（10000 网关主 + 5000 官方兜底）、独立限速口径与 DuckDB 锁恢复门禁。
2. 在 S3ar 收口文档中登记 AKShare/BaoStock 为最后底牌预留（不在当前圈实装）。
3. 验证历史窗口可稳定落袋后，启动 S3b：完成 A/B/C 对照与实盘-回测偏差三分解（signal/execution/cost）。
4. 形成收益来源结论并驱动 S4b 参数；继续补齐更细撮合规则（一字板/流动性枯竭）并沉淀可回放证据。

---

## 风险提示

1. S0c 行业快照为“全市场聚合”最小实现，尚未接入 SW 行业粒度聚合。
2. 真实采集链路已接入，仍需持续观测长窗口吞吐与限频稳定性。
3. 若 `validation_weight_plan` 桥接链路缺失或不可审计，必须阻断 S2c->S3a/S3/S4 迁移。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
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
