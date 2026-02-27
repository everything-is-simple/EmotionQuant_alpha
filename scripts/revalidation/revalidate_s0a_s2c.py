"""S0A->S2C 顺序重验执行器。

设计目标：
1. 严格按执行卡顺序执行（S0A, S0B, S0C, S1A, S1B, S2A, S2B, S2C）。
2. 每一步都落独立日志，便于 run/test/artifact/review/sync 复盘。
3. 失败不静默：保留失败上下文并在汇总文件里标记。

说明：
- 本脚本只负责“执行+记录”；是否 GO 由治理文档回填时判定。
- 默认使用 canary 复核交易日 20241220，S1B 用 20200102~20241231 窗口。
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Step:
    """可执行步骤定义。"""

    card: str
    stage: str  # run / test / gate
    name: str
    cmd: Sequence[str]


def _run_step(step: Step, project_root: Path, logs_dir: Path) -> dict[str, object]:
    """执行单个步骤并写日志文件。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = step.name.replace(" ", "_").replace("/", "_")
    log_path = logs_dir / f"{step.card.lower()}_{step.stage}_{safe_name}_{ts}.log"

    started = datetime.now()
    proc = subprocess.run(
        step.cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ended = datetime.now()

    # 日志中保留命令、stdout/stderr、退出码，便于后续审计。
    content = []
    content.append(f"# card={step.card} stage={step.stage} name={step.name}")
    content.append(f"# command={' '.join(step.cmd)}")
    content.append(f"# started={started.isoformat()}")
    content.append(f"# ended={ended.isoformat()}")
    content.append(f"# returncode={proc.returncode}")
    content.append("\n## stdout\n")
    content.append(proc.stdout or "")
    content.append("\n## stderr\n")
    content.append(proc.stderr or "")
    log_path.write_text("\n".join(content), encoding="utf-8")

    return {
        "card": step.card,
        "stage": step.stage,
        "name": step.name,
        "command": list(step.cmd),
        "returncode": proc.returncode,
        "started": started.isoformat(),
        "ended": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 3),
        "log_path": str(log_path),
    }


