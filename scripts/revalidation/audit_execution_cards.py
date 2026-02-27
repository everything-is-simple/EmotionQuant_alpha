"""全实现卡（S0A-S4BR）代码级重验审计脚本。

目标：
1. 按执行卡顺序执行 run/test（含修复子圈），不依赖文档推断。
2. 每步产生日志，保留 stdout/stderr/耗时/退出码，支持事后追溯。
3. 生成按卡片聚合的通过/卡住结论，供路线图与执行卡回填。

说明：
- 本脚本做“代码级可执行性与测试可复现性”审计。
- 业务价值判定（GO/NO_GO）仍需结合看板与阻断矩阵。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Step:
    """单个可执行步骤。"""

    card: str
    phase: str  # run / test / gate
    name: str
    display_command: str
    cmd: tuple[str, ...]


def _run_step(step: Step, project_root: Path, logs_dir: Path, timeout_seconds: int) -> dict[str, object]:
    """执行步骤并写入独立日志。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = step.name.replace(" ", "_").replace("/", "_")
    log_path = logs_dir / f"{step.card.lower()}_{step.phase}_{safe_name}_{ts}.log"

    started = datetime.now()
    timed_out = False
    env = dict(os.environ)
    # 兼容本地未安装可编辑包场景：确保 `eq` 入口可从仓库根目录导入 `src`。
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    project_path = str(project_root)
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{project_path};{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = project_path

    try:
        proc = subprocess.run(
            list(step.cmd),
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout_seconds,
        )
        rc = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = 124
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[timeout] step exceeded {timeout_seconds}s"

    ended = datetime.now()

    content = [
        f"# card={step.card} phase={step.phase} name={step.name}",
        f"# display_command={step.display_command}",
        f"# command={' '.join(step.cmd)}",
        f"# started={started.isoformat()}",
        f"# ended={ended.isoformat()}",
        f"# returncode={rc}",
        f"# timed_out={timed_out}",
        "\n## stdout\n",
        stdout,
        "\n## stderr\n",
        stderr,
    ]
    log_path.write_text("\n".join(content), encoding="utf-8")

    return {
        "card": step.card,
        "phase": step.phase,
        "name": step.name,
        "display_command": step.display_command,
        "command": list(step.cmd),
        "returncode": rc,
        "timed_out": timed_out,
        "started": started.isoformat(),
        "ended": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 3),
        "log_path": str(log_path),
    }


def _py_main(*args: str) -> tuple[str, ...]:
    """统一通过主入口执行，避免 eq 可执行名差异导致假失败。"""
    return ("python", "-m", "src.pipeline.main", *args)


def _pytest(*args: str) -> tuple[str, ...]:
    return ("pytest", *args)


