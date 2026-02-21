from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3c.l2"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_sw31_inputs(db_path: Path, trade_date: str) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_daily (
                ts_code VARCHAR,
                stock_code VARCHAR,
                trade_date VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                vol BIGINT,
                amount DOUBLE
            )
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_daily_basic (
                ts_code VARCHAR,
                stock_code VARCHAR,
                trade_date VARCHAR,
                pe_ttm DOUBLE,
                pb DOUBLE
            )
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_limit_list (
                ts_code VARCHAR,
                stock_code VARCHAR,
                trade_date VARCHAR,
                limit_type VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_index_classify (
                index_code VARCHAR,
                industry_name VARCHAR,
                level VARCHAR,
                industry_code VARCHAR,
                src VARCHAR,
                trade_date VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_index_member (
                index_code VARCHAR,
                con_code VARCHAR,
                in_date VARCHAR,
                out_date VARCHAR,
                trade_date VARCHAR,
                ts_code VARCHAR,
                stock_code VARCHAR
            )
            """
        )

        classify_rows: list[tuple[str, str, str, str, str, str]] = []
        member_rows: list[tuple[str, str, str, str, str, str, str]] = []
        daily_rows: list[tuple[object, ...]] = []
        basic_rows: list[tuple[object, ...]] = []
        limit_rows: list[tuple[str, str, str, str]] = []

        for idx in range(31):
            industry_code = f"{idx + 1:06d}"
            index_code = f"801{idx + 100:03d}.SI"
            stock_code = f"{idx + 1:06d}"
            ts_code = f"{stock_code}.SZ"
            open_price = 10.0 + idx * 0.2
            close_price = open_price * (1.0 + (idx % 5 - 2) * 0.01)
            high_price = max(open_price, close_price) * 1.02
            low_price = min(open_price, close_price) * 0.98
            volume = 500000 + idx * 5000
            amount = close_price * volume

            classify_rows.append(
                (index_code, f"行业{idx + 1}", "L1", industry_code, "SW2021", "20260201")
            )
            member_rows.append(
                (index_code, ts_code, "20200101", "", "20260201", ts_code, stock_code)
            )
            daily_rows.append(
                (
                    ts_code,
                    stock_code,
                    trade_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    amount,
                )
            )
            basic_rows.append(
                (
                    ts_code,
                    stock_code,
                    trade_date,
                    10.0 + idx * 0.3,
                    1.0 + idx * 0.05,
                )
            )
            if idx % 7 == 0:
                limit_rows.append((ts_code, stock_code, trade_date, "U"))

        connection.executemany(
            "INSERT INTO raw_index_classify VALUES (?, ?, ?, ?, ?, ?)",
            classify_rows,
        )
        connection.executemany(
            "INSERT INTO raw_index_member VALUES (?, ?, ?, ?, ?, ?, ?)",
            member_rows,
        )
        connection.executemany(
            "INSERT INTO raw_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            daily_rows,
        )
        connection.executemany(
            "INSERT INTO raw_daily_basic VALUES (?, ?, ?, ?, ?)",
            basic_rows,
        )
        connection.executemany(
            "INSERT INTO raw_limit_list VALUES (?, ?, ?, ?)",
            limit_rows,
        )


def test_industry_snapshot_sw31_strict_contract(tmp_path: Path) -> None:
    trade_date = "20260213"
    config = _build_config(tmp_path)
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    _seed_sw31_inputs(db_path, trade_date)

    result = run_l2_snapshot(
        trade_date=trade_date,
        source="tushare",
        config=config,
        strict_sw31=True,
    )

    assert result.has_error is False
    assert result.industry_snapshot_count == 31

    with duckdb.connect(str(db_path), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM industry_snapshot WHERE trade_date = ?",
            [trade_date],
        ).fetchone()[0]
        distinct_codes = connection.execute(
            "SELECT COUNT(DISTINCT industry_code) FROM industry_snapshot WHERE trade_date = ?",
            [trade_date],
        ).fetchone()[0]
        all_count = connection.execute(
            "SELECT COUNT(*) FROM industry_snapshot WHERE trade_date = ? AND industry_code = 'ALL'",
            [trade_date],
        ).fetchone()[0]
        sample_cols = set(connection.execute("SELECT * FROM industry_snapshot LIMIT 1").df().columns.tolist())

    assert int(count) == 31
    assert int(distinct_codes) == 31
    assert int(all_count) == 0
    assert {"market_amount_total", "style_bucket"} <= sample_cols
    assert (Path("artifacts") / "spiral-s3c" / trade_date / "industry_snapshot_sw31_sample.parquet").exists()
    assert (Path("artifacts") / "spiral-s3c" / trade_date / "sw_mapping_audit.md").exists()

