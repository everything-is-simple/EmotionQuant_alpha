"""IC/ICIR 校准基线契约测试。

验证：
- calibrate_ic_baseline() 可独立调用
- 产出 JSON 校准报告且可审计
- 样本充足时产出 IC/ICIR 数值
- 样本不足时降级为 WARN
- 报告字段完整性
"""
from __future__ import annotations

import json
from pathlib import Path

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.calibration import CalibrationResult, calibrate_ic_baseline
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.calibration"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_multi_day_inputs(config: Config, dates: list[str]) -> None:
    """准备多日数据以产生足够样本量。"""
    for trade_date in dates:
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


def test_calibration_baseline_produces_report(tmp_path: Path) -> None:
    """校准基线可执行且产出 JSON 报告文件。"""
    config = _build_config(tmp_path)
    dates = [
        "20260102", "20260105", "20260106", "20260107", "20260108",
        "20260109", "20260112", "20260113",
    ]
    _prepare_multi_day_inputs(config, dates)

    artifacts_dir = tmp_path / "calibration_artifacts"
    result = calibrate_ic_baseline(
        trade_date="20260113",
        config=config,
        lookback_days=60,
        artifacts_dir=artifacts_dir,
    )

    assert isinstance(result, CalibrationResult)
    assert result.report_path.exists()
    assert result.return_source in {"real_pct_chg", "close_derived"}
    assert result.calibration_gate in {"PASS", "WARN", "FAIL"}
    assert result.tolerance_ic == 0.02
    assert result.tolerance_icir == 0.10

    # 验证 JSON 报告内容完整
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    required_fields = {
        "trade_date", "lookback_days", "sample_count", "return_source",
        "ic_mean", "ic_std", "icir", "rank_ic_mean", "rank_ic_std",
        "rank_icir", "tolerance_ic", "tolerance_icir",
        "calibration_gate", "contract_version", "created_at",
    }
    assert required_fields <= set(report.keys())
    assert report["contract_version"] == "nc-v1"
    assert report["return_source"] in {"real_pct_chg", "close_derived"}


def test_calibration_baseline_cold_start_warn(tmp_path: Path) -> None:
    """样本不足时校准应返回 WARN 而非硬失败。"""
    config = _build_config(tmp_path)
    # 仅准备 1 天数据
    _prepare_multi_day_inputs(config, ["20260212"])

    artifacts_dir = tmp_path / "calibration_cold"
    result = calibrate_ic_baseline(
        trade_date="20260212",
        config=config,
        lookback_days=60,
        artifacts_dir=artifacts_dir,
    )

    assert result.calibration_gate == "WARN"
    assert result.sample_count < 5
    assert result.report_path.exists()


def test_calibration_baseline_no_database(tmp_path: Path) -> None:
    """数据库不存在时校准应返回 WARN。"""
    config = _build_config(tmp_path)

    artifacts_dir = tmp_path / "calibration_nodb"
    result = calibrate_ic_baseline(
        trade_date="20260212",
        config=config,
        lookback_days=60,
        artifacts_dir=artifacts_dir,
    )

    assert result.calibration_gate == "WARN"
    assert result.sample_count == 0
    assert result.report_path.exists()
