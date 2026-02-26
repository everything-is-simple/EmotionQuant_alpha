# S7a 执行卡（v1.0）

**状态**: Planned  
**更新时间**: 2026-02-26  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S7a（自动调度闭环：安装/观测/去重/重试）

---

## 1. 目标

- 交付每日自动调度可安装、可观测、可去重。
- 确保非交易日自动跳过，交易日重复任务幂等去重。
- 固化运行历史、失败重试与最近结果的可审计证据。
- 调度层不改业务语义，仅做编排与运维增强。

---

## 2. Scope（本圈必须/禁止）

- In Scope：`eq scheduler install/status/run-once` CLI 子命令、CalendarGuard 非交易日跳过、Idempotency 幂等去重、RunHistory 运行历史可审计、失败重试（最多3次、间隔5分钟）、gate_report §Design-Alignment-Fields。
- Out Scope：盘中增量调度（`run_intraday_incremental`）、QualityMonitor 全量检查、DataBackfill 回填机制、服务化部署。

---

## 3. 模块级补齐任务（全部必做）

| 模块 | 必须补齐 | 设计依据 | 验收要点 |
|---|---|---|---|
| SchedulerCore | `eq scheduler install`：注册每日任务（默认 16:00 CST）；`eq scheduler status`：查询当前状态；`eq scheduler run-once`：手动触发单日全链路 | `docs/design/core-infrastructure/data-layer/data-layer-api.md` §6 DataScheduler API | install/status/run-once 三命令可用；内部按 data-layer 设计抽象 |
| CalendarGuard | 消费 `raw_trade_cal` 判断是否交易日；非交易日自动跳过并记录 skip 事件 | `docs/design/core-infrastructure/data-layer/data-layer-algorithm.md` §7.1 调度时间表 | 非交易日不执行产线；交易日跳过不默认触发 |
| RunHistory + Idempotency | `task_execution_log` 表记录每次执行（trade_date/task_name/start_time/end_time/status/error_message）；同 trade_date+task_name 幂等去重；失败重试最多3次、间隔5分钟 | `docs/design/core-infrastructure/data-layer/data-layer-algorithm.md` §6.2 任务执行日志 + §7.2 调度器实现 | 运行历史可审计；重复执行不重复写入 |

---

## 4. run

**baseline**（圈前健康检查）：

```bash
pytest tests/unit/config/test_env_docs_alignment.py -q
python -m scripts.quality.local_quality_check --contracts --governance
```

**target**（本圈收口必须成立）：

```bash
eq scheduler install
eq scheduler status
eq scheduler run-once
```

---

## 5. test

**baseline**（已存在）：

```bash
pytest tests/unit/config/test_env_docs_alignment.py -q
pytest tests/unit/scripts/test_contract_behavior_regression.py -q
```

**target**（本圈必须补齐并执行）：

```bash
pytest tests/unit/pipeline/test_scheduler_install_contract.py -q
pytest tests/unit/pipeline/test_scheduler_calendar_idempotency.py -q
pytest tests/unit/pipeline/test_scheduler_run_history_contract.py -q
```

验证要点：

- **CalendarGuard**：非交易日自动跳过，交易日正常执行。
- **Idempotency**：同一 trade_date+task_name 重复调用不重复写入。
- **RunHistory**：`task_execution_log` 可查询、失败重试记录可追溯。

---

## 6. artifact

- `artifacts/spiral-s7a/{trade_date}/scheduler_status.json`
- `artifacts/spiral-s7a/{trade_date}/scheduler_run_history.md`
- `artifacts/spiral-s7a/{trade_date}/scheduler_bootstrap_checklist.md`
- `artifacts/spiral-s7a/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s7a/{trade_date}/consumption.md`

---

## 7. review

- 复盘文件：`Governance/specs/spiral-s7a/review.md`
- 必填结论：
  - 调度安装与状态查询是否稳定可用
  - 交易日判定与幂等去重是否符合预期
  - 失败重试与运行历史证据是否可追溯
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 8. 硬门禁

- `eq scheduler install/status/run-once` 任一命令不可用，S7a 不得标记 `completed`。
- CalendarGuard 非交易日未跳过，状态必须置 `blocked`。
- 幂等去重失败（同 trade_date 重复写入），状态必须置 `blocked`。
- 运行历史不可审计，不得标记阶段C完成。
- `python -m scripts.quality.local_quality_check --contracts --governance` 未通过时，只允许进入 S7ar 修复圈。

---

## 9. sync

- `Governance/specs/spiral-s7a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 10. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S7ar` 修复子圈，不得标记阶段C完成。
- 若发现稳定化基线异常：回退 S6 修复后再返回 S7a。

---

## 11. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`
- Data Layer 调度 API：`docs/design/core-infrastructure/data-layer/data-layer-api.md`（§6 DataScheduler API）
- Data Layer 调度实现：`docs/design/core-infrastructure/data-layer/data-layer-algorithm.md`（§7 每日调度流程）
- 改进行动计划：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`（ENH-11 定时调度器）

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-02-26 | 升级至 S2c 同精度：新增 Scope、模块级补齐任务表（3模块）、硬门禁、质量检查命令、设计文档交叉引用（3篇）；run/test 改为 baseline+target 双层；确认落位 pipeline CLI |
| v0.1 | 2026-02-20 | 首版执行卡 |

---

---

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

（2026-02-26）

- ✅ `src/pipeline/scheduler.py` 调度模块已实现（SchedulerCore + CalendarGuard + RunHistory + Idempotency）。
- ✅ `eq scheduler install/status/run-once` CLI 子命令已落地。
- ✅ 3 个 target 测试文件已创建，26 条测试全部通过（test_scheduler_install_contract / test_scheduler_calendar_idempotency / test_scheduler_run_history_contract）。
- 待完成：端到端 artifact 产出、review/sync 闭环。

