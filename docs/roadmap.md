# EmotionQuant v2 — 全系统重建路线图 + 实现卡

## 0. 审计复核总结

### 0.1 SOS 发现验证结论

经代码级逐项实锤，11 个 SOS 子目录共 183 项偏差，其中 ~80 项为致命/严重级。**全部属实，无误报**。

各模块验证结论：

* **数据层** (14项, 5×P0)：P0 快照计算错误已确认，cascade 影响 MSS/IRS/PAS 全链路。**真实且紧急**。
* **MSS** (12项, 3×P0)：P0 全部在 information-flow 文档，核心算法公式 13/13 正确。**文档修正优先级高，代码改动量小**。
* **IRS** (8项, 3×致命)：C1/C2 归一化路径数学上不等价已确认（PE量级10-100 vs PB量级1-10 直接加权会被 PE 主导）。C3 硬编码 0.5/0.5 已确认。**真实且紧急**。
* **PAS** (16+项, 8×P0)：代码实锤确认——`wbg = 0.4*wlur + 0.4*wnhr + 0.2*wmaxpct`（应为 0.4/0.3/0.3）；`w_str = 0.7*pos + 0.3*bsn`（缺 trend_continuity_ratio）；`wvq` 退化为简单量比；行为因子组件全错。**真实，三因子公式全部需要重写**。
* **Validation** (13项, 11×🔴)：代码实锤确认——4 个因子名与设计 15 个零重叠（`irs_pas_coupling` 等均为虚构）；IC 计算的是 IRS vs PAS 相关性而非因子 vs 未来收益；ICIR = abs(IC) 而非 mean/std；WFA 为启发式公式非真实 OOS 回测。**架构级断裂，需近乎完全重写**。
* **Integration** (19项, 7×P0)：strength_factor 未应用、IRS 方向来源错误、仓位乘子缺失。**真实**。
* **Backtest** (19项, 12×🔴)：代码实锤确认——T+1 后无条件清仓（无止损/止盈/持仓天数判断）；max_drawdown 公式错误（全局最高-最低 vs 峰谷追踪）；成交价无滑点；核心绩效指标全缺。**真实，回测结果不可信**。
* **Trading** (26项, 5×P0)：成交模型与 Backtest 不一致、信号过滤逻辑不统一、风控检查缺失。**真实**。
* **Analysis** (16项, 12×🔴)：绩效指标全部硬编码 0.0、日报/风险分析完全缺失、equity_curve 跨模块断裂。**真实，60% 功能缺失**。
* **GUI** (25项, 7×P0)：架构完全不同（设计 4 层 18 文件 vs 代码扁平 5 文件）、6 个 Service 层全缺。**真实，需完全重建**。
* **增强** (15项, 5×🔴)：Qlib 适配层完全缺失、监控模块仅占位。**真实**。

### 0.2 跨模块依赖链

```
数据层 P0（快照计算错误）
  ↓ cascade
MSS 温度 / IRS 行业分 / PAS 基因库 → 全部受污染
  ↓
Validation Gate 不可信（且自身也是断裂的）
  ↓
Integration final_score 错误
  ↓
Backtest 回测结果不可信（且自身卖出逻辑也是错的）
  ↓
Trading 交易信号不可信
  ↓
Analysis 绩效全部为 0
  ↓
GUI 展示的是错误数据
```

**结论：这不是局部修补能解决的问题。需要按依赖链自底向上重建。**

### 0.3 核心架构决策（已确认）

* **AD-01 代码向设计对齐**：设计经过多轮 review，是权威口径。代码偏离设计的，修代码。
* **AD-02 OOP 架构**：设计定义的是 OOP（Service/Repository/Engine/Model），代码全部改为 OOP。每个模块统一结构。
* **AD-03 Qlib 主线回测**：回测引擎收敛到 Qlib 单一主线。本地向量化回测器作为 Qlib 不可用时的 fallback，不作为并行主线。
* **AD-04 设计文档同步修正**：information-flow / data-models 中滞后的部分，随模块重建同步修正。不单独开一轮文档修订。
* **AD-05 统一模块目录结构**：所有模块遵循相同的文件组织规范（见§1）。

