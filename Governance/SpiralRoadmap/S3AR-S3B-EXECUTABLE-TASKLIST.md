# S3ar/S3b 可执行任务清单（四列表）

**状态**: S3ar Completed / S3b Completed  
**更新时间**: 2026-02-25  
**用途**: 将 `debt-clearance-plan-v1.md` 拆解为可直接执行的任务单（文件 / 命令 / 测试 / 产物）

---

## S3ar（采集稳定性修复圈）

| 文件 | 命令 | 测试 | 产物 |
|---|---|---|---|
| `src/data/fetcher.py` `src/data/fetch_batch_pipeline.py` `src/config/config.py` | `eq fetch-batch --start {start} --end {end} --batch-size 365 --workers 3` | `pytest tests/unit/data/test_fetcher_contract.py -q` `pytest tests/unit/data/test_fetch_batch_contract.py -q` `pytest tests/unit/config/test_config_defaults.py -q` | `artifacts/spiral-s3a/{trade_date}/fetch_progress.json` |
| `scripts/data/check_tushare_l1_token.py` `scripts/data/benchmark_tushare_l1_rate.py` | `python scripts/data/check_tushare_l1_token.py --token-env TUSHARE_PRIMARY_TOKEN --http-url http://106.54.191.157:5000` `python scripts/data/check_tushare_l1_token.py --token-env TUSHARE_FALLBACK_TOKEN` `python scripts/data/benchmark_tushare_l1_rate.py --token-env TUSHARE_PRIMARY_TOKEN --http-url http://106.54.191.157:5000 --api daily --calls 500 --workers 50` `python scripts/data/benchmark_tushare_l1_rate.py --token-env TUSHARE_FALLBACK_TOKEN --api daily --calls 500 --workers 50` | `pytest tests/unit/data/test_fetch_retry_contract.py -q` | `artifacts/token-checks/tushare_l1_token_check_*.json` `artifacts/token-checks/tushare_l1_rate_benchmark_*.json` |
| `src/data/fetch_batch_pipeline.py` `src/data/l1_pipeline.py` | `eq fetch-retry` `eq fetch-status` | `pytest tests/unit/data/test_fetch_resume_contract.py -q` | `artifacts/spiral-s3a/{trade_date}/fetch_retry_report.md` `artifacts/spiral-s3a/{trade_date}/throughput_benchmark.md` |
| `Governance/specs/spiral-s3ar/final.md` `Governance/specs/spiral-s3ar/review.md` | `python -m scripts.quality.local_quality_check --contracts --governance` | `pytest tests/unit/scripts/test_governance_consistency_check.py -q` | `Governance/specs/spiral-s3ar/final.md` `Governance/specs/spiral-s3ar/review.md` |

### S3ar 完成判定

1. 主通道失败可自动切到兜底通道，且日志可审计。
2. DuckDB 锁冲突可恢复，或失败时有完整证据链（等待时长/重试次数/错误信息）。
3. 重试过程不产生重复写入（幂等成立）。

---

## S3b（收益归因验证圈）

| 文件 | 命令 | 测试 | 产物 |
|---|---|---|---|
| `src/pipeline/main.py`（analysis 子命令） `src/analysis/pipeline.py` | `eq analysis --start {start} --end {end} --ab-benchmark` | `pytest tests/unit/pipeline/test_cli_entrypoint.py -q`（analysis 分支） | `artifacts/spiral-s3b/{trade_date}/consumption.md` |
| `src/analysis/pipeline.py` `src/backtest/pipeline.py` `src/trading/pipeline.py` | `eq analysis --date {trade_date} --deviation live-backtest` | `pytest tests/unit/analysis/test_ab_benchmark_contract.py -q`（新增） `pytest tests/unit/analysis/test_live_backtest_deviation_contract.py -q`（新增） | `artifacts/spiral-s3b/{trade_date}/ab_benchmark_report.md` `artifacts/spiral-s3b/{trade_date}/live_backtest_deviation_report.md` |
| `src/analysis/pipeline.py` | `eq analysis --date {trade_date} --attribution-summary` | `pytest tests/unit/analysis/test_attribution_summary_contract.py -q`（新增） | `artifacts/spiral-s3b/{trade_date}/attribution_summary.json` `artifacts/spiral-s3b/{trade_date}/gate_report.md` |
| `Governance/specs/spiral-s3b/final.md` `Governance/specs/spiral-s3b/review.md` | `python -m scripts.quality.local_quality_check --contracts --governance` | `pytest tests/unit/scripts/test_contract_behavior_regression.py -q` | `Governance/specs/spiral-s3b/final.md` `Governance/specs/spiral-s3b/review.md` |

### S3b 完成判定

1. A/B/C 对照齐备，且三分解（signal/execution/cost）齐备。
2. 归因结果可追溯到 S3/S4 真实产物，不允许“仅回测口径推断”。
3. 结论可驱动 S4b 参数，不可复核则停留在 S3b。

---

## 同步清单（每圈固定）

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`
