# S0c Requirements（6A A1/A2）

**Spiral**: S0c  
**状态**: completed  
**最后更新**: 2026-02-15

## 1. A1 Align

- 主目标: 完成 L1 -> L2 快照生成与失败分级最小闭环。
- In Scope:
  - `eq run --date {trade_date} --source tushare --to-l2` 可执行
  - 从 L1 (`raw_daily`, `raw_limit_list`) 生成 L2 (`market_snapshot`, `industry_snapshot`)
  - 输出 `s0_canary_report.md` 与分级错误清单（含 `error_level`）
  - 补齐 `tests/unit/data/test_snapshot_contract.py` 与 `tests/unit/data/test_s0_canary.py`
- Out Scope:
  - MSS/IRS/PAS 计算
  - 真实远端采集增强（断点续传/并发）

## 2. A2 Architect

- CP Slice: `CP-01`（1 个 Slice）
- 跨模块契约:
  - 输入: L1 DuckDB 表 `raw_daily` 与 `raw_limit_list`
  - 输出: L2 DuckDB 表 `market_snapshot` 与 `industry_snapshot`
  - 质量字段: `data_quality/stale_days/source_trade_date` 必须存在
  - 失败分级: `error_manifest.json` 条目必须包含 `error_level`
- 失败策略:
  - L1 缺失或当日空数据判定 `P0` 并阻断收口
  - 字段缺失判定 `P1` 并阻断收口

## 3. 本圈最小证据定义

- run:
  - `C:\miniconda3\python.exe -m src.pipeline.main run --date 20260215 --source tushare --to-l2`
- test:
  - `C:\miniconda3\python.exe -m pytest -q tests/unit/data/test_snapshot_contract.py tests/unit/data/test_s0_canary.py`
- artifact:
  - `Governance/specs/spiral-s0c/market_snapshot_sample.parquet`
  - `Governance/specs/spiral-s0c/industry_snapshot_sample.parquet`
  - `Governance/specs/spiral-s0c/s0_canary_report.md`
- review/final:
  - `Governance/specs/spiral-s0c/review.md`
  - `Governance/specs/spiral-s0c/final.md`

