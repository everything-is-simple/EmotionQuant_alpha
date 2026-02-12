# EmotionQuant 涡旋演进路线图 (Vortex Evolution Roadmap)

**版本**: v1.3.1
**创建日期**: 2026-02-12
**最后更新**: 2026-02-12
**状态**: Candidate（待审批）
**适用范围**: S0-S6 全周期螺旋实施
**适用对象**: 单开发者、个人使用

---

## 0. 本文档是什么

本文档是 EmotionQuant 系统的**螺旋型实施总路线图**，融合业界优秀 Roadmap 模板要素与本项目治理体系，提供从 S0 到 S6 的完整演进视图。

### 0.1 优秀路线图的关键要素（本文档遵循）

1. **愿景锚定** — 每个 Spiral 必须回答"为什么做"，对齐系统定位。
2. **里程碑与时间线** — 可视化进度，以 Spiral 为时间单位（默认 7 天/圈）。
3. **依赖链与遗产链** — 显式标注上下游依赖与产出资产流转。
4. **进度与状态追踪** — 每个 Spiral 有状态标记，支持实时看板。
5. **风险矩阵与降级策略** — 提前识别阻塞并给出退路。
6. **验收门禁** — 每个 Spiral 有明确的 Go/No-Go 判定标准。
7. **活文档** — 随执行演进持续更新，不做一次性冻结。

### 0.2 上位约束

