#!/usr/bin/env python3
"""Render JM2-connected plots with the corrected single-BVM visual authority."""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
REFERENCE_EXP = REPO / "test/exploration/bvmsim-single-corrected-baseline-v1-20260903"
REFERENCE_RENDERER = REFERENCE_EXP / "analysis/render_plots.py"
REFERENCE_INTERNAL_RENDERER = REFERENCE_EXP / "analysis/render_bvm_internal_state.py"

CONDITIONS = OrderedDict(
    (
        ("S0-R-JM2C", {
            "raw": EXP / "runs/S0-R-JM2C/raw/run-01.csv",
            "reference": REFERENCE_EXP / "runs/S0-R-CORRECTED/raw/run-01.csv",
            "load": "direct_10ohm",
            "state": 0,
            "jtl": False,
        }),
        ("S1-R-JM2C", {
            "raw": EXP / "runs/S1-R-JM2C/raw/run-01.csv",
            "reference": REFERENCE_EXP / "runs/S1-R-CORRECTED/raw/run-01.csv",
            "load": "direct_10ohm",
            "state": 1,
            "jtl": False,
        }),
        ("S0-J-JM2C", {
            "raw": EXP / "runs/S0-J-JM2C/raw/run-01.csv",
            "reference": REFERENCE_EXP / "runs/S0-J-CORRECTED-RERUN/raw/run-01.csv",
            "load": "six_stage_jtl_plus_10ohm",
            "state": 0,
            "jtl": True,
        }),
        ("S1-J-JM2C", {
            "raw": EXP / "runs/S1-J-JM2C/raw/run-01.csv",
            "reference": REFERENCE_EXP / "runs/S1-J-CORRECTED-RERUN/raw/run-01.csv",
            "load": "six_stage_jtl_plus_10ohm",
            "state": 1,
            "jtl": True,
        }),
    )
)

BVM_INTERNAL_STATE = [
    f"{kind}(B_{junction}|XBVM1)"
    for junction in ("JM1", "JM2", "JS1", "JS2")
    for kind in ("P", "V", "I")
] + [
    "V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
    "P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)",
    "P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)",
    "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
]

PLOTS = OrderedDict(
    (
        (
            "BVM_STIMULUS_AND_STATE",
            (["I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "P(BVMOUT)"],
             "Corrected single-BVM stimulus and state — WRITE WL+BL; READ WL+SE (BL=0)"),
        ),
        (
            "BVM_SENSING",
            ([
                "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "P(B_JS2|XBVM1)",
                "V(SL1)", "I(L_SL|XBVM1)", "P(B_LD4_01)", "V(B_LD4_01)",
                "P(B_LD4_11)", "V(B_LD4_11)", "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
            ], "Corrected single-BVM sensing line and terminal response"),
        ),
        ("BVM_INTERNAL_STATE", (BVM_INTERNAL_STATE, "complete BVM internal JJ state and SL boundary")),
        (
            "QB_INTERNAL",
            ([
                "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
                "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
                "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
                "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)",
                "I(L1|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)", "I(IB|XBQ1)",
            ], "Original QB internal phase, voltage and current probes"),
        ),
        (
            "QB_BURST",
            ([
                "V(QBIN)", "V(QBOUT)", "P(BJS|XBQ1)", "V(BJS|XBQ1)",
                "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)",
            ], "Original QB READ-associated response — phase is rad/(2pi) turns"),
        ),
        (
            "JTL_TRANSPORT",
            ([
                item
                for stage in range(1, 7)
                for item in (
                    f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})",
                    f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})",
                )
            ], "Six-stage historical JTL transport — B01/B02 phase and voltage"),
        ),
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_input(path: Path, labels: list[str]) -> RawTrace:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns require explicit occurrence: {path}: {trace.duplicate_columns}")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{path}: missing plot labels: {missing}")
    return trace


