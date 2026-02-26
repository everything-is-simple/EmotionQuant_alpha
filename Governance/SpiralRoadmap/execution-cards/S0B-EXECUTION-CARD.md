# S0b 执行卡（v0.3）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S0b（L1 采集入库）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，L1 入库与数据门禁持久化满足实战可审计要求。
- 证据锚点：`src/data/l1_pipeline.py`、`src/data/quality_store.py`、`tests/unit/data/test_fetcher_contract.py`、`tests/unit/data/test_l1_repository_contract.py`、`tests/unit/data/test_data_readiness_persistence_contract.py`。
- 关键确认：`system_config/data_quality_report/data_readiness_gate` 已稳定落库并可被后续微圈消费。

---

## 1. 目标

- 打通 L1 原始数据采集与入库闭环。
- 保障 `raw_daily` 与 `raw_trade_cal` 当日可复核。
- 失败链路产出 `error_manifest.json`。
- 落地数据门禁元数据持久化：`system_config`、`data_quality_report`、`data_readiness_gate`。
- 保证 S2 桥接所需基础快照可用：`raw_index_member`、`raw_index_classify`、`raw_stock_basic`。

---

## 2. run

```bash
eq run --date {trade_date} --source tushare --l1-only
```

---

## 3. test

```bash
pytest tests/unit/data/test_fetcher_contract.py -q
pytest tests/unit/data/test_l1_repository_contract.py -q
pytest tests/unit/data/test_data_readiness_persistence_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s0b/{trade_date}/raw_counts.json`
- `artifacts/spiral-s0b/{trade_date}/fetch_retry_report.md`
- `artifacts/spiral-s0b/{trade_date}/error_manifest_sample.json`
- `artifacts/spiral-s0b/{trade_date}/l1_quality_gate_report.md`
- `artifacts/spiral-s0b/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `raw_daily/raw_trade_cal/data_readiness_gate` 与 `data-layer-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s0b/review.md`
- 必填结论：
  - `raw_daily` 是否 `> 0`
  - `raw_trade_cal` 是否包含 `{trade_date}`
  - `raw_index_member/raw_index_classify/raw_stock_basic` 是否可被后续圈消费
  - `data_readiness_gate` 是否落库且状态可复核（ready/degraded/blocked）
  - `data_quality_report` 是否记录覆盖率与动作（continue/block/fallback）
  - 失败链路是否输出 `error_manifest`
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s0b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若 `raw_daily` 为空或交易日缺失：状态置 `blocked`，仅修复 S0b，不推进 S0c。
- 若 `data_readiness_gate.status=blocked`：状态置 `blocked`，仅修复 S0b，不推进 S0c。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S0b 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`

---

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

