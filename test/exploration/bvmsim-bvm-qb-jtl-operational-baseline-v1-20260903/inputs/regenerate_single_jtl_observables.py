#!/usr/bin/env python3
"""Create probe-complete attempt-02 decks for the two single-BVM JTL runs.

The attempt-01 raw files are retained.  This repair adds only the six-stage
JTL P/V print probes that were omitted from the first generated decks.
"""

from __future__ import annotations

from pathlib import Path

from generate_baseline_decks import EXP, make_single, sha256, write_new


def main() -> int:
    for run_id in ("S0-J", "S1-J"):
        attempt_dir = EXP / "runs" / "single" / run_id / "attempt-02"
        deck = attempt_dir / "deck.cir"
        content = "* ATTEMPT-02: completed six-stage JTL P/V observability; physics unchanged.\n" + make_single(run_id, attempt_dir)
        write_new(deck, content)
        print(f"{run_id}: {deck} sha256={sha256(deck)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
