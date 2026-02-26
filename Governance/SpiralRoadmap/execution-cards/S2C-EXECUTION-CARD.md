# S2c 执行卡（v0.4）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2c）  
**微圈**: S2c（核心算法深化：完整语义实现 + 权重桥接硬门禁）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡“核心算法深化”任务已完成，MSS/IRS/PAS/Validation/Integration 全链路达到完整语义实现。
- 证据锚点：`src/algorithms/mss/engine.py`、`src/algorithms/irs/pipeline.py`、`src/algorithms/pas/pipeline.py`、`src/algorithms/validation/pipeline.py`、`src/integration/pipeline.py`、`tests/unit/integration/test_algorithm_semantics_regression.py`。
- 关键确认：`validation_weight_plan` 桥接硬门禁、Integration 四模式与推荐硬约束、MSS `rank/percentile` 落库均已落实。

---

## 1. 目标

- 完成核心算法 Full 语义落地：MSS/IRS/PAS/Validation/Integration 按设计文档实现，不再停留在最小可跑骨架。
- 把 `validation_weight_plan` 桥接升级为硬门禁，阻断无桥接放行。
- 形成“核心算法完成 DoD”所需关键证据。
- 明确边界：阶段 DoD 达成不等于核心算法完成，核心算法完成仅按独立 DoD 判定。

---

## 2. Scope（本圈必须/禁止）

- In Scope：MSS 六因子、IRS 六因子、PAS 三因子、Validation 因子/权重验证、Integration 权重桥接与 Gate 阻断。
- Out Scope：S3/S4 回测交易、S5-S7a GUI/稳定化/调度，不在 S2c 内完成。

---

## 3. 模块级补齐任务（全部必做）

| 模块 | 必须补齐 | 设计依据 | 验收要点 |
|---|---|---|---|
| MSS | 六因子完整实现（大盘系数、赚钱效应、亏钱效应、连续性、极端、波动）+ 统一 `ratio -> zscore -> [0,100]` + 完整温度公式 + `rank/percentile` 落库 | `docs/design/core-algorithms/mss/mss-algorithm.md` | 因子语义与权重口径一致；缺失基线回退 50；温度与 `mss_rank/mss_percentile` 可追溯 |
| IRS | 六因子完整实现（广度、连续性、资金流、估值、龙头、行业基因）+ 轮动状态判定 | `docs/design/core-algorithms/irs/irs-algorithm.md` | 不再使用简化映射；行业得分与 `rotation_status` 可审计 |
| PAS | 三因子完整实现（牛股基因、结构位置、行为确认）+ `effective_risk_reward_ratio` 口径 | `docs/design/core-algorithms/pas/pas-algorithm.md` | 因子互斥归属；不允许单指标独立触发交易；输出字段齐全 |
| Validation | 因子验证（IC/RankIC/ICIR/衰减）+ 权重验证（Walk-Forward baseline vs candidate）+ Gate 决策 | `docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md` | 产出五件套：`validation_factor_report`/`validation_weight_report`/`validation_gate_decision`/`validation_weight_plan`/`validation_run_manifest` |
| Integration | Gate 前置检查 + 权重计划解析 + 桥接链路硬门禁 + FAIL 阻断 + 四模式集成 + 推荐数量硬约束 | `docs/design/core-algorithms/integration/integration-algorithm.md` | `selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id` 全链路一致；`integration_mode` 可追溯；每日<=20/行业<=5 |

---

## 4. run

```bash
eq recommend --date {trade_date} --mode integrated --with-validation-bridge --evidence-lane release
```

```bash
python -m scripts.quality.local_quality_check --contracts --governance
```

---

## 5. test

