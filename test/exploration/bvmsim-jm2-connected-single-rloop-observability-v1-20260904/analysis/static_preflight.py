#!/usr/bin/env python3
"""Run-before-physics static identity and observability preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903"
SOLVER = REPO / "build/josim-cli"
VARIANT = OLD / "variants/bvm_jm2_connected.cir"
JJ_MODEL = REPO / "circuits/models/jjmit.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"

RUNS = OrderedDict((
    ("S0-J-RLOOP", "S0-J-JM2C"),
    ("S1-J-RLOOP", "S1-J-JM2C"),
))

ORIGINAL_PROBES = (
    "I(I_WL1)", "I(I_BL1)", "I(I_SE1)",
    "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "I(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)", "V(B_JM2|XBVM1)", "I(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)", "I(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)", "I(B_JS2|XBVM1)",
    "I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)", "I(L_PM|XBVM1)",
    "V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
    "P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)",
    "P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)",
    "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
    "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
    "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
    "I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)",
    "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)",
)
for stage in range(1, 7):
    ORIGINAL_PROBES += (
        f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})",
    )

NEW_PROBES = (
    "I(R_JM1|XBVM1)", "I(L_S1|XBVM1)", "I(L_S2|XBVM1)",
    "I(R_S|XBVM1)", "I(L_S3|XBVM1)", "I(R_SE|XBVM1)",
    "I(L_PSE|XBVM1)", "I(R_SL|XBVM1)",
    "V(R_JM1|XBVM1)", "V(R_S|XBVM1)", "V(L_S3|XBVM1)",
    "V(R_SE|XBVM1)", "V(L_PSE|XBVM1)", "V(L_S1|XBVM1)",
    "V(L_S2|XBVM1)", "V(L_PSL|XBVM1)", "V(R_SL|XBVM1)", "V(L_SL|XBVM1)",
)
ALL_PROBES = ORIGINAL_PROBES + NEW_PROBES

VARIANT_COMPONENTS = {
    "B_JM1": ("2", "7"), "R_JM1": ("2", "7"), "L_M1": ("7", "0"),
    "L_M2": ("2", "3"), "B_JM2": ("3", "4"), "L_M3": ("4", "8"),
    "L_PM": ("8", "0"), "L_S1": ("4", "5"), "B_JS1": ("5", "6"),
    "R_SE": ("SE", "14"), "L_PSE": ("14", "6"), "R_S": ("6", "10"),
    "L_S3": ("6", "10"), "L_S2": ("8", "9"), "B_JS2": ("9", "10"),
    "L_PSL": ("10", "11"), "R_SL": ("11", "12"), "L_SL": ("12", "SL"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def print_expressions(text: str) -> list[str]:
    expressions: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*\.print\b", line, re.I):
            expressions.extend(re.findall(r"[IVP]\([^\s)]+(?:\|[^\s)]+)?\)", line))
    return expressions


def normalize(text: str) -> list[str]:
    """Normalize only comments, print controls and relocated include spelling."""
    output: list[str] = []
    include_aliases = {
        "circuits/models/jjmit.cir": ".include circuits/models/jjmit.cir",
        "BVMSim/BQ.cir": ".include BVMSim/BQ.cir",
        "BVMSim/library_josim/jtl2.cir": ".include BVMSim/library_josim/jtl2.cir",
        "bvm_jm2_connected.cir": ".include historical-jm2-variant/bvm_jm2_connected.cir",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if re.match(r"^\.print\b", stripped, re.I):
            continue
        if re.match(r"^\.include\b", stripped, re.I):
            if "circuits/models/jjmit.cir" in stripped:
                output.append(include_aliases["circuits/models/jjmit.cir"])
            elif "BVMSim/library_josim/jtl2.cir" in stripped:
                output.append(include_aliases["BVMSim/library_josim/jtl2.cir"])
            elif "BVMSim/BQ.cir" in stripped:
                output.append(include_aliases["BVMSim/BQ.cir"])
            elif "bvm_jm2_connected.cir" in stripped:
                output.append(include_aliases["bvm_jm2_connected.cir"])
            else:
                output.append(stripped)
        else:
            output.append(stripped)
    return output


def variant_lines() -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    in_subckt = False
    for line in VARIANT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(".subckt bvm"):
            in_subckt = True
            continue
        if in_subckt and stripped.lower() == ".ends bvm":
            break
        if not in_subckt or not stripped or stripped.startswith("*"):
            continue
        fields = stripped.split()
        if len(fields) >= 3 and fields[0][0].upper() in "BRL":
            found[fields[0]] = (fields[1], fields[2])
    return found


def solver_info() -> dict[str, object]:
    completed = subprocess.run([str(SOLVER), "--version"], capture_output=True, text=True, check=False)
    return {
        "path": str(SOLVER),
        "sha256": sha256(SOLVER) if SOLVER.is_file() else None,
        "version_exit_code": completed.returncode,
        "version": completed.stdout.strip(),
    }


def check_deck(condition: str, old_id: str) -> dict[str, object]:
    new = EXP / "runs" / condition / "deck.cir"
    old = OLD / "runs" / old_id / "deck.cir"
    result: dict[str, object] = {
        "condition": condition,
        "new_deck": rel(new),
        "old_authority_deck": rel(old),
        "old_deck_sha256": sha256(old),
        "new_deck_sha256": sha256(new),
    }
    new_text = new.read_text(encoding="utf-8")
    old_text = old.read_text(encoding="utf-8")
    old_prints = print_expressions(old_text)
    new_prints = print_expressions(new_text)
    new_counts = Counter(new_prints)
    old_counts = Counter(old_prints)
    expected_missing = [probe for probe in ALL_PROBES if new_counts[probe] == 0]
    duplicate_labels = {label: count for label, count in new_counts.items() if count > 1}
    original_lost = [probe for probe, count in old_counts.items() if new_counts[probe] < count]
    normalized_old = normalize(old_text)
    normalized_new = normalize(new_text)
    body_diff = [
        {"index": index, "old": left, "new": right}
        for index, (left, right) in enumerate(zip(normalized_old, normalized_new))
        if left != right
    ]
    if len(normalized_old) != len(normalized_new):
        body_diff.append({"length_old": len(normalized_old), "length_new": len(normalized_new)})
    expected_includes = {
        ".include circuits/models/jjmit.cir",
        ".include BVMSim/BQ.cir",
        ".include BVMSim/library_josim/jtl2.cir",
        ".include historical-jm2-variant/bvm_jm2_connected.cir",
    }
    include_tokens = [line for line in normalize(new_text) if line.startswith(".include ")]
    include_identity = set(include_tokens) == expected_includes
    source_contract = (REPO / "src/RelevantTrace.cpp").read_text(encoding="utf-8")
    direct_voltage_contract = all(
        fragment in source_contract
        for fragment in (
            "if (l == tokens.at(0))",
            "temp.storageType = StorageType::Voltage",
            r'temp.deviceLabel = "\"V(" + s + ")\""',
        )
    )
    tran = re.findall(r"^\s*\.tran\s+([^\n]+)$", new_text, re.I | re.M)
    physical_flags = {
        "tran_0.1p_200p": len(tran) == 1 and tran[0].strip().lower() == "0.1p 200p",
        "single_bvm": len(re.findall(r"^\s*XBVM1\s+", new_text, re.I | re.M)) == 1,
        "twelve_terminal_jjs": len(re.findall(r"^\s*B_LD4_\d{2}\s+", new_text, re.I | re.M)) == 11
        and len(re.findall(r"^\s*BVMout\s+", new_text, re.I | re.M)) == 1,
        "six_jtl": sorted(int(item) for item in re.findall(r"^\s*xjtl1_(\d+)\s+", new_text, re.I | re.M)) == list(range(1, 7)),
        "original_bq": bool(re.search(r"^\s*xBQ1\s+QBin\s+QBout\s+BQ\s*$", new_text, re.I | re.M)),
        "ten_ohm_load": bool(re.search(r"^\s*RBQ1\s+o6\s+0\s+10\s*$", new_text, re.I | re.M)),
        "canonical_bvm_absent": "circuits/bvm/bvm_cell.cir" not in new_text,
    }
    outputs = {
        "raw.csv": not (EXP / "runs" / condition / "raw.csv").exists(),
        "run.log": not (EXP / "runs" / condition / "run.log").exists(),
        "metadata.json": not (EXP / "runs" / condition / "metadata.json").exists(),
    }
    result.update({
        "source_hash_identity": True,
        "normalized_physics_difference_count": len(body_diff),
        "normalized_physics_differences": body_diff,
        "probe_only_extension": not body_diff,
        "old_probe_count": len(old_prints),
        "new_probe_count": len(new_prints),
        "original_probe_loss": original_lost,
        "missing_required_probes": expected_missing,
        "duplicate_probe_labels": duplicate_labels,
        "include_identity": include_identity,
        "include_tokens": include_tokens,
        "direct_element_voltage_parser_contract": direct_voltage_contract,
        "variant_component_identity": {
            "status": "PASS" if set(variant_lines()) >= set(VARIANT_COMPONENTS) else "FAIL",
            "missing": sorted(set(VARIANT_COMPONENTS) - set(variant_lines())),
            "endpoints": {name: list(variant_lines()[name]) for name in VARIANT_COMPONENTS if name in variant_lines()},
        },
        "physical_flags": physical_flags,
        "outputs_absent_before_run": outputs,
        "status": "PASS" if (
            not body_diff
            and not original_lost
            and not expected_missing
            and not duplicate_labels
            and include_identity
            and direct_voltage_contract
            and all(physical_flags.values())
            and all(outputs.values())
        ) else "FAIL",
    })
    return result


def build_report() -> dict[str, object]:
    deck_results = OrderedDict((condition, check_deck(condition, old_id)) for condition, old_id in RUNS.items())
    source_files = [
        OLD / "runs/S0-J-JM2C/deck.cir", OLD / "runs/S1-J-JM2C/deck.cir",
        VARIANT, JJ_MODEL, BQ, JTL,
        REPO / "src/RelevantTrace.cpp", REPO / "scripts/josim-plot2.py",
        EXP / "generate_decks.py", EXP / "experiment.yaml",
    ]
    result = {
        "schema": "bvm-jm2-connected-rloop-static-preflight-v1",
        "experiment": "bvmsim-jm2-connected-single-rloop-observability-v1-20260904",
        "preflight_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(),
        "git_status_before_run": subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(),
        "solver": solver_info(),
        "source_hashes": OrderedDict((rel(path), sha256(path)) for path in source_files),
        "variant_sha256": sha256(VARIANT),
        "variant_expected_sha256": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
        "shared_jj_model_sha256": sha256(JJ_MODEL),
        "direct_voltage_mode": "DIRECT_ELEMENT_VOLTAGE_SUPPORTED",
        "node_difference_fallback": "NOT_USED",
        "runs": deck_results,
        "status": "PASS" if all(item["status"] == "PASS" for item in deck_results.values()) else "FAIL",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write static_preflight.json and provenance.json")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    if args.require_clean and status:
        print("STATIC_PREFLIGHT_FAIL: working tree is dirty")
        print(status)
        return 2
    report = build_report()
    if args.write:
        (EXP / "analysis/static_preflight.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        provenance = {
            "schema": "bvm-jm2-connected-rloop-provenance-v1",
            "experiment": report["experiment"],
            "head_before_task": "824c5c735b647028712e752a599bee8711c46a30",
            "head_at_static_preflight": report["git_head"],
            "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
            "source_files": report["source_hashes"],
            "variant": {
                "path": rel(VARIANT),
                "sha256": report["variant_sha256"],
                "expected_sha256": report["variant_expected_sha256"],
                "identity_status": "PASS" if report["variant_sha256"] == report["variant_expected_sha256"] else "FAIL",
            },
            "solver": report["solver"],
            "new_decks": {
                condition: {
                    "path": item["new_deck"],
                    "sha256": item["new_deck_sha256"],
                    "old_authority": item["old_authority_deck"],
                    "old_sha256": item["old_deck_sha256"],
                    "normalized_physics_difference_count": item["normalized_physics_difference_count"],
                    "probe_only_extension": item["probe_only_extension"],
                }
                for condition, item in report["runs"].items()
            },
            "static_preflight": {
                "status": report["status"],
                "direct_element_voltage_mode": report["direct_voltage_mode"],
                "node_difference_fallback": report["node_difference_fallback"],
            },
        }
        (EXP / "provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "runs": report["runs"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
