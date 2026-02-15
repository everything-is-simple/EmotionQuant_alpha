# S0c 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S0c（L2 快照与错误分级）

---

## 1. 目标

- 生成 L2 快照：`market_snapshot` 与 `industry_snapshot`。
- 确保质量字段 `data_quality/stale_days/source_trade_date` 可追溯。
- 失败链路带 `error_level` 分级。

---

## 2. run

```bash
eq run --date {trade_date} --source tushare --to-l2
```

---

## 3. test

```bash
pytest tests/unit/data/test_snapshot_contract.py -q
pytest tests/unit/data/test_s0_canary.py -q
```

---

## 4. artifact

- `artifacts/spiral-s0c/{trade_date}/market_snapshot_sample.parquet`
- `artifacts/spiral-s0c/{trade_date}/industry_snapshot_sample.parquet`
- `artifacts/spiral-s0c/{trade_date}/s0_canary_report.md`
- `artifacts/spiral-s0c/{trade_date}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s0c/review.md`
- 必填结论：
  - `market_snapshot` 当日是否存在
  - 质量字段是否齐全
  - 错误分级是否可追溯

---

## 6. sync

- `Governance/specs/spiral-s0c/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若快照缺失或质量字段不全：状态置 `blocked`，仅修复 S0c，不推进 S1a。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S0c 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
