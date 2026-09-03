#!/usr/bin/env python3
"""Create corrected non-overwriting four-BVM attempt-03 decks.

Attempt-02 is retained as a failed path-resolution attempt.  These decks are
one directory deeper, so every repository include and the local QB include
gets exactly one additional parent component.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


EXP = Path(__file__).resolve().parents[1]
FOUR_IDS = (
    "F4_R12_T100", "F4_R12_T050", "F4_R12_T025", "F4_R12_T0125",
    "F4_R11P5_T100", "F4_R11P5_T050", "F4_R11P5_T025", "F4_R11P5_T0125",
    "F4_R11_T100", "F4_R11_T050", "F4_R11_T025", "F4_R11_T0125",
)


def main() -> int:
    records = []
    for run_id in FOUR_IDS:
        original = EXP / "runs" / run_id / "deck.cir"
        target = EXP / "runs" / run_id / "attempt-03" / "deck.cir"
        if not original.is_file():
            raise RuntimeError(f"missing original deck: {original}")
        if target.exists():
            raise RuntimeError(f"refusing to overwrite: {target}")
        text = original.read_text(encoding="utf-8")
        if text.count(".print I(BVMOUT)") != 1 or "P(BVMOUT)" in text:
            raise RuntimeError(f"unexpected BVMout probe state in {original}")
        text = text.replace(".print I(BVMOUT)", ".print P(BVMOUT) V(BVMOUT) I(BVMOUT)", 1)
        text = text.replace("../../../../../circuits/", "../../../../../../circuits/")
        text = text.replace("../../../../../BVMSim/", "../../../../../../BVMSim/")
        text = text.replace("../../inputs/", "../../../inputs/")
        include_lines = [line for line in text.splitlines() if line.startswith(".include")]
        if not all(
            line.startswith((".include ../../../../../../circuits/", ".include ../../../../../../BVMSim/", ".include ../../../inputs/"))
            for line in include_lines
        ):
            raise RuntimeError(f"include depth was not fully corrected in {target}: {include_lines}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        records.append(
            {
                "run_id": run_id,
                "attempt": "attempt-03",
                "source_deck": str(original.relative_to(EXP.parent.parent.parent)),
                "deck": str(target.relative_to(EXP.parent.parent.parent)),
                "change": "full BVMout probes plus corrected include depth",
                "raw": str((target.parent / "raw/run-01.csv").relative_to(EXP.parent.parent.parent)),
            }
        )
    manifest = {
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "reason": "attempt-02 retained failed include-depth run; attempt-03 is probe-complete",
        "records": records,
    }
    out = EXP / "analysis" / "four_probe_attempt3_manifest.json"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite: {out}")
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"created {len(records)} corrected attempt-03 decks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
