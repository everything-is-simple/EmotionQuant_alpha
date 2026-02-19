#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查 TuShare token 是否可用于 EmotionQuant 所需的 8 个 L1 原始接口。

默认读取顺序：
1) 环境变量 TUSHARE_PRIMARY_TOKEN
2) docs/reference/tushare/tushare-10000积分-网关/tushare-10000积分-网关.TXT
3) docs/reference/tushare/tushare-config-5000积分-官方-兜底号.md

可通过参数覆盖。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_TOKEN_FILES = [
    "docs/reference/tushare/tushare-10000积分-网关/tushare-10000积分-网关.TXT",
    "docs/reference/tushare/tushare-config-5000积分-官方-兜底号.md",
    "docs/reference/tushare/tushare-5000积分-官方.txt",
]

API_ORDER = [
    "daily",
    "daily_basic",
    "limit_list_d",
    "index_daily",
    "index_member",
    "index_classify",
    "stock_basic",
    "trade_cal",
]

CORE_APIS = ["daily", "daily_basic", "limit_list_d", "index_daily"]


@dataclass(frozen=True)
class ApiCheckResult:
    api_name: str
    status: str
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
    # 提取最长的字母数字串，适配文本中夹杂说明文字的情况
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

    try:
        open_days = df[df["is_open"] == 1]["cal_date"].astype(str).tolist()
    except Exception as exc:
        raise RuntimeError(f"failed to parse trade_cal: {exc}") from exc

    if not open_days:
        raise RuntimeError("no open trading day found in latest 45 days")
    open_days.sort()
    return open_days[-1]


def _check_api(pro: Any, api_name: str, params: dict[str, Any]) -> ApiCheckResult:
    try:
        method = getattr(pro, api_name)
        df = method(**params)
        rows = _to_rows(df)
        if rows > 0:
            return ApiCheckResult(api_name=api_name, status="success", rows=rows)
        return ApiCheckResult(api_name=api_name, status="empty", rows=0)
    except Exception as exc:
        return ApiCheckResult(api_name=api_name, status="error", rows=0, error=str(exc))


def _build_api_params(trade_date: str, index_ts_code: str, cal_year: int) -> dict[str, dict[str, Any]]:
    year_start = f"{cal_year}0101"
    year_end = f"{cal_year}1231"
    return {
        "daily": {
            "trade_date": trade_date,
            "fields": "ts_code,trade_date,open,high,low,close,vol,amount",
        },
        "daily_basic": {
            "trade_date": trade_date,
            "fields": "ts_code,trade_date,turnover_rate,pe_ttm,pb,total_mv,circ_mv",
        },
        "limit_list_d": {
            "trade_date": trade_date,
            "fields": "ts_code,trade_date,limit",
        },
        "index_daily": {
            "ts_code": index_ts_code,
            "trade_date": trade_date,
            "fields": "ts_code,trade_date,open,high,low,close,pct_chg,vol,amount",
        },
        "index_member": {},
        "index_classify": {},
        "stock_basic": {
            "list_status": "L",
            "fields": "ts_code,name,industry,list_date",
        },
        "trade_cal": {
            "exchange": "SSE",
            "start_date": year_start,
            "end_date": year_end,
            "fields": "cal_date,is_open",
        },
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check TuShare token for 8 L1 raw APIs.")
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
        "--trade-date",
        default="",
        help="Optional fixed trade date in YYYYMMDD; if empty resolve latest open date.",
    )
    parser.add_argument(
        "--index-ts-code",
        default="000001.SH",
        help="Index ts_code for index_daily.",
    )
    parser.add_argument(
        "--calendar-year",
        type=int,
        default=date.today().year,
        help="Year window for trade_cal check.",
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

    print("[info] checking TuShare L1 token")
    print(f"[info] token_source={token_source}")
    print(f"[info] token_mask={_mask_token(token)}")
    print(f"[info] provider={args.provider}")
    print(f"[info] http_url={(args.http_url or '<default>')}")

    try:
        pro = _make_pro_client(
            token=token,
            provider=args.provider,
            http_url=args.http_url,
        )
    except Exception as exc:
        print(f"[FAIL] init client failed: {exc}")
        return 2

    try:
        trade_date = _resolve_trade_date(pro, args.trade_date.strip() or None)
        print(f"[info] resolved_trade_date={trade_date}")
    except Exception as exc:
        print(f"[FAIL] resolve trade date failed: {exc}")
        return 2

    params_map = _build_api_params(
        trade_date=trade_date,
        index_ts_code=args.index_ts_code,
        cal_year=int(args.calendar_year),
    )
    results: list[ApiCheckResult] = []
    for api_name in API_ORDER:
        result = _check_api(pro, api_name, params_map[api_name])
        results.append(result)
        if result.status == "success":
            print(f"[OK] {api_name}: rows={result.rows}")
        elif result.status == "empty":
            print(f"[WARN] {api_name}: empty")
        else:
            print(f"[FAIL] {api_name}: {result.error}")

    success_names = [item.api_name for item in results if item.status == "success"]
    core_ready = all(name in success_names for name in CORE_APIS)
    all_ready = len(success_names) == len(API_ORDER)

    payload = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "token_source": token_source,
        "token_mask": _mask_token(token),
        "provider": args.provider,
        "http_url": args.http_url or "",
        "trade_date": trade_date,
        "core_ready": core_ready,
        "all_ready": all_ready,
        "results": [
            {
                "api_name": item.api_name,
                "status": item.status,
                "rows": item.rows,
                "error": item.error,
            }
            for item in results
        ],
    }

    output_path = Path(args.output) if args.output else Path(
        "artifacts/token-checks"
    ) / f"tushare_l1_token_check_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    _write_report(output_path, payload)
    print(f"[report] {output_path.as_posix()}")

    if all_ready:
        print("[OK] all 8 L1 APIs are available")
        return 0
    if core_ready:
        print("[WARN] core 4 APIs are available, but not all 8")
        return 1
    print("[FAIL] core APIs unavailable")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
