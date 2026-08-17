#!/usr/bin/env python3
"""render_timing_report.py -- deterministic timing report renderer (A02).

Renders report.md from analysis.json (structured result) and the frozen
preregistration identity: run_id, frozen spec identity, disposition,
JM1/JM2 p2p by all registered windows, A/B Delta/readiness contrasts, and
the bounded no-mechanism claim ceiling.  Deterministic: same input bytes ->
same output bytes.
"""
import json
import pathlib
import sys

RUN = pathlib.Path(__file__).resolve().parent


def render(analysis: dict) -> str:
    lines = [
        f"# {analysis['run_id']} — BVM S2 initialization rising-edge timing",
        "",
        f"- run_id: {analysis['run_id']}",
        "- frozen spec identity: bvm-s2-timing-preregistration-v1 "
        "(task JH-20260817-BVM-S2-TIMING-001, "
        "design/preregistration.yaml + design/analysis-schema.json)",
        f"- metric spec: readiness threshold "
        f"{analysis['metric_spec']['readiness_threshold_rad']} rad; "
        "half-open actual CSV time windows; Decimal exact timestamps",
        f"- disposition: {analysis['disposition']}",
        f"- provenance: {analysis['provenance']['binary']} "
        f"({analysis['provenance']['version']}), dt="
        f"{analysis['provenance']['timestep_ps']} ps, tstop="
        f"{analysis['provenance']['tstop_ps']} ps, R_LD=12 ohm, no read",
        "",
        "## JM1/JM2 phase p2p (rad) by registered window",
        "",
        "| run | timing | polarity | window | JM1 p2p | JM2 p2p |",
        "|---|---|---|---|---|---|",
    ]
    for e in analysis["runs"]:
        for wname in ("settling_early", "settling_mid", "settling_late",
                      "readiness"):
            w = e["windows"][wname]
            lines.append(
                f"| {e['id']} | {e['timing']} | {e['polarity']} | "
                f"{wname} | {w['jm1_p2p_rad']} | {w['jm2_p2p_rad']} |")
    lines += [
        "",
        "## Readiness (co-primary, both JM1 and JM2 <= 0.020 rad in "
        "[80,90) ps)",
        "",
        "| run | timing | polarity | co-primary ready |",
        "|---|---|---|---|",
    ]
    for e in analysis["runs"]:
        lines.append(
            f"| {e['id']} | {e['timing']} | {e['polarity']} | "
            f"{e['readiness']['co_primary_ready']} |")
    lines += [
        "",
        "## A/B contrasts (Delta = S1_REGISTERED - S2_REGISTERED, "
        "[80,90) ps)",
        "",
        "| polarity | Delta JM2 (rad) | |Delta JM2| >= 0.020 | "
        "readiness classification changed |",
        "|---|---|---|---|",
    ]
    for pol in ("positive", "negative"):
        c = analysis["contrasts"][pol]
        lines.append(
            f"| {pol} | {c['delta_jm2_readiness_p2p_rad']} | "
            f"{c['abs_delta_jm2_ge_threshold']} | "
            f"{c['readiness_classification_changed']} |")
    lines += [
        "",
        "## Claim ceiling",
        "",
        "- Bounded fixed-closure, fixed-grid evidence for or against a "
        "reproducible association of the registered initialization "
        "rising-edge intervention with JM1/JM2 pre-read "
        "settling/readiness only.",
        "- No detailed physical mechanism, convergence, logical-state, "
        "preservation, load-back-action, receiver, SFQ, fluxoid, "
        "interface, route, hardware, or universal claim.",
        f"- Disposition: {analysis['disposition']}.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    analysis = json.loads((RUN / "analysis.json").read_text(encoding="utf-8"))
    report = render(analysis)
    (RUN / "report.md").write_text(report, encoding="utf-8")
    if "--check" in sys.argv:
        current = (RUN / "report.md").read_text(encoding="utf-8")
        if current != report:
            print("REPORT INCONSISTENT")
            return 1
        print("REPORT CONSISTENT")
        return 0
    print(f"rendered {RUN.name}/report.md ({len(report)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
