from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s0c"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_s0c_generates_market_and_industry_snapshots(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    run_l1_collection(
        trade_date="20260215",
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )

    result = run_l2_snapshot(
        trade_date="20260215",
        source="tushare",
        config=config,
    )

    assert result.has_error is False
    assert result.market_snapshot_count > 0
    assert result.industry_snapshot_count > 0

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        market_count = connection.execute(
            "SELECT COUNT(*) FROM market_snapshot WHERE trade_date='20260215'"
        ).fetchone()[0]
        fields = set(
            connection.execute("SELECT * FROM market_snapshot LIMIT 1")
            .df()
            .columns.to_list()
        )

    assert market_count > 0
    assert {"data_quality", "stale_days", "source_trade_date"} <= fields
    assert (result.artifacts_dir / "market_snapshot_sample.parquet").exists()
    assert (result.artifacts_dir / "industry_snapshot_sample.parquet").exists()
    assert (result.artifacts_dir / "s0_canary_report.md").exists()
