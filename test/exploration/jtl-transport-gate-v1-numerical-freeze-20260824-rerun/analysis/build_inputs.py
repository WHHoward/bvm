#!/usr/bin/env python3
"""Build the hash-bound, independent JTL numerical replay inputs."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parents[2]
DT_PS = (0.025, 0.0125, 0.00625)

PARENTS = {
    "r11": REPO / "test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/inputs/positive-control.cir",
    "pulse5-original": REPO / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/original/main.cir",
    "pulse5-reverse": REPO / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/reverse/main.cir",
}
JTL = REPO / "circuits/standard/JTL.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rewrite(parent: Path, dt_ps: float) -> str:
    lines = []
    for line in parent.read_text(encoding="utf-8").splitlines():
        if line.startswith(".include "):
            if "jjmit.cir" in line:
                line = ".include jjmit.cir"
            elif "JTL.cir" in line:
                line = ".include JTL.cir"
        if line.startswith(".tran "):
            stop = line.split()[-1]
            line = f".tran {dt_ps:g}p {stop}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def main() -> None:
    manifest = {
        "parent_head": "8bb86f61c3243655467d61f00680977349b41cf3",
        "dt_ps": list(DT_PS),
        "parents": {},
        "fixtures": [],
        "shared": {
            "jtl_path": str(JTL.relative_to(REPO)),
            "jtl_sha256": sha256(JTL),
            "jjmit_path": str(JJMIT.relative_to(REPO)),
            "jjmit_sha256": sha256(JJMIT),
        },
    }
    for fixture, parent in PARENTS.items():
        manifest["parents"][fixture] = {
            "path": str(parent.relative_to(REPO)),
            "sha256": sha256(parent),
        }
        for dt_ps in DT_PS:
            tag = str(dt_ps).replace(".", "p")
            out = EXP / "inputs" / fixture / tag
            out.mkdir(parents=True, exist_ok=False)
            (out / "main.cir").write_text(rewrite(parent, dt_ps), encoding="utf-8")
            shutil.copy2(JTL, out / "JTL.cir")
            shutil.copy2(JJMIT, out / "jjmit.cir")
            manifest["fixtures"].append({
                "fixture": fixture,
                "dt_ps": dt_ps,
                "deck": str((out / "main.cir").relative_to(EXP)),
                "deck_sha256": sha256(out / "main.cir"),
                "jtl_sha256": sha256(out / "JTL.cir"),
                "jjmit_sha256": sha256(out / "jjmit.cir"),
            })
    (EXP / "inputs" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
