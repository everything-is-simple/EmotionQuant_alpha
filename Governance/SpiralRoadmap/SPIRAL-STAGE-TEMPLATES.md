# EmotionQuant 大阶段模板（v0.2）

**状态**: Active  
**更新时间**: 2026-02-16  
**用途**: 定义 `阶段A/B/C` 的统一执行模板，约束每个大阶段的目标、门禁、产物与失败回退。  
**角色**: 阶段级执行合同（配合微圈执行，不替代 `SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`）。

---

## 1. 使用规则

1. 本模板用于“阶段级收口与推进控制”，微圈执行仍以各圈合同为准。
2. 每个阶段必须先满足 `入口门禁` 才能开始，满足 `退出门禁` 才能进入下一阶段。
3. 任一阶段未达 `退出门禁`，只允许在本阶段内开修复子圈，不允许跳阶段推进。
4. 全阶段统一门禁：`python -m scripts.quality.local_quality_check --contracts --governance`。
5. 阶段 DoD 与核心算法完成 DoD 分离：阶段推进遵循本模板；核心算法完成仅以 `Governance/Capability/SPIRAL-CP-OVERVIEW.md` 第 9 节为准。

---

## 2. 阶段A模板（S0-S2c）

### 2.1 目标

- 打通 `入口/配置 -> L1/L2 -> MSS/IRS/PAS/Validation -> Integration` 全链路。
- 形成可追溯的推荐产物：`integrated_recommendation`。

### 2.2 入口门禁

- 本地质量门禁通过：`--contracts --governance`。
- 上位 SoT 无冲突（`Capability`、`steering`、`docs/design` 一致）。
- 当前阶段状态在治理记录中登记为 `in_progress`。

### 2.3 退出门禁

- `validation_gate_decision` 可追溯，且 `contract_version = "nc-v1"`。
- `integrated_recommendation` 稳定产出，口径与契约一致。
- `validation_weight_plan` 桥接硬门禁通过：`selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id`。
- 圈级五件套完整：`run/test/artifact/review/sync`。
- 若 S2b 或 S2c 门禁 FAIL，必须先完成 S2r 修复并重验通过。

### 2.4 必交付产物

- `quality_gate_report.md`
- `s2_go_nogo_decision.md`
- L1/L2/L3 样本快照（可复核）
- 阶段收口结论：`stage-a-closeout.md`

### 2.5 失败回退

- 仅允许回退到阶段A内修复子圈（S2r 或同级修复圈）。
- 禁止进入阶段B（S3a/S3/S4）直到门禁恢复 PASS/WARN。

---

## 3. 阶段B模板（S3a-S4b）

### 3.1 目标

- 完成回测与纸上交易闭环，验证策略执行路径。
- 明确收益来源：信号主导还是执行主导。
- 完成极端场景防御：连续跌停、流动性枯竭应急降杠杆。

### 3.2 入口门禁

- 阶段A收口通过（S2c PASS/WARN，且修复债务已登记）。
- 阶段A输入桥接链路完整（`validation_weight_plan` 硬门禁通过）。
- `integrated_recommendation` 可被 S3/S4 稳定消费。
- A 股关键约束字段齐备（T+1/涨跌停/交易时段口径可追溯）。

### 3.3 退出门禁

- A/B/C 对照完成，并形成可复核结论。
- `live-backtest` 偏差分解齐备：`signal/execution/cost`。
- 压力场景回放通过，极端防御策略可执行可重放。
- 阶段内五件套完整，治理同步完成。

### 3.4 必交付产物

- `backtest_results`、`backtest_trade_records`
- `trade_records`、`positions`、`risk_events`
- `ab_benchmark_report.md`
- `live_backtest_deviation_report.md`
- `extreme_defense_report.md`
- 阶段收口结论：`stage-b-closeout.md`

### 3.5 失败回退

- 留在阶段B内开修复子圈（如 S3r/S4r/S4br）并重验。
- 若发现阶段A输入契约异常，回退阶段A修复后再返回阶段B。

---

## 4. 阶段C模板（S5-S7a）

### 4.1 目标

- 完成 GUI + 报告导出标准化。
- 完成稳定化重跑一致性验证。
- 完成自动调度上线与运维可观测闭环。

### 4.2 入口门禁

- 阶段B收口通过（含归因与极端防御结论）。
- 风险阈值与运行策略已有基线版本。
- 调度前置条件明确（交易日判定、幂等键、失败告警）。

### 4.3 退出门禁

- 全链路重跑一致性通过（核心产物可复现）。
- 调度行为可审计：状态、历史、失败重试可追踪。
- 非交易日自动跳过与重复任务去重有效。
- 阶段内五件套完整，治理同步完成。

### 4.4 必交付产物

- GUI 页面快照与日报导出样本
- `consistency_replay_report.md`
- `scheduler_status.json`
- `scheduler_run_history.md`
- `scheduler_bootstrap_checklist.md`
- 阶段收口结论：`stage-c-closeout.md`

### 4.5 失败回退

- 优先在阶段C内修复并重验。
- 若发现阶段B归因/防御参数失真，回退阶段B重校准后再推进。

---

## 5. 阶段状态机（统一）

| 状态 | 说明 | 可执行动作 |
|---|---|---|
| planned | 已定义未启动 | 准备入口门禁 |
| in_progress | 执行中 | 圈内实现与验证 |
| blocked | 被门禁阻断 | 仅修复，不推进 |
| completed | 阶段收口完成 | 可进入下一阶段 |

约束：

1. 不满足 `退出门禁` 不得标记 `completed`。
2. `blocked` 必须记录阻断原因与修复计划（写入 `review/debts`）。
3. 阶段切换必须更新 `Governance/record/development-status.md`。

---

## 6. 与现有文档关系

- 全局看板：`Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
- 执行路线：`Governance/SpiralRoadmap/SPIRAL-PRODUCTION-ROUTES.md`
- S0-S2c 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 上位 SoT：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.2 | 2026-02-16 | 阶段A口径从 S0-S2 升级为 S0-S2c；新增 `validation_weight_plan` 桥接硬门禁（阶段A出口 + 阶段B入口）；明确阶段 DoD 与核心算法 DoD 分离 |
| v0.1 | 2026-02-15 | 首版：定义阶段A/B/C统一模板（目标、入口门禁、退出门禁、必交付产物、失败回退）并对齐现有 Spiral 圈序 |
