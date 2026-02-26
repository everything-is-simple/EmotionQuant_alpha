# S0b Review（6A A4/A5）

**Spiral**: S0b  
**状态**: completed  
**复盘日期**: 2026-02-15

## 1. A3 交付结果

- `run --l1-only` 可执行，输出 L1 采集统计与门禁判定。
- Fetcher/Repository/L1 pipeline 三层最小骨架已打通。
- 合同测试覆盖重试、异常、落库、产物输出。

## 2. A4 验证记录

### run

- `C:\miniconda3\python.exe -m src.pipeline.main run --date 20260215 --source tushare --l1-only`  
  结果: PASS（`raw_daily=1`, `raw_trade_cal=1`, `raw_limit_list=1`, `status=ok`）

### test

- `C:\miniconda3\python.exe -m pytest -q tests/unit/data/test_fetcher_contract.py tests/unit/data/test_l1_repository_contract.py`  
  结果: PASS（5 passed）

### contracts/governance

- `C:\miniconda3\python.exe -m scripts.quality.local_quality_check --contracts --governance`  
  结果: PASS（contracts/behavior/governance 全通过）

### 防跑偏门禁

- `C:\miniconda3\python.exe -m pytest -q tests/unit/scripts/test_contract_behavior_regression.py tests/unit/scripts/test_governance_consistency_check.py`  
  结果: PASS（11 passed）

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s0b/requirements.md`
- raw counts: `Governance/specs/spiral-s0b/raw_counts.sample.json`
- retry report: `Governance/specs/spiral-s0b/fetch_retry_report.sample.md`
- error sample: `Governance/specs/spiral-s0b/error_manifest_sample.json`
- 关键实现:
  - `src/data/fetcher.py`
  - `src/data/repositories/base.py`
  - `src/data/l1_pipeline.py`
  - `src/pipeline/main.py`

## 4. 偏差与风险

- 偏差: 当前 run 使用模拟客户端离线数据，未接入真实远端限流与网络波动。
- 风险: 中低。真实源切换前需补一次端到端实采回归。

## 5. 消费记录

- 下游消费方: S0c。
- 消费结论: 已提供标准 L1 输入表与错误分级入口；待 S0c 执行时验证 `L1 -> L2` 读取链路。

---

## 6. 业务重验记录（2026-02-26）

- 重验窗口: 2020-01-01 ~ 2024-12-31（canary-5y）
- 代表日期: 20241220
- run: PASS（raw_daily=5373, raw_trade_cal=1 含交易日, raw_index_classify=31, status=ok）
- test: PASS（11 passed in 3.90s）
- 关键确认: 使用真实 TuShare 数据（非模拟客户端），解消首次实现时的“未接入真实远端”偏差
- gate_report: PASS（§Design-Alignment-Fields 全部对齐）
- artifact: `artifacts/spiral-s0b/20241220/`
- 结论: S0b 业务重验通过，可推进 S0c
