# Analysis 模块 — 代码-设计偏差总览

## 审计范围

| 维度 | 对象 |
|------|------|
| 设计文档 | `docs/design/core-infrastructure/analysis/` — algorithm v3.2 / api v4.0 / data-models v3.2 / info-flow v3.2 |
| 代码 | `src/analysis/pipeline.py`, `src/analysis/benchmark_comparison.py`, `src/backtest/pipeline.py` |

## 核心矛盾

设计是一个 **绩效计算 + 信号归因 + 风险分析 + 日报/周报/月报生成** 的完整分析引擎；
代码是一个 **A/B 基准对比 + 偏差检测 + 归因分解** 的阶段性最小实现。

**约 60% 的设计功能在代码中完全缺失或硬编码为零值占位。**

## 跨模块数据断裂

Analysis 的核心问题不仅在自身，还在上游 Backtest 的数据输出缺口：

1. **equity_curve 断裂** — Backtest 在内存中计算了完整净值曲线，但未持久化到 DuckDB。
   Analysis 设计的全部绩效指标（Sharpe/Sortino/Calmar/年化/波动率）均依赖此数据。
2. **费用字段断裂** — Backtest 逐笔费用在内存中计算后仅汇总持久化，Analysis 无法获取逐笔明细。
3. **持仓天数断裂** — Backtest 不计算也不持久化 hold_days。

## 问题统计

| 严重程度 | 数量 |
|----------|:---:|
| 🔴 致命（功能缺失/数据错误） | 12 |
| 🟡 次要（文档差异/低风险） | 4 |
| **合计** | **16** |

## 致命问题速览

| ID | 问题 | 根因 |
|----|------|------|
| A-01 | 7 个绩效指标全部硬编码 0.0 | equity_curve 未持久化 (A-07) |
| A-02 | CP-08 最小闭环未落地 | 流程架构与设计不一致 |
| A-03 | 日报生成完全缺失 | 功能未实现 |
| A-04 | 风险分析完全缺失 | 功能未实现 |
| A-05 | 14 个数据模型类全部缺失 | 代码用 dict/DataFrame 替代 |
| A-06 | 信号偏差用 score 代理而非 forward_return | 量纲错误导致偏差不自洽 |
| A-07 | equity_curve 跨模块断裂 | Backtest 未持久化净值序列 |
| A-08 | 回测交易记录缺费用明细 | Backtest 仅汇总持久化 |
| A-09 | Dashboard 快照缺失 | 功能未实现 |
| A-10 | CSV 导出缺失 | 功能未实现 |
| A-11 | L3 算法输出直读缺失 | 日报功能未实现故不需要 |
| A-12 | hold_days 字段缺失 | Backtest 未计算/持久化 |

## 文件索引

| 文件 | 内容 |
|------|------|
| `01-gap-inventory.md` | 16 项偏差逐条清单（含汇总对照表） |
| `02-risk-assessment.md` | 风险评级 P0/P1/P2 + 依赖链分析 |
| `03-remediation-plan.md` | 分 3 批次修复方案 + 依赖拓扑 |
