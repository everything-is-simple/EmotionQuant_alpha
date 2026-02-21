from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s1a"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_s1a_generates_mss_panorama_and_artifacts(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    run_l1_collection(
        trade_date="20260215",
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )
    run_l2_snapshot(
        trade_date="20260215",
        source="tushare",
        config=config,
    )

    result = run_mss_scoring(
        trade_date="20260215",
        config=config,
    )
    assert result.has_error is False
    assert result.mss_panorama_count > 0
    assert result.sample_path.exists()
    assert result.factor_trace_path.exists()
    assert result.factor_intermediate_sample_path.exists()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM mss_panorama WHERE trade_date = '20260215'"
        ).fetchone()[0]
        fields = set(
            connection.execute("SELECT * FROM mss_panorama LIMIT 1")
            .df()
            .columns.to_list()
        )

    assert rows > 0
    assert {"mss_score", "mss_temperature", "mss_cycle", "mss_rank", "mss_percentile"} <= fields
