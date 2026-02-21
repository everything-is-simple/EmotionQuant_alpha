from __future__ import annotations

from pathlib import Path

from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.mss.probe import run_mss_probe
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3d.probe"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_s3d_mss_probe_supports_future_returns_series_source(tmp_path: Path) -> None:
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
        "20260218",
        "20260219",
    ]
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

    artifacts_dir = tmp_path / "artifacts" / "spiral-s3d" / f"{trade_dates[0]}_{trade_dates[-1]}"
    result = run_mss_probe(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        config=config,
        return_series_source="future_returns",
        artifacts_dir=artifacts_dir,
    )
    assert result.return_series_source == "future_returns"
    assert result.probe_report_path.exists()
    assert result.gate_report_path.exists()
    assert result.consumption_case_path.exists()
    content = result.probe_report_path.read_text(encoding="utf-8")
    assert "return_series_source: future_returns" in content
