# Spiral S3ar Requirements

## 主目标
- 收口采集稳定性阻断项：多源兜底（TuShare -> AKShare -> BaoStock）与 DuckDB 文件锁恢复。

## In Scope
- L1 八类接口读取链路保持不变，新增数据源降级策略与错误分类。
- DuckDB 锁等待、重试、锁持有者记录。
- 失败批次重试幂等写入校验。

## Out Scope
- S3b 归因算法实现。
- GUI 与自动调度。

## 验收门禁
1. 可执行：`eq fetch-batch` + `eq fetch-retry`。
2. 自动化：新增 fallback/lock recovery 契约测试通过。
3. 产物：`fetch_progress.json`、`fetch_retry_report.md`、`source_failover_report.md`。
