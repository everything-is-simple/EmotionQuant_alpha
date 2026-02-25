# 数据脚本说明（scripts/data）

本目录按“一个用途一个工具”整理后，仅保留以下脚本：

1. `bulk_download.py`
用途：高速历史补采（主工具，持久 DuckDB 连接 + 断点续传）

2. `run_l1_fetch.ps1`
用途：`bulk_download.py` 的 PowerShell 运行入口（前台/后台、状态查看、重试）

3. `run_l1_fetch_monthly.ps1`
用途：按月分段执行补采（带月度超时和重试）

4. `check_tushare_dual_tokens.py`
用途：一次检查主/备 Token 在 L1 八接口上的可用性

5. `benchmark_tushare_l1_channels_window.py`
用途：对主/备通道做窗口级性能基准测试（真实 L1 接口口径）

## 常用命令

```powershell
# 1) 直接批量补采（推荐）
python scripts/data/bulk_download.py --start 20250101 --end 20260224 --skip-existing

# 2) PowerShell 入口（前台）
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -Start 20250101 -End 20260224 -BatchSize 10 -RetryMax 3 -SkipExisting

# 3) PowerShell 入口（后台）
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -Start 20250101 -End 20260224 -Background -SkipExisting

# 4) 查看状态 / 查看后台进程 / 停止后台进程
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StatusOnly
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -RunnerStatus
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StopRunner

# 5) 按月补采
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch_monthly.ps1 `
  -Start 20250101 -End 20260224 -RetryMax 2 -MaxMonthMinutes 20

# 6) 检查双 Token 可用性
python scripts/data/check_tushare_dual_tokens.py --env-file .env --channels both

# 7) 基准测试（窗口口径）
python scripts/data/benchmark_tushare_l1_channels_window.py `
  --env-file .env --start 20250101 --end 20250131 --channels both
```

## 备注

- 所有路径和密钥均通过 `Config.from_env()` / `.env` 注入，不在脚本中硬编码。
- `bulk_download.py` 会把进度写入 `artifacts/bulk_download_progress.json`，用于断点续传和状态查看。
- 批量补采阶段默认不执行 Quality Gate；单日质量验证可在补采后单独执行。
