# S3b 执行卡（v0.4）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-25  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3b（收益归因验证闭环）

---

## 0. 现状对齐（2026-02-21）

- 本卡仍为执行中，不得标记为 `Completed`。
- `eq analysis` 最小闭环已落地，但窗口级归因证据尚未收口。
- 固定窗口 `20260210-20260213` 已从 `FAIL` 解锁为 `WARN/GO`（无成交样本按 N/A 口径记警告，不再硬阻断）。
- S3b 未收口前，仍不得推进 S3c/S3d/S3e 的完成声明。

---

## 1. 目标

- 完成 A/B/C 对照与实盘-回测偏差三分解（signal/execution/cost）。
- 输出“收益来源结论”（信号主导或执行主导），作为 S4b 防御参数校准输入。
- 完成 `MSS vs 随机基准`、`MSS vs 技术基线(MA/RSI/MACD)` 对照并给出可复核结论。
- 形成可复核归因证据，避免仅凭回测推断。

---

## 2. run

```bash
eq analysis --start {start} --end {end} --ab-benchmark
eq analysis --date {trade_date} --deviation live-backtest
```

---

## 3. test

```bash
pytest tests/unit/analysis/test_ab_benchmark_contract.py -q
pytest tests/unit/analysis/test_live_backtest_deviation_contract.py -q
pytest tests/unit/analysis/test_attribution_summary_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3b/{trade_date}/ab_benchmark_report.md`
- `artifacts/spiral-s3b/{trade_date}/live_backtest_deviation_report.md`
- `artifacts/spiral-s3b/{trade_date}/attribution_summary.json`
- `artifacts/spiral-s3b/{trade_date}/consumption.md`
- `artifacts/spiral-s3b/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `ab_benchmark_report/attribution_summary` 与 `analysis-data-models.md` 一致性）
- `ab_benchmark_report.md` 必须包含：`MSS vs 随机基准`、`MSS vs 技术基线(MA/RSI/MACD)` 对比切片与窗口说明

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3b/review.md`
- 必填结论：
  - A/B/C 对照是否齐备并可复核
  - 三分解是否完整且口径一致
  - 收益来源结论是否可用于 S4b 参数校准
  - `dominant_component≠'none'` 比例是否 >=50%（归因质量底线）
  - 基准对照是否齐全：`MSS vs 随机`、`MSS vs 技术基线`
  - 对照结论是否通过：若 `MSS` 同时不优于随机与技术基线，则 `go_nogo=NO_GO` 且留在 S3b
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s3b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若归因证据不完整或结论不可复核：状态置 `blocked`，留在 S3b 修复，不推进 S4b。
- 若定位到交易执行数据缺失：回退 S4/S4r 补齐后再返回 S3b。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`

---

## 9. 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

---

## 10. 独立审计进展（2026-02-21）

- 已落地最小执行入口：`eq analysis`（A/B/C 对照、实盘-回测偏差、归因摘要）。
- 已补齐并通过 S3b 合同测试：`tests/unit/analysis/*`。
- 已形成窗口证据：`artifacts/spiral-s3b/20260219/*`，结论 `quality_status=WARN`、`go_nogo=GO`。
- 固定窗口 `20260210-20260213` 已形成可复核证据：`S3 backtest` 为 `WARN/GO`（`no_long_entry_signal_in_window`），`S3b analysis` 为 `WARN/GO`（`deviation/attribution` N/A 警告），圈位继续 `Active` 进入下一收口项。

