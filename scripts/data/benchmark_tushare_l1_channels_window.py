#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对比 TuShare 主通道/兜底通道在指定窗口获取 L1 数据的真实速度与数据量。

说明：
1) 该脚本只做“拉取测速”，不落库，不会污染现有 DuckDB。
2) 口径尽量贴近 L1 生产接口：daily/daily_basic/index_daily/limit_list +
   月度静态接口 stock_basic/index_member/index_classify + trade_cal。
3) 输出 JSON 报告到 artifacts/token-checks，便于和 S3/S3b 卡点对照。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# 兼容直接以脚本方式运行：将仓库根目录加入 sys.path。
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config.config import Config
from src.data.fetcher import RealTuShareClient, TuShareFetcher


@dataclass
class ApiStat:
    calls: int = 0
    rows: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0


def _safe_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _mask_token(token: str) -> str:
    value = token.strip()
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return f"<len={len(value)}>"
    return f"{value[:4]}...{value[-4:]} (len={len(value)})"


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d")


def _month_anchor(trade_date: str) -> str:
    return f"{trade_date[:6]}01"


def _half_year_anchor(trade_date: str) -> str:
    year = trade_date[:4]
    month = int(trade_date[4:6])
    return f"{year}0101" if month <= 6 else f"{year}0701"


def _to_rows(payload: Any) -> int:
    if payload is None:
        return 0
    try:
        return int(len(payload))
    except Exception:
        return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark primary/fallback TuShare channels for L1 window fetch."
    )
    parser.add_argument("--env-file", default=".env", help="Env file path.")
    parser.add_argument("--start", required=True, help="Start date YYYYMMDD.")
    parser.add_argument("--end", required=True, help="End date YYYYMMDD.")
    parser.add_argument(
        "--channels",
        choices=("primary", "fallback", "both"),
        default="both",
        help="Which channel(s) to benchmark.",
    )
    parser.add_argument(
        "--index-ts-code",
        default="000001.SH",
        help="Index ts_code used by index_daily benchmark calls.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output json path.",
    )
    return parser


def _channel_specs(config: Config, channels: str) -> list[dict[str, str | int]]:
    specs: list[dict[str, str | int]] = []
    if channels in {"primary", "both"}:
        specs.append(
            {
                "name": "primary",
                "token": str(config.tushare_primary_token or config.tushare_token),
                "provider": str(config.tushare_primary_sdk_provider or config.tushare_sdk_provider or "tushare"),
                "http_url": str(config.tushare_primary_http_url or config.tushare_http_url),
                "rate_limit_per_min": int(
                    config.tushare_primary_rate_limit_per_min or config.tushare_rate_limit_per_min
                ),
            }
        )
    if channels in {"fallback", "both"}:
        specs.append(
            {
                "name": "fallback",
                "token": str(config.tushare_fallback_token),
                "provider": str(config.tushare_fallback_sdk_provider or "tushare"),
                "http_url": str(config.tushare_fallback_http_url),
                "rate_limit_per_min": int(
                    config.tushare_fallback_rate_limit_per_min or config.tushare_rate_limit_per_min
                ),
            }
        )
    return specs


def _sleep_to_rate_limit(last_call_at: float, rate_limit_per_min: int) -> float:
    if rate_limit_per_min <= 0:
        return time.monotonic()
    min_interval = 60.0 / float(rate_limit_per_min)
    now = time.monotonic()
    elapsed = now - last_call_at
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.monotonic()


