# S3a 执行卡（v0.2）

**状态**: Active  
**更新时间**: 2026-02-18  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3a（ENH-10 数据采集增强）

---

## 1. 目标

- 在不改变数据语义前提下，交付分批下载、断点续传、多线程能力。
- 产出并固化采集进度与恢复证据：`fetch_progress.json`。
- 形成 S3 回测准入证据：吞吐基准与失败重试链路可审计。

---

## 2. run

```bash
eq fetch-batch --start {start} --end {end} --batch-size 365 --workers 3
eq fetch-status
eq fetch-retry
```

---

## 3. test

```bash
pytest tests/unit/data/test_fetch_batch_contract.py -q
pytest tests/unit/data/test_fetch_resume_contract.py -q
pytest tests/unit/data/test_fetch_retry_contract.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3a/{trade_date}/fetch_progress.json`
- `artifacts/spiral-s3a/{trade_date}/throughput_benchmark.md`
- `artifacts/spiral-s3a/{trade_date}/fetch_retry_report.md`
- `artifacts/spiral-s3a/{trade_date}/quality_gate_report.md`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3a/review.md`
- 必填结论：
  - 中断恢复是否从 `last_success_batch_id` 续传
  - 失败批次是否被 `fetch-retry` 有效收敛
  - 多线程吞吐是否优于单线程且结论可复核

---

## 6. sync

- `Governance/specs/spiral-s3a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若进度记录损坏、断点续传失效或重试链路不可追溯：状态置 `blocked`，仅修复 S3a，不推进 S3。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S3a 验收。

---

## 8. 关联

- 执行路线：`Governance/SpiralRoadmap/SPIRAL-PRODUCTION-ROUTES.md`
- 依赖图：`Governance/SpiralRoadmap/DEPENDENCY-MAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 上位 SoT：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 9. 本轮进度（2026-02-18）

- S3a 已收口完成：真实 TuShare 适配、实测吞吐报告、失败批次真实重跑证据齐备。
- contracts/governance 门禁与全量测试均已通过，已完成向 S3 的消费衔接。
- 当前圈位已推进到 S3/S4 执行中。