def build_steps() -> list[Step]:
    """构建 S0A-S4BR 全实现卡审计步骤。"""
    td = "20241220"
    start_long = "20200102"
    end_long = "20241231"
    start_mid = "20240101"
    end_mid = "20241220"
    fetch_start = "20241220"
    fetch_end = "20241220"

    steps: list[Step] = [
        # S0A
        Step("S0A", "run", "cli_help_main", "python -m src.pipeline.main --help", _py_main("--help")),
        Step("S0A", "run", "cli_help_eq", "eq --help", ("eq", "--help")),
        Step("S0A", "run", "run_dry", "eq --env-file .env --print-config run --date 20260215 --dry-run", _py_main("--env-file", ".env", "--print-config", "run", "--date", "20260215", "--dry-run")),
        Step("S0A", "test", "cli_entrypoint", "pytest tests/unit/pipeline/test_cli_entrypoint.py -q", _pytest("tests/unit/pipeline/test_cli_entrypoint.py", "-q")),
        Step("S0A", "test", "config_defaults", "pytest tests/unit/config/test_config_defaults.py -q", _pytest("tests/unit/config/test_config_defaults.py", "-q")),
        Step("S0A", "test", "env_docs_alignment", "pytest tests/unit/config/test_env_docs_alignment.py -q", _pytest("tests/unit/config/test_env_docs_alignment.py", "-q")),
        # S0B
        Step("S0B", "run", "l1_only", f"eq run --date {td} --source tushare --l1-only", _py_main("run", "--date", td, "--source", "tushare", "--l1-only")),
        Step("S0B", "test", "fetcher_contract", "pytest tests/unit/data/test_fetcher_contract.py -q", _pytest("tests/unit/data/test_fetcher_contract.py", "-q")),
        Step("S0B", "test", "l1_repository_contract", "pytest tests/unit/data/test_l1_repository_contract.py -q", _pytest("tests/unit/data/test_l1_repository_contract.py", "-q")),
        Step("S0B", "test", "readiness_contract", "pytest tests/unit/data/test_data_readiness_persistence_contract.py -q", _pytest("tests/unit/data/test_data_readiness_persistence_contract.py", "-q")),
        # S0C
        Step("S0C", "run", "to_l2_sw31", f"eq run --date {td} --source tushare --to-l2 --strict-sw31", _py_main("run", "--date", td, "--source", "tushare", "--to-l2", "--strict-sw31")),
        Step("S0C", "test", "snapshot_contract", "pytest tests/unit/data/test_snapshot_contract.py -q", _pytest("tests/unit/data/test_snapshot_contract.py", "-q")),
        Step("S0C", "test", "s0_canary", "pytest tests/unit/data/test_s0_canary.py -q", _pytest("tests/unit/data/test_s0_canary.py", "-q")),
        Step("S0C", "test", "sw31_contract", "pytest tests/unit/data/test_industry_snapshot_sw31_contract.py -q", _pytest("tests/unit/data/test_industry_snapshot_sw31_contract.py", "-q")),
        Step("S0C", "test", "readiness_contract", "pytest tests/unit/data/test_data_readiness_persistence_contract.py -q", _pytest("tests/unit/data/test_data_readiness_persistence_contract.py", "-q")),
        Step("S0C", "test", "flat_threshold", "pytest tests/unit/data/test_flat_threshold_config_contract.py -q", _pytest("tests/unit/data/test_flat_threshold_config_contract.py", "-q")),
        # S1A
        Step("S1A", "run", "mss_daily", f"eq mss --date {td}", _py_main("mss", "--date", td)),
        Step("S1A", "test", "mss_contract", "pytest tests/unit/algorithms/mss/test_mss_contract.py -q", _pytest("tests/unit/algorithms/mss/test_mss_contract.py", "-q")),
        Step("S1A", "test", "mss_engine", "pytest tests/unit/algorithms/mss/test_mss_engine.py -q", _pytest("tests/unit/algorithms/mss/test_mss_engine.py", "-q")),
        Step("S1A", "test", "mss_semantics", "pytest tests/unit/algorithms/mss/test_mss_full_semantics_contract.py -q", _pytest("tests/unit/algorithms/mss/test_mss_full_semantics_contract.py", "-q")),
        # S1B
        Step("S1B", "run", "mss_probe", f"eq mss-probe --start {start_long} --end {end_long}", _py_main("mss-probe", "--start", start_long, "--end", end_long)),
        Step("S1B", "test", "mss_probe_contract", "pytest tests/unit/algorithms/mss/test_mss_probe_contract.py -q", _pytest("tests/unit/algorithms/mss/test_mss_probe_contract.py", "-q")),
        Step("S1B", "test", "mss_integration_contract", "pytest tests/unit/integration/test_mss_integration_contract.py -q", _pytest("tests/unit/integration/test_mss_integration_contract.py", "-q")),
        # S2A
        Step("S2A", "run", "recommend_mss_irs_pas", f"eq recommend --date {td} --mode mss_irs_pas --with-validation", _py_main("recommend", "--date", td, "--mode", "mss_irs_pas", "--with-validation")),
        Step("S2A", "test", "irs_contract", "pytest tests/unit/algorithms/irs/test_irs_contract.py -q", _pytest("tests/unit/algorithms/irs/test_irs_contract.py", "-q")),
        Step("S2A", "test", "pas_contract", "pytest tests/unit/algorithms/pas/test_pas_contract.py -q", _pytest("tests/unit/algorithms/pas/test_pas_contract.py", "-q")),
        Step("S2A", "test", "validation_gate", "pytest tests/unit/integration/test_validation_gate_contract.py -q", _pytest("tests/unit/integration/test_validation_gate_contract.py", "-q")),
        Step("S2A", "test", "weight_bridge", "pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q", _pytest("tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py", "-q")),
        # S2B
        Step("S2B", "run", "integrated_top_down", f"eq recommend --date {td} --mode integrated --integration-mode top_down", _py_main("recommend", "--date", td, "--mode", "integrated", "--integration-mode", "top_down")),
        Step("S2B", "run", "integrated_bottom_up", f"eq recommend --date {td} --mode integrated --integration-mode bottom_up", _py_main("recommend", "--date", td, "--mode", "integrated", "--integration-mode", "bottom_up")),
        Step("S2B", "run", "integrated_dual_verify", f"eq recommend --date {td} --mode integrated --integration-mode dual_verify", _py_main("recommend", "--date", td, "--mode", "integrated", "--integration-mode", "dual_verify")),
        Step("S2B", "run", "integrated_complementary", f"eq recommend --date {td} --mode integrated --integration-mode complementary", _py_main("recommend", "--date", td, "--mode", "integrated", "--integration-mode", "complementary")),
        Step("S2B", "test", "integration_contract", "pytest tests/unit/integration/test_integration_contract.py -q", _pytest("tests/unit/integration/test_integration_contract.py", "-q")),
        Step("S2B", "test", "quality_gate_contract", "pytest tests/unit/integration/test_quality_gate_contract.py -q", _pytest("tests/unit/integration/test_quality_gate_contract.py", "-q")),
        Step("S2B", "test", "cli_entrypoint", "pytest tests/unit/pipeline/test_cli_entrypoint.py -q", _pytest("tests/unit/pipeline/test_cli_entrypoint.py", "-q")),
        # S2C
        Step("S2C", "run", "integrated_bridge_release", f"eq recommend --date {td} --mode integrated --with-validation-bridge --evidence-lane release", _py_main("recommend", "--date", td, "--mode", "integrated", "--with-validation-bridge", "--evidence-lane", "release")),
        Step("S2C", "run", "quality_contracts_governance", "python -m scripts.quality.local_quality_check --contracts --governance", ("python", "-m", "scripts.quality.local_quality_check", "--contracts", "--governance")),
        Step("S2C", "test", "mss_semantics", "pytest tests/unit/algorithms/mss/test_mss_full_semantics_contract.py -q", _pytest("tests/unit/algorithms/mss/test_mss_full_semantics_contract.py", "-q")),
        Step("S2C", "test", "irs_semantics", "pytest tests/unit/algorithms/irs/test_irs_full_semantics_contract.py -q", _pytest("tests/unit/algorithms/irs/test_irs_full_semantics_contract.py", "-q")),
        Step("S2C", "test", "pas_semantics", "pytest tests/unit/algorithms/pas/test_pas_full_semantics_contract.py -q", _pytest("tests/unit/algorithms/pas/test_pas_full_semantics_contract.py", "-q")),
        Step("S2C", "test", "factor_metrics", "pytest tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py -q", _pytest("tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py", "-q")),
        Step("S2C", "test", "weight_wfa", "pytest tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py -q", _pytest("tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py", "-q")),
        Step("S2C", "test", "weight_bridge", "pytest tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py -q", _pytest("tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py", "-q")),
        Step("S2C", "test", "validation_bridge", "pytest tests/unit/integration/test_validation_weight_plan_bridge.py -q", _pytest("tests/unit/integration/test_validation_weight_plan_bridge.py", "-q")),
        Step("S2C", "test", "semantics_regression", "pytest tests/unit/integration/test_algorithm_semantics_regression.py -q", _pytest("tests/unit/integration/test_algorithm_semantics_regression.py", "-q")),
        Step("S2C", "test", "integration_contract", "pytest tests/unit/integration/test_integration_contract.py -q", _pytest("tests/unit/integration/test_integration_contract.py", "-q")),
        # S2R
        Step("S2R", "run", "repair_s2r_default", f"eq recommend --date {td} --mode integrated --repair s2r", _py_main("recommend", "--date", td, "--mode", "integrated", "--repair", "s2r")),
        Step("S2R", "run", "repair_s2r_top_down", f"eq recommend --date {td} --mode integrated --integration-mode top_down --repair s2r", _py_main("recommend", "--date", td, "--mode", "integrated", "--integration-mode", "top_down", "--repair", "s2r")),
        Step("S2R", "test", "validation_gate", "pytest tests/unit/integration/test_validation_gate_contract.py -q", _pytest("tests/unit/integration/test_validation_gate_contract.py", "-q")),
        Step("S2R", "test", "quality_gate", "pytest tests/unit/integration/test_quality_gate_contract.py -q", _pytest("tests/unit/integration/test_quality_gate_contract.py", "-q")),
        # S3A
        Step("S3A", "run", "fetch_batch", f"eq fetch-batch --start {fetch_start} --end {fetch_end} --batch-size 30 --workers 3", _py_main("fetch-batch", "--start", fetch_start, "--end", fetch_end, "--batch-size", "30", "--workers", "3")),
        Step("S3A", "run", "fetch_status", "eq fetch-status", _py_main("fetch-status")),
        Step("S3A", "run", "fetch_retry", "eq fetch-retry", _py_main("fetch-retry")),
        Step("S3A", "test", "fetch_batch_contract", "pytest tests/unit/data/test_fetch_batch_contract.py -q", _pytest("tests/unit/data/test_fetch_batch_contract.py", "-q")),
        Step("S3A", "test", "fetch_resume_contract", "pytest tests/unit/data/test_fetch_resume_contract.py -q", _pytest("tests/unit/data/test_fetch_resume_contract.py", "-q")),
        Step("S3A", "test", "fetch_retry_contract", "pytest tests/unit/data/test_fetch_retry_contract.py -q", _pytest("tests/unit/data/test_fetch_retry_contract.py", "-q")),
        # S3
        Step("S3", "run", "backtest_local_vectorized", f"eq backtest --engine local_vectorized --start {start_mid} --end {end_mid}", _py_main("backtest", "--engine", "local_vectorized", "--start", start_mid, "--end", end_mid)),
        Step("S3", "test", "backtest_contract", "pytest tests/unit/backtest/test_backtest_contract.py -q", _pytest("tests/unit/backtest/test_backtest_contract.py", "-q")),
        Step("S3", "test", "bridge_contract", "pytest tests/unit/backtest/test_validation_integration_bridge.py -q", _pytest("tests/unit/backtest/test_validation_integration_bridge.py", "-q")),
        Step("S3", "test", "reproducibility", "pytest tests/unit/backtest/test_backtest_reproducibility.py -q", _pytest("tests/unit/backtest/test_backtest_reproducibility.py", "-q")),
        Step("S3", "test", "coverage_gate", "pytest tests/unit/backtest/test_backtest_core_algorithm_coverage_gate.py -q", _pytest("tests/unit/backtest/test_backtest_core_algorithm_coverage_gate.py", "-q")),
        # S3R
        Step("S3R", "run", "repair_s3r", f"eq backtest --engine local_vectorized --start {start_mid} --end {end_mid} --repair s3r", _py_main("backtest", "--engine", "local_vectorized", "--start", start_mid, "--end", end_mid, "--repair", "s3r")),
        Step("S3R", "test", "backtest_contract", "pytest tests/unit/backtest/test_backtest_contract.py -q", _pytest("tests/unit/backtest/test_backtest_contract.py", "-q")),
        Step("S3R", "test", "reproducibility", "pytest tests/unit/backtest/test_backtest_reproducibility.py -q", _pytest("tests/unit/backtest/test_backtest_reproducibility.py", "-q")),
        # S4
        Step("S4", "run", "trade_paper", f"eq trade --mode paper --date {td}", _py_main("trade", "--mode", "paper", "--date", td)),
        Step("S4", "test", "order_contract", "pytest tests/unit/trading/test_order_pipeline_contract.py -q", _pytest("tests/unit/trading/test_order_pipeline_contract.py", "-q")),
        Step("S4", "test", "position_contract", "pytest tests/unit/trading/test_position_lifecycle_contract.py -q", _pytest("tests/unit/trading/test_position_lifecycle_contract.py", "-q")),
        Step("S4", "test", "risk_guard", "pytest tests/unit/trading/test_risk_guard_contract.py -q", _pytest("tests/unit/trading/test_risk_guard_contract.py", "-q")),
        # S3AR
        Step("S3AR", "run", "fetch_batch", f"eq fetch-batch --start {fetch_start} --end {fetch_end} --batch-size 30 --workers 3", _py_main("fetch-batch", "--start", fetch_start, "--end", fetch_end, "--batch-size", "30", "--workers", "3")),
        Step("S3AR", "run", "fetch_status", "eq fetch-status", _py_main("fetch-status")),
        Step("S3AR", "run", "fetch_retry", "eq fetch-retry", _py_main("fetch-retry")),
        Step("S3AR", "run", "check_tushare_dual_tokens", "python scripts/data/check_tushare_dual_tokens.py --env-file .env --channels both", ("python", "scripts/data/check_tushare_dual_tokens.py", "--env-file", ".env", "--channels", "both")),
        Step("S3AR", "run", "bench_tushare_dual_tokens", f"python scripts/data/benchmark_tushare_l1_channels_window.py --env-file .env --start {fetch_start} --end {fetch_end} --channels both", ("python", "scripts/data/benchmark_tushare_l1_channels_window.py", "--env-file", ".env", "--start", fetch_start, "--end", fetch_end, "--channels", "both")),
        Step("S3AR", "test", "fetcher_contract", "pytest tests/unit/data/test_fetcher_contract.py -q", _pytest("tests/unit/data/test_fetcher_contract.py", "-q")),
        Step("S3AR", "test", "fetch_retry_contract", "pytest tests/unit/data/test_fetch_retry_contract.py -q", _pytest("tests/unit/data/test_fetch_retry_contract.py", "-q")),
        Step("S3AR", "test", "config_defaults", "pytest tests/unit/config/test_config_defaults.py -q", _pytest("tests/unit/config/test_config_defaults.py", "-q")),
        # S3B
        Step("S3B", "run", "ab_benchmark", f"eq analysis --start {start_mid} --end {end_mid} --ab-benchmark", _py_main("analysis", "--start", start_mid, "--end", end_mid, "--ab-benchmark")),
        Step("S3B", "run", "deviation", f"eq analysis --date {td} --deviation live-backtest", _py_main("analysis", "--date", td, "--deviation", "live-backtest")),
        Step("S3B", "run", "attribution_summary", f"eq analysis --date {td} --deviation live-backtest --attribution-summary", _py_main("analysis", "--date", td, "--deviation", "live-backtest", "--attribution-summary")),
        Step("S3B", "test", "ab_contract", "pytest tests/unit/analysis/test_ab_benchmark_contract.py -q", _pytest("tests/unit/analysis/test_ab_benchmark_contract.py", "-q")),
        Step("S3B", "test", "deviation_contract", "pytest tests/unit/analysis/test_live_backtest_deviation_contract.py -q", _pytest("tests/unit/analysis/test_live_backtest_deviation_contract.py", "-q")),
        Step("S3B", "test", "attribution_contract", "pytest tests/unit/analysis/test_attribution_summary_contract.py -q", _pytest("tests/unit/analysis/test_attribution_summary_contract.py", "-q")),
        # S3C
        Step("S3C", "run", "to_l2_sw31", f"eq run --date {td} --to-l2 --strict-sw31", _py_main("run", "--date", td, "--to-l2", "--strict-sw31")),
        Step("S3C", "run", "irs_sw31", f"eq irs --date {td} --require-sw31", _py_main("irs", "--date", td, "--require-sw31")),
        Step("S3C", "test", "industry_sw31_contract", "pytest tests/unit/data/test_industry_snapshot_sw31_contract.py -q", _pytest("tests/unit/data/test_industry_snapshot_sw31_contract.py", "-q")),
        Step("S3C", "test", "irs_sw31_contract", "pytest tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py -q", _pytest("tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py", "-q")),
        # S3D
        Step("S3D", "run", "mss_adaptive", f"eq mss --date {td} --threshold-mode adaptive", _py_main("mss", "--date", td, "--threshold-mode", "adaptive")),
        Step("S3D", "run", "mss_probe_future", f"eq mss-probe --start {start_mid} --end {end_mid} --return-series-source future_returns", _py_main("mss-probe", "--start", start_mid, "--end", end_mid, "--return-series-source", "future_returns")),
        Step("S3D", "test", "mss_adaptive_contract", "pytest tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py -q", _pytest("tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py", "-q")),
        Step("S3D", "test", "mss_probe_source_contract", "pytest tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py -q", _pytest("tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py", "-q")),
        # S3E
        Step("S3E", "run", "validation_regime_dual", f"eq validation --trade-date {td} --threshold-mode regime --wfa dual-window", _py_main("validation", "--trade-date", td, "--threshold-mode", "regime", "--wfa", "dual-window")),
        Step("S3E", "run", "validation_manifest", f"eq validation --trade-date {td} --export-run-manifest", _py_main("validation", "--trade-date", td, "--export-run-manifest")),
        Step("S3E", "test", "factor_future_contract", "pytest tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py -q", _pytest("tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py", "-q")),
        Step("S3E", "test", "dual_window_contract", "pytest tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py -q", _pytest("tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py", "-q")),
        Step("S3E", "test", "oos_metrics_contract", "pytest tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py -q", _pytest("tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py", "-q")),
        # S4B
        Step("S4B", "run", "stress_limit_down", f"eq stress --scenario limit_down_chain --date {td}", _py_main("stress", "--scenario", "limit_down_chain", "--date", td)),
        Step("S4B", "run", "stress_liquidity", f"eq stress --scenario liquidity_dryup --date {td}", _py_main("stress", "--scenario", "liquidity_dryup", "--date", td)),
        Step("S4B", "test", "stress_limit_test", "pytest tests/unit/trading/test_stress_limit_down_chain.py -q", _pytest("tests/unit/trading/test_stress_limit_down_chain.py", "-q")),
        Step("S4B", "test", "stress_liquidity_test", "pytest tests/unit/trading/test_stress_liquidity_dryup.py -q", _pytest("tests/unit/trading/test_stress_liquidity_dryup.py", "-q")),
        Step("S4B", "test", "deleveraging_contract", "pytest tests/unit/trading/test_deleveraging_policy_contract.py -q", _pytest("tests/unit/trading/test_deleveraging_policy_contract.py", "-q")),
        # S4BR
        Step("S4BR", "run", "stress_repair_all", f"eq stress --scenario all --date {td} --repair s4br", _py_main("stress", "--scenario", "all", "--date", td, "--repair", "s4br")),
        Step("S4BR", "test", "stress_limit_test", "pytest tests/unit/trading/test_stress_limit_down_chain.py -q", _pytest("tests/unit/trading/test_stress_limit_down_chain.py", "-q")),
        Step("S4BR", "test", "stress_liquidity_test", "pytest tests/unit/trading/test_stress_liquidity_dryup.py -q", _pytest("tests/unit/trading/test_stress_liquidity_dryup.py", "-q")),
        # S4R
        Step("S4R", "run", "trade_repair", f"eq trade --mode paper --date {td} --repair s4r", _py_main("trade", "--mode", "paper", "--date", td, "--repair", "s4r")),
        Step("S4R", "test", "order_contract", "pytest tests/unit/trading/test_order_pipeline_contract.py -q", _pytest("tests/unit/trading/test_order_pipeline_contract.py", "-q")),
        Step("S4R", "test", "risk_guard", "pytest tests/unit/trading/test_risk_guard_contract.py -q", _pytest("tests/unit/trading/test_risk_guard_contract.py", "-q")),
        # 全局附加门禁
        Step("GLOBAL", "gate", "contracts_governance", "python -m scripts.quality.local_quality_check --contracts --governance", ("python", "-m", "scripts.quality.local_quality_check", "--contracts", "--governance")),
    ]

    return steps


