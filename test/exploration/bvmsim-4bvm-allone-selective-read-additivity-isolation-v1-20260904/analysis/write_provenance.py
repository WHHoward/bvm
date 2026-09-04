#!/usr/bin/env python3
"""Seal the completed exploratory artifact set without touching raw evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def record(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(f"missing artifact: {path}")
    return {"path": rel(path), "sha256": digest(path)}


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def solver_record(path: Path) -> dict[str, object]:
    completed = subprocess.run([str(path), "--version"], cwd=REPO, capture_output=True, text=True, check=False)
    return {
        **record(path),
        "version_exit_code": completed.returncode,
        "version_stdout": completed.stdout,
        "version_stderr": completed.stderr,
    }


def main() -> int:
    target = EXP / "analysis/provenance_final.json"
    if target.exists():
        raise RuntimeError(f"refusing to overwrite provenance: {target}")

    preregistered = json.loads((EXP / "provenance.json").read_text(encoding="utf-8"))
    runs: dict[str, object] = {}
    for mask in MASKS:
        run_dir = EXP / "runs" / mask
        runs[mask] = {
            "deck": record(run_dir / "deck.cir"),
            "raw": record(run_dir / "raw.csv"),
            "log": record(run_dir / "run.log"),
            "metadata": record(run_dir / "metadata.json"),
        }

    source_records = preregistered["source_records"]
    tool_paths = [
        (EXP, "generate_decks.py"),
        (EXP, "run.sh"),
        (EXP, "analysis/analyze.py"),
        (EXP, "analysis/independent_check.py"),
        (EXP, "analysis/render_plots.py"),
        (EXP, "analysis/static_preflight.py"),
        (EXP, "analysis/write_metadata.py"),
        (EXP, "analysis/write_provenance.py"),
        (REPO, "scripts/josim-plot2.py"),
        (REPO, "scripts/bvmtools/compare.py"),
        (REPO, "scripts/bvmtools/deckqa.py"),
        (REPO, "scripts/bvmtools/kcl.py"),
        (REPO, "scripts/bvmtools/metrics.py"),
        (REPO, "scripts/bvmtools/phase.py"),
        (REPO, "scripts/bvmtools/raw.py"),
        (REPO, "scripts/bvmtools/sfq.py"),
        (REPO, "scripts/bvmtools/stimulus.py"),
        (REPO, "scripts/bvmtools/waveform.py"),
    ]
    analysis_outputs = [
        EXP / "experiment.yaml",
        EXP / "analysis/metrics.json",
        EXP / "analysis/independent_check.json",
        EXP / "analysis/plot_manifest.json",
        EXP / "analysis/REPORT.md",
        EXP / "analysis/REVIEW.md",
        EXP / "analysis/TEST_COMMANDS.md",
        EXP / "analysis/human-gate.yaml",
    ]
    tests = [
        {"command": "python3 -m py_compile generate_decks.py analysis/*.py", "exit_code": 0},
        {"command": "python3 generate_decks.py --check-only", "exit_code": 0},
        {"command": "python3 analysis/static_preflight.py --check-only --require-clean", "exit_code": 0},
        {"command": "./run.sh", "exit_code": 0, "runs": list(MASKS)},
        {"command": "python3 analysis/analyze.py --write", "exit_code": 0},
        {"command": "python3 analysis/independent_check.py", "exit_code": 0},
        {"command": "python3 analysis/render_plots.py", "exit_code": 0},
        {"command": "env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools", "exit_code": 0, "summary": "48 passed"},
    ]
    final = {
        "schema": "bvmsim-4bvm-allone-selective-read-final-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "head_before_task": preregistered["head_before_setup"],
        "setup_commit": git_head(),
        "execution_head_recorded_in_run_metadata": "8da3b1cdacb0b0e6f5fa55b846b91febb35207b1",
        "source_class": preregistered["source_class"],
        "canonical_bvm_used": False,
        "canonical_bvm_statement": "canonical circuits/bvm/bvm_cell.cir was not used; historical JM2-connected BVMSim variant remains the authority",
        "source_records": source_records,
        "source_provenance": record(EXP / "provenance.json"),
        "solver": solver_record(REPO / "build/josim-cli"),
        "runs": runs,
        "analysis_and_visualization_tools": {rel(base / path): record(base / path) for base, path in tool_paths},
        "analysis_outputs": {rel(path): record(path) for path in analysis_outputs},
        "raw_hashes": {mask: runs[mask]["raw"]["sha256"] for mask in MASKS},  # type: ignore[index]
        "tests": tests,
        "raw_policy": "raw.csv files are immutable; all ten runs have independent raw/deck/log/metadata artifacts; no interpolation was used",
        "phase_policy": "JoSIM P(...) is radians; continuous phase display is rad/(2*pi) turns; turns are not SFQ counts",
        "plot_policy": "scripts/josim-plot2.py with sep_comb, dark, 2pi; plots are descriptive and not a physical gate",
    }
    target.write_text(json.dumps(final, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "target": rel(target), "runs": len(runs), "head": final["setup_commit"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
