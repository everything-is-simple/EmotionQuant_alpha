# EmotionQuant 外挂增强系统设计（权威版）

**生成模型**: Claude 4.6 Opus (Max)
**生成时间**: 2026-02-10
**版本**: v3.0.0
**性质**: 外挂系统权威设计文档
**状态**: 正式 v3.0.0（已完成候选权威 v2.1 审核）

---

## 文档对齐声明

> 本文档与以下核心设计保持严格一致，任何修改须重新验证对齐性。

> `docs/design/enhancements/drafts/` 与历史草稿记录（已收敛）仅作研究参考，不作为权威引用源。

| 依赖文档 | 版本 | 引用内容 |
|----------|------|----------|
| `docs/system-overview.md` | v4.1.3 | 架构分层、回测选型、数据策略 |
| `docs/design/core-infrastructure/data-layer/data-layer-data-models.md` | v3.2.5 | L1 八张原始表 schema、L2/L3 字段定义 |
| `docs/design/core-infrastructure/data-layer/data-layer-api.md` | v3.1.2 | TuShareClient 异常体系、重试机制 |
| `docs/design/core-algorithms/mss/mss-data-models.md` | v3.1.6 | MssPanorama 输出字段 |
| `docs/design/core-algorithms/integration/integration-data-models.md` | v3.4.10 | IntegratedRecommendation 28 字段 |
| `docs/design/core-infrastructure/backtest/backtest-data-models.md` | v3.4.10 | BacktestSignal.source 双来源、EngineType 枚举 |
| `docs/design/core-infrastructure/backtest/backtest-engine-selection.md` | v1.1.0 | Qlib 主选 + 本地向量化基线 |
| `docs/design/core-algorithms/validation/factor-weight-validation-data-models.md` | v2.1.1 | 五张 Validation 表、ValidationWeightPlan 桥接 |
| `docs/design/core-infrastructure/analysis/analysis-data-models.md` | v3.1.6 | L4 日报模板字段、绩效公式 |
| `docs/design/enhancements/eq-improvement-plan-core-frozen.md` | v2.1.0 | ENH-01~08 白名单、冻结边界 |
| `Governance/steering/系统铁律.md` | v5.1.1 | 单指标不得独立决策；技术指标仅可对照/辅助 |

### 冻结边界声明