## 1. 标准化模块目录结构

### 1.1 统一文件规范

每个业务模块（不论核心算法还是基础设施）遵循同一套骨架：

```
src/{module}/
├── __init__.py           # 公开 API 导出
├── pipeline.py           # 编排入口（调度 service 方法，不含业务逻辑）
├── service.py            # OOP 业务门面（Service 类，封装 engine + repository）
├── engine.py             # 纯计算引擎（无 IO，可独立测试）
├── models.py             # dataclass / enum / NamedTuple（数据模型）
├── repository.py         # 持久化层（DuckDB 读写）
└── {可选子目录}/          # 模块特有扩展
```

* `pipeline.py`：唯一入口，只做"加载 → 调用 service → 持久化 → 产物输出"。
* `service.py`：OOP 门面类，构造函数注入 `Config` + `Repository`。封装 engine 调用和业务流程。
* `engine.py`：纯函数/纯类，输入 dataclass 输出 dataclass，无 IO 依赖。核心算法放这里。
* `models.py`：所有 dataclass、enum、TypedDict 集中定义。
* `repository.py`：DuckDB 读写封装，SQL 只出现在这里。

### 1.2 全局共享层

```
src/
├── core/                          # 跨模块基础设施
│   ├── __init__.py
│   ├── base.py                    # BasePipeline, BaseService, BaseRepository 抽象基类
│   ├── protocols.py               # Protocol 定义（依赖注入接口）
│   ├── exceptions.py              # 统一异常体系（DataNotReadyError, GateFailError 等）
│   └── types.py                   # 共享类型别名
├── shared/                        # 跨模块共享计算
│   ├── __init__.py
│   ├── zscore.py                  # Z-Score 归一化（统一 (z+3)/6×100 实现）
│   ├── execution_model.py         # 成交模型（fill_probability, impact_cost — Trading/Backtest 共用）
│   └── fee_calculator.py          # 费用计算（commission, stamp_tax — Trading/Backtest 共用）
├── models/                        # 全局枚举 & 共享模型
│   ├── __init__.py
│   └── enums.py                   # RecommendationGrade, RotationStatus, CycleState 等
```

### 1.3 各模块具体结构

**数据层** `src/data/`：保留现有 adapters/models/repositories 子目录（已是最规范的模块），补 service.py。
**核心算法** `src/algorithms/{mss,irs,pas,validation}/`：统一为 pipeline + service + engine + models + repository。
**Integration** `src/algorithms/integration/`：从 `src/integration/` 移入 algorithms 下（它是核心算法，不是基础设施）。
**Backtest** `src/backtest/`：增加 engine.py + service.py + models.py + repository.py + adapters/qlib_adapter.py。
**Trading** `src/trading/`：增加 engine.py + service.py + models.py + repository.py + risk/risk_manager.py。
**Analysis** `src/analysis/`：增加 engine.py + service.py + models.py + repository.py + reports/daily_report.py。
**GUI** `src/gui/`：重组为 pages/ + services/ + components/ + models/ + utils/ 四层。
**Pipeline 编排** `src/pipeline/`：保留 main.py（ENH-01 统一入口）+ scheduler.py。

## 2. 新螺旋路线图

原始路线图 S0-S6 + S3a + S7a 的骨架保留，但每个 Spiral 内容因重建而大幅扩充。新路线图编号为 R0-R9（R = Rebuild）。

### 依赖关系总图

```
R0 工程基座
 ↓
R1 数据层重建  ←─────────────────────┐
 ↓                                    │
R2 MSS 重建                           │
 ↓                                    │
R3 IRS + PAS 重建  ───────────────────┤ （数据依赖）
 ↓                                    │
R4 Validation + Integration 重建      │
 ↓                                    │
R5 Backtest 重建 (Qlib)               │
 ↓                                    │
R6 Trading 重建  ─── 共享 execution_model/fee_calculator
 ↓
R7 Analysis 重建
 ↓
R8 GUI 重建
 ↓
R9 增强包 + 稳定化 + 文档收口
```