def _bench_one_channel(
    *,
    name: str,
    token: str,
    provider: str,
    http_url: str,
    rate_limit_per_min: int,
    start_date: str,
    end_date: str,
    index_ts_code: str,
) -> dict[str, Any]:
    if not token.strip():
        return {
            "channel": name,
            "status": "skipped",
            "reason": "token_empty",
        }

    # 这里显式绑定单通道 client，避免主备自动切换干扰测速结果。
    client = RealTuShareClient(
        token=token.strip(),
        sdk_provider=provider.strip() or "tushare",
        http_url=http_url.strip(),
    )
    fetcher = TuShareFetcher(client=client, max_retries=3)

    api_stats: dict[str, ApiStat] = {
        "trade_cal": ApiStat(),
        "daily": ApiStat(),
        "daily_basic": ApiStat(),
        "index_daily": ApiStat(),
        "limit_list": ApiStat(),
        "stock_basic": ApiStat(),
        "index_member": ApiStat(),
        "index_classify": ApiStat(),
    }
    error_samples: list[str] = []

    def tracked_call(api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        stat = api_stats[api_name]
        started = time.perf_counter()
        try:
            rows = fetcher.fetch_with_retry(api_name, params)
            stat.calls += 1
            stat.rows += _to_rows(rows)
            stat.elapsed_seconds += time.perf_counter() - started
            return rows
        except Exception as exc:
            stat.calls += 1
            stat.errors += 1
            stat.elapsed_seconds += time.perf_counter() - started
            if len(error_samples) < 12:
                error_samples.append(f"{api_name}: {type(exc).__name__}: {exc}")
            return []

    started = time.perf_counter()
    last_call_at = 0.0

    # 先一次性拿窗口交易日历，避免每个日期都额外探测。
    last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
    cal_rows = tracked_call(
        "trade_cal",
        {"start_date": start_date, "end_date": end_date},
    )
    open_days = sorted(
        {
            str(row.get("trade_date", row.get("cal_date", ""))).strip()
            for row in cal_rows
            if str(row.get("trade_date", row.get("cal_date", ""))).strip()
            and str(row.get("is_open", row.get("is_trading", "0"))).strip().lower() in {"1", "true", "y", "yes"}
        }
    )

    month_anchors = sorted({_month_anchor(day) for day in open_days})
    half_year_anchors = sorted({_half_year_anchor(day) for day in open_days})

    # 月度/半年度静态接口：按窗口锚点最小次数调用。
    for month_anchor in month_anchors:
        for list_status in ("L", "D", "P"):
            last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
            _ = tracked_call("stock_basic", {"list_status": list_status})
        last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
        _ = tracked_call(
            "index_member",
            {"start_date": month_anchor, "end_date": month_anchor, "src": "SW2021"},
        )
    for _ in half_year_anchors:
        last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
        _ = tracked_call("index_classify", {"src": "SW2021", "level": "L1"})

    # 日频接口：只对开市日拉取，口径对齐 L1 核心产物。
    for trade_date in open_days:
        last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
        _ = tracked_call("daily", {"trade_date": trade_date})
        last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
        _ = tracked_call("daily_basic", {"trade_date": trade_date})
        last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
        _ = tracked_call("index_daily", {"trade_date": trade_date, "ts_code": index_ts_code})
        last_call_at = _sleep_to_rate_limit(last_call_at, rate_limit_per_min)
        _ = tracked_call("limit_list", {"trade_date": trade_date})

    wall_seconds = max(time.perf_counter() - started, 1e-9)
    total_calls = sum(item.calls for item in api_stats.values())
    total_rows = sum(item.rows for item in api_stats.values())
    total_errors = sum(item.errors for item in api_stats.values())

    return {
        "channel": name,
        "status": "ok" if total_errors == 0 else "partial_error",
        "token_mask": _mask_token(token),
        "provider": provider,
        "http_url": http_url,
        "rate_limit_per_min": rate_limit_per_min,
        "start_date": start_date,
        "end_date": end_date,
        "open_trade_days": len(open_days),
        "month_anchors": month_anchors,
        "half_year_anchors": half_year_anchors,
        "summary": {
            "total_calls": total_calls,
            "total_rows": total_rows,
            "total_errors": total_errors,
            "wall_seconds": wall_seconds,
            "calls_per_min": total_calls / wall_seconds * 60.0,
            "rows_per_sec": total_rows / wall_seconds,
        },
        "api_stats": {
            api: {
                "calls": stat.calls,
                "rows": stat.rows,
                "errors": stat.errors,
                "elapsed_seconds": stat.elapsed_seconds,
                "avg_latency_seconds": (stat.elapsed_seconds / stat.calls) if stat.calls > 0 else 0.0,
            }
            for api, stat in api_stats.items()
        },
        "error_samples": error_samples,
    }


def main() -> int:
    _safe_stdout()
    parser = _build_parser()
    args = parser.parse_args()

    _ = _parse_date(args.start)
    _ = _parse_date(args.end)
    if args.end < args.start:
        print("end date must be >= start date")
        return 2

    config = Config.from_env(env_file=args.env_file)
    specs = _channel_specs(config, args.channels)

    results: list[dict[str, Any]] = []
    for spec in specs:
        name = str(spec["name"])
        print(f"[run] channel={name} start={args.start} end={args.end}")
        result = _bench_one_channel(
            name=name,
            token=str(spec["token"]),
            provider=str(spec["provider"]),
            http_url=str(spec["http_url"]),
            rate_limit_per_min=int(spec["rate_limit_per_min"]),
            start_date=args.start,
            end_date=args.end,
            index_ts_code=args.index_ts_code,
        )
        results.append(result)
        summary = result.get("summary", {})
        print(
            "[result] "
            f"channel={name} status={result.get('status')} "
            f"calls={summary.get('total_calls', 0)} rows={summary.get('total_rows', 0)} "
            f"errors={summary.get('total_errors', 0)} "
            f"wall_seconds={summary.get('wall_seconds', 0):.2f} "
            f"calls_per_min={summary.get('calls_per_min', 0):.2f}"
        )

    payload = {
        "event": "tushare_l1_channels_window_benchmark",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "env_file": args.env_file,
        "start_date": args.start,
        "end_date": args.end,
        "channels": args.channels,
        "results": results,
    }

    output_path = (
        Path(args.output)
        if str(args.output).strip()
        else Path("artifacts/token-checks")
        / f"tushare_l1_channels_window_benchmark_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"[report] {output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
