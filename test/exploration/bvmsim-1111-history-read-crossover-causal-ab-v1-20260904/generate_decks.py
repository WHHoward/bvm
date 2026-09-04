#!/usr/bin/env python3
"""Generate the two authorized 1111 history crossover decks.

The parent decks remain immutable.  This generator changes only the
70--81 ps HISTORY_READ source fragments and, for the OLD-derived deck, the
active .print section to the already-used full observability schema.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
OLD_PARENT = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/deck.cir"
NEW_PARENT = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir"
OLD_RAW = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv"
NEW_RAW = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv"

OLD_PARENT_SHA256 = "3fcdb8b0d61c91cadcacee77c3c06b3a03f8f9392a8c838e9b8574b8938b4e88"
NEW_PARENT_SHA256 = "5ee085051cfdc2cc6e45deac657230e86c64795d9cd9be100735b13974c3222e"
OLD_RAW_SHA256 = "9563ac09d75770cd9d9c2f2a93de0f418778012e64adb40fbf118ae0561d813f"
NEW_RAW_SHA256 = "b3d421822dd893d17331016b7f954784d24c90c97f58bc362676467c7650998b"

OLD_HISTORY = "70p 0 71p 100u 80p 100u 81p 0"
OLD_NO_HISTORY_WL = "70p 0 81p 0"
OLD_NO_HISTORY_SE = "70p 0 81p 0"
NEW_NO_HISTORY_WL = "70p 0 81p 0"
NEW_NO_HISTORY_SE = "70p 0 90p 0"
NEW_WITH_HISTORY_WL = OLD_HISTORY
NEW_WITH_HISTORY_SE = OLD_HISTORY + " 90p 0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def active_print_labels(text: str) -> list[str]:
    labels: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(".print"):
            labels.extend(stripped.split()[1:])
    return labels


def replace_source_fragments(text: str, *, mode: str) -> str:
    if mode not in {"old_no_history", "new_with_history"}:
        raise ValueError(mode)
    output: list[str] = []
    replacements = 0
    for line in text.splitlines():
        if line.lstrip().startswith("*"):
            output.append(line)
            continue
        match = re.match(r"^(I_(WL|SE)([1-4]))\s+.*$", line.strip())
        if not match:
            output.append(line)
            continue
        name, control, _ = match.groups()
        if mode == "old_no_history":
            old = OLD_HISTORY
            new = OLD_NO_HISTORY_WL if control == "WL" else OLD_NO_HISTORY_SE
        else:
            old = NEW_NO_HISTORY_WL if control == "WL" else NEW_NO_HISTORY_SE
            new = NEW_WITH_HISTORY_WL if control == "WL" else NEW_WITH_HISTORY_SE
        if line.strip().count(old) != 1:
            raise RuntimeError(f"{name}: expected one source fragment {old!r}")
        output.append(line.strip().replace(old, new))
        replacements += 1
    if replacements != 8:
        raise RuntimeError(f"expected 8 history source replacements, got {replacements}")
    return "\n".join(output)


def replace_print_section(old_text: str, new_text: str) -> str:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    old_tran = [i for i, line in enumerate(old_lines) if line.strip().lower().startswith(".tran ")]
    new_tran = [i for i, line in enumerate(new_lines) if line.strip().lower().startswith(".tran ")]
    old_end = [i for i, line in enumerate(old_lines) if line.strip().lower() == ".end"]
    new_end = [i for i, line in enumerate(new_lines) if line.strip().lower() == ".end"]
    if len(old_tran) != 1 or len(new_tran) != 1 or len(old_end) != 1 or len(new_end) != 1:
        raise RuntimeError("expected one .tran and one .end in each parent deck")
    if old_lines[old_tran[0]].strip() != new_lines[new_tran[0]].strip():
        raise RuntimeError("parent .tran lines differ")
    return "\n".join(old_lines[: old_tran[0] + 1] + new_lines[new_tran[0] + 1 : new_end[0]] + old_lines[old_end[0] :])


def make_deck(kind: str) -> str:
    if kind == "OLD-NO-HISTORY":
        base = OLD_PARENT.read_text(encoding="utf-8")
        text = replace_source_fragments(base, mode="old_no_history")
        text = replace_print_section(text, NEW_PARENT.read_text(encoding="utf-8"))
        header = (
            "* GENERATED HISTORY CROSSOVER DECK: condition=OLD-NO-HISTORY\n"
            "* context=OLD; history=HISTORY_READ_ABSENT\n"
            "* physics inherited from immutable OLD-WITH-HISTORY parent; full probes are observability-only\n"
        )
    elif kind == "NEW-WITH-HISTORY":
        base = NEW_PARENT.read_text(encoding="utf-8")
        text = replace_source_fragments(base, mode="new_with_history")
        header = (
            "* GENERATED HISTORY CROSSOVER DECK: condition=NEW-WITH-HISTORY\n"
            "* context=NEW; history=HISTORY_READ_PRESENT\n"
            "* physics inherited from immutable NEW-NO-HISTORY parent; exact OLD history waveform inserted\n"
        )
    else:
        raise ValueError(kind)
    return header + text.rstrip() + "\n"


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    for path, expected in ((OLD_PARENT, OLD_PARENT_SHA256), (NEW_PARENT, NEW_PARENT_SHA256), (OLD_RAW, OLD_RAW_SHA256), (NEW_RAW, NEW_RAW_SHA256)):
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"immutable parent hash mismatch: {path}")
    old_deck = make_deck("OLD-NO-HISTORY")
    new_deck = make_deck("NEW-WITH-HISTORY")
    old_path = EXP / "runs/OLD-NO-HISTORY/deck.cir"
    new_path = EXP / "runs/NEW-WITH-HISTORY/deck.cir"
    write_once(old_path, old_deck)
    write_once(new_path, new_deck)
    labels_old = active_print_labels(old_deck)
    labels_new = active_print_labels(new_deck)
    if labels_old != labels_new or len(labels_old) != len(set(labels_old)):
        raise RuntimeError("new decks do not share one unique full probe schema")
    provenance = {
        "schema": "bvmsim-1111-history-read-crossover-provenance-v1",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment": EXP.name,
        "head_before_task": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "parents": {
            "O+": {"deck": str(OLD_PARENT.relative_to(REPO)), "deck_sha256": OLD_PARENT_SHA256, "raw": str(OLD_RAW.relative_to(REPO)), "raw_sha256": OLD_RAW_SHA256},
            "N-": {"deck": str(NEW_PARENT.relative_to(REPO)), "deck_sha256": NEW_PARENT_SHA256, "raw": str(NEW_RAW.relative_to(REPO)), "raw_sha256": NEW_RAW_SHA256},
        },
        "new_decks": {
            "O-": {"path": str(old_path.relative_to(REPO)), "sha256": sha256(old_path)},
            "N+": {"path": str(new_path.relative_to(REPO)), "sha256": sha256(new_path)},
        },
        "history_waveform": {
            "old_exact_fragment": OLD_HISTORY,
            "new_wl_fragment": NEW_WITH_HISTORY_WL,
            "new_se_fragment": NEW_WITH_HISTORY_SE,
            "amplitude_uA": {"WL": 100, "SE": 100, "BL": 0},
            "window_ps": [70, 81],
        },
        "probe_schema": {"count": len(labels_old), "labels": labels_old},
        "simulation_invoked": False,
        "raw_policy": "existing parent raw immutable; new raw paths must be absent before run",
        "canonical_bvm_used": False,
    }
    write_once(EXP / "provenance.json", json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")
    print(f"generated {old_path}")
    print(f"generated {new_path}")
    print(f"full_probe_count={len(labels_old)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