### R0 工程基座 (Foundation)

**目标**：建立标准化项目骨架，所有后续模块在此骨架上实现。
**映射**：新增阶段，原路线图无对应。
**产出**：
* `src/core/` 全套基类（BasePipeline, BaseService, BaseRepository）+ Protocol + 异常体系
* `src/shared/` 共享计算模块（zscore.py, execution_model.py, fee_calculator.py）
* `src/models/enums.py` 完善全局枚举（补齐 ValidatedFactor, PositionAdvice, CycleState 等）
* 目录骨架搭建：所有模块的 `__init__.py` + 空文件占位
* `pyproject.toml` / `setup.cfg` 整理
* `tests/` 目录标准化：`tests/unit/{module}/` + `tests/contracts/{module}/` + `tests/canary/`
**工期**：3-4 天

### R1 数据层重建 (Data Layer)

**目标**：修复 14 项 SOS 偏差，L1/L2 数据完全可信。
**映射**：对应 S0（CP-01）。
**SOS 覆盖**：sos-数据篇 全部 14 项。
**关键任务**：
* 修复 5 项 P0 快照计算逻辑错误（cascade 根因）
* 修复 5 项 P1 功能/命名不一致
* 修复 4 项 P2 路径/结构偏差
* 补 `src/data/service.py`（DataService OOP 门面）
* 确保 `market_snapshot` / `industry_snapshot` / `stock_gene_cache` 数据正确
**验证**：抽取 3 个交易日，逐字段比对快照输出与设计公式。
**工期**：5-7 天

### R2 MSS 重建

**目标**：MSS 代码 OOP 化 + 文档修正 + 补齐缺失防御。
**映射**：对应 S1（CP-02）。
**SOS 覆盖**：sos-mss 全部 12 项。
**关键任务**：
* 重写 `mss-information-flow.md` §2.6/§3/§6（3 项 P0 文档矛盾）
* 补 `MssService` OOP 门面 + 注入 `MssRepository`
* P1-1：Z-Score baseline 标注当前硬编码状态，登记技术债（parquet 加载为 Phase-2 目标）
* P1-2：补必备字段缺失检查（`_to_int/_to_float` 静默吞零问题）
* P2-1：修复返回类型注解 `MssScoreResult → MssPanorama`
* P2-2：更新 `mss-data-models.md` 补齐质量字段
* P3-1~P3-5：预警标注未实现、PositionAdvice 枚举、trend_quality 补充等
**验证**：契约测试 + 温度曲线 3 日重跑比对。
**工期**：4-5 天

### R3 IRS + PAS 重建

**目标**：两个评分系统的因子计算完全对齐设计。这是工作量最大的一个阶段。
**映射**：对应 S2 前半段（CP-03/04）。
**SOS 覆盖**：sos-irs篇 全部 8 项 + sos-pas 全部 16+ 项。

**IRS 关键任务**：
* C1/C2：修复估值因子和龙头因子归一化路径（"先 z 后合再 z" vs 当前"先合后 z"）
* C3：calculator.py 恢复 style_bucket 生命周期映射
* M1/M2/M3：数据源语义对齐 + quality_flag 补齐
* m1/m2：输出列清理 + docstring 修正
* 补 `IrsService` OOP 门面
* `calculator.py` 与 `pipeline.py` 对齐，消除副本漂移

**PAS 关键任务（四批修复）**：
* 第一批 数据源：读取 `raw_daily_basic` 真实 turnover_rate + `raw_limit_list` 真实涨跌停状态
* 第二批 三因子公式：
    * 牛股基因权重 0.4/0.3/0.3 + max_pct_chg 去掉 /0.30 天花板
    * 结构因子恢复 trend_continuity_ratio（0.4/0.3/0.3）
    * 行为因子恢复 limit_up_flag + pct_chg_norm ±20% + 权重 0.4/0.3/0.3
    * volume_quality 恢复三子组件（量比 60% + 换手率 25% + 收盘保真度 15%）
    * breakout_ref 随窗口切换 + 突破强度改为简单比率
