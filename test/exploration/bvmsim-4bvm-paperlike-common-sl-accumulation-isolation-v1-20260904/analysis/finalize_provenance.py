#!/usr/bin/env python3
"""Collect immutable post-run hashes without rewriting raw evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def main() -> int:
    setup = json.loads((EXP / "provenance.json").read_text(encoding="utf-8"))
    sources = {
        "setup_provenance": EXP / "provenance.json",
        "topology_preflight": EXP / "analysis/topology_preflight.json",
        "template_deck": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir",
        "jm2_connected_bvm_variant": REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "shared_jjmit_model": REPO / "circuits/models/jjmit.cir",
        "canonical_bvm_not_used": REPO / "circuits/bvm/bvm_cell.cir",
        "solver": REPO / "build/josim-cli",
        "plotter": REPO / "scripts/josim-plot2.py",
        "old_distributed_metrics": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/analysis/metrics.json",
        "generate_decks": EXP / "generate_decks.py",
        "topology_preflight_script": EXP / "analysis/topology_preflight.py",
        "analyze_script": EXP / "analysis/analyze.py",
        "independent_check_script": EXP / "analysis/independent_check.py",
        "render_plots_script": EXP / "analysis/render_plots.py",
        "run_script": EXP / "run.sh",
    }
    runs: dict[str, object] = {}
    for mask in MASKS:
        paths = {name: EXP / "runs" / mask / name for name in ("deck.cir", "raw.csv", "run.log", "metadata.json")}
        metadata = json.loads(paths["metadata.json"].read_text(encoding="utf-8"))
        runs[mask] = {
            "artifacts": {name: {"path": rel(path), "sha256": digest(path), "size_bytes": path.stat().st_size} for name, path in paths.items()},
            "exit_code": metadata["exit_code"],
            "execution_status": metadata["execution_status"],
        }
    result = {
        "schema": "bvmsim-paperlike-common-sl-final-provenance-v1",
        "experiment_id": EXP.name,
        "finalized_at_local": subprocess.check_output(["date", "--iso-8601=seconds"], text=True).strip(),
        "head_before_setup": setup["head_before_setup"],
        "setup_commit": "d6a355b2",
        "head_before_runs": "d6a355b2",
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "canonical_bvm_used": False,
        "source_hashes": {name: {"path": rel(path), "sha256": digest(path)} for name, path in sources.items()},
        "runs": runs,
        "analysis_artifacts": {
            name: {"path": rel(path), "sha256": digest(path), "size_bytes": path.stat().st_size}
            for name, path in {
                "metrics": EXP / "analysis/metrics.json",
                "report": EXP / "analysis/REPORT.md",
                "review": EXP / "analysis/REVIEW.md",
                "commands": EXP / "analysis/COMMANDS.md",
                "independent_check": EXP / "analysis/independent_check.json",
                "plot_manifest": EXP / "analysis/plot_manifest.json",
            }.items()
        },
        "raw_policy": "raw.csv files were created once per mask and not rewritten",
        "analysis_policy": "no QB/JTL metrics; phase displayed as continuous_unwrap(rad)/(2*pi) only",
        "gate": {
            "state": "AWAITING_USER_REVIEW",
            "user_reviewed": False,
            "next_step_authorized": False,
            "automatic_next_experiment": False,
            "next_action": "STOP",
        },
    }
    output = EXP / "analysis/provenance_final.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": rel(output), "raw_count": len(runs), "head_before_runs": result["head_before_runs"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
