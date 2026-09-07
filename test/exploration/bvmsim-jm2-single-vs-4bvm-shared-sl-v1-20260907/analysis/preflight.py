#!/usr/bin/env python3
"""Independent mechanical topology and stimulus preflight for the two decks."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SOLVER = REPO / "build/josim-cli"

TARGET_PWL = {
    "WL": "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0",
    "BL": "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0",
    "SE": "0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0",
}
QUIET_PWL = {
    "WL": "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0",
    "BL": "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0",
    "SE": "0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("*")]


def include_paths(deck: Path, text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in active_lines(text):
        if not line.lower().startswith(".include "):
            continue
        raw = line.split(None, 1)[1].strip().strip('"')
        resolved = (deck.parent / raw).resolve()
        result[raw] = rel(resolved)
    return result


def parse_controls(text: str) -> dict[str, str]:
    controls: dict[str, str] = {}
    pattern = re.compile(r"^I_(WL|BL|SE)([1-4])\s+0\s+\S+\s+pwl\((.*)\)$", re.IGNORECASE)
    for line in active_lines(text):
        match = pattern.match(line)
        if match:
            controls[f"{match.group(1).upper()}{match.group(2)}"] = " ".join(match.group(3).split())
    return controls


def parse_bvms(text: str) -> list[dict[str, str]]:
    pattern = re.compile(r"^XBVM(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+BVM$", re.IGNORECASE)
    return [
        {"instance": match.group(1), "wl": match.group(2), "bl": match.group(3), "se": match.group(4), "sl": match.group(5)}
        for line in active_lines(text)
        if (match := pattern.match(line))
    ]


def parse_jsls(text: str) -> list[dict[str, str]]:
    pattern = re.compile(r"^B_JSL(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+area=([0-9.]+)$", re.IGNORECASE)
    return [
        {"number": match.group(1), "from": match.group(2), "to": match.group(3), "model": match.group(4), "area": match.group(5)}
        for line in active_lines(text)
        if (match := pattern.match(line))
    ]


def print_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for line in active_lines(text):
        if line.lower().startswith(".print "):
            tokens.extend(line.split()[1:])
    return tokens


def downstream_lines(text: str) -> list[str]:
    lines = active_lines(text)
    start = lines.index("XBQ1 QBIN QBOUT BQ")
    end = lines.index("R_TERM JTL6_OUT 0 10") + 1
    return lines[start:end]


def expect(condition: bool, failures: list[str], name: str, detail: object) -> None:
    if not condition:
        failures.append(f"{name}: {detail}")


def expected_probe_labels(instances: list[int], endpoint: str) -> set[str]:
    labels: set[str] = set()
    for i in instances:
        h = f"XBVM{i}"
        labels.update(f"{kind}({jj}|{h})" for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2") for kind in ("P", "V", "I"))
        labels.update(f"{kind}({branch}|{h})" for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL") for kind in ("I", "V"))
        labels.update({f"I(I_WL{i})", f"I(I_BL{i})", f"I(I_SE{i})"})
    labels.add(endpoint)
    for i in range(1, 9):
        labels.update({f"P(B_JSL{i})", f"V(B_JSL{i})", f"I(B_JSL{i})"})
    labels.update({"V(QBIN)", "V(QBOUT)", "I(R_TERM)"})
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "IB"):
        labels.update({f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"})
    for jj in ("BJS", "BJ1", "BJ2"):
        labels.update({f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"})
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        labels.update({f"P(B01|{h})", f"V(B01|{h})", f"I(B01|{h})", f"P(B02|{h})", f"V(B02|{h})", f"I(B02|{h})", f"V(JTL{stage}_OUT)"})
    return labels


def check_deck(kind: str, path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    failures: list[str] = []
    includes = include_paths(path, text)
    expected_includes = {
        "../../../../../circuits/models/jjmit.cir": rel(JJMIT),
        "../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir": rel(VARIANT),
        "../../../../../BVMSim/BQ.cir": rel(BQ),
        "../../../../../BVMSim/library_josim/jtl2.cir": rel(JTL),
    }
    expect(includes == expected_includes, failures, "include_resolution", {"actual": includes, "expected": expected_includes})
    expect("circuits/bvm/bvm_cell.cir" not in text, failures, "canonical_bvm_absent", "canonical BVM token is active or embedded")
    expect(text.count(".tran 0.1p 200p") == 1, failures, "tran_count", text.count(".tran 0.1p 200p"))
    bvms = parse_bvms(text)
    jsls = parse_jsls(text)
    if kind == "single":
        expected_instances = [{"instance": "1", "wl": "WL1", "bl": "BL1", "se": "SE1", "sl": "SL1"}]
        endpoint = "V(SL1)"
        expected_upstream = "SL1"
    else:
        expected_instances = [
            {"instance": str(i), "wl": f"WL{i}", "bl": f"BL{i}", "se": f"SE{i}", "sl": "COMMON_SL"}
            for i in range(1, 5)
        ]
        endpoint = "V(COMMON_SL)"
        expected_upstream = "COMMON_SL"
    expect(bvms == expected_instances, failures, "bvm_instances", {"actual": bvms, "expected": expected_instances})
    expect(len(jsls) == 8, failures, "exactly_eight_jsl", len(jsls))
    expect([item["number"] for item in jsls] == [str(i) for i in range(1, 9)], failures, "jsl_order", jsls)
    expect(all(item["model"].casefold() == "jjmit" and item["area"] == "5.0" for item in jsls), failures, "jsl_model_area", jsls)
    if jsls:
        expect(jsls[0]["from"] == expected_upstream, failures, "jsl1_upstream", jsls[0])
        expect(jsls[-1]["to"] == "QBIN", failures, "jsl8_downstream", jsls[-1])
        expect(all(jsls[i]["to"] == jsls[i + 1]["from"] for i in range(7)), failures, "jsl_series_connections", jsls)
    expect(len(re.findall(r"(?im)^XBQ1\s+QBIN\s+QBOUT\s+BQ$", text)) == 1, failures, "exactly_one_qb", "XBQ1")
    expect(len(re.findall(r"(?im)^XJTL1_[1-6]\s+\S+\s+\S+\s+jtl$", text)) == 6, failures, "exactly_six_jtl", "XJTL1_1..XJTL1_6")
    expect(len(re.findall(r"(?im)^R_TERM\s+\S+\s+0\s+10$", text)) == 1, failures, "exactly_one_termination", "R_TERM 10 ohm")
    controls = parse_controls(text)
    expected_controls = {f"{name}{i}": TARGET_PWL[name] if kind == "single" or i == 1 else QUIET_PWL[name] for i in range(1, 5) for name in ("WL", "BL", "SE") if kind == "array" or i == 1}
    expect(controls == expected_controls, failures, "registered_stimulus", {"actual": controls, "expected": expected_controls})
    tokens = set(print_tokens(text))
    required = expected_probe_labels([int(item["instance"]) for item in bvms], endpoint)
    missing = sorted(required - tokens)
    expect(not missing, failures, "full_probe_schema", missing[:20])
    duplicate_prints = sorted(token for token in tokens if print_tokens(text).count(token) > 1)
    expect(not duplicate_prints, failures, "duplicate_probe_labels", duplicate_prints[:20])
    return {
        "kind": kind,
        "path": rel(path),
        "deck_sha256": sha256(path),
        "bytes": path.stat().st_size,
        "bvm_count": len(bvms),
        "jsl_count": len(jsls),
        "qb_count": len(re.findall(r"(?im)^XBQ1\s+QBIN\s+QBOUT\s+BQ$", text)),
        "jtl_count": len(re.findall(r"(?im)^XJTL1_[1-6]\s+\S+\s+\S+\s+jtl$", text)),
        "termination_count": len(re.findall(r"(?im)^R_TERM\s+\S+\s+0\s+10$", text)),
        "include_resolution": includes,
        "controls": controls,
        "probe_count": len(tokens),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    decks = {kind: EXP / "runs" / kind / "deck.cir" for kind in ("single", "array")}
    failures: list[str] = []
    for path in (VARIANT, HISTORICAL_BVM, CANONICAL_BVM, JJMIT, BQ, JTL, SOLVER):
        expect(path.is_file(), failures, "required_source", rel(path) if path.exists() else str(path))
    checks = {kind: check_deck(kind, path) if path.is_file() else {"status": "FAIL", "failures": ["deck missing"]} for kind, path in decks.items()}
    for kind, result in checks.items():
        failures.extend(f"{kind}.{item}" for item in result.get("failures", []))
    if all(path.is_file() for path in decks.values()):
        single_text = decks["single"].read_text(encoding="utf-8")
        array_text = decks["array"].read_text(encoding="utf-8")
        expect(downstream_lines(single_text) == downstream_lines(array_text), failures, "downstream_block_identity", "SINGLE and ARRAY downstream text differs")
        single_controls = parse_controls(single_text)
        array_controls = parse_controls(array_text)
        expect({name: single_controls[name] for name in ("WL1", "BL1", "SE1")} == {name: array_controls[name] for name in ("WL1", "BL1", "SE1")}, failures, "target_control_static_identity", "SINGLE target deck and ARRAY BVM1 deck differ")
        expect(len(re.findall(r"(?im)^B_JSL\d+\s+", single_text)) == 8, failures, "single_jsl_line_count", "not 8")
        expect(len(re.findall(r"(?im)^B_JSL\d+\s+", array_text)) == 8, failures, "array_jsl_line_count", "not 8")
    variant_lines = VARIANT.read_text(encoding="utf-8").splitlines() if VARIANT.is_file() else []
    historical_lines = HISTORICAL_BVM.read_text(encoding="utf-8").splitlines() if HISTORICAL_BVM.is_file() else []
    differences = [
        {"line": index + 1, "historical": left, "variant": right}
        for index, (left, right) in enumerate(zip(historical_lines, variant_lines))
        if left != right
    ]
    expected_difference = [{"line": 37, "historical": "L_M2    2       4       24.5P", "variant": "L_M2    2       3       24.5P"}]
    expect(len(historical_lines) == len(variant_lines) and differences == expected_difference, failures, "jm2_variant_diff", differences)
    result = {
        "schema": "jm2-single-vs-4bvm-shared-sl-topology-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "PASS" if not failures else "FAIL",
        "head_at_preflight": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER) if SOLVER.is_file() else None},
        "source_hashes": {name: sha256(path) if path.is_file() else None for name, path in {"bvm_variant": VARIANT, "qb": BQ, "jtl": JTL, "jjmit": JJMIT, "canonical_bvm_not_used": CANONICAL_BVM}.items()},
        "variant_diff": {"status": "PASS" if differences == expected_difference else "FAIL", "differences": differences},
        "decks": checks,
        "cross_fixture": {
            "downstream_text_identical": not any(item.startswith("downstream_block_identity") for item in failures),
            "target_static_controls_identical": not any(item.startswith("target_control_static_identity") for item in failures),
            "same_nominal_tran": True,
            "same_jsl_count_area_model": True,
            "canonical_bvm_used": False,
        },
        "failures": failures,
    }
    write_once(EXP / "analysis/topology_preflight.json", json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# PREFLIGHT — JM2-connected SINGLE vs 4-BVM shared-SL",
        "",
        f"- Status: **{result['status']}**",
        f"- Preflight time: `{result['created_at_local']}`",
        f"- HEAD at preflight: `{result['head_at_preflight']}`",
        "- Scientific tier: `EXPLORATION / QUICK`; no physical mechanism interpretation is registered.",
        "",
        "## Frozen scope",
        "",
        "- BVM source is the historical JM2-connected variant; `circuits/bvm/bvm_cell.cir` is not used.",
        "- Both fixtures use exactly 8 `jjmit area=5.0` JSL junctions, the exact `BVMSim/BQ.cir`, the exact six-stage `BVMSim/library_josim/jtl2.cir`, and one 10-ohm termination.",
        "- The target controls and absolute timing are registered identically; ARRAY BVM2–BVM4 are quiet only during the final selective READ.",
        "- Full P/V/I probe coverage is retained in both raw runs, including JSL2–JSL7 and ARRAY BVM2–BVM4.",
        "",
        "## Mechanical checks",
        "",
        "| check | result |",
        "|---|---|",
        f"| SINGLE topology | `{checks.get('single', {}).get('status', 'FAIL')}`; 1 BVM, 8 JSL, 1 QB, 6 JTL, 1 × 10 Ω |",
        f"| ARRAY topology | `{checks.get('array', {}).get('status', 'FAIL')}`; 4 BVM, 8 shared JSL, 1 QB, 6 JTL, 1 × 10 Ω |",
        f"| JM2 variant diff | `{'PASS' if differences == expected_difference else 'FAIL'}`; only registered `L_M2` node 4 → 3 |",
        f"| downstream identity | `{'PASS' if not any(item.startswith('downstream_block_identity') for item in failures) else 'FAIL'}` |",
        f"| target static control identity | `{'PASS' if not any(item.startswith('target_control_static_identity') for item in failures) else 'FAIL'}` |",
        f"| full probe schema | `{'PASS' if not any('full_probe_schema' in item for item in failures) else 'FAIL'}` |",
        "",
        "## Decision",
        "",
        ("Preflight passed. The two registered physical runs may execute directly." if result["status"] == "PASS" else "Preflight failed. No physical run is authorized by this preregistration; preserve the failed artifact and stop."),
        "",
        "Machine record: `analysis/topology_preflight.json`.",
        "",
    ]
    write_once(EXP / "PREFLIGHT.md", "\n".join(lines))
    print(json.dumps({"status": result["status"], "failures": failures, "record": "analysis/topology_preflight.json"}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
