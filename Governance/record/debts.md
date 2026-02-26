# EmotionQuant 技术债登记表（Spiral 版）

**最后更新**: 2026-02-26  
**版本**: v1.51  
**范围**: S0-S6

---

## 分级标准

| 优先级 | 定义 | 处理时限 |
|---|---|---|
| P0 | 阻断实现或造成错误决策 | 立即 |
| P1 | 影响核心闭环质量 | 当圈或下一圈 |
| P2 | 影响效率/可维护性 | 2-3 圈内 |
| P3 | 优化项 | 视资源安排 |

---

## 当前债务清单

| ID | 问题 | 优先级 | 影响 | 计划处理圈 | 状态 |
|---|---|---|---|---|---|
| TD-S0-002 | ~~Validation 生产级真实收益口径与统计校准~~ | P2 | 影响 S3 回测与实盘前解释力一致性 | S3e | ✅ 已清償 |
| TD-S0-005 | ~~仓库内仍有部分 `Phase` 历史措辞（设计参考文档）~~ | P2 | 容易带回线性心智 | S0-S2 | ✅ 已清償 |
| TD-S2C-019 | ~~`recommend --with-validation-bridge` 在 `mss_factor_intermediate` 仅 Parquet 单日覆盖场景会报 `source_missing`，即便 integrated 已产出也返回 failed~~ | P1 | 影响桥接证据一致性与命令退出码稳定性，干扰自动化编排 | S2c-S3b | ✅ 已清償 |
| TD-S3A-015 | ~~AKShare/BaoStock 适配器骨架已存在但未接入主链、无自动化测试~~ | P2 | 极端情况下对 TuShare 双通道仍存在单生态依赖 | S6 | ✅ 已清償 |
| TD-ARCH-001 | 设计文档定义 OOP（Calculator/Repository），代码采用 Pipeline + DuckDB 直写 | P2 | 设计-代码架构认知偏差；已决策选项B（文档对齐代码） | -- | ✅ 已决策 |
| TD-DA-009 | Enum 设计-实现对齐缺口（3 个类名偏差、 4 个设计枚举缺失、 4 个成员名偏差） | P3 | 设计文档与代码枚举不一致，长期维护歧义 | S6 | ? 待处理 |
| TD-GOV-012 | ~~`DESIGN_TRACE` 已扩展到 S3 Backtest 与 S4 Trading 核心模块，但仍未覆盖全仓核心代码~~ | P2 | 仍可能存在“实现无设计溯源标记”的盲区 | S3-S4 | ✅ 已清償 |
| TD-DA-001 | ~~Calculator/Repository 类不存在（设计定义各模块 Calculator/Repository，但实现为函数式 API）~~ | P2 | 可测试性/可替换性下降 | S6 | ✅ 已清償 |
| TD-DA-002 | ~~Enum 类不存在~~ | P2 | 类型安全缺失 | S6 | ✅ 已清償 |
| TD-DA-003 | ~~输出模型命名偏差~~ | P2 | 跨模块接口理解成本 | S6 | ✅ 已清償 |
| TD-DA-004 | ~~DuckDB 工具函数重复~~ | P2 | 维护成本高 | S6 | ✅ 已清償 |
| TD-DA-005 | ~~PAS discount 字段未持久化（`liquidity_discount`/`tradability_discount` 计算后丢弃）~~ | P2 | 诊断/回测解释力不足 | S6 | ✅ 已清償 |
| TD-DA-006 | ~~Validation 丰富 API 未实现（设计 12 接口 vs 仅 `run_validation_gate()`）~~ | P2 | 高级验证能力缺失 | S6 | ✅ 已清償 |
| TD-DA-007 | ~~Integration 模式文档缺失（`dual_verify`/`complementary` 代码已实现但设计未定义）~~ | P2 | 文档-代码不一致 | S6 | ✅ 已清償 |
| TD-DA-008 | ~~MSS `mss_score` 冗余字段~~ | P2 | 语义冗余/迁移成本 | S6 | ✅ 已清償 |

---

## 已清偿

