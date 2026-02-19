# L1 Fetch Tool

Use `scripts/data/run_l1_fetch.ps1` to run L1 backfill locally with visible progress and retry loops.

## Commands

```powershell
# Status only (no download)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StatusOnly

# Full backfill + auto retry
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 `
  -Start 20200101 -End 20260218 -BatchSize 365 -Workers 3 -RetryMax 10

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
- `fetch-retry` always retries failed batches from the latest progress file (`artifacts/spiral-s3a/<date>/fetch_progress.json`).
- `-ForceStopLockPid` can only be used with `-CheckLock`.
- `-RetryUnlock` is equivalent to `-RetryOnly -CheckLock -ForceStopLockPid`.
