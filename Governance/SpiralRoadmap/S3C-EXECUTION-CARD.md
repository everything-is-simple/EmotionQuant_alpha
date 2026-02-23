# S3c 执行卡（v0.1）

**状态**: Completed  
**更新时间**: 2026-02-21  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3c（行业语义校准闭环）

---

## 1. 目标

- 完成 `industry_snapshot` 从 `ALL` 聚合到 SW31 行业映射的主流程切换。
- 固化 IRS 31 行业全覆盖门禁与 `allocation_advice` 覆盖性检查。
- 形成行业映射审计证据，为 S3d/S3e 提供稳定输入。

---

## 2. run

```bash
eq run --date {trade_date} --to-l2 --strict-sw31
eq irs --date {trade_date} --require-sw31
```

---

## 3. test

```bash
pytest tests/unit/data/test_industry_snapshot_sw31_contract.py -q
pytest tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3c/{trade_date}/industry_snapshot_sw31_sample.parquet`
- `artifacts/spiral-s3c/{trade_date}/irs_allocation_coverage_report.md`
- `artifacts/spiral-s3c/{trade_date}/sw_mapping_audit.md`
- `artifacts/spiral-s3c/{trade_date}/consumption.md`
- `artifacts/spiral-s3c/{trade_date}/gate_report.md`

---

## 4.1 本轮执行证据（2026-02-21）

- 实跑窗口：`trade_date=20260219`
- Run 结果：
  - `eq run --date 20260219 --to-l2 --strict-sw31` => `industry_snapshot_count=31`
  - `eq irs --date 20260219 --require-sw31` => `irs_industry_count=31`, `gate_status=PASS`, `go_nogo=GO`
- Test 结果：
  - `python -m pytest tests/unit/data/test_industry_snapshot_sw31_contract.py -q` 通过
  - `python -m pytest tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py -q` 通过
  - `python -m pytest tests/unit/pipeline/test_cli_entrypoint.py::test_main_irs_command_wires_to_pipeline -q` 通过
- 说明：
  - 已补齐 `S3c gate_report/consumption` 产物契约落地（由 `eq irs --require-sw31` 输出）。
  - `S3c` 当前维持 `Active`，待与 `S3b` 固定窗口收口节奏对齐后再切 `Completed`。

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3c/review.md`
- 必填结论：
  - SW31 行业映射是否完整可复核
  - 是否仍存在 `industry_code=ALL` 主流程输入
  - IRS 配置建议是否实现 31 行业全覆盖

---

## 6. sync

- `Governance/specs/spiral-s3c/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 SW31 覆盖未通过：状态置 `blocked`，留在 S3c 修复，不推进 S3d。
- 若定位到 L1 行业映射输入异常：回退数据层修复后重验。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