* 第三批 输出模型：主表补 stock_name/industry_code/entry/stop/target + 中间表补齐 18 字段
* 第四批 文档：docstring 更新 + baseline parquet 机制
* 补 `PasService` OOP 门面

**验证**：3-5 个交易日全量运行，比对评分分布 + 人工抽检 10 只标的因子中间值。
**工期**：12-15 天（本路线图最大工作量阶段）

### R4 Validation + Integration 重建

**目标**：Validation 从"启发式代理"重写为"真实截面验证 + WFA"；Integration 修复评分和模式语义。
**映射**：对应 S2 后半段（CP-10/05）。
**SOS 覆盖**：sos-validation 全部 13 项 + sos-Integration 全部 19 项。

**Validation 关键任务（近乎完全重写）**：
* 实现 `ValidatedFactor` 枚举（15 个因子，与 MSS/IRS/PAS 内部因子硬绑定）
* 重写 IC 计算：逐日截面 `factor_series` vs `future_returns`，按 `(trade_date, stock_code)` 对齐
* 实现真实 ICIR = `mean(ic_series) / std(ic_series)`
* 实现真实衰减：decay_1d/3d/5d/10d 多持有期
* 实现 positive_ic_ratio + coverage_ratio
* 修正 Regime 分类：`hot_or_volatile`(temp≥70 OR vol≥0.035) 而非 `hot_stable`(temp≥75 AND vol≤0.02)
* 修正 Regime 阈值调整方向（热/波动→放宽IC收紧ICIR；冷/安静→收紧覆盖率）
* 实现真实双窗口 WFA（long_cycle 252/63/63 + short_cycle 126/42/42）
* Gate 4 维判定（IC / ICIR / positive_ic_ratio / coverage_ratio）
* 补 `ValidationService` + `ValidationRepository` OOP 层

**Integration 关键任务**：
* P0：strength_factor 应用 + IRS 方向来源修正 + 仓位乘子补齐 + neutrality 加权 + cycle 风控参数对齐 + position_size 公式修正 + 情绪温度对 final_score 调制
* P1：dual_verify / complementary 模式语义修正
* P2：推荐列表筛选/排序修正 + Gate 回退逻辑 + 异常处理
* P3：数据模型补齐 + Regime 参数 + 信息流文档更新
* 补 `IntegrationService` OOP 门面

**验证**：端到端信号链测试（Data → MSS/IRS/PAS → Validation → Integration → 检查 integrated_recommendation 28 字段）。
**工期**：10-12 天

### R5 Backtest 重建 (Qlib 主线)

**目标**：可信的回测结果，Qlib 为主线引擎。
**映射**：对应 S3 + S3a（CP-06/09 + ENH-09/10）。
**SOS 覆盖**：sos-backtest 全部 19 项 + sos-enhancements ENH-09。

**关键任务**：
* **Qlib 适配层** `src/backtest/adapters/qlib_adapter.py`：将 integrated_recommendation 映射为 Qlib 信号 + 读取 Qlib 标准回测结果
* **本地引擎保留为 fallback** `src/backtest/adapters/local_engine.py`：从 pipeline.py 重构
* **卖出逻辑重写**：条件触发退出（止损/止盈/时限平仓），优先级 stop_loss > take_profit > time_exit，跌停/停牌顺延
* **max_drawdown 公式修正**：峰谷追踪 `(equity_t - peak_t) / peak_t`
* **total_return 修正**：基于期末总权益（含未平仓市值）
* **信号过滤补齐**：4 层（final_score / recommendation / direction / risk_reward_ratio）
* **integration_mode 模式过滤**：按 R4 输出的 top_down / bottom_up / dual_verify / complementary 模式消费信号；BU 模式需查 `pas_breadth_daily.pas_sa_ratio` 做活跃度门控，不足时回退 TD 并标记 `warn_mode_fallback`
* **Gate 粒度修正**：逐日检查，当日 FAIL 仅跳过当日
* **仓位基数修正**：equity（cash + 持仓市值）而非 cash
* **核心绩效指标实现**：annual_return, volatility, sharpe, sortino, calmar, profit_factor, win_rate
* **equity_curve 持久化**：写入 DuckDB 供 Analysis 消费
* **逐笔费用持久化**：commission/stamp_tax/impact_cost 写入 backtest_trade_records
* **hold_days 字段**：买卖配对后计算并持久化
* **max_positions 约束**：回测循环中实际执行
* **成交价滑点**：开盘价 ± slippage
* **BacktestEngine / BacktestService / BacktestRepository** OOP 层
* **A/B/C 对照框架**（ENH-06）
* **数据采集增强**（ENH-10）：分批下载 + 断点续传

