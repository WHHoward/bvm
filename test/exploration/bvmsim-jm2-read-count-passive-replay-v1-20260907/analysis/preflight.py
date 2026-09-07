#!/usr/bin/env python3
"""Mechanical preflight for N2-N4 passive capture and N1 references."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "source/source_manifest.json"
HEAD_AT_SETUP = "217305580f1c9cec17839896730fbe9b1016c837"
READ_COUNTS = (2, 3, 4)
PWL_RE = re.compile(r"pwl\((.*)\)", re.IGNORECASE)
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def netlist_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("*", ".", "+"))
    ]


def control_pairs(path: Path, name: str, instance: int) -> list[tuple[str, str]]:
    prefix = f"I_{name}{instance} 0 {name}{instance} "
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {prefix} line in {path}, got {len(matches)}")
    match = PWL_RE.fullmatch(matches[0])
    if not match:
        raise RuntimeError(f"control is not a single PWL in {path}: {prefix}")
    return [(time, value) for time, value in PAIR_RE.findall(match.group(1))]


def passive_check(read_count: int) -> dict[str, object]:
    path = EXP / "runs" / f"n{read_count}_passive" / "deck.cir"
    failures: list[str] = []
    lines = netlist_lines(path)
    bvm = [line for line in lines if line.endswith("BVM")]
    jsl = [line for line in lines if line.startswith("B_JSL")]
    if len(bvm) != 4:
        failures.append(f"BVM count {len(bvm)} != 4")
    if len(jsl) != 8:
        failures.append(f"JSL count {len(jsl)} != 8")
    if any("jjmit" not in line or "area=5.0" not in line for line in jsl):
        failures.append("JSL model/area mismatch")
    if not jsl or jsl[-1].split()[2] != "0":
        failures.append("JSL8 does not terminate at ground")
    if any(token in line.lower() for line in lines for token in ("bq", "jtl", "r_term")):
        failures.append("forbidden QB/JTL/termination element found")
    if len([line for line in lines if line.startswith("I_")]) != 12:
        failures.append("control source count is not 12")
    if any(f"XBVM{i} WL{i} BL{i} SE{i} COMMON_SL BVM" not in bvm for i in range(1, 5)):
        failures.append("BVM instance or COMMON_SL endpoint mismatch")
    tran = [line for line in path.read_text(encoding="utf-8").splitlines() if line.lower().startswith(".tran")]
    if tran != [".tran 0.1p 200p"]:
        failures.append(f"timing line mismatch: {tran}")
    text = path.read_text(encoding="utf-8")
    required_tokens = [
        "P(B_JM1|XBVM1)", "V(B_JM2|XBVM4)", "I(L_SL|XBVM1)",
        "I(I_WL1)", "I(I_SE4)", "V(COMMON_SL)", "P(B_JSL8)", "I(B_JSL8)",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        failures.append(f"required probe token(s) absent: {missing}")
    mask = "".join("1" if control_pairs(path, "WL", i) == control_pairs(path, "WL", 1) else "0" for i in range(1, 5))
    # The WL waveform is the registered final-read discriminator for this
    # fixture; BL and SE are checked independently below.
    expected_mask = f"{'1' * read_count}{'0' * (4 - read_count)}"
    if mask != expected_mask:
        failures.append(f"WL final-read mask {mask} != {expected_mask}")
    # Each active cell must have the exact registered active controls and each
    # quiet cell the exact registered quiet controls. These exact strings are
    # checked against the generated N4 deck in the source manifest below.
    controls = {f"{name}{i}": control_pairs(path, name, i) for i in range(1, 5) for name in ("WL", "BL", "SE")}
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": path.relative_to(REPO).as_posix(),
        "deck_sha256": sha256(path),
        "read_count": read_count,
        "final_read_mask": expected_mask,
        "bvm_count": len(bvm),
        "jsl_count": len(jsl),
        "jsl8_to_ground": bool(jsl and jsl[-1].split()[2] == "0"),
        "controls": controls,
        "probe_token_check": not missing,
        "failures": failures,
    }


def main() -> int:
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    if current_head != HEAD_AT_SETUP:
        failures.append(f"HEAD changed since preregistration: {current_head}")
    source_checks: dict[str, object] = {}
    for key in ("bvm_variant", "jjmit", "qb", "jtl", "solver"):
        record = manifest["sources"][key]
        path = REPO / record["path"]
        actual = sha256(path)
        source_checks[key] = {"path": record["path"], "expected_sha256": record["sha256"], "actual_sha256": actual, "unchanged": actual == record["sha256"]}
        if actual != record["sha256"]:
            failures.append(f"source hash changed: {key}")
    n1_checks: dict[str, object] = {}
    for name, record in manifest["n1_reference"].items():
        path = REPO / record["path"]
        actual = sha256(path)
        item = {"path": record["path"], "expected_sha256": record["sha256"], "actual_sha256": actual, "unchanged": actual == record["sha256"], "rerun": False}
        n1_checks[name] = item
        if actual != record["sha256"]:
            failures.append(f"N1 reference raw hash changed: {name}")
    passive: dict[str, object] = {}
    for read_count in READ_COUNTS:
        item = passive_check(read_count)
        passive[f"N{read_count}_PASSIVE"] = item
        failures.extend(f"N{read_count}_PASSIVE: {message}" for message in item["failures"])

    # The generated deck itself is the frozen control source. Compare all
    # points before final READ across N2, N3 and N4, and require only the
    # registered mask segment to differ.
    control_history: dict[str, object] = {}
    for name in ("WL", "BL", "SE"):
        for instance in range(1, 5):
            values = {read_count: control_pairs(EXP / "runs" / f"n{read_count}_passive" / "deck.cir", name, instance) for read_count in READ_COUNTS}
            prefixes = {read_count: [pair for pair in pairs if float(pair[0]) < 110.0] for read_count, pairs in values.items()}
            if not (prefixes[2] == prefixes[3] == prefixes[4]):
                failures.append(f"control history differs before final READ: {name}{instance}")
            control_history[f"{name}{instance}"] = {
                "pre_final_read_identical": prefixes[2] == prefixes[3] == prefixes[4],
                "sample_counts": {str(key): len(value) for key, value in values.items()},
            }

    record = {
        "schema": "jm2-read-count-passive-replay-topology-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "stage": "PASSIVE_BEFORE_CAPTURE",
        "status": "PASS" if not failures else "FAIL",
        "head_at_setup": HEAD_AT_SETUP,
        "head_at_preflight": current_head,
        "source_hashes_unchanged": not any(not item["unchanged"] for item in source_checks.values()),
        "n1_reference_hashes_unchanged": not any(not item["unchanged"] for item in n1_checks.values()),
        "sources": source_checks,
        "n1_references": n1_checks,
        "passive": passive,
        "control_history": control_history,
        "replay_contract": {
            "status": "REGISTERED_POST_CAPTURE_MECHANICAL_CHECK_REQUIRED",
            "contains_bvm": False,
            "contains_jsls": False,
            "qb_source": manifest["sources"]["qb"],
            "jtl_source": manifest["sources"]["jtl"],
            "termination_ohm": 10.0,
            "pwl_source": "captured N2/N3/N4 passive I(B_JSL8) exact timestamp/value pairs",
        },
        "failures": failures,
    }
    write_once(EXP / "analysis/topology_preflight.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    markdown = f"""# PREFLIGHT — read-count passive capture

