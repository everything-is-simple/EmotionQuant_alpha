# S3a Requirements（6A A1/A2）

**Spiral**: S3a  
**状态**: in_progress  
**最后更新**: 2026-02-17

## 1. A1 Align

- 主目标: 完成 ENH-10 数据采集增强闭环，支持分批下载、断点续传和失败重试。
- In Scope:
  - 实现 `eq fetch-batch --start {start} --end {end} --batch-size 365 --workers 3`
  - 实现 `eq fetch-status` 进度查询
  - 实现 `eq fetch-retry` 失败批次重试
  - 固化进度产物 `fetch_progress.json`（含 `contract_version=nc-v1`）
  - 产出吞吐对比报告 `throughput_benchmark.md`
  - 产出失败收敛报告 `fetch_retry_report.md`
- Out Scope:
  - S3 回测执行与指标归因
  - 交易执行链路（S4）
  - 调度器能力（S7a）

## 2. A2 Architect

- CP Slice: `CP-01`（1-2 个 Slice，执行增强与进度恢复）
- 跨模块契约:
  - 输入: `{start}/{end}` 交易日区间、采集源配置（由 `Config.from_env()` 注入）
  - 输出:
    - `fetch_progress.json`
    - `throughput_benchmark.md`
    - `fetch_retry_report.md`
  - 命名/契约约束:
    - `contract_version = "nc-v1"`
    - 进度字段至少包含：`total_batches/completed_batches/failed_batches/last_success_batch_id/status`
- 失败策略:
  - 进度文件损坏、主键冲突、批次不可重入判定 `P0`（阻断）
  - 单批次远端失败判定 `P1`（重试 + 记录）

## 3. A3 启动记录（2026-02-17）

- 已实现命令入口:
  - `eq fetch-batch`
  - `eq fetch-status`
  - `eq fetch-retry`
- 已落地实现:
  - `src/data/fetch_batch_pipeline.py`（分批、进度、续传、失败重试、吞吐/重试报告）
  - `src/pipeline/main.py`（S3a CLI 路由与 JSON 证据输出）
- 已新增测试:
  - `tests/unit/data/test_fetch_batch_contract.py`
  - `tests/unit/data/test_fetch_resume_contract.py`
  - `tests/unit/data/test_fetch_retry_contract.py`
  - `tests/unit/pipeline/test_cli_entrypoint.py::test_main_fetch_batch_status_and_retry`

## 4. 本圈最小证据定义

- run:
  - `eq fetch-batch --start 20250101 --end 20251231 --batch-size 365 --workers 3`
  - `eq fetch-status`
  - `eq fetch-retry`
- test:
  - `python -m pytest tests/unit/data/test_fetch_batch_contract.py -q`
  - `python -m pytest tests/unit/data/test_fetch_resume_contract.py -q`
  - `python -m pytest tests/unit/data/test_fetch_retry_contract.py -q`
  - `python -m pytest tests/unit/pipeline/test_cli_entrypoint.py::test_main_fetch_batch_status_and_retry -q`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s3a/{trade_date}/fetch_progress.json`
  - `artifacts/spiral-s3a/{trade_date}/throughput_benchmark.md`
  - `artifacts/spiral-s3a/{trade_date}/fetch_retry_report.md`
- review/final:
  - `Governance/specs/spiral-s3a/review.md`
  - `Governance/specs/spiral-s3a/final.md`