**验证**：选 3 个月区间运行，对比 Qlib 输出与本地引擎输出，检查绩效指标合理性。
**工期**：12-14 天

### R6 Trading 重建

**目标**：纸上交易与回测共享成交模型和信号过滤逻辑。
**映射**：对应 S4（CP-07/09）。
**SOS 覆盖**：sos-trading 全部 26 项。

**关键任务**：
* P0-1：复用 `src/shared/execution_model.py`（从 Backtest 提取的 fill_probability/impact_cost）
* P0-2：信号过滤与 Backtest 统一（4 层过滤）
* P0-3：补齐单股仓位上限 + 行业集中度检查
* P0-4：信号字段读取补齐（stop/target/neutrality）
* P1：trade_records / positions 字段对齐 + 费用计算统一
* P2：设计文档状态更新 + risk_events 纳入设计 + RejectReason 枚举同步
* P3（远期）：止损/止盈多日持仓策略、Regime 阈值解析
* **TradingEngine / TradingService / TradingRepository / RiskManager** OOP 层

**验证**：纸上交易 5 个交易日，检查订单/持仓/风控日志。
**工期**：7-8 天

### R7 Analysis 重建

**目标**：从"硬编码 0"到真实绩效计算 + 信号归因 + 日报。
**映射**：对应 S5 前半段（CP-08）。
**SOS 覆盖**：sos-analysis 全部 16 项。

**关键任务**：
* 从 equity_curve（R5 已持久化）计算完整绩效指标
* 信号归因用 forward_return_5d 而非 final_score 差值
* 日报生成（Markdown 模板：市场概况 + 行业轮动 + 信号统计 + 绩效摘要）
* 风险分析（neutrality 三级分布 + HHI 行业集中度）
* Dashboard 快照 JSON 输出
* CSV / Markdown 导出
* 14 个 dataclass 数据模型
* **AnalysisEngine / AnalysisService / AnalysisRepository** OOP 层

**验证**：对 R5 回测结果运行 Analysis，检查指标非零且与手算一致。
**工期**：6-8 天

### R8 GUI 重建

**目标**：完全按设计的 4 层架构重建。
**映射**：对应 S5 后半段（CP-08/09）。
**SOS 覆盖**：sos-gui 全部 25 项。

**关键任务**：
* 目录重组：`pages/ + services/ + components/ + models/ + utils/`
* 7 个页面模块（Dashboard / Market / Industry / Stock / Backtest / Trading / Analysis）
* 5 个 Service 层：DataService(repository) + CacheService + FilterService + ChartService + ExportService
* 数据模型：GuiRunResult / IntegratedPageData / TemperatureChartData / ChartZone / GuiConfig 等
* FilterConfig 真正生效（当前参数被接受但从未使用）
* FreshnessMeta 真实缓存年龄（非 now() 填充）
* 回测数据字段名匹配（backtest_id vs backtest_name、annual_return 等）
* `run_minimal()` CP-09 最小闭环入口

**验证**：Streamlit 启动，逐页面检查数据展示正确性。
**工期**：8-10 天

### R9 增强包 + 稳定化

**目标**：ENH-01~11 落地 + 全链路一致性验证 + 文档收口。
**映射**：对应 S6 + S7a。
**SOS 覆盖**：sos-enhancements 全部 15 项。

