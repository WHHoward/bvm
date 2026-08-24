#!/usr/bin/env python3
"""Build the V2 visualization/topology manifests and human indexes.

The manifests are the source for both indexes.  This script only reads
existing reports, raw CSV paths, plots, and schematic artifacts; it never
invokes JoSIM and never edits a scientific circuit or raw output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

import yaml

from render_alignment_ui import render_index as render_rich_index
from render_alignment_ui import render_topology_index


ROOT = Path(__file__).resolve().parents[1]
# The documentation-only alignment rebuild is anchored to the repository HEAD
# that was present when this task started.  It is deliberately not replaced by
# the post-generation commit hash.
HEAD = "3e714f3fdd593511971136ee470ec0418d775d24"
MANIFEST_PATH = ROOT / "docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml"
TOPOLOGY_PATH = ROOT / "docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml"

PHASE_SEMANTICS = {
    "continuous_absolute": "原始 JoSIM P(t)/(2π) 连续相位轨迹；未基线相减、未按脉冲归零；不等于 SFQ 计数。",
    "relative_to_baseline": "相对登记 baseline 的 [P(t)-P_pre]/(2π)。",
    "event_delta": "登记同一 JJ、同一 monotonic segment 的 ΔP/(2π)。",
    "settled_well": "pre/post 稳定势阱变化 Δn；不能由连续轨迹本身替代。",
}


# The indexes are a research narrative, not a lexical directory listing.
# Keep the sequence explicit so a newly added directory cannot silently move
# an old result to a different place in the story.
EXPERIMENT_ORDER = [
    "bvm-internal-readout-20260819",
    "bvm-sfq-receiver-r0-20260819",
    "bvm-sfq-receiver-r0b-20260819",
    "bvm-sfq-receiver-r1-oneshot-20260819",
    "bvm-sfq-receiver-r1a-transfer-20260819",
    "bvm-sfq-receiver-r1b-output-jj-20260819",
    "bvm-sfq-receiver-r1b-area008-20260821",
    "bvm-sfq-receiver-r1b-differential-output-20260821",
    "bvm-sfq-receiver-r1c-bias-margin-20260821",
    "bvm-sfq-receiver-r2a-coupling-20260821",
    "bvm-sfq-receiver-r2b-damping-20260821",
    "bvm-sfq-receiver-r2c-directdrive-20260821",
    "bvm-sfq-receiver-r2d-duration-20260821",
    "bvm-sfq-receiver-r2e-ampthreshold-20260821",
    "bvm-sfq-receiver-r2f-dwell-20260821",
    "bvm-sfq-receiver-r2g-twopulse-20260821",
    "bvm-sfq-receiver-r3a-onset-extraction-20260822",
    "bvm-sfq-receiver-r4a-weak-mutual-capture-20260822",
    "bvm-sfq-receiver-r5a-biased-quantizer-20260822",
    "bvm-sfq-receiver-r5b-loadline-20260822",
    "bvm-sfq-receiver-r5c-saddle-selectivity-20260822",
    "bvm-sfq-receiver-native-qb-20260822",
    "bvm-sfq-receiver-r6a-native-qb-isolation-20260822",
    "bvm-sfq-receiver-r6b-native-qb-ratio-20260822",
    "bvm-sfq-receiver-r7a-l1-routing-20260823",
    "bvm-sfq-receiver-r8-bjl2-area070-20260823",
    "bvm-sfq-receiver-r9a-l2-routing-20260823",
    "bvm-sfq-receiver-r10a-local-bjl2-bias-20260823",
    "bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823",
    "bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823",
    "bvm-sfq-receiver-r13a-temporal-conditioning-20260823",
    "bvm-sfq-receiver-r14a-dcsfq-detector-20260823",
    "bvm-sfq-receiver-r15a-afq3-20260823",
    "bvm-sfq-receiver-r15b-magnetic-correction-20260823",
    "bvm-sfq-receiver-r15c-jset-causal-20260823",
    "bvm-sfq-receiver-r15d-jq-compressor-20260823",
    "qb-q0-standalone-current-quantized-event-20260824",
    "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824",
    "qb-q2a-source-decoupled-waveform-replay-20260824",
    "qb-q2b-central-bias-bracketing-20260824",
    "qb-q2c-uniform-junction-scale-20260824",
    "paper-sl-l0-20260824",
    "paper-sl-q1-20260824",
    "paper-sl-q2-20260824",
    "paper-sl-q3-pre-20260824",
    "q3-l1-routing-closure-20260824",
    "paper-sl-q3-l1-routing-closure-20260824",
    "paper-sl-q4-l1-l2-placement-20260824",
    "paper-sl-q5-l1-l2-factorial-20260824",
    "paper-sl-q6-qb-jtl-compatibility-20260824",
    "qb-load-boundary-matrix-20260824",
    "parallel-qb-jtl-interface-mechanism-20260824",
    "jtl-transport-gate-polarity-replay-20260824",
    "jtl-transport-gate-v1-methodology-20260824",
    "jtl-transport-gate-v1-numerical-freeze-20260824",
    "jtl-transport-gate-v1-numerical-freeze-20260824-rerun",
    "qb-to-jtl-load-backaction-causal-audit-v1-20260824",
]

STAGE_DEFINITIONS = [
    ("stage-00", "基础 source：canonical BVM readout", range(1, 2)),
    ("stage-01", "R0–R1：trigger / passive transfer", range(2, 10)),
    ("stage-02", "R2：direct receiver feasibility", range(10, 17)),
    ("stage-03", "R3–R5：capture / quantizer closure", range(17, 22)),
    ("stage-04", "R6–R10：native QB isolation / routing", range(22, 29)),
    ("stage-05", "R11–R15：direct JTL / active-stage route", range(29, 37)),
    ("stage-06", "QB-Q0–Q2：standalone scaled QB", range(37, 42)),
    ("stage-07", "PAPER-SL：JSL waveform → QB", range(42, 51)),
    ("stage-08", "QB output boundary / JTL transport", range(51, 58)),
]


def order_metadata(name: str) -> tuple[int, str, str]:
    """Return one-based execution order and stage metadata."""
    try:
        number = EXPERIMENT_ORDER.index(name) + 1
    except ValueError:
        number = len(EXPERIMENT_ORDER) + 1
    for stage_id, title, positions in STAGE_DEFINITIONS:
        if number in positions:
            return number, stage_id, title
    return number, "stage-99", "其它 / 后续补充"


def ordered_entries(entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for name, entry in entries.items():
        sequence, stage_id, stage_title = order_metadata(Path(name).name)
        entry.setdefault("sequence", sequence)
        entry.setdefault("stage_id", stage_id)
        entry.setdefault("stage_title", stage_title)
    return sorted(entries.values(), key=lambda e: (int(e.get("sequence", 10**9)), e.get("experiment_id", "")))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def exists(path: str | None) -> bool:
    return bool(path) and (ROOT / path).exists()


def report_for(exploration: Path) -> str | None:
    preferred = [
        exploration / "analysis/REPORT.md",
        exploration / "analysis/QB_Q0_REPORT.md",
        exploration / "analysis/R13A_REPORT.md",
        exploration / "REPORT.md",
        exploration / "analysis-v2/REPORT.md",
        exploration / "SUMMARY.md",
        exploration / "summary.md",
        exploration / "analysis/summary.md",
    ]
    for path in preferred:
        if path.exists():
            return rel(path)
    candidates = sorted(exploration.glob("**/*REPORT*.md")) + sorted(exploration.glob("**/*report*.md"))
    return rel(candidates[0]) if candidates else None


KNOWN_VERDICTS = [
    "JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE",
    "MIXED_DYNAMIC_LOADING",
    "TEMPORAL_CONDITIONING_INSUFFICIENT",
    "PAPER_JSL_QB_SUBTHRESHOLD",
    "PAPER_JSL_LOAD_VALID",
    "QB_SOURCE_BACKACTION_FAILURE",
    "QB_BVM_SUBTHRESHOLD",
    "NO_JTL_TRIGGER",
    "DCSFQ_BVM_NO_TRIGGER",
    "ACTIVE_STAGE_NO_TRIGGER",
    "CAUSAL_NEAR_THRESHOLD",
    "BACK_ACTION_FAILURE",
    "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED",
    "Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT",
    "Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT",
    "UNIFORM_SCALE_NO_OUTPUT_EVENT",
    "BIAS_BRACKET_NO_BJL1_EVENT",
    "PAPER_JSL_WAVEFORM_MATCHES_QB_ONE_SHOT",
]


def infer_verdict(exploration: Path) -> str:
    paths = [p for p in [exploration / "SUMMARY.md", exploration / "summary.md", exploration / "REPORT.md", exploration / "analysis/REPORT.md"] if p.exists()]
    discovered = report_for(exploration)
    if discovered:
        discovered_path = ROOT / discovered
        if discovered_path not in paths:
            paths.append(discovered_path)
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)
    for verdict in KNOWN_VERDICTS:
        if verdict in text:
            return verdict
    return "REPORT_PRESENT" if paths else "NO_FORMAL_REPORT_FOUND"


def case_role(case_id: str) -> str:
    low = case_id.lower()
    if "read0-control" in low or "read=0" in low or "control" in low or "zero" in low:
        return "ZERO_CONTROL"
    if "positive-control" in low or "positive" in low:
        return "POSITIVE_CONTROL"
    if "reverse" in low:
        return "NEGATIVE_CONTROL"
    if "paper" in low and ("reference" in low or "original" in low):
        return "HISTORICAL_REFERENCE"
    if "logical0" in low or "read0" in low:
        return "NEGATIVE_CONTROL"
    return "RESULT"


def raw_cases(exploration: Path) -> list[dict[str, Any]]:
    roots = [exploration / "raw"]
    if not roots[0].exists():
        roots = [exploration / "raw-v2"] if (exploration / "raw-v2").exists() else [exploration / "raw-v3"]
    out = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.csv")):
            if "reference" in path.parts or "invalid" in path.parts:
                continue
            case_id = path.relative_to(root).as_posix()
            if case_id.endswith("/run-01.csv"):
                case_id = case_id[:-len("/run-01.csv")]
            elif case_id.endswith(".csv"):
                case_id = case_id[:-4]
            out.append({
                "id": case_id,
                "role": case_role(case_id),
                "fixture": exploration.name,
                "condition": case_id,
                "expected_classification": "REPORT_DEFINED",
                "raw": rel(path),
            })
    return out


def signals_from_cases(cases: list[dict[str, Any]]) -> list[str]:
    signals: set[str] = set()
    for case in cases[:8]:
        raw = case.get("raw")
        if not raw or not (ROOT / raw).is_file():
            continue
        try:
            with (ROOT / raw).open("r", encoding="utf-8", errors="replace") as handle:
                header = next((line for line in handle if line.startswith("time,")), None)
            if header:
                columns = next(csv.reader([header]))
                signals.update(c for c in columns if c.startswith(("P(", "V(", "I(")))
        except (OSError, StopIteration, csv.Error):
            continue
    return sorted(signals)


def read_plot_meta(path: Path) -> dict[str, Any]:
    meta_path = path.with_suffix(".metadata.json")
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def plot_record(path: str, *, role: str, cases: list[str], source_classification: str,
                phase: str | None = "continuous_absolute", source_experiments: list[str] | None = None) -> dict[str, Any]:
    record = {
        "path": path,
        "role": role,
        "cases": cases,
        "source_classification": source_classification,
        "phase_semantics": phase,
    }
    if source_experiments:
        record["source_experiments"] = source_experiments
    meta = read_plot_meta(ROOT / path)
    if meta.get("source_paths"):
        record["source_paths"] = meta["source_paths"]
    return record


def common_plot(exploration: Path, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = exploration / "plots/alignment-overview.html"
    if not path.exists():
        path = exploration / "plots/overview.html"
    if not path.exists():
        return []
    return [plot_record(rel(path), role="RESULT", cases=[c["id"] for c in cases], source_classification="CURRENT_RESULT")]


def key_entry(name: str, *, title: str, question: str, result: str, status: str,
              report: str | None, claim_type: str, topology_id: str,
              notes: str = "", cases: list[dict[str, Any]] | None = None,
              plots: list[dict[str, Any]] | None = None,
              reading: str = "", topology_variants: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entry = {
        "experiment_id": name,
        "title_cn": title,
        "scientific_question": question,
        "formal_result": result,
        "scientific_status": status,
        "current_status": ("NO_WAVEFORM_VISUALIZATION_REQUIRED" if not (cases or []) else ("ALIGNED" if plots else "VISUALIZATION_INCOMPLETE")),
        "report": report,
        "claim_type": claim_type,
        "required_cases": cases or [],
        "required_signals": ["phase P(...)", "same-JJ voltage V(...)", "current I(...)"],
        "plots": plots or [],
        "topology_id": topology_id,
        "phase_semantics": PHASE_SEMANTICS,
        "notes": notes,
        "reading_guide": reading,
    }
    if topology_variants:
        entry["topology_variants"] = topology_variants
    return entry


def explicit_cases(items: list[tuple[str, str, str, str, str, str]]) -> list[dict[str, Any]]:
    return [{"id": i, "role": role, "fixture": fixture, "condition": cond,
             "expected_classification": expected, "raw": raw} for i, role, fixture, cond, expected, raw in items]


def curated_entries() -> dict[str, dict[str, Any]]:
    e: dict[str, dict[str, Any]] = {}
    q0 = "test/exploration/qb-q0-standalone-current-quantized-event-20260824"
    scaled_cases = explicit_cases([
        ("scaled/iin-0", "ZERO_CONTROL", q0, "scaled 0 µA", "ZERO_EVENT", f"{q0}/raw/scaled/iin-0.csv"),
        ("scaled/iin-45u", "RESULT", q0, "scaled 45 µA", "NO_COMPLETE_EVENT", f"{q0}/raw/scaled/iin-45u.csv"),
        ("scaled/iin-68p4u", "RESULT", q0, "scaled 68.4 µA", "EXACTLY_ONE", f"{q0}/raw/scaled/iin-68p4u.csv"),
        ("scaled/iin-90u", "RESULT", q0, "scaled 90 µA", "MULTI_EVENT", f"{q0}/raw/scaled/iin-90u.csv"),
        ("paper/iin-0", "HISTORICAL_REFERENCE", q0, "paper 0 µA", "ZERO_EVENT", f"{q0}/raw/paper/iin-0.csv"),
        ("paper/iin-68p4u", "HISTORICAL_REFERENCE", q0, "paper 68.4 µA", "NO_COMPLETE_EVENT", f"{q0}/raw/paper/iin-68p4u.csv"),
        ("paper/iin-90u", "HISTORICAL_REFERENCE", q0, "paper 90 µA", "NO_COMPLETE_EVENT", f"{q0}/raw/paper/iin-90u.csv"),
    ])
    e[q0] = key_entry(
        q0, title="QB-Q0：低 Ic QB standalone 量化窗口",
        question="低 Ic scaled QB 在理想输入下的 zero / subthreshold / exactly-one / multi-event 窗口是什么？",
        result="scaled 0=ZERO_EVENT；45=NO_COMPLETE_EVENT；68.4=EXACTLY_ONE；90=MULTI_EVENT。paper-original 68.4/90 均无完整 BJL2 event。",
        status="ACCEPTED_STANDALONE_REFERENCE", report=f"{q0}/analysis/QB_Q0_REPORT.md", claim_type="input_window",
        topology_id="QB_Q0_10OHM", cases=scaled_cases, plots=[
            plot_record(f"{q0}/plots/scaled-comparison.html", role="COMPARISON", cases=[c["id"] for c in scaled_cases[:4]], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-68p4uA.html", role="RESULT", cases=["scaled/iin-68p4u"], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-90uA.html", role="RESULT", cases=["scaled/iin-90u"], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-45uA.html", role="RESULT", cases=["scaled/iin-45u"], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-0uA.html", role="ZERO_CONTROL", cases=["scaled/iin-0"], source_classification="CURRENT_ZERO_CONTROL"),
            plot_record(f"{q0}/plots/paper-reference-comparison.html", role="HISTORICAL_REFERENCE", cases=[c["id"] for c in scaled_cases[4:]], source_classification="PAPER_REFERENCE"),
            plot_record(f"{q0}/plots/68p4-paper-reference.html", role="HISTORICAL_REFERENCE", cases=["paper/iin-68p4u"], source_classification="PAPER_REFERENCE"),
            plot_record(f"{q0}/plots/90-paper-reference.html", role="HISTORICAL_REFERENCE", cases=["paper/iin-90u"], source_classification="PAPER_REFERENCE"),
        ], notes="论文参数 QB 对照不得成为 scaled-Q0 exactly-one 的 primary evidence。",
        reading="先看 scaled-comparison；再看 68.4 exactly-one 和 90 multi-event；最后看 paper reference 对照。",
    )

    q1 = "test/exploration/paper-sl-q1-20260824"
    q1_cases = explicit_cases([
        ("q0-68p4u-positive-control", "POSITIVE_CONTROL", q1, "Q0 scaled 68.4 µA", "EXACTLY_ONE", "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv"),
        ("paper-j1-logical1-read", "RESULT", q1, "paper-JSL logical1 READ", "PAPER_JSL_QB_SUBTHRESHOLD", f"{q1}/raw/paper-j1-logical1-read.csv"),
        ("paper-j0-logical0-read", "NEGATIVE_CONTROL", q1, "paper-JSL logical0 READ", "NO_COMPLETE_EVENT", f"{q1}/raw/paper-j0-logical0-read.csv"),
        ("paper-j1-logical1-read0-control", "ZERO_CONTROL", q1, "logical1 READ=0", "ZERO_EVENT", f"{q1}/raw/paper-j1-logical1-read0-control.csv"),
        ("paper-j0-logical0-read0-control", "ZERO_CONTROL", q1, "logical0 READ=0", "ZERO_EVENT", f"{q1}/raw/paper-j0-logical0-read0-control.csv"),
    ])
    e[q1] = key_entry(q1, title="PAPER-SL-Q1：paper-JSL replay → frozen scaled QB",
        question="paper-JSL waveform replay 是否足以驱动 frozen scaled QB？", result="read1 > read0 >> controls，但 BJL2 未达到 exactly-one；Q0 68.4 µA 仅作为 positive control。",
        status="PAPER_JSL_QB_SUBTHRESHOLD", report=f"{q1}/analysis/REPORT.md", claim_type="source_to_receiver",
        topology_id="PAPER_JSL_TO_FROZEN_QB", cases=q1_cases, plots=[
            plot_record(f"{q1}/plots/qb-replay/comparison.html", role="COMPARISON", cases=[c["id"] for c in q1_cases], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j1-logical1-read.html", role="RESULT", cases=["paper-j1-logical1-read"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j0-logical0-read.html", role="NEGATIVE_CONTROL", cases=["paper-j0-logical0-read"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j1-logical1-read0-control.html", role="ZERO_CONTROL", cases=["paper-j1-logical1-read0-control"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j0-logical0-read0-control.html", role="ZERO_CONTROL", cases=["paper-j0-logical0-read0-control"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/q0-68p4u-positive-control.html", role="POSITIVE_CONTROL", cases=["q0-68p4u-positive-control"], source_classification="Q0_REFERENCE"),
            plot_record(f"{q1}/plots/paper-sl-l0-classic/logical1-read.html", role="SOURCE_REFERENCE", cases=["paper-JSL/logical1-read"], source_classification="PAPER_JSL_SOURCE"),
        ], notes="source waveform 只能是 SOURCE_REFERENCE；核心图必须展示 QB response。")

    q2 = "test/exploration/paper-sl-q2-20260824"
    q2cases = raw_cases(ROOT / q2)
    e[q2] = key_entry(q2, title="PAPER-SL-Q2：central-bias bracket",
        question="37.5 与 40 µA central bias 是否关闭 frozen paper-JSL replay 的 BJL1/BJL2 event？",
        result="BIAS_BRANCH_SUBTHRESHOLD；两点均保持 bounded，未建立 complete BJL1/BJL2 event。",
        status="BIAS_BRANCH_SUBTHRESHOLD", report=f"{q2}/analysis/REPORT.md", claim_type="bias_comparison",
        topology_id="PAPER_JSL_TO_FROZEN_QB", cases=q2cases, plots=[
            plot_record(f"{q2}/plots/bias-37p5-vs-40-comparison.html", role="COMPARISON", cases=[c["id"] for c in q2cases], source_classification="CURRENT_RESULT"),
            plot_record(f"{q2}/plots/37p5u/comparison.html", role="RESULT", cases=[c["id"] for c in q2cases if c["id"].startswith("37p5u/")], source_classification="CURRENT_RESULT"),
            plot_record(f"{q2}/plots/40u/comparison.html", role="RESULT", cases=[c["id"] for c in q2cases if c["id"].startswith("40u/")], source_classification="CURRENT_RESULT"),
        ], notes="comparison 必须同时覆盖 37.5 和 40 µA。")

    factor_info = {
        "paper-sl-q3-l1-routing-closure-20260824": ("Q3", "L1=4.50,L2=3.91", "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED"),
        "paper-sl-q4-l1-l2-placement-20260824": ("Q4", "L1=3.91,L2=4.50", "Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT"),
        "paper-sl-q5-l1-l2-factorial-20260824": ("Q5", "L1=4.50,L2=4.50", "Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT"),
    }
    for exp, (label, point, verdict) in factor_info.items():
        path = ROOT / "test/exploration" / exp
        cases = raw_cases(path)
        plots = [plot_record(f"test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html", role="COMPARISON", cases=["Q2", "Q3", "Q4", "Q5"], source_classification="FACTORIAL_RESULT", source_experiments=["paper-sl-q2-20260824", *factor_info.keys()])]
        plots.append(plot_record(f"test/exploration/{exp}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in cases], source_classification="CURRENT_RESULT"))
        e[str(path.relative_to(ROOT))] = key_entry(str(path.relative_to(ROOT)), title=f"{label}：{point}",
            question="L1/L2 placement 如何影响 QB routing 与 BJL2 response？",
            result=verdict, status=verdict, report=report_for(path), claim_type="factorial_point",
            topology_id="PAPER_JSL_TO_FROZEN_QB", cases=cases, plots=plots,
            notes="Q2/Q3/Q4/Q5 factorial comparison 是正式 comparison claim 的核心入口。")

    load = "test/exploration/qb-load-boundary-matrix-20260824"
    load_cases = raw_cases(ROOT / load)
    e[load] = key_entry(load, title="QB load-boundary matrix：Q0 output boundary",
        question="同一 Q0 source 在 OPEN、10Ω、JTL-only、10Ω||JTL 下如何改变 local quantization 与 transport？",
        result="Q0+10Ω exactly-one；OPEN multi-event；JTL-only 与 10Ω||JTL event lost；机制报告为 MIXED_DYNAMIC_LOADING。",
        status="MIXED_DYNAMIC_LOADING", report=f"{load}/analysis/REPORT.md", claim_type="load_matrix",
        topology_id="QB_Q0_10OHM", cases=load_cases, plots=[
            plot_record(f"{load}/plots/q0-complete-boundary-comparison.html", role="COMPARISON", cases=["Q0 + 10Ω (accepted)", "Q0 OPEN", "Q0 JTL-only", "Q0 10Ω || JTL"], source_classification="Q0_BOUNDARY_RESULT"),
            plot_record(f"{load}/plots/q5-open-vs-jtl-read1.html", role="COMPARISON", cases=[c["id"] for c in load_cases if c["id"].startswith(("D-", "E-"))], source_classification="Q5_BOUNDARY_RESULT"),
            plot_record(f"{load}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in load_cases], source_classification="CURRENT_RESULT"),
        ], notes="Q5 OPEN/JTL 为独立 secondary comparison，不替代 Q0 four-boundary core。每个 output boundary 都保留独立 topology provenance。",
        topology_variants=[
            {"topology_id": "QB_Q0_OPEN", "title_cn": "低 Ic QB → OPEN output boundary",
             "representative_deck": f"{load}/inputs-v2/A-q0-open/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/topology.svg"},
            {"topology_id": "QB_Q0_JTL_ONLY", "title_cn": "低 Ic QB → standard JTL direct",
             "representative_deck": f"{load}/inputs-v2/B-q0-jtl-only/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u/topology.svg"},
            {"topology_id": "QB_Q0_10OHM_PARALLEL_JTL", "title_cn": "低 Ic QB + 10Ω || standard JTL",
             "representative_deck": f"{load}/inputs-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u-2/topology.svg"},
        ])

    par = "test/exploration/parallel-qb-jtl-interface-mechanism-20260824"
    par_path = ROOT / par
    e[par] = key_entry(par, title="M1–M5：QB→JTL interface mechanism matrix",
        question="不同输出接口如何影响 QB local event 与 JTL transport？", result="M5 positive-control 的历史 exactly-one 解释已废止；保留 full matrix 与 strict local/transport distinction。",
        status="BOUNDED_INTERFACE_MATRIX", report=f"{par}/analysis-v2/REPORT.md", claim_type="interface_matrix",
        topology_id="QB_M3_SERIES10_JTL", cases=raw_cases(par_path), plots=[
            plot_record(f"{par}/plots/interface-qb-phase-comparison.html", role="COMPARISON", cases=["M1", "M2", "M3", "M4", "M5"], source_classification="QB_INTERFACE_RESULT"),
            plot_record(f"{par}/plots/interface-jtl-phase-comparison.html", role="COMPARISON", cases=["M1", "M2", "M3", "M4", "M5"], source_classification="JTL_INTERFACE_RESULT"),
            plot_record(f"{par}/plots/M1-ideal-replay.html", role="RESULT", cases=["M1"], source_classification="CURRENT_RESULT"),
            plot_record(f"{par}/plots/M3-rseries10.html", role="RESULT", cases=["M3"], source_classification="CURRENT_RESULT"),
            plot_record(f"{par}/plots/M5-positive-control.html", role="HISTORICAL_REFERENCE", cases=["M5"], source_classification="SUPERSEDED_M5_INTERPRETATION"),
            plot_record(f"{par}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in raw_cases(par_path)], source_classification="CURRENT_RESULT"),
        ], notes="M5-PC 标记 MULTI_WELL_TRANSPORT_NOT_ONE_TURN；历史 exactly-one interpretation 不作为 current claim。每个接口变体均绑定自己的 representative deck。",
        topology_variants=[
            {"topology_id": "QB_M1_IDEAL_REPLAY_JTL", "title_cn": "Q0 recorded V(OUT) ideal replay → standard JTL",
             "representative_deck": f"{par}/inputs/M1-ideal-replay/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main/topology.svg"},
            {"topology_id": "QB_M2_RISO10_JTL", "title_cn": "低 Ic QB → RISO=10Ω → standard JTL",
             "representative_deck": f"{par}/inputs/M2-riso10/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-2/topology.svg"},
            {"topology_id": "QB_M4_LISO10P_JTL", "title_cn": "低 Ic QB → LISO=10pH → standard JTL",
             "representative_deck": f"{par}/inputs/M4-liso10p/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-4/topology.svg"},
            {"topology_id": "QB_M5_SCALED_JTL", "title_cn": "低 Ic QB → scaled JTL",
             "representative_deck": f"{par}/inputs/M5-q0-scaled/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-5/topology.svg"},
        ])

    jm = "test/exploration/jtl-transport-gate-v1-methodology-20260824"
    jn = "test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun"
    jcases = [{"id": x, "role": "POSITIVE_CONTROL" if x == "r11" else ("NEGATIVE_CONTROL" if "reverse" in x else "RESULT"), "fixture": jm, "condition": x, "expected_classification": "REGISTERED_REPLAY", "raw": f"{jn}/raw/{x}"} for x in ["r11", "pulse5-original", "pulse5-reverse"]]
    e[jm] = key_entry(jm, title="JTL transport methodology",
        question="标准正控、Q0 pulse5 原极性与反极性的 transport evidence 是否一致？",
        result="保留 strict replay distinction；numerical freeze 当前为 JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE。",
        status="JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE", report=f"{jn}/analysis/REPORT.md", claim_type="polarity_convergence",
        topology_id="STANDARD_JTL_2CELL", cases=jcases, plots=[
            plot_record(f"{jn}/plots/r11-timestep-comparison.html", role="POSITIVE_CONTROL", cases=["r11"], source_classification="STANDARD_JTL_POSITIVE_CONTROL"),
            plot_record(f"{jn}/plots/pulse5-original-timestep-comparison.html", role="RESULT", cases=["pulse5-original"], source_classification="Q0_ORIGINAL_REPLAY"),
            plot_record(f"{jn}/plots/pulse5-reverse-timestep-comparison.html", role="NEGATIVE_CONTROL", cases=["pulse5-reverse"], source_classification="Q0_REVERSE_REPLAY"),
        ], notes="不把 post-window robustness 未完全通过误写成 timestep classification 不稳定。")

    back = "test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824"
    back_cases = explicit_cases([
        ("Q0+10Ω", "RESULT", back, "Q0 + 10Ω", "ACCEPTED_Q0_REFERENCE", "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv"),
        ("Q0 OPEN", "RESULT", back, "Q0 OPEN", "Q0_OPEN", "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/A-q0-open/scaled-iin-68p4u.csv"),
        ("Q0 JTL-only", "RESULT", back, "Q0 JTL-only", "Q0_JTL_ONLY", "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/B-q0-jtl-only/scaled-iin-68p4u.csv"),
        ("Q0 10Ω||JTL", "RESULT", back, "Q0 10Ω||JTL", "Q0_PARALLEL_JTL", "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.csv"),
        ("M3 series10Ω→JTL", "RESULT", back, "M3 series10Ω→JTL", "M3_SERIES_R", "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M3-rseries10/run.csv"),
    ])
    e[back] = key_entry(back, title="QB→JTL load back-action causal audit",
        question="负载改变 Q0 BJL2 trajectory 的主要阶段是 barrier crossing 前、crossing 中还是 retrap？",
        result="MIXED_DYNAMIC_LOADING；核心时间窗 208–210、210–217.1、217.1–259 ps。",
        status="MIXED_DYNAMIC_LOADING", report=f"{back}/analysis/REPORT.md", claim_type="load_backaction_audit",
        topology_id="QB_Q0_10OHM", cases=back_cases, plots=[
            plot_record(f"{back}/plots/backaction_compare.html", role="COMPARISON", cases=["Q0+10Ω", "Q0 OPEN", "Q0 JTL-only", "Q0 10Ω||JTL", "M3 series10Ω→JTL"], source_classification="BACKACTION_AUDIT"),
        ], notes="不能把非线性接口压缩为单一 scalar impedance，除非 report 证据支持；比较图并列引用以下真实 interface topology。",
        topology_variants=[
            {"topology_id": "QB_Q0_OPEN", "title_cn": "低 Ic QB → OPEN output boundary",
             "representative_deck": f"{load}/inputs-v2/A-q0-open/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/topology.svg"},
            {"topology_id": "QB_Q0_JTL_ONLY", "title_cn": "低 Ic QB → standard JTL direct",
             "representative_deck": f"{load}/inputs-v2/B-q0-jtl-only/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u/topology.svg"},
            {"topology_id": "QB_Q0_10OHM_PARALLEL_JTL", "title_cn": "低 Ic QB + 10Ω || standard JTL",
             "representative_deck": f"{load}/inputs-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u-2/topology.svg"},
            {"topology_id": "QB_M3_SERIES10_JTL", "title_cn": "低 Ic QB → series 10Ω → standard JTL",
             "representative_deck": f"{par}/inputs/M3-rseries10/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-3/topology.svg"},
        ])

    r13 = "test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823"
    r13path = ROOT / r13
    e[r13] = key_entry(r13, title="R13-A：temporal conditioning requirements",
        question="极性整流、20 ps hold 或两者是否足以触发 frozen DCSFQ？", result="TEMPORAL_CONDITIONING_INSUFFICIENT。raw/C1/C2/C3 均未完成 selective DCSFQ event。",
        status="TEMPORAL_CONDITIONING_INSUFFICIENT", report=f"{r13}/analysis/R13A_REPORT.md", claim_type="conditioning_matrix",
        topology_id="DCSFQ_REPLAY_CONDITIONER", cases=raw_cases(r13path), plots=[
            plot_record(f"{r13}/plots/raw-vs-c1-vs-c2-vs-c3.html", role="COMPARISON", cases=["raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20"], source_classification="CONDITIONING_RESULT"),
            *[plot_record(f"{r13}/plots/{c}/comparison.html", role="RESULT", cases=[f"{c}/{x}" for x in ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]], source_classification="CONDITIONING_RESULT") for c in ["raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20"]],
        ], notes="理想 waveform transformation 的结果只建立 requirements boundary，不是 physical receiver implementation。")

    q6 = "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824"
    e[q6] = key_entry(q6, title="PAPER-SL-Q6：Q5 → standard JTL compatibility",
        question="Q5 near-threshold QB output 接入 standard JTL 后是否产生 selective regenerative event？", result="NO_JTL_TRIGGER；Q5 standalone 对照必须与 Q6 coupled 并列。",
        status="NO_JTL_TRIGGER", report=f"{q6}/REPORT.md", claim_type="qb_to_jtl", topology_id="Q5_TO_STANDARD_JTL", cases=raw_cases(ROOT / q6), plots=[
            plot_record(f"{q6}/plots/q5-standalone-vs-q6-coupled.html", role="COMPARISON", cases=["Q5 standalone", "Q6 coupled"], source_classification="Q5_Q6_RESULT"),
            plot_record(f"{q6}/plots/q6-q5-to-two-cell-jtl/comparison.html", role="RESULT", cases=[c["id"] for c in raw_cases(ROOT / q6)], source_classification="Q6_COUPLED_RESULT"),
            plot_record(f"{q6}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in raw_cases(ROOT / q6)], source_classification="CURRENT_RESULT"),
        ])

    for name, title, question, result, status, claim, topology_id in [
        ("test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824", "QB-Q1：physical BVM → frozen scaled QB", "canonical BVM 直接驱动 frozen scaled QB 是否保持 source guard 并量化？", "QB_SOURCE_BACKACTION_FAILURE；次级 QB_BVM_SUBTHRESHOLD。", "QB_SOURCE_BACKACTION_FAILURE", "source_backaction", "BVM_TO_SCALED_QB"),
        ("test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824", "QB-Q2A：source-decoupled waveform replay", "source isolation alone 是否足以让 frozen QB 量化？", "QB_DYNAMIC_WINDOW_MISMATCH。", "QB_DYNAMIC_WINDOW_MISMATCH", "source_isolation", "SCALED_QB_REPLAY"),
        ("test/exploration/qb-q2b-central-bias-bracketing-20260824", "QB-Q2B：central-bias bracket", "central bias bracket 是否建立 read1-only BJL1 event？", "BIAS_BRACKET_NO_BJL1_EVENT。", "BIAS_BRACKET_NO_BJL1_EVENT", "bias_bracket", "SCALED_QB_REPLAY"),
        ("test/exploration/qb-q2c-uniform-junction-scale-20260824", "QB-Q2C：uniform junction-scale bracketing", "uniform junction scaling 是否建立 selective BJL1/BJL2 event？", "UNIFORM_SCALE_NO_OUTPUT_EVENT。", "UNIFORM_SCALE_NO_OUTPUT_EVENT", "uniform_scale", "SCALED_QB_REPLAY"),
    ]:
        path = ROOT / name
        e[name] = key_entry(name, title=title, question=question, result=result, status=status,
            report=report_for(path), claim_type=claim, topology_id=topology_id, cases=raw_cases(path),
            plots=common_plot(path, raw_cases(path)), notes="重要因果节点；overview 只用于导航，正式结论以 report 为准。")

    # Q3 routing closure is an analysis-only provenance checkpoint.  It has no
    # independent waveform/report package; the accepted Q3 execution fixture
    # is the paper-sl-q3-l1-routing-closure entry below.  Keep this checkpoint
    # visible in execution order without inventing a result plot or report.
    q3_pre = "test/exploration/q3-l1-routing-closure-20260824"
    e[q3_pre] = key_entry(
        q3_pre, title="PAPER-SL-Q3-PRE：L1 routing closure precheck",
        question="Q3 的 L1 routing hypothesis 是否值得进入单点 execution？",
        result="分析-only provenance checkpoint；不单独产生 waveform verdict。",
        status="NO_WAVEFORM_VISUALIZATION_REQUIRED", report=None, claim_type="analysis_only",
        topology_id="PAPER_JSL_TO_FROZEN_QB", cases=[], plots=[],
        notes="该目录只保存分析/拓扑来源；正式 raw、report 和 result plot 归属于 paper-sl-q3-l1-routing-closure-20260824。",
    )

    bvm = "test/exploration/bvm-internal-readout-20260819"
    e[bvm] = key_entry(
        bvm, title="Canonical BVM：storage/readout cell",
        question="canonical BVM 的 S-Loop、R-Loop、read timing 与 SL output 的真实结构和 waveform 是什么？",
        result="canonical BVM source/read behavior frozen；本页只做结构与已有 read evidence 导航。",
        status="ACCEPTED_CANONICAL_SOURCE", report=f"{bvm}/summary.md", claim_type="canonical_source",
        topology_id="BVM_CANONICAL", cases=raw_cases(ROOT / bvm),
        plots=common_plot(ROOT / bvm, raw_cases(ROOT / bvm)),
        notes="publication schematic 已通过 semantic + geometric validation；不把 schematic 当作 receiver verdict。",
    )
    return e


def topology_signature(deck: Path) -> str:
    """Create a structural, parameter-insensitive signature for an input deck."""
    if not deck.exists():
        return "MISSING"
    rows: list[str] = []
    for raw in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith(";"):
            continue
        low = line.lower()
        if low.startswith((".include", ".print", ".plot", ".tran", ".option", ".end", ".param", ".model")):
            continue
        tokens = line.replace("\t", " ").split()
        if not tokens:
            continue
        name = tokens[0]
        if name.startswith("K") and len(tokens) >= 3:
            rows.append("K " + " ".join(tokens[:3]))
        elif name[0].upper() == "X" and len(tokens) >= 4:
            # Preserve subcircuit instance identity and its endpoint list;
            # otherwise standard versus scaled JTL (and physical versus
            # replay fixtures) could collapse to the same false signature.
            rows.append("X " + " ".join(tokens))
        elif len(tokens) >= 3 and name[0].upper() in "BICJLRV":
            rows.append(f"{name[0].upper()} {name} {tokens[1]} {tokens[2]}")
    return hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest()


def include_refs(deck: Path | None) -> list[str]:
    if not deck or not deck.exists():
        return []
    refs = []
    for line in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = line.strip().split()
        if tokens and tokens[0].lower() == ".include" and len(tokens) > 1:
            refs.append(tokens[1])
    return refs


LIBRARY_ONLY_NAMES = {
    "jjmit.cir", "bvm_cell.cir", "bq_cell.cir", "bq_cell_paper.cir",
    "JTL.cir", "JTL_SCALED.cir", "DCSFQ_BVM.cir", "receiver.cir",
}


def has_top_level_circuit_elements(path: Path) -> bool:
    """Reject copied include libraries when resolving a representative deck."""
    if not path.exists() or path.name in LIBRARY_ONLY_NAMES:
        return False
    inside_subckt = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(("*", ";")):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            inside_subckt = True
            continue
        if low.startswith(".ends"):
            inside_subckt = False
            continue
        if inside_subckt or low.startswith((".include", ".print", ".plot", ".tran", ".option", ".end", ".param", ".model", ".ic", ".nodeset")):
            continue
        tokens = line.replace("\t", " ").split()
        if tokens and len(tokens) >= 3 and tokens[0][0].upper() in "BICJLRV":
            return True
        if tokens and len(tokens) >= 4 and tokens[0].upper().startswith("X"):
            return True
    return False


def inherited_source_deck(experiment: Path) -> Path | None:
    """Read an analysis-only fixture's explicit source-deck provenance."""
    notes = sorted(experiment.glob("**/README*.md")) + sorted(experiment.glob("**/*REPORT*.md"))
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"source deck[^`]*`([^`]+)`", text, re.IGNORECASE)
        if match:
            candidate = ROOT / match.group(1).strip()
            if candidate.exists():
                return candidate
    return None


