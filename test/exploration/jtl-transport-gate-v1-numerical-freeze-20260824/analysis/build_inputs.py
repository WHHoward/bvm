#!/usr/bin/env python3
"""Create independent timestep copies from the accepted JTL fixtures."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parents[2]
DT_PS = (0.025, 0.0125, 0.00625)

R11_PARENT = REPO / "test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/inputs/positive-control.cir"
REPLAY_PARENTS = {
    "pulse5-original": REPO / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/original/main.cir",
    "pulse5-reverse": REPO / "test/exploration/jtl-transport-gate-polarity-replay-20260824/inputs/reverse/main.cir",
}
JTL = REPO / "circuits/standard/JTL.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rewrite(parent: Path, dt_ps: float) -> str:
    text = parent.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
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
    }
    for name, parent in [("R11", R11_PARENT), *REPLAY_PARENTS.items()]:
        manifest["parents"][name] = {
            "path": str(parent.relative_to(REPO)),
            "sha256": sha256(parent),
        }
    for fixture, parent in [("r11", R11_PARENT),
                            ("pulse5-original", REPLAY_PARENTS["pulse5-original"]),
                            ("pulse5-reverse", REPLAY_PARENTS["pulse5-reverse"])]:
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
                "jtl_sha256": sha256(out / "JTL.cir"),
                "jjmit_sha256": sha256(out / "jjmit.cir"),
            })
    (EXP / "inputs" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
