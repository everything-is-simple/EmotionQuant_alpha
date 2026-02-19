# 核心基础设施设计目录

**最后更新**: 2026-02-19  
**状态**: 设计基线有效（代码分圈落地中）

---

## 1. 目录定位

本目录存放 EmotionQuant 核心基础设施设计文档，覆盖 **5 个支撑模块**：

1. **Data Layer**：数据采集与清洗（TuShare → Parquet → DuckDB）
2. **Backtest**：可复现回测（Qlib 主选 + 本地向量化基线）
3. **Trading**：纸上交易与风控执行
4. **GUI**：可视化展示（Streamlit + Plotly）
5. **Analysis**：绩效归因与日报

---

## 2. 模块文件结构

每个模块目录统一包含 **4 类文档**（四位一体）：

```
{module}/
├── {module}-algorithm.md          # 处理逻辑、计算流程、约束条件
├── {module}-data-models.md        # 数据模型、字段定义、表结构
├── {module}-api.md               # 接口契约、输入输出、异常语义
└── {module}-information-flow.md  # 模块间信息流与依赖边界
```

### 2.1 完整文件清单

**Data Layer （data-layer/）**
- `data-layer-algorithm.md`
- `data-layer-data-models.md`
- `data-layer-api.md`
- `data-layer-information-flow.md`

**Backtest （backtest/）**
- `backtest-algorithm.md`
- `backtest-data-models.md`
- `backtest-api.md`
- `backtest-information-flow.md`
- `backtest-engine-selection.md`（选型策略，额外文档）
- `backtest-test-cases.md`（测试用例，额外文档）

**Trading （trading/）**
- `trading-algorithm.md`
- `trading-data-models.md`
- `trading-api.md`
- `trading-information-flow.md`

**GUI （gui/）**
- `gui-algorithm.md`
- `gui-data-models.md`
- `gui-api.md`
- `gui-information-flow.md`

**Analysis （analysis/）**
- `analysis-algorithm.md`
- `analysis-data-models.md`
- `analysis-api.md`
- `analysis-information-flow.md`

---

## 3. 模块职责与核心功能

### 3.1 Data Layer：数据采集与清洗

**职责**：从 TuShare 双通道采集 A 股数据，清洗后存入本地 Parquet/DuckDB  
**输入**：TuShare API（10000 网关主 + 5000 官方兜底）  
**输出**：L1 八张原始表（`raw_daily`, `raw_daily_basic`, `raw_limit_list` 等）+ L2 快照表（`market_snapshot`, `industry_snapshot`, `stock_gene_cache`）  
**核心功能**：
- 增量补采与全量拉取
- Parquet 落盘 + DuckDB 入库
- 异常重试（tenacity）与限流控制
- 交易日历管理

### 3.2 Backtest：可复现回测

**职责**：将 `integrated_recommendation` 转化为回测信号，执行历史回测  
**输入**：`integrated_recommendation` + 历史价格数据  
**输出**：`backtest_results` + `backtest_trade_records`  
**核心功能**：
- Qlib 适配层（主选研究平台）
- 本地向量化回测器（执行基线，对齐 A 股规则）
- backtrader 兼容适配（可选）
- A/B/C 对照框架（情绪主线 / 随机选股 / 等权持有）

### 3.3 Trading：纸上交易与风控执行

**职责**：将推荐信号转化为订单，执行风控检查，管理持仓  
**输入**：`integrated_recommendation` + `validation_gate_decision`  
**输出**：`trade_records` + `positions` + `risk_events`  
**核心功能**：
- 信号→订单转化（集合竞价/限价单）
- **风控检查**：资金、单股仓位（20%）、行业集中度（30%）、总仓位（80%）
- **A 股规则强制**：T+1、涨跌停、交易时段
- 止损止盈管理

### 3.4 GUI：可视化展示

**职责**：以只读方式展示系统数据与报告  
**输入**：L1-L4 全层数据  
**输出**：Dashboard 页面 + 导出文件  
**核心功能**：
- Streamlit 多页面布局
- Plotly 交互式图表
- 温度曲线、行业热力图、个股评分卡
- GUI 只读展示，不执行算法计算

### 3.5 Analysis：绩效归因与日报

**职责**：分析回测/交易结果，输出绩效归因与日度报告  
**输入**：`backtest_results` + `trade_records` + L3 算法输出  
**输出**：`daily_report` + `performance_metrics` + `signal_attribution`  
**核心功能**：
- 年化收益、最大回撤、Sharpe 计算
- 信号归因（哪个系统贡献最大）
- Markdown 日报模板生成
- 报告归档命名规范

---

## 4. 使用指南

### 4.1 如何阅读这些文档

**按链路顺序阅读**：
1. `data-layer/`（数据从哪里来）
2. `backtest/`（回测怎么跑）
3. `trading/`（交易怎么执行 + 风控怎么守卫）
4. `analysis/`（结果怎么分析）
5. `gui/`（最终怎么展示）

**实现时阅读顺序**：
1. 先读 `*-data-models.md` 确认字段定义
2. 再读 `*-api.md` 确认接口契约
3. 最后读 `*-algorithm.md` 实现处理逻辑
4. 参考 `*-information-flow.md` 理解模块间依赖

### 4.2 核心基础设施链路流程

```text
核心算法输出 (integrated_recommendation)
  ↓
┌──────────────────────────────────────┐
│  Backtest (历史回测)                  │
│  Trading  (纸上交易 + 风控)           │
└──────────────────────────────────────┘
  ↓
Analysis (绩效归因 + 日报)
  ↓
GUI (可视化展示)
```

### 4.3 与核心算法的关系

- 基础设施模块**消费**核心算法输出，不生成交易信号
- 基础设施模块是**可替换的**：可换回测引擎、换 GUI 框架、换数据源
- 核心算法模块是**不可替换的**：MSS/IRS/PAS/Validation/Integration 的语义固定

---

## 5. 边界说明

### 5.1 设计约束

- 基础设施的职责是**服务核心算法**，不得反向改写算法语义
- 数据存储统一使用 Parquet + DuckDB，路径/密钥通过 `Config.from_env()` 注入
- A 股规则（T+1、涨跌停、交易时段）在 Trading/Backtest 中刚性执行

### 5.2 允许变更范围

1. 替换数据源适配器（如 TuShare → 其他数据源）
2. 替换回测引擎（如 Qlib → backtrader）
3. 替换 GUI 框架（如 Streamlit → 其他）
4. 调整风控参数（仓位上限、止损比例等）

### 5.3 禁止事项

1. 在基础设施中实现交易决策逻辑
2. 绕过核心算法直接生成推荐信号
3. 硬编码路径/密钥/API Token

---

## 6. 参考资料

- 系统总览：`docs/system-overview.md`
- 模块索引：`docs/module-index.md`
- 回测选型策略：`backtest/backtest-engine-selection.md`
- 系统铁律：`Governance/steering/系统铁律.md`
