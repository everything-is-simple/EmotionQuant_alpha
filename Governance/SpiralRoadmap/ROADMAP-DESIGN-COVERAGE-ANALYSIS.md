# 路线图与设计文档覆盖分析

**状态**: Active  
**更新时间**: 2026-02-17  
**文档角色**: 路线图完整性审计报告（修订）

---

## 0. 分析目标

验证以下三份路线图是否完整覆盖核心设计文档：

- `Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- `Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- `Governance/SpiralRoadmap/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`

覆盖对象：

- 核心算法：`docs/design/core-algorithms/`
- 核心基础设施：`docs/design/core-infrastructure/`
- 外挂增强：`docs/design/enhancements/`

---

## 1. 设计基线盘点

### 1.1 核心算法（`docs/design/core-algorithms/`）

共 5 个模块（20 份设计文档）：

- MSS
- IRS
- PAS
- Validation
- Integration

### 1.2 核心基础设施（`docs/design/core-infrastructure/`）

共 5 个模块（22 份设计文档）：

- Data Layer（4）
- Backtest（6，含选型与测试用例）
- Trading（4）
- GUI（4）
- Analysis（4）

### 1.3 外挂增强（`docs/design/enhancements/`）

正式文档（4 份）：

- `eq-improvement-plan-core-frozen.md`（唯一执行基线）
- `enhancement-selection-analysis_claude-opus-max_20260210.md`（选型论证输入）
- `scheduler-orchestration-design.md`
- `monitoring-alerting-design.md`

ENH 外挂（11 项）：

- ENH-01 统一运行入口 CLI
- ENH-02 数据预检与限流
- ENH-03 失败产物协议
- ENH-04 适配层契约测试
- ENH-05 金丝雀数据包
- ENH-06 A/B/C 对照看板
- ENH-07 L4 产物标准化
- ENH-08 设计冻结检查
- ENH-09 Qlib 适配层
- ENH-10 数据采集增强
- ENH-11 定时调度器

---

## 2. 路线图覆盖分析

### 2.1 阶段 A（S0-S2c）

| Spiral | 主目标 | 覆盖模块 | 覆盖 ENH | 覆盖状态 |
|---|---|---|---|---|
| S0a | 统一入口与配置注入 | Data Layer（入口/配置） | ENH-01 | ✅ |
| S0b | L1 采集入库闭环 | Data Layer（L1） | ENH-02、ENH-03、ENH-04(Data) | ✅ |
| S0c | L2 快照与失败链路闭环 | Data Layer（L2） | ENH-05、ENH-08（骨架） | ✅ |
| S1a | MSS 最小评分可跑 | MSS | ENH-04(MSS) | ✅ |
| S1b | MSS 消费验证闭环 | MSS（消费验证） | - | ✅ |
| S2a | IRS + PAS + Validation 最小闭环 | IRS + PAS + Validation | ENH-04(IRS/PAS/Validation) | ✅ |
| S2b | MSS+IRS+PAS 集成推荐闭环 | Integration | ENH-04(Integration) | ✅ |
| S2c | 核心算法深化闭环 | Validation + Integration（权重桥接） | - | ✅ |
| S2r | 质量门失败修复子圈 | 阶段A修复 | - | ✅ |

阶段 A 结论：核心算法 5/5 + Data Layer 全部覆盖。

### 2.2 阶段 B（S3a-S4b）

| Spiral | 主目标 | 覆盖模块 | 覆盖 ENH | 覆盖状态 |
|---|---|---|---|---|
| S3a | 采集增强闭环 | Data Layer（执行层增强） | ENH-10 | ✅ |
| S3 | 回测闭环 | Backtest | ENH-04(Backtest)、ENH-06、ENH-09 | ✅ |
| S3r | 回测修复子圈 | Backtest（修复） | - | ✅ |
| S4 | 纸上交易闭环 | Trading | ENH-04(Trading)、ENH-03 | ✅ |
| S4r | 纸上交易修复子圈 | Trading（修复） | - | ✅ |
| S3b | 收益归因验证闭环 | Analysis | - | ✅ |
| S4b | 极端防御专项闭环 | Trading（压力场景） | - | ✅ |
| S4br | 极端防御修复子圈 | Trading（修复） | - | ✅ |

