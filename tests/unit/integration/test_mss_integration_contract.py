from __future__ import annotations

from pathlib import Path

from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.mss.probe import run_mss_probe
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.integration.mss_consumer import REQUIRED_MSS_FIELDS, load_mss_panorama_for_integration


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s1b.integration"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_mss_history(config: Config, trade_dates: list[str]) -> None:
    for trade_date in trade_dates:
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


def test_mss_output_is_consumable_by_integration_probe(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = [
        "20260210",
        "20260211",
        "20260212",
        "20260213",
        "20260214",
        "20260215",
        "20260216",
        "20260217",
    ]
    _prepare_mss_history(config, trade_dates)

    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    frame = load_mss_panorama_for_integration(
        database_path=database_path,
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
    )
    assert not frame.empty
    assert REQUIRED_MSS_FIELDS <= set(frame.columns)

    probe = run_mss_probe(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        config=config,
    )
    assert probe.has_error is False
    assert probe.probe_report_path.exists()
    assert probe.consumption_case_path.exists()

    report_text = probe.probe_report_path.read_text(encoding="utf-8")
    assert "top_bottom_spread_5d" in report_text

    case_text = probe.consumption_case_path.read_text(encoding="utf-8")
    assert "consumed_fields: mss_score,mss_temperature,mss_cycle,mss_trend,trade_date" in case_text
    assert "consumption_conclusion:" in case_text
