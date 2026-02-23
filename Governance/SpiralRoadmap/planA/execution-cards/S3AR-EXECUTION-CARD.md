# S3ar 执行卡（v0.3）

**状态**: Completed（2026-02-21 复核通过）  
**更新时间**: 2026-02-21  
**阶段**: 阶段B（S3a-S4b）  
**微圈**: S3ar（采集稳定性修复圈：双 TuShare 主备 + DuckDB 锁恢复）

---

## 完成态复核（2026-02-21）

- 复核结论：S3ar 已完成并收口，主备通道与锁恢复语义已落地。
- 证据锚点：`Governance/specs/spiral-s3ar/final.md`、`Governance/specs/spiral-s3ar/review.md`。
- 代码锚点：`src/data/fetcher.py`、`src/data/fetch_batch_pipeline.py`、`src/data/repositories/base.py`。
- 测试锚点：`tests/unit/data/test_fetcher_contract.py`、`tests/unit/data/test_fetch_retry_contract.py`、`tests/unit/data/test_duckdb_lock_recovery_contract.py`。

## 1. 目标

- 在不改变 L1-L4 合同语义前提下，收口采集链路稳定性阻断项。
- 固化通道策略：10000 网关主通道（`TUSHARE_PRIMARY_*`）+ 5000 官方兜底通道（`TUSHARE_FALLBACK_*`）。
- 落地主/兜底独立限速口径（全局 + 通道级）。
- 落地 DuckDB 锁冲突恢复门禁（等待/重试/锁持有者记录/幂等写入）。
- AKShare/BaoStock 仅登记为后续底牌路线，不在本圈实装。

---

## 2. run

```bash
eq fetch-batch --start {start} --end {end} --batch-size 365 --workers 3
eq fetch-status
eq fetch-retry
python scripts/data/check_tushare_l1_token.py --token-env TUSHARE_PRIMARY_TOKEN --http-url http://106.54.191.157:5000
python scripts/data/check_tushare_l1_token.py --token-env TUSHARE_FALLBACK_TOKEN
python scripts/data/benchmark_tushare_l1_rate.py --token-env TUSHARE_PRIMARY_TOKEN --http-url http://106.54.191.157:5000 --api daily --calls 500 --workers 50
python scripts/data/benchmark_tushare_l1_rate.py --token-env TUSHARE_FALLBACK_TOKEN --api daily --calls 500 --workers 50
```

---

## 3. test

```bash
pytest tests/unit/data/test_fetcher_contract.py -q
pytest tests/unit/data/test_fetch_retry_contract.py -q
pytest tests/unit/config/test_config_defaults.py -q
```

---

## 4. artifact

- `artifacts/spiral-s3a/{trade_date}/fetch_progress.json`
- `artifacts/spiral-s3a/{trade_date}/fetch_retry_report.md`
- `artifacts/spiral-s3a/{trade_date}/throughput_benchmark.md`
- `artifacts/token-checks/tushare_l1_token_check_*.json`
- `artifacts/token-checks/tushare_l1_rate_benchmark_*.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s3ar/review.md`
- 必填结论：
  - 主通道失败时是否自动切换到兜底通道。
  - 主/兜底独立限速是否生效并可解释。
  - DuckDB 锁冲突是否可恢复；不可恢复是否具备可审计失败证据。
  - 重试是否保持幂等（无重复写入）。
  - AKShare/BaoStock 是否已登记为下一圈底牌计划。

---

## 6. sync

- `Governance/specs/spiral-s3ar/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若主备通道切换不可审计或独立限速失效：状态置 `blocked`，仅修复 S3ar，不推进 S3b。
- 若锁恢复门禁失效或出现重复写入：状态置 `blocked`，回退到采集链路修复子步，不允许进入归因圈。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`
- 上位 SoT：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- 通道策略：`docs/reference/tushare/tushare-channel-policy.md`

---

## 9. 本轮进度（2026-02-19）

- 已完成口径修订：S3ar 当前聚焦“双 TuShare 主备 + 锁恢复”，AKShare/BaoStock 转为路线图预留。
- 本卡作为 S3ar 收口合同，后续实现需严格按本卡 run/test/artifact/review/sync 执行。
