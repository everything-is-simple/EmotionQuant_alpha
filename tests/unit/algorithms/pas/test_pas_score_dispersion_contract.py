from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.pas.pipeline import run_pas_daily
from src.config.config import Config


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.pas.dispersion"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_raw_daily(db_path: Path) -> str:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    trade_dates = [f"202602{day:02d}" for day in range(1, 21)]
    target_date = trade_dates[-1]

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
                amount DOUBLE,
                pre_close DOUBLE,
                change DOUBLE,
                pct_chg DOUBLE
            )
            """
        )

        records: list[tuple[object, ...]] = []
        prev_close_a = 10.0
        prev_close_b = 20.0
        for idx, trade_date in enumerate(trade_dates):
            close_a = 10.0 + 0.15 * idx + (0.8 if idx == len(trade_dates) - 1 else 0.0)
            open_a = close_a * 0.99
            high_a = max(open_a, close_a) * 1.02
            low_a = min(open_a, close_a) * 0.98
            vol_a = int(900_000 + idx * 30_000)
            amount_a = close_a * vol_a
            change_a = close_a - prev_close_a
            pct_chg_a = ((close_a - prev_close_a) / max(prev_close_a, 1e-9)) * 100.0
            records.append(
                (
                    "000001.SZ",
                    "000001",
                    trade_date,
                    open_a,
                    high_a,
                    low_a,
                    close_a,
                    vol_a,
                    amount_a,
                    prev_close_a,
                    change_a,
                    pct_chg_a,
                )
            )
            prev_close_a = close_a

            close_b = 20.0 - 0.12 * idx - (0.6 if idx == len(trade_dates) - 1 else 0.0)
            open_b = close_b * 1.01
            high_b = max(open_b, close_b) * 1.01
            low_b = min(open_b, close_b) * 0.98
            vol_b = int(max(250_000, 1_100_000 - idx * 20_000))
            amount_b = close_b * vol_b
            change_b = close_b - prev_close_b
            pct_chg_b = ((close_b - prev_close_b) / max(prev_close_b, 1e-9)) * 100.0
            records.append(
                (
                    "000002.SZ",
                    "000002",
                    trade_date,
                    open_b,
                    high_b,
                    low_b,
                    close_b,
                    vol_b,
                    amount_b,
                    prev_close_b,
                    change_b,
                    pct_chg_b,
                )
            )
            prev_close_b = close_b

        connection.executemany(
            "INSERT INTO raw_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            records,
        )

    return target_date


def test_pas_score_not_collapsed_to_constant(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    trade_date = _seed_raw_daily(db_path)

    result = run_pas_daily(trade_date=trade_date, config=config)

    assert result.count == 2
    assert result.frame["pas_score"].round(4).nunique() > 1
    assert not (result.frame["pas_score"].round(4) == 50.0).all()
    assert result.factor_intermediate_sample_path.exists()
