# SOS — 系统代码与核心设计差异审计总库

**审计日期**: 2026-02-27
**审计立场**: 设计文档为唯一权威口径。代码偏离设计的，修代码。无例外。
**目标系统**: 正规实战系统。不搞 demo，不搞缩量版，不做权宜之计。

---

## 审计总览

| 模块 | 目录 | 总差异 | 致命/严重 | 核心结论 |
|------|------|--------|-----------|----------|
| 数据层 | `data-layer/` | 14 | 5×P0 | 快照计算逻辑错误，cascade 污染全链路 |
| MSS | `mss/` | 12 | 3×P0 | 核心算法正确，information-flow 文档严重滞后 |
| IRS | `irs/` | 8 | 3×致命 | 归一化路径数学不等价，calculator 副本漂移 |
| PAS | `pas/` | 16 | 8×P0 | 三因子公式全部偏离设计，需完整重写 |
| Validation | `validation/` | 13 | 11×致命 | 架构级断裂：因子名零重叠、IC 语义错误、WFA 为公式估算 |
| Integration | `integration/` | 19 | 7×P0 | final_score 计算错误、模式语义偏离 |
| Backtest | `backtest/` | 19 | 12×致命 | T+1 无条件清仓、公式错误、绩效指标全缺 |
| Trading | `trading/` | 26 | 5×P0 | 三角脱节：设计/Trading代码/Backtest代码 各不一致 |
| Analysis | `analysis/` | 16 | 12×致命 | 60% 功能缺失，绩效指标全部硬编码 0 |
| GUI | `gui/` | 25 | 7×P0 | 架构完全不同（设计 4 层 18 文件 vs 代码 5 文件）|
| 增强 | `enhancements/` | 15 | 5×致命 | Qlib 适配层完全缺失、监控仅占位 |

**总计 183 项差异，其中 ~80 项为致命/严重级。**

---

## 跨模块依赖链

```
数据层 P0（快照计算错误）
  ↓ cascade
MSS 温度 / IRS 行业分 / PAS 基因库 → 全部受污染
  ↓
Validation Gate 不可信（且自身也是架构级断裂）
  ↓
Integration final_score 错误
  ↓
Backtest 回测结果不可信（且自身卖出逻辑也是错的）
  ↓
Trading 交易信号不可信
  ↓
Analysis 绩效全部为 0
  ↓
GUI 展示的是错误数据
```

**结论：不是局部修补能解决的。必须按依赖链自底向上重建。**

---

## 审计立场声明

1. **设计文档是唯一权威**。经过多轮推敲修订的核心设计不可动摇。代码偏离设计的，一律修代码。
2. **不接受"先简化后补齐"**。每一项设计规格必须完整实现。不存在"MVP 先行"或"标记为技术债"的选项。
3. **OOP 架构强制**。设计定义的是 Service/Repository/Engine/Model 四件套，代码必须遵循。
4. **Qlib 为唯一回测主线**。不维护并行回测引擎。
5. **代码中合理的超额实现**（如 style_bucket、risk_events 等）须反向补入设计文档。

---

## 标准文件结构

每个模块目录统一包含 4 个文件：

```
{module}/
├── README.md              # 总览：差异全景、核心矛盾、影响链
├── 01-gap-inventory.md    # 差异清单：逐项列出，含代码位置和设计原文
├── 02-risk-assessment.md  # 风险评估：每项的业务影响和技术风险
└── 03-remediation-plan.md # 修复方案：完整实现方案，分批但不分级
```

---

## 代码验证方法

每项差异均经过以下验证流程：
1. **设计原文定位**：找到对应的 `docs/design/` 文件和章节
2. **代码定位**：找到对应的 `src/` 文件和行号
3. **逻辑比对**：逐公式、逐字段、逐流程比对
4. **实锤确认**：在代码中找到具体的偏离证据

所有 183 项差异均已通过此流程确认。无误报。

---

## 模块导航

按依赖链顺序阅读：

1. [`data-layer/`](data-layer/README.md) — 数据采集与清洗（L1/L2）
2. [`mss/`](mss/README.md) — 市场情绪系统
3. [`irs/`](irs/README.md) — 行业轮动系统
4. [`pas/`](pas/README.md) — 个股机会系统
5. [`validation/`](validation/README.md) — 因子与权重验证
6. [`integration/`](integration/README.md) — 三系统集成推荐
7. [`backtest/`](backtest/README.md) — 回测系统
8. [`trading/`](trading/README.md) — 纸上交易
9. [`analysis/`](analysis/README.md) — 绩效分析
10. [`gui/`](gui/README.md) — 可视化展示
11. [`enhancements/`](enhancements/README.md) — 外挂增强
