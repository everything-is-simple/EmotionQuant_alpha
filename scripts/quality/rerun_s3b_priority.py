from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class StepResult:
    step: str
    rc: int
    payload: dict[str, Any]
    stdout_tail: str
    stderr_tail: str


def _tail(text: str, lines: int = 20) -> str:
    if not text:
        return ""
    parts = text.splitlines()
    if len(parts) <= lines:
        return text
    return "\n".join(parts[-lines:])


def _parse_last_json(stdout: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line or not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            payload = obj
            break
    return payload


def _run_cli(*, env_file: str, argv: list[str]) -> StepResult:
    cmd = [sys.executable, "-m", "src.pipeline.main", "--env-file", env_file, *argv]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = _parse_last_json(proc.stdout)
    return StepResult(
        step=" ".join(argv),
        rc=int(proc.returncode),
        payload=payload,
        stdout_tail=_tail(proc.stdout),
        stderr_tail=_tail(proc.stderr),
    )


def _load_priority_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    rows.sort(key=lambda item: int(str(item.get("priority", "999999"))))
    return rows


def _is_step_failed(result: StepResult) -> tuple[bool, str]:
    payload = result.payload
    quality_status = str(payload.get("quality_gate_status", "")).strip().upper()
    go_nogo = str(payload.get("go_nogo", "")).strip().upper()
    final_gate = str(payload.get("final_gate", "")).strip().upper()
    gate_status = str(payload.get("gate_status", "")).strip().upper()
    status = str(payload.get("status", "")).strip().lower()
    reason_parts: list[str] = []
    if final_gate:
        reason_parts.append(f"final_gate={final_gate}")
    if quality_status:
        reason_parts.append(f"quality_gate_status={quality_status}")
    if gate_status:
        reason_parts.append(f"gate_status={gate_status}")
    if go_nogo:
        reason_parts.append(f"go_nogo={go_nogo}")
    if status:
        reason_parts.append(f"status={status}")

    if result.rc != 0:
        if reason_parts:
            return (True, f"return_code={result.rc};" + ",".join(reason_parts))
        return (True, f"return_code={result.rc}")
    if not payload:
        return (False, "")
    if status == "failed":
        return (True, "status=failed")
    if quality_status == "FAIL":
        return (True, "quality_gate_status=FAIL")
    if final_gate == "FAIL":
        return (True, "final_gate=FAIL")
    if gate_status == "FAIL":
        return (True, "gate_status=FAIL")
    if go_nogo == "NO_GO":
        return (True, "go_nogo=NO_GO")
    return (False, "")


def _build_steps(
    *,
    trade_date: str,
    stage: str,
    integration_mode: str,
    evidence_lane: str,
    skip_integrated: bool,
    recommend_with_upstream: bool,
    recommend_reuse_validation: bool,
) -> list[list[str]]:
    if stage == "irs":
        steps: list[list[str]] = [
            ["run", "--date", trade_date, "--to-l2", "--strict-sw31"],
            ["mss", "--date", trade_date],
            ["irs", "--date", trade_date, "--require-sw31"],
        ]
        if skip_integrated:
            return steps
        steps.append(
            [
                "recommend",
                "--date",
                trade_date,
                "--mode",
                "integrated",
                "--integration-mode",
                integration_mode,
                "--with-validation-bridge",
                "--evidence-lane",
                evidence_lane,
            ]
        )
        if not recommend_reuse_validation:
            steps[-1][8:8] = [
                "--with-validation",
                "--validation-threshold-mode",
                "regime",
                "--validation-wfa",
                "dual-window",
                "--validation-export-run-manifest",
            ]
        return steps
    if skip_integrated:
        return []
    steps: list[list[str]] = []
    if recommend_with_upstream:
        steps.extend(
            [
                ["run", "--date", trade_date, "--to-l2", "--strict-sw31"],
                ["mss", "--date", trade_date],
            ]
        )
    steps.append(
        [
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "integrated",
            "--integration-mode",
            integration_mode,
            "--with-validation-bridge",
            "--evidence-lane",
            evidence_lane,
        ]
    )
    if not recommend_reuse_validation:
        steps[-1][8:8] = [
            "--with-validation",
            "--validation-threshold-mode",
            "regime",
            "--validation-wfa",
            "dual-window",
            "--validation-export-run-manifest",
        ]
    return steps


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.quality.rerun_s3b_priority",
        description="Replay S3b priority failures with a single env-file and serial steps.",
    )
    parser.add_argument(
        "--priority-csv",
        required=True,
        help="Path to rebuild_failures_priority.csv.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Env file path used for every command in this run.",
    )
    parser.add_argument(
        "--integration-mode",
        default="top_down",
        choices=("top_down", "bottom_up", "dual_verify", "complementary"),
        help="Integration mode for integrated recommend.",
    )
    parser.add_argument(
        "--evidence-lane",
        default="release",
        choices=("release", "debug"),
        help="Evidence lane for integrated recommend artifacts.",
    )
    parser.add_argument(
        "--stop-on-fail",
        action="store_true",
        help="Stop immediately when any date fails.",
    )
    parser.add_argument(
        "--skip-integrated",
        action="store_true",
        help="For stage=irs rows, only run run->mss->irs and skip recommend integrated.",
    )
    parser.add_argument(
        "--only-stage",
        default="",
        choices=("", "irs", "recommend"),
        help="Optionally run only a single stage from priority csv.",
    )
    parser.add_argument(
        "--recommend-with-upstream",
        action="store_true",
        help="For stage=recommend rows, prepend run --to-l2 --strict-sw31 and mss before recommend.",
    )
    parser.add_argument(
        "--recommend-reuse-validation",
        action="store_true",
        help="For recommend integrated step, reuse existing validation_gate_decision and skip --with-validation recompute.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional output summary json path. Default: sibling of priority csv.",
    )
    parser.add_argument(
        "--output-csv",
        default="",
        help="Optional output result csv path. Default: sibling of priority csv.",
    )
    args = parser.parse_args(argv)

    priority_csv = Path(args.priority_csv)
    rows = _load_priority_rows(priority_csv)
    output_json = (
        Path(args.output_json)
        if str(args.output_json).strip()
        else priority_csv.parent / "rerun_priority_summary.json"
    )
    output_csv = (
        Path(args.output_csv)
        if str(args.output_csv).strip()
        else priority_csv.parent / "rerun_priority_results.csv"
    )

    results: list[dict[str, Any]] = []
    for row in rows:
        trade_date = str(row.get("trade_date", "")).strip()
        stage = str(row.get("stage", "unknown")).strip()
        if str(args.only_stage).strip() and stage != str(args.only_stage).strip():
            continue
        steps = _build_steps(
            trade_date=trade_date,
            stage=stage,
            integration_mode=args.integration_mode,
            evidence_lane=args.evidence_lane,
            skip_integrated=bool(args.skip_integrated),
            recommend_with_upstream=bool(args.recommend_with_upstream),
            recommend_reuse_validation=bool(args.recommend_reuse_validation),
        )
        if not steps:
            continue
        date_status = "ok"
        fail_reason = ""
        step_records: list[dict[str, Any]] = []
        for cmd_argv in steps:
            step_result = _run_cli(env_file=args.env_file, argv=cmd_argv)
            failed, reason = _is_step_failed(step_result)
            step_records.append(
                {
                    "step": step_result.step,
                    "rc": step_result.rc,
                    "payload": step_result.payload,
                    "stdout_tail": step_result.stdout_tail,
                    "stderr_tail": step_result.stderr_tail,
                    "failed": failed,
                    "reason": reason,
                }
            )
            if failed:
                date_status = "failed"
                fail_reason = f"{cmd_argv[0]}:{reason}"
                break
        results.append(
            {
                "priority": int(str(row.get("priority", "0")) or "0"),
                "blocking_level": str(row.get("blocking_level", "")),
                "trade_date": trade_date,
                "stage": stage,
                "status": date_status,
                "fail_reason": fail_reason,
                "steps": step_records,
            }
        )
        if date_status == "failed" and bool(args.stop_on_fail):
            break

    failed_items = [item for item in results if item["status"] != "ok"]
    summary = {
        "priority_csv": str(priority_csv),
        "env_file": str(args.env_file),
        "integration_mode": str(args.integration_mode),
        "evidence_lane": str(args.evidence_lane),
        "skip_integrated": bool(args.skip_integrated),
        "recommend_with_upstream": bool(args.recommend_with_upstream),
        "recommend_reuse_validation": bool(args.recommend_reuse_validation),
        "only_stage": str(args.only_stage),
        "total": len(results),
        "failed": len(failed_items),
        "failed_dates": [item["trade_date"] for item in failed_items],
        "results": results,
    }
    _write_json(output_json, summary)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "priority",
                "blocking_level",
                "trade_date",
                "stage",
                "status",
                "fail_reason",
            ],
        )
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "priority": item["priority"],
                    "blocking_level": item["blocking_level"],
                    "trade_date": item["trade_date"],
                    "stage": item["stage"],
                    "status": item["status"],
                    "fail_reason": item["fail_reason"],
                }
            )

    print(
        json.dumps(
            {
                "event": "s3b_priority_rerun",
                "total": len(results),
                "failed": len(failed_items),
                "output_json": str(output_json),
                "output_csv": str(output_csv),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if failed_items else 0


if __name__ == "__main__":
    raise SystemExit(main())
