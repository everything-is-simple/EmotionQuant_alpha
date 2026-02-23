# EmotionQuant 技术需求与选型说明（TRD）

**版本**: v1.0.2  
**创建日期**: 2026-02-12  
**最后更新**: 2026-02-14  
**状态**: Active（治理层技术权威）

---

## 1. 文档定位

本文件定义 EmotionQuant 的技术源头口径，回答三类问题：

1. 为什么选这套技术栈与架构边界
2. 哪些技术约束不可破坏（冻结区/铁律）
3. 路线图执行时如何判定“技术方案已落地”

本文件与以下 SoT 联动：
- 能力状态 SoT：`Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`
- 工作流：`Governance/steering/6A-WORKFLOW.md`
- 系统总览：`docs/system-overview.md`
- 改进主计划：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`

---

## 2. 技术目标与非目标

### 2.1 技术目标

1. 建立可复现、可追溯、可审计的情绪驱动量化主链路
2. 保障本地数据优先与 A 股规则硬约束落地
3. 在单开发者条件下保持 Spiral 闭环交付效率（run/test/artifact/review/sync）

### 2.2 非目标

1. 不追求一次性“大而全”平台化重构
2. 不以技术指标替代情绪主信号
3. 不将远端 API 直连作为主流程数据源

---

## 3. 架构与边界约束

### 3.1 八层架构

Data → Signal → Validation → Integration → Backtest → Trading → Analysis → GUI

### 3.2 冻结区（只能实现，不改语义）

1. MSS/IRS/PAS/Validation/Integration 核心语义
2. L1-L4 数据分层与单向依赖
3. A 股规则：T+1、涨跌停、交易时段、整手、费用模型、申万行业
4. 本地数据优先 + 远端仅补充

### 3.3 路径与配置约束

严禁硬编码路径或密钥，统一经 `Config.from_env()` 注入。  
`DATA_PATH` 作为数据根目录输入，派生 `duckdb/ parquet/ cache/ logs/` 子目录。

---

## 4. 核心技术选型与理由

| 主题 | 选型 | 理由 | 约束 |
|---|---|---|---|
| 语言运行时 | Python >= 3.10 | 生态成熟、开发效率高、数据工具链完整 | 与 `pyproject.toml` 一致 |
| 存储 | Parquet + DuckDB（单库优先） | 批量落盘效率高 + 本地分析性能好 + 低运维成本 | 默认 `DUCKDB_DIR/emotionquant.duckdb` |
| 数据源 | TuShare（远端）+ 本地库（主） | A 股覆盖与字段稳定性可接受；满足本地优先策略 | 远端数据必须先落地 |
| 回测主线 | 本地向量化回测器 | 可控、可复现、与主流程契约一致 | 作为收口基线 |
| 回测研究 | Qlib 适配层（ENH-09） | 保留研究能力与实验扩展 | 非收口主路径 |
| GUI | Streamlit + Plotly | 交付快，适合个人项目迭代 | 先保障可用再做美化 |
| 质量守卫 | canary + contract + freeze_check | 提前发现契约漂移与回归问题 | 每圈至少 1 条自动化测试 |

### 4.1 术语消歧（研究主选 vs 收口主线）

- 研究主选：`Qlib`，用于因子研究、策略实验与快速验证。
- 收口主线：本地向量化回测器，用于可复现交付、交易口径对齐与治理收口。
- 兼容路径：`backtrader` 仅保留兼容回放，不作为主线口径。

---

## 5. 数据契约与产物口径

1. L1 原始层：`raw_*`，只采集不计算  
2. L2 特征层：`market_snapshot / industry_snapshot / stock_gene_cache`  
3. L3 信号与门禁层：`validation_gate_decision / validation_weight_plan / integrated_recommendation`  
4. L4 分析层：日报、指标、图表导出

关键要求：
- 主流程只读本地（DuckDB/Parquet）
- 任意报告必须可回溯到输入数据、参数与版本

---

## 6. 路线图分层映射（实施占比口径）

路线图按三类构建对象执行并统计工时：

1. 核心算法：MSS/IRS/PAS/Validation/Integration
2. 核心基础设施：Data/Backtest/Trading/Analysis/GUI
3. 系统外挂：ENH-01~ENH-09

当前规划占比（来自 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`）：
- 核心算法：27%
- 核心基础设施：46%
- 系统外挂：27%

---

## 7. 风险与降级策略

| 风险 | 触发 | 策略 |
|---|---|---|
| 远端数据不可用 | TuShare 限流/中断 | 使用 canary/mock，待恢复后补录 |
| 契约破坏 | 字段/语义变化 | Gate=FAIL 阻断，先修契约再推进 |
| 回测与交易口径漂移 | 指标或执行语义不一致 | parity tests 阻断 + 回滚到 baseline |
| 文档实现漂移 | Roadmap/CP 与代码不一致 | freeze_check + Spiral review 强制对齐 |

---

## 8. 变更控制

以下变更必须走 Strict 6A，并同步更新本 TRD：

1. 核心数据契约破坏性变更
2. Validation Gate 决策逻辑变更
3. 主链路新增关键外部依赖
4. 回测主线引擎替换

---

## 9. 退出标准（TRD 视角）

可认为“技术方案落地有效”的最小条件：

1. 任一 Spiral 均可提供可复现 `run` 命令
2. 自动化测试可稳定通过
3. 产物具备结构化追溯信息
4. SoT 文档间口径一致（Roadmap/Workflow/CP/Design）

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0.2 | 2026-02-14 | 修复 R33（review-011）：补充“研究主选 vs 收口主线”术语消歧，明确 Qlib 与本地向量化回测器的职责边界 |
| v1.0.1 | 2026-02-12 | 路线图引用补全为完整路径，避免跨目录阅读时路径歧义 |
| v1.0.0 | 2026-02-12 | 初版建立：定义技术目标、选型理由、边界约束、分层映射与变更控制 |
