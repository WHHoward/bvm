#!/usr/bin/env python3
"""Generate the frozen RJ1 variants and all 24 experiment-local decks.

The source templates are existing, hash-recorded exploratory fixtures.  The
generated decks change only the include path to the local QB variant, the
four-BVM timestep, and the run metadata comment.  No historical fixture is
edited.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
CANONICAL_QB = REPO / "circuits/qb/bq_cell_bvmsim_v1.cir"
FOUR_TEMPLATE = REPO / "test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/migrated/T100.cir"
S0_TEMPLATE = REPO / "test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/inputs/s0-j.cir"
S1_TEMPLATE = REPO / "test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/inputs/s1-j.cir"

VARIANTS = {
    "R12": (12.0, "qb-rj1-12.cir"),
    "R11P5": (11.5, "qb-rj1-11p5.cir"),
    "R11": (11.0, "qb-rj1-11.cir"),
}
FOUR_TIMESTEPS = {
    "T100": 0.1,
    "T050": 0.05,
    "T025": 0.025,
    "T0125": 0.0125,
}
SINGLE_TIMESTEPS = {"T025": 0.025, "T0125": 0.0125}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite existing generated file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def variant_text(rj1: float) -> str:
    text = CANONICAL_QB.read_text(encoding="utf-8")
    matches = [match.rstrip() for match in re.findall(r"(?m)^RJ1\s+2\s+0\s+[^\s]+\s*$", text)]
    if matches != ["RJ1 2 0 12"]:
        raise RuntimeError(f"unexpected canonical QB RJ1 line: {matches!r}")
    replacement = f"RJ1 2 0 {int(rj1) if rj1.is_integer() else rj1:g}"
    return text.replace(matches[0], replacement, 1)


def rewrite_includes(text: str, qb_filename: str) -> str:
    replacements = {
        "../../../../circuits/models/jjmit.cir": "../../../../../circuits/models/jjmit.cir",
        "../../../../BVMSim/bvm_cell.cir": "../../../../../BVMSim/bvm_cell.cir",
        "../../../../BVMSim/library_josim/jtl2.cir": "../../../../../BVMSim/library_josim/jtl2.cir",
        "../../../../circuits/qb/bq_cell_bvmsim_v1.cir": f"../../inputs/{qb_filename}",
    }
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"template include not found: {old}")
        text = text.replace(old, new)
    return text


def replace_tran(text: str, timestep_ps: float, *, four: bool) -> str:
    replacement = f".tran {timestep_ps:g}p 200p 45p" if four else f".tran {timestep_ps:g}p 200p"
    updated, count = re.subn(r"(?m)^\.tran\s+[^\n]+$", replacement, text)
    if count != 1:
        raise RuntimeError(f"expected one .tran line, found {count}")
    return updated


def make_deck(template: Path, run_id: str, qb_filename: str, timestep_ps: float, *, four: bool, state: str | None = None) -> str:
    text = template.read_text(encoding="utf-8")
    text = rewrite_includes(text, qb_filename)
    text = replace_tran(text, timestep_ps, four=four)
    metadata = (
        f"* GENERATED RUN {run_id}; RJ1 variant {qb_filename}; dt={timestep_ps:g} ps\n"
        f"* Physics template: {template.relative_to(REPO)}; state={state or 'collective'}\n"
    )
    return metadata + text


def normalized_qb_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if re.match(r"^RJ1\s+2\s+0\s+", line):
            lines.append("RJ1 2 0 <RJ1>")
        else:
            lines.append(line)
    return lines


def normalized_deck(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.startswith(".include ../../inputs/qb-rj1-"):
            result.append(".include <LOCAL_QB_VARIANT>")
        elif stripped.startswith(".tran "):
            result.append(".tran <RUN_TIMESTEP>")
        else:
            result.append(line)
    return result


def config_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rkey, (rj1, qb_filename) in VARIANTS.items():
        for tkey, timestep in FOUR_TIMESTEPS.items():
            records.append(
                {
                    "run_id": f"F4_{rkey}_{tkey}",
                    "family": "four_bvm",
                    "rj1_ohm": rj1,
                    "rj1_key": rkey,
                    "timestep_ps": timestep,
                    "state": "collective",
                    "template": str(FOUR_TEMPLATE.relative_to(REPO)),
                    "qb_variant": qb_filename,
                    "four_bvm": True,
                }
            )
        for tkey, timestep in SINGLE_TIMESTEPS.items():
            for state in ("S0", "S1"):
                records.append(
                    {
                        "run_id": f"S1B_{rkey}_{tkey}_{state}",
                        "family": "single_bvm_protection",
                        "rj1_ohm": rj1,
                        "rj1_key": rkey,
                        "timestep_ps": timestep,
                        "state": state,
                        "template": str((S0_TEMPLATE if state == "S0" else S1_TEMPLATE).relative_to(REPO)),
                        "qb_variant": qb_filename,
                        "four_bvm": False,
                    }
                )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    for path in (CANONICAL_QB, FOUR_TEMPLATE, S0_TEMPLATE, S1_TEMPLATE):
        if not path.is_file():
            raise RuntimeError(f"missing source/template: {path}")

    if args.check_only:
        print("source templates present")
        return 0

    variant_records: list[dict[str, Any]] = []
    variant_texts: dict[str, str] = {}
    for rkey, (rj1, filename) in VARIANTS.items():
        text = variant_text(rj1)
        path = EXP / "inputs" / filename
        write_new(path, text)
        variant_texts[rkey] = text
        variant_records.append(
            {
                "rj1_key": rkey,
                "rj1_ohm": rj1,
                "path": str(path.relative_to(REPO)),
                "sha256": sha256(path),
                "diff_from_authoritative": list(
                    difflib.unified_diff(
                        CANONICAL_QB.read_text(encoding="utf-8").splitlines(),
                        text.splitlines(),
                        fromfile="circuits/qb/bq_cell_bvmsim_v1.cir",
                        tofile=filename,
                        lineterm="",
                    )
                ),
            }
        )

    normalized_variant_equal = len({tuple(normalized_qb_lines(text)) for text in variant_texts.values()}) == 1
    if not normalized_variant_equal:
        raise RuntimeError("QB variants differ beyond RJ1")

    deck_records: list[dict[str, Any]] = []
    for record in config_records():
        template = REPO / record["template"]
        deck_path = EXP / "runs" / record["run_id"] / "deck.cir"
        deck_text = make_deck(
            template,
            record["run_id"],
            record["qb_variant"],
            record["timestep_ps"],
            four=record["four_bvm"],
            state=record["state"],
        )
        write_new(deck_path, deck_text)
        deck_records.append(
            {
                **record,
                "deck": str(deck_path.relative_to(REPO)),
                "deck_sha256": sha256(deck_path),
                "raw": str((deck_path.parent / "raw/run-01.csv").relative_to(REPO)),
                "normalized_physics_sha256": hashlib.sha256(
                    "\n".join(normalized_deck(deck_text)).encode("utf-8")
                ).hexdigest(),
            }
        )

    four_fingerprints = {
        item["normalized_physics_sha256"]
        for item in deck_records
        if item["family"] == "four_bvm"
    }
    if len(four_fingerprints) != 1:
        raise RuntimeError("four-BVM decks differ beyond declared QB/timestep substitutions")
    single_by_state: dict[str, set[str]] = {"S0": set(), "S1": set()}
    for item in deck_records:
        if item["family"] == "single_bvm_protection":
            single_by_state[item["state"]].add(item["normalized_physics_sha256"])
    if any(len(values) != 1 for values in single_by_state.values()):
        raise RuntimeError("single-BVM decks differ beyond declared QB/timestep substitutions within a state")

    manifest = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": str(Path(__file__).relative_to(REPO)),
        "source_hashes": {
            str(path.relative_to(REPO)): sha256(path)
            for path in (CANONICAL_QB, FOUR_TEMPLATE, S0_TEMPLATE, S1_TEMPLATE)
        },
        "variant_rule": "only RJ1 2 0 12/11.5/11 may differ",
        "variant_normalized_equal": normalized_variant_equal,
        "variants": variant_records,
        "deck_count": len(deck_records),
        "decks": deck_records,
        "deck_physics_fingerprint": {
            "four_bvm_unique_count": len(four_fingerprints),
            "single_s0_unique_count": len(single_by_state["S0"]),
            "single_s1_unique_count": len(single_by_state["S1"]),
        },
        "no_historical_file_modified": True,
    }
    manifest_path = EXP / "analysis" / "deck_manifest.json"
    write_new(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    check_path = EXP / "inputs" / "variant_diff_check.json"
    write_new(
        check_path,
        json.dumps(
            {
                "status": "PASS",
                "rule": "QB variants must have identical normalized lines after replacing RJ1 with <RJ1>",
                "normalized_equal": normalized_variant_equal,
                "variant_paths": [item["path"] for item in variant_records],
                "variant_sha256": {item["rj1_key"]: item["sha256"] for item in variant_records},
                "deck_count": len(deck_records),
                "four_bvm_fingerprint_count": len(four_fingerprints),
                "single_s0_fingerprint_count": len(single_by_state["S0"]),
                "single_s1_fingerprint_count": len(single_by_state["S1"]),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
    )
    print(f"generated {len(variant_records)} QB variants and {len(deck_records)} decks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
