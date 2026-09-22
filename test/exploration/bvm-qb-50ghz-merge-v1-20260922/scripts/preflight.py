#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
PREFLIGHT = ROOT / "PREFLIGHT.md"
EXPECTED_HEAD = "57241ff6d837b679b2cc2c2008991619fb56d429"
EXPECTED = {
    "build/josim-cli": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
    "circuits/standard/MERGE.cir": "2fdc5c24798c619eee97dee07d1dcb02b2e49e3b96bfa868f86ec978dca6f96e",
    "circuits/models/jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "circuits/standard/JTL.cir": "ac02fc931742bb857723f9fbb57ac97a179beb6a6466d5a1184e7cf937f599aa",
    "test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/circuits/bvm_tunable.cir": "1b0431c5c06616bc04e3c1c21187a74e7e1dd0805552905e0c4e609849c95c66",
    "test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/circuits/bq_tunable.cir": "140154e3375a76de07b55c218f5069b27fdbacea23308485124422ece5163eda",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    errors = []
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head != EXPECTED_HEAD:
        errors.append(f"HEAD changed after pre-registration: {head} != {EXPECTED_HEAD}")
    if not PREFLIGHT.is_file() or "This experiment is governed by docs/EXPERIMENT_CONTRACT.md." not in PREFLIGHT.read_text(encoding="utf-8"):
        errors.append("PREFLIGHT.md missing contract sentence")
    hashes = {}
    for rel, expected in EXPECTED.items():
        path = REPO / rel
        actual = digest(path) if path.is_file() else None
        hashes[rel] = actual
        if actual != expected:
            errors.append(f"source hash mismatch: {rel}: {actual} != {expected}")
    version = subprocess.check_output([str(REPO / "build/josim-cli"), "--version"], text=True).strip()
    data = {"schema": "bvm-qb-50ghz-preflight-qa-v1", "status": "PASS" if not errors else "FAIL", "parent_head": head, "expected_head": EXPECTED_HEAD, "source_hashes": hashes, "solver_version": version, "authorized_solve_counts": {"phase_a": 14, "phase_b": 3, "phase_c": 26, "phase_d_conditional": 8}, "errors": errors}
    out = ROOT / "analysis" / "PREFLIGHT_QA.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
