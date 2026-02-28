# EmotionQuant 技术选型基线 (Technical Baseline)

**版本**: v1.3.0
**最后更新**: 2026-02-28
**定位**: 统一记录系统技术选型决策、备选方案与排除理由

---

## 1. 约束条件

| 约束 | 说明 |
|---|---|
| 开发模式 | 单开发者，个人使用 |
| 开发环境 | Windows（PowerShell 7.x） |
| 运行时 | Python ≥3.10 |
| 目标市场 | 中国 A 股 |
| 数据预算 | 双 Key：10000 网关（主）+ 5000 官方（兜底） |
| 部署形态 | 单机本地运行 |
| 数据位置 | `DATA_PATH` 环境变量注入（默认 `G:\EmotionQuant_data`，仓库外独立目录） |

---

## 2. 技术选型总表

| 领域 | 选型 | 一句话理由 | 备选 | 排除理由 |
|---|---|---|---|---|
| 编程语言 | Python ≥3.10 | 量化生态最成熟，Qlib/pandas/numpy 全链路原生支持 | — | — |
| 数据源 | TuShare 双通道（10000 网关主 + 5000 官方兜底） | 10000 覆盖更全，5000 延迟更低；主路失败可自动兜底 | AKShare / BaoStock | 作为最终底牌预留，当前未实装 |
| 落盘格式 | Parquet | 列式存储，pandas 原生支持，跨平台 | CSV | 无类型、无压缩、大文件性能差 |
| 查询引擎 | DuckDB（单库） | 单文件嵌入式、SQL 查询、零运维 | SQLite / PostgreSQL | SQLite 无列式优化；PG 需独立运维 |
| 回测主选 | Qlib | 因子研究完整、社区活跃、近年持续更新 | backtrader / RQAlpha | BT 社区停滞；RQ 定制度低 |
| 回测执行基线 | 本地向量化回测器 | 对齐 A 股规则、快速迭代、口径自主可控 | — | — |
| 回测兼容 | backtrader（可选） | 回放兼容，不是主线 | — | — |
| GUI 框架 | Streamlit + Plotly | 快速原型、交互图表、单文件部署 | Altair / Dash | Altair 表达力弱；Dash 重量级 |
| 行业分类 | 申万一级（31 个） | A 股主流分类标准，TuShare 原生支持 | 中信 / Wind | TuShare 无原生支持 |
| CLI 框架 | Typer / Click | 子命令管理、自动帮助文档 | argparse | 样板代码多 |
| 配置管理 | `.env` + `Config.from_env()` | 密钥不入仓库、路径可注入 | YAML / TOML | 个人项目过度设计 |

---

## 3. 数据架构决策

| 决策 | 结论 | 理由 |
|---|---|---|
| 存储策略 | Parquet 落盘 + DuckDB 单库查询 | Parquet 保证跨工具兼容；DuckDB 提供 SQL 查询能力 |
| 数据根目录 | `DATA_PATH` 环境变量注入 | 代码与数据分离，仓库外独立目录 |
| 分库策略 | 单库优先，分库仅在性能阈值触发后启用 | 个人项目数据量可控，避免过早优化 |
| 四层架构 | L1(原始) → L2(特征) → L3(算法) → L4(分析) | 层级单向依赖，禁止反向读取 |
| 交易日历 | TuShare `trade_cal` 为准 | 与数据源保持一致 |

详见：`docs/design/core-infrastructure/data-layer/data-layer-data-models.md`

---

## 4. 算法架构决策

| 决策 | 结论 | 理由 |
|---|---|---|
| 信号架构 | 三三制（MSS 市场 + IRS 行业 + PAS 个股） | 多层次情绪信号覆盖，同权协同 |
| Validation | 独立模块，输出 Gate 决策（PASS/WARN/FAIL） | 门禁与算法解耦，Integration 消费 Gate 决策 |
| Integration | 加权集成 MSS/IRS/PAS | 不偏废单算法，权重由 Validation 桥接 |
| 命名契约源 | Schema-first（`docs/naming-contracts.schema.json`，`nc-v1`） | 阈值/枚举单源，降低跨文档漂移 |
| 执行前契约校验 | Integration/Trading/Backtest 读取 `contract_version` 并前置校验 | 不兼容时阻断，避免静默错配 |
| 情绪因子优先 | 铁律1 — 信号主逻辑以情绪因子为核心 | 系统定位决定 |
| 技术指标边界 | 可对照/辅助特征，不得独立触发交易 | 铁律2 |
| 权重初始化 | baseline 等权 `[1/3, 1/3, 1/3]` | Walk-Forward 在 S6 才做 |

详见：`docs/design/core-algorithms/`