def _aggregate_by_card(results: Iterable[dict[str, object]]) -> dict[str, dict[str, object]]:
    """按卡片聚合 run/test/gate 结果，给出通过/卡住判定。"""
    summary: dict[str, dict[str, object]] = {}
    for row in results:
        card = str(row["card"])
        info = summary.setdefault(
            card,
            {
                "card": card,
                "run_steps": 0,
                "test_steps": 0,
                "gate_steps": 0,
                "run_failed": 0,
                "test_failed": 0,
                "gate_failed": 0,
                "failed_steps": [],
            },
        )
        phase = str(row["phase"])
        rc = int(row["returncode"])
        if phase == "run":
            info["run_steps"] += 1
            if rc != 0:
                info["run_failed"] += 1
        elif phase == "test":
            info["test_steps"] += 1
            if rc != 0:
                info["test_failed"] += 1
        else:
            info["gate_steps"] += 1
            if rc != 0:
                info["gate_failed"] += 1

        if rc != 0:
            info["failed_steps"].append(
                {
                    "phase": phase,
                    "name": row["name"],
                    "returncode": rc,
                    "log_path": row["log_path"],
                }
            )

    for info in summary.values():
        blocked = info["run_failed"] > 0 or info["test_failed"] > 0 or info["gate_failed"] > 0
        info["status"] = "blocked" if blocked else "completed"
    return summary


