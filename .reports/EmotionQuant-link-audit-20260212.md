# EmotionQuant 文件链接审计报告

**日期**: 2026-02-12  
**审计范围**: `G:\EmotionQuant-gpt`、`G:\EmotionQuant_data`

---

## 1. 范围与方法

1. 扫描 `EmotionQuant-gpt` 活跃文档（根目录 `*.md` + `docs/**` + `Governance/**`，排除历史归档目录）。
2. 校验 Markdown 链接（`[text](path)`）是否指向真实路径。
3. 对核心入口文档中的路径文本引用（SoT/路线/治理入口）做一致性整理。
4. 校验 `EmotionQuant_data` 文档文件数量。

---

## 2. 审计结果

- `EmotionQuant_data`：`0` 个 Markdown 文件（无文档链接可审计项）。
- `EmotionQuant-gpt`：扫描活跃 Markdown `97` 个。
- 结果：**Markdown 语法链接失效数 = 0**。

---

## 3. 本轮修复项（路径口径整理）

### 3.1 主入口文档

- `AGENTS.md`
- `CLAUDE.md`
- `WARP.md`
- `README.md`
- `README.en.md`
- `docs/system-overview.md`

修复内容：
- `enhancement-selection-analysis...` 引用补全为完整路径 `docs/design/enhancements/...`。
- `debts.md` 统一为 `Governance/record/debts.md`。
- 移除已失效 `SpiralRoadmap/draft/` 入口，统一为：
  - `Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md`
  - `Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
- 历史归档目录表述由失效路径改为当前有效口径（workflow 并入 `6A-WORKFLOW.md`）。

### 3.2 路线与治理文档

- `Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md`
- `Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
- `Governance/steering/6A-WORKFLOW.md`
- `Governance/steering/TRD.md`
- `Governance/record/reusable-assets.md`

修复内容：
- 主计划、系统总览、CP 主控引用补全为完整路径。
- 历史说明改为“已并入主文件”，移除失效归档目录引用。
- 资产登记中的失效 workflow 归档路径改为有效入口。

### 3.3 Analysis 文档归档路径统一

- `docs/design/core-infrastructure/analysis/analysis-api.md`
- `docs/design/core-infrastructure/analysis/analysis-information-flow.md`

修复内容：
- 归档路径口径统一为 `.reports/archive/analysis/...`，不再使用 `.archive/analysis/...`。

---

## 4. 结论

当前活跃文档中，Markdown 链接无失效项；核心入口文件的路径口径已完成统一，消除了主要“路径漂移/失效入口”问题。

