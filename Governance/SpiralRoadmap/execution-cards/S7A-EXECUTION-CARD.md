# S7a 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S7a（自动调度闭环）

---

## 1. 目标

- 交付每日自动调度可安装、可观测、可去重。
- 确保非交易日自动跳过，交易日重复任务幂等去重。
- 固化运行历史、失败重试与最近结果的可审计证据。

---

## 2. run

```bash
eq scheduler install
eq scheduler status
eq scheduler run-once
```

---

## 3. test

```bash
pytest tests/unit/pipeline/test_scheduler_install_contract.py -q
pytest tests/unit/pipeline/test_scheduler_calendar_idempotency.py -q
pytest tests/unit/pipeline/test_scheduler_run_history_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s7a/{trade_date}/scheduler_status.json`
- `artifacts/spiral-s7a/{trade_date}/scheduler_run_history.md`
- `artifacts/spiral-s7a/{trade_date}/scheduler_bootstrap_checklist.md`
- `artifacts/spiral-s7a/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields）
- `artifacts/spiral-s7a/{trade_date}/consumption.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s7a/review.md`
- 必填结论：
  - 调度安装与状态查询是否稳定可用
  - 交易日判定与幂等去重是否符合预期
  - 失败重试与运行历史证据是否可追溯
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s7a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S7ar` 修复子圈，不得标记阶段C完成。
- 若发现稳定化基线异常：回退 S6 修复后再返回 S7a。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 本轮进度（2026-02-20）

- 计划中，前置依赖为 S6 `PASS/WARN`。
