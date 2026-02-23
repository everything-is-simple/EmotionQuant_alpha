# EmotionQuant 可复用资产登记表（Spiral 版）

**最后更新**: 2026-02-23  
**版本**: v2.29  
**范围**: S0-S6

---

## 分级定义

| 等级 | 说明 |
|---|---|
| S | 可直接复用、稳定 |
| A | 可复用，但需少量适配 |
| B | 结构可参考，需较大改造 |

---

## 治理与流程资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| S-GOV-001 | Spiral 主控路线图 | `Governance/Capability/SPIRAL-CP-OVERVIEW.md` | S | 圈级目标、CP 组合、最小同步 |
| S-GOV-002 | CP 能力包模板 | `Governance/Capability/CP-*.md` | S | 契约/Slice/Gate 复用 |
| S-GOV-003 | Task 闭环卡片模板 | `Governance/Capability/SPIRAL-TASK-TEMPLATE.md` | S | 每日任务拆解 |
| S-GOV-004 | 统一 6A 工作流 | `Governance/steering/6A-WORKFLOW.md` | S | Spiral 到 Task 到 Step 一体执行 |
| S-GOV-005 | 6A 历史兼容说明 | `Governance/steering/6A-WORKFLOW.md` | A | 回溯历史口径（已并入主工作流），不参与当前执行 |
| S-GOV-006 | 命名契约变更模板 | `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` | S | 契约变更单点归档与审计 |
| S-GOV-007 | 跨文档联动模板 | `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md` | S | 变更影响面同步 |
| A-GOV-008 | 质量门禁 CI 工作流 | `.github/workflows/quality-gates.yml` | A | contracts/governance 自动化检查 |
| S-GOV-009 | S0a/S0b/S0c 6A 证据档案模板 | `Governance/specs/spiral-s0a/*` + `Governance/specs/spiral-s0b/*` + `Governance/specs/spiral-s0c/*` | S | requirements/review/final 与样例证据可复用 |
| S-GOV-010 | S1a 6A 证据档案模板 | `Governance/specs/spiral-s1a/*` | S | MSS 圈 requirements/review/final 与样例证据复用 |
| S-GOV-011 | S1b 6A 证据档案模板 | `Governance/specs/spiral-s1b/*` | S | MSS 消费验证圈 requirements/review/final 与样例证据复用 |
| S-GOV-012 | S2a 6A 证据档案模板 | `Governance/specs/spiral-s2a/*` | S | IRS/PAS/Validation 圈 requirements/review/final 与样例证据复用 |
| S-GOV-013 | S2b 6A 证据档案模板 | `Governance/specs/spiral-s2b/*` | S | Integration 圈 requirements/review/final 与样例证据复用 |
| S-GOV-014 | S3a 6A 证据档案模板 | `Governance/specs/spiral-s3a/*` | S | ENH-10 圈 requirements/review/final 与门禁证据骨架复用 |
| S-GOV-015 | S2c 6A 阶段证据模板 | `Governance/specs/spiral-s2c/*` | A | 桥接硬门禁子步与 full 语义收口证据复用 |
| S-GOV-016 | S3ar 6A 证据档案模板 | `Governance/specs/spiral-s3ar/*` | S | 采集稳定性修复圈 requirements/review/final 与门禁证据骨架复用 |
| S-GOV-017 | S3ar 执行卡模板 | `Governance/SpiralRoadmap/planA/execution-cards/S3AR-EXECUTION-CARD.md` | S | 双 TuShare 主备与 DuckDB 锁恢复 run/test/artifact/review/sync 合同复用 |
| S-GOV-018 | S2r 6A 修复子圈证据模板 | `Governance/specs/spiral-s2r/*` | S | FAIL 修复场景下 requirements/review/final 与 patch/delta 证据口径复用 |

---

