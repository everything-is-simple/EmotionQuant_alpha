import duckdb

conn = duckdb.connect(r"G:\EmotionQuant_data\duckdb\emotionquant.duckdb", read_only=True)

# Get all open trade dates 2020-2026
open_days = conn.execute(
    "SELECT trade_date FROM raw_trade_cal "
    "WHERE CAST(is_open AS INTEGER) = 1 AND trade_date >= '20200102' AND trade_date <= '20260219' "
    "ORDER BY trade_date"
).fetchall()
all_open = set(r[0] for r in open_days)
print(f"Total open trade dates 2020-01-02 ~ 2026-02-19: {len(all_open)}")

# Check each key table
tables_to_check = [
    # L2
    "irs_factor_intermediate",
    "pas_factor_intermediate",
    "industry_snapshot",
    "market_snapshot",
    "quality_gate_report",
    # L3
    "stock_pas_daily",
    "irs_industry_daily",
    "mss_panorama",
    "integrated_recommendation",
]

for t in tables_to_check:
    existing = conn.execute(
        f"SELECT DISTINCT trade_date FROM {t} ORDER BY trade_date"
    ).fetchall()
    existing_set = set(r[0] for r in existing)
    missing = sorted(all_open - existing_set)
    covered = sorted(all_open & existing_set)

    print(f"\n=== {t} ===")
    print(f"  Covered dates: {len(covered)} / {len(all_open)} ({100*len(covered)/len(all_open):.1f}%)")
    print(f"  Missing dates: {len(missing)}")
    if missing:
        # Show by year
        from collections import Counter
        year_counts = Counter(d[:4] for d in missing)
        for yr in sorted(year_counts):
            print(f"    {yr}: {year_counts[yr]} missing days")
        # Show first/last few missing
        if len(missing) <= 10:
            print(f"    Missing: {missing}")
        else:
            print(f"    First 3: {missing[:3]}")
            print(f"    Last 3:  {missing[-3:]}")

conn.close()
