# design-review-sandbox 修复记录（2026-02-14）

## 0. 备份

- 已完成系统文档打包：`.reports/system-docs-backup-20260214-131149.zip`
- 打包范围：`docs/`、`Governance/`、`AGENTS.md`

## 1. 统一结构修复（12 份报告）

- 文件范围：`review-001` 到 `review-012`
- 修复项：
1. 将 `4.1/4.2` 子段标题统一由二级标题改为三级标题（`##` -> `###`）。
2. 统一校验为 8 段模板：`1..8` 主段完整且顺序一致。
3. 校验“实战沙盘演示”章节在 12 份报告中全部存在。

## 2. 单文件专项修复

1. `review-001-mss-20260214.md`
- 新增 `## 5. 实战沙盘演示（预期行为）`（4 个场景）
- 原章节重排：
  - `防御措施盘点`：`5 -> 6`
  - `需要进化的点`：`6 -> 7`
  - `下一步`：`7 -> 8`

2. `review-011-system-overview-governance-20260214.md`
- 修复证据行英文连接词：`to` -> `到`

3. `review-001/002/003`
- 章节标题统一：`## 4. A 股适配阶段与不适配阶段`

## 3. 校验结果

1. 子段层级问题：已清零（无 `^## 4.1` / `^## 4.2` 残留）。
2. 英文连接词笔误：已清零（无 `to` 残留）。
3. 模板完整性：12/12 通过（均为 8 段结构）。

## 4. 备注

- 本轮为结构与一致性修复，未改变各报告核心结论立场。
- 若继续下一轮，建议按 `review-001 -> review-012` 逐份做“证据行号复核 + 表述压缩 + 风险优先级复评”内容级精修。

## 5. 第二轮进度（内容级精修）

1. 已完成：`review-001-mss-20260214.md`
- 逐条复核证据行号并纠偏：
  - 核心输出证据由 `mss-algorithm.md:14` 校正为 `mss-algorithm.md:16`
  - Integration 角色证据由 `integration-algorithm.md:226` 优化为 `integration-algorithm.md:92`
- 全文完成表述压缩（不改变原结论立场）
- 结构完整性复核通过（8 段模板齐全）

2. 已完成：`review-002-irs-20260214.md`
- 逐条复核证据行号并纠偏：
  - 输出契约证据补齐 `rotation_status` 与 `neutrality` 行位点（`irs-algorithm.md:20/:23`）
  - “尺度约束”证据补齐 `count->ratio->zscore` 直接位点（`irs-algorithm.md:411`）
  - Integration 软约束证据补齐规则总述位点（`integration-algorithm.md:225`）
- 删除证据不足表述并压缩全文（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

3. 已完成：`review-003-pas-20260214.md`
- 逐条复核证据行号并纠偏：
  - 输出契约证据补齐 `opportunity_grade/direction` 行位点（`pas-algorithm.md:20/:21`）
  - 行为因子 ±20% 映射证据由变更记录位点改为规则位点（`pas-algorithm.md:161`）
  - RR 口径冲突条目移除，改为“算法与数据模型已对齐”并双证据确认（`pas-algorithm.md:345` + `pas-data-models.md:286`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

4. 已完成：`review-004-validation-20260214.md`
- 逐条复核证据行号并纠偏：
  - 补齐 Validation 双目标证据（`factor-weight-validation-algorithm.md:11/:14`）
  - 权重验证条件证据改为规则位点（`...:89/:91/:115/:118`）
  - Gate 关键治理字段改为精确字段位点（`data-models.md:95-98`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

5. 已完成：`review-005-integration-20260214.md`
- 逐条复核证据行号并纠偏：
  - Gate 输入字段证据细化到字段位点（`integration-algorithm.md:79/:80/:81`）
  - 软约束与排序证据改为规则位点（`...:225/:228/:229/:234`，`...:363/:364/:365`）
  - 输出可追溯证据改为模型字段位点（`integration-data-models.md:153/:155/:158/:161/:164`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

