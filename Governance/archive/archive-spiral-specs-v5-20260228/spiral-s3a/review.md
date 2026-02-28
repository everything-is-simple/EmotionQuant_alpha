# S3a Review（6A A4/A5）

**Spiral**: S3a  
**状态**: completed  
**复盘日期**: 2026-02-17

## 1. A3 交付结果

1. `TuShareFetcher` 已接入真实 TuShare 客户端适配（有 `TUSHARE_TOKEN` 时走真实链路；无 token 保持离线合同模式）。
2. `eq fetch-batch` 已从公式伪造吞吐升级为实测吞吐报告（记录 `measured_wall_seconds`、`effective_batches_per_sec`、逐批详情）。
3. `eq fetch-retry` 已从“状态直接改成功”升级为“失败批次真实重跑并写回恢复结果”。
4. 非交易日门禁已补齐：`trade_cal.is_open=0` 时不再把 `raw_daily_empty` 误判为失败。

## 2. A4 验证记录

### run

- `eq fetch-batch --start 20260101 --end 20260105 --batch-size 2 --workers 3`
- `eq fetch-status`
- `eq fetch-retry`
- `python -c "from src.config.config import Config; from src.data.fetch_batch_pipeline import run_fetch_batch, run_fetch_retry; c=Config.from_env(env_file=None); run_fetch_batch(start_date='20260101', end_date='20260110', batch_size=3, workers=3, config=c, fail_once_batch_ids={2}); run_fetch_retry(config=c)"`
- 结果：PASS（先 `partial_failed`，后 `completed`，`retried_batches=1`）

### test

- `python -m pytest -q`
- 结果：PASS（96 passed）

### contracts/governance

- `python -m scripts.quality.local_quality_check --contracts --governance`
- 结果：PASS

### 补充复验（2026-02-18，沙箱隔离环境）

- run:
  - `python -m src.pipeline.main --env-file none fetch-batch --start 20250101 --end 20260218 --batch-size 365 --workers 3`
  - `python -m src.pipeline.main --env-file none fetch-status`
  - `python -m src.pipeline.main --env-file none fetch-retry`
  - 运行时采用隔离变量：`DATA_PATH/DUCKDB_DIR/PARQUET_PATH/CACHE_PATH/LOG_PATH -> G:/EmotionQuant-alpha/.tmp/s3a-data`，`TUSHARE_TOKEN=''`
  - 结果：PASS（`status=completed`, `failed_batches=0`, `last_success_batch_id=2`）
- test:
  - `pytest tests/unit/data/test_fetch_batch_contract.py -q -p no:tmpdir -p no:cacheprovider -p pytest_safe_tmp_plugin`
  - `pytest tests/unit/data/test_fetch_resume_contract.py -q -p no:tmpdir -p no:cacheprovider -p pytest_safe_tmp_plugin`
  - `pytest tests/unit/data/test_fetch_retry_contract.py -q -p no:tmpdir -p no:cacheprovider -p pytest_safe_tmp_plugin`
  - 结果：PASS（3/3）
- contracts/governance:
  - `python -m scripts.quality.local_quality_check --contracts --governance`
  - 结果：PASS
- 说明：本次为不污染正式数据目录的隔离复验，不替代 2026-02-17 已归档的真实 TuShare 链路证据。

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s3a/requirements.md`
- artifact:
  - `artifacts/spiral-s3a/{trade_date}/fetch_progress.json`
  - `artifacts/spiral-s3a/{trade_date}/throughput_benchmark.md`
  - `artifacts/spiral-s3a/{trade_date}/fetch_retry_report.md`
- test:
  - `tests/unit/data/test_fetcher_contract.py`
  - `tests/unit/data/test_fetch_batch_contract.py`
  - `tests/unit/data/test_fetch_resume_contract.py`
  - `tests/unit/data/test_fetch_retry_contract.py`
  - `tests/unit/data/test_l1_repository_contract.py`

## 4. 偏差与风险

1. `fetch-status` 目前仍读取“最近一次任务状态”，多任务并存查询能力待后续补齐。
2. 多线程吞吐执行策略仍保持 `sequential_write_safe`，后续可在不破坏 DuckDB 写一致性的前提下扩展并发写方案。

## 5. 消费记录

- 下游消费方：S3（回测闭环）。
- 消费结论（2026-02-17）：
  - S3 继续通过 `fetch_progress.status=completed` 门禁消费 S3a 输入。
  - 门禁与桥接阻断逻辑保持有效，S3 未出现回归破坏。

## 6. 跨文档联动

- 本次未触发破坏性契约变更；暂不触发 CP 细粒度契约文档变更。
