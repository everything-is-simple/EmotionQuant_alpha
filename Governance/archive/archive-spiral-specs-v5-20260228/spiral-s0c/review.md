# S0c Review（6A A4/A5）

**Spiral**: S0c  
**状态**: completed  
**复盘日期**: 2026-02-21

## 1. A3 交付结果

- `run --to-l2` 路径已落地，支持从 L1 表生成 L2 快照。
- 新增 `src/data/l2_pipeline.py`，包含 gate 校验、错误分级、canary 产物。
- 新增 S0c 合同测试：
  - `tests/unit/data/test_snapshot_contract.py`
  - `tests/unit/data/test_s0_canary.py`

## 2. A4 验证记录

### run

- `C:\miniconda3\python.exe -m src.pipeline.main run --date 20260215 --source tushare --to-l2`  
  结果: PASS（`market_snapshot_count=1`, `industry_snapshot_count=1`, `status=ok`）

### test

- `C:\miniconda3\python.exe -m pytest -q tests/unit/data/models/test_snapshots.py tests/unit/data/test_snapshot_contract.py tests/unit/data/test_s0_canary.py`  
  结果: PASS（5 passed）

### contracts/governance

- `C:\miniconda3\python.exe -m scripts.quality.local_quality_check --contracts --governance`  
  结果: PASS（contracts/behavior/governance 全通过）

### 防跑偏门禁

- `C:\miniconda3\python.exe -m pytest -q tests/unit/scripts/test_contract_behavior_regression.py tests/unit/scripts/test_governance_consistency_check.py`  
  结果: PASS（11 passed）

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s0c/requirements.md`
- market snapshot 样例: `Governance/specs/spiral-s0c/market_snapshot_sample.parquet`
- industry snapshot 样例: `Governance/specs/spiral-s0c/industry_snapshot_sample.parquet`
- canary 报告: `Governance/specs/spiral-s0c/s0_canary_report.md`
- error sample: `Governance/specs/spiral-s0c/error_manifest_sample.json`
- 核心实现:
  - `src/data/l2_pipeline.py`
  - `src/pipeline/main.py`

## 4. 偏差与风险

- 偏差: S0c 当前行业快照采用“全市场聚合”最小实现，尚未接入 SW 行业真实聚合口径。
- 风险: 中。S1a 前可用，但 S1b/S2 前需补真实行业映射与覆盖回归。

## 5. 消费记录

- 下游消费方: S1a（MSS）。
- 消费结论: `market_snapshot` 已包含 `data_quality/stale_days/source_trade_date`，可作为 MSS 最小输入。

## 6. 跨文档联动

- 本圈未引入命名契约破坏性变更，不触发 `docs/naming-contracts.schema.json` 与 CP 文档强制联动。

## 7. S0c-R1 收口补记（2026-02-21）

### A3 交付补充

- 修复 S0c 门禁语义漂移：在 DuckDB 文件缺失场景恢复 `duckdb_not_found` 错误语义，同时保留 `data_readiness_gate` 持久化。
- 升级离线模拟 SW31 数据：`index_classify/index_member` 提供 31 行业映射，支持 `strict_sw31` 默认门禁回归。
- 新增合同测试：
  - `tests/unit/data/test_data_readiness_persistence_contract.py`
  - `tests/unit/data/test_flat_threshold_config_contract.py`

### A4 验证补充

- run:
  - `$env:TUSHARE_TOKEN=''; $env:TUSHARE_PRIMARY_TOKEN=''; $env:TUSHARE_FALLBACK_TOKEN=''; python -m src.pipeline.main --env-file artifacts/spiral-s0c/20260215/.env.s0c.hardening run --date 20260215 --source tushare --l1-only`
  - `$env:TUSHARE_TOKEN=''; $env:TUSHARE_PRIMARY_TOKEN=''; $env:TUSHARE_FALLBACK_TOKEN=''; python -m src.pipeline.main --env-file artifacts/spiral-s0c/20260215/.env.s0c.hardening run --date 20260215 --source tushare --to-l2 --strict-sw31`
  - 结果: PASS（`industry_snapshot_count=31`，`status=ok`）
- test:
  - `pytest -q tests/unit/data/test_s0_canary.py tests/unit/data/test_snapshot_contract.py tests/unit/data/test_industry_snapshot_sw31_contract.py tests/unit/data/test_data_readiness_persistence_contract.py tests/unit/data/test_flat_threshold_config_contract.py tests/unit/data/test_quality_gate.py tests/unit/data/test_fetcher_contract.py`
  - 结果: PASS（18 passed）
- contracts/governance:
  - `python -m scripts.quality.local_quality_check --contracts --governance`
  - 结果: PASS（contracts/behavior/traceability/governance 全通过）

### A5 证据链补充

- `Governance/specs/spiral-s0c/l2_quality_gate_report.md`
- `Governance/specs/spiral-s0c/sw_mapping_audit.md`
- `Governance/specs/spiral-s0c/industry_snapshot_sw31_sample.parquet`

### 复盘结论

- S0c v0.2 门禁与测试契约已收敛；`strict_sw31 + data_readiness + flat_threshold` 三项已形成可复核证据链。
