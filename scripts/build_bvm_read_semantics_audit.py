#!/usr/bin/env python3
"""Build the repository-wide BVM READ semantics audit manifest/report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from verify_bvm_read_semantics import parse_deck, protocol_signature


ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def add_direct(cases: list[dict[str, Any]], case_id: str, path: Path, lineage: list[str], note: str = "") -> dict[str, Any]:
    parsed = parse_deck(path, lineage=lineage, role_hint=case_id)
    item = {"id": case_id, **parsed}
    item["path"] = rel(path)
    item["source_lineage"] = lineage
    if note:
        item["notes"] = note
    cases.append(item)
    return item


def add_replay(cases: list[dict[str, Any]], case_id: str, path: Path, parent: dict[str, Any], role: str, note: str = "") -> dict[str, Any]:
    sig = parent.get("protocol_signature") or {"has_read": role.endswith("read")}
    parsed = parse_deck(path, inherited_protocol=sig, lineage=[parent["id"]], role_hint=role)
    item = {"id": case_id, **parsed, "path": rel(path), "source_lineage": [parent["id"]]}
    if role == "logical0_read" and parent.get("current_validity") == "LOGICAL0_GATE_NOT_TESTED":
        item["current_validity"] = "LOGICAL0_GATE_NOT_TESTED"
        item["required_action"] = "Do not use as canonical logical0 gate evidence; rerun with canonical WL+SE READ."
    elif role.endswith("no_read_control"):
        item["required_action"] = "May remain a no-read control if no READ source is present."
    if note:
        item["notes"] = note
    cases.append(item)
    return item


def build_manifest() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    bvm = ROOT / "test/exploration/bvm-internal-readout-20260819/inputs"
    canonical = {}
    for name, role in {
        "pos-read-single.cir": "logical1_read",
        "neg-init-pos-read.cir": "logical0_read",
        "pos-control.cir": "logical1_no_read_control",
        "neg-control.cir": "logical0_no_read_control",
        "pos-init-neg-read.cir": "negative_polarity_read_diagnostic",
        "neg-read-single.cir": "logical0_read",
    }.items():
        item = add_direct(cases, f"canonical.{role}.{name[:-4]}", bvm / name, ["canonical_bvm"],
                          "Canonical BVM internal-readout fixture." if "control" not in name else "Canonical no-READ control.")
        canonical[name] = item

    paper = ROOT / "test/exploration/paper-sl-l0-20260824/inputs"
    paper_cases = {}
    for name, role in {
        "logical1-read.cir": "logical1_read",
        "logical0-read.cir": "logical0_read",
        "logical1-read0-control.cir": "logical1_no_read_control",
        "logical0-read0-control.cir": "logical0_no_read_control",
    }.items():
        paper_cases[name] = add_direct(cases, f"paper_sl_l0.{name[:-4]}", paper / name, ["paper_sl_l0"],
                                       "PAPER-SL-L0 external 12-JSL source fixture.")

    width = ROOT / "test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824"
    phase_a = {}
    for width_ps in (12, 15, 20):
        for state in ("logical1", "logical0"):
            name = f"{state}-read.cir"
            item = add_direct(cases, f"width.phase_a.{width_ps}ps.{state}_read",
                              width / f"inputs/phase-a/{width_ps}ps/{name}", ["canonical_bvm"],
                              "Phase-A external R_LD=12 Ω canonical width fixture.")
            phase_a[(width_ps, state)] = item
    phase_b = {}
    for state in ("logical1", "logical0"):
        name = f"{state}-read.cir"
        parent = paper_cases[f"{state}-read.cir"]
        phase_b[state] = add_direct(cases, f"width.phase_b.12ps.{state}_read",
                                    width / f"inputs/phase-b/12jsl-12ps/{name}", [parent["id"]],
                                    "Phase-B 12-JSL source; logical0 preserves historical WL-only semantics.")

    q1 = ROOT / "test/exploration/paper-sl-q1-20260824/inputs"
    q1_cases = {}
    q1_names = {
        "paper-j1-logical1-read.cir": ("logical1_read", paper_cases["logical1-read.cir"]),
        "paper-j0-logical0-read.cir": ("logical0_read", paper_cases["logical0-read.cir"]),
        "paper-j1-logical1-read0-control.cir": ("logical1_no_read_control", paper_cases["logical1-read0-control.cir"]),
        "paper-j0-logical0-read0-control.cir": ("logical0_no_read_control", paper_cases["logical0-read0-control.cir"]),
    }
    for name, (role, parent) in q1_names.items():
        q1_cases[name] = add_replay(cases, f"paper_sl_q1.{name[:-4]}", q1 / name, parent, role,
                                    "Ideal-current replay; protocol is inherited, not present in replay deck.")

    q2_root = ROOT / "test/exploration/paper-sl-q2-20260824/inputs"
    q2_cases: dict[str, dict[str, Any]] = {}
    for bias in ("37p5u", "40u"):
        for name, (role, parent_name) in {
            "paper-j1-logical1-read.cir": ("logical1_read", "paper-j1-logical1-read.cir"),
            "paper-j0-logical0-read.cir": ("logical0_read", "paper-j0-logical0-read.cir"),
            "paper-j1-logical1-read0-control.cir": ("logical1_no_read_control", "paper-j1-logical1-read0-control.cir"),
            "paper-j0-logical0-read0-control.cir": ("logical0_no_read_control", "paper-j0-logical0-read0-control.cir"),
        }.items():
            parent = q1_cases[parent_name]
            q2_cases[f"{bias}/{name}"] = add_replay(cases, f"paper_sl_q2.{bias}.{name[:-4]}", q2_root / bias / name, parent, role,
                                                    "Q2 replay derived from Q1 source deck; logical0 lineage remains noncanonical.")

    # Q3/Q4/Q5/Q6 are downstream replay descendants.  Record one complete
    # case family per experiment, rather than pretending their ideal replay
    # decks contain a BVM READ source of their own.
    descendants = [
        ("paper_sl_q3", ROOT / "test/exploration/paper-sl-q3-l1-routing-closure-20260824/inputs/l1-4p5"),
        ("paper_sl_q4", ROOT / "test/exploration/paper-sl-q4-l1-l2-placement-20260824/inputs/q4-l1-3p91-l2-4p50"),
        ("paper_sl_q5", ROOT / "test/exploration/paper-sl-q5-l1-l2-factorial-20260824/inputs/q5-l1-4p50-l2-4p50"),
        ("paper_sl_q6", ROOT / "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/inputs/q6-q5-to-two-cell-jtl"),
    ]
    for prefix, root in descendants:
        for name, role in (("paper-j1-logical1-read.cir", "logical1_read"), ("paper-j0-logical0-read.cir", "logical0_read"),
                           ("paper-j1-logical1-read0-control.cir", "logical1_no_read_control"), ("paper-j0-logical0-read0-control.cir", "logical0_no_read_control")):
            parent_key = "paper-j1-logical1-read.cir" if name.startswith("paper-j1") else "paper-j0-logical0-read.cir"
            if name.endswith("read0-control.cir"):
                parent_key = "paper-j1-logical1-read0-control.cir" if name.startswith("paper-j1") else "paper-j0-logical0-read0-control.cir"
            parent = q2_cases[f"40u/{parent_key}"]
            add_replay(cases, f"{prefix}.{name[:-4]}", root / name, parent, role,
                       f"{prefix.upper()} replay descendant; logical0 gate status inherited from PAPER-SL-L0.")

    matched_pairs = []
    # Direct canonical pairs.
    matched_pairs.append({"id": "canonical_internal_read", "logical1_read": canonical["pos-read-single.cir"]["id"], "logical0_read": canonical["neg-init-pos-read.cir"]["id"]})
    for width_ps in (12, 15, 20):
        matched_pairs.append({"id": f"phase_a_{width_ps}ps", "logical1_read": phase_a[(width_ps, "logical1")]["id"], "logical0_read": phase_a[(width_ps, "logical0")]["id"]})
    mismatched_pairs = [
        {"id": "paper_sl_l0_legacy", "logical1_read": paper_cases["logical1-read.cir"]["id"], "logical0_read": paper_cases["logical0-read.cir"]["id"], "disposition": "READ_PROTOCOL_MISMATCH"},
        {"id": "phase_b_12ps_legacy", "logical1_read": phase_b["logical1"]["id"], "logical0_read": phase_b["logical0"]["id"], "disposition": "READ_PROTOCOL_MISMATCH"},
    ]
    for prefix in ("paper_sl_q1", "paper_sl_q3", "paper_sl_q4", "paper_sl_q5", "paper_sl_q6"):
        mismatched_pairs.append({"id": prefix, "logical1_read": f"{prefix}.paper-j1-logical1-read", "logical0_read": f"{prefix}.paper-j0-logical0-read", "disposition": "INHERITED_NONCANONICAL_LOGICAL0"})
    for bias in ("37p5u", "40u"):
        mismatched_pairs.append({"id": f"paper_sl_q2_{bias}", "logical1_read": f"paper_sl_q2.{bias}.paper-j1-logical1-read", "logical0_read": f"paper_sl_q2.{bias}.paper-j0-logical0-read", "disposition": "INHERITED_NONCANONICAL_LOGICAL0"})

    lineage_edges = []
    for child in cases:
        for parent in child.get("source_lineage", [])[0:1]:
            if parent in {item["id"] for item in cases}:
                lineage_edges.append({"parent": parent, "child": child["id"]})

    return {
        "schema_version": "bvm-read-semantics-v1",
        "parent_head": "576ca9d32b15c99f8c35c4271336ffa079664b64",
        "canonical_protocol": {
            "name": "CANONICAL_READ_PROTOCOL_V1",
            "logical1_initialization": "WL=+100 µA, BL=+100 µA",
            "logical0_initialization": "WL=-100 µA, BL=-100 µA",
            "read": "WL=+100 µA and SE=+100 µA, same onset/width/rise/fall",
            "no_read": "WL=0 and SE=0 after initialization",
        },
        "phase_semantics": "continuous_absolute",
        "cases": cases,
        "matched_pairs": matched_pairs,
        "mismatched_pairs": mismatched_pairs,
        "lineage_edges": lineage_edges,
    }


def build_report(manifest: dict[str, Any], validation: dict[str, Any]) -> str:
    lines = [
        "# BVM READ semantics audit",
        "",
        f"审计 parent HEAD：`{manifest['parent_head']}`。本文件只重标语义和 provenance，不修改任何旧 raw。",
        "",
        "## Canonical READ_PROTOCOL_V1",
        "",
        "- logical1：positive WL+BL initialization；logical0：negative WL+BL initialization。",
        "- 两种 stored state 的 READ 完全相同：WL=+100 µA、SE=+100 µA、相同 onset/plateau/rise/fall。",
        "- WL-only negative-state read 是 `WL_ONLY_NEGATIVE_STATE_DIAGNOSTIC`，不是 canonical logical0 gate。",
        "- WL=0、SE=0 的 case 是 `NO_READ_CONTROL`。",
        "- phase 图统一为原始 JoSIM `P(t)/(2π)` 连续轨迹；不等于 SFQ count。",
        "",
        "## 审计结论",
        "",
        "| 范围 | 结论 | 处置 |",
        "|---|---|---|",
        "| canonical BVM `neg-init-pos-read.cir` | canonical logical0_read | 保持当前有效 |",
        "| PAPER-SL-L0 `logical0-read.cir` | negative initialization + WL-only READ | 重标为 WL-only diagnostic |",
        "| PAPER-SL-Q1→Q6 logical0 replay | 继承 PAPER-SL-L0 noncanonical source | 不得作为 canonical logical0 gate evidence |",
        "| Phase-A width 12/15/20 ps | WL+SE canonical pair | 可用于 canonical width source comparison |",
        "| Phase-B/C 既有 12 ps logical0 | 继承 WL-only source | 旧结论保留 provenance，但 logical0 gate 降级 |",
        "",
        "## 影响边界",
        "",
        "PAPER-SL 的 read1 source、同一 read1 source 下的 QB 参数相对比较，以及真正无 READ 的 controls 不因该审计自动撤销。受影响的是把旧 PAPER-SL logical0 直接表述为 canonical logical0→zero 的结论。",
        "",
        "## 机器审计结果",
        "",
        f"- case 数：{validation['case_count']}；matched pair 数：{validation['matched_pair_count']}。",
        f"- validator：`{validation['status']}`。",
        "",
        "## Case inventory",
        "",
        "| case | stored state | role | classification | validity | source lineage |",
        "|---|---|---|---|---|---|",
    ]
    for case in manifest["cases"]:
        lines.append("| `{}` | {} | `{}` | `{}` | `{}` | {} |".format(
            case["id"], case.get("stored_state", "unknown"), case.get("case_role", ""),
            case.get("classification", ""), case.get("current_validity", ""),
            " → ".join(case.get("source_lineage", []))))
    lines += ["", "## Required action", "", "1. 继续使用正式四角色命名。", "2. 对 canonical logical0 gate 只使用 `neg-init-pos-read.cir` 或其协议完全一致的后继。", "3. 先完成新 Exploration 的 12 ps canonical logical0 correction，再决定 13/14/15 ps。", "4. 未完成 ideal replay 的 1/0/0 closure 前，不进入 physical BVM→JSL12→QB。", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=ROOT / "docs/BVM_READ_SEMANTICS_MANIFEST.yaml")
    ap.add_argument("--report", type=Path, default=ROOT / "docs/BVM_READ_SEMANTICS_AUDIT.md")
    args = ap.parse_args()
    manifest = build_manifest()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    from verify_bvm_read_semantics import validate_manifest
    validation = validate_manifest(manifest)
    args.report.write_text(build_report(manifest, validation), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