| ID | 问题 | 完成时间 | 说明 |
|---|---|---|---|
| TD-S0-001 | 尚未形成 S0 可运行最小闭环（命令+测试+产物） | 2026-02-15 | S0a/S0b/S0c 已完成 run/test/artifact/review/sync，6A 证据归档至 `Governance/specs/spiral-s0a`、`Governance/specs/spiral-s0b`、`Governance/specs/spiral-s0c` |
| TD-S0-003 | 权重验证模块仅设计未实现 | 2026-02-17 | S2c 已在 `src/algorithms/validation/pipeline.py` 落地 Walk-Forward 权重验证与 Gate 决策，并由 `test_weight_validation_walk_forward_contract.py` 覆盖 |
| TD-S2-009 | IRS/PAS 当前使用最小启发式评分，未接入完整行业映射与收益校准 | 2026-02-17 | S2c 已完成 IRS/PAS full 语义实现与合同测试；后续生产级收益校准由 `TD-S0-002` 跟踪 |
| TD-S0-006 | S0c 行业快照暂为全市场聚合，未接入 SW 行业映射聚合 | 2026-02-21 | S0c-R1 已完成 SW31 严格门禁与映射落地，`industry_snapshot` 不再回落 `ALL` 作为默认主路径；新增持久化与门禁契约测试收口 |
| TD-S0-004 | S3 更细撮合规则与执行成本模型未完善（历史债务） | 2026-02-22 | 已完成一字板/流动性枯竭显式拒单、绩效指标落库、分层费率与冲击成本模型落地，并补齐成本契约测试 |
| TD-S3-017 | S3d/S3e 执行卡目标命令尚未完全落地（缺 `eq validation` 子命令与 MSS adaptive/probe 参数契约） | 2026-02-21 | 已落地 `eq validation` 与 MSS `--threshold-mode/--return-series-source`，并补齐 5 条目标合同测试 |
| TD-S1-007 | MSS 当前采用固定阈值（30/45/60/75），未实现自适应分位阈值 | 2026-02-21 | MSS CLI 已支持 `threshold-mode`，并产出阈值快照与回退证据 |
| TD-S1-008 | S1b 探针当前以 `mss_temperature` 前后变化代替收益序列，统计解释力有限 | 2026-02-21 | MSS probe 已支持 `return_series_source=future_returns` 并形成门禁与消费产物 |
| TD-S3B-016 | `eq` 可执行入口在部分环境存在包路径兼容问题（`ModuleNotFoundError: src`） | 2026-02-21 | 已修复 `pyproject.toml` 打包发现规则为 `where='.' + include='src*'`；仓库外目录执行 `G:\\EmotionQuant-alpha\\.venv\\Scripts\\eq.cmd --help` 通过，不再依赖 `python -m src.pipeline.main` 兜底 |
| TD-S3B-018 | 固定窗口 `20260210-20260213` 在 S3 回测阶段 `backtest_trade_records_empty` 触发硬阻断 | 2026-02-21 | 已修订为“无可开仓信号窗口 WARN 语义”，回测输出 `no_long_entry_signal_in_window`，S3b 双侧无成交样本按 N/A 警告处理并保持 GO |
| TD-S3E-020 | `regime + dual-window` 下 `20260126/20260202` 触发 `factor_validation_fail`，导致 20 日窗口覆盖降为 `18/20` | 2026-02-22 | 已完成 S3e 定向清零：`artifacts/spiral-s3b/20260213/s3e_targeted_clearance_summary.json` 记录 `remaining_failures=0`、`integrated_days=20` |
| TD-S2-010 | S2c 已接入 `validation_weight_plan` 桥接硬门禁，但候选权重生成与 Walk-Forward 选优尚未实现 | 2026-02-17 | 候选权重评估与 Walk-Forward 选优已落地，桥接与语义回归测试通过 |
| TD-S3A-011 | ENH-10 已完成最小实现，但真实远端采集链路吞吐与异常恢复证据尚未补齐 | 2026-02-17 | S3a 已收口：真实 TuShare 客户端接入、实测吞吐报告落地、失败批次真实重跑恢复；全量测试与治理门禁通过 |
| TD-S3A-014 | S3ar 锁恢复实现已落地（重试/PID/等待时长/幂等写入），但真实窗口压测与实网证据归档未完成 | 2026-02-20 | S3ar 已收口：主/兜底 token check、独立限速压测与窗口采集产物已归档，状态由 `in_progress` 切换为 `completed` |
| TD-S3A-021 | `SimulatedTuShareClient.trade_cal` 离线分支默认开市导致节假日误判 | 2026-02-22 | 已修复为“周末+法定闭市日”判定，并补齐闭市日契约测试，`20260218/20260219` 不再返回开市 |
| TD-S2C-019 | `recommend --with-validation-bridge` 在 Parquet 单日覆盖场景误报 `source_missing` | 2026-02-25 | 已修复桥接样例源判断：DuckDB 无表但 L3 Parquet 源存在时不再误报；新增 `test_materialize_s2c_bridge_samples_accepts_parquet_only_sources` 与 `test_integrated_bridge_parquet_only_source_does_not_mark_run_failed` 回归测试 |
| TD-S0-002 | Validation 生产级真实收益口径与统计校准 | 2026-02-26 | 独立审计确认：`calibration.py` 实现 `calibrate_ic_baseline()`（真实 pct_chg + IC/ICIR + PASS/WARN/FAIL gate），有合同测试 `test_calibration_baseline_contract.py` 与 CLI 集成 |
| TD-DA-002 | Enum 类不存在（设计枚举未落地） | 2026-02-26 | 卡 A：新建 `src/models/enums.py`（7 个 StrEnum），已接入 MSS/IRS/PAS/Integration 全部 4 个核心模块 |
| TD-DA-003 | 输出模型命名偏差（MssScoreResult） | 2026-02-25 | 卡 A：重命名为 `MssPanorama`，`MssScoreResult` 保留为类型别名 |
| TD-DA-004 | DuckDB 工具函数重复（16 处） | 2026-02-25 | 卡 A：统一到 `src/db/helpers.py`，16 文件改为 import |
| TD-DA-005 | PAS discount 字段未持久化（`liquidity_discount`/`tradability_discount` 计算后丢弃） | 2026-02-25 | 已在 `stock_pas_daily` 持久化 `liquidity_discount`/`tradability_discount` 字段，并由 PAS full semantics 契约测试覆盖 |
| TD-DA-007 | Integration 模式文档缺失（`dual_verify`/`complementary` 代码已实现但设计未定义） | 2026-02-25 | `integration-algorithm.md` v3.6.0 已补齐 `dual_verify`/`complementary` 正式定义与验收口径 |
| TD-DA-008 | MSS `mss_score` 冗余字段 | 2026-02-25 | 卡 A：字段保留 + deprecation 注释，新消费方指向 `mss_temperature` |
| TD-DA-001 | Calculator/Repository 类不存在（设计定义各模块 Calculator/Repository，但实现为函数式 API） | 2026-02-25 | 卡 B：完成 MSS+IRS 试点，落地 `MssCalculator/MssRepository` 与 `IrsCalculator/IrsRepository`，并补齐 IRS calculator/repository 契约测试 |
| TD-DA-006 | Validation 丰富 API 未实现（设计 12 接口 vs 仅 `run_validation_gate()`） | 2026-02-25 | 卡 C：新增 `validate_factor()` 与 `evaluate_candidate()` 独立入口，补齐 `test_validation_api_contract.py` |
| TD-GOV-012 | DESIGN_TRACE 未覆盖全仓核心代码 | 2026-02-25 | 已扩展到 Data/GUI 核心文件（`fetcher/l1/l2/gui app/dashboard`），`local_quality_check` 输出 `[traceability] pass (16 files)` |
| TD-S0-005 | 仓库内仍有部分 `Phase` 历史措辞（设计参考文档） | 2026-02-26 | 独立审计确认：`Phase` 仅残留于 `Governance/archive/archive-legacy-linear-v4-20260207/`（只读归档），`src/`、`docs/design/`、活跃治理目录均无残留 |
| TD-S3A-015 | AKShare/BaoStock 最后底牌适配器 | 2026-02-26 | 已落地 `src/data/adapters/`（AKShare daily 字段映射 + BaoStock 接口骨架），补齐 6 条 AKShare 适配器契约测试，全量 212 tests passed |
| TD-S4-013 | S4 当前为单日 paper trade 最小闭环，尚未形成跨日持仓卖出与跌停不可卖的连续回放 | 2026-02-18 | S4 收口已完成跨日回放验证：复现“跌停不可卖 -> 次日重试卖出”并固化证据于 `artifacts/spiral-s4/20260222/*` |
| TD-GOV-008 | contracts/governance 检查未进入任务模板门禁 | 2026-02-14 | 已在 `SPIRAL-TASK-TEMPLATE.md` 增加 S2+/契约变更场景检查项 |
| TD-GOV-013 | S2c 同日 PASS/FAIL 证据冲突（正式证据与调试证据混写） | 2026-02-17 | 已引入 `evidence_lane`（release/debug）隔离并新增 `scripts/quality/sync_s2c_release_artifacts.py` 前置校验，正式证据统一为 release |
| TD-GOV-007 | 执行链路 `contract_version` 兼容口径缺失 | 2026-02-14 | 已统一为 `nc-v1` 并同步到 CP-05/06/07/10 与主控路线 |
| TD-GOV-006 | PAS 与执行层 `risk_reward_ratio` 门槛漂移 | 2026-02-14 | 已统一为执行门槛 `risk_reward_ratio >= 1.0`，`<1.0` 过滤 |
| TD-GOV-005 | Spiral 文档同步负担过重 | 2026-02-07 | 已改为最小同步 5 项，CP 文档仅在契约变化时更新 |
| TD-GOV-001 | 路线图缺少 I/O/边界/错误处理 | 2026-02-07 | 已在 ROADMAP 能力包中补齐 |
| TD-GOV-002 | “零技术指标”口径与实践冲突 | 2026-02-07 | 已修订为“单指标不得独立决策” |
| TD-GOV-003 | DuckDB 按年分库为默认策略 | 2026-02-07 | 已改为单库优先、阈值触发分库 |
| TD-GOV-004 | 回测引擎单选写死 | 2026-02-07 | 已改为接口优先、可替换实现 |

