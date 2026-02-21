# S3d 执行卡（v0.1）

**状态**: Planned  
**更新时间**: 2026-02-20  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3d（MSS 自适应校准闭环）

---

## 0. 现状对齐（2026-02-21）

- 本卡为计划圈，尚未进入执行态。
- 进入执行前必须先补齐 CLI 能力：`eq mss --threshold-mode` 与 `eq mss-probe --return-series-source` 参数契约。
- 以上能力未落地前，S3d 不得标记 `in_progress/completed`。

## 1. 目标

- 落地 MSS `adaptive` 阈值模式（`T30/T45/T60/T75` + 冷启动回退）。
- 升级趋势判定到 `EMA + slope + trend_band` 抗抖口径。
- 将 MSS probe 从“温度差代理”切换为“真实收益序列”。

---

## 2. run

```bash
eq mss --date {trade_date} --threshold-mode adaptive
eq mss-probe --start {start} --end {end} --return-series-source future_returns
```

---

## 3. test

```bash
pytest tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py -q
pytest tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3d/{trade_date}/mss_regime_thresholds_snapshot.json`
- `artifacts/spiral-s3d/{trade_date}/mss_probe_return_series_report.md`
- `artifacts/spiral-s3d/{trade_date}/mss_adaptive_regression.md`
- `artifacts/spiral-s3d/{trade_date}/consumption.md`
- `artifacts/spiral-s3d/{trade_date}/gate_report.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3d/review.md`
- 必填结论：
  - adaptive 阈值与冷启动回退是否按设计生效
  - 趋势抗抖是否替代旧三点单调口径
  - probe 是否已基于真实收益序列

---

## 6. sync

- `Governance/specs/spiral-s3d/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若 adaptive/probe 任一门禁未通过：状态置 `blocked`，留在 S3d 修复，不推进 S3e。
- 若定位到上游行业语义输入缺陷：回退 S3c 修复后重验。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
