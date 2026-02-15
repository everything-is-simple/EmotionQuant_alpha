# S1b 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S1b（MSS 消费验证）

---

## 1. 目标

- 打通 MSS 输出消费验证闭环（非只算分）。
- 产出 `mss_only_probe_report` 与 `mss_consumption_case`。
- 固化 `top_bottom_spread_5d` 与消费结论。

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

- `artifacts/spiral-s1b/{end}/mss_only_probe_report.md`
- `artifacts/spiral-s1b/{end}/mss_consumption_case.md`
- `artifacts/spiral-s1b/{end}/error_manifest_sample.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s1b/review.md`
- 必填结论：
  - `mss_only_probe_report` 是否生成
  - 是否包含 `top_bottom_spread_5d`
  - MSS 输出是否被下游消费并形成结论

---

## 6. sync

- `Governance/specs/spiral-s1b/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若探针报告缺失或消费结论不成立：状态置 `blocked`，仅修复 S1b，不推进 S2a。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S1b 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
