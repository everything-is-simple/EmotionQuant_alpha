# Task 模板（Spiral 闭环卡片）

**版本**: v4.1.0  
**最后更新**: 2026-02-14  
**适用范围**: 默认工作流 `Scope -> Build -> Verify -> Sync`

---

## 使用原则

1. 1 个 Task 仅解决 1 个最小问题。
2. 1 个 Task 建议不超过 1 天。
3. 必须写清 `run/test/artifact`，否则不算闭环。

---

## 模板

### Task: `{task_name}`

- Spiral: `S{N}`
- Task ID: `S{N}-{index}`
- Owner: `{name}`
- 预计工时: `{<=1d}`
- 能力包: `CP-0X`
- 风险等级: `Low | Medium | High`

#### 1. 目标（Scope）

一句话描述“本任务完成后系统新增的可运行能力”。

#### 2. 范围（Scope）

- In Scope:
- Out Scope:

#### 3. 输入契约（Scope）

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| 示例输入 | CP-01 | 文件存在 | P0 阻断 |

#### 4. 输出契约（Build）

- 代码文件：
- 测试文件：
- 产物文件：

#### 5. 执行命令（Verify，必须可复制）

```bash
# run

# test

# S2+ 或涉及契约/治理变更时（必须）
# python -m scripts.quality.local_quality_check --contracts --governance
```

#### 6. 验收门禁（Verify）

- [ ] `run` 命令成功
- [ ] `test` 命令成功
- [ ] 产物存在且可检查
- [ ] 关键日志无 P0/P1 未处理错误
- [ ] S2+ 或涉及契约/治理变更时，`python -m scripts.quality.local_quality_check --contracts --governance` 通过
- [ ] `Governance/specs/spiral-s{N}/review.md` 已更新（A5 Archive）

#### 7. 同步清单（Sync）

- [ ] `Governance/specs/spiral-s{N}/final.md` 已更新
- [ ] `Governance/record/development-status.md` 已更新
- [ ] `Governance/record/debts.md` 已更新（如有）
- [ ] `Governance/record/reusable-assets.md` 已更新（如有）
- [ ] `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 已更新
- [ ] 契约/治理检查结果路径已记录到 `final.md`（如适用）

#### 8. 风险与回滚

- 风险：
- 回滚方式：
- 新增债务（如有）：

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v4.1.0 | 2026-02-14 | 增加 S2+/契约变更门禁：`local_quality_check --contracts --governance`；同步清单补充检查结果归档 |
| v4.0.1 | 2026-02-11 | 修复同步清单口径：A6 增加 `SPIRAL-CP-OVERVIEW.md`，将 `review.md` 调整为 A5 产物检查项 |
| v4.0.0 | 2026-02-07 | 改为 Spiral 闭环卡片模板，显式绑定 Scope/Build/Verify/Sync |
| v3.0.0 | 2026-02-07 | 初版 Spiral Task 模板 |