## 设计资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| S-DES-001 | 系统总览（Spiral） | `docs/system-overview.md` | S | 架构基线 |
| S-DES-002 | 模块索引 | `docs/module-index.md` | S | 设计导航 |
| S-DES-003 | 命名契约 Schema | `docs/naming-contracts.schema.json` | S | 枚举/阈值机器可读单源 |
| S-DES-004 | 命名契约术语表 | `docs/naming-contracts-glossary.md` | S | 名词与边界统一 |
| S-DES-007 | TuShare 主备通道策略文档 | `docs/reference/tushare/tushare-channel-policy.md` | S | 10000 主 + 5000 兜底 + 限速口径统一 |
| A-DES-005 | 回测选型策略 | `docs/design/core-infrastructure/backtest/backtest-engine-selection.md` | A | 引擎替换决策 |
| A-DES-006 | 因子/权重验证设计 | `docs/design/core-algorithms/validation/*` | A | 验证模块落地 |

---

## 代码与配置资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| A-CFG-001 | Python 项目依赖分层 | `pyproject.toml` | A | 主依赖与可选依赖管理 |
| A-CFG-002 | 运行依赖清单 | `requirements.txt` | A | 快速环境安装 |
| S-QA-003 | 本地一致性检查脚本 | `scripts/quality/local_quality_check.py` | S | contracts/governance 本地门禁 |
| S-QA-004 | 契约行为回归脚本 | `scripts/quality/contract_behavior_regression.py` | S | 边界行为固定回归 |
| S-QA-005 | 设计溯源检查脚本 | `scripts/quality/design_traceability_check.py` | A | 检查 MSS/IRS/PAS/Validation/Integration 等核心模块 `DESIGN_TRACE` 标记，降低设计-实现漂移 |
| S-QA-006 | S2c release 证据同步脚本 | `scripts/quality/sync_s2c_release_artifacts.py` | S | 同步前强校验 PASS/GO 与样例行数，防止调试证据污染正式收口 |
| A-QA-007 | TuShare L1 吞吐压测脚本 | `scripts/data/benchmark_tushare_l1_rate.py` | A | 统一输出 calls/min、成功率、延迟分位与错误类型，作为主备通道实测证据 |
| A-QA-009 | S3ar 实网验真证据样例集 | `artifacts/token-checks/tushare_l1_token_check_20260220-*.json` + `artifacts/token-checks/tushare_l1_rate_benchmark_20260220-*.json` + `artifacts/spiral-s3a/20260213/*` | A | 作为后续圈复跑时的证据口径对照样本（主备可用性、限速、窗口采集） |
| A-QA-008 | Unit 环境隔离夹具（全局） | `tests/unit/conftest.py` + `tests/unit/pipeline/conftest.py` + `tests/unit/data/conftest.py` | A | 切断宿主 `.env` 与 `TUSHARE_*`/路径配置对 unit 测试污染，恢复门禁稳定性 |
| A-CODE-005 | 统一 CLI 入口骨架 | `src/pipeline/main.py` + `main.py` | A | 统一入口、参数路由、配置注入 |
| A-CODE-006 | L1 采集最小闭环骨架 | `src/data/fetcher.py` + `src/data/l1_pipeline.py` + `src/data/repositories/*` | A | S0b 数据采集、落库、产物输出 |
| A-CODE-007 | L2 快照与 canary 最小闭环骨架 | `src/data/l2_pipeline.py` + `src/data/models/snapshots.py` | A | S0c 快照生成、质量字段门禁、错误分级 |
| A-CODE-037 | Data Readiness 持久化与阈值配置基座 | `src/data/quality_store.py` + `src/data/l1_pipeline.py` + `src/data/l2_pipeline.py` + `src/config/config.py` | A | 提供 `system_config/data_quality_report/data_readiness_gate` 落库与 `flat_threshold/min_coverage_ratio/stale_hard_limit_days` 配置化 |
| A-TEST-008 | S0 合同测试集 | `tests/unit/pipeline/test_cli_entrypoint.py` + `tests/unit/data/test_fetcher_contract.py` + `tests/unit/data/test_l1_repository_contract.py` + `tests/unit/data/test_snapshot_contract.py` + `tests/unit/data/test_s0_canary.py` | A | 入口/L1/L2 合同回归保障 |
| A-TEST-038 | S0c 门禁持久化与阈值合同测试集 | `tests/unit/data/test_data_readiness_persistence_contract.py` + `tests/unit/data/test_flat_threshold_config_contract.py` | A | 固化 `data_readiness` 落库契约与 `flat_threshold` 统计口径契约 |
| A-CODE-009 | MSS 最小评分骨架 | `src/algorithms/mss/engine.py` + `src/algorithms/mss/pipeline.py` + `src/pipeline/main.py` | A | S1a 的 `eq mss` 计算、落库、产物输出 |
| A-TEST-010 | MSS 合同测试集 | `tests/unit/algorithms/mss/test_mss_contract.py` + `tests/unit/algorithms/mss/test_mss_engine.py` | A | MSS 输出字段与评分边界回归保障 |
| A-CODE-011 | MSS 探针与消费器骨架 | `src/algorithms/mss/probe.py` + `src/integration/mss_consumer.py` + `src/pipeline/main.py` | A | S1b 的 `eq mss-probe` 消费验证与证据生成 |
| A-TEST-012 | MSS 探针/集成消费合同测试集 | `tests/unit/algorithms/mss/test_mss_probe_contract.py` + `tests/unit/integration/test_mss_integration_contract.py` | A | MSS 输出可消费性与探针指标回归保障 |
| A-CODE-013 | S2a 推荐编排与三表最小闭环骨架 | `src/algorithms/irs/pipeline.py` + `src/algorithms/pas/pipeline.py` + `src/algorithms/validation/pipeline.py` + `src/pipeline/recommend.py` | A | S2a 的 `eq recommend --mode mss_irs_pas --with-validation` |
| A-TEST-014 | S2a 合同测试集 | `tests/unit/algorithms/irs/test_irs_contract.py` + `tests/unit/algorithms/pas/test_pas_contract.py` + `tests/unit/integration/test_validation_gate_contract.py` | A | IRS/PAS/Validation 输出契约回归保障 |
| A-CODE-015 | S2b 集成推荐与质量门完整实现 | `src/integration/pipeline.py` + `src/pipeline/recommend.py` + `src/pipeline/main.py` | A | S2b 的 `eq recommend --mode integrated`，覆盖四模式集成与推荐硬约束（每日<=20/行业<=5） |
| A-TEST-016 | S2b 合同测试集 | `tests/unit/integration/test_integration_contract.py` + `tests/unit/integration/test_quality_gate_contract.py` + `tests/unit/pipeline/test_cli_entrypoint.py` | A | Integration/Quality Gate/CLI 路径回归保障 |
| A-CODE-017 | S2c Validation-Integration 桥接硬门禁实现 | `src/algorithms/validation/pipeline.py` + `src/integration/pipeline.py` + `src/pipeline/recommend.py` + `src/pipeline/main.py` | A | `selected_weight_plan -> validation_weight_plan -> integrated_recommendation` 契约落地 |
| A-TEST-018 | S2c 桥接与语义回归测试集 | `tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py` + `tests/unit/integration/test_validation_weight_plan_bridge.py` + `tests/unit/integration/test_algorithm_semantics_regression.py` | A | 桥接一致性、Gate 阻断、关键语义边界回归 |
| A-CODE-019 | MSS zscore 语义实现与中间产物输出 | `src/algorithms/mss/engine.py` + `src/algorithms/mss/pipeline.py` | A | `ratio->zscore->[0,100]` + 缺失回退 50 + `mss_factor_intermediate` 证据 |
| A-TEST-020 | MSS full 语义合同测试 | `tests/unit/algorithms/mss/test_mss_full_semantics_contract.py` | A | 六因子温度公式与缺失回退 50 行为回归 |
| A-CODE-021 | IRS full 语义实现与中间产物输出 | `src/algorithms/irs/pipeline.py` | A | 六因子评分 + 轮动状态 + 配置建议 + `irs_factor_intermediate` 证据 |
| A-CODE-022 | PAS full 语义实现与中间产物输出 | `src/algorithms/pas/pipeline.py` | A | 三因子评分 + `effective_risk_reward_ratio` + `pas_factor_intermediate` 证据 |
| A-CODE-023 | Validation full 语义实现（五件套） | `src/algorithms/validation/pipeline.py` | A | 因子验证 + Walk-Forward 权重验证 + Gate 决策 + `validation_run_manifest` |
| A-TEST-024 | S2c full 语义合同测试集 | `tests/unit/algorithms/irs/test_irs_full_semantics_contract.py` + `tests/unit/algorithms/pas/test_pas_full_semantics_contract.py` + `tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py` + `tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py` | A | IRS/PAS/Validation full 语义回归保障 |
| A-CODE-025 | S2c 证据车道隔离能力 | `src/pipeline/main.py` + `src/pipeline/recommend.py` + `src/algorithms/irs/pipeline.py` + `src/algorithms/pas/pipeline.py` + `src/algorithms/validation/pipeline.py` | A | `release/debug` 双车道，避免测试/演练覆盖正式证据 |
| A-TEST-026 | S2c 证据隔离与同步校验测试 | `tests/unit/pipeline/test_recommend_evidence_lane.py` + `tests/unit/scripts/test_sync_s2c_release_artifacts.py` | A | 保证 lane 分流与 release 同步前置校验行为稳定 |
| A-CODE-027 | S3a 采集增强实现（收口版） | `src/data/fetcher.py` + `src/data/fetch_batch_pipeline.py` + `src/data/l1_pipeline.py` + `src/pipeline/main.py` | A | 真实 TuShare 适配、实测吞吐基准、失败批次真实重跑恢复与非交易日门禁兼容 |
| A-TEST-028 | S3a 合同与 CLI 回归测试集（收口版） | `tests/unit/data/test_fetcher_contract.py` + `tests/unit/data/test_fetch_batch_contract.py` + `tests/unit/data/test_fetch_resume_contract.py` + `tests/unit/data/test_fetch_retry_contract.py` + `tests/unit/data/test_l1_repository_contract.py` + `tests/unit/pipeline/test_cli_entrypoint.py::test_main_fetch_batch_status_and_retry` | A | 保证 S3a 真实/离线双模式、吞吐证据与恢复链路契约稳定 |
| A-CODE-029 | S3 回测输入准备与消费门禁实现 | `src/backtest/pipeline.py` + `src/pipeline/main.py` | A | 消费 S3a `fetch_progress` + Integration/Validation 桥接校验 + 回测最小产物输出 |
| A-TEST-030 | S3 Backtest 合同与可复现测试集 | `tests/unit/backtest/test_backtest_contract.py` + `tests/unit/backtest/test_validation_integration_bridge.py` + `tests/unit/backtest/test_backtest_reproducibility.py` + `tests/unit/pipeline/test_cli_entrypoint.py::test_main_backtest_runs_with_s3a_consumption` | A | 保证 S3 消费链路、桥接阻断与可复现性 |
| A-CODE-031 | S3 多交易日回放与 A 股执行细节实现 | `src/backtest/pipeline.py` | A | 按交易日历执行 T+1、涨停买入拒绝、跌停卖出阻断、费用与权益曲线计算 |
| A-TEST-032 | S3 T+1/涨跌停执行细节测试 | `tests/unit/backtest/test_backtest_t1_limit_rules.py` | A | 保证多日回放与 A 股执行约束行为稳定 |
| A-CODE-033 | S4 paper trade 消费链与门禁实现 | `src/trading/pipeline.py` + `src/pipeline/main.py` | A | 复用 S3 consumption/gate 证据链，输出订单/持仓/风控样例产物 |
| A-TEST-034 | S4 交易链路合同测试集 | `tests/unit/trading/support.py` + `tests/unit/trading/test_order_pipeline_contract.py` + `tests/unit/trading/test_position_lifecycle_contract.py` + `tests/unit/trading/test_risk_guard_contract.py` + `tests/unit/pipeline/test_cli_entrypoint.py::test_main_trade_runs_paper_mode` | A | 保证 S4 订单、持仓生命周期与风控守卫契约稳定；收口样例证据见 `artifacts/spiral-s4/20260222/manual_test_summary.md` |
| A-CODE-035 | DuckDB 锁恢复与 `trade_date` 幂等覆盖写入基座 | `src/data/repositories/base.py` + `src/data/l1_pipeline.py` | A | 在 L1 写入链路统一提供锁重试、PID 审计、等待时长统计与覆盖写入能力 |
| A-TEST-036 | S3ar 锁恢复/幂等写入合同测试 | `tests/unit/data/test_duckdb_lock_recovery_contract.py` | A | 校验“锁冲突可恢复/耗尽可审计/同 trade_date 不重复写入”三类契约 |
| A-CODE-039 | S3/S4 历史库 schema 兼容写入基座 | `src/backtest/pipeline.py` + `src/trading/pipeline.py` | A | 兼容旧 `backtest_results/trade_records` 缺列场景，避免实跑因表结构漂移崩溃 |
| A-TEST-040 | S3/S4 schema 兼容合同测试集 | `tests/unit/backtest/test_backtest_schema_compat_contract.py` + `tests/unit/trading/test_backtest_status_schema_compat_contract.py` | A | 固化“旧表可读可写、缺列不崩溃”的兼容契约 |
| A-CODE-041 | Validation decay 单调代理实现 | `src/algorithms/validation/pipeline.py` | A | 修复 `decay_5d` 与 `|IC|` 关系反向问题，确保强信号不会被反向惩罚 |
| A-TEST-042 | Validation decay 单调性测试 | `tests/unit/algorithms/validation/test_decay_proxy_contract.py` | A | 固化 decay 代理与 `|IC|` 单调关系，防止回归 |
| A-CODE-043 | S3c CLI 门禁/消费产物写入器 | `src/pipeline/main.py` | A | 在 `eq irs --require-sw31` 路径固化 `gate_report/consumption` 契约，保证执行卡产物与代码一致 |
| A-CODE-044 | L2 质量上下文初始化受控回退 | `src/data/l2_pipeline.py` | A | 避免 `run --to-l2` 在质量上下文初始化阶段因 IO 异常直接抛栈中断 |
| A-TEST-045 | S3c CLI 产物契约回归测试 | `tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline` | A | 固化 `s3c_irs` 输出 `gate_status/go_nogo/gate_report_path/consumption_path` 契约 |
| A-CODE-046 | S3 回测无可开仓窗口 WARN 语义实现 | `src/backtest/pipeline.py` | A | 将“无可开仓信号”从 P0 阻断改为可审计 WARN，固定窗口不再被误阻断 |
| A-CODE-047 | S3b 空样本 N/A 警告实现 | `src/analysis/pipeline.py` | A | 对 live/backtest 双侧无成交样本输出 N/A 警告并保持 GO，避免误判 FAIL |
| A-CODE-048 | Integration 旧表数值列类型修复器 | `src/integration/pipeline.py` | A | 自动修复 `integrated_recommendation` 旧表数值列为 DOUBLE（含 `position_size`），避免整型截断 |
| A-TEST-049 | S3 回测无可开仓窗口合同测试 | `tests/unit/backtest/test_backtest_contract.py::test_backtest_no_long_entry_signal_window_is_warn_not_fail` | A | 固化固定窗口 `total_trades=0` 时的 WARN/GO 契约 |
| A-TEST-050 | S3b 空样本 N/A 语义测试 | `tests/unit/analysis/test_live_backtest_deviation_contract.py::test_live_backtest_deviation_empty_both_sides_is_warn` + `tests/unit/analysis/test_attribution_summary_contract.py::test_attribution_summary_no_filled_trade_is_warn` | A | 固化偏差/归因在无成交样本场景的 WARN/GO 契约 |
| A-TEST-051 | Integration 旧表类型修复回归测试 | `tests/unit/integration/test_integration_contract.py::test_s2b_repairs_legacy_position_size_integer_schema` | A | 固化 `position_size` 旧整型表自动修复并恢复小数仓位能力 |
| A-QA-052 | S3b 优先级串行重跑器 | `scripts/quality/rerun_s3b_priority.py` | A | 支持按优先级 CSV 串行执行 `run/mss/irs/recommend`，并落盘失败归因与摘要 |
| A-TEST-053 | S3e neutral soft-gate 契约测试 | `tests/unit/algorithms/validation/test_neutral_regime_soft_gate_contract.py` | A | 固化 `regime + dual-window + neutral` 场景下 `factor_gate_raw=FAIL` 到决策 `WARN` 的审计契约 |
| A-TEST-054 | CLI `pas` 与 validation 参数透传测试 | `tests/unit/pipeline/test_cli_entrypoint.py::test_main_pas_command_wires_to_pipeline` + `tests/unit/pipeline/test_cli_entrypoint.py::test_main_recommend_forwards_validation_mode_flags` + `tests/unit/pipeline/test_recommend_evidence_lane.py::test_integrated_bridge_validation_defaults_to_s3e_modes` | A | 固化 `pas` 子命令与 `recommend` 的 S3e 参数透传/默认值契约 |
| A-CODE-055 | S4r/S4br 修复子圈执行资产 | `src/trading/pipeline.py` + `src/stress/pipeline.py` + `src/pipeline/main.py` | A | 落地 `trade --repair s4r` 与 `stress --repair s4br`，统一输出 patch/delta 审计产物并透传 CLI 事件 |
| A-TEST-056 | S4r/S4br 修复子圈合同测试资产 | `tests/unit/trading/test_order_pipeline_contract.py` + `tests/unit/trading/test_deleveraging_policy_contract.py` + `tests/unit/trading/test_backtest_status_schema_compat_contract.py` + `tests/unit/pipeline/test_cli_entrypoint.py` | A | 固化修复子圈 patch/delta 产物契约与 legacy `trade_records` 自动补列写入兼容契约 |
| A-CODE-057 | S5 GUI 最小闭环代码资产 | `src/gui/app.py` + `src/pipeline/main.py` | A | 落地 `eq gui` 子命令与 `--export daily-report` 导出链路，输出 manifest/gate/consumption 审计产物 |
| A-TEST-058 | S5 GUI 最小闭环测试资产 | `tests/unit/gui/test_gui_launch_contract.py` + `tests/unit/gui/test_gui_readonly_contract.py` + `tests/unit/analysis/test_daily_report_export_contract.py` | A | 固化 GUI 启动契约、DuckDB 只读访问契约与 daily-report 导出契约 |

