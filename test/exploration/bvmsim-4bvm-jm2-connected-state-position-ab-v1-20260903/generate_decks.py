#!/usr/bin/env python3
"""从不可变的 A 侧 endpoint deck 生成 JM2-connected 六状态 deck。

生成器只改变四个 BVM 的 include 路径。它不会重建 stimulus、QB、JTL 或
print 顺序，且拒绝覆盖已经存在的 deck/raw 产物。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
A_ROOT = REPO / "test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903"
A_ENDPOINT_ROOT = A_ROOT / "runs_sl_endpoints"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
SOLVER = REPO / "build/josim-cli"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_array_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)
from bvmtools.sl_probes import historical_sensing_line_endpoint_probes  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"拒绝覆盖已有产物: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def variant_diff() -> dict[str, object]:
    old = HISTORICAL_BVM.read_text(encoding="utf-8").splitlines()
    new = VARIANT.read_text(encoding="utf-8").splitlines()
    differences = [
        {"line": index + 1, "historical": left, "connected": right}
        for index, (left, right) in enumerate(zip(old, new))
        if left != right
    ]
    if len(old) != len(new):
        raise RuntimeError("JM2 variant 与 historical BVM 行数不同")
    expected = {
        "line": 37,
        "historical": "L_M2    2       4       24.5P",
        "connected": "L_M2    2       3       24.5P",
    }
    if differences != [expected]:
        raise RuntimeError(f"variant 存在未授权差异: {differences}")
    return {
        "status": "PASS",
        "difference_count": 1,
        "difference": expected,
        "historical_sha256": sha256(HISTORICAL_BVM),
        "connected_variant_sha256": sha256(VARIANT),
    }


def expected_labels() -> tuple[str, ...]:
    controls = tuple(
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "BL", "SE")
    )
    bvm = flatten_probe_labels(historical_bvm_array_probes(4))
    endpoint = flatten_probe_labels(historical_sensing_line_endpoint_probes())
    qb = flatten_probe_labels(original_bvmsim_qb_probes())
    jtl = flatten_probe_labels(historical_jtl_probes(6))
    output: list[str] = []
    for label in controls + bvm + endpoint + qb + jtl:
        if label not in output:
            output.append(label)
    return tuple(output)


def active_print_labels(text: str) -> list[str]:
    labels: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(".print"):
            continue
        labels.extend(stripped.split()[1:])
    return labels


def normalized_lines(text: str) -> list[str]:
    """Drop comments/blank lines and normalize exactly the BVM include."""

    normalized: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.lower().startswith(".include "):
            token = stripped.split(None, 1)[1].strip().strip('"')
            token = token.replace("\\", "/")
            if token.endswith("BVMSim/bvm_cell.cir") or token.endswith("bvm_jm2_connected.cir"):
                normalized.append(".include BVM_VARIANT_OR_HISTORICAL")
                continue
        normalized.append(stripped)
    return normalized


def source_deck(state: str) -> Path:
    path = A_ENDPOINT_ROOT / state / "deck.cir"
    if not path.is_file():
        raise RuntimeError(f"缺少 A 侧不可变 endpoint deck: {path}")
    return path


def make_deck(state: str) -> tuple[str, Path]:
    source_path = source_deck(state)
    source = source_path.read_text(encoding="utf-8")
    old_include = re.compile(r"(?m)^\.include\s+[^\n]*BVMSim/bvm_cell\.cir\s*$")
    matches = old_include.findall(source)
    if len(matches) != 1:
        raise RuntimeError(f"{source_path}: historical BVM include 数量不是 1: {len(matches)}")
    deck_dir = EXP / "runs" / state
    variant_include = os.path.relpath(VARIANT, deck_dir).replace("\\", "/")
    content = old_include.sub(f".include {variant_include}", source, count=1)
    header = (
        f"* GENERATED JM2-CONNECTED PHASE B DECK: state={state}\n"
        "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT\n"
        "* A/B difference is the approved BVM JM2 L_M2 node connection only\n"
        "* all QB/JTL/sensing/stimulus/termination values are inherited unchanged\n"
    )
    return header + content, source_path


def validate_content(state: str, content: str, source_path: Path) -> None:
    required_tokens = (
        "bvm_jm2_connected.cir",
        ".include ../../../../../BVMSim/BQ.cir",
        ".include ../../../../../BVMSim/library_josim/jtl2.cir",
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        "XBVM2 WL2 BL2 SE2 SL2 BVM",
        "XBVM3 WL3 BL3 SE3 SL3 BVM",
        "XBVM4 WL4 BL4 SE4 SL4 BVM",
        "BVMout    nld4_21 QBin jjmit area=3.2",
        "xBQ1 QBin QBout BQ",
        "xjtl1_6 o5 o6 jtl",
        "RBQ1 o6 0 10",
        ".tran 0.1p 200p 45p",
    )
    lowered = content.lower()
    for token in required_tokens:
        if token.lower() not in lowered:
            raise RuntimeError(f"{state}: deck 缺少 {token}")
    if "circuits/bvm/bvm_cell.cir" in content:
        raise RuntimeError(f"{state}: 意外包含 canonical BVM")
    if "BVMSim/bvm_cell.cir" in content:
        raise RuntimeError(f"{state}: historical BVM include 未被替换")
    instances = re.findall(r"(?mi)^\s*XBVM(\d+)\s+", content)
    if sorted(instances) != ["1", "2", "3", "4"]:
        raise RuntimeError(f"{state}: BVM 实例异常: {instances}")
    source_norm = normalized_lines(source_path.read_text(encoding="utf-8"))
    candidate_norm = normalized_lines(content)
    if source_norm != candidate_norm:
        diff = "\n".join(
            difflib.unified_diff(source_norm, candidate_norm, fromfile=str(source_path), tofile="candidate", lineterm="")
        )
        raise RuntimeError(f"{state}: A/B 归一化后存在未授权差异:\n{diff}")
    labels = active_print_labels(content)
    duplicate_labels = sorted({label for label in labels if labels.count(label) > 1})
    if duplicate_labels:
        raise RuntimeError(f"{state}: active .print 存在重复探针: {duplicate_labels}")
    missing = [label for label in expected_labels() if label not in labels]
    if missing:
        raise RuntimeError(f"{state}: deck 缺少 required probes: {missing}")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def write_provenance(deck_records: dict[str, dict[str, object]], head: str) -> None:
    sources = {
        "historical_fixture": HISTORICAL_BVM.parent / "test_bvm_mixed_0.cir",
        "historical_bvm": HISTORICAL_BVM,
        "historical_qb": HISTORICAL_QB,
        "historical_jtl": HISTORICAL_JTL,
        "shared_jjmit_reference": SHARED_JJMIT,
        "canonical_bvm_not_used": CANONICAL_BVM,
        "jm2_connected_variant": VARIANT,
    }
    a_records = {
        state: {
            "formal_deck": rel(A_ROOT / "runs" / state / "deck.cir"),
            "formal_deck_sha256": sha256(A_ROOT / "runs" / state / "deck.cir"),
            "formal_raw": rel(A_ROOT / "runs" / state / "raw.csv"),
            "formal_raw_sha256": sha256(A_ROOT / "runs" / state / "raw.csv"),
            "endpoint_deck": rel(A_ENDPOINT_ROOT / state / "deck.cir"),
            "endpoint_deck_sha256": sha256(A_ENDPOINT_ROOT / state / "deck.cir"),
            "endpoint_raw": rel(A_ENDPOINT_ROOT / state / "raw.csv"),
            "endpoint_raw_sha256": sha256(A_ENDPOINT_ROOT / state / "raw.csv"),
        }
        for state in STATES
    }
    source_records = {
        name: {"path": rel(path), "sha256": sha256(path)}
        for name, path in sources.items()
    }
    record = {
        "schema": "bvmsim-4bvm-jm2-connected-state-position-ab-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_before_setup": head,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "source_records": source_records,
        "variant_diff": variant_diff(),
        "a_side": a_records,
        "b_side_decks": deck_records,
        "solver": {
            "path": rel(SOLVER),
            "sha256": sha256(SOLVER),
            "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True),
        },
        "frozen": {
            "states": list(STATES),
            "timestep_ps": 0.1,
            "stop_time_ps": 200,
            "output_start_ps": 45,
            "qb": "BVMSim/BQ.cir; RJ1=12 ohm; RJ2=4 ohm; IB=250 uA",
            "jtl": "BVMSim/library_josim/jtl2.cir; six stages; 10 ohm termination",
        },
        "canonical_bvm_statement": "canonical circuits/bvm/bvm_cell.cir was not used; historical BVM and canonical BVM remain distinct authorities",
    }
    write_once(EXP / "provenance.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    required_files = (HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL, SHARED_JJMIT, VARIANT, SOLVER)
    for path in required_files:
        if not path.is_file():
            raise RuntimeError(f"缺少 required file: {path}")
    variant_diff()
    records: dict[str, dict[str, object]] = {}
    contents: dict[str, str] = {}
    for state in STATES:
        content, source_path = make_deck(state)
        validate_content(state, content, source_path)
        contents[state] = content
        records[state] = {
            "path": rel(EXP / "runs" / state / "deck.cir"),
            "source_endpoint_deck": rel(source_path),
            "source_endpoint_deck_sha256": sha256(source_path),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "variant_include": os.path.relpath(VARIANT, EXP / "runs" / state).replace("\\", "/"),
        }
    if args.check_only:
        print(json.dumps({"status": "PASS", "states": list(STATES), "writes": False}, ensure_ascii=False))
        return 0
    for state, content in contents.items():
        write_once(EXP / "runs" / state / "deck.cir", content)
    write_provenance(records, git_head())
    print(json.dumps({"status": "PASS", "states": list(STATES), "writes": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
