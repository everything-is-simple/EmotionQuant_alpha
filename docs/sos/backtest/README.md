# Backtest（回测系统）— SOS 审计总览

**范围**: `src/backtest/pipeline.py` vs backtest 设计文档 v3.5.x
**总差异**: 19 项（致命×12 / 次要×7）

---

## 核心矛盾

> 设计是一个 **条件触发退出（止损/止盈/时限）+ 多引擎多模式 + 完整绩效评估** 的策略回测系统；
> 代码是一个 **T+1 无条件清仓 + 单路径信号消费** 的阶段性实现。
> 约 70% 的核心交易逻辑在代码中缺失或语义反转。

关键缺陷：
1. **T+1 无条件清仓**：设计要求止损/止盈/时限条件退出，代码实现为买入次日无条件全部卖出
2. **max_drawdown 公式错误**：设计 `(peak-trough)/peak`，代码 `(peak-trough)/initial_capital`
3. **total_return 口径偏差**：设计 `final/initial - 1`，代码 `sum(trade_pnl)/initial`
4. **核心绩效指标全缺**：Sharpe/Sortino/Calmar/年化收益/年化波动率/胜率均未实现
5. **仓位基数错误**：设计用 equity（总权益），代码用 cash（可用现金）

## 跨模块断裂

- **equity_curve 未持久化**：内存中计算了但未写入 backtest_results 表，Analysis 无法获取
- **逐笔费用未持久化**：trade_records 表不含 commission/stamp_tax 等字段
- **hold_days 字段缺失**：Analysis 无法计算 avg_holding_days

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 19 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估
- [03-remediation-plan.md](03-remediation-plan.md) — 完整修复方案