阶段 B 结论：Backtest/Trading/Analysis 完整覆盖。

### 2.3 阶段 C（S5-S7a）

| Spiral | 主目标 | 覆盖模块 | 覆盖 ENH | 覆盖状态 |
|---|---|---|---|---|
| S5 | 展示闭环 | GUI + Analysis（日报导出） | ENH-01、ENH-07 | ✅ |
| S5r | 展示修复子圈 | GUI + Analysis（修复） | - | ✅ |
| S6 | 稳定化闭环 | 全链路（Data/Backtest/Trading/Analysis/GUI） | ENH-08（全量） | ✅ |
| S6r | 稳定化修复子圈 | 全链路（修复） | - | ✅ |
| S7a | 自动调度闭环 | Data Layer（调度层）+ Trading（运行态守护） | ENH-11 | ✅ |
| S7ar | 调度修复子圈 | Data Layer + Trading（修复） | - | ✅ |

阶段 C 结论：GUI/Analysis/稳定化/调度完整覆盖。

---

## 3. 覆盖矩阵汇总

### 3.1 核心算法覆盖

| 模块 | 覆盖 Spiral | 覆盖率 |
|---|---|---|
| MSS | S1a + S1b | 100% |
| IRS | S2a | 100% |
| PAS | S2a | 100% |
| Validation | S2a + S2c | 100% |
| Integration | S2b + S2c | 100% |

### 3.2 核心基础设施覆盖

| 模块 | 覆盖 Spiral | 覆盖率 |
|---|---|---|
| Data Layer | S0a + S0b + S0c + S3a | 100% |
| Backtest | S3 + S3r | 100% |
| Trading | S4 + S4r + S4b + S4br | 100% |
| Analysis | S3b + S5 | 100% |
| GUI | S5 + S5r | 100% |

### 3.3 ENH 覆盖

| ENH | 覆盖 Spiral | 覆盖状态 |
|---|---|---|
| ENH-01 | S0a + S5 | ✅ |
| ENH-02 | S0b | ✅ |
| ENH-03 | S0b + S4 | ✅ |
| ENH-04 | S0b/S1a/S2a/S2b/S3/S4 | ✅ |
| ENH-05 | S0c | ✅ |
| ENH-06 | S3 | ✅ |
| ENH-07 | S5 | ✅ |
| ENH-08 | S0c（骨架）+ S6（全量） | ✅ |
| ENH-09 | S3 | ✅ |
| ENH-10 | S3a | ✅ |
| ENH-11 | S7a | ✅ |

---

## 4. 结论

✅ 三份路线图对以下设计范围已实现完整覆盖：

- 核心算法（5/5，20/20）
- 核心基础设施（5/5，22/22）
- 外挂增强（ENH 11/11，正式文档 4/4）

当前无覆盖性缺口；主要风险点为文档一致性维护。

---

## 5. 风险与建议

1. 当 `docs/design/core-infrastructure/` 或 `docs/design/enhancements/` 新增正式文档时，必须同步补充路线图落位。
2. 严格执行修复子圈触发条件（`gate = FAIL` 必须先修复后推进）。
3. 严格执行阶段门禁：S2c -> S3a/S3，S4b -> S5。
4. 保持 ENH-10 前置、ENH-11 后置的排期策略，避免运维能力打断主线收口。

---

## 6. 变更记录

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.1 | 2026-02-17 | 去重重复章节；修正 ENH-05 落位为 S0c；统一阶段覆盖矩阵口径 |
| v1.0 | 2026-02-17 | 首版：路线图与核心设计覆盖分析（100%） |
