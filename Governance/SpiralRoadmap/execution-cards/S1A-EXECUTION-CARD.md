# S1a 执行卡（v0.3）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S1a（MSS 最小评分）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，MSS 核心语义（含历史排序字段）已按完整设计实现。
- 证据锚点：`src/algorithms/mss/engine.py`、`src/algorithms/mss/pipeline.py`、`tests/unit/algorithms/mss/test_mss_contract.py`、`tests/unit/algorithms/mss/test_mss_full_semantics_contract.py`。
- 关键确认：`mss_score/mss_temperature/mss_cycle/mss_rank/mss_percentile/mss_trend_quality` 全量可追溯。

---

## 0. 定位

- 本卡对应 S1 阶段任务之一（S1 = S1a + S1b），不属于 S0。
- 本卡是 `Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md` 中 S1a 条目的可执行展开。

---

## 1. 目标

- 产出 `mss_panorama` 当日评分结果。
- 确保核心字段 `mss_score/mss_temperature/mss_cycle/mss_rank/mss_percentile/mss_trend_quality` 可追溯。
- 形成 MSS 因子轨迹与中间因子证据。

---

## 2. run

```bash
eq mss --date {trade_date}
```

---

## 3. test

```bash
pytest tests/unit/algorithms/mss/test_mss_contract.py -q
pytest tests/unit/algorithms/mss/test_mss_engine.py -q
pytest tests/unit/algorithms/mss/test_mss_full_semantics_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s1a/{trade_date}/mss_panorama_sample.parquet`
- `artifacts/spiral-s1a/{trade_date}/mss_factor_trace.md`
- `artifacts/spiral-s1a/{trade_date}/mss_factor_intermediate_sample.parquet`
- `artifacts/spiral-s1a/{trade_date}/error_manifest_sample.json`
- `artifacts/spiral-s1a/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `mss_panorama` 与 `mss-data-models.md` 一致性）

---

## 5. gate / contracts / consumption

- gate:
  - `mss_panorama` 当日记录数 `> 0`
  - 输出字段至少包含 `mss_score/mss_temperature/mss_cycle/mss_rank/mss_percentile/mss_trend_quality`
- contracts:
  - `python -m scripts.quality.local_quality_check --contracts --governance` 必须通过
- consumption:
  - S1b 必须记录 MSS 输出消费结论（`mss_only_probe_report` + `mss_consumption_case`）

---

## 6. review

- 复盘文件：`Governance/specs/spiral-s1a/review.md`
- 必填结论：
  - `mss_panorama` 当日记录是否 `> 0`
  - 核心字段（含 `mss_rank/mss_percentile/mss_trend_quality`）是否齐全
  - 因子轨迹与中间因子是否可复核
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 7. sync

- `Governance/specs/spiral-s1a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 8. 代码映射

- `src/algorithms/mss/engine.py`
- `src/algorithms/mss/pipeline.py`
- `src/pipeline/main.py`

---

## 9. 失败回退

- 若评分结果为空或字段缺失：状态置 `blocked`，仅修复 S1a，不推进 S1b。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S1a 验收。

---

## 10. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 核心设计：`docs/design/core-algorithms/mss/mss-algorithm.md`

---

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

