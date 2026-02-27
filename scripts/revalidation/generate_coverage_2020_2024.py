from __future__ import annotations

import json
from pathlib import Path

import duckdb


def main() -> int:
    db_path = Path(r"G:\EmotionQuant_data\duckdb\emotionquant.duckdb")
    out_dir = Path(r"G:\EmotionQuant-alpha\artifacts\spiral-s0s2\revalidation")
    out_dir.mkdir(parents=True, exist_ok=True)

    start = "20200101"
    end = "20241231"

    with duckdb.connect(str(db_path), read_only=True) as con:
        trade_rows = con.execute(
            """
            SELECT CAST(cal_date AS VARCHAR) AS trade_date
            FROM raw_trade_cal
            WHERE is_open = 1
              AND CAST(cal_date AS VARCHAR) BETWEEN ? AND ?
            """,
            [start, end],
        ).fetchall()
        daily_rows = con.execute(
            """
            SELECT DISTINCT CAST(trade_date AS VARCHAR) AS trade_date
            FROM raw_daily
            WHERE CAST(trade_date AS VARCHAR) BETWEEN ? AND ?
            """,
            [start, end],
        ).fetchall()

    trade_set = {r[0] for r in trade_rows}
    daily_set = {r[0] for r in daily_rows}

    years = ["2020", "2021", "2022", "2023", "2024"]
    yearly: list[dict[str, object]] = []
    for y in years:
        trading = sorted(d for d in trade_set if d.startswith(y))
        covered = sorted(d for d in daily_set if d.startswith(y))
        missing = sorted(set(trading) - set(covered))
        coverage = (len(covered) / len(trading) * 100.0) if trading else 0.0
        yearly.append(
            {
                "year": y,
                "trading_days": len(trading),
                "covered_days": len(covered),
                "missing_days": len(missing),
                "coverage_ratio": round(coverage, 4),
                "missing_dates_sample": missing[:10],
            }
        )

    all_trading = len(trade_set)
    all_covered = len(trade_set & daily_set)
    all_missing = sorted(trade_set - daily_set)
    all_coverage = (all_covered / all_trading * 100.0) if all_trading else 0.0

    payload = {
        "window": {"start": start, "end": end},
        "trading_days": all_trading,
        "covered_days": all_covered,
        "missing_days": len(all_missing),
        "coverage_ratio": round(all_coverage, 4),
        "missing_dates_sample": all_missing[:20],
        "yearly": yearly,
    }

    json_path = out_dir / "coverage_2020_2024.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    gate = "PASS" if payload["coverage_ratio"] >= 99.0 else "FAIL"
    lines = [
        "# 2020-2024 数据覆盖率报告",
        "",
        f"- 窗口: {start} ~ {end}",
        f"- 交易日总数: {all_trading}",
        f"- 已覆盖交易日: {all_covered}",
        f"- 缺失交易日: {len(all_missing)}",
        f"- 覆盖率: {payload['coverage_ratio']:.4f}%",
        f"- 门禁(>=99%): {gate}",
        "",
        "## 年度明细",
        "",
        "| 年度 | 开市日 | 覆盖日 | 缺口 | 覆盖率 |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in yearly:
        lines.append(
            f"| {item['year']} | {item['trading_days']} | {item['covered_days']} | {item['missing_days']} | {item['coverage_ratio']:.4f}% |"
        )
    lines.append("")
    lines.append("## 缺口样例")
    lines.append("")
    if all_missing:
        lines.extend([f"- {d}" for d in all_missing[:20]])
    else:
        lines.append("- 无缺口")

    md_path = out_dir / "coverage_2020_2024.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "coverage_ratio": payload["coverage_ratio"],
                "missing_days": len(all_missing),
                "json_path": str(json_path),
                "md_path": str(md_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