---

## 当前空缺（需后续沉淀）

1. 可复用 IRS 全覆盖门禁审计器（目标 S3c）
2. 可复用验证报告生成器（目标 S1/S2）
3. 可复用回测基线 Runner（目标 S3）
4. `local_quality_check` 结果自动归档器（目标 S2/S3）
5. MSS 自适应分位阈值基线生成器（目标 S3）
6. Probe 真实收益口径桥接器（目标 S3）
7. IRS/PAS 评分校准器（目标 S3）
8. 采集多源底牌适配器（AKShare/BaoStock）与 `eq` 入口环境自检脚本资产（目标 S3ar-next/S3b）

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-23 | v2.31 | 新增 S5 GUI 最小闭环代码/测试资产（A-CODE-057、A-TEST-058） |
| 2026-02-23 | v2.30 | S3b 收口一致性同步：本次仅执行 `review/final` 与看板口径对齐，无新增可复用代码/测试资产 |
| 2026-02-23 | v2.29 | 新增 S4r/S4br 修复子圈代码与测试资产（A-CODE-055、A-TEST-056） |
| 2026-02-22 | v2.28 | 新增 S3b 优先级串行重跑器（A-QA-052）与 S3e 软门/CLI 透传测试资产（A-TEST-053~054） |
| 2026-02-21 | v2.27 | 新增 S3/S3b 固定窗口解锁资产（A-CODE-046、A-CODE-047）与 Integration 旧表类型修复资产（A-CODE-048），并补齐对应合同测试（A-TEST-049~051） |
| 2026-02-21 | v2.26 | 新增 S3c CLI 产物契约资产（A-CODE-043、A-TEST-045）与 L2 初始化受控回退资产（A-CODE-044） |
| 2026-02-21 | v2.25 | 新增 S3/S4 历史 schema 兼容资产（A-CODE-039、A-TEST-040）与 Validation decay 单调口径资产（A-CODE-041、A-TEST-042） |
| 2026-02-21 | v2.24 | 新增 S2r 规格资产模板（S-GOV-018）；将 A-CODE-015 升级为完整语义口径（四模式 + 推荐硬约束） |
| 2026-02-21 | v2.23 | 新增 S0c-R1 资产：`quality_store` 持久化基座（A-CODE-037）与门禁持久化/阈值合同测试集（A-TEST-038）；空缺项由 SW 映射聚合转为 IRS 全覆盖门禁审计器 |
| 2026-02-20 | v2.22 | 新增 S3ar 实网验真证据样例集资产（A-QA-009），用于主备可用性/限速/窗口采集证据复用对照 |
| 2026-02-20 | v2.21 | 新增 unit 环境隔离夹具资产（A-QA-008）与 S3ar 锁恢复/幂等写入代码测试资产（A-CODE-035、A-TEST-036） |
| 2026-02-19 | v2.20 | 新增 TuShare 主备通道策略文档资产（S-DES-007）与吞吐压测脚本资产（A-QA-007）；将 AK/Bao 空缺调整为 S3ar-next 预留 |
| 2026-02-19 | v2.19 | 新增 S3ar 资产登记：`Governance/specs/spiral-s3ar/*` 与 `Governance/SpiralRoadmap/planA/execution-cards/S3AR-EXECUTION-CARD.md`；补充“多源兜底与锁恢复”空缺项 |
| 2026-02-18 | v2.18 | 更新 S4 测试资产说明：补充收口样例证据入口（`artifacts/spiral-s4/20260222/manual_test_summary.md`） |
| 2026-02-17 | v2.17 | 升级 S3a 资产登记为收口版：纳入真实 TuShare 适配、实测吞吐与失败恢复实测相关代码/测试资产 |
| 2026-02-17 | v2.16 | 增加 S3 多交易日回放与 T+1/涨跌停资产（A-CODE-031、A-TEST-032）及 S4 paper trade 资产（A-CODE-033、A-TEST-034） |
| 2026-02-17 | v2.15 | 增加 S3 回测输入准备与消费门禁资产（A-CODE-029）及 Backtest 合同/可复现测试资产（A-TEST-030） |
| 2026-02-17 | v2.14 | 增加 S3a 采集增强实现与测试资产（A-CODE-027、A-TEST-028） |
| 2026-02-17 | v2.13 | 增加 S2c release 同步脚本资产（S-QA-006）与证据车道隔离代码/测试资产（A-CODE-025、A-TEST-026） |
| 2026-02-17 | v2.12 | 增加 IRS/PAS/Validation full 语义实现与测试资产（A-CODE-021/022/023、A-TEST-024），并更新 S-QA-005 覆盖范围 |
| 2026-02-17 | v2.11 | 增加设计溯源检查资产（S-QA-005）与 MSS 语义实现/测试资产（A-CODE-019、A-TEST-020） |
| 2026-02-17 | v2.10 | 增加 S2c 阶段证据模板（S-GOV-015）与桥接硬门禁实现/测试资产（A-CODE-017、A-TEST-018） |
| 2026-02-16 | v2.9 | 增加 S3a 证据模板资产登记（S-GOV-014） |
| 2026-02-15 | v2.8 | 增加 S2b 证据模板与 Integration/Quality Gate 代码测试资产登记 |
| 2026-02-15 | v2.7 | 增加 S2a 证据模板与推荐编排/三表合同资产登记 |
| 2026-02-15 | v2.6 | 增加 S1b 证据模板与 MSS 探针/集成消费资产登记 |
| 2026-02-15 | v2.5 | 增加 S1a 证据模板与 MSS 代码/测试资产登记 |
| 2026-02-15 | v2.4 | 增加 S0c L2/canary 资产与 S0 全链路合同测试资产登记 |
| 2026-02-15 | v2.3 | 增加 S0a/S0b 6A 证据档案资产与 CLI/L1 合同资产登记 |
| 2026-02-14 | v2.2 | 新增命名契约与质量门禁资产（schema/glossary/templates/local-check/CI workflow）；补齐当前空缺 |
| 2026-02-12 | v2.1 | 路径整理：S-GOV-005 从失效归档目录切换为 `6A-WORKFLOW.md` 历史兼容说明入口 |
| 2026-02-07 | v2.0 | 重建为 Spiral 资产清单，移除旧线性 Task 占位口径 |
| 2026-02-05 | v1.4 | 线性阶段资产登记版本 |