- 系统铁律：`Governance/steering/系统铁律.md`
- 核心原则：`Governance/steering/CORE-PRINCIPLES.md`
- 6A 工作流：`Governance/steering/6A-WORKFLOW.md`
- CP 主控：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- 改进主计划：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`

### 0.3 与已有文档的关系

- 历史草稿已完成收敛，本目录以本文件与 `Governance/SpiralRoadmap/DEPENDENCY-MAP.md` 作为正式桥梁入口。
- 本文档作为 `Governance/SpiralRoadmap/` 目录主入口，用于螺旋执行可视化与里程碑管理。
- 执行权威仍以 `docs/design/enhancements/eq-improvement-plan-core-frozen.md` 为最终口径，本文档为其可视化执行伴侣。

---

## 1. 系统愿景与路线目标

### 1.1 系统定位

EmotionQuant 是面向中国 A 股的**情绪驱动量化系统**。情绪因子为主信号来源，技术指标仅可用于辅助特征与对照实验，不得独立触发交易。

### 1.2 路线目标

通过 7 个螺旋周期（S0-S6），从"零可运行"推进到"可持续运营"：

```
S0 数据闭环 → S1 市场信号 → S2 信号生成+集成 → S3 回测闭环 → S4 纸上交易 → S5 可视化 → S6 稳定化
```

每个 Spiral 交付一个**可运行闭环**，禁止"看起来完成"。

---

## 2. 全局执行契约

> 以下规则在所有 Spiral 中生效，不再在每个 Spiral 章节重复。

### 2.1 冻结区（只允许实现，不允许改语义）

1. 情绪优先与"单指标不得独立决策"。
2. MSS / IRS / PAS / Validation / Integration 核心公式与命名。
3. L1-L4 数据契约与关键业务表字段。
4. A 股规则：T+1、涨跌停（主板10%/创业板科创板20%/ST 5%）、交易时段、整手、费用模型、申万行业。

### 2.2 切片预算

- 一圈仅 1 个主目标。
- 一圈仅 1-3 个 CP Slice。
- 单 Task 超过 1 天必须拆分。
- 超出预算则拆为子圈，各留五件套证据。

### 2.3 五件套退出条件（每圈必须）

| 证据 | 要求 |
|---|---|
| run | 至少 1 条可复制命令 |
| test | 至少 1 组自动化测试 |
| artifact | 至少 1 个结构化产物 |
| review | `Governance/specs/spiral-s{N}/review.md` |
| sync | 最小同步 5 文件 |

### 2.4 错误分级

| 级别 | 定义 | 处理 |
|---|---|---|
| P0 | 核心输入缺失、契约破坏、合规违规 | 阻断 |
| P1 | 局部数据缺失、局部计算失败 | 降级 + 标记 |
| P2 | 非关键异常 | 重试 + 记录 |

### 2.5 Strict 6A 升级触发

- S4 默认 Strict 6A。
- S3 / S6 在以下条件触发：数据契约破坏性变化、Validation Gate 规则变更、新关键外部依赖进入主路径。

### 2.6 分类定义（用于工时分配）

- **核心算法**：MSS/IRS/PAS/Validation/Integration 的算法实现与验证。
- **核心基础设施**：Data/Backtest/Trading/GUI/Analysis 的编排、配置、适配、可运行能力。
- **系统外挂**：ENH-01~09，对核心语义不做改写的守卫、对照、可视化、回归资产。

---

## 3. 路线总览看板

### 3.1 Spiral 进度看板

| Spiral | 代号 | 主目标 | 推荐 CP 组合 | 预估工时 | 状态 |
|---|---|---|---|---|---|
| S0 | 🌱 数据根基 | 数据最小闭环 | CP-01 | 4.5d | 🚧 待启动 |
| S1 | 🌡️ 市场脉搏 | MSS 闭环 | CP-01, CP-02 | 3.5d | 📋 未开始 |
| S2 | 📡 信号生成 | 信号生成闭环（含集成） | CP-03, CP-04, CP-10, CP-05 | 5.8d | 📋 未开始 |
| S3 | 🔬 回测闭环 | 回测 + 分析闭环 | CP-10, CP-06, CP-09 | 3.9d | 📋 未开始 |
| S4 | 📜 纸上实战 | 纸上交易闭环（Strict 6A） | CP-07, CP-09 | 4.5d | 📋 未开始 |
| S5 | 🖥️ 可见之眼 | GUI + 日报闭环 | CP-08, CP-09 | 3.0d | 📋 未开始 |
| S6 | 🔒 稳态收敛 | 稳定化 + 债务清偿 | CP-10, CP-07, CP-09 | 4.0d | 📋 未开始 |
| **合计** | | | | **29.2d** | |

> 说明：S2 为父圈视图，执行时拆分为 S2a/S2b 子圈，保证每子圈满足“1-3 个 Slice”约束。

### 3.2 累计能力演进图

```
S0  ██░░░░░░░░░░░░  数据可读
S1  █████░░░░░░░░░  市场温度可算
S2  █████████░░░░░  信号可出 + 推荐可生成
S3  ██████████░░░░  回测可验 + 绩效可比
S4  ████████████░░  交易可模拟 + 风控可执行
S5  █████████████░  结果可视化 + 日报可导
S6  ██████████████  全链路可复现 + 可持续运行
```

### 3.3 三分类工时分布

> 分类口径对齐 `docs/design/README.md` 三层结构。核心算法 = MSS/IRS/PAS/Validation/Integration；核心基础设施 = Data/Backtest/Trading/GUI/Analysis；系统外挂 = ENH-01~09。

| Spiral | 核心算法 | 核心基础设施 | 系统外挂(ENH) | 总计 |
|---|---:|---:|---:|---:|
| S0 | 0d (0%) | 3.0d (67%) | 1.5d (33%) | 4.5d |
| S1 | 2.0d (57%) | 0.8d (23%) | 0.7d (20%) | 3.5d |
| S2 | 4.9d (84%) | 0d (0%) | 0.9d (16%) | 5.8d |
| S3 | 0d (0%) | 2.1d (54%) | 1.8d (46%) | 3.9d |
| S4 | 0d (0%) | 3.3d (73%) | 1.2d (27%) | 4.5d |
| S5 | 0d (0%) | 2.2d (73%) | 0.8d (27%) | 3.0d |
| S6 | 1.0d (25%) | 2.0d (50%) | 1.0d (25%) | 4.0d |
| **合计** | **7.9d (27%)** | **13.4d (46%)** | **7.9d (27%)** | **29.2d** |

> 核心算法集中在 S1-S2（三三制信号全链路）；基础设施分布在 S0/S3-S5（数据/回测/交易/展示）；外挂均匀分布，每圈 16%-46%，全局占比 27%。

---

## 4. 依赖链与遗产链

### 4.1 Spiral 间依赖关系

```
S0 ──→ S1 ──→ S2 ──→ S3 ──→ S4 ──→ S5 ──→ S6
│       │       │       │       │       │       │
│       │       │       │       │       │       ├── 全链路重跑一致性
│       │       │       │       │       ├── Dashboard + 日报
│       │       │       │       ├── 订单/持仓/风控
│       │       │       ├── 推荐 + 回测 + 绩效
│       │       ├── IRS + PAS + Gate + Integration
│       ├── MSS 温度/周期/趋势
├── L1/L2 数据集
```

### 4.2 遗产流转链（Heritage Chain）

每个 Spiral 产出的可复用资产，及其下游消费者：

| 产出 Spiral | 遗产资产 | 消费 Spiral |
|---|---|---|
| S0 | `TuShareFetcher`（统一采集入口） | S1, S2 |
| S0 | `eq run` CLI 入口 | S1-S6 全部 |
| S0 | canary 数据包（离线回归） | S1-S6 全部 |
| S0 | `market_snapshot` / `industry_snapshot` L2 表 | S1, S2 |
| S1 | `normalize_zscore` 标准化实现 | S2 |
| S1 | `mss_panorama` 输出表 | S2 (Integration) |
| S1 | 周期/趋势判定模板 | S2 (IRS/PAS 参考) |
| S2 | `irs_industry_daily` / `stock_pas_daily` | S2 (Integration), S3 |
| S2 | `validation_gate_decision` | S2 (Integration 前置门禁), S3 |
| S2 | `integrated_recommendation` | S3 (回测), S4 (Trading) |
| S2 | `validation_weight_plan` 桥接表 | S3, S6 |
| S3 | 向量化回测器 | S4 (口径对齐), S6 (重跑) |
| S3 | `performance_metrics` | S5 (GUI 展示) |
| S3 | A/B/C 对照基线 | S6 (权重对照) |
| S4 | `trade_records` / `positions` / `risk_events` | S5 (GUI 展示) |
| S4 | 回测-交易口径一致性测试 | S6 (重跑验证) |
| S5 | GUI 基线模板 | S6 (稳态展示) |
| S5 | 日报模板与归档命名 | S6 (运营基线) |
| S6 | 全链路重跑基线 | 后续迭代 |
| S6 | 权重更新证据链 | 后续迭代 |

### 4.3 CP 跨 Spiral 参与矩阵

| CP | S0 | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|---|
| CP-01 Data | ★ | ○ | | | | | |
| CP-02 MSS | | ★ | | | | | |
| CP-03 IRS | | | ★ | | | | |
| CP-04 PAS | | | ★ | | | | |
| CP-05 Integration | | | ★ | | | | |
| CP-06 Backtest | | | | ★ | | | |
| CP-07 Trading | | | | | ★ | | ○ |
| CP-08 GUI | | | | | | ★ | |
| CP-09 Analysis | | | | ★ | ○ | ★ | ○ |
| CP-10 Validation | | | ★ | ○ | | | ○ |

> ★ = 主要实现圈, ○ = 复用/扩展圈

---

## 5. S0 🌱 数据根基

### 5.1 使命

无稳定 L1/L2 输入，后续所有算法无法形成可验证结果。S0 的使命是建立**可复现的最小数据链路**。

### 5.2 范围

**In Scope**:
- `raw_daily / raw_daily_basic / raw_limit_list / raw_index_daily / raw_trade_cal` 最小可用
- `market_snapshot` 完整字段（含 `data_quality / stale_days / source_trade_date`）
- `industry_snapshot` 骨架字段
- `eq run` 统一入口与环境配置
- 数据根目录通过 `DATA_PATH` 环境变量注入（实际部署：`G:\EmotionQuant_data`，仓库外独立目录）

**Out Scope**:
- MSS / IRS / PAS 评分
- Validation Gate
- Backtest / Trading / GUI

### 5.3 任务分解

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S0-T1 CLI 与配置落地 | 外挂 ENH-01 | `eq run`、`.env.example`、Config 接线 | 没有统一入口无法闭环复现 | 0.8d |
| S0-T2 TuShare 采集实现 | 核心基础设施（含 ENH-02） | `TuShareFetcher` 可用拉取 | 数据源入口必须先通 | 1.0d |
| S0-T3 Parquet->DuckDB 入库 | 核心基础设施 | Repository 入库链路 | 后续算法统一读本地 | 1.0d |
| S0-T4 L2 快照计算 | 核心基础设施 | `market_snapshot / industry_snapshot` | MSS/IRS 输入前置依赖 | 1.0d |
| S0-T5 守卫与回归资产 | 外挂 ENH-03/04/05/08 | `error_manifest`、canary、freeze_check | 保证失败可追踪、离线可回归 | 0.7d |

### 5.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| `TUSHARE_TOKEN` 缺失/无效 | P0 | 立即阻断 |
| API 限流或网络抖动 | P2 | 重试3次 + 指数退避 |
| 非交易日无数据 | P1 | 回退最近交易日并标注 stale |
| Parquet/DuckDB 写入失败 | P0 | 阻断并写 error_manifest |
| 局部标的缺失 | P1 | 跳过并标注质量 |

### 5.5 验收门禁

1. `eq run --date 20260207 --source mock` 返回 0
2. `pytest tests/canary tests/contracts/test_data_* -q` 全通过
3. DuckDB 存在 `market_snapshot` 且字段契约完整
4. 失败流程能输出 `error_manifest.json`（含 `error_level`）
5. `freeze_check` 可执行并给出关键文档锚点结果

### 5.6 退出五件套

- **run**: `eq run --date {trade_date} --source mock`
- **test**: `pytest tests/canary tests/contracts/test_data_* -q`
- **artifact**: parquet + duckdb 表 + error_manifest
- **review**: `Governance/specs/spiral-s0/review.md`
- **sync**: 最小同步 5 文件

### 5.7 遗产产出

- 统一数据采集入口（TuShareFetcher）
- 统一运行入口（CLI）
- canary 数据夹（离线回归）
- 设计冻结锚点（防漂移）
- L2 快照表（S1/S2 直接消费）

### 5.8 降级策略

若 TuShare 不可用：以 mock 数据完成闭环，TuShare 接入延后到 S0 子圈。

---

## 6. S1 🌡️ 市场脉搏

### 6.1 使命

MSS 给出市场层主信号（温度/周期/趋势），是后续 Integration 的必需输入。S1 完成后，系统具备"感知市场情绪"的基础能力。

### 6.2 范围

**In Scope**:
- 六因子实现与温度合成（`0.17 / 0.34 / 0.34 / 0.05 / 0.05 / 0.05`）
- 周期判定（含 `unknown` 兜底）与趋势判定
- `mss_panorama` 落库与契约测试

**Out Scope**:
- IRS / PAS / Validation
- 交易触发逻辑

### 6.3 任务分解

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S1-T1 六因子引擎 | 核心算法 | `src/algorithms/mss/factors.py` | 没有因子就没有温度来源 | 1.0d |
| S1-T2 温度/周期/趋势 | 核心算法 | `src/algorithms/mss/engine.py` | 周期直接影响推荐等级规则 | 1.0d |
| S1-T3 Writer + CLI | 核心基础设施 | `mss_panorama` 与 `eq mss` | 没有落库无法被下游消费 | 0.8d |
| S1-T4 契约测试与可视化基础 | 外挂 ENH-04 | mss contract tests + L4 温度序列 | 防回归并为 S5 提前准备 | 0.7d |

### 6.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| `market_snapshot` 关键字段缺失 | P0 | 阻断并提示回到 S0 |
| 历史样本不足 | P1 | 分数置 50 并标记 cold_start |
| 温度越界 | P1 | 裁剪到 [0,100] 并告警 |
| 非交易日输入 | P0 | 阻断 |

### 6.5 验收门禁

1. `eq mss --date {trade_date}` 成功产出 `mss_panorama`
2. `pytest tests/contracts/test_mss_* -q` 通过
3. `temperature in [0,100]`、`neutrality in [0,1]`
4. 相同输入重复运行结果一致
5. 无交易触发字段（保持信号层边界）

### 6.6 退出五件套

- **run**: `eq mss --date {trade_date}`
- **test**: `pytest tests/contracts/test_mss_* -q`
- **artifact**: `mss_panorama`
- **review**: `Governance/specs/spiral-s1/review.md`
- **sync**: 最小同步 5 文件

### 6.7 遗产产出

- `normalize_zscore` 统一实现
- MSS 输出标准表
- 周期与趋势判定实现模板（IRS/PAS 可参考）

### 6.8 降级策略

若六因子中部分数据源不可用：先实现可用因子子集（最少 3 因子），缺失因子给等权回退值，标记 `degraded`。

---

## 7. S2 📡 信号生成

### 7.1 使命

完成行业层与个股层信号，建立因子验证门禁，并产出 TopN 推荐与集成输出。S2 结束后三三制（市场/行业/个股）信号全部就位且 `integrated_recommendation` 可追溯。

> 对齐 `Governance/Capability/SPIRAL-CP-OVERVIEW.md` S2 = CP-03, CP-04, CP-10, CP-05

### 7.2 范围

**In Scope**:
- IRS 六因子最小版（31 行业覆盖）
- PAS 三因子最小版（等级/方向/RR）
- Validation 因子门禁（IC / RankIC / ICIR / positive_ratio → PASS / WARN / FAIL）
- Integration baseline 集成输出（TopN 推荐 + `integrated_recommendation`）

**Out Scope**:
- 回测与绩效分析（放 S3）
- 权重 WFA（放 S6 CP10-S2）

### 7.3 任务分解

> 本段为 S2 父圈视图，合计覆盖 4 个 CP Slice（CP-03, CP-04, CP-10, CP-05）。根据 6A 约束（每圈 1-3 Slice），执行时必须拆为 S2a/S2b 子圈，各留五件套。

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S2-T1 `industry_snapshot` 补齐 + IRS 引擎 | 核心算法 | `irs_industry_daily` | 三三制行业层输入 | 1.3d |
| S2-T2 `stock_gene_cache` + PAS 引擎 | 核心算法 | `stock_pas_daily` | 三三制个股层输入 | 1.3d |
| S2-T3 Validation 因子门禁 | 核心算法 | `validation_gate_decision` | Integration 前置门禁 | 1.2d |
| S2-T4 Integration 引擎 + `validation_weight_plan` | 核心算法 | `integrated_recommendation` + baseline plan | 下游唯一信号入口 | 1.1d |
| S2-T5 契约测试与编排骨架 | 外挂 ENH-04 | `eq recommend` 命令 | 完整信号链路可复现 | 0.9d |

### 7.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| 行业覆盖不足 31 | P1 | 标记 stale，允许继续 |
| 估值样本不足 8 只 | P1 | 沿用前值，标记 cold_start |
| 个股停牌或缺行情 | P1 | 跳过该股 |
| Validation 输入缺失 | P0 | Gate=FAIL，阻断后续集成 |
| baseline plan 缺失 | P0 | 阻断（契约不完整） |

### 7.5 验收门禁

1. `irs_industry_daily` 覆盖 31 行业
2. `stock_pas_daily` 评分/等级/方向范围合法
3. `validation_gate_decision` 具备 PASS / WARN / FAIL + reason
4. `integrated_recommendation.final_score` 可追溯到 MSS/IRS/PAS + 权重
5. TopN 推荐可生成且集成输出可追溯

### 7.6 退出五件套

- **run**: `eq recommend --date {trade_date}`
- **test**: `pytest tests/contracts/test_irs_* tests/contracts/test_pas_* tests/contracts/test_validation_* tests/contracts/test_integration_* -q`
- **artifact**: `irs_industry_daily` + `stock_pas_daily` + `validation_gate_decision` + `integrated_recommendation`
- **review**: `Governance/specs/spiral-s2/review.md`
- **sync**: 最小同步 5 文件

### 7.7 遗产产出

- 行业与个股信号标准表
- Validation Gate 决策表与桥接表
- `integrated_recommendation` 统一推荐输出表
- S3 回测可直接消费的稳定集成输出

### 7.8 降级策略

S2 复杂度最高（含 4 Slice），超时风险最大。降级优先级：
1. 拆为 S2a（IRS+PAS+Gate）和 S2b（Integration）两个子圈
2. Integration 可延后为独立子圈，不破信号层闭环
3. IRS/PAS 先各保最小 3 因子版

---

## 8. S3 🔬 回测闭环

### 8.1 使命

用回测验证 S2 产出的集成推荐是否有效，并产出最小绩效摘要。S3 形成"信号到证据"的第一个完整闭环。

> 对齐 `Governance/Capability/SPIRAL-CP-OVERVIEW.md` S3 = CP-10, CP-06, CP-09

### 8.2 范围

**In Scope**:
- CP-10 Validation 纳入回测前置校验
- CP-06 本地向量化回测器
- CP-09 最小绩效指标摘要
- Qlib 适配层可选接入（非阻断）

**Out Scope**:
- 权重 WFA（S6 CP10-S2）
- 交易执行（S4）
- Integration 引擎（已在 S2 完成）

### 8.3 任务分解

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S3-T1 向量化回测器 | 核心基础设施 | `backtest_results / trade_records` | 验证信号有效性 | 1.2d |
| S3-T2 分析指标实现 | 核心基础设施 | `performance_metrics` | 形成可对比证据 | 0.9d |
| S3-T3 Qlib 适配器 | 外挂 ENH-09 | `qlib_adapter` | 保持研究主选兼容 | 0.8d |
| S3-T4 A/B/C 对照 | 外挂 ENH-06 | 对照报表 | 证明情绪主线价值 | 1.0d |

### 8.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| `integrated_recommendation` 缺失 | P0 | 阻断（回到 S2） |
| Validation Gate=FAIL | P0 | 阻断回测 |
| 信号与行情日期错位 | P0 | 阻断 |
| 个别标的无行情 | P1 | 跳过并记录 |
| Qlib 不可用 | P2 | 仅执行向量化基线 |

### 8.5 验收门禁

1. `eq backtest --engine vectorized` 可复现
2. T+1 与涨跌停规则测试通过
3. 产出 `performance_metrics`（基线回测报告 + 指标摘要）
4. A/B/C 对照表可生成且归档

### 8.6 退出五件套

- **run**: `eq backtest --engine vectorized --start {start} --end {end}`
- **test**: `pytest tests/contracts/test_backtest_* tests/contracts/test_analysis_* -q`
- **artifact**: `backtest_results` + `performance_metrics` + A/B/C 报表
- **review**: `Governance/specs/spiral-s3/review.md`
- **sync**: 最小同步 5 文件

### 8.7 遗产产出

- 可复用回测引擎与指标模块
- 对照基线数据资产
- 绩效指标标准表

### 8.8 降级策略

1. Qlib 环境不通：以向量化引擎为收口基线，Qlib 作为研究旁路
2. 对照任务超时：对照延后到 S6 不破圈

---

## 9. S4 📜 纸上实战（Strict 6A）

### 9.1 使命

验证"信号 → 订单 → 持仓 → 风控"的真实执行链路，并与 S3 回测口径对齐，防止回测与交易语义分叉。**本圈默认 Strict 6A**。

### 9.2 范围

**In Scope**:
- 订单状态机
- 持仓与 T+1 冻结
- 风控规则（20/30/80、止损8%、止盈15%）
- 回测-交易一致性验证

**Out Scope**:
- 实盘接入
- 异常恢复演练（S6 CP07-S3）

### 9.3 任务分解

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S4-T1 订单管理 | 核心基础设施 | `trade_records` | 交易链路最小单元 | 1.0d |
| S4-T2 持仓 / T+1 管理 | 核心基础设施 | `positions` + `t1_frozen` | A 股规则刚性要求 | 1.1d |
| S4-T3 风控引擎 | 核心基础设施 | `risk_events` | 防止执行失控 | 1.2d |
| S4-T4 口径对齐测试 | 外挂 ENH-04 | parity tests | 确保回测与交易一致 | 1.2d |

### 9.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| 非交易日下单 | P0 | 阻断 |
| 涨停买入 / 跌停卖出 | P0 | 阻断并记录 risk_event |
| T+1 违规卖出 | P0 | 阻断 |
| 风控规则冲突 | P0 | 执行更严格规则 |
| 资金不足 | P1 | 降仓或跳过 |

### 9.5 验收门禁

1. `eq trade --mode paper --date {trade_date}` 可运行
2. `trade_records / positions / risk_events` 三表可追溯
3. 订单状态机可重放
4. 回测-交易同信号一致性测试通过
5. Strict 6A 文档证据齐全

### 9.6 退出五件套

- **run**: `eq trade --mode paper --date {trade_date}`
- **test**: `pytest tests/contracts/test_trading_* tests/contracts/test_backtest_trading_signal_parity.py -q`
- **artifact**: `trade_records` + `positions` + `t1_frozen` + `risk_events`
- **review**: `Governance/specs/spiral-s4/review.md`
- **sync**: 最小同步 5 文件

### 9.7 遗产产出

- 纸上交易主链实现
- 风控事件标准日志
- 回测-交易一致性基线测试

### 9.8 降级策略

Strict 6A 文档负担过重时：仅保最小 6A 证据，不做额外文档扩张。

---

## 10. S5 🖥️ 可见之眼

### 10.1 使命

将 L3/L4 数据转为可见、可导出、可归档的产物，支撑日常使用与复盘。S5 是系统从"后端可运行"跨越到"前端可使用"的关键一步。

### 10.2 范围

**In Scope**:
- Streamlit 单页 Dashboard（温度、行业、TopN、持仓）
- 日报自动生成
- CSV / Markdown 导出与归档

**Out Scope**:
- 高级筛选（CP08-S2，留 S6 或后续）
- 深度归因漂移（S6）

### 10.3 任务分解

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S5-T1 Dashboard 最小版 | 核心基础设施 | `src/gui/app.py` 可运行 | 形成用户可视入口 | 1.2d |
| S5-T2 日报生成 | 核心基础设施 | `daily_report` + markdown 文件 | 固化每日证据 | 1.0d |
| S5-T3 导出归档 | 外挂 ENH-07 | CSV/MD 导出规范 | 运营可复查、可流转 | 0.8d |

### 10.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| 上游表缺失 | P1 | 空态展示 + 告警 |
| 导出失败 | P2 | 重试并提示 |
| 数据刷新超时 | P2 | 回退最近快照 |

### 10.5 验收门禁

1. `eq gui --date {trade_date}` 可启动
2. 页面符合 A 股红涨绿跌
3. `daily_report` 可生成并归档
4. 导出文件与页面关键指标一致

### 10.6 退出五件套

- **run**: `eq gui --date {trade_date}`
- **test**: `pytest tests/contracts/test_gui_* tests/contracts/test_analysis_* -q`
- **artifact**: 页面截图 + `daily_report` + 导出文件
- **review**: `Governance/specs/spiral-s5/review.md`
- **sync**: 最小同步 5 文件

### 10.7 遗产产出

- GUI 基线模板
- 日报模板与归档命名规范
- 面向运营的可见化入口

### 10.8 降级策略

Plotly 图表实现超时：先用 Streamlit 原生组件出最小版，Plotly 图表延后到 S6。

---

## 11. S6 🔒 稳态收敛

### 11.1 使命

清债、稳态、校准。S6 的目标是让系统从"能跑"转到"可持续运行"，形成收敛里程碑。

### 11.2 范围

**In Scope**:
- 全链路重跑一致性
- P0 / P1 债务清偿
- Validation 权重对照最小版（CP10-S2）
- 归因与漂移报告（CP09-S3）

**Out Scope**:
- 新功能扩张
- 实盘接入

### 11.3 任务分解

| 任务 | 分类 | 主要产出 | 存在理由 | 工时 |
|---|---|---|---|---:|
| S6-T1 全链路重跑与一致性报告 | 核心基础设施 | run-all diff 报告 | 验证系统确定性 | 1.0d |
| S6-T2 债务清偿 | 核心基础设施 | debts P0/P1 清零记录 | 防技术债滚雪球 | 1.0d |
| S6-T3 CP10-S2 最小权重对照 | 核心算法 | baseline vs candidate 结论 | 让权重变更有证据 | 1.0d |
| S6-T4 归档与冻结全检 | 外挂 ENH-08 | freeze 报告 + 里程碑归档 | 防文档/实现漂移 | 1.0d |

### 11.4 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| run-all 前后结果不可解释漂移 | P0 | 阻断收口，回溯变更 |
| 债务项无法关闭 | P1 | 明确延期圈号与阻断影响 |
| candidate 权重不优于 baseline | P1 | 回退 baseline |
| freeze_check 失败 | P0 | 阻断并定位变更来源 |

### 11.5 验收门禁

1. `eq run-all --start {start} --end {end}` 两次结果一致（允许时间戳差异）
2. `Governance/record/debts.md` 中 P0/P1 均有处置结论
3. `validation_weight_report` 与 `validation_weight_plan` 可追溯
4. 归因报告可生成且输入链可追溯
5. 冻结检查通过

### 11.6 退出五件套

- **run**: `eq run-all --start {start} --end {end}`
- **test**: `pytest -q`（含 contracts / canary / parity）
- **artifact**: 一致性报告 + 债务清偿记录 + validation weight 报告 + freeze 报告
- **review**: `Governance/specs/spiral-s6/review.md`
- **sync**: 最小同步 5 文件

### 11.7 遗产产出

- 重跑一致性基线
- 权重更新证据链
- 可持续运营的收敛里程碑

### 11.8 降级策略

权重对照无明显优化：维持 baseline 权重，记录"无变更"结论，不强行改权重。

---

## 12. 风险矩阵

| 风险 | 影响 Spiral | 概率 | 影响度 | 缓解策略 |
|---|---|---|---|---|
| TuShare API 不可用/限流 | S0 | 中 | 高 | mock 数据兜底；canary 离线包 |
| S2 复杂度过高导致超时 | S2 | 高 | 高 | 优先保 IRS+PAS+Gate；桥接延后 |
| Qlib 环境与本地向量化口径不一致 | S3 | 中 | 中 | 以向量化为收口基线；Qlib 为旁路 |
| Strict 6A 文档负担拖慢 S4 | S4 | 中 | 中 | 仅保最小 6A 证据 |
| 回测与交易语义分叉 | S4 | 低 | 高 | S4-T4 显式口径对齐测试 |
| Plotly 图表实现复杂度 | S5 | 低 | 低 | Streamlit 原生组件先行 |
| 全链路重跑发现不可解释漂移 | S6 | 中 | 高 | 阻断收口，逐层回溯定位 |
| 文档先行但实现滞后（当前最大风险） | 全局 | 高 | 高 | 从 S0 开始立即写代码；铁律7 强制执行 |

---

## 13. 治理集成

### 13.1 与治理体系的接口

| 治理组件 | 在本路线图中的角色 |
|---|---|
| 系统铁律 | 每个 Spiral 验收时的合规检查基线 |
| 核心原则 | 冻结区定义的来源 |
| 6A 工作流 | 每个 Spiral 执行时遵循的步骤框架 |
| CP 能力包 | 每个 Spiral 的 Slice 来源 |
| Task 模板 | 每个子任务的标准卡片格式 |
| 技术债登记 | 每圈 review 时的同步目标 |
| 可复用资产 | 遗产登记与跨 Spiral 复用的依据 |

### 13.2 文档同步规则

每圈收口时强制更新：
1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

本路线图自身：仅在 Spiral 完成或路线调整时更新，不要求每圈都改。

---

## 14. 使用指南

### 14.1 日常查阅

- 看全局进度 → 第 3 节 路线总览看板
- 看当前圈做什么 → 找到对应 Spiral 章节的任务分解
- 看上下游依赖 → 第 4 节 依赖链与遗产链
- 看风险 → 第 12 节 风险矩阵

### 14.2 执行时

1. 开始新 Spiral → 更新看板状态为 🚧
2. 拆解 Task → 使用 `Governance/Capability/SPIRAL-TASK-TEMPLATE.md`
3. 执行 → 遵循 `Governance/steering/6A-WORKFLOW.md`
4. 收口 → 检查五件套 + 验收门禁
5. 完成 → 更新看板状态为 ✅，更新遗产表

### 14.3 路线调整时

1. 在本文档对应 Spiral 章节记录调整原因
2. 更新看板状态与工时
3. 若涉及 CP 契约变化，同步更新 `CP-*.md`
4. 若涉及主计划变化，同步更新 `docs/design/enhancements/eq-improvement-plan-core-frozen.md`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.3.1 | 2026-02-12 | 链接口径整理：收敛 `draft/` 描述为正式桥梁入口；主计划与 CP 主控引用改为完整路径 |
| v1.3.0 | 2026-02-12 | 术语收敛为“核心算法/核心基础设施/系统外挂”；在 3.1 增补 S2 父圈拆分说明，显式对齐 1-3 Slice 约束 |
| v1.2.0 | 2026-02-12 | 新增 3.3 三分类工时分布（核心算法/基础设施/外挂）；所有任务表分类列统一为三层口径并标注 ENH 编号；对齐 `docs/design/README.md` 三层结构 |
| v1.1.1 | 2026-02-12 | 修复复核残留：消除 `||` 表格语法错误；S2 切片约束文案改为"父圈视图+执行拆圈"；修正"囨入"错字 |
| v1.1.0 | 2026-02-12 | P1: S2/S3 CP 分配对齐 SPIRAL-CP-OVERVIEW（S2 含 CP-05 Integration，S3 转为 CP-10/CP-06/CP-09 回测闭环）；P1: S6 CP 从"全部"改为 CP-10/CP-07/CP-09 合规切片；P2: 修正任务模板路径为完整路径；P3: 统一 risk_events 命名 |
| v1.0.0 | 2026-02-12 | 初版：融合业界 Roadmap 最佳实践与项目治理体系，覆盖 S0-S6 全周期 |