```bash
pytest tests/unit/algorithms/mss/test_mss_full_semantics_contract.py -q
pytest tests/unit/algorithms/irs/test_irs_full_semantics_contract.py -q
pytest tests/unit/algorithms/pas/test_pas_full_semantics_contract.py -q
pytest tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py -q
pytest tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py -q
pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q
pytest tests/unit/integration/test_validation_weight_plan_bridge.py -q
pytest tests/unit/integration/test_algorithm_semantics_regression.py -q
pytest tests/unit/integration/test_integration_contract.py -q
```

---

## 6. artifact

- `artifacts/spiral-s2c/{trade_date}/mss_factor_intermediate_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/irs_factor_intermediate_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/pas_factor_intermediate_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/validation_factor_report_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/validation_weight_report_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/validation_weight_plan_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/validation_run_manifest_sample.json`
- `artifacts/spiral-s2c/{trade_date}/integrated_recommendation_sample.parquet`
- `artifacts/spiral-s2c/{trade_date}/s2c_semantics_traceability_matrix.md`
- `artifacts/spiral-s2c/{trade_date}/s2c_algorithm_closeout.md`
- `artifacts/spiral-s2c/{trade_date}/error_manifest_sample.json`
- `artifacts/spiral-s2c/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 MSS/IRS/PAS/Validation/Integration 核心产物表与对应 `*-data-models.md` 一致性）
- `artifacts/spiral-s2c-debug/{trade_date}/*`（调试/演练证据，不作为正式收口来源）

---

## 7. review

- 复盘文件：`Governance/specs/spiral-s2c/review.md`
- 必填结论：`selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id` 是否全链路一致
- 必填结论：Gate=FAIL 是否阻断、Gate=PASS/WARN 是否按契约放行
- 必填结论：IC/RankIC/ICIR 与 Walk-Forward 结果是否支持当日权重选择
- 必填结论：MSS/IRS/PAS 是否完成“设计条目 -> 实现 -> 测试 -> 产物”追踪矩阵
- 必填结论：`contract_version=nc-v1` 与 `risk_reward_ratio>=1.0` 执行边界是否一致
- 必填结论：gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 8. 硬门禁

- 任一算法模块仍为“简化映射/占位实现”，S2c 不得标记 `completed`。
- `validation_weight_plan` 桥接链路缺失或不可审计，状态必须置 `blocked`。
- `final_gate=FAIL` 必须阻断后续圈推进，不得降级放行进入 S3a/S3。
- 合同与治理检查失败时，只允许进入 S2r 修复圈。
- 正式收口证据必须来自 `evidence_lane=release`；`debug` 目录不得直接同步到 `Governance/specs/spiral-s2c`。

---

## 9. sync

- `Governance/specs/spiral-s2c/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 10. 失败回退

- 若核心语义补齐未完成：状态置 `blocked`，不得推进 S3a/S3，进入 S2r 并记录债务。
- 若桥接链路缺失或不一致：状态置 `blocked`，不得推进 S3a/S3，必须进入 S2r。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2c 验收。

---

## 11. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- MSS 设计：`docs/design/core-algorithms/mss/mss-algorithm.md`
- IRS 设计：`docs/design/core-algorithms/irs/irs-algorithm.md`
- PAS 设计：`docs/design/core-algorithms/pas/pas-algorithm.md`
- Validation 设计：`docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md`
- Integration 设计：`docs/design/core-algorithms/integration/integration-algorithm.md`

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.4 | 2026-02-21 | 升级完全版口径：补充 MSS `rank/percentile` 契约落库、Integration 四模式与推荐硬约束（每日<=20/行业<=5）为 S2c 必验项 |
| v0.3 | 2026-02-17 | 新增 `evidence_lane` 收口口径：正式证据固定 `release` 车道，`debug` 目录仅用于调试/演练 |
| v0.2 | 2026-02-16 | 明确 S2c 为“核心算法完整实现 + 桥接硬门禁”双目标；新增 MSS/IRS/PAS/Validation/Integration 模块级补齐任务、测试与产物清单 |
| v0.1 | 2026-02-16 | 首版：定义 S2c 执行卡（权重桥接 + 语义收口） |

---

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

