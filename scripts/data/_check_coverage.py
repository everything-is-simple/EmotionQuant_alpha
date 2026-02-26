"""临时脚本：按年检查本地数据库覆盖率。"""
import duckdb

db = duckdb.connect("G:/EmotionQuant_data/duckdb/emotionquant.duckdb", read_only=True)

# 交易日历基准
cal = db.execute("""
    SELECT CAST(trade_date AS VARCHAR) as td
    FROM raw_trade_cal
    WHERE CAST(is_open AS INTEGER) = 1
      AND CAST(trade_date AS VARCHAR) >= '20000101'
      AND CAST(trade_date AS VARCHAR) <= '20260226'
    ORDER BY td
""").fetchall()
cal_dates = {r[0] for r in cal}

tables = ["raw_daily", "raw_daily_basic", "raw_index_daily", "raw_limit_list"]
table_dates = {}
for t in tables:
    try:
        rows = db.execute(
            f"SELECT DISTINCT CAST(trade_date AS VARCHAR) FROM {t}"
        ).fetchall()
        table_dates[t] = {r[0] for r in rows}
    except Exception:
        table_dates[t] = set()
db.close()

# 按年统计
header = f"{'年份':>6} | {'日历':>4} | {'daily':>6} | {'basic':>6} | {'index':>6} | {'limit':>6}"
print(header)
print("-" * len(header.encode("gbk")))

for year in range(2000, 2027):
    ys = str(year)
    y_cal = {d for d in cal_dates if d[:4] == ys}
    parts = [f"{year:>6}", f"{len(y_cal):>4}"]
    for t in tables:
        y_data = {d for d in table_dates[t] if d[:4] == ys}
        n = len(y_data)
        missing = len(y_cal) - n
        if missing > 0:
            parts.append(f"{n}(-{missing})")
        else:
            parts.append(f"{n:>6}")
        
    print(" | ".join(parts))
