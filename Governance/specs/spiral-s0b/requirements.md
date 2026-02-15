# S0b Requirements（6A A1/A2）

**Spiral**: S0b  
**状态**: completed  
**最后更新**: 2026-02-15

## 1. A1 Align

- 主目标: 完成 L1 原始数据采集与入库闭环。
- In Scope:
  - `run --l1-only` 触发 L1 采集编排
  - `raw_daily/raw_trade_cal/raw_limit_list` 入 DuckDB + Parquet
  - 失败输出 `error_manifest.json`，成功至少输出 sample manifest
  - 合同测试 `test_fetcher_contract.py` 与 `test_l1_repository_contract.py`
- Out Scope:
  - L2 快照构建
  - MSS/IRS/PAS 计算

## 2. A2 Architect

- CP Slice: `CP-01`（1 个 Slice）
- 跨模块契约:
  - Fetcher 负责重试与错误归因
  - Repository 负责落库与落盘
  - Pipeline 负责 gate 判定与产物组织
- 门禁:
  - `raw_daily > 0`
  - `raw_trade_cal` 含 `trade_date`
  - 异常必须可追溯到 `error_manifest`

## 3. 本圈最小证据定义

- run:
  - `C:\miniconda3\python.exe -m src.pipeline.main run --date 20260215 --source tushare --l1-only`
- test:
  - `C:\miniconda3\python.exe -m pytest -q tests/unit/data/test_fetcher_contract.py tests/unit/data/test_l1_repository_contract.py`
- artifact:
  - `Governance/specs/spiral-s0b/raw_counts.sample.json`
  - `Governance/specs/spiral-s0b/fetch_retry_report.sample.md`
  - `Governance/specs/spiral-s0b/error_manifest_sample.json`
- review/final:
  - `Governance/specs/spiral-s0b/review.md`
  - `Governance/specs/spiral-s0b/final.md`