本文档定义的所有外挂**不得修改**以下冻结区语义：
- `docs/design/**` 核心算法/数据模型/API/信息流
- `docs/system-overview.md`、`docs/module-index.md`、`docs/naming-conventions.md`
- `Governance/Capability/CP-*.md`、`Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- `Governance/steering/系统铁律.md`、`Governance/steering/CORE-PRINCIPLES.md`
- MSS/IRS/PAS/Validation 评分公式与门禁逻辑
- Spiral + CP 主路线
- R1-R31 已收口的字段、枚举、数据模型

外挂仅在以下目录操作：`src/pipeline/`、`src/adapters/`、`tests/contracts/`、`tests/canary/`、`scripts/quality/`（如需改 `src/data/`、`src/backtest/`、`src/trading/`、`src/gui/`，仅可按既有设计落地，不得重定义契约）

---

## 0. 本文档用途

用户核心诉求：**完全实现核心算法 + 数据采集落库 + 校验核心算法 + 集成核心算法 + Qlib 回测出结果**。

外挂（Enhancement）的唯一存在价值：**服务上述核心诉求**。如果某个外挂不能让核心链路跑得更稳、验得更准、坏了更容易定位，那就不该做。

本报告回答：
1. 现有 ENH-01~08 是否全部必要？哪些可砍、哪些必留？
2. 是否还缺少未被 ENH 覆盖的关键外挂？
3. 每个外挂的选型理由、功效、阶段、工时、与核心的依赖关系。

**审查依据**（全部已通读）：
- 三份实施方案（core-frozen v2.0、Claude 详细版、GPT-5 Codex 候选稿）
- 系统总览 `docs/system-overview.md` v4.1.3
- 系统铁律 `Governance/steering/系统铁律.md` v5.1.1
- SPIRAL-CP-OVERVIEW v6.1.0
- 对标批判报告（原版 + 修订版）及两份行动计划
- Validation 算法设计 `factor-weight-validation-algorithm.md` v2.1.0
- 数据模型、MSS/IRS/PAS/Integration/Backtest/Trading/Analysis/GUI 设计文档

---

## 1. 审查框架：外挂的三个判定维度

一个外挂是否应该纳入，用三个问题判定：

**维度一：核心链路是否依赖它？**
核心链路 = `TuShare → Parquet → DuckDB → MSS/IRS/PAS → Validation Gate → Integration → Qlib 回测 → 绩效指标`
如果外挂不在这条链路上，但能让链路的**可运行性、可验证性、可定位性**显著提升，才有做的理由。

**维度二：不做会怎样？**
如果不做这个外挂，核心链路能否跑通？跑通后出了问题能否定位？定位后能否复现？

**维度三：投入产出比**
外挂工时占总工时比例是否合理？是否有更简单的替代方案？

---

## 2. ENH-01~08 逐项裁决

### ENH-01 统一运行入口（`eq run / eq mss / eq recommend / eq backtest`）

**来源**：对标 RQAlpha 批判 §3.1——"你缺开箱即跑入口"
**功效**：将 `python -m src.xxx --date ...` 这类零散调用统一为 `eq {subcommand}` CLI
**核心依赖**：五件套的 `run` 证据直接依赖它。没有 CLI 就无法写出可复现的闭环命令。

**裁决：必留 ✅**
- 不做的后果：每圈收口的 `run` 证据无法标准化，开发者每次需要记住不同 python 模块入口
- 工时：0.5-0.8d（仅骨架 + 子命令占位）
- 出现阶段：**S0**（首圈就必须有）
- 实现要点：Typer 或 Click，子命令 `run/mss/recommend/backtest/trade/gui/run-all`

---

### ENH-02 数据预检与限流守卫

**来源**：对标批判 §3.2 + 实际 TuShare 5000 积分限流经验
**功效**：在调 TuShare API 前验证 token 有效性、检查交易日历、实施频率限流
**核心依赖**：TuShare 是主采集源。token 无效或超频会导致 S0 数据链路 P0 阻断。

**裁决：必留 ✅**
- 不做的后果：首次运行 token 失败时只有 TuShare 原始异常，无法快速定位；超频后被封 IP 影响后续所有圈
- 工时：0.3-0.5d（token 预检 + tenacity 重试装饰器）
- 出现阶段：**S0**（数据采集的前置守卫）
- 实现要点：
  - `validate_token()` 预检（调 `tushare.pro_api().trade_cal()` 小请求验通）
  - `@retry(stop=stop_after_attempt(3), wait=wait_exponential())` 装饰器（tenacity）
  - 交易日历预检（非交易日直接跳过不拉取）
- 与核心设计对齐（`data-layer-api.md` SS10）：
  - 异常体系复用已有设计：`DataFetchError`、`RateLimitError`、`ConnectionError`
  - 重试装饰器复用 `src/data/utils/retry_with_backoff()`，不另建
  - 限流参数从 `TuShareClient(rate_limit=120)` 读取，不硬编码

---

### ENH-03 失败产物协议（`error_manifest.json`）

**来源**：对标批判 §3.6——"你缺失败可复盘机制"
**功效**：任何 P0/P1 失败时，统一输出结构化错误文件，包含 error_level、failed_step、trade_date、timestamp、error_message
**核心依赖**：不在核心算法链路上，但直接影响**问题定位效率**。

**裁决：必留 ✅**
- 不做的后果：核心算法跑失败时只有 Python traceback，无法快速判定是数据问题、算法 bug 还是配置错误
- 工时：0.3d（统一 error_manifest 写入函数 + 在关键步骤 catch 后调用）
- 出现阶段：**S0**（首圈建立协议），**S4** 复用（交易失败也用同一协议）
- 实现要点：
  ```python
  # error_manifest.json 最小字段
  {"error_level": "P0", "step": "fetch_daily", "trade_date": "20260207",
   "error_type": "TuShareAPIError", "message": "...", "timestamp": "..."}
  ```
- 写入位置：`${DATA_PATH}/error_manifest.json`（最后一次失败覆盖写入，不累积）

---

### ENH-04 适配层契约测试

**来源**：三份方案均独立提出；解决的问题是"上游输出字段变了，下游才发现不兼容"
**功效**：在 `tests/contracts/` 中为每个模块间接口写字段/类型/范围断言
**核心依赖**：直接保障核心链路的**模块间契约稳定性**。MSS 输出被 Integration 消费，如果 mss_panorama 少了 `temperature` 字段而没有测试守卫，Integration 会在运行时崩溃。

**裁决：必留 ✅（但分批，不在 S0 全做）**
- 不做的后果：修改任何一个模块时可能悄悄破坏下游，发现时已经是端到端失败，定位成本高
- 工时：每组约 0.3d × 7 组 = ~2d 总计，分散在 S0-S4
- 出现阶段与分组：

| 契约组 | 阶段 | 验证什么 |
|--------|------|----------|
| Data Layer | S0 | L1 parquet schema → L2 DuckDB schema |
| MSS | S1 | mss_panorama 字段可被 Integration 消费 |
| IRS | S2 | irs_industry_daily 字段合法 |
| PAS | S2 | stock_pas_daily 评分范围 + 等级枚举 |
| Validation | S2 | gate_decision 含 factor_gate/weight_gate/final_gate/selected_weight_plan/stale_days/reason |
| Validation→Integration | S2 | `validation_weight_plan` 桥接存在且 `(w_mss+w_irs+w_pas)=1` |
| Integration | S2 | integrated_recommendation 28 字段完整 + 权重和=1 + recommendation 合法值 |
| Backtest→Trading | S4 | 同一信号，两条路径成交一致 |

---

### ENH-05 小样本金丝雀数据包

**来源**：对标批判建议 [6]——"10 天小样本回归包"
**功效**：提供 10 个交易日的 mock parquet 数据，让所有圈的测试都能**离线运行、不依赖 TuShare 网络**
**核心依赖**：不在核心链路上，但是**核心算法测试的前置条件**。如果没有金丝雀包，每次跑测试都要真的拉 TuShare，不可接受。

**裁决：必留 ✅**
- 不做的后果：测试依赖网络和 TuShare 积分，CI 不稳定，离线环境无法验证
- 工时：0.5-0.7d
- 出现阶段：**S0**（首圈生成，后续所有圈复用）
- 实现要点：
  - `tests/fixtures/canary_10d/` 下放置 daily/daily_basic/limit_list/index_daily/trade_cal/stock_basic 的 parquet；【新增必备】`index_member/`、`index_classify/` 两类表用于行业映射，字段与 `data-layer-data-models.md §2.5/§2.6` 对齐
  - 数据量精简（每天 50-100 只股票足够），但字段完整
  - `eq run --date {date} --source mock` 从 fixtures 读取而非 TuShare

---

### ENH-06 A/B/C 对照看板

**来源**：对标 czsc 批判 §3.5——"你缺基准对照证据"
**功效**：回测时同时运行三组对照：A=情绪主线（系统信号） / B=随机选股 / C=等权买入持有；可选 D=技术指标基线（仅作对照，不入交易链），输出年化收益/最大回撤/Sharpe 对照表，符合铁律“技术指标仅可对照实验”。
**核心依赖**：不在核心链路上。属于"证明系统有效"的证据工具。

**裁决：可选延后 ⚠️ → 建议在 S3 做最小版**
- 不做的后果：核心链路完全不受影响，但缺少"情绪主线到底比随机好多少"的量化证据
- 做的好处：一次性投入后，每次回测自动产出对照表，是系统价值的核心证据
- 工时：0.5-1d（B/C 组逻辑简单——随机选股和等权持有只是 numpy 数行代码）
- 出现阶段：**S3**（回测圈，此时向量化引擎已可用）
- 精简方案：首版只输出 CSV 对照表（3 行 × 3 列：组别/年化收益/Sharpe），不做可视化

---

### ENH-07 L4 产物标准化

**来源**：对标 QUANTAXIS 批判 §3.4——"你缺可见产物面板"
**功效**：固定日报 Markdown 模板 + 报告归档命名规范（`{name}_{YYYYMMDD}_{HHMMSS}.md`）
**核心依赖**：不在核心链路上。属于"输出可读性"增强。

**裁决：延后到 S5 ⚠️**
- 不做的后果：S0-S3 的核心链路完全不受影响。日报和报告是 S5 展示闭环的内容。
- 做的好处：统一报告格式，方便归档和回溯
- 工时：0.3-0.5d
- 出现阶段：**S5**（展示闭环时自然完成）
- 理由：在核心算法和回测跑通之前，做报告模板没有实际消费者

---

### ENH-08 设计冻结检查

**来源**：冻结边界守卫——防止核心权威文档被意外修改
**功效**：对核心设计文件生成 SHA256 hash 锚点，每圈收口前运行检查，hash 变化则 P0 阻断
**核心依赖**：不在核心链路上，但保障"实现与设计一致性"的最终守卫。

**裁决：可选延后 ⚠️ → 建议 S0 做骨架，S6 全量执行**
- 不做的后果：设计文档被无意修改时不会立即发现，可能导致实现偏离冻结设计
- 实际风险评估：个人开发环境下，设计文档被意外修改的概率较低。但作为长期守卫，值得投入。
- 工时：0.3d（S0 骨架）+ 0.2d（S6 全量验证）
- 出现阶段：**S0**（生成锚点）+ **S6**（全量检查）
- 实现要点：
  - `scripts/quality/freeze_check.py`：校验以下锚点并计算 SHA256，与 `freeze_anchors.json` 比对
    - `docs/design/**/*.md`
    - `docs/system-overview.md`
    - `docs/module-index.md`
    - `docs/naming-conventions.md`
    - `Governance/Capability/CP-*.md`
    - `Governance/Capability/SPIRAL-CP-OVERVIEW.md`
    - `Governance/steering/系统铁律.md`
    - `Governance/steering/CORE-PRINCIPLES.md`
  - 阻断规则：任一锚点变化且无本圈审查记录时，直接 P0 失败

---

## 3. 现有 ENH 之外缺少的关键外挂

以上 8 个 ENH 来自批判报告和主计划。但交叉审查后发现，有 **1 个关键外挂**被三份方案提到但未纳入 ENH 编号体系（另一个为 Validation 核心输出，非外挂）：

### ENH-09（新增）Qlib 适配层

**来源**：主计划 §2.3 明确"回测主选 Qlib"，三份方案均在 S3 提到 `qlib_adapter`，但没有 ENH 编号
**功效**：将 `integrated_recommendation` 转换为 Qlib 可消费的信号格式（DataFrame with `score` column indexed by `datetime × instrument`），将 Qlib 回测结果转回系统标准格式
**核心依赖**：**直接在核心链路上**。用户明确要求"使用 Qlib 跑出回测结果"。没有这个适配层，Qlib 就用不了。

**裁决：必留 ✅**
- 不做的后果：无法满足"Qlib 回测出结果"的核心诉求
- 工时：0.8-1d
- 出现阶段：**S3**
- 实现要点：
  - `src/adapters/qlib_adapter.py`
  - `to_qlib_signal(recommendations_df, source: Literal["integrated","pas_fallback"]) → qlib_signal_df`（兼容 BacktestSignal.source 双来源）
  - `from_qlib_result(qlib_backtest_output) → backtest_results 标准格式`
  - Qlib 安装走现有 optional dependency：`emotionquant[backtest]`（包含 `pyqlib`）

### 历史编号说明：ENH-10 并入 CP-10（已废止独立编号）

- 历史草案中曾出现 ENH-10（Validation 权重桥接）编号。
- 当前权威口径已将其并入 `CP-10 Validation` 核心实现，不再保留独立 ENH 编号。
- 本文档正式外挂编号以 ENH-01~ENH-09 为准。

### 注：Validation→Integration 权重桥接表（核心，不计入 ENH）

**来源**：`factor-weight-validation-algorithm.md` §6.1 明确定义了桥接协议，三份方案在 S2 都提到 `validation_weight_plan`，但 GPT-5 Codex 稿将其单独列为 S2-T4 任务
**功效**：确保 Validation Gate 输出的权重方案能被 Integration 正确消费（`selected_weight_plan → weight_plan → Integration.calculate()`）
**核心依赖**：**直接在核心链路上**。Gate 决策和权重桥接是 Integration 的前置必需。

**归属：CP-10 Validation 核心实现的一部分（非外挂）**
- 实际上这不应该算"外挂"，它是 CP-10 Validation 的核心输出。
- 但三份方案处理方式不同（Claude 版在 S2-T3 内嵌、GPT-5 版单独拆出 S2-T4），需要明确：**首版 `validation_weight_plan` 始终输出 baseline `[1/3, 1/3, 1/3]`，Walk-Forward 在 S6 才做**。
- 这个"桥接最小版"的工时约 0.3d，归入 S2 Validation 任务即可，不需要独立 ENH 编号。

---

## 4. 裁决汇总表

| ENH | 名称 | 裁决 | 工时 | 阶段 | 核心链路依赖度 |
|-----|------|------|------|------|---------------|
| ENH-01 | 统一运行入口 CLI | **必留** | 0.5-0.8d | S0 | 高：五件套 run 证据直接依赖 |
| ENH-02 | 数据预检与限流 | **必留** | 0.3-0.5d | S0 | 高：TuShare 采集稳定性守卫 |
| ENH-03 | 失败产物协议 | **必留** | 0.3d | S0+S4 | 中：问题定位效率 |
| ENH-04 | 适配层契约测试 | **必留（分批）** | ~2d 总计 | S0-S4 | 高：模块间接口稳定性 |
| ENH-05 | 金丝雀数据包 | **必留** | 0.5-0.7d | S0 | 高：离线测试前置条件 |
| ENH-06 | A/B/C 对照看板 | **S3 最小版** | 0.5-1d | S3 | 低：证据工具 |
| ENH-07 | L4 产物标准化 | **延后 S5** | 0.3-0.5d | S5 | 低：展示层增强 |
| ENH-08 | 设计冻结检查 | **S0 骨架+S6 全量** | 0.5d | S0+S6 | 低：长期守卫 |
| ENH-09 | Qlib 适配层 | **必留（新增）** | 0.8-1d | S3 | **最高：核心诉求** |

> 注：`validation_weight_plan` 桥接表为 Validation 核心产出，已并入核心实现，不计入 ENH 列表。

**外挂总工时**：~6-7.5d / 总 30d ≈ **20-25%**

---

## 5. 按阶段排布

### S0 外挂（~2.5d）

| 外挂 | 做什么 | 为什么在 S0 |
|------|--------|------------|
| ENH-01 | CLI 骨架 `eq run/mss/recommend/backtest/trade/gui` | 后续所有圈的 run 证据起点 |
| ENH-02 | token 预检 + tenacity 重试 | 数据采集第一步就需要 |
| ENH-03 | error_manifest.json 写入函数 | 首圈就要建立失败协议 |
| ENH-04(Data) | test_data_layer_contract.py | L1→L2 字段契约守卫 |
| ENH-05 | canary_10d mock 数据包 | 后续所有圈离线测试基础 |
| ENH-08(骨架) | freeze_check.py + freeze_anchors.json | 建立锚点，后续每圈可选运行 |

### S1 外挂（~0.5d）

| 外挂 | 做什么 | 为什么在 S1 |
|------|--------|------------|
| ENH-04(MSS) | test_mss_contract.py | 验证 mss_panorama 可被 Integration 消费 |

### S2 外挂（~0.8d）

| 外挂 | 做什么 | 为什么在 S2 |
|------|--------|------------|
| ENH-04(IRS/PAS/Validation/Integration) | 4 组契约测试 | 信号链路全模块接口守卫 |

### S3 外挂（~1.5-2d）

| 外挂 | 做什么 | 为什么在 S3 |
|------|--------|------------|
| **ENH-09** | **Qlib 适配层** | **核心诉求：Qlib 回测出结果** |
| ENH-06 | A/B/C 对照最小版 | 回测引擎可用后才能跑对照 |

### S4 外挂（~0.5d）

| 外挂 | 做什么 | 为什么在 S4 |
|------|--------|------------|
| ENH-03(复用) | 交易失败时复用 error_manifest | 交易链路也需要失败定位 |
| ENH-04(Trading) | 回测-交易口径一致性测试 | 防止回测和交易语义分叉 |

### S5 外挂（~0.5d）

| 外挂 | 做什么 | 为什么在 S5 |
|------|--------|------------|
| ENH-07 | 日报模板 + 归档命名规范 | 展示闭环的自然组成 |

### S6 外挂（~0.5d）

| 外挂 | 做什么 | 为什么在 S6 |
|------|--------|------------|
| ENH-08(全量) | 全量冻结检查 | 收敛圈最终守卫 |

---

## 6. 不做的外挂（明确排除）

以下在批判报告或行动计划中被提到，但**明确不纳入**：

| 项目 | 排除理由 |
|------|----------|
| AKShare 适配器 | 主采集源已确定为 TuShare 5000 积分。AKShare 作为备选源的价值在个人项目中不高，且会增加数据字段映射的维护负担。如果 TuShare 不可用，优先用金丝雀 mock 数据降级，而非切换数据源。 |
| vn.py / easytrader 交易适配 | S4 的纸上交易是自研的订单状态机 + 持仓管理 + 风控，不需要真实券商通道。实盘接入不在 S0-S6 范围内。 |
| RQAlpha 回测桥 | 回测主选已确定为 Qlib（系统总览 §5）。向量化回测器作为执行基线。两者已够，不再接入第三个回测引擎。 |
| backtrader 兼容适配 | 主计划 §2.3 明确"可选，不是主线"。S6 可选项，不作为外挂承诺。 |
| CP 脚本模板（run.sh/test.sh） | 对 Windows（当前开发环境）不友好。CLI `eq {subcommand}` 已覆盖此需求。 |
| Adapter 合约文档（docs/adapters/） | 契约测试（ENH-04）已覆盖接口稳定性。独立文档在个人项目中维护成本 > 收益。 |

---

## 7. 三份方案差异对外挂的影响

| 差异点 | core-frozen | Claude 详细版 | GPT-5 Codex | 本报告结论 |
|--------|-------------|--------------|-------------|-----------|
| S2 是否含 Integration | ✅ (S2 含 4CP) | ✅ (S2 含 IRS/PAS/Validation/Integration) | ❌ (S2 只含 IRS/PAS/Validation，Integration 推到 S3) | **保持核心路线口径**：S2 包含 Integration（CP-05）；通过缩小 Slice 控制负荷，不改 CP 映射 |
| Qlib 适配层编号 | 无 ENH 编号 | S3-T2 任务但无 ENH 编号 | S3-T4 任务但无 ENH 编号 | **新增 ENH-09**，用户核心诉求必须有明确编号 |
| ENH-06 何时做 | S2 | S3-T4 | S3-T5 | **S3**（回测引擎就绪后才能跑对照） |
| ENH-07 何时做 | S1/S2 | S1-T4 + S3-T3 | S5-T2 | **S5**（前面圈没有消费者，延后更合理） |

---

## 8. 最终建议

1. **ENH-01/02/03/04/05 全部必做**——它们是让核心链路"跑得起来、测得到、坏了能查"的最低保障。
2. **ENH-09（Qlib 适配层）必做**——这是用户核心诉求的直接交付物。
3. **ENH-06 在 S3 做最小版**——情绪主线有效性需要证据，但首版只要 CSV 表，不做可视化。
4. **ENH-07/08 延后**——在核心算法和回测跑通之前，报告模板和冻结检查的优先级低于任何核心实现。
5. **明确排除 AKShare/vn.py/easytrader/RQAlpha/backtrader 适配**——个人项目不需要多数据源和多回测引擎的适配器生态。
6. **外挂总工时控制在 20-25%**——核心实现必须占 60%+，这是"核心不动只落地"原则的刚性约束。

---

## 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-02-11 | v3.0.0 | 二次冲突审计修订：补齐主计划正式路径、S2 保持含 Integration、Qlib 依赖改为 `emotionquant[backtest]`、ENH-08 冻结检查范围扩展到核心治理锚点、修复 ENH-04 表格格式、补充 ENH-10 历史并入说明 |
| 2026-02-11 | v2.1.0 | 状态下调为候选权威（审核中）；明确主计划仅引用正式路径，draft 仅作参考；完成 S2 口径/依赖声明/冻结检查覆盖/表格与 ENH-10 历史说明修订 |
| 2026-02-10 | v2.0.0 | 升级为权威设计文档；核心设计交叉审查修正：ENH-05 金丝雀补 index_member/index_classify、ENH-06 A/B/C/D 对照对齐铁律、ENH-04 Validation 完整字段 + 权重和检查、ENH-09 双信号源、ENH-02 对齐异常体系、新增文档对齐声明与冻结边界 |
| 2026-02-10 | v1.0.0 | 基于三份方案交叉审查 + 核心设计文档 + 批判报告全面分析，输出外挂选型裁决 |
