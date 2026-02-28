# 债务清理卡 A — 代码骨架整固

**状态**: Completed  
**更新时间**: 2026-02-25  
**触发**: 设计-代码对齐审计 P2 债务（TD-DA-002/003/004/008）  
**定位**: 跨模块结构性重构，消除重复 + 强化类型安全  
**预估工作量**: 1 圈（~3 天）

---

## 1. 目标

消除代码中最突出的结构性债务：
- 16 处 DuckDB 工具函数重复 → 统一到 `src/db/helpers.py`
- 纯字符串枚举 → 正式 Enum 类（设计契约对齐）
- `MssScoreResult` → 与设计命名 `MssPanorama` 对齐
- `mss_score` 冗余字段标记废弃路径

---

## 2. Scope

### In Scope

| 序号 | 债务 ID | 任务 | 影响范围 |
|---|---|---|---|
| 1 | TD-DA-004 | 抽取 `_table_exists`/`_persist`/`_duckdb_type`/`_ensure_columns` 到 `src/db/helpers.py`，各模块改为 import | 16 个文件 |
| 2 | TD-DA-002 | 新建 `src/models/enums.py`，落地 `MssCycle`/`MssTrend`/`IrsRotationStatus`/`IrsRotationDetail`/`PasDirection`/`RecommendationGrade` 等 Enum | MSS/IRS/PAS/Integration |
| 3 | TD-DA-003 | `MssScoreResult` 重命名为 `MssPanorama`，保留 `MssScoreResult` 作为类型别名（backward compat） | MSS + 消费方 |
| 4 | TD-DA-008 | `mss_score` 字段添加 `@property` 废弃标记，指向 `mss_temperature` | MSS + Integration |

### Out Scope

- Calculator/Repository 接口抽象（卡 B）
- PAS discount 持久化（卡 B）
- Validation 丰富 API（卡 C）

---

## 3. 执行顺序

| 轮次 | 任务 | 预估 | 依赖 |
|---|---|---|---|
| 第 1 轮 | TD-DA-004: DuckDB helpers 抽取 | 60 min | 无 |
| 第 2 轮 | TD-DA-002: Enum 类落地 | 45 min | 无 |
| 第 3 轮 | TD-DA-003: MssScoreResult → MssPanorama | 20 min | 第 2 轮 |
| 第 4 轮 | TD-DA-008: mss_score 废弃标记 | 10 min | 第 3 轮 |

---

## 4. run

```bash
pytest tests/ -q
python -m scripts.quality.local_quality_check --contracts --governance
```

---

## 5. test

每轮完成后运行全量测试，确保无回归：
```bash
pytest tests/unit/algorithms/ tests/unit/integration/ -v --tb=short
```

---

## 6. artifact

- `src/db/__init__.py` + `src/db/helpers.py`（新建）
- `src/models/__init__.py` + `src/models/enums.py`（新建）
- 各模块 pipeline.py 的 diff（import 替换）

---

## 7. 验收标准

- `_table_exists` 全仓仅 `src/db/helpers.py` 一处定义，其他文件全部 import
- Enum 类实际被模块引用（非纸面定义）
- `MssPanorama` 为正式类名，`MssScoreResult` 为别名
- 全量测试通过（45+ tests）
- `local_quality_check --contracts --governance` 通过

---

## 8. 失败回退

- 若 helpers 抽取导致循环依赖：回退该轮，保留原副本并记录阻断原因
- 若 Enum 引入导致大量序列化/反序列化不兼容：仅在内部使用 Enum.value，外部接口保持字符串

---

## 9. 关联

- 债务来源: `Governance/SpiralRoadmap/execution-cards/DESIGN-ALIGNMENT-ACTION-CARD.md` §4
- 债务登记: `Governance/record/debts.md`（TD-DA-002/003/004/008）
- 设计枚举: `docs/design/core-algorithms/mss/mss-data-models.md`、`irs-data-models.md`、`pas-data-models.md`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-02-25 | 首版：定义卡 A（DuckDB helpers + Enum + 命名 + 冗余字段） |
| v1.0 | 2026-02-25 | 全部 4 项完成：helpers 统一（16 文件）、Enum 7 类、MssPanorama 重命名、mss_score 废弃标记；193 tests pass |
