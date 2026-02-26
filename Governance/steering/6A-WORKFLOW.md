# EmotionQuant 6A 工作流（Spiral 闭环版）

**版本**: v6.2.2  
**最后更新**: 2026-02-17  
**状态**: 当前唯一权威工作流

---

## 1. 适用范围

- 适用于当前系统的 Spiral 开发与改进行动计划实施。
- 执行目标: 每个 Spiral 必须形成可复核闭环，禁止“看起来完成”。

---

## 2. 核心执行约束

1. 每个 Spiral 只允许 1 个主目标。
2. 每个 Spiral 只取 1-3 个 CP Slice。
3. 单个 Task 超过 1 天必须继续拆分。
4. 每个 Spiral 必须具备 `run/test/artifact/review/sync` 五件套。
5. 默认流程是 `Scope -> Build -> Verify -> Sync`，高风险时升级 Strict 6A。
6. 每个微圈必须有 1 张执行卡（Execution Card），并在各阶段模板中持续更新。

---

## 3. 6A 步骤（合并版）

### A1 Align（对齐目标）

- 执行卡要求（必须）: 建立或确认本微圈执行卡链接，未挂接执行卡不得进入 A2。
- 确定本圈主目标与 In/Out Scope。
- 明确依赖、输入、输出、失败策略。
- 产出: `Governance/specs/spiral-s{N}/requirements.md`

### A2 Architect（切片设计）

- 执行卡要求（必须）: 在执行卡中写明本圈 1-3 个 Slice、跨模块契约与验收口径。
- 从 CP 中选择 1-3 个 Slice。
- 写清跨模块输入输出契约与验收口径。
- 明确本圈 `run/test/artifact` 最小证据。

### A3 Act（最小实现）

- 执行卡要求（必须）: 在执行卡中更新实现进度、`run/test` 当前状态与阻塞项。
- 只实现当前 Slice 的最小可运行能力。
- 同步补至少 1 条自动化测试。
- 设计溯源要求（新增）: 涉及核心模块（算法/集成/编排）改动时，必须在代码中添加 `DESIGN_TRACE` 标记，指向对应 `docs/design/**` 与执行卡来源。
- 不改核心冻结区（情绪主逻辑、MSS/IRS/PAS/Validation/Integration 核心语义、Spiral+CP 主路线）。

### A4 Assert（验证收敛）

- 执行卡要求（必须）: 在执行卡登记测试结论、产物路径与 `review.md` 链接。
- `run` 可复制执行成功。
- `test` 自动化测试通过。
- `traceability` 通过：`python -m scripts.quality.local_quality_check --contracts --governance` 中的 `traceability` 检查必须 PASS。
- `artifact` 可检查且可追溯。
- 在 `review.md` 记录偏差、风险、降级策略。

### A5 Archive（复盘固化）

- 执行卡要求（必须）: 在执行卡标注复盘结论、遗留债务与对应去向。
- 产出 `review.md` 与 `final.md`。
- 整理本圈证据链（命令、测试结果、产物路径、风险处理）。
- 未解决问题同步进入 `Governance/record/debts.md`。

### A6 Advance（同步推进）

- 执行卡要求（必须）: 在执行卡标记 sync 完成，并挂接最小同步 5 项链接。
- 最小同步 5 项：
  1. `Governance/specs/spiral-s{N}/final.md`
  2. `Governance/record/development-status.md`
  3. `Governance/record/debts.md`
  4. `Governance/record/reusable-assets.md`
  5. `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`
- 若涉及改进行动计划变更，同步更新：
  - `docs/design/enhancements/eq-improvement-plan-core-frozen.md`

---

## 4. 分支与合并策略（当前口径）

- 默认口径（当前仓库）：合并目标为 `main`。
- 推荐开发分支命名：`feature/spiral-s{N}-{topic}`。
- 若后续启用 `develop`，则切换为“feature -> develop -> main（里程碑发布）”。

