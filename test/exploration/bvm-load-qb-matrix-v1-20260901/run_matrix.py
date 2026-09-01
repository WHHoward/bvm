#!/usr/bin/env python3
"""Run one immutable fixture family in the BVM/JSL/QB matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOLVER = REPO / "build/josim-cli"
WIDTHS = (9, 13)
LOADS = ("12x320", "8x500")
ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_one(kind: str, width_ps: int, load: str, role: str) -> dict[str, Any]:
    deck = ROOT / "inputs" / kind / f"{width_ps}ps" / load / f"{role}.cir"
    raw = ROOT / "raw" / kind / f"{width_ps}ps" / load / role / "run-01.csv"
    stdout = ROOT / "logs" / kind / f"{width_ps}ps" / load / f"{role}.stdout.txt"
    stderr = ROOT / "logs" / kind / f"{width_ps}ps" / load / f"{role}.stderr.txt"
    output_hash = raw.with_suffix(raw.suffix + ".sha256")
    for path in (raw, stdout, stderr, output_hash):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    if not deck.exists():
        raise RuntimeError(f"missing deck: {deck}")
    raw.parent.mkdir(parents=True, exist_ok=True)
    stdout.parent.mkdir(parents=True, exist_ok=True)
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    stdout.write_text(result.stdout, encoding="utf-8")
    stderr.write_text(result.stderr, encoding="utf-8")
    finished = datetime.now().astimezone().isoformat(timespec="seconds")
    record: dict[str, Any] = {
        "kind": kind,
        "width_ps": width_ps,
        "load": load,
        "role": role,
        "deck": deck.relative_to(ROOT).as_posix(),
        "raw": raw.relative_to(ROOT).as_posix(),
        "command": command,
        "started_at": started,
        "finished_at": finished,
        "returncode": result.returncode,
        "stdout": stdout.relative_to(ROOT).as_posix(),
        "stderr": stderr.relative_to(ROOT).as_posix(),
    }
    if raw.exists():
        digest = sha256(raw)
        output_hash.write_text(f"{digest}  {raw.name}\n", encoding="utf-8")
        record["raw_sha256"] = digest
        record["raw_bytes"] = raw.stat().st_size
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("source", "physical", "replay"), required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    tasks = [(args.kind, width, load, role) for width in WIDTHS for load in LOADS for role in ROLES]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(run_one, *task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({
                "kind": args.kind,
                "width_ps": result["width_ps"],
                "load": result["load"],
                "role": result["role"],
                "returncode": result["returncode"],
            }, ensure_ascii=False), flush=True)
    results.sort(key=lambda item: (item["width_ps"], item["load"], item["role"]))
    execution = ROOT / "logs" / f"execution-{args.kind}.json"
    execution.parent.mkdir(parents=True, exist_ok=True)
    execution.write_text(json.dumps({
        "kind": args.kind,
        "started_at": results[0]["started_at"] if results else None,
        "finished_at": results[-1]["finished_at"] if results else None,
        "solver": str(SOLVER.relative_to(REPO)),
        "results": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [item for item in results if item["returncode"] != 0]
    print(json.dumps({
        "kind": args.kind,
        "completed": len(results),
        "failures": len(failures),
        "execution": execution.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
