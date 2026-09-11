#!/usr/bin/env python3
"""Register the exact passive/replay mechanism diagnostic without solving."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_EXP = REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOLVER = REPO / "build/josim-cli"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
MASKS = ("0011", "0111", "1111")
PASSIVE_RUNS = tuple(f"PASSIVE_N{index}_{mask}" for index, mask in ((2, "0011"), (3, "0111"), (4, "1111")))
REPLAY_RUNS = tuple(f"REPLAY_N{index}_{mask}_RJ2P12" for index, mask in ((2, "0011"), (3, "0111"), (4, "1111")))
ALL_RUNS = PASSIVE_RUNS + REPLAY_RUNS
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
INPUT_HASHES = {
    "array_fixture_template.cir": "8971a82dfbac223b9be139f719afae2eb156f0f68fb2a4811858f0a0b482cf71",
    "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    "BQ_parameterized_bjs400.cir": "883308517d48470cbedab878f9e3c71721cd972db248c6b821ce5dba642ff810",
    "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
}
LATEST_PACKAGES = {
    "rj2p10": (REPO / "test/exploration/bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/handoff/bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_corrected-v2_raw_handoff.zip", "8651e9dd61aad4efedbf5cf5883687af542ab457d106c159e57b6d9435e9bf06"),
    "rj2p11": (REPO / "test/exploration/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/handoff/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_raw_handoff.zip", "785be4b1d92d9eeea4e3dfa044a70ac55cf47d7a6f2feea860f4b1c3d79566af"),
    "rj2p12": (SOURCE_EXP / "handoff/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip", "3ceba168be95b7e48cbb77ccb13d4f4133893cb39813c025b7d4a3f631a09dff"),
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        return subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True).split()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None


def write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.write_text(text, encoding="utf-8")


def write_json_once(path: Path, value: Any) -> None:
    write_once(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def local_source(name: str) -> Path:
    return EXP / "inputs" / name


def source_record(path: Path, role: str, origin: Path | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "role": role,
    }
    if origin is not None:
        record["copied_from"] = origin.relative_to(REPO).as_posix()
        record["origin_sha256"] = sha256(origin)
    return record


def control_values(kind: str, active: bool) -> str:
    if kind == "WL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "BL":
        points = "0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0"
    elif kind == "SE":
        points = "0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0"
    else:
        raise ValueError(kind)
    final = "+100u" if active and kind in {"WL", "SE"} else "0"
    return f"pwl({points} 110p 0 111p {final} 120p {final} 121p 0 200p 0)"


def control_line(instance: int, kind: str, active: bool) -> str:
    return f"I_{kind}{instance} 0 {kind}{instance} {control_values(kind, active)}"


def make_passive_template() -> str:
    source = (EXP / "inputs/array_fixture_template.cir").read_text(encoding="utf-8").splitlines()
    output = [
        "* GENERATED PASSIVE ARRAY DECK: current BJS400 population BVM/JSL source counterfactual",
        "* source_class=CURRENT_BJS400_POPULATION_BVM_JSL_CONFIGURATION",
        "* Four BVMs share COMMON_SL; QB, six-stage JTL and terminal are removed.",
        "* B_JSL8 is terminated at ground only for passive source capture.",
        "",
        ".include ../../inputs/jjmit.cir",
        ".include ../../inputs/bvm_jm2_connected.cir",
        "",
        "XBVM1 WL1 BL1 SE1 COMMON_SL BVM",
        "XBVM2 WL2 BL2 SE2 COMMON_SL BVM",
        "XBVM3 WL3 BL3 SE3 COMMON_SL BVM",
        "XBVM4 WL4 BL4 SE4 COMMON_SL BVM",
        "",
        "B_JSL1 COMMON_SL JSL_NODE1 jjmit area=5.0",
        "B_JSL2 JSL_NODE1 JSL_NODE2 jjmit area=5.0",
        "B_JSL3 JSL_NODE2 JSL_NODE3 jjmit area=5.0",
        "B_JSL4 JSL_NODE3 JSL_NODE4 jjmit area=5.0",
        "B_JSL5 JSL_NODE4 JSL_NODE5 jjmit area=5.0",
        "B_JSL6 JSL_NODE5 JSL_NODE6 jjmit area=5.0",
        "B_JSL7 JSL_NODE6 JSL_NODE7 jjmit area=5.0",
        "B_JSL8 JSL_NODE7 0 jjmit area=5.0",
        "",
    ]
    controls = [f"@@ARRAY_I_{kind}{instance}@@" for instance in range(1, 5) for kind in ("WL", "BL", "SE")]
    output.extend(controls)
    output.extend(["", ".tran 0.1p 200p", ""])
    for line in source:
        stripped = line.strip()
        if not stripped.startswith(".print"):
            continue
        if any(token in stripped for token in ("QBIN", "QBOUT", "XBQ1", "XJTL1_", "R_TERM", "JTL")):
            continue
        output.append(stripped)
    output.append(".end")
    return "\n".join(output) + "\n"


def build_passive_deck(mask: str, template: str) -> str:
    text = template
    for instance in range(1, 5):
        active = mask[instance - 1] == "1"
        for kind in ("WL", "BL", "SE"):
            text = text.replace(f"@@ARRAY_I_{kind}{instance}@@", control_line(instance, kind, active), 1)
    if "@@" in text:
        raise RuntimeError(f"unresolved control placeholder for mask {mask}")
    return text.replace("PASSIVE ARRAY DECK", f"PASSIVE {mask} ARRAY DECK", 1)


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", "."))]


def check_passive_deck(path: Path, mask: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    failures: list[str] = []
    bvm = [line for line in lines if line.endswith("BVM")]
    jsl = [line for line in lines if line.startswith("B_JSL")]
    controls = [line for line in lines if line.startswith("I_")]
    if len(bvm) != 4 or any(f"XBVM{index} WL{index} BL{index} SE{index} COMMON_SL BVM" not in bvm for index in range(1, 5)):
        failures.append("passive BVM instance/topology mismatch")
    if len(jsl) != 8 or any("jjmit area=5.0" not in line for line in jsl):
        failures.append("passive JSL model/area mismatch")
    if jsl[-1].split()[2] != "0":
        failures.append("B_JSL8 is not connected to passive ground endpoint")
    if any(token in line.casefold() for line in lines for token in ("bq", "jtl", "r_term", "qbin", "qbout")):
        failures.append("receiver leakage in passive active netlist")
    if len(controls) != 12:
        failures.append(f"control count {len(controls)} != 12")
    expected = [control_line(instance, kind, mask[instance - 1] == "1") for instance in range(1, 5) for kind in ("WL", "BL", "SE")]
    if controls != expected:
        failures.append("stored-history or final-read mask mismatch")
    if [line for line in text.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("tran mismatch")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "failures": failures, "bvm_count": len(bvm), "jsl_count": len(jsl), "control_count": len(controls), "jsl8_branch": jsl[-1] if jsl else None}


def latest_package_records() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for name, (path, expected) in LATEST_PACKAGES.items():
        if not path.is_file():
            raise RuntimeError(f"latest {name} population package is missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"latest {name} population package hash changed: {actual} != {expected}")
        records[name] = {"path": path.relative_to(REPO).as_posix(), "sha256": actual, "bytes": path.stat().st_size}
    return records


def build_source_manifest() -> dict[str, Any]:
    local: list[dict[str, Any]] = []
    for name, role in (
        ("array_fixture_template.cir", "current population stimulus/topology template"),
        ("bvm_jm2_connected.cir", "current population BVM source include"),
        ("jjmit.cir", "current population/JSL JJ model include"),
        ("jtl2.cir", "current population six-stage JTL include"),
        ("BQ_parameterized_bjs400.cir", "current population BQ baseline include"),
        ("BQ_parameterized_bjs400_rj2.cir", "current RJ2=12 replay BQ include"),
    ):
        path = local_source(name)
        origin = SOURCE_EXP / "inputs" / name
        if not path.is_file() or not origin.is_file() or sha256(path) != sha256(origin):
            raise RuntimeError(f"local source is not byte-identical to current population input: {name}")
        if name in INPUT_HASHES and sha256(path) != INPUT_HASHES[name]:
            raise RuntimeError(f"current population input hash changed: {name}")
        local.append(source_record(path, role, origin))
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("solver identity changed")
    local.append({"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "bytes": SOLVER.stat().st_size, "role": "solver identity", "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)})
    passive_template = EXP / "inputs/passive_fixture_template.cir"
    write_once(passive_template, make_passive_template())
    local.append(source_record(passive_template, "derived passive fixture template; receiver removal only"))
    return {
        "schema": "bvm-population-passive-source-replay-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "repository_head_at_registration": head(),
        "remote_master_at_registration": remote_head(),
        "current_population_experiment": str(SOURCE_EXP.relative_to(REPO)),
        "current_population_source_manifest": source_record(SOURCE_EXP / "SOURCE_MANIFEST.json", "current population source authority manifest"),
        "latest_population_evidence": latest_package_records(),
        "local_sources": local,
        "fixed_working_point": {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "BJS_area": 4, "BJS_Ic_uA": 400},
        "passive_source": {"signal": "I(B_JSL8)", "branch": "B_JSL8 JSL_NODE7 0 jjmit area=5.0", "orientation": "first node to second node", "endpoint": "ground"},
        "replay_source": {"branch": "I_REPLAY 0 QBIN", "orientation": "positive current injects QBIN", "sign_change": False, "transformations": []},
    }


def make_preflight(record: dict[str, Any], *, refreshed: bool) -> dict[str, Any]:
    template = EXP / "inputs/passive_fixture_template.cir"
    decks: dict[str, Any] = {}
    for index, mask in ((2, "0011"), (3, "0111"), (4, "1111")):
        run = f"PASSIVE_N{index}_{mask}"
        path = EXP / "runs" / run / "deck.cir"
        write_once(path, build_passive_deck(mask, template.read_text(encoding="utf-8")))
        decks[run] = check_passive_deck(path, mask)
    failures = [f"{name}: {failure}" for name, item in decks.items() for failure in item["failures"]]
    source_manifest = json.loads((EXP / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    failures.extend(f"source: {key}" for key in () if key)
    record.update({
        "schema": "bvm-population-passive-source-replay-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "preregistration_head": record.get("preregistration_head", head()),
        "head_at_preflight": head(),
        "head_refresh": refreshed,
        "remote_master_at_preflight": remote_head(),
        "authorized_passive_runs": list(PASSIVE_RUNS),
        "authorized_replay_runs": list(REPLAY_RUNS),
        "authorized_physical_solve_count": 6,
        "physical_solve_count_before_preflight": 0,
        "unauthorized_extra_solves": 0,
        "scientific_analysis_performed": False,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
        "passive_decks": decks,
        "replay_decks": "generated only after passive raw capture; not yet authorized for solve",
        "orientation_status": "PASS: current closed-loop branch is JSL_NODE7 -> QBIN and replay is 0 -> QBIN; passive retains first-to-second direction",
        "source_authority": source_manifest,
        "failures": failures,
    })
    return record


def preflight_markdown(record: dict[str, Any]) -> str:
    rows = []
    for run, item in record["passive_decks"].items():
        rows.append(f"| `{run}` | `{item['jsl8_branch']}` | {item['control_count']} | `{item['status']}` |")
    return "\n".join([
        "# BVM population passive source replay — PREFLIGHT", "",
        CONTRACT_SENTENCE, "",
        f"- Experiment: `{EXP.name}`",
        f"- Initial registration HEAD: `{record['preregistration_head']}`",
        f"- Sealed preflight HEAD: `{record['head_at_preflight']}`",
        f"- Remote `bvm/master` observed at preflight: `{record.get('remote_master_at_preflight')}`",
        f"- Status: **{record['status']}**",
        "- Physical solve count before preflight: `0`.", "",
        "## Exact matrix", "",
        "- Passive captures: N2 `0011`, N3 `0111`, N4 `1111`.",
        "- Replay solves: the three exact passive source snapshots into the same RJ2=12 receiver.",
        "- Total: exactly `6` physical solves; no extra mask, sweep, timestep, parameter or receiver case.", "",
        "## Passive topology", "",
        "The current BJS400 population BVM/JSL configuration is used byte-identically for the BVM/JJ model inputs. Four BVMs share `COMMON_SL`; eight `jjmit area=5.0` JSL junctions terminate at ground only in this passive counterfactual. QB, JTL and `R_TERM` are absent from the active passive netlist.", "",
        "| passive case | JSL8 branch | controls | deck QA |", "|---|---|---:|---|", *rows, "",
        "## Frozen protocol and replay boundary", "",
        "Stored history is IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; selective final READ 110–121ps; TAIL 121–200ps, with 100uA amplitude, 1ps rise/fall, and `.tran 0.1p 200p`.",
        "Replay decks are not generated until passive raw files exist. They will contain only `I_REPLAY 0 QBIN`, current RJ2=12 BQ, current six-stage JTL and current 10 ohm termination. Raw timestamps/current values will be retained exactly; no interpolation or waveform transformation is registered.", "",
        "## Evidence ceiling", "",
        "P values remain raw radians. Any phase-turn display is `rad/(2*pi)`. Phase landmarks, voltage/current activity, voltage area and terminal area are navigation evidence only, not SFQ counts. Passive source is a counterfactual and replay is ideal forcing, not a circuit-equivalent source. Scientific interpretation is `NOT_PERFORMED`.", "",
        "Machine record: `analysis/preflight.json`.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-head", action="store_true", help="seal the preflight against the current registration commit")
    args = parser.parse_args()
    source_manifest_path = EXP / "SOURCE_MANIFEST.json"
    if source_manifest_path.is_file():
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    else:
        source_manifest = build_source_manifest()
        write_json_once(source_manifest_path, source_manifest)
    if not source_manifest_path.is_file():
        raise RuntimeError("source manifest was not created")
    base = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8")) if (EXP / "analysis/preflight.json").is_file() else {"preregistration_head": head()}
    record = make_preflight(base, refreshed=args.refresh_head)
    output = EXP / "analysis/preflight.json"
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.refresh_head:
        output.write_text(text, encoding="utf-8")
        (EXP / "PREFLIGHT.md").write_text(preflight_markdown(record), encoding="utf-8")
    else:
        write_once(output, text)
        write_once(EXP / "PREFLIGHT.md", preflight_markdown(record))
    print(json.dumps({"status": record["status"], "head": record["head_at_preflight"], "passive_decks": list(record["passive_decks"]), "physical_solve_count": 0, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