def build_steps() -> list[Step]:
    """组装 S0A->S2C 的顺序重验步骤。"""
    return [
        # S0A
        Step("S0A", "run", "cli_help", ["python", "-m", "src.pipeline.main", "--help"]),
        Step("S0A", "run", "dry_run_config", ["python", "-m", "src.pipeline.main", "--env-file", ".env", "--print-config", "run", "--date", "20260215", "--dry-run"]),
        Step("S0A", "test", "cli_entrypoint", ["pytest", "tests/unit/pipeline/test_cli_entrypoint.py", "-q"]),
        Step("S0A", "test", "config_defaults", ["pytest", "tests/unit/config/test_config_defaults.py", "-q"]),
        Step("S0A", "test", "env_docs_alignment", ["pytest", "tests/unit/config/test_env_docs_alignment.py", "-q"]),
        # S0B
        Step("S0B", "run", "l1_only", ["python", "-m", "src.pipeline.main", "run", "--date", "20241220", "--source", "tushare", "--l1-only"]),
        Step("S0B", "test", "fetcher_contract", ["pytest", "tests/unit/data/test_fetcher_contract.py", "-q"]),
        Step("S0B", "test", "l1_repository_contract", ["pytest", "tests/unit/data/test_l1_repository_contract.py", "-q"]),
        Step("S0B", "test", "data_readiness_contract", ["pytest", "tests/unit/data/test_data_readiness_persistence_contract.py", "-q"]),
        # S0C
        Step("S0C", "run", "to_l2_sw31", ["python", "-m", "src.pipeline.main", "run", "--date", "20241220", "--source", "tushare", "--to-l2", "--strict-sw31"]),
        Step("S0C", "test", "snapshot_contract", ["pytest", "tests/unit/data/test_snapshot_contract.py", "-q"]),
        Step("S0C", "test", "s0_canary", ["pytest", "tests/unit/data/test_s0_canary.py", "-q"]),
        Step("S0C", "test", "sw31_contract", ["pytest", "tests/unit/data/test_industry_snapshot_sw31_contract.py", "-q"]),
        Step("S0C", "test", "flat_threshold_contract", ["pytest", "tests/unit/data/test_flat_threshold_config_contract.py", "-q"]),
        # S1A
        Step("S1A", "run", "mss_daily", ["python", "-m", "src.pipeline.main", "mss", "--date", "20241220"]),
        Step("S1A", "test", "mss_contract", ["pytest", "tests/unit/algorithms/mss/test_mss_contract.py", "-q"]),
        Step("S1A", "test", "mss_engine", ["pytest", "tests/unit/algorithms/mss/test_mss_engine.py", "-q"]),
        Step("S1A", "test", "mss_full_semantics", ["pytest", "tests/unit/algorithms/mss/test_mss_full_semantics_contract.py", "-q"]),
        # S1B
        Step("S1B", "run", "mss_probe", ["python", "-m", "src.pipeline.main", "mss-probe", "--start", "20200102", "--end", "20241231"]),
        Step("S1B", "test", "mss_probe_contract", ["pytest", "tests/unit/algorithms/mss/test_mss_probe_contract.py", "-q"]),
        Step("S1B", "test", "mss_integration_contract", ["pytest", "tests/unit/integration/test_mss_integration_contract.py", "-q"]),
        # S2A
        Step("S2A", "run", "recommend_mss_irs_pas", ["python", "-m", "src.pipeline.main", "recommend", "--date", "20241220", "--mode", "mss_irs_pas", "--with-validation"]),
        Step("S2A", "test", "irs_contract", ["pytest", "tests/unit/algorithms/irs/test_irs_contract.py", "-q"]),
        Step("S2A", "test", "pas_contract", ["pytest", "tests/unit/algorithms/pas/test_pas_contract.py", "-q"]),
        Step("S2A", "test", "validation_gate_contract", ["pytest", "tests/unit/integration/test_validation_gate_contract.py", "-q"]),
        Step("S2A", "test", "weight_plan_bridge_contract", ["pytest", "tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py", "-q"]),
        # S2B
        Step("S2B", "run", "integrated_top_down", ["python", "-m", "src.pipeline.main", "recommend", "--date", "20241220", "--mode", "integrated", "--integration-mode", "top_down"]),
        Step("S2B", "run", "integrated_bottom_up", ["python", "-m", "src.pipeline.main", "recommend", "--date", "20241220", "--mode", "integrated", "--integration-mode", "bottom_up"]),
        Step("S2B", "run", "integrated_dual_verify", ["python", "-m", "src.pipeline.main", "recommend", "--date", "20241220", "--mode", "integrated", "--integration-mode", "dual_verify"]),
        Step("S2B", "run", "integrated_complementary", ["python", "-m", "src.pipeline.main", "recommend", "--date", "20241220", "--mode", "integrated", "--integration-mode", "complementary"]),
        Step("S2B", "test", "integration_contract", ["pytest", "tests/unit/integration/test_integration_contract.py", "-q"]),
        Step("S2B", "test", "quality_gate_contract", ["pytest", "tests/unit/integration/test_quality_gate_contract.py", "-q"]),
        # S2C
        Step("S2C", "run", "integrated_bridge_release", ["python", "-m", "src.pipeline.main", "recommend", "--date", "20241220", "--mode", "integrated", "--with-validation-bridge", "--evidence-lane", "release"]),
        Step("S2C", "test", "s2c_semantics_mss", ["pytest", "tests/unit/algorithms/mss/test_mss_full_semantics_contract.py", "-q"]),
        Step("S2C", "test", "s2c_semantics_irs", ["pytest", "tests/unit/algorithms/irs/test_irs_full_semantics_contract.py", "-q"]),
        Step("S2C", "test", "s2c_semantics_pas", ["pytest", "tests/unit/algorithms/pas/test_pas_full_semantics_contract.py", "-q"]),
        Step("S2C", "test", "s2c_validation_factor", ["pytest", "tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py", "-q"]),
        Step("S2C", "test", "s2c_validation_walkforward", ["pytest", "tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py", "-q"]),
        Step("S2C", "test", "s2c_bridge_test", ["pytest", "tests/unit/integration/test_validation_weight_plan_bridge.py", "-q"]),
        Step("S2C", "test", "s2c_semantics_regression", ["pytest", "tests/unit/integration/test_algorithm_semantics_regression.py", "-q"]),
        # 全局治理门禁
        Step("GLOBAL", "gate", "contracts_governance", ["python", "-m", "scripts.quality.local_quality_check", "--contracts", "--governance"]),
    ]


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = project_root / "artifacts" / "spiral-s0s2" / "revalidation" / run_id
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    steps = build_steps()
    results: list[dict[str, object]] = []
    failed = False

    for idx, step in enumerate(steps, start=1):
        print(f"[{idx}/{len(steps)}] {step.card} {step.stage} {step.name}", flush=True)
        result = _run_step(step, project_root, logs_dir)
        results.append(result)
        if result["returncode"] != 0:
            failed = True
            print(f"  -> FAILED (rc={result['returncode']}) log={result['log_path']}", flush=True)
            # 失败后继续执行，保留完整失败面，便于一次性修复。
        else:
            print("  -> OK", flush=True)

    summary = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "total_steps": len(results),
        "failed_steps": [r for r in results if r["returncode"] != 0],
        "results": results,
    }

    summary_json = out_dir / "s0a_s2c_revalidation_summary.json"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 生成一份人可读摘要，方便直接贴到 review/final。
    lines = []
    lines.append("# S0A-S2C 重验汇总")
    lines.append("")
    lines.append(f"- run_id: {run_id}")
    lines.append(f"- total_steps: {len(results)}")
    lines.append(f"- failed_steps: {len(summary['failed_steps'])}")
    lines.append("")
    lines.append("| card | stage | step | rc | log |")
    lines.append("|---|---|---|---:|---|")
    for r in results:
        lines.append(
            f"| {r['card']} | {r['stage']} | {r['name']} | {r['returncode']} | {r['log_path']} |"
        )

    summary_md = out_dir / "s0a_s2c_revalidation_summary.md"
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"summary_json={summary_json}")
    print(f"summary_md={summary_md}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
