#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双通道验证 TuShare 主/备 key 的可用性（按 EmotionQuant L1 八接口口径）。

设计目标：
1) 显式读取 .env（通过 Config.from_env），避免 shell 未导入环境变量时的误判。
2) 一次执行同时给出 primary/fallback 两路结论，便于 S3/S4b 运维排障。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# 兼容直接脚本运行：将仓库根目录加入 sys.path。
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config.config import Config

from scripts.data import check_tushare_l1_token as single_check


def _safe_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


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
    masked_token = single_check._mask_token(token)
    result: dict[str, Any] = {
        "channel": name,
        "token_mask": masked_token,
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
        pro = single_check._make_pro_client(
            token=token.strip(),
            provider=provider.strip() or "tushare",
            http_url=http_url.strip(),
        )
    except Exception as exc:
        result["error"] = f"init_client_failed: {exc}"
        return result

    try:
        resolved_trade_date = single_check._resolve_trade_date(
            pro, trade_date.strip() or None
        )
    except Exception as exc:
        result["error"] = f"resolve_trade_date_failed: {exc}"
        return result

    params_map = single_check._build_api_params(
        trade_date=resolved_trade_date,
        index_ts_code=index_ts_code,
        cal_year=int(calendar_year),
    )
    checks: list[single_check.ApiCheckResult] = []
    for api_name in single_check.API_ORDER:
        checks.append(single_check._check_api(pro, api_name, params_map[api_name]))

    success_names = {item.api_name for item in checks if item.status == "success"}
    core_ready = all(name in success_names for name in single_check.CORE_APIS)
    all_ready = len(success_names) == len(single_check.API_ORDER)

    result.update(
        {
            "status": "ok" if all_ready else ("partial" if core_ready else "fail"),
            "core_ready": core_ready,
            "all_ready": all_ready,
            "trade_date": resolved_trade_date,
            "results": [
                {
                    "api_name": item.api_name,
                    "status": item.status,
                    "rows": item.rows,
                    "error": item.error,
                }
                for item in checks
            ],
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
            f"channel={channel_name} token={single_check._mask_token(spec['token'])} "
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
        # 某些受限环境仅允许只读执行；此时保留控制台结论，不阻断 token 可用性判定。
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
