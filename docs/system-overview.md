# EmotionQuant 系统总览（Spiral 实现版）

**版本**: v4.1.6
**最后更新**: 2026-02-14
**状态**: 实现前最终架构基线（文档）

---

## 1. 系统定位

EmotionQuant 是面向中国 A 股的情绪驱动量化系统。自 2026-02-07 起，执行模型从线性 Phase 切换为 Spiral 闭环：

- 每 7 天一圈（默认）
- 每圈必须有 `run/test/artifact/review/sync`（命令、测试、产物、复盘、同步）
- 文档服务实现，不再作为线性阻塞关卡

---

## 2. 核心原则（实现口径）

1. 情绪优先：情绪因子是主信号来源。
2. 单指标不得独立决策：技术指标可用于对照实验或辅助特征工程，但必须与情绪因子联合验证，且不得单独触发交易。
3. 本地数据优先：主流程以本地数据为准，远端只用于补采。
4. 禁止路径/密钥硬编码。
5. A 股规则刚性执行（T+1、涨跌停、交易时段；精度口径见 `Governance/steering/系统铁律.md` 与 `Governance/steering/CORE-PRINCIPLES.md`）。
6. Spiral 闭环强制：缺任一闭环证据不得收口。

---

## 3. 架构分层（八层）

| 层 | 职责 | 关键输出 |
|---|---|---|
| Data Layer | 原始数据采集与清洗 | L1/L2 数据集 |
| Signal Layer | MSS/IRS/PAS 计算 | 单系统分数 |
| Validation Layer | 因子验证 + 权重验证（新） | 验证报告 + Gate 决策 |
| Integration Layer | 信号集成与推荐生成 | `integrated_recommendation` |
| Backtest Layer | 可复现回测与敏感性分析 | 回测结果 |
| Trading Layer | 纸上交易/风控执行 | 订单与持仓日志 |
| Analysis Layer | 绩效归因与日报 | 归因与报告 |
| GUI Layer | 可视化展示与导出 | Dashboard + 导出文件 |

> 关键新增：Validation Layer 是独立模块，不再散落在算法/回测说明中。

---

## 4. 数据架构（简化口径）

- 存储策略：`Parquet + DuckDB 单库优先`
- 数据根目录：`DATA_PATH`（通过 `.env` 注入，实际部署为 `G:\EmotionQuant_data`，位于仓库外独立目录）
- 默认数据库：`DATA_PATH/duckdb/emotionquant.duckdb`
- 子目录布局：`parquet/` · `duckdb/` · `cache/` · `logs/`（均可通过 `.env` 单独覆盖）
- 一键校验脚本：`powershell -ExecutionPolicy Bypass -File scripts/setup/prepare_storage_layout.ps1 -DataRoot G:\EmotionQuant_data`
- 分库策略：仅在明确性能阈值触发后启用（需 ADR + 基准测试）

### 4.0 仓库整洁度（执行口径）

- 仓库 `G:\EmotionQuant-alpha` 仅保留代码/文档/治理与必要产物，临时目录按 `tmp_*` / `temp_*` / `.tmp_*` 统一清理。
- 本地数据库与数据文件统一落在 `G:\EmotionQuant_data`，避免与仓库内容混存。

### 4.1 分层

- L1：原始数据（raw_*）
- L2：特征与快照（market_snapshot / industry_snapshot / stock_gene_cache）
- L3：算法输出与集成推荐
  - 含 Validation 输出：`validation_gate_decision`、`validation_weight_plan`
- L4：分析产物（报告/指标）

---

## 5. 回测引擎选型策略（更新）

采用“平台主选 + 接口可替换”：

- 主选研究平台：`Qlib`（社区活跃、近年持续更新、因子研究能力完整）
- 执行口径基线：本地向量化回测器（对齐 A 股规则与快速迭代）
- 兼容适配：`backtrader` 保留为兼容选项，不作为主选
- 切换条件：因子研究与快速验证阶段优先 `Qlib`；生产决策与口径对齐阶段使用本地向量化回测器；`backtrader` 仅用于兼容回放

