from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.quality.sync_s2c_release_artifacts import sync_s2c_release_artifacts


def _prepare_root(tmp_path: Path, trade_date: str) -> tuple[Path, Path]:
    release_dir = tmp_path / "artifacts" / "spiral-s2c" / trade_date
    spec_dir = tmp_path / "Governance" / "specs" / "spiral-s2c"
    release_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)
    return release_dir, spec_dir


def test_sync_s2c_release_artifacts_success(tmp_path: Path) -> None:
    trade_date = "20260218"
    release_dir, spec_dir = _prepare_root(tmp_path, trade_date)

    (release_dir / "quality_gate_report.md").write_text(
        "# S2 Quality Gate Report\n\n"
        f"- trade_date: {trade_date}\n"
        "- status: PASS\n"
        "- validation_gate: PASS\n"
        "- integrated_count: 1\n"
        "- rr_filtered_count: 0\n"
        "- message: all_checks_passed\n",
        encoding="utf-8",
    )
    (release_dir / "s2_go_nogo_decision.md").write_text(
        "# S2 Go/No-Go Decision\n\n"
        f"- trade_date: {trade_date}\n"
        "- decision: GO\n"
        "- quality_gate_status: PASS\n"
        "- reason: all_checks_passed\n",
        encoding="utf-8",
    )
    pd.DataFrame.from_records([{"trade_date": trade_date, "stock_code": "000001"}]).to_parquet(
        release_dir / "integrated_recommendation_sample.parquet",
        index=False,
    )
    pd.DataFrame.from_records([{"trade_date": trade_date, "mss_score": 62.5}]).to_parquet(
        release_dir / "mss_factor_intermediate_sample.parquet",
        index=False,
    )
    pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "final_gate": "PASS",
                "selected_weight_plan": "vp_balanced_v1",
            }
        ]
    ).to_parquet(
        release_dir / "validation_gate_decision_sample.parquet",
        index=False,
    )
    pd.DataFrame.from_records([{"trade_date": trade_date, "plan_id": "vp_balanced_v1"}]).to_parquet(
        release_dir / "validation_weight_plan_sample.parquet",
        index=False,
    )

    exit_code = sync_s2c_release_artifacts(trade_date=trade_date, root=tmp_path)
    assert exit_code == 0
    assert (spec_dir / "quality_gate_report.md").exists()
    assert (spec_dir / "s2_go_nogo_decision.md").exists()
    assert (spec_dir / "integrated_recommendation_sample.parquet").exists()
    assert (spec_dir / "mss_factor_intermediate_sample.parquet").exists()
    assert (spec_dir / "validation_gate_decision_sample.parquet").exists()
    assert (spec_dir / "validation_weight_plan_sample.parquet").exists()


def test_sync_s2c_release_artifacts_blocks_fail_status(tmp_path: Path) -> None:
    trade_date = "20260218"
    release_dir, spec_dir = _prepare_root(tmp_path, trade_date)

    (release_dir / "quality_gate_report.md").write_text(
        "# S2 Quality Gate Report\n\n"
        f"- trade_date: {trade_date}\n"
        "- status: FAIL\n"
        "- validation_gate: PASS\n"
        "- integrated_count: 0\n"
        "- rr_filtered_count: 0\n"
        "- message: selected_weight_plan_missing\n",
        encoding="utf-8",
    )
    (release_dir / "s2_go_nogo_decision.md").write_text(
        "# S2 Go/No-Go Decision\n\n"
        f"- trade_date: {trade_date}\n"
        "- decision: NO_GO\n"
        "- quality_gate_status: FAIL\n"
        "- reason: selected_weight_plan_missing\n",
        encoding="utf-8",
    )
    pd.DataFrame.from_records([]).to_parquet(
        release_dir / "integrated_recommendation_sample.parquet",
        index=False,
    )
    pd.DataFrame.from_records([{"trade_date": trade_date, "mss_score": 62.5}]).to_parquet(
        release_dir / "mss_factor_intermediate_sample.parquet",
        index=False,
    )
    pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "final_gate": "FAIL",
                "selected_weight_plan": "",
            }
        ]
    ).to_parquet(
        release_dir / "validation_gate_decision_sample.parquet",
        index=False,
    )

    exit_code = sync_s2c_release_artifacts(trade_date=trade_date, root=tmp_path)
    assert exit_code == 1
    assert not (spec_dir / "quality_gate_report.md").exists()
