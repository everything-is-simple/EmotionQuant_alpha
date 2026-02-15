# S1a 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S1a（MSS 最小评分）

---

## 1. 目标

- 产出 `mss_panorama` 当日评分结果。
- 确保核心字段 `mss_score/mss_temperature/mss_cycle` 可追溯。
- 形成 MSS 因子轨迹证据。

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
```

---

## 4. artifact

- `artifacts/spiral-s1a/{trade_date}/mss_panorama_sample.parquet`
- `artifacts/spiral-s1a/{trade_date}/mss_factor_trace.md`
- `artifacts/spiral-s1a/{trade_date}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s1a/review.md`
- 必填结论：
  - `mss_panorama` 当日记录是否 `> 0`
  - 核心字段是否齐全
  - 因子轨迹是否可复核

---

## 6. sync

- `Governance/specs/spiral-s1a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若评分结果为空或字段缺失：状态置 `blocked`，仅修复 S1a，不推进 S1b。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S1a 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