def representative_deck(experiment: Path, topo_id: str, explicit: str | None = None) -> Path | None:
    """Resolve the top-level simulation deck, never a copied library include."""
    if explicit:
        candidate = ROOT / explicit
        if candidate.exists():
            return candidate
    special = {
        "QB_Q0_10OHM": experiment / "inputs/scaled-iin-68p4u.cir",
        "BVM_CANONICAL": experiment / "inputs/pos-read-single.cir",
        "PAPER_JSL_TO_FROZEN_QB": experiment / "inputs/paper-j1-logical1-read.cir",
        "BVM_TO_SCALED_QB": experiment / "inputs/logical1-read.cir",
        "QB_M3_SERIES10_JTL": experiment / "inputs/M3-rseries10/main.cir",
        "STANDARD_JTL_2CELL": ROOT / "test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/inputs/r11/0p0125/main.cir",
        "Q5_TO_STANDARD_JTL": experiment / "inputs/q6-q5-to-two-cell-jtl/paper-j1-logical1-read.cir",
        "DCSFQ_REPLAY_CONDITIONER": experiment / "inputs/raw-replay/read1.cir",
        "SCALED_QB_REPLAY": ROOT / "test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/inputs/C-canonical-logical1-vsl.cir",
    }
    if topo_id in special and special[topo_id].exists():
        return special[topo_id]
    inherited = inherited_source_deck(experiment)
    if inherited:
        return inherited
    inputs = experiment / "inputs"
    if not inputs.exists():
        return None
    candidates = [p for p in sorted(inputs.rglob("*.cir")) if has_top_level_circuit_elements(p)]
    if not candidates:
        return None
    preferred_tokens = ("logical1", "read1", "positive", "main", "paper-j1", "scaled-iin-68")
    candidates.sort(key=lambda p: (0 if any(token in p.name.lower() for token in preferred_tokens) else 1, len(p.parts), p.as_posix()))
    return candidates[0]


