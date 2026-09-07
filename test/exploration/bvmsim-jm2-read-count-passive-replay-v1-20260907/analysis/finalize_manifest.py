#!/usr/bin/env python3
"""Create the final hash inventory after all analysis and plots are frozen."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"
DIRECT = REPO / "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907"
OUT = EXP / "analysis/provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path) -> dict[str, object]:
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    source_manifest = json.loads((EXP / "source/source_manifest.json").read_text(encoding="utf-8"))
    replay_manifest = json.loads((EXP / "analysis/replay_source_manifest.json").read_text(encoding="utf-8"))
    raw = {}
    decks = {}
    for name, path in {
        "N1_PASSIVE": BASELINE / "runs/array_passive/raw.csv",
        "N2_PASSIVE": EXP / "runs/n2_passive/raw.csv",
        "N3_PASSIVE": EXP / "runs/n3_passive/raw.csv",
        "N4_PASSIVE": EXP / "runs/n4_passive/raw.csv",
        "N1_REPLAY": BASELINE / "runs/replay_array/raw.csv",
        "N2_REPLAY": EXP / "runs/n2_replay/raw.csv",
        "N3_REPLAY": EXP / "runs/n3_replay/raw.csv",
        "N4_REPLAY": EXP / "runs/n4_replay/raw.csv",
    }.items():
        raw[name] = {**record(path), "role": "N1_REFERENCE" if name.startswith("N1_") else "NEW_RUN"}
    for name, path in {
        "N1_PASSIVE": BASELINE / "runs/array_passive/deck.cir",
        "N2_PASSIVE": EXP / "runs/n2_passive/deck.cir",
        "N3_PASSIVE": EXP / "runs/n3_passive/deck.cir",
        "N4_PASSIVE": EXP / "runs/n4_passive/deck.cir",
        "N1_REPLAY": BASELINE / "runs/replay_array/deck.cir",
        "N2_REPLAY": EXP / "runs/n2_replay/deck.cir",
        "N3_REPLAY": EXP / "runs/n3_replay/deck.cir",
        "N4_REPLAY": EXP / "runs/n4_replay/deck.cir",
    }.items():
        decks[name] = {**record(path), "role": "N1_REFERENCE" if name.startswith("N1_") else "NEW_RUN"}
    source_files = {
        "bvm_variant": REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "canonical_bvm_not_used": REPO / "circuits/bvm/bvm_cell.cir",
        "jjmit": REPO / "circuits/models/jjmit.cir",
        "qb": REPO / "BVMSim/BQ.cir",
        "jtl": REPO / "BVMSim/library_josim/jtl2.cir",
        "solver": REPO / "build/josim-cli",
        "plotter": REPO / "scripts/josim-plot2.py",
    }
    script_names = ("generate_decks.py", "analysis/preflight.py", "analysis/run_passive.py", "analysis/build_replay.py", "analysis/replay_preflight.py", "analysis/run_replay.py", "analysis/analyze.py", "analysis/independent_check.py", "analysis/event_observation.py", "analysis/render_plots.py", "analysis/render_summary.py", "analysis/finalize_manifest.py")
    scripts = {path: record(EXP / path) for path in script_names}
    pages = {}
    for path in sorted((EXP / "plots").glob("*.html")):
        pages[path.stem] = record(path)
    plot_inputs = {path.stem: record(path) for path in sorted((EXP / "plots/data").glob("*.csv"))}
    preserved_attempts = [path.relative_to(REPO).as_posix() for path in sorted((EXP / "analysis/attempts").rglob("*")) if path.is_file()]
    status = subprocess.check_output(["git", "status", "--short", "--branch"], cwd=REPO, text=True).splitlines()
    manifest = {
        "schema": "jm2-read-count-passive-replay-final-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "head_at_setup": source_manifest["head_at_setup"],
        "head_at_finalization": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status_at_finalization": status,
        "sources": {name: record(path) for name, path in source_files.items()},
        "source_manifest": record(EXP / "source/source_manifest.json"),
        "replay_source_manifest": record(EXP / "analysis/replay_source_manifest.json"),
        "n1_reference": source_manifest["n1_reference"],
        "raw": raw,
        "decks": decks,
        "scripts": scripts,
        "analysis_records": {path.stem: record(path) for path in sorted((EXP / "analysis").glob("*.json")) if path.name != OUT.name},
        "plots": pages,
        "plot_inputs": plot_inputs,
        "result_brief": record(EXP / "RESULT_BRIEF.md"),
        "baseline_replay_manifest_sha256": sha256(BASELINE / "analysis/replay_source_manifest.json"),
        "contextual_direct_raw": {"single": record(DIRECT / "runs/single/raw.csv"), "array": record(DIRECT / "runs/array/raw.csv")},
        "preserved_attempt_files": preserved_attempts,
        "new_physical_solve_count": 6,
        "n1_rerun": False,
        "raw_immutable": True,
        "visualization_pages": {"standalone": 8, "aggregate": 5, "total": len(pages)},
    }
    if OUT.exists():
        raise RuntimeError(f"refusing to overwrite existing final provenance: {OUT}")
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": "analysis/provenance.json", "raw": len(raw), "pages": len(pages), "preserved_attempt_files": len(preserved_attempts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
