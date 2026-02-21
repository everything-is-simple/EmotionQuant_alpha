from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.readiness.persistence"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_data_readiness_outputs_persist_after_l1_and_l2(tmp_path: Path) -> None:
    trade_date = "20260215"
    config = _build_config(tmp_path)

    l1_result = run_l1_collection(
        trade_date=trade_date,
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )
    assert l1_result.has_error is False

    l2_result = run_l2_snapshot(
        trade_date=trade_date,
        source="tushare",
        config=config,
        strict_sw31=True,
    )
    assert l2_result.has_error is False

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        table_names = {
            str(row[0])
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name IN ('system_config', 'data_quality_report', 'data_readiness_gate')"
            ).fetchall()
        }
        assert {"system_config", "data_quality_report", "data_readiness_gate"} <= table_names

        config_keys = {
            str(row[0])
            for row in connection.execute(
                "SELECT config_key FROM system_config "
                "WHERE config_key IN ('flat_threshold', 'min_coverage_ratio', 'stale_hard_limit_days')"
            ).fetchall()
        }
        assert {"flat_threshold", "min_coverage_ratio", "stale_hard_limit_days"} <= config_keys

        gate_row = connection.execute(
            "SELECT status, is_ready, coverage_ratio FROM data_readiness_gate WHERE trade_date = ?",
            [trade_date],
        ).fetchone()
        assert gate_row is not None
        assert str(gate_row[0]) in {"ready", "degraded", "blocked"}
        assert isinstance(bool(gate_row[1]), bool)
        assert float(gate_row[2]) >= 0.0

        check_items = {
            str(row[0])
            for row in connection.execute(
                "SELECT check_item FROM data_quality_report WHERE trade_date = ?",
                [trade_date],
            ).fetchall()
        }
        assert "l1_readiness_gate" in check_items
        assert "l2_readiness_gate" in check_items
