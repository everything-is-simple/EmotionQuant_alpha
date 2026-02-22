from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.pas.pipeline import run_pas_daily
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2a.pas"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_s2a_generates_stock_pas_daily(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    run_l1_collection(
        trade_date="20260212",
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )
    result = run_pas_daily(
        trade_date="20260212",
        config=config,
    )
    assert result.count > 0

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM stock_pas_daily WHERE trade_date='20260212'"
        ).fetchone()[0]
        fields = set(
            connection.execute("SELECT * FROM stock_pas_daily LIMIT 1")
            .df()
            .columns.to_list()
        )

    assert count > 0
    assert {"pas_score", "pas_direction", "risk_reward_ratio", "contract_version"} <= fields

