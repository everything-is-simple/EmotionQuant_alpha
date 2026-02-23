# SpiralRoadmap 目录说明

**状态**: Active  
**更新时间**: 2026-02-23  
**定位**: Spiral 执行路线与依赖图目录（执行伴随文档，不替代上位 SoT）

---

本目录存放 Spiral 路线执行文档与依赖关系文档。

## PlanA / PlanB 集中入口

- `planA/planA-OVERVIEW.md`
  - Plan A 关联文件集中入口（增强主线，主路线文件已迁移到 `planA/`）
- `planA/planA-ENHANCEMENT.md`
  - Plan A 增强方案正文
- `planB/planB-REBORN-SPIRAL-OVERVIEW.md`
  - Plan B（Reborn 螺旋闭环）总览

## 当前执行入口

- `planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
  - S0-S2c 微圈执行合同（实操层）
- `planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
  - 阶段B（S3a-S4b）微圈执行合同（实操层）
- `planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
  - 阶段C（S5-S7a）微圈执行合同（实操层）
- `planA/EXECUTION-CARDS-INDEX.md`
  - Plan A 全执行卡集中索引（按阶段A/B/C分组）
- `S3AR-S3B-EXECUTABLE-TASKLIST.md`
  - S3ar/S3b 四列表任务单（文件/命令/测试/产物），用于把债务清偿计划落到可执行粒度
- `planA/SPIRAL-PRODUCTION-ROUTES.md`
  - S0-S7a 三套完整实战路线（推荐/稳健/激进，含 S3b 收益归因与 S4b 极端防御专项）
- `SPIRAL-STAGE-TEMPLATES.md`
  - 阶段A/B/C 标准模板（目标/门禁/产物/回退）
- `planA/VORTEX-EVOLUTION-ROADMAP.md`
  - 全局进度看板与圈序约束
- `planA/DEPENDENCY-MAP.md`
  - Spiral/ENH 依赖图与阻断条件

## 执行环境口径

- 仓库根目录：`${REPO_ROOT}`（当前工作目录）
- 数据目录：`${DATA_PATH}`（见 `.env` / `.env.example`）
- DuckDB 目录：`${DUCKDB_DIR}`（见 `.env` / `.env.example`）
- 远端主库：`${REPO_REMOTE_URL}`
- 远端备份库：`backup`（本地 git remote 配置）
- Git 远端约定：`origin=主库`，`backup=备份库`

## 统一门禁入口（执行前）

- 本地一致性检查（推荐最小门禁）：
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- 可选补充（硬编码路径扫描）：
  - `python -m scripts.quality.local_quality_check --scan`
- CI 阻断工作流：
  - `.github/workflows/quality-gates.yml`

## 清理原则

- 过时评审、旧版归档原文、历史草稿、空文件全部删除
- 本目录文档不得替代上位 SoT：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.7 | 2026-02-23 | 清理兼容入口：删除 `PLAN-A-ENHANCEMENT.md`，统一保留 `planA/planA-ENHANCEMENT.md` |
| v2.6 | 2026-02-23 | 执行卡物理迁移：全部 `*-EXECUTION-CARD.md` 迁入 `planA/execution-cards/`，新增 `planA/EXECUTION-CARDS-INDEX.md` 并完成全仓引用改写 |
| v2.5 | 2026-02-23 | PlanA 完全物理迁移：`SPIRAL-S0-S2/S3A-S4B/S5-S7A`、`VORTEX`、`DEPENDENCY`、`SPIRAL-PRODUCTION-ROUTES` 迁入 `planA/`，并完成全仓引用改写 |
| v2.4 | 2026-02-23 | 新增 PlanA/PlanB 集中入口：`planA/planA-OVERVIEW.md`；`PLAN-A-ENHANCEMENT.md` 转为兼容跳转入口 |
| v2.3 | 2026-02-20 | 按 6A 工作流补齐阶段C执行卡索引：新增 `S5/S5R/S6/S6R/S7A/S7AR-EXECUTION-CARD.md` |
| v2.2 | 2026-02-20 | 阶段B执行卡索引新增 `S3C/S3D/S3E-EXECUTION-CARD.md`，与主控路线新增的核心实现深度圈保持一致 |
| v2.1 | 2026-02-19 | 新增 `S3AR-S3B-EXECUTABLE-TASKLIST.md` 入口，用于 S3ar/S3b 四列表执行拆解（文件/命令/测试/产物） |
| v2.0 | 2026-02-18 | 按 6A 工作流补齐阶段B全子圈执行卡索引：新增 `S3/S3R/S4/S4R/S3B/S4B/S4BR-EXECUTION-CARD.md` |
| v1.9 | 2026-02-16 | 同步 S2c 算法深化圈：S0-S2 口径升级为 S0-S2c，并纳入 `Governance/SpiralRoadmap/planA/execution-cards/S2C-EXECUTION-CARD.md` 索引 |
| v1.8 | 2026-02-16 | 新增 `Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md` 入口，补齐阶段C（S5-S7a）可执行合同索引 |
| v1.7 | 2026-02-16 | 新增 `Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md` 入口，补齐阶段B（S3a-S4b）可执行合同索引 |
| v1.6 | 2026-02-16 | 新增 `Governance/SpiralRoadmap/planA/execution-cards/S3A-EXECUTION-CARD.md` 入口，并将下一阶段执行卡扩展到 S3a（ENH-10） |
| v1.5 | 2026-02-15 | 扩展执行卡索引：从单张 `S0A` 补齐到 `S0A~S2R` 全微圈执行卡 |
| v1.4 | 2026-02-15 | 新增 `Governance/SpiralRoadmap/planA/execution-cards/S0A-EXECUTION-CARD.md` 入口，作为 S0a 微圈一页执行卡 |
| v1.3 | 2026-02-15 | 新增 `SPIRAL-STAGE-TEMPLATES.md` 入口，统一阶段级执行模板引用 |
| v1.2 | 2026-02-15 | 目录说明同步新增 S3b/S4b 专项圈位口径（收益归因与极端防御） |
| v1.1 | 2026-02-14 | 增加目录元信息；执行环境改为环境变量口径；新增统一门禁入口（local quality + CI） |
| v1.0 | 2026-02-13 | 首版 |