**关键任务**：
* ENH-01 统一 CLI 入口 `eq run/mss/recommend/backtest/trade/gui`
* ENH-02 数据预检 + validate_token() + 限流守卫
* ENH-03 失败产物协议（error_manifest 补齐 error_level/failed_step/timestamp）
* ENH-04 契约测试目录 `tests/contracts/`
* ENH-05 金丝雀数据包 `tests/canary/`
* ENH-07 L4 产物标准化
* ENH-08 设计冻结检查（SHA256 锚点）
* ENH-11 定时调度器
* 全链路重跑一致性验证（S0→R1 已修复的数据 → 跑完整链路 → 检查每一层输出）
* 设计文档最终收口（information-flow / data-models 全部与重建后代码对齐）
* 技术债清偿记录
* **监控模块重建** `src/monitoring/quality_monitor.py`：实现设计定义的 6 层监控（数据/因子/Validation/集成/交易/系统）、9 条关键指标与阈值、P0/P1/P2 三级告警 + 升级规则、统一通知路径（控制台 + 日志）

**工期**：7-10 天

## 3. 实现卡

### CARD-R0: 工程基座

**前置条件**：无
**交付物**：
- [ ] `src/core/base.py` — BasePipeline / BaseService / BaseRepository 抽象基类
- [ ] `src/core/protocols.py` — Protocol 定义
- [ ] `src/core/exceptions.py` — 统一异常体系（从 `src/config/exceptions.py` 迁移+扩展）
- [ ] `src/core/types.py` — TradeDate, StockCode 等类型别名
- [ ] `src/shared/zscore.py` — 统一 Z-Score 归一化
- [ ] `src/shared/execution_model.py` — 共享成交模型
- [ ] `src/shared/fee_calculator.py` — 共享费用计算
- [ ] `src/models/enums.py` — 补齐 ValidatedFactor(15), PositionAdvice, CycleState, IntegrationMode, BacktestState, LiquidityTier 等
- [ ] 目录骨架：所有模块的空文件占位
- [ ] `tests/` 目录标准化
- [ ] CI 基础配置（lint/typecheck 能跑通）

### CARD-R1: 数据层重建

**前置条件**：R0 完成
**交付物**：
- [ ] 修复 P0-1~P0-5 快照计算逻辑（market_snapshot / industry_snapshot）
- [ ] 修复 P1-1~P1-5 功能/命名一致性
- [ ] 修复 P2-1~P2-4 路径/结构
- [ ] `src/data/service.py` — DataService OOP 门面
- [ ] 契约测试 `tests/contracts/test_data_layer.py`
- [ ] 3 个交易日快照验证报告

### CARD-R2: MSS 重建

**前置条件**：R1 完成（依赖正确的 market_snapshot）
**交付物**：
- [ ] 重写 `mss-information-flow.md` §2.6 / §3 / §6
- [ ] `src/algorithms/mss/service.py` — MssService
- [ ] `src/algorithms/mss/models.py` — 从 engine.py 提取 dataclass
- [ ] engine.py 补输入验证（P1-2）
- [ ] engine.py 修复返回类型注解（P2-1）
- [ ] 更新 `mss-data-models.md` 补齐质量字段（P2-2）
- [ ] 契约测试 `tests/contracts/test_mss.py`

### CARD-R3: IRS + PAS 重建

**前置条件**：R1 完成（依赖正确的 industry_snapshot / stock_gene_cache / raw_daily）

**IRS 交付物**：
- [ ] 修复归一化路径 C1/C2（先 z 后合再 z）
- [ ] 修复 calculator.py C3（恢复 style_bucket）
- [ ] 修复数据源 M1/M2/M3
- [ ] `src/algorithms/irs/service.py` — IrsService
- [ ] `src/algorithms/irs/models.py` — 从 pipeline.py 提取 dataclass
- [ ] pipeline.py 与 calculator.py 对齐
- [ ] 契约测试 `tests/contracts/test_irs.py`

