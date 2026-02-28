# WARP.md

本文件为自动化代理提供最小、可执行的仓库工作规则。与 `AGENTS.en.md`、`CLAUDE.md`、`CLAUDE.en.md`、`WARP.md`、`WARP.en.md` 内容等价，面向通用代理运行时。

---

## 1. 文档定位

- 作用：给自动化代理提供最小、可执行的仓库工作规则。
- 执行主计划唯一入口：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`（`docs/design/enhancements/enhancement-selection-analysis_claude-opus-max_20260210.md` 仅作选型论证输入）。
- 权威架构入口：`docs/system-overview.md`
- 权威能力状态入口：`docs/roadmap.md`（R0-R9 路线图）
- 权威治理入口：`Governance/steering/`
- 权威执行卡入口：`docs/cards/`（R0-R9 执行卡）

---

## 2. 系统定位

EmotionQuant 是面向中国 A 股的情绪驱动量化系统。

- 个人项目，单开发者
- 执行模型：**微圈闭环**（原 Spiral，2026-02-28 起升级为 R0-R9 Rebuild 路线）
- 每圈默认 7 天，必须有 `run/test/artifact/review/sync` 五件套
- 文档服务实现，不追求"文档完美"

---

## 3. 系统铁律（7 条，零容忍）

| # | 铁律 | 核心要求 |
|---|------|----------|
| 1 | 情绪优先 | 信号主逻辑必须以情绪因子为核心 |
| 2 | 单指标不得独立决策 | 技术指标可对照/辅助特征，但必须与情绪因子联合验证，不得单独触发交易 |
| 3 | 本地数据优先 | 主流程读取本地数据，远端仅补采，缺口先落库再进主流程 |
| 4 | 路径密钥禁止硬编码 | 路径/密钥必须通过 `Config.from_env()` 或环境变量注入 |
| 5 | A 股规则刚性执行 | T+1、涨跌停（主板10%/创业板科创板20%/ST 5%）、交易时段、申万行业 |
| 6 | 微圈闭环强制 | 每圈必须有五件套证据，缺一不得收口 |
| 7 | 文档服务实现 | 禁止文档膨胀阻塞开发，最小同步优先 |

**技术指标边界**：历史 archive 中"零技术指标绝对禁令"不属于现行口径。MA/RSI/MACD 等可用于对照实验或特征工程，但不得作为独立买卖信号。

**权威细则**：`Governance/steering/系统铁律.md`

---

## 4. 6A 工作流（微圈闭环版）

### 4.1 六步定义

| 阶段 | 名称 | 核心动作 |
|------|------|----------|
| A1 | Align | 确定本圈主目标与 In/Out Scope |
| A2 | Architect | 选 1-3 个 CP Slice，定义跨模块契约 |
| A3 | Act | 最小实现 + 至少 1 条自动化测试 |
| A4 | Assert | run/test/artifact 全部可复现验证 |
| A5 | Archive | 产出 review.md + final.md，整理证据链 |
| A6 | Advance | 最小同步 5 项，推进路线状态 |

### 4.2 执行约束

1. 每圈只允许 **1 个主目标**
2. 每圈只取 **1-3 个 CP Slice**
3. 单个 Task 超过 1 天必须继续拆分
4. 默认流程：`Scope → Build → Verify → Sync`
5. 高风险时升级 Strict 6A（交易路径/风控/数据契约破坏性变更/关键外部依赖）

### 4.3 退出条件

以下任一未满足，本圈不得收口：
- 无可运行命令 / 无自动化测试 / 无产物文件 / 无复盘记录 / 无同步记录

### 4.4 分支策略

- 默认合并目标：`main`
- 开发分支命名：`rebuild/r{N}-{module}`
- 若后续启用 `develop`，切换为 `feature → develop → main（里程碑发布）`

### 4.5 每圈最小同步（4 项）

1. `Governance/record/development-status.md`
2. `Governance/record/debts.md`
3. `docs/roadmap.md` 对应阶段状态
4. `docs/cards/` 对应卡片勾选

**权威流程**：`Governance/steering/6A-WORKFLOW.md`

---

## 5. 命名约定

**强制要求**：代码中使用英文，注释/文档/UI 使用中文。

### 5.1 情绪周期（MssCycle 枚举）

| 英文 | 中文 | 温度条件 |
|------|------|----------|
| emergence | 萌芽期 | <30°C + up |
| fermentation | 发酵期 | 30-45°C + up |
| acceleration | 加速期 | 45-60°C + up |
| divergence | 分歧期 | 60-75°C + up/sideways |
| climax | 高潮期 | ≥75°C |
| diffusion | 扩散期 | 60-75°C + down |
| recession | 退潮期 | <60°C + down/sideways |
| unknown | 异常兜底 | 输入异常或不可判定 |

### 5.2 趋势方向（Trend 枚举）

`up` / `down` / `sideways`（不使用 `flat`）

### 5.3 PAS 方向（PasDirection 枚举）

`bullish` / `bearish` / `neutral`

### 5.4 轮动状态（RotationStatus 枚举）

`IN` / `OUT` / `HOLD`

### 5.5 推荐等级

`STRONG_BUY`(≥75) / `BUY`(≥70) / `HOLD`(50-69) / `SELL`(30-49) / `AVOID`(<30)

### 5.6 字段规范

- 统一 `snake_case`
- 内部股票代码：`stock_code`（6 位，如 `000001`）
- 外部股票代码：`ts_code`（TuShare 格式，如 `000001.SZ`）
- 统一使用 `risk_reward_ratio`（非 `rr_ratio`）
- 跨模块契约版本字段：`contract_version`（当前 `nc-v1`）

**权威命名规范**：`docs/naming-conventions.md`
**机器可读契约源**：`docs/naming-contracts.schema.json`
**术语/模板入口**：`docs/naming-contracts-glossary.md` / `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`

---

## 6. 数据架构

### 6.1 存储策略

Parquet + DuckDB 单库优先（`DUCKDB_DIR/emotionquant.duckdb`）。分库仅在性能阈值触发后启用。

### 6.2 四层架构

| 层级 | 内容 |
|------|------|
| L1 | 原始数据（raw_*），外部采集不做计算 |
| L2 | 特征与快照（market_snapshot / industry_snapshot / stock_gene_cache） |
| L3 | 算法输出 + Validation 输出（validation_gate_decision / validation_weight_plan） |
| L4 | 分析产物（报告/指标） |

**依赖规则**：L2 只读 L1；L3 只读 L1/L2；L4 只读 L1/L2/L3。禁止反向依赖。

### 6.3 路径管理

```python
# ✅ 必须
from utils.config import Config
config = Config.from_env()
db_path = config.database_path