6. 已完成：`review-006-backtest-20260214.md`
- 逐条复核证据行号并纠偏：
  - 引擎选型证据细化到三轨位点（`backtest-engine-selection.md:13/:14/:15`）
  - 执行约束沙盘证据补齐测试用例期望位点（`backtest-test-cases.md:13/:33`）
  - 质量门禁证据改为条目位点（`backtest-test-cases.md:163/:167/:171`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

7. 已完成：`review-007-trading-20260214.md`
- 逐条复核证据行号并纠偏：
  - 风控检查描述修正为“多段检查”（文档实际为 1/2/2.5/3/4/5 共六类）
  - 风控阈值证据补齐行业位点（`trading-algorithm.md:180`）
  - 沙盘拒单证据细化到具体条件位点（`...:164/:167/:169`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

8. 已完成：`review-008-analysis-20260214.md`
- 逐条复核证据行号并纠偏：
  - 归因切换证据细化到上下文分支与三路贡献位点（`analysis-algorithm.md:170/:172/:174/:199/:201`）
  - 风险摘要证据细化到字段位点（`analysis-data-models.md:199-205`）
  - 防御“外部库边界”补充直接证据（`analysis-api.md:13`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

9. 已完成：`review-009-gui-20260214.md`
- 逐条复核证据行号并纠偏：
  - GUI 定位证据补齐“信号展示/只读展示”位点（`gui-algorithm.md:14/:16`）
  - 缓存策略证据补齐“交易执行数据 1 分钟”位点（`gui-algorithm.md:260`）
  - 异常反馈证据聚焦用户态三条消息位点（`gui-information-flow.md:468/:469/:470`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

10. 已完成：`review-010-data-layer-20260214.md`
- 逐条复核证据行号并纠偏：
  - 降级字段证据细化到三字段位点（`data-layer-data-models.md:229/:230/:231`）
  - L3 执行关键字段证据改为关键列位点（`...:441/:443/:450`）
  - 存储边界证据聚焦主库/ops 库位点（`data-layer-api.md:682/:683`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

11. 已完成：`review-011-system-overview-governance-20260214.md`
- 逐条复核证据行号并纠偏：
  - 原区间证据改为关键规则位点（`system-overview.md:21/:25/:26`，`6A-WORKFLOW.md:18/:21`）
  - SoT 导航证据聚焦入口位点（`system-overview.md:105/:107`，`GOVERNANCE-STRUCTURE.md:29/:35/:40`）
  - 6A 收口失败沙盘证据细化到退出条件条目位点（`6A-WORKFLOW.md:95/:99`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性复核通过（8 段模板齐全）

12. 已完成：`review-012-naming-contracts-20260214.md`
- 逐条复核证据行号并纠偏：
  - 移除过期 P0 冲突叙述（`pas-data-models >= 0`），改为“RR 口径已对齐”并补四端证据（`pas-algorithm.md:22/:345`、`pas-data-models.md:286`、`trading-algorithm.md:52`、`backtest-algorithm.md:103`）
  - Validation->Integration 桥接证据细化到“业务键 -> 数值对象”位点（`factor-weight-validation-api.md:127/:132`、`factor-weight-validation-data-models.md:95/:162`、`integration-api.md:91/:102`）
  - 代码字段契约证据补齐“命名规范 + Data Layer 转换边界”双位点（`naming-conventions.md:280/:281`、`data-layer-api.md:612/:614/:882`）
- 全文完成表述压缩（结论方向不变）
- 结构完整性与引用解析复核通过（`sections=8; seq=1..8`，`ALL_REFERENCES_RESOLVED`）

13. 已完成：命名/契约一致性 P0 自动检查落地
- 新增脚本：`scripts/quality/naming_contracts_check.py`
  - 覆盖 6 类关键契约：`sideways/flat`、`unknown`、`risk_reward_ratio` 命名与 `>=1.0` 门槛、`STRONG_BUY=75`、`stock_code/ts_code` 分层边界、`PASS/WARN/FAIL` Gate 语义
  - 当前基线检查通过：`[contracts] pass (26 checks)`
- 集成入口：`scripts/quality/local_quality_check.py`
  - 新增 `--contracts` 参数，支持与现有 `--session/--scan` 统一执行
