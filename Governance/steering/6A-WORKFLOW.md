# EmotionQuant 6A 工作流（Spiral 闭环版）

**版本**: v6.1.2  
**最后更新**: 2026-02-12  
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

---

## 3. 6A 步骤（合并版）

### A1 Align（对齐目标）

- 确定本圈主目标与 In/Out Scope。
- 明确依赖、输入、输出、失败策略。
- 产出: `Governance/specs/spiral-s{N}/requirements.md`

### A2 Architect（切片设计）

- 从 CP 中选择 1-3 个 Slice。
- 写清跨模块输入输出契约与验收口径。
- 明确本圈 `run/test/artifact` 最小证据。

### A3 Act（最小实现）

- 只实现当前 Slice 的最小可运行能力。
- 同步补至少 1 条自动化测试。
- 不改核心冻结区（情绪主逻辑、MSS/IRS/PAS/Validation/Integration 核心语义、Spiral+CP 主路线）。

### A4 Assert（验证收敛）

- `run` 可复制执行成功。
- `test` 自动化测试通过。
- `artifact` 可检查且可追溯。
- 在 `review.md` 记录偏差、风险、降级策略。

### A5 Archive（复盘固化）

- 产出 `review.md` 与 `final.md`。
- 整理本圈证据链（命令、测试结果、产物路径、风险处理）。
- 未解决问题同步进入 `Governance/record/debts.md`。

### A6 Advance（同步推进）

- 最小同步 5 项：
  1. `Governance/specs/spiral-s{N}/final.md`
  2. `Governance/record/development-status.md`
  3. `Governance/record/debts.md`
  4. `Governance/record/reusable-assets.md`
  5. `Governance/Capability/SPIRAL-CP-OVERVIEW.md`
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

---

## 7. 历史文件处理说明

- 旧文件 `6A-WORKFLOW-phase-to-task.md` 与 `6A-WORKFLOW-task-to-step.md` 已并入本文件，不再单独维护。
- 两文件不再作为执行入口；全局工作流统一以本文件为准。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v6.1.2 | 2026-02-12 | 链接整理：历史文件说明改为“已并入本文件”，移除失效归档目录引用 |
| v6.1.1 | 2026-02-11 | 修正 A3 冻结区表述：补充 Integration 模块 |
| v6.1.0 | 2026-02-10 | 旧 `phase-to-task/task-to-step` 文件归档；明确本文件为唯一执行入口 |
| v6.0.0 | 2026-02-10 | 合并 `phase-to-task` 与 `task-to-step` 为单一 6A 权威流程；默认合并目标切换为 `main`，保留 `develop` 可选策略 |