术语消歧（治理一致性）：
- 研究主选：指研究与实验阶段的默认平台（`Qlib`）。
- 收口主线：指可复现交付与策略口径对齐的执行基线（本地向量化回测器）。

详见：`docs/design/core-infrastructure/backtest/backtest-engine-selection.md`

---

## 6. GUI 技术口径（更新）

- 主线组合：`Streamlit + Plotly`
- `Altair` 已转为可选依赖，待现有 Altair 图表完成 Plotly 迁移后移除

---

## 7. Spiral 周期可行性说明

“7 天一圈”可行，但前提是圈目标足够小：

- 每圈只允许 1 个主目标
- 每圈只切 1-3 个能力包切片
- 无法闭环时必须拆分为更小圈，不得硬收口

补充口径：

- 路线术语统一使用 `Capability Pack (CP)`。
- `CP-*.md` 为正式命名，不代表线性阶段闸门。

---

## 8. 文档导航

- 技术选型基线：`docs/technical-baseline.md`
- 模块索引：`docs/module-index.md`
- 命名规范：`docs/naming-conventions.md`
- 命名契约 Schema：`docs/naming-contracts.schema.json`
- 命名术语字典：`docs/naming-contracts-glossary.md`
- 设计目录总览：`docs/design/`（`core-algorithms/` + `core-infrastructure/` + `enhancements/`）
- 路线总览：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- 能力包（CP）：`Governance/Capability/CP-*.md`
- 新系统螺旋实现路线：`Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md`（总路线） + `Governance/SpiralRoadmap/DEPENDENCY-MAP.md`（依赖图）
- 技术需求与选型（TRD）：`Governance/steering/TRD.md`
- 治理 SoT 矩阵：`Governance/steering/GOVERNANCE-STRUCTURE.md`
- 6A 工作流：`Governance/steering/6A-WORKFLOW.md`
- 跨文档联动模板：`Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`
- 命名契约联动模板：`Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`
- 因子/权重验证设计：`docs/design/core-algorithms/validation/`
- 回测选型：`docs/design/core-infrastructure/backtest/backtest-engine-selection.md`
- 本地质量门禁：`python -m scripts.quality.local_quality_check --contracts --governance`
- CI 质量门禁：`.github/workflows/quality-gates.yml`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v4.1.7 | 2026-02-18 | 固化本地部署口径：新增 `G:\EmotionQuant_data` 存储校验脚本入口；补充“仓库整洁度”执行口径（代码文档与数据目录分离） |
| v4.1.6 | 2026-02-14 | 文档导航补齐命名契约体系入口（schema/glossary/模板）与质量门禁入口（本地检查命令 + CI workflow） |
| v4.1.5 | 2026-02-14 | 修复 R33（review-011）：补充 `run/test/artifact/review/sync` 明文口径；A 股规则增加精度定义链接（铁律/原则）；新增“研究主选 vs 收口主线”术语消歧；文档导航补充 TRD/治理 SoT/6A 入口 |
| v4.1.4 | 2026-02-12 | 文档导航中的 SpiralRoadmap 入口由 `draft/` 收敛为 `VORTEX-EVOLUTION-ROADMAP.md` + `DEPENDENCY-MAP.md` |
| v4.1.3 | 2026-02-11 | 文档导航补充设计三层结构（核心算法/核心基础设施/外挂增强），对齐目录重构 |
| v4.1.2 | 2026-02-09 | 修复 R29：明确技术指标边界与铁律一致（可对照/辅助特征但不得独立决策）；L3 分层补充 Validation 运行时输出 |
| v4.1.1 | 2026-02-09 | 修复 R25：L2 分层补充 `stock_gene_cache`；明确回测引擎切换条件；补充 Altair 移除前置条件 |
| v4.1.0 | 2026-02-07 | 明确回测平台主选 Qlib；补充本地执行基线与兼容口径 |
| v4.0.0 | 2026-02-07 | 切换到 Spiral 实现口径；新增 Validation Layer；更新回测与存储策略 |
| v3.3.0 | 2026-02-05 | 线性重构版 |
