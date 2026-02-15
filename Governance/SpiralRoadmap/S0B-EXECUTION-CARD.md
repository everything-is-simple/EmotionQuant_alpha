# S0b 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S0b（L1 采集入库）

---

## 1. 目标

- 打通 L1 原始数据采集与入库闭环。
- 保障 `raw_daily` 与 `raw_trade_cal` 当日可复核。
- 失败链路产出 `error_manifest.json`。

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
```

---

## 4. artifact

- `artifacts/spiral-s0b/{trade_date}/raw_counts.json`
- `artifacts/spiral-s0b/{trade_date}/fetch_retry_report.md`
- `artifacts/spiral-s0b/{trade_date}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s0b/review.md`
- 必填结论：
  - `raw_daily` 是否 `> 0`
  - `raw_trade_cal` 是否包含 `{trade_date}`
  - 失败链路是否输出 `error_manifest`

---

## 6. sync

- `Governance/specs/spiral-s0b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 `raw_daily` 为空或交易日缺失：状态置 `blocked`，仅修复 S0b，不推进 S0c。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S0b 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