- 单测补齐：
  - 新增 `tests/unit/scripts/test_naming_contracts_check.py`
  - 更新 `tests/unit/scripts/test_local_quality_check.py`
  - 新增 `tests/conftest.py`（确保 `scripts.*` 可导入）
  - 针对当前环境权限限制，测试临时目录改用仓库内 `.reports/.tmp-test-artifacts`
- 验证结果：
  - `pytest tests/unit/scripts/test_local_quality_check.py tests/unit/scripts/test_naming_contracts_check.py` -> 7 passed
  - `C:\\miniconda3\\python.exe -m scripts.quality.local_quality_check --contracts` -> pass

14. 已完成：`review-001-mss-20260214.md` 对应设计问题修复（第一项闭环）
- 修订文件：
  - `docs/design/core-algorithms/mss/mss-algorithm.md`
  - `docs/design/core-algorithms/mss/mss-data-models.md`
  - `docs/design/core-algorithms/mss/mss-api.md`
- 核心修复点（对应 review-001 第 7 节）：
  - P0：周期阈值从固定值扩展为 `fixed/adaptive` 双模式，新增分位阈值 `T30/T45/T60/T75` 与冷启动回退规则
  - P0：`strong_up/down` 改为分板块制度归一口径（主板10%/创业板与科创板20%/ST 5%）
  - P1：趋势判定由“3 日严格单调”升级为 `EMA + slope + trend_band` 抗抖逻辑
  - P1：极端因子新增方向语义 `extreme_direction_bias`（区分恐慌尾部与逼空尾部）
  - P2：异常处理统一语义，明确“禁止沿用前值”与 `stale_days` 分层处理
- 契约同步：
  - 数据模型新增 `extreme_direction_bias`、`trend_quality` 字段与校验约束
  - API 增加 `get_extreme_direction_bias()` 并矩阵化错误处理

15. 已完成：`review-002-irs-20260214.md` 对应设计问题修复（第二项闭环）
- 修订文件：
  - `docs/design/core-algorithms/irs/irs-algorithm.md`
  - `docs/design/core-algorithms/irs/irs-data-models.md`
  - `docs/design/core-algorithms/irs/irs-api.md`
  - `docs/design/core-algorithms/irs/irs-information-flow.md`
  - `docs/design/core-algorithms/README.md`
- 核心修复点（对应 review-002 第 7 节）：
  - P0：配置建议由固定排名映射升级为“分位 + 集中度（HHI）”动态映射，并保留 `fixed` 兼容模式
  - P0：轮动状态由“3 日单调”升级为“robust slope + MAD band”，并保留冷启动回退逻辑
  - P1：资金流向因子加入 `flow_share` 与拥挤惩罚（`crowding_penalty_lambda` / `crowding_trigger`）
  - P1：估值因子加入生命周期 `style_bucket`（growth/balanced/value）进行 PE/PB 权重校准
  - P2：修复跨文档口径冲突：`core-algorithms/README.md` 明确 MSS 不直接作为 IRS 因子输入，风险约束在 Integration 层协同
- 契约同步：
  - 数据模型新增 `market_amount_total/style_bucket` 输入，新增 `rotation_slope/allocation_mode` 输出与 DDL 字段
  - API 返回契约补充 `allocation_mode/rotation_slope`，并新增 `get_allocation_mode()`
  - 信息流同步改为动态映射与 slope+band 判定，异常处理补充 `stale_days>3` 阻断

16. 已完成：`review-003-pas-20260214.md` 对应设计问题修复（第三项闭环）
- 修订文件：
  - `docs/design/core-algorithms/pas/pas-algorithm.md`
  - `docs/design/core-algorithms/pas/pas-data-models.md`
  - `docs/design/core-algorithms/pas/pas-api.md`
  - `docs/design/core-algorithms/pas/pas-information-flow.md`
