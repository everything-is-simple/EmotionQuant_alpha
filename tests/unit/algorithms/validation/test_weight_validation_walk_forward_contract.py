from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.validation.weight"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, trade_date: str) -> tuple[int, int]:
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
    run_mss_scoring(trade_date=trade_date, config=config)
    irs_result = run_irs_daily(trade_date=trade_date, config=config)
    pas_result = run_pas_daily(trade_date=trade_date, config=config)
    return (irs_result.count, pas_result.count)


def test_validation_weight_walk_forward_contract(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    irs_count, pas_count = _prepare_inputs(config, trade_date)

    result = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=irs_count,
        pas_count=pas_count,
        mss_exists=True,
    )

    assert result.weight_report_sample_path.exists()
    assert result.weight_plan_sample_path.exists()
    assert result.run_manifest_sample_path.exists()
    assert result.selected_weight_plan in {"vp_balanced_v1", "vp_candidate_v1", ""}

    required_columns = {
        "plan_id",
        "window_group",
        "expected_return",
        "max_drawdown",
        "sharpe",
        "tradability_score",
        "gate",
        "contract_version",
    }
    assert required_columns <= set(result.weight_report_frame.columns)
    assert set(result.weight_report_frame["gate"].unique().tolist()) <= {"PASS", "WARN", "FAIL"}

    payload = json.loads(result.run_manifest_sample_path.read_text(encoding="utf-8"))
    assert payload["trade_date"] == trade_date
    assert payload["final_gate"] in {"PASS", "WARN", "FAIL"}

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        weight_report_count = connection.execute(
            "SELECT COUNT(*) FROM validation_weight_report WHERE trade_date=?",
            [trade_date],
        ).fetchone()[0]
        run_manifest_count = connection.execute(
            "SELECT COUNT(*) FROM validation_run_manifest WHERE trade_date=?",
            [trade_date],
        ).fetchone()[0]
        plan_row = connection.execute(
            "SELECT plan_id, w_mss, w_irs, w_pas FROM validation_weight_plan WHERE trade_date=?",
            [trade_date],
        ).fetchone()

    assert int(weight_report_count) > 0
    assert int(run_manifest_count) > 0
    assert plan_row is not None
    assert float(plan_row[1]) > 0.0
    assert float(plan_row[2]) > 0.0
    assert float(plan_row[3]) > 0.0
