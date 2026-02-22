from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.irs.pipeline import run_irs_daily
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2a.irs"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_s2a_generates_irs_industry_daily(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    run_l1_collection(
        trade_date="20260212",
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )
    run_l2_snapshot(
        trade_date="20260212",
        source="tushare",
        config=config,
    )

    result = run_irs_daily(
        trade_date="20260212",
        config=config,
    )
    assert result.count > 0

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM irs_industry_daily WHERE trade_date='20260212'"
        ).fetchone()[0]
        fields = set(
            connection.execute("SELECT * FROM irs_industry_daily LIMIT 1")
            .df()
            .columns.to_list()
        )

    assert count > 0
    assert {"irs_score", "rotation_status", "recommendation", "contract_version"} <= fields