- 核心修复点（对应 review-003 第 7 节）：
  - P0：结构因子由固定窗口升级为“波动率+换手率”驱动的自适应窗口（20/60/120），并保留 `fixed` 兼容模式
  - P0：风险收益比新增成交约束折扣，输出 `effective_risk_reward_ratio`（执行口径）与名义 RR（分析口径）分层
  - P1：行为确认由单量比扩展为 `volume_quality`（量比+换手+收盘保真）
  - P1：新增 `quality_flag/sample_days` 质量字段（normal/cold_start/stale）并用于执行降级
  - P2：新增 PAS 契约漂移自动检查（RR 门槛、枚举、窗口集合）与失败阻断语义
- 契约同步：
  - 数据模型补齐自适应窗口依赖字段（20/60/120 高低点、波动率、样本质量）与输出/DDL 字段
  - API 增加 `run_contract_checks()`，并明确 stale/cold_start 的降级返回语义
  - 信息流同步更新 Step2/3/5/6、Integration 交互字段与异常处理策略

17. 已完成：`review-004-validation-20260214.md` 对应设计问题修复（第四项闭环）
- 修订文件：
  - `docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md`
  - `docs/design/core-algorithms/validation/factor-weight-validation-data-models.md`
  - `docs/design/core-algorithms/validation/factor-weight-validation-api.md`
  - `docs/design/core-algorithms/validation/factor-weight-validation-information-flow.md`
- 核心修复点（对应 review-004 第 7 节）：
  - P0：门禁阈值新增 `fixed/regime` 双模式，按 `mss_temperature + market_volatility_20d` 分层动态注入
  - P0：WFA 升级为双窗口并行（`252/63/63 + 126/42/42`）并采用稳健性投票决策
  - P1：fallback 分层化（`factor_failure/weight_failure/data_failure/data_stale`）并显式绑定回退方案
  - P1：`stale_days` 超阈值由“仅告警”升级为“自动降仓”（`position_cap_ratio`）
  - P2：候选评估补齐换手、冲击成本、涨跌停可成交性约束（`turnover/impact_cost_bps/tradability_pass_ratio`）
- 契约同步：
  - 数据模型新增 `failure_class/position_cap_ratio` 与双窗口评估字段，DDL 同步
  - API 增加 `resolve_regime_thresholds/build_dual_wfa_windows/classify_fallback` 接口
  - 信息流同步更新日级时序、输出边界与异常处理（自动降仓语义）

18. 已完成：`review-005-integration-20260214.md` 对应设计问题修复（第五项闭环）
- 修订文件：
  - `docs/design/core-algorithms/integration/integration-algorithm.md`
  - `docs/design/core-algorithms/integration/integration-data-models.md`
  - `docs/design/core-algorithms/integration/integration-api.md`
  - `docs/design/core-algorithms/integration/integration-information-flow.md`
- 核心修复点（对应 review-005 第 7 节）：
  - P0：补齐工程闭环口径（`IntegrationEngine.calculate + IntegrationRepository.save_batch + 5 组契约测试`）
  - P0：参数 regime 化（阈值、协同倍率、仓位乘子、BU 子预算比例）
  - P1：候选评估新增执行约束（`tradability_pass_ratio/impact_cost_bps/candidate_exec_pass`）并触发 baseline 回退
  - P1：BU/TD 冲突由“TD 全覆盖”升级为“TD 定净风险 + BU 子预算调结构”
  - P2：统一 `degraded/WARN/stale/cold_start` 为单一 `integration_state` 状态机语义
- 契约同步：
  - 数据模型与 DDL 新增 `integration_state/position_cap_ratio` 及候选执行约束字段
  - API 新增 `resolve_regime_parameters/classify_integration_state/check_candidate_executability`
  - 信息流同步更新 Step 1/2/3/5/7 与异常处理分支

19. 已完成：`review-006-backtest-20260214.md` 对应设计问题修复（第六项闭环）
- 修订文件：
  - `docs/design/core-infrastructure/backtest/backtest-algorithm.md`
  - `docs/design/core-infrastructure/backtest/backtest-data-models.md`
  - `docs/design/core-infrastructure/backtest/backtest-api.md`
  - `docs/design/core-infrastructure/backtest/backtest-information-flow.md`
  - `docs/design/core-infrastructure/backtest/backtest-test-cases.md`
