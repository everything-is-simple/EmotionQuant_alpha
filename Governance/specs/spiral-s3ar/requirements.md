# Spiral S3ar Requirements

## 主目标
- 收口采集稳定性阻断项：双 TuShare 主备（10000 网关主 + 5000 官方兜底）与 DuckDB 文件锁恢复。
- 明确 AKShare/BaoStock 仅作为最后底牌路线图预留，本圈不实装。

## In Scope
- L1 八类接口读取链路保持不变，新增主备通道降级策略与错误分类。
- 主/兜底独立限速配置（全局+通道级）落地与验证。
- DuckDB 锁等待、重试、锁持有者记录。
- 失败批次重试幂等写入校验。

## Out Scope
- S3b 归因算法实现。
- GUI 与自动调度。

## 验收门禁
1. 可执行：`eq fetch-batch` + `eq fetch-retry`。
2. 自动化：`test_fetcher_contract` + `test_fetch_retry_contract` + `test_config_defaults` 通过。
3. 产物：`fetch_progress.json`、`fetch_retry_report.md`、`throughput_benchmark.md`、`tushare_l1_rate_benchmark_*.json`。