---

## 5. 交易规则决策

| 决策 | 结论 | 依据 |
|---|---|---|
| T+1 | 买入当日不可卖出 | A 股规则 |
| 涨跌停 | 主板 ±10%，创业板/科创板 ±20%，ST ±5% | A 股规则（铁律5） |
| 交易时段 | 9:30-11:30, 13:00-15:00 | 沪深交易所 |
| 最小交易单位 | 100 股（1 手） | A 股规则 |
| 行业分类 | 申万一级 | TuShare 原生支持 |
| 风控规则 | 单股 ≤20%、行业 ≤30%、总仓 ≤80%；止损 8%、止盈 15% | 设计基线 |
| 交易模式 | 纸上交易优先，R0-R9 开发阶段不含实盘 | 开发阶段约束 |

详见：`docs/design/core-infrastructure/trading/`

---

## 6. 排除记录

以下方案经评估后明确排除：

| 方案 | 排除理由 | 评估时间 |
|---|---|---|
| AKShare/BaoStock 作为当前主流程数据源 | 当前圈聚焦双 TuShare 主备稳定性；AKShare/BaoStock 保留为路线图底牌预留（未来圈实现） | 2026-02 |
| PostgreSQL 替代 DuckDB | 需要独立服务进程和运维，个人项目不值得 | 2026-02 |
| vn.py / easytrader 实盘接入 | R0-R9 开发阶段不含实盘，纸上交易自研即可 | 2026-02 |
| RQAlpha 回测引擎 | Qlib + 向量化基线已够，不再接入第三个引擎 | 2026-02 |
| backtrader 作为主选 | 社区停滞、API 繁琐，不适合因子研究 | 2026-02 |
| Altair 替代 Plotly | 表达力不足，现有 Altair 图表将迁移至 Plotly | 2026-02 |
| YAML/TOML 配置管理 | `.env` + `Config.from_env()` 已满足需求，避免过度设计 | 2026-02 |
| CP 脚本模板（run.sh/test.sh） | Windows 环境不友好，CLI `eq {subcommand}` 已覆盖 | 2026-02 |

详见：`docs/design/enhancements/enhancement-selection-analysis_claude-opus-max_20260210.md` §6

---

## 7. 质量门禁基线

| 门禁层 | 基线命令/文件 | 作用 |
|---|---|---|
| 本地一致性检查 | `python -m scripts.quality.local_quality_check --contracts --governance` | 同步检查命名契约、行为边界与治理 SoT |
| CI 阻断 | `.github/workflows/quality-gates.yml` | PR/主干变更自动阻断漂移 |
| 命名契约行为回归 | `scripts/quality/contract_behavior_regression.py` | 固化 `unknown/sideways/RR=1.0/Gate WARN-FAIL/contract_version` 边界 |

---

## 8. 交叉引用

| 主题 | 详细文档 |
|---|---|
| 系统架构总览 | `docs/system-overview.md` |
| 回测引擎选型分析 | `docs/design/core-infrastructure/backtest/backtest-engine-selection.md` |
| TuShare 通道策略 | `docs/reference/tushare/tushare-channel-policy.md` |
| TuShare 5000 积分官方口径 | `docs/reference/tushare/tushare-config-5000积分-官方-兜底号.md` |
| 数据模型定义 | `docs/design/core-infrastructure/data-layer/data-layer-data-models.md` |
| 外挂增强系统设计 | `docs/design/enhancements/enhancement-selection-analysis_claude-opus-max_20260210.md` |
| 改进主计划 | `docs/design/enhancements/eq-improvement-plan-core-frozen.md` |
| 系统铁律 | `Governance/steering/系统铁律.md` |
| 命名规范 | `docs/naming-conventions.md` |
| 命名契约 Schema | `docs/naming-contracts.schema.json` |
| 命名术语字典 | `docs/naming-contracts-glossary.md` |
| 命名契约变更模板 | `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` |
| 跨文档联动模板 | `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md` |

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.3.0 | 2026-02-28 | R0-R9 对齐：交易模式/排除记录措辞从 S0-S6 更新为 R0-R9 |
| v1.2.0 | 2026-02-19 | 数据源口径升级为“双 TuShare 主备”（10000 网关主、5000 官方兜底）；AKShare/BaoStock 调整为路线图预留底牌；修复 TuShare 配置交叉引用 |
| v1.1.0 | 2026-02-14 | 补充 Schema-first 命名契约与 `contract_version` 执行前校验基线；新增质量门禁基线（本地检查/CI/行为回归）与契约模板交叉引用 |
| v1.0.0 | 2026-02-12 | 首版：汇聚散落的技术选型决策为统一基线文档 |
