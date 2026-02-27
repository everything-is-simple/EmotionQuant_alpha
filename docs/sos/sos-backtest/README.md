# SOS — 系统代码与核心设计的差异急救方案（Backtest 篇）

**创建日期**: 2026-02-27
**状态**: 🔴 待审阅 → 待决策 → 待执行
**涉及设计文档版本**: backtest-algorithm v3.5.1 / backtest-api v3.5.1 / backtest-data-models v3.5.0 / backtest-information-flow v3.5.0
**涉及代码路径**: `src/backtest/pipeline.py`, `src/config/config.py`

---

## 目录结构

| 文件 | 内容 |
|------|------|
| `README.md` | 本文件：总览与决策入口 |
| `01-gap-inventory.md` | 完整差异清单（12项 🔴 + 7项 🟡） |
| `02-risk-assessment.md` | 每项差异的业务风险与技术债评估 |
| `03-remediation-plan.md` | 修复方案：分级、分批、可执行的急救路线 |

---

## 差异严重度总览

| 严重度 | 数量 | 关键词 |
|--------|------|--------|
| 🔴 根本性偏离 | 12 | 卖出逻辑退化为次日清仓、max_drawdown公式错误、total_return口径偏差、信号过滤4层只实现1层、Gate全局阻断非逐日、仓位基数用cash非equity、核心绩效指标全缺、max_positions约束缺失、成交价无滑点、回测模式TD/BU不区分、成交概率模型不一致、停牌处理缺失 |
| 🟡 次要偏离 | 7 | 架构OOP→单函数、7个dataclass全缺、7个枚举全缺、trade_records表结构偏离、backtest_results表结构偏离、BacktestState状态机缺失、代码含设计未涉及概念 |

## 核心矛盾一句话

> 设计是一个 **条件触发退出（止损/止盈/时限）+ 多引擎多模式 + 完整绩效评估** 的策略回测系统；
> 代码是一个 **T+1 无条件清仓 + 单路径信号消费 + Spiral S3 门禁产物** 的阶段性实现。
> Backtest设计中约 70% 的核心交易逻辑在代码中缺失或语义反转，**回测结果不可信**。

---

## 与 Analysis 的跨模块断裂

除了 Backtest 内部的代码-设计偏差外，还存在关键的 **跨模块数据断裂**（与 Analysis 篇 GAP-A07/A08/A12 对应）：

1. **equity_curve 断裂**：Backtest 在内存中计算了完整的 `equity_curve: list[float]`（pipeline.py ~1017,1492），但未持久化到 `backtest_results` 表。Analysis 设计需要 equity_curve 来计算所有绩效指标（Sharpe/Sortino/Calmar/年化收益/波动率），但无法获取。
2. **费用字段断裂**：回测循环中逐笔计算了 commission/stamp_tax/transfer_fee/impact_cost，但 `BACKTEST_TRADE_COLUMNS` 中不含这些字段，费用仅汇总到 `backtest_results`。Analysis 无法做逐笔费用归因。
3. **持仓天数断裂**：设计中 `BacktestTrade` 含 `hold_days` 字段，代码中 `backtest_trade_records` 无此字段。Analysis 无法计算 `avg_holding_days`。

---

## 与 Validation 的跨模块关联

1. **Gate 消费方式**：代码从 `quality_gate_report` 读取 Gate 状态，但采用全局阻断而非设计的逐日跳过（GAP-B05）。修复时需与 Validation 篇的 Gate 输出口径对齐。
2. **contract_version 检查**：代码对 `integrated_recommendation.contract_version` 做了 `nc-v1` 前置兼容检查（与设计一致），但检查后是全局阻断而非逐信号过滤。

---

## 决策项（待讨论）

在审阅完详细文档后，需要就以下问题做出决策：

1. **方向选择**：以设计为准补代码？还是以代码现状为准修设计？还是折中（分阶段对齐）？
2. **优先级排序**：12项🔴差异中哪些必须本轮修复、哪些可延后？
3. **跨模块策略**：equity_curve 持久化、逐笔费用持久化是否与 Analysis 篇 GAP-A07/A08 合并修复？
4. **卖出逻辑**：修复为设计的条件触发退出需要重写核心回放循环，是否本轮执行？
5. **P2 架构**：是否接受单函数现状，还是重构为 OOP 类结构？