def main(argv: list[str]) -> int:
    timeout_seconds = 1800
    if len(argv) > 1:
        timeout_seconds = int(argv[1])

    project_root = Path(__file__).resolve().parents[2]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = project_root / "artifacts" / "spiral-allcards" / "revalidation" / run_id
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    steps = build_steps()
    results: list[dict[str, object]] = []

    print(f"[audit] run_id={run_id} total_steps={len(steps)} timeout={timeout_seconds}s", flush=True)
    for idx, step in enumerate(steps, start=1):
        print(f"[{idx}/{len(steps)}] {step.card} {step.phase} {step.name}", flush=True)
        row = _run_step(step, project_root, logs_dir, timeout_seconds)
        results.append(row)
        if int(row["returncode"]) == 0:
            print("  -> OK", flush=True)
        else:
            print(f"  -> FAILED rc={row['returncode']} log={row['log_path']}", flush=True)

    by_card = _aggregate_by_card(results)

    summary = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "timeout_seconds": timeout_seconds,
        "total_steps": len(results),
        "failed_steps": [r for r in results if int(r["returncode"]) != 0],
        "card_summary": by_card,
        "results": results,
    }

    json_path = out_dir / "execution_cards_code_audit_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    ordered_cards = [
        "S0A", "S0B", "S0C", "S1A", "S1B", "S2A", "S2B", "S2C", "S2R",
        "S3A", "S3", "S3R", "S4", "S3AR", "S3B", "S3C", "S3D", "S3E", "S4B", "S4BR", "S4R",
    ]
    lines = [
        "# S0A-S4BR 代码级复检汇总",
        "",
        f"- run_id: {run_id}",
        f"- total_steps: {len(results)}",
        f"- failed_steps: {len(summary['failed_steps'])}",
        f"- timeout_seconds: {timeout_seconds}",
        "",
        "## 卡片判定",
        "",
        "| 卡片 | 状态 | run失败 | test失败 | gate失败 |",
        "|---|---|---:|---:|---:|",
    ]

    for card in ordered_cards:
        info = by_card.get(card)
        if info is None:
            lines.append(f"| {card} | missing | - | - | - |")
            continue
        lines.append(
            f"| {card} | {info['status']} | {info['run_failed']} | {info['test_failed']} | {info['gate_failed']} |"
        )

    lines.extend([
        "",
        "## 失败明细",
        "",
        "| 卡片 | 阶段 | 步骤 | rc | 日志 |",
        "|---|---|---|---:|---|",
    ])

    has_fail = False
    for row in results:
        if int(row["returncode"]) == 0:
            continue
        has_fail = True
        lines.append(
            f"| {row['card']} | {row['phase']} | {row['name']} | {row['returncode']} | {row['log_path']} |"
        )
    if not has_fail:
        lines.append("| - | - | - | 0 | 全部通过 |")

    md_path = out_dir / "execution_cards_code_audit_summary.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"summary_json={json_path}")
    print(f"summary_md={md_path}")

    return 1 if summary["failed_steps"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
