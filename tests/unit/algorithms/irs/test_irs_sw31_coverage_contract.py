from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.algorithms.irs.pipeline import run_irs_daily
from src.config.config import Config
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3c.irs"
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


def test_irs_sw31_coverage_gate_passes_with_31_industries(tmp_path: Path) -> None:
    trade_date = "20260213"
    config = _build_config(tmp_path)
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    _seed_sw31_inputs(db_path, trade_date)

    l2_result = run_l2_snapshot(
        trade_date=trade_date,
        source="tushare",
        config=config,
        strict_sw31=True,
    )
    assert l2_result.has_error is False

    irs_result = run_irs_daily(
        trade_date=trade_date,
        config=config,
        require_sw31=True,
    )
    assert irs_result.count == 31
    assert irs_result.coverage_report_path.exists()
    assert irs_result.frame["allocation_advice"].astype(str).str.strip().ne("").all()


def test_irs_sw31_coverage_gate_fails_for_all_aggregate(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            """
            CREATE OR REPLACE TABLE industry_snapshot (
                trade_date VARCHAR,
                industry_code VARCHAR,
                industry_name VARCHAR,
                stock_count BIGINT,
                rise_count BIGINT,
                fall_count BIGINT,
                flat_count BIGINT,
                industry_close DOUBLE,
                industry_pct_chg DOUBLE,
                industry_amount DOUBLE,
                industry_turnover DOUBLE,
                market_amount_total DOUBLE,
                style_bucket VARCHAR,
                industry_pe_ttm DOUBLE,
                industry_pb DOUBLE,
                limit_up_count BIGINT,
                limit_down_count BIGINT,
                new_100d_high_count BIGINT,
                new_100d_low_count BIGINT,
                top5_codes VARCHAR,
                top5_pct_chg VARCHAR,
                top5_limit_up BIGINT,
                yesterday_limit_up_today_avg_pct DOUBLE,
                data_quality VARCHAR,
                stale_days BIGINT,
                source_trade_date VARCHAR
            )
            """
        )
        connection.execute(
            """
            INSERT INTO industry_snapshot VALUES
            ('20260213','ALL','全市场聚合',100,55,40,5,10.1,0.8,1000000,500000,1000000,'balanced',
             10.0,1.2,3,1,0,0,'[]','[]',0,0.0,'normal',0,'20260213')
            """
        )

    with pytest.raises(ValueError, match="irs_sw31_coverage_gate_failed"):
        run_irs_daily(trade_date="20260213", config=config, require_sw31=True)

