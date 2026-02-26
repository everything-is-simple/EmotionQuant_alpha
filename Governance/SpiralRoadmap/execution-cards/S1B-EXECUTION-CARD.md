# S1b 执行卡（v0.3）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S1b（MSS 消费验证）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，MSS 输出消费验证闭环满足实战要求。
- 证据锚点：`src/algorithms/mss/probe.py`、`src/integration/mss_consumer.py`、`tests/unit/algorithms/mss/test_mss_probe_contract.py`、`tests/unit/integration/test_mss_integration_contract.py`。
- 关键确认：消费语义字段 `mss_trend_quality/mss_rank/mss_percentile` 已形成稳定契约。

---

## 0. 定位

- 本卡对应 S1 阶段任务之一（S1 = S1a + S1b），不属于 S0。
- 本卡是 `Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md` 中 S1b 条目的可执行展开。

---

## 1. 目标

- 打通 MSS 输出消费验证闭环（非只算分）。
- 产出 `mss_only_probe_report` 与 `mss_consumption_case`。
- 固化 `top_bottom_spread_5d` 与消费结论。
- 强制校验 `contract_version = nc-v1`，防止错误契约被静默消费。
- 固化消费语义字段：`mss_trend_quality/mss_rank/mss_percentile` 必须可追溯。

---

## 2. run

```bash
eq mss-probe --start {start} --end {end}
```

---

## 3. test

```bash
pytest tests/unit/algorithms/mss/test_mss_probe_contract.py -q
pytest tests/unit/integration/test_mss_integration_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s1b/{start}_{end}/mss_only_probe_report.md`
- `artifacts/spiral-s1b/{start}_{end}/mss_consumption_case.md`
- `artifacts/spiral-s1b/{start}_{end}/error_manifest_sample.json`
- `artifacts/spiral-s1b/{start}_{end}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 MSS 消费字段与 `mss-data-models.md` 一致性）

---

## 5. gate / contracts / consumption

- gate:
  - 产出 `mss_only_probe_report` 且包含 `top_bottom_spread_5d`
  - 产出 `mss_consumption_case` 且包含消费字段与结论
  - 消费记录必须覆盖 `mss_trend_quality/mss_rank/mss_percentile`
  - `contract_version` 必须为 `nc-v1`，否则 `blocked`
- contracts:
  - `python -m scripts.quality.local_quality_check --contracts --governance` 必须通过
- consumption:
  - S2a 在复盘中必须记录“IRS/PAS 叠加前如何消费 S1b 结论”

---

## 6. review

- 复盘文件：`Governance/specs/spiral-s1b/review.md`
- 必填结论：
  - `mss_only_probe_report` 是否生成
  - 是否包含 `top_bottom_spread_5d`
  - MSS 输出是否被下游消费并形成结论
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 7. sync

- `Governance/specs/spiral-s1b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 8. 代码映射

- `src/algorithms/mss/probe.py`
- `src/integration/mss_consumer.py`
- `src/pipeline/main.py`

---

## 9. 失败回退

- 若探针报告缺失或消费结论不成立：状态置 `blocked`，仅修复 S1b，不推进 S2a。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S1b 验收。

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

