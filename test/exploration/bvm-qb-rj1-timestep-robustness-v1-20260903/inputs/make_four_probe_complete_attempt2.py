#!/usr/bin/env python3
"""Create non-overwriting four-BVM attempt-02 decks with full BVMout probes."""

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
        target = EXP / "runs" / run_id / "attempt-02" / "deck.cir"
        if not original.is_file():
            raise RuntimeError(f"missing original deck: {original}")
        if target.exists():
            raise RuntimeError(f"refusing to overwrite: {target}")
        text = original.read_text(encoding="utf-8")
        old = ".print I(BVMOUT)"
        new = ".print P(BVMOUT) V(BVMOUT) I(BVMOUT)"
        if text.count(old) != 1 or "P(BVMOUT)" in text:
            raise RuntimeError(f"unexpected BVMout probe state in {original}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        records.append(
            {
                "run_id": run_id,
                "attempt": "attempt-02",
                "source_deck": str(original.relative_to(EXP.parent.parent.parent)),
                "deck": str(target.relative_to(EXP.parent.parent.parent)),
                "change": "I(BVMOUT) -> P(BVMOUT) V(BVMOUT) I(BVMOUT)",
                "raw": str((target.parent / "raw/run-01.csv").relative_to(EXP.parent.parent.parent)),
            }
        )
    manifest = {
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "reason": "initial four-BVM attempt lacked P/V(BVMOUT); raw was not overwritten",
        "records": records,
    }
    out = EXP / "analysis" / "four_probe_attempt2_manifest.json"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite: {out}")
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"created {len(records)} attempt-02 decks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
