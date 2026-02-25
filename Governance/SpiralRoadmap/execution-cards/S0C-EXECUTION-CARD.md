# S0c 执行卡（v0.3）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S0c（L2 快照与错误分级）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，L2 快照、SW31 严格门禁与错误分级满足实战口径。
- 证据锚点：`src/data/l2_pipeline.py`、`tests/unit/data/test_snapshot_contract.py`、`tests/unit/data/test_industry_snapshot_sw31_contract.py`、`tests/unit/data/test_flat_threshold_config_contract.py`。
- 关键确认：`flat_threshold` 与 SW31 规则执行一致，S2 所需行业映射链路可审计。

---

## 1. 目标

- 生成 L2 快照：`market_snapshot` 与 `industry_snapshot`。
- 确保质量字段 `data_quality/stale_days/source_trade_date` 可追溯。
- 默认执行严格 SW31 门禁（31 行业覆盖，禁止 `industry_code=ALL` 回退）。
- `flat_count` 口径对齐 `flat_threshold`（单位 `%`，来自 `system_config`）。
- 失败链路带 `error_level` 分级。
- 形成可供 S2 集成层消费的行业映射链路证据（成员表 + 分类表 + 快照一致性）。

---

## 2. run

```bash
eq run --date {trade_date} --source tushare --to-l2 --strict-sw31
```

---

## 3. test

```bash
pytest tests/unit/data/test_snapshot_contract.py -q
pytest tests/unit/data/test_s0_canary.py -q
pytest tests/unit/data/test_industry_snapshot_sw31_contract.py -q
pytest tests/unit/data/test_data_readiness_persistence_contract.py -q
pytest tests/unit/data/test_flat_threshold_config_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s0c/{trade_date}/market_snapshot_sample.parquet`
- `artifacts/spiral-s0c/{trade_date}/industry_snapshot_sample.parquet`
- `artifacts/spiral-s0c/{trade_date}/s0_canary_report.md`
- `artifacts/spiral-s0c/{trade_date}/error_manifest_sample.json`
- `artifacts/spiral-s0c/{trade_date}/sw_mapping_audit.md`
- `artifacts/spiral-s0c/{trade_date}/l2_quality_gate_report.md`
- `artifacts/spiral-s0c/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `market_snapshot/industry_snapshot` 与 `data-layer-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s0c/review.md`
- 必填结论：
  - `market_snapshot` 当日是否存在
  - `industry_snapshot` 是否为 SW31 31 行业且不含 `ALL`
  - 行业映射审计（`sw_mapping_audit`）是否可支持 S2 `stock -> industry` 桥接
  - `flat_count` 是否按 `flat_threshold` 计算
  - 质量字段是否齐全
  - `data_readiness_gate` 是否落库并与 gate 结论一致
  - 错误分级是否可追溯
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s0c/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若快照缺失或质量字段不全：状态置 `blocked`，仅修复 S0c，不推进 S1a。
- 若 SW31 门禁不通过（行业数!=31 或包含 `ALL`）：状态置 `blocked`，仅修复 S0c，不推进 S1a。
- 若 `data_readiness_gate.status=blocked`：状态置 `blocked`，仅修复 S0c，不推进 S1a。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S0c 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`




