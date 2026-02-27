# SOS — 系统代码与核心设计的差异急救方案（Analysis 篇）

**创建日期**: 2026-02-27
**状态**: 🔴 待审阅 → 待决策 → 待执行
**涉及设计文档版本**: analysis-algorithm v3.2.0 / analysis-api v4.0.0 / analysis-data-models v3.2.0 / analysis-information-flow v3.2.0
**涉及代码路径**: `src/analysis/pipeline.py`, `src/analysis/benchmark_comparison.py`, `src/backtest/pipeline.py`

---

## 目录结构

| 文件 | 内容 |
|------|------|
| `README.md` | 本文件：总览与决策入口 |
| `01-gap-inventory.md` | 完整差异清单（12项 🔴 + 4项 🟡） |
| `02-risk-assessment.md` | 每项差异的业务风险与技术债评估 |
| `03-remediation-plan.md` | 修复方案：分级、分批、可执行的急救路线 |

---

## 差异严重度总览

| 严重度 | 数量 | 关键词 |
|--------|------|--------|
| 🔴 根本性偏离 | 12 | 绩效指标全部硬编码0、日报生成完全缺失、风险分析完全缺失、equity_curve未持久化致分析层无法计算、数据模型类全部缺失、daily_report表未创建、信号偏差用score代理而非forward_return、回测费用字段缺失、Dashboard快照缺失、CSV导出缺失、L3直读缺失、CP-08最小闭环未落地 |
| 🟡 次要偏离 | 4 | API多出benchmark_mode参数、产物路径差异、bt_cost_rate硬编码0、Markdown渲染简化 |

## 核心矛盾一句话

> 设计是一个 **绩效计算 + 信号归因 + 风险分析 + 日报/周报/月报生成** 的完整分析引擎；
> 代码是一个 **A/B基准对比 + 偏差检测 + 归因分解** 的S3b阶段性最小实现。
> Analysis设计中约 60% 的核心功能在代码中完全缺失或硬编码为零值占位。

---

## 与 Backtest 的跨模块断裂

除了 Analysis 内部的代码-设计偏差外，还存在关键的 **跨模块数据断裂**：

1. **equity_curve 断裂**：Backtest 在内存中计算了完整的 equity_curve，但未持久化到 DuckDB。Analysis 设计需要 equity_curve 来计算所有绩效指标（Sharpe/Sortino/Calmar/年化收益/波动率），但代码中无法获取。
2. **费用字段断裂**：Analysis 设计期望 trade_records 含独立的 commission/slippage/impact_cost_bps 字段。Backtest 的 backtest_trade_records 不含这些字段（费用在内存中计算后未逐笔持久化）。
3. **持仓天数断裂**：设计期望 trade 含 hold_days 字段，backtest_trade_records 无此字段。

---

## 决策项（待讨论）

在审阅完详细文档后，需要就以下问题做出决策：

1. **方向选择**：以设计为准补代码？还是以代码现状为准修设计？还是折中（分阶段对齐）？
2. **优先级排序**：12项🔴差异中哪些必须本轮修复、哪些可延后？
3. **跨模块策略**：equity_curve 持久化是修 Backtest 还是修 Analysis 设计？
4. **日报/周报/月报**：是否仍然需要？还是用现有 artifacts markdown 替代？
5. **数据模型**：是否引入完整 dataclass 体系？还是继续用 dict/DataFrame？