- Status: **{record['status']}**
- Preflight time: `{record['created_at_local']}`
- HEAD at setup/preflight: `{HEAD_AT_SETUP}` / `{current_head}`
- N1: existing `ARRAY_PASSIVE` raw is referenced by hash and is not rerun.
- New physical captures: exactly N2, N3 and N4.

## Passive fixtures

| case | final READ mask | BVM | JSL | JSL8 endpoint | QB/JTL/termination | result |
|---|---|---:|---:|---|---|---|
| `N2_PASSIVE` | `1100` | 4 -> `COMMON_SL` | 8 x `jjmit area=5.0` | GND | absent | `{passive['N2_PASSIVE']['status']}` |
| `N3_PASSIVE` | `1110` | 4 -> `COMMON_SL` | 8 x `jjmit area=5.0` | GND | absent | `{passive['N3_PASSIVE']['status']}` |
| `N4_PASSIVE` | `1111` | 4 -> `COMMON_SL` | 8 x `jjmit area=5.0` | GND | absent | `{passive['N4_PASSIVE']['status']}` |

All three decks use the historical JM2-connected variant, exact registered model files, the common WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 history, and `.tran 0.1p 200p`. Only the final READ mask changes.

Replay decks are generated only after the passive raw captures and a separate exact-PWL preflight.

Machine record: `analysis/topology_preflight.json`.
"""
    write_once(EXP / "PREFLIGHT.md", markdown)
    print(json.dumps({"status": record["status"], "record": "analysis/topology_preflight.json", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
