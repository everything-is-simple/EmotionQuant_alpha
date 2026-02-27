import duckdb

conn = duckdb.connect(r"G:\EmotionQuant_data\duckdb\emotionquant.duckdb", read_only=True)

l1_tables = ["raw_trade_cal", "raw_daily", "raw_daily_basic", "raw_stock_basic", "raw_index_daily", "raw_index_classify", "raw_index_member", "raw_limit_list"]
l2_tables = ["irs_factor_intermediate", "pas_factor_intermediate", "industry_snapshot", "market_snapshot", "data_quality_report", "data_readiness_gate", "quality_gate_report"]
l3_tables = ["stock_pas_daily", "irs_industry_daily", "mss_panorama", "integrated_recommendation"]

for label, tlist in [("L1", l1_tables), ("L2", l2_tables), ("L3", l3_tables)]:
    print(f"\n=== {label} TABLES ===")
    for t in tlist:
        try:
            cols = [r[0] for r in conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{t}'"
            ).fetchall()]
            date_col = None
            for c in ["trade_date", "cal_date", "metric_date"]:
                if c in cols:
                    date_col = c
                    break
            if date_col:
                r = conn.execute(f"SELECT COUNT(*) cnt, MIN({date_col}) mn, MAX({date_col}) mx FROM {t}").fetchone()
                # count distinct dates
                d = conn.execute(f"SELECT COUNT(DISTINCT {date_col}) FROM {t}").fetchone()
                print(f"  {t}: rows={r[0]:,}, dates={d[0]:,}, range=[{r[1]} ~ {r[2]}]")
            else:
                r = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                print(f"  {t}: rows={r[0]:,}, no date column")
        except Exception as e:
            print(f"  {t}: ERROR {e}")

# Also check L3 year-by-year coverage
print("\n=== L3 YEARLY BREAKDOWN ===")
for t in l3_tables:
    print(f"\n  --- {t} ---")
    try:
        rows = conn.execute(
            f"SELECT SUBSTRING(CAST(trade_date AS VARCHAR), 1, 4) AS yr, COUNT(*) cnt, "
            f"MIN(trade_date) mn, MAX(trade_date) mx "
            f"FROM {t} GROUP BY yr ORDER BY yr"
        ).fetchall()
        for r in rows:
            print(f"    {r[0]}: {r[1]:>8,} rows  [{r[2]} ~ {r[3]}]")
    except Exception as e:
        print(f"    ERROR: {e}")

# Check raw_trade_cal for open days in 2020-2026
print("\n=== TRADE CALENDAR: open days per year (2020-2026) ===")
try:
    rows = conn.execute(
        "SELECT SUBSTRING(CAST(trade_date AS VARCHAR), 1, 4) AS yr, "
        "SUM(CASE WHEN CAST(is_open AS INTEGER) = 1 THEN 1 ELSE 0 END) AS open_days "
        "FROM raw_trade_cal "
        "WHERE trade_date >= '20200101' AND trade_date <= '20261231' "
        "GROUP BY yr ORDER BY yr"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]} open days")
except Exception as e:
    print(f"  ERROR: {e}")

conn.close()