- 核心修复点（对应 review-006 第 7 节）：
  - P0：补齐 CP-06 最小可运行闭环口径（`local_vectorized + top_down` 命令 + 落库验收）
  - P0：成交模型从示意升级为 `queue + volume + fill_probability` 可执行规则
  - P1：成本模型补齐流动性分层（L1/L2/L3）与 `impact_cost_bps_cap` 约束
  - P1：`blocked_by_gate/degraded/fallback` 统一为 `backtest_state` 状态机
  - P2：模式切换从纯配置扩展为 `config_fixed/regime_driven/hybrid_weight`
- 契约同步：
  - 数据模型新增 `mode_switch_policy/min_fill_probability/queue_participation_rate/impact_cost_bps_cap` 等配置字段
  - 交易记录新增 `fill_probability/queue_ratio/liquidity_tier/impact_cost_bps/backtest_state`
  - API 新增 `run_minimal()/resolve_mode()/ExecutionFeasibilityModel/LiquidityCostModel`
  - 测试清单补齐状态机覆盖与最小命令验收条目

20. 已完成：`review-007-trading-20260214.md` 对应设计问题修复（第七项闭环）
- 修订文件：
  - `docs/design/core-infrastructure/trading/trading-algorithm.md`
  - `docs/design/core-infrastructure/trading/trading-data-models.md`
  - `docs/design/core-infrastructure/trading/trading-api.md`
  - `docs/design/core-infrastructure/trading/trading-information-flow.md`
- 核心修复点（对应 review-007 第 7 节）：
  - P0：补齐 CP-07 最小可运行闭环口径（`signal -> order -> execution -> positions/t1_frozen`）与 `run_minimal` 接口定义
  - P0：成交模型由“默认全额成交”升级为“`fill_probability + fill_ratio + liquidity_tier + impact_cost_bps`”可执行规则
  - P1：风险阈值新增 `fixed/regime` 双模式，按 `mss_temperature + market_volatility_20d` 动态解析
  - P1：拒单原因统一为 `REJECT_*` 标准枚举，便于跨期统计与参数回放
  - P2：补齐 `auction_sliced/time_windowed` 分批时段化执行实验口径
- 契约同步：
  - 数据模型新增执行可行性字段与状态字段：`fill_probability/fill_ratio/liquidity_tier/impact_cost_bps/reject_reason/trading_state/execution_mode/slice_seq`
  - API 新增/扩展 `execute_sliced()/ExecutionFeasibilityModel/resolve_regime_thresholds()/TradingEngine.run_minimal()`
  - 信息流统一 `blocked_by_gate/degraded` 为 `blocked_gate_fail/warn_data_fallback`，异常表改为 `REJECT_*` 枚举口径

21. 已完成：`review-008-analysis-20260214.md` 对应设计问题修复（第八项闭环）
- 修订文件：
  - `docs/design/core-infrastructure/analysis/analysis-algorithm.md`
  - `docs/design/core-infrastructure/analysis/analysis-data-models.md`
  - `docs/design/core-infrastructure/analysis/analysis-api.md`
  - `docs/design/core-infrastructure/analysis/analysis-information-flow.md`
- 核心修复点（对应 review-008 第 7 节）：
  - P0：补齐 CP-08 最小可运行闭环口径（`compute_metrics -> attribute_signals -> generate_daily_report -> persist/export`）并新增 `run_minimal` 入口
  - P0：归因升级为稳健口径（双尾分位截尾 + 小样本回退），新增 `raw/trimmed/trim_ratio/attribution_method` 审计字段
  - P1：风险摘要前瞻化，新增 `high_risk_change_rate/low_risk_change_rate/risk_turning_point/risk_regime`
  - P1：补齐实盘-回测偏差分解（`signal_deviation/execution_deviation/cost_deviation/total_deviation`）
  - P2：新增 GUI/治理共用 `dashboard_snapshot` 输出与字段规范
