# L1 Fetch Tool

Use `scripts/data/run_l1_fetch.ps1` to run L1 backfill locally with visible progress and retry loops.

## Commands

```powershell
# One command entry (default full range: 20100101..today, default background)
powershell -ExecutionPolicy Bypass -File scripts/data/start_l1_full_fetch.ps1

# Foreground mode (stay in current terminal)
powershell -ExecutionPolicy Bypass -File scripts/data/start_l1_full_fetch.ps1 -Foreground

# Custom range / params
powershell -ExecutionPolicy Bypass -File scripts/data/start_l1_full_fetch.ps1 `
  -Start 20100101 -End 20260219 -BatchSize 365 -Workers 3 -RetryMax 10

# Wrapper pass-through status/runner controls
powershell -ExecutionPolicy Bypass -File scripts/data/start_l1_full_fetch.ps1 -StatusOnly
powershell -ExecutionPolicy Bypass -File scripts/data/start_l1_full_fetch.ps1 -RunnerStatus
powershell -ExecutionPolicy Bypass -File scripts/data/start_l1_full_fetch.ps1 -StopRunner

# Check TuShare token for required 8 L1 APIs (primary token by default)
python scripts/data/check_tushare_l1_token.py

# Check with explicit token source file
python scripts/data/check_tushare_l1_token.py `
  --token-file docs/reference/tushare/tushare-config-5000积分-官方-兜底号.md

# Check with gateway settings (for 10000 trial gateway)
python scripts/data/check_tushare_l1_token.py `
  --token-file docs/reference/tushare/tushare-10000积分-网关/tushare-10000积分-网关.TXT `
  --provider tushare `
  --http-url http://106.54.191.157:5000

# Benchmark one L1 API with concurrent calls (official channel example)
python scripts/data/benchmark_tushare_l1_rate.py `
  --token-env TUSHARE_PRIMARY_TOKEN `
  --provider tushare `
  --api daily `
  --calls 500 `
  --workers 50

# Benchmark gateway channel throughput (10000 trial)
python scripts/data/benchmark_tushare_l1_rate.py `
  --token-file docs/reference/tushare/tushare-10000积分-网关/tushare-10000积分-网关.TXT `
  --provider tushare `
  --http-url http://106.54.191.157:5000 `
  --api daily `
  --calls 500 `
  --workers 50

# Status only (no download)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StatusOnly

# Full backfill + auto retry
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -Start 20200101 -End 20260218 -BatchSize 365 -Workers 3 -RetryMax 10

# Full backfill in background (return PID immediately, no blocking wait)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -Start 20200101 -End 20260218 -BatchSize 365 -Workers 3 -RetryMax 10 -Background

# Query/stop background runner
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -RunnerStatus
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StopRunner

# Retry failed batches only (use existing progress file range)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -RetryOnly -RetryMax 10

# Retry only + lock check + auto stop lock holder PIDs (one command)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -RetryUnlock -RetryMax 10

# Retry only + lock check (no process stop)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -RetryOnly -CheckLock -RetryMax 10

# Optional: force eq CLI (default runner is python -m src.pipeline.main)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -Start 20200101 -End 20260218 -UseEq
```

## Notes

- `fetch-batch` shows a progress bar by default.
- `fetch-retry` does not have a built-in progress bar; this script prints round-by-round status summary.
- `fetch-retry` always retries failed batches from the latest progress file (`artifacts/spiral-s3a/<date>/fetch_progress.json`), and the retry date span is exactly `start_date/end_date` in that file.
- `-ForceStopLockPid` can only be used with `-CheckLock`.
- `-RetryUnlock` is equivalent to `-RetryOnly -CheckLock -ForceStopLockPid`.
- Use `-Background` to avoid waiting in terminal. Logs are written to `artifacts/spiral-s3a/_state/`.
