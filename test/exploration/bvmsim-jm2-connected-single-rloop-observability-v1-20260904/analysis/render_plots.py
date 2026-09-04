#!/usr/bin/env python3
"""Render focused JM2-connected plots with the frozen single-BVM authority."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"

CONDITIONS = OrderedDict((
    ("S0-J-RLOOP", EXP / "runs/S0-J-RLOOP/raw.csv"),
    ("S1-J-RLOOP", EXP / "runs/S1-J-RLOOP/raw.csv"),
))

STANDARD_PLOTS = OrderedDict((
    (
        "BVM_STIMULUS_AND_STATE",
        ["I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "P(BVMOUT)"],
    ),
    (
        "BVM_SENSING",
        [
            "V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
            "P(B_LD4_01)", "V(B_LD4_01)", "P(B_LD4_11)", "V(B_LD4_11)",
            "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
        ],
    ),
    (
        "BVM_INTERNAL_STATE",
        [
            item
            for junction in ("JM1", "JM2", "JS1", "JS2")
            for item in (f"P(B_{junction}|XBVM1)", f"V(B_{junction}|XBVM1)", f"I(B_{junction}|XBVM1)")
        ]
        + ["I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)", "I(L_PM|XBVM1)"],
    ),
    (
        "QB_INTERNAL",
        [
            "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
            "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
            "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
            "I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)",
            "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)",
        ],
    ),
    (
        "JTL_TRANSPORT",
        [
            item
            for stage in range(1, 7)
            for junction in ("B01", "B02")
            for item in (f"P({junction}|XJTL1_{stage})", f"V({junction}|XJTL1_{stage})")
        ],
    ),
))

FOCUSED_PLOTS = OrderedDict((
    (
        "BVM_RLOOP_PASSIVE_NETWORK",
        [
            "I(L_M3|XBVM1)",
            "I(B_JS1|XBVM1)", "I(L_S1|XBVM1)",
            "I(B_JS2|XBVM1)", "I(L_S2|XBVM1)",
            "I(R_SE|XBVM1)", "I(L_PSE|XBVM1)",
            "I(R_S|XBVM1)", "I(L_S3|XBVM1)",
            "I(L_PSL|XBVM1)", "I(R_SL|XBVM1)", "I(L_SL|XBVM1)",
            "I(R_JM1|XBVM1)",
        ],
    ),
    (
        "BVM_RLOOP_PASSIVE_VOLTAGE",
        [
            "V(R_JM1|XBVM1)",
            "V(L_S1|XBVM1)", "V(B_JS1|XBVM1)",
            "V(L_S2|XBVM1)", "V(B_JS2|XBVM1)",
            "V(R_SE|XBVM1)", "V(L_PSE|XBVM1)",
            "V(R_S|XBVM1)", "V(L_S3|XBVM1)",
            "V(L_PSL|XBVM1)", "V(R_SL|XBVM1)", "V(L_SL|XBVM1)",
        ],
    ),
    (
        "BVM_RLOOP_KCL",
        [
            "I(KCL_JM1_shunt_node7)",
            "I(KCL_SE_RLOOP_node6)",
            "I(KCL_RLOOP_output_node10)",
            "I(KCL_SL_series_node11)",
            "I(KCL_SL_series_node12)",
        ],
    ),
))

COMPARISON_PLOTS = OrderedDict((
    (
        "S0_VS_S1_RLOOP_PASSIVE_NETWORK",
        (EXP / "plots/comparison/data/S0_VS_S1_RLOOP_PASSIVE_NETWORK.csv", [
            "I(L_M3|XBVM1) [S0]", "I(L_M3|XBVM1) [S1]",
            "I(R_JM1|XBVM1) [S0]", "I(R_JM1|XBVM1) [S1]",
            "I(R_S|XBVM1) [S0]", "I(R_S|XBVM1) [S1]",
            "I(L_S3|XBVM1) [S0]", "I(L_S3|XBVM1) [S1]",
            "I(R_SL|XBVM1) [S0]", "I(R_SL|XBVM1) [S1]",
            "I(L_SL|XBVM1) [S0]", "I(L_SL|XBVM1) [S1]",
            "P(B_JS1|XBVM1) [S0]", "P(B_JS1|XBVM1) [S1]",
            "P(B_JS2|XBVM1) [S0]", "P(B_JS2|XBVM1) [S1]",
        ]),
    ),
    (
        "S0_VS_S1_RLOOP_KCL",
        (EXP / "plots/comparison/data/S0_VS_S1_RLOOP_KCL.csv", [
            "I(KCL_JM1_shunt_node7) [S0]", "I(KCL_JM1_shunt_node7) [S1]",
            "I(KCL_SE_RLOOP_node6) [S0]", "I(KCL_SE_RLOOP_node6) [S1]",
            "I(KCL_RLOOP_output_node10) [S0]", "I(KCL_RLOOP_output_node10) [S1]",
            "I(KCL_SL_series_node12) [S0]", "I(KCL_SL_series_node12) [S1]",
        ]),
    ),
))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_headers(path: Path) -> list[str]:
    import csv
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle).__next__())


def check_input(path: Path, labels: list[str]) -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from bvmtools.raw import read_csv
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate columns in plot input: {path}: {trace.duplicate_columns}")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"missing plot labels in {path}: {missing}")


def render(input_path: Path, output_path: Path, title: str, labels: list[str]) -> dict[str, object]:
    check_input(input_path, labels)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"plot failed: {output_path}\n{completed.stdout}\n{completed.stderr}")
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"not html: {output_path}")
    if '"title":{"text":"Unknown"}' in html:
        raise RuntimeError(f"Unknown axis in plot: {output_path}")
    if any(label.startswith("P(") for label in labels) and "Phase (turns)" not in html:
        raise RuntimeError(f"phase unit QA failed: {output_path}")
    return {
        "path": str(output_path.relative_to(REPO)),
        "input": str(input_path.relative_to(REPO)),
        "output_sha256": sha256(output_path),
        "input_sha256": sha256(input_path),
        "title": title,
        "labels": labels,
        "command": command,
        "exit_code": completed.returncode,
        "qa": {
            "html": True,
            "unknown_axis_absent": True,
            "phase_display": "rad/(2pi) turns",
            "classic_renderer": True,
        },
    }


def main() -> int:
    raw_before = {condition: sha256(path) for condition, path in CONDITIONS.items()}
    manifest: list[dict[str, object]] = []
    for condition, raw in CONDITIONS.items():
        for name, labels in STANDARD_PLOTS.items():
            manifest.append(render(
                raw,
                EXP / "plots/runs" / condition / f"{name}.html",
                f"{condition} — {name}",
                labels,
            ))
        for name, labels in FOCUSED_PLOTS.items():
            if name == "BVM_RLOOP_KCL":
                derived = EXP / "plots/runs" / condition / "derived/BVM_RLOOP_KCL.csv"
                if not derived.is_file():
                    raise RuntimeError(f"missing derived KCL CSV; run analyze.py first: {derived}")
                input_path = derived
            else:
                input_path = raw
            manifest.append(render(
                input_path,
                EXP / "plots/runs" / condition / f"{name}.html",
                f"{condition} — {name}",
                labels,
            ))

    for name, (input_path, labels) in COMPARISON_PLOTS.items():
        manifest.append(render(
            input_path,
            EXP / "plots/comparison" / f"{name}.html",
            f"S0 vs S1 — {name}",
            labels,
        ))
    raw_after = {condition: sha256(path) for condition, path in CONDITIONS.items()}
    if raw_before != raw_after:
        raise RuntimeError("raw hash changed during plotting")
    manifest_record = {
        "schema": "bvm-jm2-connected-rloop-plot-manifest-v1",
        "renderer": "scripts/josim-plot2.py",
        "layout": "sep_comb",
        "color": "dark",
        "phase": "2pi",
        "raw_hash_before": raw_before,
        "raw_hash_after": raw_after,
        "raw_unchanged": True,
        "plots": manifest,
    }
    (EXP / "analysis/plot_manifest.json").write_text(
        json.dumps(manifest_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "plot_count": len(manifest), "raw_unchanged": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
