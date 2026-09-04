#!/usr/bin/env python3
"""Static artifact and scope checks before the physical run set."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402

sys.path.insert(0, str(EXP))
from generate_decks import MASKS, TEMPLATE, TEMPLATE_SHA256, required_probe_labels, sha256  # noqa: E402


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def git_status() -> list[str]:
    output = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO,
        text=True,
    )
    return [line for line in output.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()

    status = git_status()
    if args.require_clean and status:
        raise RuntimeError("working tree is not clean: " + repr(status))
    provenance_path = EXP / "provenance.json"
    if not provenance_path.is_file():
        raise RuntimeError(f"missing preregistered provenance: {provenance_path}")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if sha256(TEMPLATE) != TEMPLATE_SHA256:
        raise RuntimeError("physical template SHA-256 changed")
    required_sources = (TEMPLATE, VARIANT, HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL, SHARED_JJMIT, SOLVER, CANONICAL_BVM)
    missing_sources = [rel(path) for path in required_sources if not path.is_file()]
    if missing_sources:
        raise RuntimeError(f"missing required source files: {missing_sources}")
    if provenance.get("authorized_head") != provenance.get("head_before_setup"):
        raise RuntimeError("authorized_head/head_before_setup mismatch in provenance")
    if provenance.get("source_class") != "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT":
        raise RuntimeError("unexpected source class")
    if "circuits/bvm/bvm_cell.cir" in json.dumps(provenance, ensure_ascii=False):
        # The canonical path is allowed only in the explicit not-used record.
        statement = provenance.get("canonical_bvm_statement", "")
        if "not used" not in statement:
            raise RuntimeError("canonical BVM boundary is not explicit")

    expected = tuple(required_probe_labels())
    result: dict[str, object] = {
        "schema": "bvmsim-4bvm-allone-selective-read-static-preflight-v1",
        "status": "PASS",
        "experiment": EXP.name,
        "check_only": args.check_only,
        "require_clean": args.require_clean,
        "git_status": status,
        "template": {"path": rel(TEMPLATE), "sha256": sha256(TEMPLATE)},
        "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER)},
        "canonical_bvm_used": False,
        "required_probe_count": len(expected),
        "masks": {},
    }

    for mask in MASKS:
        deck = EXP / "runs" / mask / "deck.cir"
        if not deck.is_file():
            raise RuntimeError(f"missing deck for mask {mask}: {deck}")
        text = deck.read_text(encoding="utf-8")
        if "circuits/bvm/bvm_cell.cir" in text:
            raise RuntimeError(f"mask {mask}: canonical BVM included")
        if "bvm_jm2_connected.cir" not in text:
            raise RuntimeError(f"mask {mask}: JM2-connected variant missing")
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
            raise RuntimeError(f"mask {mask}: deck QA failed: {qa}")
        record = provenance.get("b_side_decks", {}).get(mask, {})
        if record.get("sha256") != sha256(deck):
            raise RuntimeError(f"mask {mask}: deck hash differs from provenance")
        absent = {}
        for name in ("raw.csv", "run.log", "metadata.json"):
            target = EXP / "runs" / mask / name
            absent[name] = not target.exists()
            if not absent[name]:
                raise RuntimeError(f"mask {mask}: refusing to overwrite existing {target}")
        result["masks"][mask] = {  # type: ignore[index]
            "deck": rel(deck),
            "deck_sha256": sha256(deck),
            "deck_qa": qa,
            "outputs_absent": absent,
        }

    # A raw reader smoke check is only performed if a caller explicitly invokes
    # this preflight after artifacts exist; the normal pre-run path requires
    # those artifacts to be absent and therefore does not fabricate evidence.
    result["source_hashes"] = {
        name: sha256(path)
        for name, path in {
            "jm2_connected_variant": VARIANT,
            "historical_bvm": HISTORICAL_BVM,
            "historical_qb": HISTORICAL_QB,
            "historical_jtl": HISTORICAL_JTL,
            "shared_jjmit": SHARED_JJMIT,
        }.items()
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"STATIC_PREFLIGHT_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
