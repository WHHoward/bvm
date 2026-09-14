#!/usr/bin/env python3
"""Add raw-direct supplemental state pages for BVM2, BVM3 and BVM4."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
STATE = EXP / "screening/closure_state.json"
BASE_MANIFEST = EXP / "visualization/manifest.json"
OUTPUT_ROOT = EXP / "visualization/plots/runs"
SUPPLEMENT_ROOT = EXP / "visualization/supplemental_bvm_states"
MANIFEST = SUPPLEMENT_ROOT / "manifest.json"
PLOTTER = REPO / "scripts/josim-plot2.py"
BVM_INDICES = (2, 3, 4)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def headers(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return next(csv.reader(stream))


def labels_for_bvm(index: int) -> tuple[str, ...]:
    return (
        f"P(B_JM1|XBVM{index})", f"V(B_JM1|XBVM{index})", f"I(B_JM1|XBVM{index})",
        f"P(B_JM2|XBVM{index})", f"V(B_JM2|XBVM{index})", f"I(B_JM2|XBVM{index})",
        f"P(B_JS1|XBVM{index})", f"V(B_JS1|XBVM{index})", f"I(B_JS1|XBVM{index})",
        f"P(B_JS2|XBVM{index})", f"V(B_JS2|XBVM{index})", f"I(B_JS2|XBVM{index})",
        f"I(L_SL|XBVM{index})", f"V(L_SL|XBVM{index})", "V(COMMON_SL)",
    )


def plot(raw: Path, output: Path, labels: tuple[str, ...], title: str) -> list[str]:
    actual = headers(raw)
    missing = [label for label in labels if label not in actual]
    if missing:
        raise RuntimeError(f"missing labels for {raw}: {missing}")
    if output.exists():
        raise RuntimeError(f"refusing to overwrite supplemental plot: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"plot failed: {output}: {completed.stderr[-1000:]}")
    return command


def write_navigation(run_id: str, entries: list[dict[str, Any]]) -> None:
    path = SUPPLEMENT_ROOT / "run_summaries" / f"{run_id}.md"
    if path.exists():
        raise RuntimeError(f"refusing to overwrite supplemental navigation: {path}")
    lines = [f"# {run_id} remaining BVM state supplement", "", "Raw-direct 0–200 ps pages for the remaining BVM cells:"]
    for entry in entries:
        filename = Path(entry["output_path"]).name
        lines.append(f"- [XBVM{entry['bvm_index']} state](../../plots/runs/{run_id}/{filename})")
    lines.extend(["", "Signals are P/V/I for JM1, JM2, JS1, JS2 plus L_SL and COMMON_SL.", "P(...) is raw radians; -j 2pi is display/navigation only, never an SFQ count."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    base_manifest_sha = sha256(BASE_MANIFEST)
    entries: list[dict[str, Any]] = []
    navigation: dict[str, str] = {}
    for mask, case in sorted(state["screening_cases"].items()):
        run_id = case["run_id"]
        raw = REPO / case["raw_path"]
        run_entries: list[dict[str, Any]] = []
        for index in BVM_INDICES:
            labels = labels_for_bvm(index)
            output = OUTPUT_ROOT / run_id / f"02_BVM_STATE_XBVM{index}.html"
            command = plot(raw, output, labels, f"{run_id} — XBVM{index} state")
            entry = {"run_id": run_id, "mask": mask, "bvm_index": index, "semantic_view": f"02_BVM_STATE_XBVM{index}", "input_mode": "RAW_DIRECT", "input_raw": rel(raw), "input_raw_sha256": sha256(raw), "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "signal_order": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0]}
            entries.append(entry)
            run_entries.append(entry)
        write_navigation(run_id, run_entries)
        navigation[run_id] = rel(SUPPLEMENT_ROOT / "run_summaries" / f"{run_id}.md")
    record = {"schema": "bvm-qb-l1-l3-bj2-targeted-closure-supplemental-bvm-state-visualization-v1", "experiment_id": EXP.name, "created_at_local": now(), "base_visualization_manifest": rel(BASE_MANIFEST), "base_visualization_manifest_sha256": base_manifest_sha, "supplement_scope": "remaining BVM states XBVM2, XBVM3 and XBVM4 for each executed screening run", "standalone_window_ps": [0.0, 200.0], "entries": entries, "navigation": navigation, "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "plots_are_descriptive": True, "canonical_zip_modified": False}
    SUPPLEMENT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "entry_count": len(entries), "run_count": len(state["screening_cases"]), "bvm_indices": list(BVM_INDICES), "canonical_zip_modified": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
