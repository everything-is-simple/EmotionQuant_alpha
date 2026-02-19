#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Benchmark TuShare/TuShare-gateway request throughput for one L1 API.

Output:
1) Console summary
2) JSON report under artifacts/token-checks by default
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_TOKEN_FILES = [
    "docs/reference/tushare/tushare-config-5000积分-官方-兜底号.md",
    "docs/reference/tushare/tushare-5000积分-官方.txt",
]


@dataclass(frozen=True)
class CallResult:
    index: int
    status: str
    elapsed_seconds: float
    rows: int
    error: str = ""


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


def _extract_token_from_text(content: str) -> str:
    candidates = re.findall(r"[A-Za-z0-9]{24,}", content or "")
    if not candidates:
        return ""
    candidates.sort(key=len, reverse=True)
    return candidates[0].strip()


def _load_token(args: argparse.Namespace) -> tuple[str, str]:
    if args.token.strip():
        return args.token.strip(), "arg:--token"

    env_token = os.getenv(args.token_env, "").strip()
    if env_token:
        return env_token, f"env:{args.token_env}"

    for token_file in args.token_file:
        path = Path(token_file)
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        parsed = _extract_token_from_text(content)
        if parsed:
            return parsed, f"file:{path.as_posix()}"

    return "", "not_found"


def _load_provider_module(provider: str):
    provider_name = (provider or "tushare").strip().lower()
    module_name = "tinyshare" if provider_name == "tinyshare" else "tushare"
    return __import__(module_name)


def _make_pro_client(token: str, provider: str, http_url: str):
    module = _load_provider_module(provider)
    pro = module.pro_api(token)
    if hasattr(pro, "_DataApi__token"):
        setattr(pro, "_DataApi__token", token)
    gateway_url = (http_url or "").strip()
    if gateway_url and hasattr(pro, "_DataApi__http_url"):
        setattr(pro, "_DataApi__http_url", gateway_url)
    return pro


def _to_rows(df: Any) -> int:
    if df is None:
        return 0
    try:
        return int(len(df))
    except Exception:
        return 0


def _resolve_trade_date(pro: Any, override_trade_date: str | None) -> str:
    if override_trade_date:
        return override_trade_date
    end_day = date.today()
    start_day = end_day - timedelta(days=45)
    df = pro.trade_cal(
        exchange="SSE",
        start_date=start_day.strftime("%Y%m%d"),
        end_date=end_day.strftime("%Y%m%d"),
        fields="cal_date,is_open",
    )
    if df is None or len(df) == 0:
        raise RuntimeError("trade_cal returned empty when resolving latest trade date")
    open_days = df[df["is_open"] == 1]["cal_date"].astype(str).tolist()
    if not open_days:
        raise RuntimeError("no open trading day found in latest 45 days")
    open_days.sort()
    return open_days[-1]


