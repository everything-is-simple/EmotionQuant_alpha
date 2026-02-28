# Trading 模块 — 代码-设计偏差总览

## 审计范围

| 维度 | 对象 |
|------|------|
| 设计文档 | `docs/design/core-infrastructure/trading/` 全部 4 文档 (v3.3 + api v4.0) |
| Trading 代码 | `src/trading/pipeline.py` (1 225 行) |
| Backtest 代码 | `src/backtest/pipeline.py` (~1 700 行) |

Trading 与 Backtest 共享同一套设计约束（算法、A股规则、成交模型、费用公式），因此本模块同时审计
**Trading→设计** 偏差和 **Backtest→设计** 偏差，以及两套代码之间的**交叉一致性**。

## 核心病理：三角脱节

```
         设计文档 (v3.3)
          /          \
   严重偏离        严重偏离
        /              \
Trading 代码 ←不一致→ Backtest 代码
```

- **设计** 定义完整 OOP 架构、28 字段 trade_records、部分成交模型、6 项风控、条件平仓
- **Trading 代码** 极简 Pipeline，全额成交，无止损，无成交模型
- **Backtest 代码** 独立实现了部分高级功能（成交模型、冲击成本），又缺失另一些（总仓位上限）

三方在信号过滤、费用计算、成交模型、持仓卖出策略上**全面不一致**。

## 问题统计

| 严重程度 | Trading→设计 | Backtest→设计 | 合计 |
|----------|:---:|:---:|:---:|
| P0 致命 | 6 | 1 | 7 |
| P1 严重 | 5 | 5 | 10 |
| P2 中度 | 4 | 4 | 8 |
| P3 轻度 | 1 | 0 | 1 |
| **合计** | **16** | **10** | **26** |

## 致命问题速览 (P0)

1. **成交模型完全缺失** — Trading 用"开盘价全额成交"，设计要求 fill_probability + fill_ratio + impact_cost
2. **信号字段仅读 10/18** — 缺 stop/target/neutrality/opportunity_grade 等 8 字段
3. **信号质量验证 v2.0 不存在** — 无 neutrality 风险分级、无仓位调整
4. **风控 6 项仅实现 3 项** — 单股仓位上限、行业集中度、Regime 阈值全缺
5. **止损/止盈/回撤检查全缺** — 两套代码都是 T+1 无条件全卖
6. **t1_frozen 独立表未建** — 用 can_sell_date 字段内联替代
7. **Backtest 无总仓位上限** — Trading 有但 Backtest 缺失

## 文件索引

| 文件 | 内容 |
|------|------|
| `01-gap-inventory.md` | 26 项偏差逐条清单（含三方对照矩阵） |
| `02-risk-assessment.md` | 风险评级、级联影响分析、三方一致性矩阵 |
| `03-remediation-plan.md` | 分 4 批次修复方案 + 6 项决策点 |