**PAS 交付物**：
- [ ] 数据源：读取 raw_daily_basic + raw_limit_list
- [ ] 牛股基因因子：权重 0.4/0.3/0.3 + max_pct_chg 修正
- [ ] 结构因子：恢复 trend_continuity_ratio + breakout_ref 窗口化 + 突破强度简单比率
- [ ] 行为因子：恢复 limit_up_flag + pct_chg_norm ±20% + volume_quality 三子组件
- [ ] 输出模型补全（主表 + 中间表）
- [ ] `src/algorithms/pas/service.py` — PasService
- [ ] `src/algorithms/pas/models.py`
- [ ] `src/algorithms/pas/engine.py` — 纯计算从 pipeline.py 分离
- [ ] 契约测试 `tests/contracts/test_pas.py`
- [ ] 评分分布验证报告

### CARD-R4: Validation + Integration 重建

**前置条件**：R2 + R3 完成（依赖正确的 MSS/IRS/PAS 输出）

**Validation 交付物**：
- [ ] `ValidatedFactor` 枚举（15 因子）
- [ ] 真实 IC/RankIC 计算（因子 vs future_returns 截面对齐）
- [ ] 真实 ICIR = mean/std
- [ ] 真实衰减 decay_1d/3d/5d/10d
- [ ] positive_ic_ratio + coverage_ratio
- [ ] Regime 分类修正
- [ ] WFA 双窗口实现（long_cycle 252/63/63 + short_cycle 126/42/42）
- [ ] Gate 4 维判定
- [ ] `src/algorithms/validation/service.py` + `engine.py` + `models.py` + `repository.py`
- [ ] 契约测试

**Integration 交付物**：
- [ ] 7 项 P0 算法修正（strength_factor / IRS方向 / 仓位乘子 / neutrality / cycle风控 / position_size / 温度调制）
- [ ] 模式语义修正（dual_verify / complementary）
- [ ] 筛选排序修正 + Gate 回退
- [ ] `src/algorithms/integration/` 目录迁移（从 src/integration/）
- [ ] `src/algorithms/integration/service.py` + `engine.py` + `models.py` + `repository.py`
- [ ] 端到端信号链测试

### CARD-R5: Backtest 重建

**前置条件**：R4 完成（依赖正确的 integrated_recommendation + validation_gate_decision）
**交付物**：
- [ ] `src/backtest/adapters/qlib_adapter.py` — Qlib 适配层
- [ ] `src/backtest/adapters/local_engine.py` — 本地引擎（从 pipeline.py 重构）
- [ ] 卖出逻辑重写（止损/止盈/时限，优先级判定，跌停顺延）
- [ ] max_drawdown / total_return 公式修正
- [ ] 信号 4 层过滤
- [ ] integration_mode 模式过滤与 BU 活跃度门控回退
- [ ] Gate 逐日粒度
- [ ] 仓位基数 = equity
- [ ] 核心绩效指标（7 项）
- [ ] equity_curve + 逐笔费用 + hold_days 持久化
- [ ] max_positions 约束
- [ ] 成交价滑点
- [ ] `src/backtest/service.py` + `engine.py` + `models.py` + `repository.py`
- [ ] A/B/C 对照框架
- [ ] ENH-10 数据采集增强（分批下载 + 断点续传）
- [ ] 3 月区间回测验证报告

### CARD-R6: Trading 重建

**前置条件**：R5 完成（共享 execution_model / fee_calculator 已在 R0 建立，R5 已验证）
**交付物**：
- [ ] 复用 shared/execution_model.py + fee_calculator.py
- [ ] 信号过滤与 Backtest 统一
- [ ] 风控检查补齐（单股仓位 + 行业集中度 + 总仓位）
- [ ] 信号字段读取补齐
- [ ] trade_records / positions 字段对齐
- [ ] `src/trading/service.py` + `engine.py` + `models.py` + `repository.py` + `risk/risk_manager.py`
- [ ] 5 个交易日纸上交易验证

### CARD-R7: Analysis 重建

