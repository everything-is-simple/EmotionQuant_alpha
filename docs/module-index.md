# EmotionQuant 模块索引（R0-R9 实现版）

**版本**: v5.0.0
**最后更新**: 2026-02-28
**状态**: 设计与契约同步版

---

## 1. 模块结构

```
docs/
├── system-overview.md
├── module-index.md
├── naming-conventions.md
├── naming-contracts.schema.json
├── naming-contracts-glossary.md
├── design/
│   ├── core-algorithms/
│   │   ├── mss/
│   │   ├── irs/
│   │   ├── pas/
│   │   ├── validation/
│   │   └── integration/
│   ├── core-infrastructure/
│   │   ├── data-layer/
│   │   ├── backtest/
│   │   │   └── backtest-engine-selection.md
│   │   ├── trading/
│   │   ├── gui/
│   │   └── analysis/
│   └── enhancements/
│       ├── eq-improvement-plan-core-frozen.md
│       ├── enhancement-selection-analysis_claude-opus-max_20260210.md
│       └── drafts/
```

---

## 2. 核心算法模块

### 2.1 MSS

- 路径：`docs/design/core-algorithms/mss/`
- 输出：温度、周期、趋势、仓位建议

### 2.2 IRS

- 路径：`docs/design/core-algorithms/irs/`
- 输出：行业评分、轮动状态、行业排名

### 2.3 PAS

- 路径：`docs/design/core-algorithms/pas/`
- 输出：机会评分、等级、方向、风险收益比

### 2.4 Validation

- 路径：`docs/design/core-algorithms/validation/`
- 输出：Gate 决策（PASS/WARN/FAIL） + 权重桥接方案
- 作用：因子有效性验证、权重方案验证、守卫核心算法链路有效性

### 2.5 Integration

- 路径：`docs/design/core-algorithms/integration/`
- 输出：消费 Gate 决策与权重方案，统一推荐信号与解释字段

---

## 3. 基础设施模块

### 3.1 Data Layer

- 路径：`docs/design/core-infrastructure/data-layer/`
- 存储口径：Parquet + DuckDB 单库优先

### 3.2 Backtest

- 路径：`docs/design/core-infrastructure/backtest/`
- 选型口径：接口优先，可替换引擎

### 3.3 Trading

- 路径：`docs/design/core-infrastructure/trading/`
- 重点：纸上交易先行，风险规则可审计

### 3.4 GUI

- 路径：`docs/design/core-infrastructure/gui/`
- 主线技术：Streamlit + Plotly

### 3.5 Analysis

- 路径：`docs/design/core-infrastructure/analysis/`
- 重点：绩效归因与日报

---

## 4. 外挂增强设计

- 路径：`docs/design/enhancements/`
- 定位：在不改核心算法与核心基础设施语义前提下，承载可审计的增强方案
- 执行基线：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`
- 选型论证：`docs/design/enhancements/enhancement-selection-analysis_claude-opus-max_20260210.md`

---

## 5. 与路线图的关系

- 路线图采用 R0-R9 Rebuild 阶段划分，详见 `docs/roadmap.md`。
- 每阶段执行卡索引见 `docs/cards/README.md`。
- 每圈从执行卡中取切片实现，收口时必须同步更新文档与 record。

---

## 6. 命名契约与质量门禁入口

- 命名权威文档：`docs/naming-conventions.md`
- 机器可读契约源：`docs/naming-contracts.schema.json`（当前 `nc-v1`）
- 术语字典：`docs/naming-contracts-glossary.md`
- 契约联动模板：`Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`
- 跨文档联动模板：`Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`
- 本地一致性检查：`python -m scripts.quality.local_quality_check --contracts --governance`
- CI 阻断工作流：`.github/workflows/quality-gates.yml`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v5.0.0 | 2026-02-28 | R0-R9 体系对齐：标题/§5 从 CP 切换为 R0-R9 路线图引用 |
| v4.2.1 | 2026-02-14 | 补充命名契约入口（Schema/Glossary/模板）与质量门禁入口（local_quality_check/CI workflow） |
| v4.2.0 | 2026-02-11 | 对齐目录重构：设计体系统一为 `core-algorithms + core-infrastructure + enhancements`，并新增外挂增强入口说明 |
| v4.1.0 | 2026-02-07 | 增补 Validation 对应 CP-10 的路线映射 |
| v4.0.0 | 2026-02-07 | 新增 Validation 模块与回测选型文档；统一 Spiral 口径 |
| v3.1.0 | 2026-02-05 | 线性重构版 |

