# 核心算法设计目录

**最后更新**: 2026-02-18  
**状态**: 设计与实现已对齐（代码已落地）

---

## 1. 目录定位

本目录存放 EmotionQuant 核心算法设计文档，覆盖 **5 个核心模块**：

1. **MSS** （Market Sentiment System）：市场情绪系统
2. **IRS** （Industry Rotation System）：行业轮动系统
3. **PAS** （Portfolio Alpha System）：个股机会系统
4. **Validation**：因子与权重验证（核心算法链路的质量守卫）
5. **Integration**：三系统集成推荐

---

## 2. 模块文件结构

每个模块目录统一包含 **4 类文档**（四位一体）：

```
{module}/
├── {module}-algorithm.md          # 算法定义、计算逻辑、约束条件
├── {module}-data-models.md        # 数据模型、字段定义、枚举口径
├── {module}-api.md               # 接口契约、输入输出、异常语义
└── {module}-information-flow.md  # 模块间信息流与依赖边界
```

### 2.1 完整文件清单

**MSS （mss/）**
- `mss-algorithm.md`
- `mss-data-models.md`
- `mss-api.md`
- `mss-information-flow.md`

**IRS （irs/）**
- `irs-algorithm.md`
- `irs-data-models.md`
- `irs-api.md`
- `irs-information-flow.md`

**PAS （pas/）**
- `pas-algorithm.md`
- `pas-data-models.md`
- `pas-api.md`
- `pas-information-flow.md`

**Validation （validation/）**
- `factor-weight-validation-algorithm.md`
- `factor-weight-validation-data-models.md`
- `factor-weight-validation-api.md`
- `factor-weight-validation-information-flow.md`

**Integration （integration/）**
- `integration-algorithm.md`
- `integration-data-models.md`
- `integration-api.md`
- `integration-information-flow.md`

---

## 3. 模块职责与核心功能

### 3.1 MSS：市场情绪系统

**职责**：计算市场整体情绪温度、判定情绪周期、识别趋势方向  
**输入**：`market_snapshot`（L2）  
**输出**：`mss_panorama`（包含 `temperature`, `cycle`, `trend`, `position_advice`）  
**核心算法**：涨跌做空系数、连板效应、极端分化、跟风效应

### 3.2 IRS：行业轮动系统

**职责**：评估行业强弱度、判定行业轮动状态、输出TopN行业  
**输入**：`industry_snapshot`（L2）+ `benchmark_pct_chg`（来自 `raw_index_daily`）  
**输出**：`irs_industry_daily`（包含 `industry_score`, `rotation_status`, `rank`）  
**核心算法**：相对强度、资金流入、龙头强度、牛股基因聚合

> 说明：MSS 不直接作为 IRS 因子输入；MSS 风险敞口约束在 Integration 层协同执行。

### 3.3 PAS：个股机会系统

**职责**：评估个股机会等级、计算风险收益比、确定方向  
**输入**：`stock_gene_cache`（L2）+ `raw_daily`（L1）  
**输出**：`stock_pas_daily`（包含 `pas_score`, `opportunity_grade`, `direction`, `risk_reward_ratio`）  
**核心算法**：牛股基因、结构强度、行为特征

### 3.4 Validation：因子与权重验证

**职责**：验证 MSS/IRS/PAS 因子有效性、验证权重方案优劣、输出 Gate 决策  
**输入**：`factor_series`（L2）+ `future_returns`（L1）+ 历史 `integrated_recommendation`  
**输出**：`validation_gate_decision`（PASS/WARN/FAIL）+ `validation_weight_plan`（权重桥接）  
**核心算法**：IC/RankIC/ICIR 验证、Walk-Forward 权重评估、Gate 决策规则

### 3.5 Integration：三系统集成推荐

**职责**：消费 MSS/IRS/PAS 评分 + Validation Gate，输出统一推荐信号  
**输入**：`mss_panorama` + `irs_industry_daily` + `stock_pas_daily` + `validation_gate_decision` + `validation_weight_plan`  
**输出**：`integrated_recommendation`（28字段，包含 `final_score`, `recommendation`, `position_size`）  
**核心算法**：加权集成、方向一致性校验、集成模式决策、TopN 筛选

---

## 4. 使用指南

### 4.1 如何阅读这些文档

**首次阅读顺序**：
1. `mss/mss-algorithm.md` → `irs/irs-algorithm.md` → `pas/pas-algorithm.md`（理解三个信号生成系统）
2. `validation/factor-weight-validation-algorithm.md`（理解质量守卫机制）
3. `integration/integration-algorithm.md`（理解最终集成逻辑）

**实现时阅读顺序**：
1. 先读 `*-data-models.md` 确认字段定义
2. 再读 `*-api.md` 确认接口契约
3. 最后读 `*-algorithm.md` 实现算法逻辑
4. 参考 `*-information-flow.md` 理解模块间依赖

### 4.2 核心算法链路流程

```text
Data Layer (L1/L2)
  ↓
┌─────────────────────────────┐
│  MSS  │  IRS  │  PAS  │  (并行计算)
└─────────────────────────────┘
  ↓
Validation (因子验证 + 权重决策)
  ↓
  Gate 决策 (PASS/WARN/FAIL)
  │
  ├── FAIL → 阻断，不进入 Integration
  │
  └── PASS/WARN → 进入 Integration
       ↓
    Integration (消费 Gate + 权重方案)
       ↓
    integrated_recommendation (TopN)
       ↓
    Backtest / Trading
```

### 4.3 关键设计原则

1. **情绪优先**：MSS 是主信号来源，其他系统必须与情绪周期对齐
2. **单指标不得独立决策**：技术指标可对照/辅助特征，但不得单独触发交易
3. **Validation 是守卫而非基础设施**：因子清单硬绑定 MSS/IRS/PAS 内部因子，Gate 决策直接控制 Integration 运行
4. **每个模块输出都必须有 DuckDB 持久化表**：不依赖 parquet 作为下游契约

---

## 5. 边界说明

### 5.1 冻结区

本目录属于核心算法冻结区，以下内容**只能实现，不得改写语义**：
- 算法定义、评分口径、门禁逻辑
- 数据模型、字段定义、枚举口径
- 接口契约、输入输出、异常语义

### 5.2 允许变更范围

仅在以下场景允许修改：
1. 修复设计缺陷（必须有 R编号证据）
2. 补充缺失字段/枚举（必须有实现需求证据）
3. 优化算法性能（不改语义，仅优化计算效率）

### 5.3 禁止事项

1. 以单技术指标替代情绪因子
2. 修改核心算法链路依赖关系
3. 绕过 Validation Gate 直接调用 Integration

---

## 6. 参考资料

- 系统总览：`docs/system-overview.md`
- 模块索引：`docs/module-index.md`
- 命名约定：`docs/naming-conventions.md`
- 系统铁律：`Governance/steering/系统铁律.md`