---

## 备注

- 技术债必须在每圈 `final.md` 中复核，禁止“静默积压”。
- P0/P1 债务必须给出明确圈号，不允许无限顺延。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-26 | v1.51 | 新增 TD-ARCH-001（已决策）：6 份 api.md OOP→Pipeline 文档对齐，架构决策记录 `Governance/record/ARCH-DECISION-001-pipeline-vs-oop.md` |
| 2026-02-26 | v1.50 | 卡 C 全部清零：清偿 TD-S3A-015（AKShare/BaoStock 适配器骨架 + 6 条冒烟测试）；确认 TD-S0-002/TD-S0-005 已在 v1.48/v1.49 清偿；全量 212 tests passed |
| 2026-02-26 | v1.49 | 独立全量审计：清偿 TD-S0-002（IC/ICIR 校准已落地）；新增 TD-DA-009 跟踪 Enum 设计-实现缺口；TD-S3A-015 更新描述（骨架已存在但未接主链）；两项历史债务插入 S6 执行卡 |
| 2026-02-26 | v1.48 | 清償 TD-S0-005：独立审计确认 Phase 措辞仅存于只读归档，活跃代码/文档无残留；审计附带发现（Calculator/Repository 接口差距、Integration 语义冲突）已插入 S3e/S6 执行卡作为历史债务 |
| 2026-02-25 | v1.47 | 清償 TD-DA-001/TD-DA-006/TD-GOV-012：完成 MSS+IRS Calculator/Repository 试点、Validation 独立 API（`validate_factor`/`evaluate_candidate`）与 DESIGN_TRACE 扩展（16 files pass） |
| 2026-02-25 | v1.46 | 清償 TD-S2C-019/TD-DA-005/TD-DA-007：桥接 Parquet 单日覆盖不再误报 `source_missing`，并补齐回归测试与契约口径同步 |
| 2026-02-25 | v1.45 | 清償 TD-DA-002/003/004/008（卡 A 完成）：DuckDB helpers 统一、Enum 7 类、MssPanorama 重命名、mss_score 废弃标记；193 tests pass |
| 2026-02-25 | v1.44 | 设计-代码对齐审计：新增 8 项 P2 结构性债务（TD-DA-001~008），来源 `Governance/SpiralRoadmap/execution-cards/DESIGN-ALIGNMENT-ACTION-CARD.md`；P0+P1 项已修复 | 
| 2026-02-23 | v1.43 | S5 启动同步：无新增 P0/P1 债务；当前仅进入 GUI 最小闭环实现阶段，生产健康相关风险继续沿用阶段B WARN 预算 |
| 2026-02-23 | v1.42 | S3b 收口一致性同步：无新增 P0/P1 债务；S3b 从“口径不一致阻塞”切换为 `completed`，后续焦点转向 S5 实现缺口 |
| 2026-02-23 | v1.41 | S4r/S4br 收口复核：无新增 P0/P1 债务；完成 legacy `trade_records` 旧 schema 写入阻断修复并补齐回归测试 |
| 2026-02-22 | v1.40 | 清偿 TD-S0-004：S3 已完成细撮合规则 + 绩效指标 + 分层费率/冲击成本模型，S3 成本执行层闭环达成 |
| 2026-02-22 | v1.39 | 更新 TD-S0-004：S3 绩效指标（回撤持续/收益分布/换手稳定性）已落地，债务继续收敛为“完整成本/滑点模型完善” |
| 2026-02-22 | v1.38 | 更新 TD-S0-004：流动性枯竭细化已落地，债务收敛为“完整成本/滑点模型完善” |
| 2026-02-22 | v1.37 | 更新 TD-S0-004：细撮合规则新增一字板显式拒单，债务收敛为“流动性枯竭细化 + 成本/滑点完善” |
| 2026-02-22 | v1.36 | 清偿 TD-S3A-021：修复离线 `trade_cal` 默认开市语义并补齐法定闭市日契约测试 |
| 2026-02-22 | v1.35 | 新增 TD-S3A-021：登记离线 `trade_cal` 默认开市导致节假日误判风险；同步进入 S3a-S3r 处理队列 |
| 2026-02-22 | v1.34 | 清偿 TD-S3E-020：S3e 定向清零后 `remaining_failures=0`，S3b 扩窗覆盖恢复至 `20/20` |
| 2026-02-22 | v1.33 | 新增 TD-S3E-020：20 日扩窗后残留 `20260126/20260202` 两天 `factor_validation_fail`，转入 S3e 精准清零 |
| 2026-02-21 | v1.32 | 清偿 TD-S3B-018：固定窗口 `20260210-20260213` 从硬阻断转为可审计 WARN/N/A 语义，S3b 可继续推进 |
| 2026-02-21 | v1.31 | S3c 启动同步：未新增债务；保留 TD-S3B-018（固定窗口无成交）作为当前阶段主阻断 |
| 2026-02-21 | v1.30 | 新增 TD-S3B-018（固定窗口无成交阻断）与 TD-S2C-019（bridge 样例源缺失导致推荐命令误失败），同步 S3b/S2c-S3b 收口风险 |
| 2026-02-21 | v1.29 | 清偿 TD-S3B-016：修复 `eq` 入口打包路径兼容问题，仓库外目录直接执行 `eq` 命令通过 |
| 2026-02-21 | v1.28 | 清偿 TD-S3-017 / TD-S1-007 / TD-S1-008：S3d/S3e CLI 阻断解除，MSS adaptive 与 future_returns probe 契约落地并通过合同测试 |
| 2026-02-21 | v1.27 | S3 审计补录：新增 TD-S3-017（S3d/S3e CLI 契约缺口），明确其为核心算法 full 实现前置阻断项 |
| 2026-02-21 | v1.26 | S0-S2r 一致性复核同步：核对路线图/执行卡/specs/record 与代码实现一致；无新增 P0/P1 债务 |
| 2026-02-21 | v1.25 | 清偿 TD-S0-006：S0c-R1 完成 SW31 严格门禁与映射收口；同步修订 TD-S2-009 说明不再引用 TD-S0-006 |
| 2026-02-20 | v1.24 | 路线图对齐：将核心算法深度债务圈位重映射到 `S3c/S3d/S3e`（SW31、MSS adaptive、Validation 生产校准） |
| 2026-02-20 | v1.23 | 清偿 TD-S3A-014（S3ar 实网证据链补齐并收口）；新增 TD-S3B-016 跟踪 `eq` 入口环境兼容风险 |
| 2026-02-20 | v1.22 | 更新 TD-S3A-014：实现侧缺口已收敛到“实网压测与证据归档”，锁恢复审计字段与幂等写入已落地 |
| 2026-02-19 | v1.21 | 将 TD-S3A-014 收敛为“锁恢复证据链缺口”；新增 TD-S3A-015 跟踪 AKShare/BaoStock 最后底牌预留实现 |
| 2026-02-19 | v1.20 | 新增 P0 债务 TD-S3A-014：多源兜底与 DuckDB 锁恢复门禁缺失，计划在 S3ar 修复圈处理 |
| 2026-02-18 | v1.19 | 清偿 TD-S4-013：S4 完成跨日持仓生命周期与跌停次日重试回放证据闭环 |
| 2026-02-17 | v1.18 | 清偿 TD-S3A-011：S3a 完成真实客户端接入、实测吞吐与失败恢复证据闭环 |
| 2026-02-17 | v1.17 | 更新 TD-S0-004：板块化涨跌停阈值（10%/20%/5%）已落地，债务收敛到更细撮合规则（如一字板/流动性枯竭） |
| 2026-02-17 | v1.16 | 更新 TD-S0-004（多日回放/T+1/涨跌停最小细节已落地）；更新 TD-GOV-012 覆盖到 S4 Trading；新增 TD-S4-013 跟踪跨日持仓回放缺口 |
| 2026-02-17 | v1.15 | 更新 TD-GOV-012：设计溯源检查已纳入 S3 Backtest 模块，状态由待处理转为处理中 |
| 2026-02-17 | v1.14 | 更新 TD-S0-004 为“处理中”：S3 已有最小回测链路，剩余完整执行细节与多窗口能力待补齐 |
| 2026-02-17 | v1.13 | 更新 TD-S3A-011 为“处理中”：S3a 最小实现已完成，剩余真实链路验证与证据补齐 |
| 2026-02-17 | v1.12 | 清偿 TD-GOV-013：完成 S2c 证据冲突清障，新增 release/debug 证据隔离与 release 同步前置校验 |
| 2026-02-17 | v1.11 | 清偿 TD-S0-003/TD-S2-009/TD-S2-010；TD-S0-002 调整为“生产级统计口径校准待 S3” |
| 2026-02-17 | v1.10 | 新增 TD-GOV-012：设计溯源标记目前仅覆盖 S2c 关键模块，需继续扩展到全仓核心代码 |
| 2026-02-17 | v1.9 | 更新 TD-S2-010：从“未接入桥接”调整为“桥接已落地、候选权重选优待实现”，计划处理圈前移至 S2c |
| 2026-02-16 | v1.8 | 启动下一圈前补录 TD-S3A-011（ENH-10 能力尚未实现），计划处理圈锁定 S3a |
| 2026-02-15 | v1.7 | S2b 收口复核：将 S2 阶段遗留债务统一推进到 S3；新增 TD-S2-010（候选权重未接入） |
| 2026-02-15 | v1.6 | S2a 收口复核：TD-S0-002 调整为“最小 Gate 已落地，完整验证待 S2b”；新增 TD-S2-009（IRS/PAS 评分校准债务） |
| 2026-02-15 | v1.5 | S1b 收口复核：TD-S0-006/TD-S1-007 处理圈推进至 S2a；新增 TD-S1-008（探针收益口径债务） |
| 2026-02-15 | v1.4 | S1a 收口复核：TD-S0-002 处理圈调整为 S2a；新增 TD-S1-007（MSS 自适应阈值债务） |
| 2026-02-15 | v1.3 | 新增 TD-S0-006（S0c 行业快照粒度债务）；TD-S0-001 清偿范围扩展至 S0c |
| 2026-02-15 | v1.2 | 清偿 TD-S0-001：S0a/S0b 闭环与 6A 证据链补齐 |
| 2026-02-14 | v1.1 | 新增并清偿 TD-GOV-006/007/008（RR 门槛漂移、contract_version 兼容口径、contracts/governance 模板门禁） |
| 2026-02-07 | v1.0 | 切换到 Spiral 技术债模型，重建债务清单 |