**前置条件**：R5 完成（依赖 equity_curve + 逐笔费用持久化）
**交付物**：
- [ ] 绩效指标计算（从 equity_curve）
- [ ] 信号归因（forward_return_5d）
- [ ] 风险分析（neutrality 分布 + HHI）
- [ ] 日报生成（Markdown 模板）
- [ ] Dashboard 快照 JSON
- [ ] CSV 导出
- [ ] 14 个 dataclass
- [ ] `src/analysis/service.py` + `engine.py` + `models.py` + `repository.py` + `reports/daily_report.py`
- [ ] 指标非零验证

### CARD-R8: GUI 重建

**前置条件**：R7 完成（依赖 Analysis 产出的 dashboard_snapshot）
**交付物**：
- [ ] 目录重组为 pages/ + services/ + components/ + models/ + utils/
- [ ] 7 个页面模块
- [ ] 5 个 Service（Data/Cache/Filter/Chart/Export）
- [ ] 数据模型（GuiRunResult / IntegratedPageData / ChartZone / GuiConfig 等）
- [ ] FilterConfig 生效 + FreshnessMeta 真实缓存
- [ ] run_minimal() CP-09 入口
- [ ] 回测字段名匹配
- [ ] Streamlit 逐页面验证

### CARD-R9: 增强包 + 稳定化

**前置条件**：R8 完成
**交付物**：
- [ ] ENH-01 统一 CLI + ENH-02 预检 + ENH-03 失败产物 + ENH-04 契约测试 + ENH-05 金丝雀
- [ ] ENH-07 L4 产物标准化 + ENH-08 设计冻结检查 + ENH-11 调度器
- [ ] 全链路重跑一致性报告
- [ ] 设计文档最终收口
- [ ] 技术债清偿记录
- [ ] 监控模块重建 `src/monitoring/quality_monitor.py`（6 层监控 + 9 条指标 + 3 级告警）

## 4. 工期估算总览

| 阶段 | 天数 | 累计 | 核心交付 |
|------|------|------|----------|
| R0 工程基座 | 3-4 | 4 | 骨架 + 共享层 |
| R1 数据层 | 5-7 | 11 | L1/L2 数据可信 |
| R2 MSS | 4-5 | 16 | 温度/周期/趋势可信 |
| R3 IRS+PAS | 12-15 | 31 | 行业分/个股分可信 |
| R4 Valid+Integ | 10-12 | 43 | Gate 可信 + 推荐信号可信 |
| R5 Backtest | 12-14 | 57 | 回测结果可信 (Qlib) |
| R6 Trading | 7-8 | 65 | 纸上交易可执行 |
| R7 Analysis | 6-8 | 73 | 绩效非零 + 日报 |
| R8 GUI | 8-10 | 83 | 展示层完整 |
| R9 增强+稳定 | 7-10 | 93 | 全链路闭环 |

**总计约 75-93 个工作日**，取中值 ~84 天 ≈ 4 个月。

## 5. 执行纪律

1. **每阶段闭环**：run + test + artifact + review（继承原 Spiral 五件套）
2. **不跨阶段施工**：R(N) 未通过验证不启动 R(N+1)
3. **代码向设计对齐**：遇到冲突，先确认设计正确性，再改代码。若设计确需修正，先改设计、记录变更、再改代码。
4. **OOP 强制**：新代码必须是 Service + Engine + Repository + Models 四件套。pipeline.py 只做编排。
5. **共享代码优先**：Trading/Backtest 的成交模型、费用计算、信号过滤必须走 `src/shared/`，禁止各自实现。
6. **提交规范**：每个 CARD 对应一个 git branch `rebuild/r{N}-{module}`，完成后 PR 合入 main。
7. **Governance 同步**：每阶段收口时更新以下文件（继承原 Spiral 同步规则）：
   - `Governance/specs/spiral-s{N}/final.md`（阶段总结）
   - `Governance/record/development-status.md`（进度状态）
   - `Governance/record/debts.md`（技术债账本）
   - `Governance/record/reusable-assets.md`（可复用资产）
   - `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`（仅状态）
8. **入口文档同步**：路径变更、流程变更、主计划状态变更时，同步更新 `AGENTS.md`、`CLAUDE.md`、`README.md`、`README.en.md`、`WARP.md`。不发生上述变化时不做无效改写。
