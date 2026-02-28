# S3 执行卡（v0.4）

**状态**: Implemented（工程完成） + Code-Revalidated（通过）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-25  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3（回测闭环）

---

## 0. 现状对齐（2026-02-21）

- 本卡仍为执行中，不得标记为 `Completed`。
- 回测主链路已可执行；若门禁失败，必须进入 `S3r`（`eq backtest --repair s3r`）后再回到 S3 重验。
- 已落地“无可开仓信号窗口”语义：此类窗口输出 `WARN/GO`（`no_long_entry_signal_in_window`），不再按 `P0` 硬阻断。
- 当前阻断主要在更细撮合规则与窗口级复现证据，未到“阶段B全量实战收口”。

---

## 代码级重验（2026-02-27）

- [x] run 冒烟通过（见统一审计汇总）
- [x] test 契约通过（见统一审计汇总）
- [x] 功能检查正常（见统一审计汇总）
- 结论：`通过`
- 证据：`artifacts/spiral-allcards/revalidation/20260227_125427/execution_cards_code_audit_summary.md`

## 1. 目标

- 完成 `S3` 回测闭环：Qlib 主线 + 本地口径可对照。
- 固化 `integrated_recommendation` 到回测执行的可审计消费链路。
- 产出可复核的回测结果与 A/B/C 指标摘要，作为 S4 纸上交易参数来源。

---

## 2. run

```bash
eq backtest --engine {engine} --start {start} --end {end}
```

---

## 3. test

```bash
pytest tests/unit/backtest/test_backtest_contract.py -q
pytest tests/unit/backtest/test_validation_integration_bridge.py -q
pytest tests/unit/backtest/test_backtest_reproducibility.py -q
pytest tests/unit/backtest/test_backtest_core_algorithm_coverage_gate.py -q
```

**backtest-test-cases 核心覆盖**（对齐 `docs/design/core-infrastructure/backtest/backtest-test-cases.md`）：
至少覆盖 §1（T+1 规则 3 条）、§2（涨跌停 4 条）、§4（费用模型 4 条）、§9（集成模式覆盖 3 条）、§10（质量门禁 5 条）共 19 条核心用例，未覆盖用例登记到 `Governance/record/debts.md`。

---

## 4. artifact

- `artifacts/spiral-s3/{trade_date}/backtest_results.parquet`
- `artifacts/spiral-s3/{trade_date}/backtest_trade_records.parquet`
- `artifacts/spiral-s3/{trade_date}/ab_metric_summary.md`
- `artifacts/spiral-s3/{trade_date}/consumption.md`
- `artifacts/spiral-s3/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `backtest_results/backtest_trade_records` 与 `backtest-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3/review.md`
- 必填结论：
  - `validation_weight_plan` 桥接链路是否可追溯
  - A/B/C 对照是否形成稳定基线结论
  - 回测结果是否可稳定复现（同窗口重复执行差异在可接受范围内）
  - backtest-test-cases 19 条核心用例是否覆盖（未覆盖须登记债务）
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s3/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `gate = FAIL` 或桥接链路不可审计：状态置 `blocked`，进入 `S3r` 修复子圈，不推进 S4。
- 若契约/治理检查失败：先修复并补齐回归证据，再重跑 S3 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`
- 核心算法设计基线：`docs/design/core-algorithms/`

---

---

## 历史债务状态（2026-02-27 清零同步）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

（2026-02-18）

- 已进入 `in_progress`，并完成多交易日回放与板块化涨跌停阈值（10%/20%/5%）落地。
- 已补齐“完整核心算法+本地库”回测门禁：S3 对 `mss_score/irs_score/pas_score` 三因子完整性与 `mss_panorama/irs_industry_daily/stock_pas_daily` 窗口覆盖进行硬校验，并在 `consumption.md`/`gate_report.md` 输出 DuckDB 覆盖证据。
- 下一步：继续补齐更细撮合规则与可回放证据，推进 S3 收口。