def render(input_path: Path, output_path: Path, title: str, labels: list[str]) -> dict[str, object]:
    command = [
        sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels,
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"josim-plot2 failed for {output_path}: exit={completed.returncode}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"not an HTML file: {output_path}")
    if re.search(r'"title":\{"text":"Unknown"\}', html):
        raise RuntimeError(f"Unknown axis in plot: {output_path}")
    if any(label.startswith("P(") for label in labels) and "Phase (turns)" not in html:
        raise RuntimeError(f"phase unit QA failed: {output_path}")
    return {
        "path": str(output_path.relative_to(REPO)),
        "input": str(input_path.relative_to(REPO)),
        "input_sha256": sha256(input_path),
        "output_sha256": sha256(output_path),
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


def comparison_csv(path: Path, reference: RawTrace, connected: RawTrace, labels: list[str]) -> list[str]:
    if not exact_time_grid_identity(reference.time, connected.time):
        raise RuntimeError(
            f"A/B comparison requires exact time-grid identity; no interpolation: {path.name}"
        )
    output_labels: list[str] = []
    for label in labels:
        output_labels.extend((f"{label} [JM2-OMITTED]", f"{label} [JM2-CONNECTED]"))
    rows = ["time," + ",".join(output_labels)]
    for index, time in enumerate(reference.time):
        values: list[str] = []
        for label in labels:
            values.extend((str(reference.column(label)[index]), str(connected.column(label)[index])))
        rows.append(",".join([str(time), *values]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return output_labels


COMPARISON_GROUPS = OrderedDict(
    (
        ("BVM_INTERNAL", BVM_INTERNAL_STATE),
        ("SENSING", PLOTS["BVM_SENSING"][0]),
        ("QB", PLOTS["QB_INTERNAL"][0]),
        ("JTL_TRANSPORT", PLOTS["JTL_TRANSPORT"][0]),
    )
)

DIRECT_GROUPS = ("BVM_INTERNAL", "SENSING", "QB")
JTL_GROUPS = ("BVM_INTERNAL", "SENSING", "QB", "JTL_TRANSPORT")
NEW_JTL_GROUPS = ("BVM_INTERNAL", "SENSING", "QB")


def comparison_specs() -> list[dict[str, Any]]:
    """Return the complete comparison matrix, including the six new JTL-load pages."""
    specs: list[dict[str, Any]] = []

    def add_group(load_family: str, group: str, state: int) -> None:
        state_name = f"S{state}"
        condition = f"{state_name}-R-JM2C" if load_family == "direct" else f"{state_name}-J-JM2C"
        legacy_jtl_name = load_family == "jtl" and group == "JTL_TRANSPORT"
        suffix = "" if load_family == "direct" or legacy_jtl_name else "_JTL"
        output_group = "JTL" if legacy_jtl_name else group
        specs.append({
            "name": f"{state_name}_JM2_OMITTED_VS_CONNECTED_{output_group}{suffix}",
            "condition": condition,
            "state": state,
            "load_family": load_family,
            "load": CONDITIONS[condition]["load"],
            "group": group,
            "labels": list(COMPARISON_GROUPS[group]),
            "new_in_task": load_family == "jtl" and group in NEW_JTL_GROUPS,
        })

    # Preserve the old eight comparison names and their logical grouping first.
    for group in DIRECT_GROUPS:
        for state in (0, 1):
            add_group("direct", group, state)
    for group in ("JTL_TRANSPORT",):
        for state in (0, 1):
            add_group("jtl", group, state)

    # Append only the new load-aware views; they use the JTL A/B raw pair.
    for group in NEW_JTL_GROUPS:
        for state in (0, 1):
            add_group("jtl", group, state)
    return specs


def comparison_coverage() -> dict[str, dict[str, list[str]]]:
    """Return the declared direct/JTL signal-group coverage matrix."""
    return {
        "direct": {
            "S0": list(DIRECT_GROUPS),
            "S1": list(DIRECT_GROUPS),
        },
        "jtl": {
            "S0": list(JTL_GROUPS),
            "S1": list(JTL_GROUPS),
        },
    }


def initial_raw_hashes() -> dict[str, str]:
    raw_hashes: dict[str, str] = {}
    for condition, info in CONDITIONS.items():
        raw_hashes[condition] = sha256(info["raw"])
        raw_hashes[f"reference:{condition}"] = sha256(info["reference"])
    return raw_hashes


def check_raw_hashes_unchanged(raw_hashes: dict[str, str]) -> None:
    for condition, info in CONDITIONS.items():
        if sha256(info["raw"]) != raw_hashes[condition] or sha256(info["reference"]) != raw_hashes[f"reference:{condition}"]:
            raise RuntimeError(f"raw hash changed during plotting: {condition}")


def render_comparison_spec(
    spec: dict[str, Any],
    traces: dict[str, RawTrace],
    reference_traces: dict[str, RawTrace],
    refuse_existing: bool = False,
) -> dict[str, object]:
    name = str(spec["name"])
    condition = str(spec["condition"])
    labels = list(spec["labels"])
    derived = EXP / "plots/comparison/data" / f"{name}.csv"
    output = EXP / "plots/comparison" / f"{name}.html"
    if refuse_existing and (derived.exists() or output.exists()):
        raise RuntimeError(f"refusing to overwrite existing new comparison artifact: {name}")

    comparison_labels = comparison_csv(derived, reference_traces[condition], traces[condition], labels)
    if spec["new_in_task"]:
        title = (
            f"{condition.split('-')[0]} — JM2 omitted vs connected — "
            f"{spec['group']} — JTL load"
        )
    else:
        title = f"{condition.split('-')[0]} — JM2 omitted vs connected — {name.rsplit('_', 1)[-1]}"
    record = render(derived, output, title, comparison_labels)
    record.update({
        "comparison": True,
        "reference_role": "JM2-OMITTED",
        "connected_role": "JM2-CONNECTED",
        "derived_csv": str(derived.relative_to(REPO)),
        "derived_csv_sha256": sha256(derived),
        "base_signal_order": labels,
        "state": spec["state"],
        "load_family": spec["load_family"],
        "load": spec["load"],
        "signal_group": spec["group"],
        "new_in_task": spec["new_in_task"],
    })
    return record


def base_manifest(
    raw_hashes: dict[str, str],
    standalone: list[dict[str, object]],
    comparisons: list[dict[str, object]],
    run_mode: str,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = dict(previous) if previous is not None else {}
    manifest.update({
        "schema": "bvmsim-jm2-connected-visual-manifest-v1",
        "experiment": "bvmsim-jm2-connected-single-ab-v1-20260903",
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_sha256": sha256(PLOTTER),
        "visual_authority": {
            "reference_experiment": str(REFERENCE_EXP.relative_to(REPO)),
            "reference_renderer": str(REFERENCE_RENDERER.relative_to(REPO)),
            "reference_renderer_sha256": sha256(REFERENCE_RENDERER),
            "reference_internal_state_renderer": str(REFERENCE_INTERNAL_RENDERER.relative_to(REPO)),
            "reference_internal_state_renderer_sha256": sha256(REFERENCE_INTERNAL_RENDERER),
            "layout": "sep_comb",
            "color": "dark",
            "phase_option": "2pi",
            "same_signal_order": True,
        },
        "phase_display": "P(...) raw radians displayed as rad/(2*pi) turns",
        "raw_unchanged": True,
        "raw_sha256": raw_hashes,
        "standalone": standalone,
        "comparisons": comparisons,
        "comparison_coverage": comparison_coverage(),
        "new_comparison_count": sum(1 for item in comparisons if item.get("new_in_task") is True),
        "total_comparison_count": len(comparisons),
        "simulation_invoked": False,
        "run_mode": run_mode,
        "comparison_limitations": {
            "unavailable_on_omitted_reference": [
                "I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)", "I(L_PM|XBVM1)"
            ],
            "reason": "immutable corrected baseline raw was not rerun and does not contain these four probes",
            "no_interpolation": True,
        },
    })
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only-new-jtl-comparisons",
        action="store_true",
        help="append the six JTL-load A/B pages without regenerating standalone or existing pages",
    )
    args = parser.parse_args()

    traces: dict[str, RawTrace] = {}
    reference_traces: dict[str, RawTrace] = {}
    raw_hashes = initial_raw_hashes()
    plots: list[dict[str, object]] = []
    manifest_path = EXP / "analysis/plot_manifest.json"
    previous_manifest: dict[str, Any] | None = None

    if args.only_new_jtl_comparisons:
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        specs = comparison_specs()
        expected_existing = {str(spec["name"]) for spec in specs if not spec["new_in_task"]}
        existing_names = {
            Path(str(record["path"])).stem
            for record in previous_manifest.get("comparisons", [])
        }
        missing = sorted(expected_existing - existing_names)
        if missing:
            raise RuntimeError(f"existing comparison manifest is incomplete: {missing}")
        for key, value in previous_manifest.get("raw_sha256", {}).items():
            if raw_hashes.get(key) != value:
                raise RuntimeError(f"raw hash differs from existing manifest: {key}")

        selected_specs = [spec for spec in specs if spec["new_in_task"]]
        selected_conditions = ["S0-J-JM2C", "S1-J-JM2C"]
        for condition in selected_conditions:
            labels = sorted({
                label
                for spec in selected_specs
                if spec["condition"] == condition
                for label in spec["labels"]
            })
            info = CONDITIONS[condition]
            traces[condition] = check_input(info["raw"], labels)
            reference_traces[condition] = check_input(info["reference"], labels)

        existing_comparisons = list(previous_manifest["comparisons"])
        new_comparisons = [
            render_comparison_spec(spec, traces, reference_traces, refuse_existing=True)
            for spec in selected_specs
        ]
        comparisons = existing_comparisons + new_comparisons
        manifest = base_manifest(
            raw_hashes,
            list(previous_manifest.get("standalone", [])),
            comparisons,
            "append-new-jtl-load-comparisons",
            previous_manifest,
        )
        generated_count = len(new_comparisons)
    else:
        specs = comparison_specs()
        # Standalone B-side plots are deliberately completed before any A/B page.
        for condition, info in CONDITIONS.items():
            all_labels = sorted(set(
                label
                for name, (labels, _) in PLOTS.items()
                if name != "JTL_TRANSPORT" or info["jtl"]
                for label in labels
            ))
            trace = check_input(info["raw"], all_labels)
            traces[condition] = trace
            for name, (labels, description) in PLOTS.items():
                if name == "JTL_TRANSPORT" and not info["jtl"]:
                    continue
                title = (
                    f"{condition} — complete BVM internal JJ state and SL boundary"
                    if name == "BVM_INTERNAL_STATE"
                    else f"{description} — {condition}"
                )
                output = EXP / "plots/runs" / condition / f"{name}.html"
                plots.append(render(info["raw"], output, title, labels))

            reference_traces[condition] = check_input(info["reference"], all_labels)

        comparisons = [
            render_comparison_spec(spec, traces, reference_traces)
            for spec in specs
        ]
        manifest = base_manifest(
            raw_hashes,
            plots,
            comparisons,
            "full-regeneration",
        )
        generated_count = len(comparisons)

    check_raw_hashes_unchanged(raw_hashes)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "standalone_plots": len(plots),
        "generated_comparison_plots": generated_count,
        "total_comparison_plots": len(manifest["comparisons"]),
        "raw_unchanged": True,
        "simulation_invoked": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
