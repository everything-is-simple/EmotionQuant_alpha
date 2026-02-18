from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.data.repositories.trade_calendars import TradeCalendarsRepository


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.repo.schema"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_repository_auto_adds_new_columns_on_insert(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    repository = TradeCalendarsRepository(config)

    rows_v1 = [
        {
            "exchange": "SSE",
            "trade_date": "20260213",
            "is_open": 1,
            "pretrade_date": "20260212",
        }
    ]
    rows_v2 = [
        {
            "exchange": "SSE",
            "trade_date": "20260214",
            "is_open": 0,
            "pretrade_date": "20260213",
            "cal_date": "20260214",
        }
    ]

    assert repository.save_to_database(rows_v1) == 1
    assert repository.save_to_database(rows_v2) == 1

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        total_count = connection.execute(
            "SELECT COUNT(*) FROM raw_trade_cal"
        ).fetchone()[0]
        cal_date_count = connection.execute(
            "SELECT COUNT(*) FROM raw_trade_cal WHERE cal_date IS NOT NULL"
        ).fetchone()[0]

    assert int(total_count) == 2
    assert int(cal_date_count) == 1