# ❌ 禁止
db_path = "data/emotionquant.db"
cache_dir = "G:/EmotionQuant_data/"
```

---

## 7. 架构分层（八层）

| 层 | 职责 |
|----|------|
| Data Layer | 原始数据采集与清洗 |
| Signal Layer | MSS/IRS/PAS 计算 |
| Validation Layer | 因子验证 + 权重验证（独立模块） |
| Integration Layer | 信号集成与推荐生成 |
| Backtest Layer | 可复现回测 |
| Trading Layer | 纸上交易/风控执行 |
| Analysis Layer | 绩效归因与日报 |
| GUI Layer | 可视化（Streamlit + Plotly） |

---

## 8. 治理结构

### 8.1 目录定位

| 目录 | 定位 |
|------|------|
| `docs/design/` | 设计基准（三层：核心算法 / 核心基础设施 / 外挂增强） |
| `docs/design/core-algorithms/` | 核心算法设计（MSS/IRS/PAS/Validation/Integration） |
| `docs/design/core-infrastructure/` | 核心基础设施设计（Data/Backtest/Trading/GUI/Analysis） |
| `docs/design/enhancements/` | 改进行动计划统一入口 |
| `Governance/steering/` | 铁律、原则、工作流 |
| `docs/roadmap.md` | R0-R9 路线图 |
| `docs/cards/` | R0-R9 执行卡 |
| `Governance/record/` | 状态、债务、复用资产 |
| `.reports/` | 报告存放（命名含日期时间） |
| `.reports/archive-*/` | 历史归档（只读） |

### 8.2 单一事实源（SoT）

| 场景 | 权威文件 |
|------|----------|
| 能力状态（路线图） | `docs/roadmap.md` |
| 执行卡 | `docs/cards/README.md` |
| 6A 工作流 | `Governance/steering/6A-WORKFLOW.md` |
| 系统铁律 | `Governance/steering/系统铁律.md` |
| 核心原则 | `Governance/steering/CORE-PRINCIPLES.md` |
| 改进行动主计划 | `docs/design/enhancements/eq-improvement-plan-core-frozen.md` |
| 设计对齐行动卡 | `Governance/archive/archive-spiral-roadmap-v5-20260228/execution-cards/DESIGN-ALIGNMENT-ACTION-CARD.md`（已归档） |
| 命名规范 | `docs/naming-conventions.md` |
| 命名契约 Schema | `docs/naming-contracts.schema.json` |
| 命名契约术语/模板 | `docs/naming-contracts-glossary.md` / `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` |
| 系统总览 | `docs/system-overview.md` |
| 模块索引 | `docs/module-index.md` |

### 8.3 归档规则

- 路线模型代际变化必须归档：`archive-{model}-{version}-{date}`
- 归档目录只读，不再迭代
- Spiral 路线模型已归档至 `Governance/archive/archive-spiral-roadmap-v5-20260228/`

---

## 9. 质量门控

### 9.1 必须门

- 命令可运行、测试可复现、产物可检查
- 硬编码检查、A 股规则检查、本地数据检查
- 契约/治理一致性检查：`python -m scripts.quality.local_quality_check --contracts --governance`

### 9.2 合并前清理

- TODO/HACK/FIXME：开发中允许，合并前必须清理或登记到 `Governance/record/debts.md`

### 9.3 原则

- 有效测试优先于覆盖率数字
- 闭环优先于扩张

---

## 10. 核心算法约束

- MSS / IRS / PAS 三算法**同权协同**，集成层不得偏废或以单算法硬否决
- 三算法以情绪因子为共同输入，保持情绪口径一致
- Validation Layer 是独立模块，负责因子有效性验证与权重方案验证，输出 Gate 决策（PASS/WARN/FAIL）
- Integration Layer 消费 Gate 决策进行信号集成，输出 `integrated_recommendation`

---

## 11. 技术栈口径

- Python `>=3.10`
- 数据：Parquet + DuckDB（单库优先）
- GUI 主线：Streamlit + Plotly
- 回测主选：Qlib（研究与实验）；执行基线：本地向量化回测器；兼容适配：backtrader（可选，不是主线）

详见：`pyproject.toml`、`docs/design/core-infrastructure/backtest/backtest-engine-selection.md`

---

## 12. 仓库远端

- `origin`: `${REPO_REMOTE_URL}`（定义见 `.env.example`）

---

## 13. 历史说明

- 旧版线性文档已归档至：`Governance/archive/archive-legacy-linear-v4-20260207/`
- 旧工作流文件已并入 `Governance/steering/6A-WORKFLOW.md`（不再保留独立归档目录）
- 本文件不再维护线性 Stage 叙述。
- Spiral 路线图（`Governance/SpiralRoadmap/`）已归档至 `Governance/archive/archive-spiral-roadmap-v5-20260228/`，新路线见 `docs/roadmap.md`。

---

## 14. 设计对齐与债务卡

> Spiral 阶段的设计对齐卡与债务卡已归档至 `Governance/archive/archive-spiral-roadmap-v5-20260228/execution-cards/`。
> R0-R9 阶段的执行卡见 `docs/cards/`，状态同步以 `docs/roadmap.md` 与 `Governance/record/debts.md` 为准。

## 15. 工具链说明

- `.claude/` 保留为历史工具资产，不作为当前规范入口。
- 可复用治理规则已迁移到 `Governance/steering/`。
- `Governance/Capability/` 已退役并归档至 `Governance/archive/archive-capability-v8-20260223/`。

## 16. Git 认证基线

- TLS 后端基线：优先 `openssl`（`git config --global http.sslbackend openssl`，允许仓库内覆盖）。
- 受限沙箱会话中，认证 `git push` 建议在非沙箱或提权模式执行，确保凭据交互与存储路径可访问。

## 17. MCP 基线

推荐 MCP 服务：
- `context`（Context7 文档/上下文检索）
- `fetch`（HTTP 内容抓取）
- `filesystem`（跨目录文件操作）
- `sequential-thinking`（多步推理）
- `mcp-playwright`（浏览器自动化）

Skill 与 MCP 边界：
- Skill 是流程说明/模板。
- MCP 是运行时工具。
- Skill 不替代 MCP。

默认触发策略：
- 版本敏感 API/框架问题优先 `context`。
- 无需浏览器渲染的网页内容优先 `fetch`。
- 非简单文件读写优先 `filesystem`。
- 多分支决策与复杂排障优先 `sequential-thinking`。
- UI 流程与截图回放优先 `mcp-playwright`。

Bootstrap：
- 一键：`powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap_dev_tooling.ps1`
- 仅 MCP：`powershell -ExecutionPolicy Bypass -File scripts/setup/configure_mcp.ps1 -ContextApiKey <your_key>`
- 可选 MCP 目标目录：`-CodexHome <path>`（默认：项目内 `.tmp/codex-home`）
- 仅 Hooks：`powershell -ExecutionPolicy Bypass -File scripts/setup/configure_git_hooks.ps1`
- 仅 Skills 检查：`powershell -ExecutionPolicy Bypass -File scripts/setup/check_skills.ps1`
