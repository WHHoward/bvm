#!/usr/bin/env python3
"""Verify result/plot/index/topology alignment without running JoSIM.

The verifier treats the alignment manifest as the only mapping authority.  A
plot directory containing an arbitrary HTML file is never used as a
completeness signal.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    "RESULT", "COMPARISON", "POSITIVE_CONTROL", "NEGATIVE_CONTROL",
    "ZERO_CONTROL", "SOURCE_REFERENCE", "HISTORICAL_REFERENCE",
    "SUPERSEDED_REFERENCE",
}
PHASES = {"continuous_absolute", "relative_to_baseline", "event_delta", "settled_well"}
EXPECTED_EXPERIMENT_KEYS = {
    "scientific_question", "formal_result", "required_cases", "required_signals",
    "what_done", "result_summary", "conclusion_boundary",
    "plots", "report", "current_status",
}


def _fail(messages: list[str], message: str) -> None:
    messages.append(message)


def _case_coverage(entry: dict[str, Any]) -> set[str]:
    coverage: set[str] = set()
    for plot in entry.get("plots", []):
        coverage.update(str(x) for x in plot.get("cases", []))
    return coverage


def _is_phase_plot(plot: dict[str, Any]) -> bool:
    if plot.get("phase_semantics"):
        return True
    name = str(plot.get("path", "")).lower()
    return any(token in name for token in ("phase", "comparison", "overview", "replay", "timestep"))


def validate_manifest(manifest: dict[str, Any], *, root: Path = ROOT,
                      topology_manifest: dict[str, Any] | None = None,
                      index_paths: tuple[Path, Path] | None = None) -> dict[str, Any]:
    errors: dict[str, list[str]] = {
        "result_alignment": [], "topology_alignment": [], "schematic_alignment": [],
        "index_alignment": [], "phase_semantics": [],
    }
    experiments = manifest.get("experiments", [])
    if not isinstance(experiments, list) or not experiments:
        _fail(errors["result_alignment"], "manifest.experiments must be a non-empty list")
        experiments = []
    ids: set[str] = set()
    for entry in experiments:
        exp_id = entry.get("experiment_id", "<missing-id>")
        if exp_id in ids:
            _fail(errors["result_alignment"], f"duplicate experiment_id: {exp_id}")
        ids.add(exp_id)
        missing = EXPECTED_EXPERIMENT_KEYS - set(entry)
        if missing:
            _fail(errors["result_alignment"], f"{exp_id}: missing fields {sorted(missing)}")
        for narrative_field in ("what_done", "result_summary", "conclusion_boundary"):
            if not str(entry.get(narrative_field, "")).strip():
                _fail(errors["result_alignment"], f"{exp_id}: empty narrative field {narrative_field}")
        required = entry.get("required_cases", [])
        if not isinstance(required, list):
            _fail(errors["result_alignment"], f"{exp_id}: required_cases is not a list")
            required = []
        required_ids = {str(c.get("id")) for c in required}
        for case in required:
            raw = case.get("raw")
            if not raw or not (root / raw).exists():
                _fail(errors["result_alignment"], f"{exp_id}: missing raw provenance {raw}")
        for plot in entry.get("plots", []):
            path = plot.get("path")
            if not path or not (root / path).exists():
                _fail(errors["result_alignment"], f"{exp_id}: missing plot {path}")
            role = plot.get("role")
            if role not in ROLES:
                _fail(errors["result_alignment"], f"{exp_id}: invalid plot role {role!r}")
            if _is_phase_plot(plot) and plot.get("phase_semantics") not in PHASES:
                _fail(errors["phase_semantics"], f"{exp_id}: phase plot {path} lacks valid phase_semantics")
            if role in {"RESULT", "COMPARISON"} and str(plot.get("source_classification", "")).upper() in {
                "PAPER_REFERENCE", "HISTORICAL_REFERENCE", "SUPERSEDED_M5_INTERPRETATION",
            }:
                _fail(errors["result_alignment"], f"{exp_id}: reference/superseded plot linked as current result {path}")
            if role in {"RESULT", "COMPARISON"} and str(plot.get("source_classification", "")).startswith("PAPER_REFERENCE"):
                _fail(errors["result_alignment"], f"{exp_id}: paper reference cannot be core evidence {path}")
        if required and not any(p.get("role") in {"RESULT", "COMPARISON"} for p in entry.get("plots", [])):
            _fail(errors["result_alignment"], f"{exp_id}: required waveform cases have no RESULT/COMPARISON plot")
        coverage = _case_coverage(entry)
        # Cross-experiment comparison entries use aliases such as Q2/Q3; an
        # experiment's own case-complete alignment-overview must still cover
        # its required raw cases.
        missing_cases = sorted(required_ids - coverage)
        if missing_cases:
            _fail(errors["result_alignment"], f"{exp_id}: required cases not visualized: {missing_cases}")
        claim = entry.get("claim_type")
        plots = entry.get("plots", [])
        comp_cases = set().union(*(set(p.get("cases", [])) for p in plots)) if plots else set()
        if claim == "bias_comparison" and not ("37p5u" in " ".join(comp_cases) and "40u" in " ".join(comp_cases)):
            _fail(errors["result_alignment"], f"{exp_id}: bias comparison lacks both 37.5 and 40 µA")
        if claim == "factorial_point" and not {"Q2", "Q3", "Q4", "Q5"}.issubset(comp_cases):
            _fail(errors["result_alignment"], f"{exp_id}: factorial comparison lacks Q2/Q3/Q4/Q5")
        if claim == "load_matrix":
            required_labels = {"Q0 + 10Ω (accepted)", "Q0 OPEN", "Q0 JTL-only", "Q0 10Ω || JTL"}
            if not required_labels.issubset(comp_cases):
                _fail(errors["result_alignment"], f"{exp_id}: load matrix lacks {sorted(required_labels - comp_cases)}")
        if claim == "polarity_convergence":
            if not {"r11", "pulse5-original", "pulse5-reverse"}.issubset(comp_cases):
                _fail(errors["result_alignment"], f"{exp_id}: polarity/convergence set incomplete")
        if claim == "conditioning_matrix":
            if not {"raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20"}.issubset(comp_cases):
                _fail(errors["result_alignment"], f"{exp_id}: R13 raw/C1/C2/C3 comparison incomplete")
        # Analysis-only provenance checkpoints may intentionally have no raw
        # waveform package and therefore no independent formal report.  They
        # remain visible in execution order, but cannot claim a result.
        analysis_only = entry.get("current_status") == "NO_WAVEFORM_VISUALIZATION_REQUIRED" or entry.get("claim_type") == "analysis_only"
        if not analysis_only and (not entry.get("report") or not (root / str(entry.get("report"))).exists()):
            _fail(errors["result_alignment"], f"{exp_id}: formal report missing")

    if topology_manifest is None:
        topology_manifest = {"topologies": []}
    topologies = {t.get("topology_id"): t for t in topology_manifest.get("topologies", [])}
    for entry in experiments:
        exp_id = entry.get("experiment_id")
        topo_id = entry.get("topology_id")
        topo = topologies.get(topo_id)
        if topo is None:
            _fail(errors["topology_alignment"], f"{exp_id}: topology_id {topo_id!r} absent")
            continue
        if exp_id not in topo.get("shared_by_experiments", []):
            _fail(errors["topology_alignment"], f"{exp_id}: topology {topo_id!r} is not declared shared by this experiment")
        expected_signature = entry.get("topology_signature")
        if expected_signature and expected_signature != topo.get("topology_signature"):
            _fail(errors["topology_alignment"], f"{exp_id}: indexed topology signature differs from linked schematic topology")
        pub = topo.get("publication_schematic")
        if pub:
            if str(pub).endswith(("topology.svg", "topology.dot", "connectivity-debug.svg", "connectivity-debug.dot")):
                _fail(errors["schematic_alignment"], f"{exp_id}: Graphviz/debug artifact marked publication schematic: {pub}")
            if not (root / pub).exists():
                _fail(errors["schematic_alignment"], f"{exp_id}: publication schematic missing: {pub}")
            for field in ("semantic_validation", "geometric_validation"):
                validation = topo.get(field)
                if not validation or not (root / validation).exists():
                    _fail(errors["schematic_alignment"], f"{exp_id}: {field} missing for publication schematic")
                else:
                    try:
                        data = json.loads((root / validation).read_text(encoding="utf-8"))
                        text = json.dumps(data).upper()
                        if "PASS" not in text and data not in ({"valid": True}, {"status": "PASS"}):
                            _fail(errors["schematic_alignment"], f"{exp_id}: {field} does not report PASS")
                    except (OSError, json.JSONDecodeError) as exc:
                        _fail(errors["schematic_alignment"], f"{exp_id}: invalid {field}: {exc}")
        debug = topo.get("connectivity_debug")
        if debug and not (root / debug).exists():
            _fail(errors["topology_alignment"], f"{exp_id}: debug graph missing: {debug}")
        for variant in entry.get("topology_variants", []):
            variant_id = variant.get("topology_id")
            variant_topo = topologies.get(variant_id)
            if variant_topo is None:
                _fail(errors["topology_alignment"], f"{exp_id}: topology variant {variant_id!r} absent")
                continue
            if exp_id not in variant_topo.get("shared_by_experiments", []):
                _fail(errors["topology_alignment"], f"{exp_id}: topology variant {variant_id!r} is not declared shared")
            representative = variant.get("representative_deck")
            if not representative or not (root / representative).exists():
                _fail(errors["topology_alignment"], f"{exp_id}: missing variant representative deck {representative}")
            if variant.get("topology_signature") and variant.get("topology_signature") != variant_topo.get("topology_signature"):
                _fail(errors["topology_alignment"], f"{exp_id}: variant {variant_id!r} signature mismatch")
            variant_debug = variant.get("connectivity_debug")
            if variant_debug and not (root / variant_debug).exists():
                _fail(errors["topology_alignment"], f"{exp_id}: variant debug graph missing: {variant_debug}")

    if index_paths:
        md_flow, html_flow = index_paths
        md_text = md_flow.read_text(encoding="utf-8") if md_flow.exists() else ""
        html_text = html_flow.read_text(encoding="utf-8") if html_flow.exists() else ""
        for entry in experiments:
            exp_id = entry.get("experiment_id", "")
            core = next((p.get("path") for p in entry.get("plots", []) if p.get("role") in {"COMPARISON", "RESULT"}), None)
            if exp_id not in md_text or exp_id not in html_text:
                _fail(errors["index_alignment"], f"{exp_id}: absent from generated MD/HTML index")
            if core and (core not in md_text or core not in html_text):
                _fail(errors["index_alignment"], f"{exp_id}: core plot differs/missing across MD and HTML indexes: {core}")
            topo = topologies.get(entry.get("topology_id"), {})
            for topo_path in (topo.get("publication_schematic"), topo.get("annotated_schematic"), topo.get("connectivity_debug")):
                if topo_path and (topo_path not in md_text or topo_path not in html_text):
                    _fail(errors["index_alignment"], f"{exp_id}: topology link differs/missing across MD and HTML indexes: {topo_path}")
            for variant in entry.get("topology_variants", []):
                for variant_path in (variant.get("publication_schematic"), variant.get("annotated_schematic"), variant.get("connectivity_debug")):
                    if variant_path and (variant_path not in md_text or variant_path not in html_text):
                        _fail(errors["index_alignment"], f"{exp_id}: topology variant link differs/missing across MD and HTML indexes: {variant_path}")

    result = {name: "PASS" if not messages else {"status": "FAIL", "errors": messages} for name, messages in errors.items()}
    result["overall"] = "PASS" if all(value == "PASS" for value in result.values()) else "FAIL"
    result["experiment_count"] = len(experiments)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=ROOT / "docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml")
    ap.add_argument("--topology", type=Path, default=ROOT / "docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml")
    ap.add_argument("--output", type=Path, default=ROOT / "visualization-alignment-validation.json")
    args = ap.parse_args()
    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    topology = yaml.safe_load(args.topology.read_text(encoding="utf-8")) if args.topology.exists() else {"topologies": []}
    result = validate_manifest(manifest, root=ROOT, topology_manifest=topology,
                               index_paths=(ROOT / "docs/EXPLORATION_FLOW_INDEX.md", ROOT / "docs/EXPLORATION_FLOW_INDEX.html"))
    # Check the visualization index in a second pass as well; the same core
    # entries must be present in both independently named pages.
    viz_result = validate_manifest(manifest, root=ROOT, topology_manifest=topology,
                                   index_paths=(ROOT / "docs/VISUALIZATION_INDEX.md", ROOT / "docs/VISUALIZATION_INDEX.html"))
    if viz_result["index_alignment"] != "PASS":
        result["index_alignment"] = viz_result["index_alignment"]
        result["overall"] = "FAIL"
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
