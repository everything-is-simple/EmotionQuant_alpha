#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双通道验证 TuShare 主/备 key 的可用性（按 EmotionQuant L1 八接口口径）。

设计目标：
1) 显式读取 .env（通过 Config.from_env），避免 shell 未导入环境变量时的误判。
2) 一次执行给出 primary/fallback 两路结论，减少运维排障成本。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# 兼容直接脚本运行：将仓库根目录加入 sys.path。
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config.config import Config

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


def _to_rows(payload: Any) -> int:
    if payload is None:
        return 0
    try:
        return int(len(payload))
    except Exception:
        return 0


def _resolve_trade_date(pro: Any, override_trade_date: str | None) -> str:
    if override_trade_date:
        return override_trade_date

    end_day = date.today()
    start_day = end_day - timedelta(days=45)
    payload = pro.trade_cal(
        exchange="SSE",
        start_date=start_day.strftime("%Y%m%d"),
        end_date=end_day.strftime("%Y%m%d"),
        fields="cal_date,is_open",
    )
    if payload is None or len(payload) == 0:
        raise RuntimeError("trade_cal returned empty when resolving latest trade date")

    try:
        open_days = payload[payload["is_open"] == 1]["cal_date"].astype(str).tolist()
    except Exception as exc:
        raise RuntimeError(f"failed to parse trade_cal: {exc}") from exc

    if not open_days:
        raise RuntimeError("no open trading day found in latest 45 days")
    open_days.sort()
    return open_days[-1]


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


def _check_api(pro: Any, api_name: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        method = getattr(pro, api_name)
        payload = method(**params)
        rows = _to_rows(payload)
        if rows > 0:
            return {"api_name": api_name, "status": "success", "rows": rows, "error": ""}
        return {"api_name": api_name, "status": "empty", "rows": 0, "error": ""}
    except Exception as exc:
        return {"api_name": api_name, "status": "error", "rows": 0, "error": str(exc)}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check TuShare primary/fallback tokens for 8 L1 raw APIs."
    )
    parser.add_argument("--env-file", default=".env", help="Env file path.")
    parser.add_argument(
        "--channels",
        choices=("primary", "fallback", "both"),
        default="both",
        help="Which channel(s) to check.",
    )
    parser.add_argument(
        "--trade-date",
        default="",
        help="Optional fixed trade date in YYYYMMDD.",
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
        help="Optional output JSON report path.",
    )
    return parser


def _channel_specs(config: Config, channels: str) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    if channels in {"primary", "both"}:
        specs.append(
            {
                "name": "primary",
                "token": str(config.tushare_primary_token or config.tushare_token),
                "provider": str(
                    config.tushare_primary_sdk_provider
                    or config.tushare_sdk_provider
                    or "tushare"
                ),
                "http_url": str(config.tushare_primary_http_url or config.tushare_http_url),
            }
        )
    if channels in {"fallback", "both"}:
        specs.append(
            {
                "name": "fallback",
                "token": str(config.tushare_fallback_token),
                "provider": str(config.tushare_fallback_sdk_provider or "tushare"),
                "http_url": str(config.tushare_fallback_http_url),
            }
        )
    return specs


def _run_channel_check(
    *,
    name: str,
    token: str,
    provider: str,
    http_url: str,
    trade_date: str,
    index_ts_code: str,
    calendar_year: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "channel": name,
        "token_mask": _mask_token(token),
        "provider": provider,
        "http_url": http_url,
        "status": "fail",
        "core_ready": False,
        "all_ready": False,
        "trade_date": "",
        "results": [],
        "error": "",
    }

    if not token.strip():
        result["status"] = "skipped"
        result["error"] = "token_empty"
        return result

    try:
        pro = _make_pro_client(
            token=token.strip(),
            provider=provider.strip() or "tushare",
            http_url=http_url.strip(),
        )
    except Exception as exc:
        result["error"] = f"init_client_failed: {exc}"
        return result

    try:
        resolved_trade_date = _resolve_trade_date(pro, trade_date.strip() or None)
    except Exception as exc:
        result["error"] = f"resolve_trade_date_failed: {exc}"
        return result

    params_map = _build_api_params(
        trade_date=resolved_trade_date,
        index_ts_code=index_ts_code,
        cal_year=int(calendar_year),
    )

    checks = [_check_api(pro, api_name, params_map[api_name]) for api_name in API_ORDER]
    success_names = {item["api_name"] for item in checks if item["status"] == "success"}
    core_ready = all(name in success_names for name in CORE_APIS)
    all_ready = len(success_names) == len(API_ORDER)

    result.update(
        {
            "status": "ok" if all_ready else ("partial" if core_ready else "fail"),
            "core_ready": core_ready,
            "all_ready": all_ready,
            "trade_date": resolved_trade_date,
            "results": checks,
        }
    )
    return result


def main() -> int:
    _safe_stdout()
    parser = _build_parser()
    args = parser.parse_args()

    config = Config.from_env(env_file=args.env_file)
    specs = _channel_specs(config, args.channels)
    if not specs:
        print("[FAIL] no channel selected")
        return 2

    print("[info] checking TuShare dual channels")
    print(f"[info] env_file={args.env_file}")
    print(f"[info] channels={args.channels}")

    channel_results: list[dict[str, Any]] = []
    for spec in specs:
        channel_name = spec["name"]
        print(
            "[run] "
            f"channel={channel_name} token={_mask_token(spec['token'])} "
            f"provider={spec['provider']} http_url={(spec['http_url'] or '<default>')}"
        )
        result = _run_channel_check(
            name=channel_name,
            token=spec["token"],
            provider=spec["provider"],
            http_url=spec["http_url"],
            trade_date=args.trade_date,
            index_ts_code=args.index_ts_code,
            calendar_year=int(args.calendar_year),
        )
        channel_results.append(result)
        print(
            "[result] "
            f"channel={channel_name} status={result['status']} "
            f"core_ready={result['core_ready']} all_ready={result['all_ready']} "
            f"trade_date={result['trade_date'] or '<none>'}"
        )
        if result["error"]:
            print(f"[error] channel={channel_name} {result['error']}")

    overall_all_ready = all(bool(item.get("all_ready")) for item in channel_results)
    overall_core_ready = all(bool(item.get("core_ready")) for item in channel_results)
    payload = {
        "event": "tushare_l1_dual_token_check",
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "env_file": args.env_file,
        "channels": args.channels,
        "overall_core_ready": overall_core_ready,
        "overall_all_ready": overall_all_ready,
        "results": channel_results,
    }

    output_path = (
        Path(args.output)
        if str(args.output).strip()
        else Path("artifacts/token-checks")
        / f"tushare_l1_dual_token_check_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"[report] {output_path.as_posix()}")
    except OSError as exc:
        # 某些受限环境只允许只读执行；此时保留控制台结论，不阻断 token 判定。
        print(f"[warn] report_write_failed path={output_path.as_posix()} error={exc}")

    if overall_all_ready:
        print("[OK] selected channels all passed 8/8 L1 APIs")
        return 0
    if overall_core_ready:
        print("[WARN] selected channels core APIs passed, but not all 8 APIs")
        return 1

    print("[FAIL] selected channels core APIs not fully ready")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
