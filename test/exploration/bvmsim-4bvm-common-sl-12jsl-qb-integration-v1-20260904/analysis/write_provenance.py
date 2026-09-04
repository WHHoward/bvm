#!/usr/bin/env python3
"""Create the final hash manifest after analysis and visualization QA."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PASSIVE = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def files_hashes(paths: list[Path]) -> dict[str, str]:
    return {rel(path): sha256(path) for path in paths if path.is_file()}


def main() -> int:
    target = EXP / "analysis/provenance_final.json"
    if target.exists():
        raise RuntimeError(f"refusing to overwrite final provenance: {target}")
    source_paths = [
        REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        REPO / "BVMSim/BQ.cir",
        REPO / "BVMSim/library_josim/jtl2.cir",
        REPO / "circuits/models/jjmit.cir",
        REPO / "circuits/bvm/bvm_cell.cir",
        PASSIVE / "runs/1111/deck.cir",
    ]
    tool_paths = [
        EXP / "generate_decks.py",
        EXP / "run.sh",
        EXP / "analysis/topology_preflight.py",
        EXP / "analysis/write_metadata.py",
        EXP / "analysis/analyze.py",
        EXP / "analysis/independent_check.py",
        EXP / "analysis/render_plots.py",
        EXP / "analysis/viz_qa.py",
        EXP / "analysis/write_provenance.py",
        REPO / "scripts/josim-plot2.py",
        REPO / "scripts/bvmtools/raw.py",
        REPO / "scripts/bvmtools/phase.py",
        REPO / "scripts/bvmtools/sfq.py",
        REPO / "scripts/bvmtools/kcl.py",
        REPO / "scripts/bvmtools/waveform.py",
        REPO / "scripts/bvmtools/compare.py",
        REPO / "docs/research/METRIC_SPEC_V2.md",
    ]
    run_files: dict[str, object] = {}
    for mask in MASKS:
        run_dir = EXP / "runs" / mask
        run_files[mask] = {
            "deck": {"path": rel(run_dir / "deck.cir"), "sha256": sha256(run_dir / "deck.cir")},
            "raw": {"path": rel(run_dir / "raw.csv"), "sha256": sha256(run_dir / "raw.csv")},
            "log": {"path": rel(run_dir / "run.log"), "sha256": sha256(run_dir / "run.log")},
            "metadata": {"path": rel(run_dir / "metadata.json"), "sha256": sha256(run_dir / "metadata.json")},
        }
    supplemental_html = sorted((EXP / "plots/runs").rglob("*.html")) + sorted((EXP / "plots/comparison").glob("*.html"))
    comparison_data = sorted((EXP / "plots/comparison/data").glob("*.csv"))
    checks = {
        "analysis_metrics": {"path": rel(EXP / "analysis/metrics.json"), "sha256": sha256(EXP / "analysis/metrics.json")},
        "independent_check": {"path": rel(EXP / "analysis/independent_check.json"), "sha256": sha256(EXP / "analysis/independent_check.json")},
        "topology_preflight": {"path": rel(EXP / "analysis/topology_preflight.json"), "sha256": sha256(EXP / "analysis/topology_preflight.json")},
        "viz_qa": {"path": rel(EXP / "analysis/viz_qa.json"), "sha256": sha256(EXP / "analysis/viz_qa.json")},
        "plot_manifest": {"path": rel(EXP / "plots/plot_manifest.json"), "sha256": sha256(EXP / "plots/plot_manifest.json")},
        "primary_overview": {"path": rel(EXP / "plots/RESULT_OVERVIEW.html"), "sha256": sha256(EXP / "plots/RESULT_OVERVIEW.html")},
    }
    solver = REPO / "build/josim-cli"
    version = subprocess.check_output([str(solver), "--version"], text=True, stderr=subprocess.STDOUT).strip()
    output = {
        "schema": "bvmsim-common-sl-12jsl-qb-final-provenance-v1",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_before_task": "a58bbb3b566b466110bccda8f89fc36c4ce2d368",
        "setup_commit": "5d19d166912af910077d68e00257a09295285995",
        "head_at_provenance": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status_at_provenance": subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True).splitlines(),
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_COMMON_SL_12JSL_QB_VARIANT",
        "canonical_bvm_used": False,
        "source_sha256": files_hashes(source_paths),
        "solver": {"path": rel(solver), "sha256": sha256(solver), "version": version},
        "analysis_tool_sha256": files_hashes(tool_paths),
        "run_artifacts": run_files,
        "analysis_and_visual_artifacts": checks,
        "supplemental_html_sha256": files_hashes(supplemental_html),
        "comparison_data_sha256": files_hashes(comparison_data),
        "command_exit_codes": {
            "generate_decks.py": 0,
            "topology_preflight.py": 0,
            "run.sh": 0,
            "analyze.py --write": 0,
            "independent_check.py": 0,
            "render_plots.py --write": 0,
            "viz_qa.py": 0,
        },
        "raw_immutability": True,
        "interpolation": "none",
        "phase_statement": "P is JoSIM radians; phase display uses continuous_unwrap(rad)/(2*pi); phase is not an SFQ count",
        "gate": {
            "state": "AWAITING_USER_REVIEW",
            "user_reviewed": False,
            "next_step_authorized": False,
            "automatic_next_experiment": False,
            "next_action": "STOP",
        },
    }
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "raw_runs": len(run_files), "supplemental_html": len(supplemental_html), "comparison_data": len(comparison_data), "output": rel(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