- 契约同步：
 - 数据模型新增 `LiveBacktestDeviation` 与 `live_backtest_deviation` DDL；扩展 `SignalAttribution`、`RiskSummary` 字段
 - API 新增/扩展 `AnalysisEngine.run_minimal()/decompose_live_backtest_deviation()/analyze_risk_trend()/export_dashboard_snapshot()`
 - 信息流同步更新日报时序、输出关系与异常状态语义（统一为 `analysis_state`）

22. 已完成：`review-009-gui-20260214.md` 对应设计问题修复（第九项闭环）
- 修订文件：
  - `docs/design/core-infrastructure/gui/gui-algorithm.md`
  - `docs/design/core-infrastructure/gui/gui-api.md`
  - `docs/design/core-infrastructure/gui/gui-data-models.md`
  - `docs/design/core-infrastructure/gui/gui-information-flow.md`
- 核心修复点（对应 review-009 第 7 节）：
  - P0：补齐 CP-09 最小可运行 GUI 闭环口径（`DataService + Dashboard + IntegratedPage`）并新增 `run_minimal`/`GuiRunResult` 约束
  - P0：默认过滤门槛改为配置驱动（`FilterConfig/resolve_filter_config`）并新增页面阈值徽标展示
  - P1：缓存一致性增强，新增 `data_asof/cache_age_sec/freshness_level` 元信息与页面新鲜度展示
  - P1：异常可观测性增强，补齐 `timeout/empty_state/data_fallback/permission_denied` 事件计数与观测面板字段
  - P2：Integrated 页面联动 Analysis 原因面板（归因 + 风险摘要 + 偏差提示）
- 契约同步：
  - 数据模型新增 `FreshnessMeta/UiObservabilityPanel/RecommendationReasonPanel`，并扩展 `DashboardData/IntegratedPageData`
  - API 新增/扩展 `run_minimal()/resolve_filter_config()/build_filter_preset_badges()/get_freshness_meta()/record_ui_event()/get_recommendation_reason_panel()`
  - 信息流同步更新 Dashboard 数据流、推荐表数据流、刷新策略与异常处理分支

23. 已完成：`review-010-data-layer-20260214.md` 对应设计问题修复（第十项闭环）
- 修订文件：
  - `docs/design/core-infrastructure/data-layer/data-layer-algorithm.md`
  - `docs/design/core-infrastructure/data-layer/data-layer-api.md`
  - `docs/design/core-infrastructure/data-layer/data-layer-data-models.md`
  - `docs/design/core-infrastructure/data-layer/data-layer-information-flow.md`
  - `src/data/models/snapshots.py`
  - `src/data/quality_gate.py`
  - `tests/unit/data/models/test_model_contract_alignment.py`
  - `tests/unit/data/models/test_snapshots.py`
  - `tests/unit/data/test_quality_gate.py`
- 核心修复点（对应 review-010 第 7 节）：
  - P0：`src/data/models` 补齐 `data_quality/stale_days/source_trade_date` 契约字段与约束
  - P0：新增质量门禁自动化原型 `evaluate_data_quality_gate()`（覆盖率、`stale_days`、跨日一致性前置检查）
  - P1：降级策略由单阈值扩展为“数据类型分级阈值 + 影响面分级”
  - P1：新增可选盘中增量层口径（观测用途，不进入主交易流水线）
  - P2：补齐分库触发阈值与回迁一致性校验流程
- 契约同步：
  - 数据模型新增 `data_readiness_gate` 门禁决策表，`data_quality_report` 扩展 `gate_status/affected_layers/action`
  - API 增补 `DataGateDecision` 契约、盘中增量 API、分库触发与回迁 API
  - 信息流补充 `ready/degraded/blocked` 门禁决策流与跨日不一致阻断语义

24. 已完成：`review-011-system-overview-governance-20260214.md` 对应设计问题修复（第十一项闭环）
- 修订文件：
  - `docs/system-overview.md`
  - `Governance/steering/TRD.md`
  - `Governance/steering/6A-WORKFLOW.md`
  - `Governance/steering/GOVERNANCE-STRUCTURE.md`
  - `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`
  - `scripts/quality/governance_consistency_check.py`
  - `scripts/quality/local_quality_check.py`
  - `tests/unit/scripts/test_governance_consistency_check.py`