---

## 5. 升级 Strict 6A 条件

满足任一条件，必须按完整 6A 严格执行并增加审查深度：

1. 交易执行路径重大改动
2. 风控规则重大改动
3. 数据契约破坏性变更
4. 关键外部依赖影响主流程

---

## 6. 退出条件（Spiral 级）

以下任一未满足，本圈不得收口：

- 无可运行命令
- 无自动化测试
- 无产物文件
- 无复盘记录
- 无同步记录
- 无执行卡（或执行卡未在阶段模板中挂接）

---

## 7. 历史文件处理说明

- 旧文件 `6A-WORKFLOW-phase-to-task.md`（已归档，文件名保留原样）与 `6A-WORKFLOW-task-to-step.md`（已归档）已并入本文件，不再单独维护。
- 两文件不再作为执行入口；全局工作流统一以本文件为准。

---

## 8. 跨文档变更联动模板（执行清单）

涉及以下任一变更时，除本圈功能交付外，必须完成联动同步：

| 变更类型 | 必改文档（最小集） | 校验要求 |
|---|---|---|
| 数据契约变更（字段/语义） | 对应 `docs/design/**/data-models.md` + `Governance/archive/archive-capability-v8-20260223/CP-*.md` + `docs/naming-conventions.md` + `docs/naming-contracts.schema.json`（若命名/阈值变更） | 字段名/枚举/阈值一致，新增字段需给出默认与降级语义 |
| 风控阈值或 Gate 规则变更 | 对应 `docs/design/**/algorithm.md` + `Governance/steering/TRD.md` + `Governance/archive/archive-capability-v8-20260223/CP-*.md` | FAIL/WARN/PASS 语义一致，阻断条件可复现 |
| 数据边界变更（本地优先/远端补采） | `docs/system-overview.md` + `Governance/steering/系统铁律.md` + 对应 Data Layer 设计文档 | 不得出现主流程远端直读，降级字段口径一致 |

执行记录要求：
1. 在当圈 `review.md` 增加“跨文档联动”小节，列出已同步文件。
2. 在当圈 `final.md` 标注“联动已完成/未涉及”。
3. 若未完成联动，不得收口。
4. 推荐执行一致性检查：`python -m scripts.quality.local_quality_check --contracts --governance`

模板文件：`Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`、`Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v6.2.2 | 2026-02-17 | 新增“设计溯源”执行约束：A3 要求核心改动添加 `DESIGN_TRACE` 标记；A4 增加 traceability 门禁通过要求 |
| v6.2.1 | 2026-02-15 | 将“每个微圈必须有执行卡”落入 A1-A6 每个阶段模板，并在核心约束与退出条件中显式阻断执行卡缺失 |
| v6.2.0 | 2026-02-15 | 新增执行卡强制约束：每个微圈必须具备执行卡，且阶段模板与微圈执行合同均需挂接链接；退出条件增加执行卡缺失阻断 |
| v6.1.4 | 2026-02-14 | 跨文档联动清单补充 Schema-first 契约源（docs/naming-contracts.schema.json）；一致性检查命令升级为 --contracts --governance；模板入口补充命名契约模板 |
| v6.1.3 | 2026-02-14 | 修复 R33（review-011）：新增“跨文档变更联动模板”执行清单（契约/风控/数据边界），并明确 review/final 记录要求 |
| v6.1.2 | 2026-02-12 | 链接整理：历史文件说明改为“已并入本文件”，移除失效归档目录引用 |
| v6.1.1 | 2026-02-11 | 修正 A3 冻结区表述：补充 Integration 模块 |
| v6.1.0 | 2026-02-10 | 旧阶段拆解文件归档；明确本文件为唯一执行入口 |
| v6.0.0 | 2026-02-10 | 合并旧阶段拆解文件为单一 6A 权威流程；默认合并目标切换为 `main`，保留 `develop` 可选策略 |



