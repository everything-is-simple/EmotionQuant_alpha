# S2a 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S2a（IRS + PAS + Validation）

---

## 1. 目标

- 打通 `IRS + PAS + Validation` 最小闭环。
- 产出并落库 `irs_industry_daily`、`stock_pas_daily`、`validation_gate_decision`。
- 固化 `contract_version = "nc-v1"` 与 FAIL 处方语义。

---

## 2. run

```bash
eq recommend --date {trade_date} --mode mss_irs_pas --with-validation
```

---

## 3. test

```bash
pytest tests/unit/algorithms/irs/test_irs_contract.py -q
pytest tests/unit/algorithms/pas/test_pas_contract.py -q
pytest tests/unit/integration/test_validation_gate_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s2a/{trade_date}/irs_industry_daily_sample.parquet`
- `artifacts/spiral-s2a/{trade_date}/stock_pas_daily_sample.parquet`
- `artifacts/spiral-s2a/{trade_date}/validation_gate_decision_sample.parquet`
- `artifacts/spiral-s2a/{trade_date}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s2a/review.md`
- 必填结论：
  - 三张输出表当日是否都 `> 0`
  - `validation_gate_decision.contract_version` 是否为 `nc-v1`
  - FAIL 场景是否包含 `validation_prescription`

---

## 6. sync

- `Governance/specs/spiral-s2a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若任一输出缺失或契约不兼容：状态置 `blocked`，仅修复 S2a，不推进 S2b。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S2a 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
