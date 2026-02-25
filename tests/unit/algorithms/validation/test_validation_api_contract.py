from __future__ import annotations

from pathlib import Path

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import evaluate_candidate, validate_factor
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.validation.api"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, trade_date: str) -> None:
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
    run_irs_daily(trade_date=trade_date, config=config)
    run_pas_daily(trade_date=trade_date, config=config)


def test_validate_factor_api_contract(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_inputs(config, trade_date)

    result = validate_factor(
        trade_date=trade_date,
        config=config,
    )
    assert result.count > 0
    assert result.final_gate in {"PASS", "WARN", "FAIL"}
    assert result.factor_report_sample_path.exists()
    assert {"factor_name", "ic", "rank_ic", "icir", "gate"} <= set(result.frame.columns)

    single_factor = validate_factor(
        trade_date=trade_date,
        config=config,
        factor_name="mss_future_returns_alignment",
    )
    assert single_factor.count == 1
    assert set(single_factor.frame["factor_name"].tolist()) == {"mss_future_returns_alignment"}


def test_evaluate_candidate_api_contract(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_inputs(config, trade_date)

    result = evaluate_candidate(
        trade_date=trade_date,
        config=config,
    )
    assert result.plan_id == "vp_candidate_v1"
    assert result.count > 0
    assert result.gate in {"PASS", "WARN", "FAIL"}
    assert result.weight_report_sample_path.exists()
    assert result.weight_plan_sample_path.exists()
    assert set(result.frame["plan_id"].tolist()) == {"vp_candidate_v1"}
    assert result.selected_weight_plan in {"", "vp_balanced_v1", "vp_candidate_v1"}
