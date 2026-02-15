from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2b.integration"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_s2b_inputs(config: Config, trade_date: str) -> None:
    run_l1_collection(
        trade_date=trade_date,
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )
    run_l2_snapshot(
        trade_date=trade_date,
        source="tushare",
        config=config,
    )
    run_mss_scoring(
        trade_date=trade_date,
        config=config,
    )
    s2a = run_recommendation(
        trade_date=trade_date,
        mode="mss_irs_pas",
        with_validation=True,
        config=config,
    )
    assert s2a.has_error is False


def test_s2b_generates_integrated_recommendation_with_execution_fields(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_s2b_inputs(config, trade_date)

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert result.has_error is False
    assert result.integrated_count > 0
    assert result.quality_gate_status in {"PASS", "WARN"}
    assert result.integrated_sample_path.exists()
    assert result.quality_gate_report_path.exists()
    assert result.go_nogo_decision_path.exists()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT contract_version, risk_reward_ratio, t1_restriction_hit, "
            "limit_guard_result, session_guard_result "
            "FROM integrated_recommendation WHERE trade_date=? LIMIT 1",
            [trade_date],
        ).fetchone()
        quality_row = connection.execute(
            "SELECT status FROM quality_gate_report WHERE trade_date=? LIMIT 1",
            [trade_date],
        ).fetchone()

    assert row is not None
    assert row[0] == "nc-v1"
    assert float(row[1]) >= 1.0
    assert row[2] in (False, 0)
    assert str(row[3]) != ""
    assert str(row[4]) != ""
    assert quality_row is not None
    assert quality_row[0] in ("PASS", "WARN")