def _p_latency(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    values_sorted = sorted(values)
    idx = int(round((len(values_sorted) - 1) * p))
    idx = max(0, min(idx, len(values_sorted) - 1))
    return values_sorted[idx]


def _call_once(
    *,
    index: int,
    token: str,
    provider: str,
    http_url: str,
    api_name: str,
    params: dict[str, Any],
) -> CallResult:
    started = time.perf_counter()
    try:
        pro = _make_pro_client(token=token, provider=provider, http_url=http_url)
        method = getattr(pro, api_name)
        df = method(**params)
        elapsed = time.perf_counter() - started
        return CallResult(
            index=index,
            status="success",
            elapsed_seconds=elapsed,
            rows=_to_rows(df),
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return CallResult(
            index=index,
            status="error",
            elapsed_seconds=elapsed,
            rows=0,
            error=f"{type(exc).__name__}: {exc}",
        )


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark TuShare L1 API throughput and stability.")
    parser.add_argument("--token", default="", help="Token string. If empty, read env/file.")
    parser.add_argument(
        "--token-env",
        default="TUSHARE_PRIMARY_TOKEN",
        help="Env var name for token fallback.",
    )
    parser.add_argument(
        "--token-file",
        action="append",
        default=[],
        help="Token file path. Can be passed multiple times.",
    )
    parser.add_argument(
        "--provider",
        default="tushare",
        choices=["tushare", "tinyshare"],
        help="SDK provider.",
    )
    parser.add_argument(
        "--http-url",
        default="",
        help="Optional gateway URL. Example: http://106.54.191.157:5000",
    )
    parser.add_argument(
        "--api",
        default="daily",
        help="API name to benchmark. Example: daily, daily_basic, stock_basic.",
    )
    parser.add_argument(
        "--trade-date",
        default="",
        help="Optional fixed trade date in YYYYMMDD; if empty resolve latest open date.",
    )
    parser.add_argument(
        "--fields",
        default="ts_code,trade_date",
        help="Fields for daily-like APIs. Leave empty to use API defaults.",
    )
    parser.add_argument(
        "--params-json",
        default="{}",
        help="Extra params as JSON object. Example: '{\"list_status\":\"L\"}'",
    )
    parser.add_argument(
        "--calls",
        type=int,
        default=200,
        help="Total API calls. Default 200.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="Parallel workers. Default 20.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON report path.",
    )
    return parser


def main() -> int:
    _safe_stdout()
    parser = build_parser()
    args = parser.parse_args()

    token_files = args.token_file or list(DEFAULT_TOKEN_FILES)
    args.token_file = token_files

    token, token_source = _load_token(args)
    if not token:
        print("[FAIL] token not found from --token / env / token files")
        print(f"[hint] token files checked: {token_files}")
        return 2

    calls = max(1, int(args.calls))
    workers = max(1, int(args.workers))
    params = {}
    if args.params_json.strip():
        try:
            parsed = json.loads(args.params_json)
            if not isinstance(parsed, dict):
                raise ValueError("params-json must be object")
            params = {str(k): v for k, v in parsed.items()}
        except Exception as exc:
            print(f"[FAIL] invalid --params-json: {exc}")
            return 2

    print("[info] benchmarking TuShare L1 API")
    print(f"[info] token_source={token_source}")
    print(f"[info] token_mask={_mask_token(token)}")
    print(f"[info] provider={args.provider}")
    print(f"[info] http_url={(args.http_url or '<default>')}")
    print(f"[info] api={args.api}")
    print(f"[info] calls={calls}")
    print(f"[info] workers={workers}")

    try:
        warmup_pro = _make_pro_client(token=token, provider=args.provider, http_url=args.http_url)
        trade_date = _resolve_trade_date(warmup_pro, args.trade_date.strip() or None)
    except Exception as exc:
        print(f"[FAIL] init/warmup failed: {exc}")
        return 2

    effective_params = dict(params)
    if "trade_date" not in effective_params and args.api in {
        "daily",
        "daily_basic",
        "limit_list_d",
        "index_daily",
    }:
        effective_params["trade_date"] = trade_date
    if "fields" not in effective_params and args.fields.strip() and args.api in {
        "daily",
        "daily_basic",
        "limit_list_d",
        "index_daily",
    }:
        effective_params["fields"] = args.fields.strip()
    if args.api == "index_daily" and "ts_code" not in effective_params:
        effective_params["ts_code"] = "000001.SH"
    if args.api == "stock_basic" and "list_status" not in effective_params:
        effective_params["list_status"] = "L"
    if args.api == "trade_cal" and "start_date" not in effective_params:
        year = date.today().year
        effective_params["exchange"] = effective_params.get("exchange", "SSE")
        effective_params["start_date"] = f"{year}0101"
        effective_params["end_date"] = f"{year}1231"

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _call_once,
                index=i + 1,
                token=token,
                provider=args.provider,
                http_url=args.http_url,
                api_name=args.api,
                params=effective_params,
            )
            for i in range(calls)
        ]
        results = [future.result() for future in futures]
    wall_seconds = time.perf_counter() - started

    success = [item for item in results if item.status == "success"]
    errors = [item for item in results if item.status == "error"]
    success_latencies = [item.elapsed_seconds for item in success]
    error_types: dict[str, int] = {}
    for item in errors:
        error_key = item.error.split(":", 1)[0].strip() if ":" in item.error else item.error
        error_types[error_key] = error_types.get(error_key, 0) + 1

    calls_per_min = calls / max(0.001, wall_seconds) * 60.0
    success_calls_per_min = len(success) / max(0.001, wall_seconds) * 60.0
    success_rate = len(success) / calls * 100.0

    payload = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "token_source": token_source,
        "token_mask": _mask_token(token),
        "provider": args.provider,
        "http_url": args.http_url or "",
        "api": args.api,
        "trade_date": trade_date,
        "params": effective_params,
        "calls": calls,
        "workers": workers,
        "wall_seconds": wall_seconds,
        "calls_per_min": calls_per_min,
        "success_calls_per_min": success_calls_per_min,
        "success": len(success),
        "errors": len(errors),
        "success_rate_pct": success_rate,
        "latency_seconds": {
            "avg": statistics.fmean(success_latencies) if success_latencies else 0.0,
            "p50": _p_latency(success_latencies, 0.50),
            "p95": _p_latency(success_latencies, 0.95),
            "max": max(success_latencies) if success_latencies else 0.0,
        },
        "error_types": error_types,
    }

    output_path = Path(args.output) if args.output else Path(
        "artifacts/token-checks"
    ) / f"tushare_l1_rate_benchmark_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    _write_report(output_path, payload)

    print("[result] benchmark summary")
    print(f"[result] trade_date={trade_date}")
    print(f"[result] success={len(success)}/{calls} ({success_rate:.1f}%)")
    print(f"[result] calls_per_min={calls_per_min:.1f}")
    print(f"[result] success_calls_per_min={success_calls_per_min:.1f}")
    print(
        "[result] latency_seconds="
        f"avg:{payload['latency_seconds']['avg']:.3f}, "
        f"p50:{payload['latency_seconds']['p50']:.3f}, "
        f"p95:{payload['latency_seconds']['p95']:.3f}, "
        f"max:{payload['latency_seconds']['max']:.3f}"
    )
    if error_types:
        print(f"[result] error_types={error_types}")
    print(f"[report] {output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