- 核心修复点（对应 review-011 第 7 节）：
  - P0：在 `system-overview` 与 `TRD` 增补“研究主选 vs 收口主线”术语消歧
  - P0：`system-overview` 文档导航补充 `TRD/GOVERNANCE-STRUCTURE/6A-WORKFLOW` 入口
  - P1：新增治理一致性自动检查脚本（SoT、6A 五件套、闭环口径、A 股精度表述）
  - P1：`system-overview` 增加 A 股规则精度链接到铁律与核心原则
  - P2：新增“跨文档变更联动模板”并接入 6A 执行清单
- 契约同步：
  - 新增 `python -m scripts.quality.local_quality_check --governance` 检查入口
  - 单测新增 `test_governance_consistency_check.py`，覆盖 missing file/pattern 与仓库基线通过
  - 验证通过：`[governance] pass (20 checks)`

25. 已完成：`review-012-naming-contracts-20260214.md` 对应设计问题修复（第十二项闭环）
- 修订文件：
  - `docs/naming-conventions.md`
  - `docs/design/core-algorithms/integration/integration-algorithm.md`
  - `docs/design/core-infrastructure/trading/trading-algorithm.md`
  - `docs/design/core-infrastructure/backtest/backtest-algorithm.md`
  - `docs/naming-contracts.schema.json`
  - `docs/naming-contracts-glossary.md`
  - `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`
  - `scripts/quality/naming_contracts_check.py`
- 核心修复点（对应 review-012 第 7 节）：
  - P0：命名/契约自动检查扩展到关键矩阵：`sideways/unknown/risk_reward_ratio/stock_code/ts_code/PASS-WARN-FAIL` + 阈值 `75/70/55/1.0`
  - P0：落地 Schema-first 机器可读源（`docs/naming-contracts.schema.json`，版本 `nc-v1`）
  - P1：Integration/Trading/Backtest 增加 `contract_version` 前置兼容检查，不兼容即阻断
  - P2：新增跨模块术语字典与命名契约变更模板（便于联动同步）
- 契约同步：
  - 新增 `docs/naming-contracts-glossary.md` 与 `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`
  - `scripts/quality/naming_contracts_check.py` 扩展为 43 项检查
  - 验证通过：`pytest tests/unit/scripts/test_naming_contracts_check.py ...`（11 passed）；`python -m scripts.quality.local_quality_check --contracts` -> `[contracts] pass (43 checks)`

26. 已完成：review-012 三个剩余缺口补齐（彻底闭环）
- 修订文件：
  - `docs/design/core-algorithms/integration/integration-api.md`
  - `docs/design/core-infrastructure/trading/trading-api.md`
  - `docs/design/core-infrastructure/backtest/backtest-api.md`
  - `scripts/quality/naming_contracts_check.py`
  - `scripts/quality/contract_behavior_regression.py`
  - `scripts/quality/local_quality_check.py`
  - `tests/unit/scripts/test_contract_behavior_regression.py`
  - `.github/workflows/quality-gates.yml`
- 关键补齐点：
  - 缺口 #1（CI 阻断）：新增 `quality-gates` 工作流，强制执行 `local_quality_check --contracts --governance` 与契约回归测试。
  - 缺口 #2（行为边界回归）：新增可执行契约场景回归（`unknown`、`sideways`、`risk_reward_ratio==1.0`、`Gate WARN/FAIL`、`contract_version mismatch`）。
  - 缺口 #3（API 契约同步）：Integration/Trading/Backtest API 文档补齐 `contract_version` 前置兼容语义与阻断行为。
- 验证结果：
  - `pytest tests/unit/scripts/test_naming_contracts_check.py tests/unit/scripts/test_contract_behavior_regression.py tests/unit/scripts/test_local_quality_check.py tests/unit/scripts/test_governance_consistency_check.py` -> 18 passed
  - `C:\miniconda3\python.exe -m scripts.quality.local_quality_check --contracts --governance` -> `[contracts] pass (49 checks)`、`[contracts-behavior] pass (7 checks)`、`[governance] pass (20 checks)`
