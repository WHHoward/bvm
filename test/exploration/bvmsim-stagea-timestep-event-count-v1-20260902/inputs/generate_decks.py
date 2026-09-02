#!/usr/bin/env python3
"""Generate timestep members from the frozen Stage-A fixture template.

The template is an existing, hash-bound Stage-A migrated deck.  This script
does not edit the template or any historical BVMSim file.  It asserts that the
requested member differs from the template only at the single transient
control line.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/migrated/m0_bvmsim_qb.cir"
TEMPLATE_SHA256 = "e0eeb3435336ca86253241f6bdabb86b8c39baf642cb16c7b0a6409035a0518e"
TRAN_RE = re.compile(r"(?m)^\.tran 0\.1p 200p 45p$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(tran: str) -> str:
    actual = sha256(TEMPLATE)
    if actual != TEMPLATE_SHA256:
        raise SystemExit(f"fixture template changed: {actual} != {TEMPLATE_SHA256}")
    text = TEMPLATE.read_text(encoding="utf-8")
    replaced, count = TRAN_RE.subn(tran, text)
    if count != 1:
        raise SystemExit(f"expected exactly one template .tran line, found {count}")
    if not replaced.endswith("\n"):
        raise SystemExit("generated deck must end with newline")
    return replaced


def changed_lines(template: str, generated: str) -> list[tuple[int, str, str]]:
    before = template.splitlines()
    after = generated.splitlines()
    if len(before) != len(after):
        raise SystemExit("generated deck changed line count")
    return [
        (index + 1, old, new)
        for index, (old, new) in enumerate(zip(before, after))
        if old != new
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, choices=("T100", "T050", "T025", "T0125", "T100_FULL"))
    parser.add_argument("--tran", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    generated = derive(args.tran)
    template = TEMPLATE.read_text(encoding="utf-8")
    changes = changed_lines(template, generated)
    if len(changes) == 0:
        if args.tran != ".tran 0.1p 200p 45p":
            raise SystemExit(f"unchanged fixture has unexpected requested .tran: {args.tran}")
    elif len(changes) != 1 or changes[0][1] != ".tran 0.1p 200p 45p" or changes[0][2] != args.tran:
        raise SystemExit(f"fixture diff is not single .tran change: {changes}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generated, encoding="utf-8")
    print(f"{args.run_id}: template_sha256={TEMPLATE_SHA256}")
    print(f"{args.run_id}: deck={args.output} sha256={sha256(args.output)}")
    if changes:
        print(f"{args.run_id}: changed_line={changes[0][0]} {changes[0][1]} -> {changes[0][2]}")
    else:
        print(f"{args.run_id}: changed_line=none (template already has {args.tran})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
