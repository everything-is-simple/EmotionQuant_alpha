# SpiralRoadmap 目录说明

**状态**: Active  
**更新时间**: 2026-02-15  
**定位**: Spiral 执行路线与依赖图目录（执行伴随文档，不替代上位 SoT）

---

本目录存放 Spiral 路线执行文档与依赖关系文档。

## 当前执行入口

- `SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
  - S0-S2 微圈执行合同（实操层）
- `SPIRAL-PRODUCTION-ROUTES.md`
  - S0-S7a 三套完整实战路线（推荐/稳健/激进，含 S3b 收益归因与 S4b 极端防御专项）
- `SPIRAL-STAGE-TEMPLATES.md`
  - 阶段A/B/C 标准模板（目标/门禁/产物/回退）
- `VORTEX-EVOLUTION-ROADMAP.md`
  - 全局进度看板与圈序约束
- `DEPENDENCY-MAP.md`
  - Spiral/ENH 依赖图与阻断条件
- `backlog/data-fetcher-enhancement-proposal-ENH-10-11-20260213.md`
  - ENH-10/11 提案归档（已纳入主路线）

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
| v1.3 | 2026-02-15 | 新增 `SPIRAL-STAGE-TEMPLATES.md` 入口，统一阶段级执行模板引用 |
| v1.2 | 2026-02-15 | 目录说明同步新增 S3b/S4b 专项圈位口径（收益归因与极端防御） |
| v1.1 | 2026-02-14 | 增加目录元信息；执行环境改为环境变量口径；新增统一门禁入口（local quality + CI） |
| v1.0 | 2026-02-13 | 首版 |
