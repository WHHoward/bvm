#!/usr/bin/env python3
"""在 JoSIM 调用前执行静态、拓扑和产物边界检查。"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
A_ROOT = REPO / "test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903"
A_ENDPOINT_ROOT = A_ROOT / "runs_sl_endpoints"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
SOLVER = REPO / "build/josim-cli"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.deckqa import deck_qa  # noqa: E402
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


def required_labels() -> tuple[str, ...]:
    controls = tuple(
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "BL", "SE")
    )
    groups = (
        flatten_probe_labels(historical_bvm_array_probes(4)),
        flatten_probe_labels(historical_sensing_line_endpoint_probes()),
        flatten_probe_labels(original_bvmsim_qb_probes()),
        flatten_probe_labels(historical_jtl_probes(6)),
    )
    output: list[str] = []
    for label in controls + tuple(label for group in groups for label in group):
        if label not in output:
            output.append(label)
    return tuple(output)


def active_print_labels(text: str) -> list[str]:
    labels: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(".print"):
            labels.extend(stripped.split()[1:])
    return labels


def normalize(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.lower().startswith(".include "):
            token = stripped.split(None, 1)[1].strip().strip('"').replace("\\", "/")
            if token.endswith("BVMSim/bvm_cell.cir") or token.endswith("bvm_jm2_connected.cir"):
                lines.append(".include BVM_VARIANT_OR_HISTORICAL")
                continue
        lines.append(stripped)
    return lines


def git_status() -> list[str]:
    output = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True)
    return [line for line in output.splitlines() if line]


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="保留接口；本检查默认不写文件")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    if args.require_clean and git_status():
        fail("运行前工作树不干净: " + repr(git_status()))

    provenance_path = EXP / "provenance.json"
    if not provenance_path.is_file():
        fail("缺少预注册 provenance.json")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("head_before_setup") != "d54233d76ed78806191d752bc3d11070e5b88697":
        fail("provenance 的授权 HEAD 与已审阅 HEAD 不一致")
    for path in (HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL, SHARED_JJMIT, VARIANT, SOLVER):
        if not path.is_file():
            fail(f"缺少 required file: {path}")
    if provenance["source_records"]["jm2_connected_variant"]["sha256"] != sha256(VARIANT):
        fail("JM2-connected variant hash 已变化")
    if provenance["source_records"]["historical_bvm"]["sha256"] != sha256(HISTORICAL_BVM):
        fail("historical BVM hash 已变化")

    results: dict[str, object] = {
        "status": "PASS",
        "experiment": EXP.name,
        "clean_required": args.require_clean,
        "git_status": git_status(),
        "states": {},
        "checks": {
            "canonical_bvm_used": False,
            "input_intermediate_dir_absent": not (EXP / "inputs").exists(),
            "solver_executable": str(SOLVER),
            "solver_sha256": sha256(SOLVER),
        },
    }
    if (EXP / "inputs").exists():
        fail("新实验不允许 inputs/*.cir 中间层")

    expected = required_labels()
    for state in STATES:
        deck = EXP / "runs" / state / "deck.cir"
        source = A_ENDPOINT_ROOT / state / "deck.cir"
        if not deck.is_file() or not source.is_file():
            fail(f"缺少 state={state} 的 B/A deck")
        text = deck.read_text(encoding="utf-8")
        source_text = source.read_text(encoding="utf-8")
        if normalize(text) != normalize(source_text):
            diff = "\n".join(difflib.unified_diff(normalize(source_text), normalize(text), lineterm=""))
            fail(f"state={state}: A/B deck 有未授权差异:\n{diff}")
        active = active_print_labels(text)
        duplicate_prints = sorted({label for label in active if active.count(label) > 1})
        missing = [label for label in expected if label not in active]
        if duplicate_prints:
            fail(f"state={state}: active .print 重复探针 {duplicate_prints}")
        if missing:
            fail(f"state={state}: deck 缺少 probes {missing}")
        if "circuits/bvm/bvm_cell.cir" in text or "BVMSim/bvm_cell.cir" in text:
            fail(f"state={state}: canonical/historical BVM include 边界错误")
        if "bvm_jm2_connected.cir" not in text:
            fail(f"state={state}: 缺少 JM2-connected variant include")
        qa = deck_qa(
            deck,
            expected_includes=("bvm_jm2_connected.cir", "BVMSim/BQ.cir", "BVMSim/library_josim/jtl2.cir"),
            expected_bvm_instances=4,
            expected_terminal_sensing_jj_count=12,
            expected_jtl_stages=6,
            expected_termination_ohm=10.0,
            expected_tran_timestep_ps=0.1,
            required_probes=expected,
        )
        if qa["status"] != "ARTIFACT_VALID":
            fail(f"state={state}: deck QA 失败 {qa}")
        recorded_hash = provenance["b_side_decks"][state]["sha256"]
        if recorded_hash != sha256(deck):
            fail(f"state={state}: deck hash 与 provenance 不一致")
        output_paths = (
            EXP / "runs" / state / "raw.csv",
            EXP / "runs" / state / "run.log",
            EXP / "runs" / state / "metadata.json",
        )
        existing = [rel(path) for path in output_paths if path.exists()]
        if existing:
            fail(f"state={state}: 拒绝覆盖已有运行产物 {existing}")
        results["states"][state] = {  # type: ignore[index]
            "deck": rel(deck),
            "deck_sha256": sha256(deck),
            "a_endpoint_deck": rel(source),
            "normalized_a_b_difference": "JM2 include only",
            "deck_qa": qa,
            "required_probe_count": len(expected),
            "output_paths_absent": True,
        }

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"STATIC_PREFLIGHT_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
