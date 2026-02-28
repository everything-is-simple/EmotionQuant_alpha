# Plan A 执行卡索引

**状态**: Active  
**更新时间**: 2026-02-27  
**定位**: Plan A 执行卡集中入口（run/test/artifact/review/sync）

---

## 阶段A（S0-S2）

- `Governance/SpiralRoadmap/execution-cards/S0A-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S0B-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S0C-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S1A-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S1B-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S2A-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S2B-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S2R-EXECUTION-CARD.md`

## 阶段B（S3-S4b）

- `Governance/SpiralRoadmap/execution-cards/S3A-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3R-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3AR-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3B-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3C-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3D-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S3E-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S4-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S4R-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S4B-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S4BR-EXECUTION-CARD.md`

## 阶段C（S5-S7a）

- `Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S5R-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S6-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S6R-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S7A-EXECUTION-CARD.md`
- `Governance/SpiralRoadmap/execution-cards/S7AR-EXECUTION-CARD.md`

---

## 状态口径（2026-02-23）

1. `Implemented（工程完成，业务待重验）`：代码与测试已落地，但尚未完成螺旋业务闭环判定。
2. `Active/Planned`：按执行卡原定义推进。
3. 螺旋闭环完成判定以：
   - `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`
   - `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`
   为准。

## 跨圈位行动卡

- `Governance/SpiralRoadmap/execution-cards/DESIGN-ALIGNMENT-ACTION-CARD.md`（设计-代码对齐修订，Completed）

## 债务清理卡

- `Governance/SpiralRoadmap/execution-cards/DEBT-CARD-A-SKELETON.md`（代码骨架整固：DuckDB helpers + Enum + 命名 + 冗余字段，Completed）
- `Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md`（契约补齐：PAS discount + Calculator/Repository + Integration 文档，Completed）
- `Governance/SpiralRoadmap/execution-cards/DEBT-CARD-C-BACKLOG.md`（滞留债务清理：bridge 修复 + Validation API + DESIGN_TRACE + legacy + AKShare，Completed）

## Revalidation 清单

- `Governance/SpiralRoadmap/planA/PLAN-A-REVALIDATION-CHECKLIST.md`

## 代码级复检快照（2026-02-27）

证据基线：`artifacts/spiral-allcards/revalidation/20260227_125427/execution_cards_code_audit_summary.md`

### 阶段A（S0-S2）
- [x] S0A
- [x] S0B
- [x] S0C
- [x] S1A
- [x] S1B
- [x] S2A
- [x] S2B
- [x] S2C
- [x] S2R

### 阶段B（S3-S4b）
- [x] S3A
- [x] S3
- [x] S3R
- [x] S3AR
- [x] S3B
- [x] S3C
- [x] S3D
- [x] S3E
- [x] S4
- [x] S4R
- [x] S4B
- [x] S4BR

### 阶段C（S5-S7a）
- [x] S5 — gui/app.py + dashboard.py + data_service.py + formatter.py + models.py 已实现，35 条 GUI 测试通过
- [ ] S5R — 条件触发修复圈，当前未触发
- [x] S6 — pipeline/consistency.py ConsistencyChecker 已实现（三层阈值），31 条测试通过
- [ ] S6R — 条件触发修复圈，当前未触发
- [x] S7A — pipeline/scheduler.py SchedulerCore + CalendarGuard + RunHistory + Idempotency 已实现，26 条测试通过
- [ ] S7AR — 条件触发修复圈，当前未触发

### 独立审计结论（2026-02-27 第二轮）

审计方法：逐文件阅读 src/ 全部源码 → 运行 308 条测试（全部通过） → 逐卡对照代码实现。

- S0A-S4BR（25 张卡）：全部代码与测试已落地，功能与执行卡描述一致。
- S5/S6/S7A（3 张主卡）：核心代码已实现，待端到端 artifact 产出与 review/sync 闭环。
- S5R/S6R/S7AR（3 张修复卡）：条件触发，当前无需代码实现。
- 源码注释：全部 ~30 个核心源文件已补充中文模块级 docstring。