def schematic_package(experiment: Path, topo_id: str) -> Path | None:
    """Find an existing or generated publication-schematic package."""
    root_package = experiment / "topology"
    root_json = root_package / "schematic.json"
    if (root_package / "schematic.svg").exists():
        if not root_json.exists():
            return root_package
        try:
            if json.loads(root_json.read_text(encoding="utf-8")).get("topology_id", topo_id) == topo_id:
                return root_package
        except (OSError, json.JSONDecodeError):
            pass
    for manifest in sorted(experiment.glob("topology/**/schematic.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("topology_id") == topo_id and (manifest.parent / "schematic.svg").exists():
            return manifest.parent
    return None


def build_topology_manifest(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    topologies: dict[str, dict[str, Any]] = {}
    for exp_id, entry in entries.items():
        topo_id = entry.get("topology_id") or f"TOPOLOGY_{hashlib.sha1(exp_id.encode()).hexdigest()[:10]}"
        shared_experiment = entry.get("_shared_experiment", exp_id)
        exp = ROOT / entry.get("_topology_experiment", shared_experiment)
        source = representative_deck(exp, topo_id, entry.get("_representative_deck"))
        topo = topologies.setdefault(topo_id, {
            "topology_id": topo_id,
            "title_cn": entry["title_cn"],
            "representative_experiment": exp_id,
            "sequence": int(entry.get("sequence") or order_metadata(Path(shared_experiment).name)[0]),
            "stage_id": entry.get("stage_id") or order_metadata(Path(shared_experiment).name)[1],
            "stage_title": entry.get("stage_title") or order_metadata(Path(shared_experiment).name)[2],
            "representative_deck": rel(source) if source and source.exists() else None,
            "includes": include_refs(source), "subcircuits": [],
            "topology_signature": topology_signature(source) if source else "MISSING",
            "core_blocks": [topo_id], "external_boundary": [],
            "publication_schematic": None, "annotated_schematic": None, "connectivity_debug": None,
            "semantic_validation": None, "geometric_validation": None,
            "shared_by_experiments": [], "status": "DEBUG_ONLY",
        })
        if shared_experiment not in topo["shared_by_experiments"]:
            topo["shared_by_experiments"].append(shared_experiment)
        tdir = exp / "topology"
        debug_override = entry.get("_connectivity_debug")
        if topo_id == "QB_M3_SERIES10_JTL" and not debug_override:
            # The matrix root graph is the M5-PC graph; use the actual M3
            # variant graph for the primary topology instead.
            debug_override = "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-3/topology.svg"
        if debug_override and not topo["connectivity_debug"]:
            topo["connectivity_debug"] = debug_override
        package = schematic_package(exp, topo_id)
        if package and not topo["publication_schematic"]:
            topo["publication_schematic"] = rel(package / "schematic.svg")
            topo["annotated_schematic"] = rel(package / "schematic-annotated.svg") if (package / "schematic-annotated.svg").exists() else None
            topo["connectivity_debug"] = rel(package / "connectivity-debug.svg") if (package / "connectivity-debug.svg").exists() else topo["connectivity_debug"]
            topo["semantic_validation"] = rel(package / "schematic-validation.json") if (package / "schematic-validation.json").exists() else None
            topo["geometric_validation"] = rel(package / "geometric-connectivity-validation.json") if (package / "geometric-connectivity-validation.json").exists() else None
            topo["status"] = "PUBLICATION_SCHEMATIC_VALIDATED" if topo["semantic_validation"] and topo["geometric_validation"] else "PUBLICATION_SCHEMATIC_UNVALIDATED"
        elif (tdir / "topology.svg").exists() and not topo["connectivity_debug"] and not debug_override:
            topo["connectivity_debug"] = rel(tdir / "topology.svg")
    values = list(topologies.values())
    values.sort(key=lambda x: (int(x.get("sequence", 10**9)), x["topology_id"]))
    for topo in values:
        seq = int(topo.get("sequence", 10**9))
        if seq < 10**9 and seq <= len(EXPERIMENT_ORDER):
            _, sid, title = order_metadata(EXPERIMENT_ORDER[seq - 1])
            topo["stage_id"] = topo.get("stage_id") or sid
            topo["stage_title"] = topo.get("stage_title") or title
    return {"schema_version": "2.0", "parent_head": HEAD, "topologies": values}


def markdown_link(path: str | None, label: str) -> str:
    return f"[{label}](../{path})" if path and exists(path) else f"`{label}（未生成）`"


def plot_links(entry: dict[str, Any]) -> list[str]:
    labels = {
        "COMPARISON": "【关键对比图】", "RESULT": "【单工况/结果图】",
        "POSITIVE_CONTROL": "【正向对照】", "NEGATIVE_CONTROL": "【负向对照】",
        "ZERO_CONTROL": "【零输入对照】", "SOURCE_REFERENCE": "【源波形参考】",
        "HISTORICAL_REFERENCE": "【历史参考】",
    }
    return [f"- {labels.get(p['role'], '[' + p['role'] + ']')} {markdown_link(p['path'], p['path'])}" for p in entry.get("plots", [])]


def render_index(entries: dict[str, dict[str, Any]], *, flow: bool) -> str:
    order = list(entries)
    if flow:
        title = "# EXPLORATION FLOW INDEX V2"
        intro = (f"生成基线 HEAD：`{HEAD}`。\n\n"
                 "本页由 `docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml` 生成，展示科研路线；结果图、controls、source/reference 和电路入口均保持角色区分。")
    else:
        title = "# VISUALIZATION INDEX V2"
        intro = (f"生成基线 HEAD：`{HEAD}`。\n\n"
                 "本页由统一 alignment manifest 生成，按科学语义列出核心结果、对比、controls 和 source/reference。")
    lines = [title, "", intro, "", "## 阅读约定", "",
             "- `continuous_absolute`：原始 JoSIM P(...) 连续轨迹的 φ/2π（turn），不等于 SFQ 计数。",
             "- source/reference/historical 图不能作为 current result 的核心证据。",
             "- 论文级 schematic、annotated schematic、connectivity debug graph 分开列出。", ""]
    for exp_id in order:
        entry = entries[exp_id]
        lines += [f"## {entry['title_cn']}", "", f"**实验 ID**：`{exp_id}`", "",
                  f"**做了什么**：{entry['scientific_question']}", "",
                  f"**关键结果**：{entry['formal_result']}", "",
                  f"**当前状态**：`{entry['scientific_status']}` / alignment=`{entry['current_status']}`", "",
                  f"**结论边界**：{entry.get('notes') or '正式结论以 report 为准；可视化不改变 scientific verdict。'}", "",
                  "**推荐先看**：", *plot_links(entry), ""]
        topo = next((t for t in yaml.safe_load(TOPOLOGY_PATH.read_text(encoding="utf-8")).get("topologies", []) if t["topology_id"] == entry.get("topology_id")), None) if TOPOLOGY_PATH.exists() else None
        if topo:
            lines += ["**电路**：",
                      f"- 【论文级电路图】 {markdown_link(topo.get('publication_schematic'), 'schematic.svg')}",
                      f"- 【实验注释电路图】 {markdown_link(topo.get('annotated_schematic'), 'schematic-annotated.svg')}",
                      f"- 【网表连接调试图】 {markdown_link(topo.get('connectivity_debug'), 'connectivity-debug.svg')}", ""]
            variants = entry.get("topology_variants", [])
            if variants:
                lines += ["**真实 topology 变体**："]
                for variant in variants:
                    label = variant.get("title_cn", variant.get("topology_id", "variant"))
                    lines += [f"- `{label}`：",
                              f"  - 【论文级电路图】 {markdown_link(variant.get('publication_schematic'), 'schematic.svg')}",
                              f"  - 【实验注释电路图】 {markdown_link(variant.get('annotated_schematic'), 'schematic-annotated.svg')}",
                              f"  - 【网表连接调试图】 {markdown_link(variant.get('connectivity_debug'), 'connectivity-debug.svg')}"]
                lines.append("")
        if entry.get("report"):
            lines += [f"**正式报告**：{markdown_link(entry['report'], entry['report'])}", ""]
        lines += ["---", ""]
    return "\n".join(lines)


def html_index(markdown: str, title: str, entries: dict[str, dict[str, Any]], topology: dict[str, Any] | None = None) -> str:
    # Keep the HTML index generated from the same entry set; the simple
    # renderer intentionally avoids a second link mapping.
    body = []
    topology_map = {t.get("topology_id"): t for t in (topology or {}).get("topologies", [])}
    for entry in entries.values():
        body.append(f"<section data-experiment-id='{html.escape(entry['experiment_id'])}'><h2>{html.escape(entry['title_cn'])}</h2>")
        body.append(f"<p><b>做了什么：</b>{html.escape(entry['scientific_question'])}</p>")
        body.append(f"<p><b>关键结果：</b>{html.escape(entry['formal_result'])}</p>")
        body.append(f"<p><b>状态：</b><code>{html.escape(entry['scientific_status'])}</code> / <code>{html.escape(entry['current_status'])}</code></p><ul>")
        for p in entry.get("plots", []):
            if exists(p["path"]):
                body.append(f"<li data-plot-role='{html.escape(p['role'])}'><a href='../{html.escape(p['path'])}'>{html.escape(p['role'])} · {html.escape(p['path'])}</a></li>")
        body.append("</ul>")
        topo = topology_map.get(entry.get("topology_id"))
        if topo:
            body.append("<p><b>电路：</b>")
            for label, key in (("论文级电路图", "publication_schematic"), ("实验注释电路图", "annotated_schematic"), ("网表连接调试图", "connectivity_debug")):
                target = topo.get(key)
                if target and exists(target):
                    body.append(f" <a href='../{html.escape(target)}'>{label}</a>")
                else:
                    body.append(f" <span>{label}（未生成）</span>")
            body.append("</p>")
            variants = entry.get("topology_variants", [])
            if variants:
                body.append("<p><b>真实 topology 变体：</b></p><ul>")
                for variant in variants:
                    body.append(f"<li><b>{html.escape(variant.get('title_cn', variant.get('topology_id', 'variant')))}</b>")
                    for label, key in (("论文级电路图", "publication_schematic"), ("实验注释电路图", "annotated_schematic"), ("网表连接调试图", "connectivity_debug")):
                        target = variant.get(key)
                        if target and exists(target):
                            body.append(f" <a href='../{html.escape(target)}'>{label}</a>")
                        else:
                            body.append(f" <span>{label}（未生成）</span>")
                    body.append("</li>")
                body.append("</ul>")
        if entry.get("report") and exists(entry["report"]):
            body.append(f"<p><a href='../{html.escape(entry['report'])}'>正式报告</a></p>")
        body.append("</section>")
    return ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>{html.escape(title)}</title><style>body{{font-family:system-ui;max-width:1200px;margin:2rem auto;line-height:1.55}}section{{border-bottom:1px solid #ddd;padding:1rem 0}}a{{color:#0758a8}}code{{background:#f2f2f2;padding:.1rem .25rem}}</style></head>"
            f"<body><h1>{html.escape(title)}</h1><p>由统一 alignment manifest 生成。基线 HEAD <code>{HEAD}</code>。</p>{''.join(body)}</body></html>\n")


def html_topology_index(topology: dict[str, Any]) -> str:
    body: list[str] = []
    for topo in topology.get("topologies", []):
        body.append(f"<section><h2>{html.escape(topo['title_cn'])}</h2><p><code>{html.escape(topo['topology_id'])}</code> · <code>{html.escape(topo['status'])}</code></p><ul>")
        for label, key in (("论文级电路图", "publication_schematic"), ("实验注释电路图", "annotated_schematic"), ("网表连接调试图", "connectivity_debug")):
            target = topo.get(key)
            if target and exists(target):
                body.append(f"<li><a href='../{html.escape(target)}'>{label}</a></li>")
            else:
                body.append(f"<li>{label}（未生成）</li>")
        body.append(f"</ul><p>representative deck: <code>{html.escape(topo.get('representative_deck') or '未记录')}</code></p></section>")
    return ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>CIRCUIT SCHEMATIC INDEX</title><style>body{{font-family:system-ui;max-width:1200px;margin:2rem auto;line-height:1.55}}section{{border-bottom:1px solid #ddd;padding:1rem 0}}a{{color:#0758a8}}code{{background:#f2f2f2;padding:.1rem .25rem}}</style></head>"
            f"<body><h1>CIRCUIT SCHEMATIC INDEX</h1><p>由 topology manifest 生成。基线 HEAD <code>{HEAD}</code>。</p>{''.join(body)}</body></html>\n")


def build_alignment_audit(manifest: dict[str, Any], topology: dict[str, Any]) -> str:
    topo_map = {t.get("topology_id"): t for t in topology.get("topologies", [])}
    lines = [
        "# Visualization Alignment Audit V2", "",
        f"基线 HEAD：`{manifest.get('parent_head')}`", "",
        "本审计只检查 raw/report/plot/index/topology 的 provenance 对齐，不改变任何 scientific verdict。", "",
        "| 实验 | 科学状态 | required cases | plots | core/comparison | report | topology | status |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for entry in manifest.get("experiments", []):
        topo = topo_map.get(entry.get("topology_id"), {})
        core = any(p.get("role") in {"RESULT", "COMPARISON"} for p in entry.get("plots", []))
        lines.append("| {} | `{}` | {} | {} | {} | {} | `{}` | `{}` |".format(
            entry.get("experiment_id"), entry.get("scientific_status"), len(entry.get("required_cases", [])),
            len(entry.get("plots", [])), "YES" if core else "NO", "YES" if entry.get("report") else "NO",
            topo.get("status", "MISSING"), entry.get("current_status")))
    lines += ["", "## 状态定义", "", "- `ALIGNED`：manifest 已明确 raw case、result/comparison plot、report，并通过角色约束；",
              "- `VISUALIZATION_INCOMPLETE`：required case 没有足够 plot coverage；",
              "- `TOPOLOGY_MISMATCH`：结构图 signature 或 publication/debug 角色不一致；",
              "- `NO_WAVEFORM_VISUALIZATION_REQUIRED`：该条目只有 analysis/documentation，没有可登记 raw waveform；",
              "- `SUPERSEDED_ONLY`：仅保留历史 provenance，不作为 current core。", "",
              "## 关键人工 spot-check 集合", "",
              "QB-Q0、PAPER-SL-Q1/Q2、Q2–Q5 factorial、QB load-boundary、M1–M5、JTL methodology/numerical freeze、back-action、R13、Q6 均由 manifest 显式登记；其 core link 不从文件名排序推断。", ""]
    return "\n".join(lines)


def build_reading_guide(entries: dict[str, dict[str, Any]]) -> str:
    rows = [
        ("我想确认 scaled QB 的输入窗口", "QB-Q0", "qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html", "看 scaled 0/45/68.4/90 的 BJL2 连续轨迹；paper 只作历史对照。", "不推出 canonical BVM compatibility。"),
        ("我想看 paper-JSL 是否驱动 QB", "PAPER-SL-Q1", "paper-sl-q1-20260824/plots/qb-replay/comparison.html", "看 BJs/BJL1/BJL2 的 read1/read0/control 分离。", "不要把 paper-JSL source 图当 QB response。"),
        ("我想比较 37.5 与 40 µA", "PAPER-SL-Q2", "paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html", "看 BJL1/BJL2 phase 与 current。", "不能只看 37.5 单点。"),
        ("我想看 L1/L2 factorial", "Q2–Q5", "paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html", "看四点的 BJL1/BJL2 与 routing current。", "phase range 不自动等于 event。"),
        ("我想看 output boundary", "QB load-boundary", "qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html", "看同一 Q0 的 10Ω/OPEN/JTL/parallel。", "Q5 boundary 是 secondary comparison。"),
        ("我想看 JTL polarity/convergence", "JTL methodology", "jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html", "同时打开 R11 与 reverse。", "严格 Gate 仍 INCONCLUSIVE。"),
        ("我想看 R13 conditioning", "R13-A", "bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html", "逐条件查看 raw/C1/C2/C3 的 B3。", "理想 replay 不是 physical implementation。"),
        ("我想看 Q5 接 JTL 的变化", "PAPER-SL-Q6", "paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html", "直接比较 BJL1/BJL2/V(OUT)。", "不把耦合系统成功等同 isolated QB event。"),
    ]
    lines = ["# Visualization Reading Guide", "", f"本指南由 alignment manifest 生成，基线 HEAD：`{HEAD}`。", "", "| 想确认什么 | 实验 | 先打开 | 看什么 | 不能据此推出什么 |", "|---|---|---|---|---|"]
    lines += ["|" + "|".join(row) + "|" for row in rows]
    lines += ["", "## Phase semantics", "", *[f"- `{k}`：{v}" for k, v in PHASE_SEMANTICS.items()], ""]
    return "\n".join(lines)


def build_schematic_index(topology: dict[str, Any], entries: dict[str, dict[str, Any]]) -> str:
    lines = ["# CIRCUIT SCHEMATIC INDEX", "", f"基线 HEAD：`{HEAD}`。本页将论文级电路图、实验注释图和连接调试图分开。", ""]
    for topo in topology["topologies"]:
        lines += [f"## {topo['title_cn']}", "", f"**Topology ID**：`{topo['topology_id']}`", "",
                  f"**状态**：`{topo['status']}`；signature=`{topo['topology_signature'][:16]}`…", "",
                  f"- 【论文级电路图】 {markdown_link(topo.get('publication_schematic'), 'schematic.svg')}",
                  f"- 【实验注释电路图】 {markdown_link(topo.get('annotated_schematic'), 'schematic-annotated.svg')}",
                  f"- 【网表连接调试图】 {markdown_link(topo.get('connectivity_debug'), 'connectivity-debug.svg')}",
                  f"- representative deck：`{topo.get('representative_deck') or '未记录'}`", "",
                  "共享实验：", *[f"- `{x}`" for x in topo.get("shared_by_experiments", [])], "", "---", ""]
    lines += ["## 结构图边界", "", "只有存在 semantic + geometric validation 的 `schematic.svg` 才列为论文级电路图；Graphviz `topology.svg` 只作 debug/provenance，不作为默认结构图入口。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default=HEAD, help="recorded parent HEAD; default is the task baseline")
    args = ap.parse_args()
    recorded_head = args.head
    entries = curated_entries()
    # Add every remaining Exploration as an explicit manifest entry.  Its
    # alignment status is conservative: the generated alignment overview is a
    # complete case view, while a missing report/topology remains visible.
    for path in sorted((ROOT / "test/exploration").iterdir()):
        exp_key = path.relative_to(ROOT).as_posix()
        if not path.is_dir() or exp_key in entries:
            continue
        cases = raw_cases(path)
        report = report_for(path)
        if not cases and not report:
            continue
        plots = common_plot(path, cases)
        entries[exp_key] = key_entry(
            exp_key, title=path.name,
            question="见该 Exploration 的 preregistration / report。",
            result="正式结论见 report；索引不新增科学解释。",
            status=("NO_WAVEFORM_VISUALIZATION_REQUIRED" if not cases else infer_verdict(path)), report=report, claim_type="generic_exploration",
            topology_id=f"TOPOLOGY_{hashlib.sha1(path.name.encode()).hexdigest()[:10]}", cases=cases,
            plots=plots, notes="自动审计条目；未在本轮改写 scientific verdict。")
    # Reinsert the mapping in explicit scientific execution order.  This order
    # drives both Markdown and HTML; directory enumeration is never a route
    # authority.
    entries = {entry["experiment_id"]: entry for entry in ordered_entries(entries)}
    # Use the recorded baseline supplied by the caller, not the current
    # post-generation HEAD, so provenance stays explicit.
    # A comparison experiment may contain several real electrical boundaries.
    # Materialize each declared variant for the topology manifest without
    # pretending that one representative deck describes the whole matrix.
    topology_entries = dict(entries)
    for exp_id, entry in entries.items():
        for variant in entry.get("topology_variants", []):
            variant_entry = dict(entry)
            variant_entry.update({
                "topology_id": variant["topology_id"],
                "title_cn": variant.get("title_cn", variant["topology_id"]),
                "_shared_experiment": exp_id,
                "_topology_experiment": exp_id,
                "_representative_deck": variant.get("representative_deck"),
                "_connectivity_debug": variant.get("connectivity_debug"),
            })
            topology_entries[f"{exp_id}::{variant['topology_id']}"] = variant_entry
    topology = build_topology_manifest(topology_entries)
    topology["parent_head"] = recorded_head
    topology_map = {t["topology_id"]: t for t in topology["topologies"]}
    for entry in entries.values():
        topo = topology_map.get(entry.get("topology_id"))
        if topo:
            entry["topology_signature"] = topo.get("topology_signature")
            entry["topology_status"] = topo.get("status")
            entry["topology"] = {
                "topology_id": topo.get("topology_id"),
                "topology_signature": topo.get("topology_signature"),
                "publication_schematic": topo.get("publication_schematic"),
                "annotated_schematic": topo.get("annotated_schematic"),
                "connectivity_debug": topo.get("connectivity_debug"),
            }
        if entry.get("topology_variants"):
            resolved_variants = []
            for variant in entry["topology_variants"]:
                vt = topology_map.get(variant["topology_id"])
                resolved = dict(variant)
                if vt:
                    resolved.update({
                        "topology_signature": vt.get("topology_signature"),
                        "publication_schematic": vt.get("publication_schematic"),
                        "annotated_schematic": vt.get("annotated_schematic"),
                        "connectivity_debug": vt.get("connectivity_debug"),
                        "status": vt.get("status"),
                    })
                resolved_variants.append(resolved)
            entry["topology_variants"] = resolved_variants
        entry["required_signals"] = signals_from_cases(entry.get("required_cases", [])) or entry.get("required_signals", [])
        groups = {"core_result": [], "key_comparison": [], "case_plots": [], "controls": [], "source_references": []}
        for plot in entry.get("plots", []):
            role = plot.get("role")
            if role == "COMPARISON":
                groups["key_comparison"].append(plot.get("path"))
            elif role in {"SOURCE_REFERENCE", "HISTORICAL_REFERENCE", "SUPERSEDED_REFERENCE"}:
                groups["source_references"].append(plot.get("path"))
            elif role in {"POSITIVE_CONTROL", "NEGATIVE_CONTROL", "ZERO_CONTROL"}:
                groups["controls"].append(plot.get("path"))
            else:
                groups["case_plots"].append(plot.get("path"))
        groups["core_result"] = [p.get("path") for p in entry.get("plots", []) if p.get("role") in {"RESULT", "COMPARISON"}]
        entry["plot_groups"] = groups
    manifest = {
        "schema_version": "2.0",
        "manifest_id": "PROJECT_VISUALIZATION_INDEX_ALIGNMENT_V2",
        "parent_head": recorded_head,
        "authority_order": ["raw", "accepted_analysis_report", "visualization", "index"],
        "phase_semantics": PHASE_SEMANTICS,
        "experiments": ordered_entries(entries),
    }
    MANIFEST_PATH.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    TOPOLOGY_PATH.write_text(yaml.safe_dump(topology, allow_unicode=True, sort_keys=False), encoding="utf-8")
    flow_md = render_index(entries, flow=True)
    viz_md = render_index(entries, flow=False)
    (ROOT / "docs/EXPLORATION_FLOW_INDEX.md").write_text(flow_md, encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_INDEX.md").write_text(viz_md, encoding="utf-8")
    entry_list = ordered_entries(entries)
    (ROOT / "docs/EXPLORATION_FLOW_INDEX.html").write_text(render_rich_index(entry_list, topology, title="BVM→QB/JTL receiver Exploration 流程总索引", flow=True, head=recorded_head), encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_INDEX.html").write_text(render_rich_index(entry_list, topology, title="BVM→QB/JTL receiver 可视化结果索引", flow=False, head=recorded_head), encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_READING_GUIDE.md").write_text(build_reading_guide(entries), encoding="utf-8")
    (ROOT / "docs/CIRCUIT_SCHEMATIC_INDEX.md").write_text(build_schematic_index(topology, entries), encoding="utf-8")
    (ROOT / "docs/CIRCUIT_SCHEMATIC_INDEX.html").write_text(render_topology_index(topology, title="BVM→QB/JTL 电路结构导航", head=recorded_head), encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_ALIGNMENT_AUDIT.md").write_text(build_alignment_audit(manifest, topology), encoding="utf-8")
    print(f"experiments={len(entries)} topologies={len(topology['topologies'])}")


if __name__ == "__main__":
    main()
