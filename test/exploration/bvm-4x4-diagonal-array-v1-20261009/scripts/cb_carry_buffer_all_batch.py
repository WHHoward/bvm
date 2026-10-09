#!/usr/bin/env python3
"""Preflight and execute exactly A027-A029 for the six-stage CB-only chain."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
RUNS = SERIES / "runs"
TASK = SERIES / "analysis" / "cb-carry-buffer-all-20261009"
BATCH_ID = "BVM4X4_CB_CARRY_BUFFER_ALL_20261009"
BASE_HEAD = "fb5139b8b0f6a084b75fcf6343faaddbfcbee104"
BASE_RUNS = {
    "A025_CARRY_CB_D1_ALL_CLOCK": "c9b3f6b2c3f707c599794658950de7bbbd3bfd6b51455d637ac3e0eee14369c9",
    "A026_CARRY_CB_D1_PAPER_CLOCK": "f9b198ecad7a7eef7181d6f99c1d8febc28db5b47e11956f91ca3beb6b29f7aa",
}
STATIC_SUBCKTS = ("THmitll_MERGE", "THmitll_DFF", "D0_JTL", "T1", "BVM", "BQ", "sJTL", "CB")
THEORY_BY_RUN = {
    "A027_FULL_CB_CHAIN_ALL_CLOCK": {"diagonal_population": [1, 2, 3, 4, 3, 2, 1],
                                      "stage_inputs": [1, 2, 4, 6, 6, 5, 3],
                                      "carry": [0, 1, 2, 3, 3, 2, 1], "product": 225,
                                      "bits": [1, 0, 0, 0, 0, 1, 1, 1]},
    "A028_FULL_CB_CHAIN_PAPER_CLOCK": {"diagonal_population": [1, 1, 1, 3, 1, 1, 1],
                                       "stage_inputs": [1, 1, 1, 3, 2, 2, 2],
                                       "carry": [0, 0, 0, 1, 1, 1, 1], "product": 143,
                                       "bits": [1, 1, 1, 1, 0, 0, 0, 1]},
    "A029_FULL_CB_CHAIN_3X3_CLOCK": {"diagonal_population": [1, 2, 1, 0, 0, 0, 0],
                                     "stage_inputs": [1, 2, 2, 1, 0, 0, 0],
                                     "carry": [0, 1, 1, 0, 0, 0, 0], "product": 9,
                                     "bits": [1, 0, 0, 1, 0, 0, 0, 0]},
}
PREFLIGHT = TASK / "PREFLIGHT.md"
STATIC_QA = TASK / "STATIC_QA.json"
PROBE_REGISTRY = TASK / "PROBE_MANIFEST.json"
WORK_UNIT = TASK / "WORK_UNIT.json"
BATCH_MANIFEST = TASK / "BATCH_MANIFEST.json"
EXPERIMENT_MANIFEST = SERIES / "experiment_manifest.json"

sys.path.insert(0, str(SERIES / "scripts"))
import diagonal_platform as platform  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def jnew(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def jreplace(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def _baseline(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    result, qa, chain_qa = (jread(run_dir / name) for name in
                            ("result.json", "qa.json", "chain_qa.json"))
    digest = sha(raw)
    if (digest != BASE_RUNS[run_id] or result.get("raw_sha256") != digest or
            result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            qa.get("status") != "PASS" or chain_qa.get("status") != "PASS" or
            chain_qa.get("raw_sha256_after_analysis") != digest):
        raise RuntimeError(f"A025/A026 baseline identity/QA mismatch: {run_id}")
    return {"run_id": run_id, "raw_sha256": digest, "raw_bytes": raw.stat().st_size,
            "deck_sha256": result.get("deck_sha256"),
            "stimulus_sha256": result.get("stimulus_sha256"), "qa_status": "PASS"}


def _pwl_pairs(line: str) -> list[tuple[str, str]]:
    body = line.split("PWL(", 1)[1].removesuffix(")").split()
    return list(zip(body[0::2], body[1::2], strict=True))


def _source_map(text: str) -> dict[str, str]:
    sources = {line.split(None, 1)[0]: line for line in text.splitlines() if line.startswith("I_")}
    if len(sources) != 24:
        raise RuntimeError(f"array stimulus must contain 24 PWL sources, found {len(sources)}")
    return sources


def _normalize_physical_deck(deck: str) -> list[str]:
    lines = []
    for line in deck.splitlines():
        if not line or line.startswith(("*", ".print ")):
            continue
        parts = line.split()
        name = parts[0] if parts else ""
        if re.match(r"(?:V_CBU_[AB]|V_CARRY_IN|XCBU|XCB_CARRY|V_T1_LINK)_D[1-6]$", name):
            continue
        lines.append(line)
    return lines


def _expected_probes(rendered: dict[str, Any]) -> None:
    signals = {item["label"] for item in rendered["probes"]["signals"]}
    required = {"V(DFF_IN)", "V(CLK_DFF)", "V(DFF_O)", "I(V_DFF_DATA)", "I(R_DFF_OUT)"}
    for jj in ("B1", "B2", "B7"):
        required.update((f"P({jj}|XDFF)", f"V({jj}|XDFF)"))
    for name, cells in platform.DIAGONALS.items():
        final_cb = f"XCB_{name}_L{len(cells)}"
        required.update((f"V(DOUT_{name})", f"P(BJ1|{final_cb})", f"V(BJ1|{final_cb})",
                         f"V(T1_I_{name})", f"V(CLK_{name})", f"V(S_{name})", f"V(C_{name})"))
        for jj in platform.T1_CRITICAL_JJS:
            required.update((f"P({jj}|XT1_{name})", f"V({jj}|XT1_{name})"))
    for index in range(1, 7):
        cb = f"XCB_CARRY_D{index}"
        required.update((f"V(CARRY_CB_IN_D{index})", f"V(CARRY_CB_OUT_D{index})",
                         f"V(CBU_JOIN_D{index})", f"I(V_CBU_A_D{index})",
                         f"I(V_CARRY_IN_D{index})", f"I(V_CBU_B_D{index})",
                         f"I(V_T1_LINK_D{index})", f"P(BJ1|{cb})", f"V(BJ1|{cb})",
                         f"P(BJ2|{cb})", f"V(BJ2|{cb})", f"I(IB1|{cb})"))
    missing = sorted(required - signals)
    if missing:
        raise RuntimeError(f"full CB-chain focus probes missing: {missing}")


def _render_regression(preset: str, run_id: str, expected_sha: str) -> dict[str, Any]:
    case, stimulus, params = platform.load_config(preset)
    rendered = platform.render(case, stimulus, params, RUNS / run_id)
    old_deck = (RUNS / run_id / "deck.cir").read_text(encoding="utf-8")
    digest = hashlib.sha256(rendered["deck"].encode()).hexdigest()
    if rendered["deck"] != old_deck or digest != expected_sha:
        raise RuntimeError(f"legacy/previous render regression failed: {preset}")
    return {"status": "PASS", "run_id": run_id, "deck_sha256": digest, "byte_identical": True}


def _static_matrix(*, run_josim_sanity: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if git("rev-parse", "HEAD") != BASE_HEAD and run_josim_sanity:
        raise RuntimeError(f"static preflight must start from base HEAD {BASE_HEAD}")
    if not platform.SOLVER.is_file() or not platform.PLOTTER.is_file() or not platform.PLOTLY_ASSET.is_file():
        raise RuntimeError("recorded JoSIM solver, classic plotter, or shared Plotly asset is missing")
    if platform.allocate_run_id("unused").split("_", 1)[0] != "A027":
        raise RuntimeError(f"run allocation is not A027: {platform.allocate_run_id('unused')}")
    for run_id, *_ in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX:
        if (RUNS / run_id).exists() or any(item.get("run_id") == run_id
                                            for item in jread(EXPERIMENT_MANIFEST).get("runs", [])):
            raise RuntimeError(f"immutable run ID already occupied; refusing overwrite: {run_id}")
    if run_josim_sanity and any(path.exists() for path in
                                (PREFLIGHT, STATIC_QA, PROBE_REGISTRY, WORK_UNIT, BATCH_MANIFEST)):
        raise RuntimeError("full-chain preflight output path collision; refusing overwrite")

    sources = platform.verify_sources()
    if set(sources) != set(platform.SOURCE_SHA256):
        raise RuntimeError("pinned canonical source closure is incomplete")
    if platform.subckt_pins(REPO / platform.SOURCE_PATHS["CB"], "CB") != ("IN", "OUT"):
        raise RuntimeError("canonical CB_0928 pin order is not IN OUT")
    if sha(REPO / platform.SOURCE_PATHS["CB"]) != platform.SOURCE_SHA256["CB"]:
        raise RuntimeError("canonical CB_0928 SHA does not match the pinned source")
    for ref in BASE_RUNS:
        _baseline(ref)

    legacy = {
        "CHAIN_ALL_GLOBAL_CLOCK": _render_regression("CHAIN_ALL_GLOBAL_CLOCK", "A021_CHAIN_ALL_GLOBAL_CLOCK",
                                                       "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364"),
        "CHAIN_PAPER_GLOBAL_CLOCK": _render_regression("CHAIN_PAPER_GLOBAL_CLOCK", "A022_CHAIN_PAPER_GLOBAL_CLOCK",
                                                        "678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364"),
        "CB_DIRECT_D1_ALL_CLOCK": _render_regression("CB_DIRECT_D1_ALL_CLOCK", "A023_CB_DIRECT_D1_ALL_CLOCK",
                                                       "46263c34dbc04627dff5b9b584f3e06eac1cf25c602d39874bca6392e46c93b4"),
        "CB_DIRECT_D1_PAPER_CLOCK": _render_regression("CB_DIRECT_D1_PAPER_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK",
                                                        "46263c34dbc04627dff5b9b584f3e06eac1cf25c602d39874bca6392e46c93b4"),
        "CB_CARRY_BUFFER_D1_ALL_CLOCK": _render_regression("CARRY_CB_D1_ALL_CLOCK", "A025_CARRY_CB_D1_ALL_CLOCK",
                                                            "25e52057272dcbb7e2a7134be2ba396583427427c16db0c60185a9ae5bdee981"),
        "CB_CARRY_BUFFER_D1_PAPER_CLOCK": _render_regression("CARRY_CB_D1_PAPER_CLOCK", "A026_CARRY_CB_D1_PAPER_CLOCK",
                                                              "25e52057272dcbb7e2a7134be2ba396583427427c16db0c60185a9ae5bdee981"),
    }
    terminal_case, terminal_stimulus, terminal_params = platform.load_config("PAPER_1101_1101")
    terminal_render = platform.render(terminal_case, terminal_stimulus, terminal_params,
                                      RUNS / "_CB_CARRY_ALL_TERMINAL_REGRESSION")
    if terminal_render["static_qa"].get("status") != "PASS" or terminal_render["static_qa"].get("t1_count", 0) != 0:
        raise RuntimeError("DIAGONAL_TERMINAL render-only compatibility failed")
    legacy["DIAGONAL_TERMINAL"] = {"status": "PASS", "static_qa": "PASS",
                                   "deck_sha256": hashlib.sha256(terminal_render["deck"].encode()).hexdigest()}
    independent_case, independent_stimulus, independent_params = platform.load_config("CHAIN_ALL_GLOBAL_CLOCK")
    independent_case.update({"CASE": "CB_CARRY_ALL_COMPAT_T1_INDEPENDENT",
                             "OUTPUT_MODE": "DIAGONAL_T1_INDEPENDENT", "T1_MODE": "ALL_INDEPENDENT",
                             "CBU_MODE": "OFF", "CARRY_MODE": "NONE", "CBU_CHAIN_TOPOLOGY": "LEGACY",
                             "CBU_OVERRIDE_D1": "NONE", "PROBE_PROFILE": "t1_array_focus",
                             "FOCUS_DIAGONAL": "D3"})
    platform.validate_config(independent_case, independent_stimulus, independent_params)
    independent_render = platform.render(independent_case, independent_stimulus, independent_params,
                                         RUNS / "_CB_CARRY_ALL_T1_INDEPENDENT_REGRESSION")
    if independent_render["static_qa"].get("status") != "PASS":
        raise RuntimeError("DIAGONAL_T1_INDEPENDENT render-only compatibility failed")
    legacy["DIAGONAL_T1_INDEPENDENT"] = {"status": "PASS", "static_qa": "PASS",
                                         "deck_sha256": hashlib.sha256(independent_render["deck"].encode()).hexdigest()}
    rendered_cases, sanity_records = [], []
    expected_sjtl = {"D0": (1,), "D1": (1, 1), "D2": (1, 2, 1),
                     "D3": (1, 2, 2, 1), "D4": (1, 2, 1), "D5": (1, 1), "D6": (1,)}
    baseline_all_case = jread(RUNS / "A025_CARRY_CB_D1_ALL_CLOCK" / "case_manifest.json")["case"]
    baseline_paper_case = jread(RUNS / "A026_CARRY_CB_D1_PAPER_CLOCK" / "case_manifest.json")["case"]
    baseline_params = {}
    for name in ("T1_PARAMS.snapshot.env", "CBU_PARAMS.snapshot.env", "DFF_PARAMS.snapshot.env",
                 "D0_JTL_PARAMS.snapshot.env"):
        baseline_params.update(platform.parse_env(RUNS / "A025_CARRY_CB_D1_ALL_CLOCK" / name))

    for run_id, preset, rows, cols, expected_population in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX:
        case, stimulus, params = platform.load_config(preset)
        expected_case = {"CASE": preset, "ROW_BITS": rows, "COL_BITS": cols,
                         "SE_ENABLE_MASK": "ALL", "OUTPUT_MODE": "DIAGONAL_T1_CHAIN",
                         "T1_MODE": "CHAIN", "CBU_MODE": "PHYSICAL_TWO_INPUT", "CARRY_MODE": "RIPPLE",
                         "CBU_TYPE": "THmitll_MERGE", "CBU_CHAIN_TOPOLOGY": "CB_CARRY_BUFFER_ALL",
                         "CBU_OVERRIDE_D1": "NONE", "DFF_TYPE": "THmitll_DFF",
                         "D0_JTL_TYPE": "D0_SJTL", "D0_JTL_COUNT": "1",
                         "T1_CHAIN_CLOCK_MODE": "GLOBAL_ONESHOT", "T1_CHAIN_CLK_START": "200p",
                         "DRIVE_MODE": "SHARED", "SE_TOPOLOGY": "CELL", "SE_GATE_MODE": "CROSSPOINT",
                         "ROW_WL_WRITE_AMPLITUDE": "400u", "COL_BL_WRITE_AMPLITUDE": "400u",
                         "ROW_WL_READ_AMPLITUDE": "400u", "COL_SE_READ_AMPLITUDE": "100u",
                         "DT": "0.01p", "STOP": "300p", "PROBE_PROFILE": "t1_chain_focus"}
        for key, value in expected_case.items():
            if case.get(key) != value:
                raise RuntimeError(f"{preset}: expected {key}={value}, found {case.get(key)}")
        if {name: _counts for name, _counts in ((d, platform._sjtl_counts(case, d)) for d in platform.DIAGONALS)} != expected_sjtl:
            raise RuntimeError(f"{preset}: array sJTL counts differ from the A025/A026 frozen pattern")
        actual_pop = [sum(cell in platform._active_cells(case) for cell in cells)
                      for cells in platform.DIAGONALS.values()]
        theory = THEORY_BY_RUN[run_id]
        if actual_pop != expected_population or actual_pop != theory["diagonal_population"]:
            raise RuntimeError(f"{preset}: ROW/COL mapping produces {actual_pop}, expected {expected_population}")
        derived_inputs = [actual_pop[index] + (theory["carry"][index-1] if index else 0)
                          for index in range(7)]
        if derived_inputs != theory["stage_inputs"]:
            raise RuntimeError(f"{preset}: stage-input reference arithmetic is inconsistent: {derived_inputs}")
        if params != baseline_params:
            raise RuntimeError(f"{preset}: T1/CBU/DFF/D0-JTL parameters differ from A025/A026")

        baseline_run = "A026_CARRY_CB_D1_PAPER_CLOCK" if rows == "1101" else "A025_CARRY_CB_D1_ALL_CLOCK"
        baseline_case = dict(baseline_paper_case if rows == "1101" else baseline_all_case)
        baseline_case.setdefault("CBU_CHAIN_TOPOLOGY", "LEGACY")
        allowed_case_differences = {"CASE", "ROW_BITS", "COL_BITS", "CBU_CHAIN_TOPOLOGY",
                                    "CBU_OVERRIDE_D1", "FOCUS_STAGE"}
        differences = {key for key in set(case) | set(baseline_case)
                       if case.get(key) != baseline_case.get(key)}
        if differences - allowed_case_differences:
            raise RuntimeError(f"{preset}: unregistered case parameter differences: {sorted(differences)}")
        base_stimulus = jread(RUNS / baseline_run / "case_manifest.json")["stimulus"]
        if rows != "1100" and stimulus != base_stimulus:
            raise RuntimeError(f"{preset}: stimulus differs from its A025/A026 matched baseline")

        rendered = platform.render(case, stimulus, params, RUNS / run_id)
        if rendered["static_qa"].get("status") != "PASS":
            raise RuntimeError(f"platform static QA failed: {preset}")
        if rendered["static_qa"]["raw_estimate_bytes"] >= platform.MAX_RAW_BYTES:
            raise RuntimeError(f"raw estimate exceeds the 100MB single-file guard: {preset}")
        deck_lines = rendered["deck"].splitlines()
        carry_lines = set()
        for index in range(1, 7):
            carry_lines.update({
                f"V_CBU_A_D{index} DOUT_D{index} CBU_JOIN_D{index} 0",
                f"V_CARRY_IN_D{index} C_D{index-1} CARRY_CB_IN_D{index} 0",
                f"XCB_CARRY_D{index} CARRY_CB_IN_D{index} CARRY_CB_OUT_D{index} CB",
                f"V_CBU_B_D{index} CARRY_CB_OUT_D{index} CBU_JOIN_D{index} 0",
                f"V_T1_LINK_D{index} CBU_JOIN_D{index} T1_I_D{index} 0"})
        if not carry_lines.issubset(set(deck_lines)):
            raise RuntimeError(f"{preset}: one or more six-stage CB_CARRY_BUFFER wires are wrong")
        if len([line for line in deck_lines if line.startswith("XCB_CARRY_D")]) != 6:
            raise RuntimeError(f"{preset}: expected exactly six added Carry CBs")
        if any(line.startswith("XCBU_D") for line in deck_lines):
            raise RuntimeError(f"{preset}: legacy ColdFlux CBU instance remains in CB-only chain")
        if len([line for line in deck_lines if re.match(r"XCB_D[0-6]_L[1-4]\s", line)]) != 16:
            raise RuntimeError(f"{preset}: array-side CB count changed")
        if len([line for line in deck_lines if line.startswith("XSJTL_")]) != 20:
            raise RuntimeError(f"{preset}: original array sJTL count changed")
        if len([line for line in deck_lines if line.startswith("XT1_D")]) != 7 or \
                len([line for line in deck_lines if line.startswith("XDFF ")]) != 1:
            raise RuntimeError(f"{preset}: T1/DFF count changed")
        if any(line.startswith(("R_TERM_D", "R_C_D", "XSJTL_CBU_D", "XJTL_CBU_D")) for line in deck_lines):
            raise RuntimeError(f"{preset}: forbidden terminal or added stage isolator/load found")
        for index in range(1, 7):
            if sum(f"CBU_JOIN_D{index}" in line for line in deck_lines
                   if not line.startswith(("*", ".print"))) != 3:
                raise RuntimeError(f"{preset}: JOIN_D{index} is not an isolated three-branch join")
        if "V_DFF_DATA C_D6 DFF_IN 0" not in deck_lines:
            raise RuntimeError(f"{preset}: C6 no longer directly drives DFF input")
        if rendered["static_qa"]["pulse_clock_count"] != 8 or rendered["static_qa"]["quiet_clock_count"] != 0:
            raise RuntimeError(f"{preset}: global one-shot clock branches differ from A025/A026")
        reference_run = ("A026_CARRY_CB_D1_PAPER_CLOCK" if rows == "1101"
                         else "A025_CARRY_CB_D1_ALL_CLOCK")
        reference_deck = (RUNS / reference_run / "deck.cir").read_text(encoding="utf-8")
        if _normalize_physical_deck(rendered["deck"]) != _normalize_physical_deck(reference_deck):
            raise RuntimeError(f"{preset}: non-CBU physical deck differs from {reference_run}")
        _expected_probes(rendered)
        pages = platform.plot_signals(rendered["probes"])
        if len(pages) != 8 or pages[:2] != [
                {"file": "01_full_chain_overview.html",
                 "title": "Seven D inputs, Sum/Carry outputs, DFF.O and all global clocks",
                 "signals": pages[0]["signals"]},
                {"file": "02_carry_propagation.html",
                 "title": "D/Carry CBU inputs, CBU outputs, T1 inputs and clocks",
                 "signals": pages[1]["signals"]}]:
            raise RuntimeError(f"{preset}: expected overview, propagation, and six stage-focus plot pages")
        if run_josim_sanity:
            with tempfile.TemporaryDirectory(prefix=".cb-carry-all-static-", dir=RUNS) as tmp_name:
                temp = Path(tmp_name)
                (temp / "deck.cir").write_text(rendered["deck"], encoding="utf-8")
                (temp / "stimulus.inc").write_text(rendered["stimulus_text"], encoding="utf-8")
                t1_target = temp / "sources" / "t1_cell_tunable.cir"
                t1_target.parent.mkdir(parents=True, exist_ok=True)
                t1_target.write_text(rendered["t1_source_text"], encoding="utf-8")
                for rel, text in rendered["chain_source_texts"].items():
                    target = temp / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(text, encoding="utf-8")
                command = [str(platform.SOLVER)]
                for subckt in STATIC_SUBCKTS:
                    command.extend(("-s", subckt))
                command.append(str(temp / "deck.cir"))
                proc = subprocess.run(command, cwd=temp, capture_output=True, text=True,
                                      check=False, timeout=120)
                stdout_b, stderr_b = proc.stdout.encode(), proc.stderr.encode()
                record = {"run_id": run_id, "argv": command, "exit_code": proc.returncode,
                          "physical_solve_count": 0,
                          "stdout_sha256": hashlib.sha256(stdout_b).hexdigest(), "stdout_bytes": len(stdout_b),
                          "stdout_tail": proc.stdout.splitlines()[-8:],
                          "stderr_sha256": hashlib.sha256(stderr_b).hexdigest(), "stderr_bytes": len(stderr_b),
                          "stderr_tail": proc.stderr.splitlines()[-8:]}
                sanity_records.append(record)
                if proc.returncode != 0:
                    raise RuntimeError(f"JoSIM -s static check failed for {preset}: {record}")
        else:
            sanity_records = []
        rendered_cases.append({"run_id": run_id, "preset": preset, "case": case,
                               "stimulus": stimulus, "params": params, "rendered": rendered,
                               "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
                               "stimulus_sha256": hashlib.sha256(rendered["stimulus_text"].encode()).hexdigest(),
                               "probe_sha256": hashlib.sha256((json.dumps(rendered["probes"], ensure_ascii=False, indent=2)+"\n").encode()).hexdigest(),
                               "expected_diagonal_population": expected_population})
    source_maps = [_source_map(item["rendered"]["stimulus_text"]) for item in rendered_cases]
    for index, baseline_run in ((0, "A025_CARRY_CB_D1_ALL_CLOCK"),
                                (1, "A026_CARRY_CB_D1_PAPER_CLOCK")):
        baseline_sources = _source_map((RUNS / baseline_run / "stimulus.inc").read_text(encoding="utf-8"))
        if source_maps[index] != baseline_sources:
            raise RuntimeError(f"{rendered_cases[index]['preset']} stimulus differs from {baseline_run}")
    full_sources, low_sources = source_maps[0], source_maps[2]
    if set(full_sources) != set(low_sources):
        raise RuntimeError("A029 stimulus source set differs from the registered 24 sources")
    expected_diff = {"I_WL_R3", "I_WL_R4"}
    expected_diff.update(f"I_SE_{cell}" for cell in platform.CELLS
                         if platform._mask_active(rendered_cases[0]["case"], cell) !=
                         platform._mask_active(rendered_cases[2]["case"], cell))
    actual_diff = {name for name in full_sources if full_sources[name] != low_sources[name]}
    if actual_diff != expected_diff:
        raise RuntimeError(f"A029 stimulus changes do not match the row/crosspoint selection: {sorted(actual_diff)}")
    low_case, low_stimulus = rendered_cases[2]["case"], rendered_cases[2]["stimulus"]
    plateau_start = platform._fmt_ps(platform._time_ps(low_stimulus["FINAL_READ_START"]) +
                                     platform._time_ps(low_stimulus["FINAL_READ_RISE"]))
    plateau_end = platform._fmt_ps(platform._time_ps(low_stimulus["FINAL_READ_START"]) +
                                   platform._time_ps(low_stimulus["FINAL_READ_RISE"]) +
                                   platform._time_ps(low_stimulus["FINAL_READ_HOLD"]))
    fall_end = platform._fmt_ps(platform._time_ps(low_stimulus["FINAL_READ_START"]) +
                                platform._time_ps(low_stimulus["FINAL_READ_RISE"]) +
                                platform._time_ps(low_stimulus["FINAL_READ_HOLD"]) +
                                platform._time_ps(low_stimulus["FINAL_READ_FALL"]))
    for source in full_sources:
        full_pairs = _pwl_pairs(full_sources[source])
        low_pairs = _pwl_pairs(low_sources[source])
        if [time for time, _value in full_pairs] != [time for time, _value in low_pairs]:
            raise RuntimeError(f"A029 changed PWL knot times for {source}")
        if any(dict(full_pairs).get(time) != dict(low_pairs).get(time)
               for time, _value in full_pairs
               if time in {"0", "0p"} or platform._time_ps(time) < platform._time_ps(plateau_start)):
            raise RuntimeError(f"A029 changed a preparation-phase PWL level for {source}")
    for row in range(1, 5):
        values = dict(_pwl_pairs(low_sources[f"I_WL_R{row}"]))
        expected_level = low_case["ROW_WL_READ_AMPLITUDE"] if low_case["ROW_BITS"][row-1] == "1" else "0"
        if any(values.get(time) != expected_level for time in (plateau_start, plateau_end)) or values.get(fall_end) != "0":
            raise RuntimeError(f"A029 FINAL_READ WL level mismatch at R{row}")
    for col in range(1, 5):
        values = dict(_pwl_pairs(low_sources[f"I_BL_C{col}"]))
        if any(values.get(time) != "0" for time in (plateau_start, plateau_end)):
            raise RuntimeError(f"A029 FINAL_READ BL_C{col} is not zero")
    active_low = set(platform._active_cells(low_case))
    for cell in platform.CELLS:
        values = dict(_pwl_pairs(low_sources[f"I_SE_{cell}"]))
        expected_level = low_case["COL_SE_READ_AMPLITUDE"] if cell in active_low else "0"
        if any(values.get(time) != expected_level for time in (plateau_start, plateau_end)) or values.get(fall_end) != "0":
            raise RuntimeError(f"A029 FINAL_READ SE level mismatch at {cell}")
    return rendered_cases, {"sources": sources, "legacy_render_regression": legacy,
                            "jo_sim_static_sanity": sanity_records}


def _expected_probes(rendered: dict[str, Any]) -> None:
    labels = {signal["label"] for signal in rendered["probes"]["signals"]}
    missing = []
    for name, cells in platform.DIAGONALS.items():
        array_cb = f"XCB_{name}_L{len(cells)}"
        for label in (f"V(DOUT_{name})", f"P(BJ1|{array_cb})", f"V(BJ1|{array_cb})",
                      f"V(T1_I_{name})", f"V(CLK_{name})", f"V(S_{name})", f"V(C_{name})"):
            if label not in labels:
                missing.append(label)
        t1 = f"XT1_{name}"
        for jj in platform.T1_CRITICAL_JJS:
            for prefix in ("P", "V"):
                label = f"{prefix}({jj}|{t1})"
                if label not in labels:
                    missing.append(label)
    for index in range(1, 7):
        cb = f"XCB_CARRY_D{index}"
        for label in (f"V(C_D{index-1})", f"V(CARRY_CB_IN_D{index})", f"V(CARRY_CB_OUT_D{index})",
                      f"V(CBU_JOIN_D{index})", f"I(V_CBU_A_D{index})", f"I(V_CARRY_IN_D{index})",
                      f"I(V_CBU_B_D{index})", f"I(V_T1_LINK_D{index})", f"I(IB1|{cb})"):
            if label not in labels:
                missing.append(label)
        for jj in ("BJ1", "BJ2"):
            for prefix in ("P", "V"):
                label = f"{prefix}({jj}|{cb})"
                if label not in labels:
                    missing.append(label)
    for label in ("V(DFF_IN)", "V(CLK_DFF)", "V(DFF_O)", "I(V_DFF_DATA)", "I(R_DFF_OUT)"):
        if label not in labels:
            missing.append(label)
    for jj in ("B1", "B2", "B7"):
        for prefix in ("P", "V"):
            label = f"{prefix}({jj}|XDFF)"
            if label not in labels:
                missing.append(label)
    if missing:
        raise RuntimeError(f"registered full-chain probes do not resolve: {sorted(set(missing))}")


def _preflight_text(qa: dict[str, Any]) -> str:
    rows = ["# Full six-stage CB_CARRY_BUFFER_ALL preflight", "",
            "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
            f"- Batch ID: `{BATCH_ID}`; risk: `NORMAL`; baseline HEAD: `{qa['parent_head']}`.",
            f"- Authorized solve matrix: exactly `{', '.join(item['run_id'] for item in qa['runs'])}`; physical solve count 3.",
            f"- Solver: `{qa['solver']['path']}`; {qa['solver']['version'].splitlines()[-1]}; SHA-256 `{qa['solver']['sha256']}`.",
            f"- Canonical CB_0928 SHA-256: `{platform.SOURCE_SHA256['CB']}`; pins `IN OUT`; no canonical sources modified.",
            "- Every D1-D6 stage uses two sensed input branches: DOUT_Dk directly to JOIN_Dk; C_D(k-1) through one CB_0928 then to the same JOIN_Dk; JOIN_Dk directly feeds T1_Dk.I.",
            "- Six new canonical Carry CB instances; no XCBU_D1-D6 MERGE instances; no extra sJTL/JTL/MERGE after joins.",
            "- D0 entrance JTL, 16 array CBs, 20 array sJTLs, seven T1s, final DFF, and all loads/clocks remain as A025/A026.",
            "- Frozen amplitudes: shared WL/BL=400u; cell SE=100u; clock=GLOBAL_ONESHOT at 200p, 1.2m, 1p/2p/1p, 2Ω; DT=0.01p, STOP=300p.",
            "- Registered windows are half-open: ARRAY_FINAL_READ [110,121), PRE_CLOCK [121,200), CLOCK_EDGE [200,205), POST_CLOCK [205,300), TOTAL [0,300) ps.",
            "- P is raw radians. Deltas are independently unwrapped per run; delta/(2π) is navigation only. No bit decoder or SFQ/event classifier is defined.",
            "- Theoretical input/carry/output vectors are references, not success gates. Scientific interpretation is NOT_PERFORMED.",
            "- A029's current platform map `d=r+3-c` yields active cells R1C3/R1C4/R2C3/R2C4 and diagonal population [1,2,1,0,0,0,0].",
            "- Hard static/solver/artifact failure stops later solves. Physical behavior outside theory is preserved as a valid negative observation; no retries or tuning.",
            "", "## Frozen run matrix", "",
            "| Run | ROW/COL | Diagonal population reference | Stage inputs reference | Target product (reference only) | Probes | Raw estimate |",
            "|---|---|---|---|---:|---:|---:|"]
    for item in qa["runs"]:
        rows.append(f"| {item['run_id']} | {item['row_bits']}/{item['column_bits']} | {item['diagonal_population_reference']} | {item['stage_inputs_reference']} | {item['product_reference']} | {item['probe_count']} | {item['raw_estimate_bytes']} B |")
    rows.extend(["", "## Static check outcomes", "",
                 "- Legacy terminal, MERGE, D1 CB_DIRECT, and D1 CB_CARRY_BUFFER render-only compatibility: PASS.",
                 "- Topology/ports/nodes/sensors/loads/probe resolution: PASS.",
                 "- JoSIM `-s` syntax/model parse for all three candidate decks: PASS; physical_solve_count=0.",
                 "- A027/A028 source/stimulus are paired to A025/A026 except registered all-CBU topology and focus-probe schema.",
                 "- A029 row/column mapping and every PWL source were verified against the existing array map; no bit-order change.",
                 "- The static QA, exact probe manifest, deck/stimulus hashes and raw estimates are recorded in `STATIC_QA.json` and `WORK_UNIT.json`.", ""])
    return "\n".join(rows)


def prepare_preflight() -> int:
    if git("rev-parse", "HEAD") != BASE_HEAD:
        raise RuntimeError(f"expected current task base HEAD {BASE_HEAD}")
    if any(path.exists() for path in (PREFLIGHT, STATIC_QA, PROBE_REGISTRY, WORK_UNIT, BATCH_MANIFEST)):
        raise RuntimeError("full CB chain preflight output collision; refusing overwrite")
    cases, static = _static_matrix(run_josim_sanity=True)
    cb_path = REPO / platform.SOURCE_PATHS["CB"]
    source_records = static["sources"]
    solver = platform._solver_info()
    if solver["parent_head"] != BASE_HEAD:
        raise RuntimeError("solver parent HEAD differs from registered baseline")
    task_paths = (PREFLIGHT, STATIC_QA, PROBE_REGISTRY, WORK_UNIT, BATCH_MANIFEST)
    if any(path.exists() for path in task_paths):
        raise RuntimeError("full CB chain preflight output collision; refusing overwrite")
    static_runs = []
    for item in cases:
        theory = THEORY_BY_RUN[item["run_id"]]
        static_runs.append({"run_id": item["run_id"], "preset": item["preset"],
                            "row_bits": item["case"]["ROW_BITS"], "column_bits": item["case"]["COL_BITS"],
                            "diagonal_population_reference": theory["diagonal_population"],
                            "stage_inputs_reference": theory["stage_inputs"],
                            "carry_reference": theory["carry"],
                            "product_reference": theory["product"],
                            "bits_lsb_to_msb_reference": theory["bits"],
                            "deck_sha256": item["deck_sha256"],
                            "stimulus_sha256": item["stimulus_sha256"],
                            "probe_sha256": item["probe_sha256"],
                            "probe_count": item["rendered"]["probes"]["signal_count"],
                            "raw_estimate_bytes": item["rendered"]["static_qa"]["raw_estimate_bytes"],
                            "plot_pages": [page["file"] for page in platform.plot_signals(item["rendered"]["probes"])],
                            "static_qa_status": item["rendered"]["static_qa"]["status"]})
    qa = {"schema": "bvm-4x4-cb-carry-buffer-all-static-qa-v1", "status": "PASS",
          "batch_id": BATCH_ID, "parent_head": BASE_HEAD, "risk_level": "NORMAL",
          "physical_solve_count": 0, "solver": solver,
          "runner_sha256": sha(Path(platform.__file__).resolve()),
          "batch_runner_sha256": sha(Path(__file__).resolve()),
          "analysis_runner_sha256": sha(SERIES / "scripts" / "analyze_cb_carry_buffer_all.py"),
          "plotter_sha256": sha(platform.PLOTTER), "plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
          "config_sha256": {path.relative_to(SERIES).as_posix(): sha(path) for path in
                            (platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS,
                             platform.CBU_PARAMS, platform.DFF_PARAMS, platform.D0_JTL_PARAMS)},
          "canonical_source_sha256": {role: item["sha256"] for role, item in source_records.items()},
          "canonical_cb_0928": {"path": platform.SOURCE_PATHS["CB"], "sha256": sha(cb_path),
                                "ports": list(platform.subckt_pins(cb_path, "CB")),
                                "default_parameters_pinned": True},
          "legacy_render_regression": static["legacy_render_regression"],
          "jo_sim_static_sanity": static["jo_sim_static_sanity"],
          "topology_checks": {"t1_count": 7, "carry_cb_count": 6, "unique_join_count": 6,
                              "array_cb_count": 16, "array_sjtl_count": 20,
                              "legacy_merge_instance_count": 0, "d0_jtl_count": 1,
                              "dff_count": 1, "join_output_cb_count": 0,
                              "added_sjtl_count": 0, "terminal_load_count": 0,
                              "c0_c5_to_matching_carry_cb": True, "c6_to_dff_direct": True,
                              "global_clock_branches": 8, "no_cross_join_short": True},
          "runs": static_runs, "raw_limit_bytes": platform.MAX_RAW_BYTES,
          "raw_storage_guard": "PASS", "scientific_interpretation_performed": False}
    probe_manifest = {"schema": "bvm-4x4-cb-carry-buffer-all-probe-registry-v1",
                      "manifests_by_run_id": {item["run_id"]: item["rendered"]["probes"] for item in cases}}
    TASK.mkdir(parents=True, exist_ok=True)
    jnew(STATIC_QA, qa)
    jnew(PROBE_REGISTRY, probe_manifest)
    PREFLIGHT.write_text(_write_preflight_text(qa),
                         encoding="utf-8", newline="\n")
    manifest = jread(EXPERIMENT_MANIFEST)
    batches = manifest.setdefault("authorization_batches", [])
    if any(item.get("batch_id") == BATCH_ID for item in batches):
        raise RuntimeError(f"authorization already exists: {BATCH_ID}")
    run_ids = [item[0] for item in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX]
    preset_names = [item[1] for item in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX]
    batches.append({"batch_id": BATCH_ID, "risk_level": "NORMAL", "authorized_cases": preset_names,
                    "run_ids": run_ids, "authorized_physical_solve_count": 3,
                    "physical_solve_count_completed": 0, "preflight_parent_head": BASE_HEAD,
                    "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
                    "preflight_sha256": sha(PREFLIGHT), "static_qa_sha256": sha(STATIC_QA),
                    "scientific_interpretation_performed": False, "automatic_follow_up": False})
    authorized = manifest.setdefault("authorized_physical_solves", [])
    for preset in preset_names:
        if preset not in authorized:
            authorized.append(preset)
    manifest["maximum_physical_solve_count"] = max(int(manifest.get("maximum_physical_solve_count", 0)), 29)
    jreplace(EXPERIMENT_MANIFEST, manifest)
    work_unit = {"schema": "bvm-4x4-cb-carry-buffer-all-work-unit-v1", "batch_id": BATCH_ID,
                 "experiment_risk_level": "NORMAL", "parent_head_at_preflight": BASE_HEAD,
                 "authorized_run_ids": run_ids, "physical_solve_count_authorized": 3,
                 "physical_solve_count_completed_at_registration": 0,
                 "preflight_sha256": sha(PREFLIGHT), "static_qa_sha256": sha(STATIC_QA),
                 "probe_manifest_sha256": sha(PROBE_REGISTRY),
                 "experiment_yaml_sha256": sha(TASK / "experiment.yaml"),
                 "metric_spec_sha256": sha(TASK / "METRIC_SPEC.json"),
                 "human_gate_sha256": sha(TASK / "human-gate.yaml"),
                 "experiment_manifest_sha256": sha(EXPERIMENT_MANIFEST),
                 "runner_sha256": sha(Path(platform.__file__).resolve()),
                 "batch_runner_sha256": sha(Path(__file__).resolve()),
                 "analysis_runner_sha256": sha(SERIES / "scripts" / "analyze_cb_carry_buffer_all.py"),
                 "canonical_cb_sha256": platform.SOURCE_SHA256["CB"],
                 "baseline_raw_sha256": BASE_RUNS,
                 "automatic_follow_up": False,
                 "scientific_interpretation_performed": False,
                 "next_action": "COMMIT_PREFLIGHT_THEN_RUN_A027_A029_AND_STOP"}
    jnew(WORK_UNIT, work_unit)
    batch = {"schema": "bvm-4x4-cb-carry-buffer-all-batch-v1", "batch_id": BATCH_ID,
             "status": "PREFLIGHT_PASS_READY", "preflight_parent_head": BASE_HEAD,
             "preflight_path": PREFLIGHT.relative_to(SERIES).as_posix(),
             "preflight_sha256": sha(PREFLIGHT), "static_qa_path": STATIC_QA.relative_to(SERIES).as_posix(),
             "static_qa_sha256": sha(STATIC_QA),
             "metric_spec_path": (TASK / "METRIC_SPEC.json").relative_to(SERIES).as_posix(),
             "metric_spec_sha256": sha(TASK / "METRIC_SPEC.json"),
             "authorized_run_ids": run_ids, "runs": [],
             "physical_solve_count_authorized": 3, "physical_solve_count_completed": 0,
             "scientific_interpretation_performed": False, "automatic_follow_up": False}
    jnew(BATCH_MANIFEST, batch)
    print(f"STATIC PREFLIGHT PASS: {BATCH_ID}; parent={BASE_HEAD}")
    for row in static_runs:
        print(f"{row['run_id']} population={row['diagonal_population_reference']} stage_inputs={row['stage_inputs_reference']} "
              f"probes={row['probe_count']} estimate={row['raw_estimate_bytes']}B deck={row['deck_sha256'][:12]} PASS")
    print("Legacy terminal/MERGE/CB_DIRECT/CB_CARRY_BUFFER render-only regressions: PASS")
    print("JoSIM -s static syntax/model validation: PASS; physical_solve_count=0.")
    return 0


def _write_preflight_text(qa: dict[str, Any]) -> str:
    lines = ["# Full CB-only carry chain A027-A029 preflight", "",
             "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.", "",
             f"- Parent HEAD: `{qa['parent_head']}`; batch: `{BATCH_ID}`; risk: `NORMAL`.",
             f"- Exactly three physical solves are authorized: `{', '.join(row['run_id'] for row in qa['runs'])}`.",
             f"- Solver: `{qa['solver']['path']}`, {qa['solver']['version'].splitlines()[-1]}, SHA-256 `{qa['solver']['sha256']}`.",
             f"- Canonical CB_0928 remains unchanged; SHA-256 `{qa['canonical_cb_0928']['sha256']}`, ports `IN OUT`.",
             "- D1-D6 each have independent JOIN nodes; current Carry alone passes through a single canonical CB; array DOUT directly joins and drives its T1 input.",
             "- No `XCBU_D1..D6` MERGE instance, join-output CB, added sJTL/JTL, or terminal Carry/DOUT load.",
             "- Array CB=16, array sJTL=20, T1=7, DFF=1; D0 entrance JTL unchanged.",
             "- Frozen stimulus and parameters: 400u shared WL/BL, 100u cell SE, one global clock at 200 ps, 1.2m, 1/2/1 ps, 2Ω; DT=0.01p, STOP=300p.",
             "- Raw phase is radians; displayed turns are navigation only. Phase/area comparisons use the same JJ and exact half-open raw rows.",
             "- Descriptive waveform-lobe candidates are not event counts. No automatic bit decoder, SFQ classifier, mechanism verdict, or optimization is authorized.",
             "- If a solver/artifact hard failure occurs, stop remaining runs. If solver/QA succeeds but output differs from theory, preserve the negative observation and continue only the remaining registered cases.",
             "", "## Registered cases", "",
             "| Run | ROW/COL | Diagonal population reference | Stage inputs reference | Product/bit reference | Probe count / raw estimate |",
             "|---|---|---|---|---|---|"]
    for row in qa["runs"]:
        output = {"A027_FULL_CB_CHAIN_ALL_CLOCK": "225 / 10000111 LSB-first",
                  "A028_FULL_CB_CHAIN_PAPER_CLOCK": "143 / 11110001 LSB-first",
                  "A029_FULL_CB_CHAIN_3X3_CLOCK": "9 / 10010000 LSB-first"}[row["run_id"]]
        lines.append(f"| {row['run_id']} | {row['row_bits']}/{row['column_bits']} | {row['diagonal_population_reference']} | {row['stage_inputs_reference']} | {output} | {row['probe_count']} / {row['raw_estimate_bytes']} B |")
    lines.extend(["", "## Static gate", "",
                 "- A029 current row/column mapping was independently enumerated from `d=r+3-c`; result is R1C3/R1C4/R2C3/R2C4 → [1,2,1,0,0,0,0].",
                 "- A025/A026 raw identity and QA checked; legacy A021/A022 MERGE, A023/A024 CB_DIRECT, and A025/A026 single-stage carry-buffer renders were compared byte-for-byte.",
                 "- Three candidate decks passed JoSIM `-s` syntax/model checks; physical solve count remains zero until the locked batch is run.",
                 "- Full probe list, hashes, source closure, output estimates and static QA are in `PROBE_MANIFEST.json` and `STATIC_QA.json`.", ""])
    return "\n".join(lines)


def _update_authorization_completed(count: int, execution_head: str | None = None) -> None:
    manifest = jread(EXPERIMENT_MANIFEST)
    records = [item for item in manifest.get("authorization_batches", []) if item.get("batch_id") == BATCH_ID]
    if len(records) != 1:
        raise RuntimeError("expected exactly one authorization record for full CB chain")
    records[0]["physical_solve_count_completed"] = count
    if execution_head is not None:
        records[0]["parent_head_at_execution"] = execution_head
    jreplace(EXPERIMENT_MANIFEST, manifest)


def run_batch() -> int:
    if git("status", "--porcelain"):
        raise RuntimeError("A027-A029 execution requires committed preflight and a clean worktree")
    if not all(path.is_file() for path in (PREFLIGHT, STATIC_QA, PROBE_REGISTRY, WORK_UNIT, BATCH_MANIFEST)):
        raise RuntimeError("locked full-chain preflight/work-unit artifacts are missing")
    qa, unit, batch = jread(STATIC_QA), jread(WORK_UNIT), jread(BATCH_MANIFEST)
    expected_ids = [item[0] for item in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX]
    if (qa.get("status") != "PASS" or batch.get("status") != "PREFLIGHT_PASS_READY" or
            batch.get("physical_solve_count_completed") != 0 or
            unit.get("authorized_run_ids") != expected_ids or
            unit.get("physical_solve_count_authorized") != 3):
        raise RuntimeError("locked preflight does not authorize exactly A027-A029")
    if (unit.get("preflight_sha256") != sha(PREFLIGHT) or
            unit.get("static_qa_sha256") != sha(STATIC_QA) or
            unit.get("probe_manifest_sha256") != sha(PROBE_REGISTRY) or
            unit.get("experiment_yaml_sha256") != sha(TASK / "experiment.yaml") or
            unit.get("metric_spec_sha256") != sha(TASK / "METRIC_SPEC.json") or
            unit.get("human_gate_sha256") != sha(TASK / "human-gate.yaml") or
            unit.get("experiment_manifest_sha256") != sha(EXPERIMENT_MANIFEST)):
        raise RuntimeError("preflight-bound inputs changed; refusing physical solve")
    for key, path in (("runner_sha256", Path(platform.__file__).resolve()),
                      ("batch_runner_sha256", Path(__file__).resolve()),
                      ("analysis_runner_sha256", SERIES / "scripts" / "analyze_cb_carry_buffer_all.py")):
        if qa.get(key) != sha(path) or unit.get(key) != sha(path):
            raise RuntimeError(f"locked {key} differs from the current file")
    if qa.get("plotter_sha256") != sha(platform.PLOTTER) or qa.get("plotly_asset_sha256") != sha(platform.PLOTLY_ASSET):
        raise RuntimeError("plotter/Plotly asset identity differs from locked static QA")
    config_hashes = {path.relative_to(SERIES).as_posix(): sha(path) for path in
                     (platform.USER_CASE, platform.STIMULUS, platform.T1_PARAMS,
                      platform.CBU_PARAMS, platform.DFF_PARAMS, platform.D0_JTL_PARAMS)}
    if qa.get("config_sha256") != config_hashes:
        raise RuntimeError("effective platform configuration changed after preflight")
    if qa.get("canonical_source_sha256") != {
            role: record["sha256"] for role, record in platform.verify_sources().items()}:
        raise RuntimeError("canonical source identity changed after preflight")

    cases, _static = _static_matrix(run_josim_sanity=False)
    locked_runs = {item["run_id"]: item for item in qa["runs"]}
    for item in cases:
        lock = locked_runs.get(item["run_id"])
        if (lock is None or lock.get("deck_sha256") != item["deck_sha256"] or
                lock.get("stimulus_sha256") != item["stimulus_sha256"] or
                lock.get("probe_sha256") != item["probe_sha256"]):
            raise RuntimeError(f"rendered case differs from preflight: {item['run_id']}")
    solver = platform._solver_info()
    if (solver["path"], solver["version"], solver["sha256"]) != (
            qa["solver"]["path"], qa["solver"]["version"], qa["solver"]["sha256"]):
        raise RuntimeError("JoSIM binary identity differs from static preflight")

    batch.update({"status": "RUNNING", "execution_head": solver["parent_head"], "runs": []})
    jreplace(BATCH_MANIFEST, batch)
    _update_authorization_completed(0, solver["parent_head"])
    for item in cases:
        run_id = item["run_id"]
        print(f"START {run_id}: {item['preset']} ROW/COL={item['case']['ROW_BITS']}/"
              f"{item['case']['COL_BITS']} topology=CB_CARRY_BUFFER_ALL", flush=True)
        code, result = platform.run_one(
            item["case"], item["stimulus"], item["params"], solver,
            batch_id=BATCH_ID, run_id_override=run_id, rendered_override=item["rendered"],
            preflight_path=PREFLIGHT, metric_spec_path_override=TASK / "METRIC_SPEC.json",
            expected_deck_sha256=locked_runs[run_id]["deck_sha256"])
        record = {"run_id": run_id, "preset": item["preset"], "status": result.get("status"),
                  "artifact_status": result.get("artifact_status"),
                  "physical_solve_count": result.get("physical_solve_count", 1),
                  "qa_status": result.get("qa_status"), "raw_sha256": result.get("raw_sha256"),
                  "raw_bytes": result.get("raw_bytes"), "deck_sha256": result.get("deck_sha256")}
        batch["runs"].append(record)
        batch["physical_solve_count_completed"] += int(result.get("physical_solve_count", 1))
        batch["status"] = "RUNNING" if code == 0 else "STOPPED_AFTER_ARTIFACT_FAILURE"
        jreplace(BATCH_MANIFEST, batch)
        _update_authorization_completed(batch["physical_solve_count_completed"])
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if code != 0:
            print("STOP: solver/raw/mechanical artifact failure; preserve evidence; no retry.",
                  file=sys.stderr, flush=True)
            return code

    analysis_script = SERIES / "scripts" / "analyze_cb_carry_buffer_all.py"
    proc = subprocess.run([sys.executable, str(analysis_script), "--write"], cwd=REPO,
                          check=False, timeout=600)
    if proc.returncode != 0:
        batch["status"] = "POSTPROCESS_FAILURE_RAW_PRESERVED"
        jreplace(BATCH_MANIFEST, batch)
        return proc.returncode
    summary = jread(TASK / "FULL_CB_CHAIN_SUMMARY.json")
    if summary.get("status") != "PASS":
        batch["status"] = "POSTPROCESS_FAILURE_RAW_PRESERVED"
        jreplace(BATCH_MANIFEST, batch)
        return 2
    batch.update({"status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "analysis_path": (TASK / "FULL_CB_CHAIN_SUMMARY.json").relative_to(SERIES).as_posix(),
                  "analysis_sha256": sha(TASK / "FULL_CB_CHAIN_SUMMARY.json"),
                  "scientific_interpretation_performed": False,
                  "automatic_follow_up": False})
    jreplace(BATCH_MANIFEST, batch)
    print(json.dumps({"status": batch["status"], "batch_id": BATCH_ID,
                      "run_ids": expected_ids,
                      "physical_solve_count": batch["physical_solve_count_completed"],
                      "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in batch["runs"]},
                      "scientific_interpretation_performed": False,
                      "automatic_follow_up": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def repair_analysis() -> int:
    """Repair the recorded postprocessor failure against the same three immutable raws."""
    batch = jread(BATCH_MANIFEST)
    if (batch.get("batch_id") != BATCH_ID or
            batch.get("status") != "POSTPROCESS_FAILURE_RAW_PRESERVED" or
            batch.get("physical_solve_count_completed") != 3 or
            [item.get("run_id") for item in batch.get("runs", [])] !=
            [item[0] for item in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX]):
        raise RuntimeError("analysis repair requires the completed A027-A029 postprocess-failure batch")
    incident = jread(TASK / "ANALYSIS_INCIDENT_001.json")
    if (incident.get("physical_solve_count_completed_before_and_after") != 3 or
            incident.get("raw_mutated") is not False or incident.get("solver_invoked_by_attempt") is not False):
        raise RuntimeError("analysis incident does not certify raw-preserving zero-solve repair scope")
    for record in batch["runs"]:
        run_id = record["run_id"]
        run_dir = RUNS / run_id
        result, qa, raw_qa = (jread(run_dir / filename) for filename in
                              ("result.json", "qa.json", "chain_qa.json"))
        raw = run_dir / "raw.csv"
        digest = sha(raw)
        if (digest != record.get("raw_sha256") or result.get("raw_sha256") != digest or
                result.get("artifact_status") != "VALID" or qa.get("status") != "PASS" or
                raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after_analysis") != digest):
            raise RuntimeError(f"raw/QA identity changed; analysis repair stopped: {run_id}")
    analyzer = SERIES / "scripts" / "analyze_cb_carry_buffer_all.py"
    print("ANALYSIS_REPAIR_ONLY: same A027-A029 immutable raw; solver_invoked=false", flush=True)
    proc = subprocess.run([sys.executable, str(analyzer), "--write", "--revision", "2"], cwd=REPO,
                          check=False, timeout=600)
    if proc.returncode != 0:
        return proc.returncode
    summary_path = TASK / "FULL_CB_CHAIN_SUMMARY_v2.json"
    summary = jread(summary_path)
    if summary.get("status") != "PASS" or summary.get("physical_solve_count") != 3:
        raise RuntimeError("repaired full-chain summary status/solve count invalid")
    batch.update({"status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "analysis_path": summary_path.relative_to(SERIES).as_posix(),
                  "analysis_sha256": sha(summary_path),
                  "analysis_revision": 2,
                  "analysis_incident_path": (TASK / "ANALYSIS_INCIDENT_001.json").relative_to(SERIES).as_posix(),
                  "analysis_incident_sha256": sha(TASK / "ANALYSIS_INCIDENT_001.json"),
                  "analysis_repair_runner_sha256": sha(analyzer),
                  "repair_solver_invoked": False,
                  "scientific_interpretation_performed": False, "automatic_follow_up": False})
    jreplace(BATCH_MANIFEST, batch)
    manifest = jread(EXPERIMENT_MANIFEST)
    auth = [item for item in manifest.get("authorization_batches", []) if item.get("batch_id") == BATCH_ID]
    if len(auth) != 1:
        raise RuntimeError("full-chain authorization record missing during postprocess repair")
    auth[0]["analysis_incident_path"] = batch["analysis_incident_path"]
    auth[0]["analysis_incident_sha256"] = batch["analysis_incident_sha256"]
    auth[0]["analysis_repair_runner_sha256"] = batch["analysis_repair_runner_sha256"]
    auth[0]["physical_solve_count_completed"] = 3
    jreplace(EXPERIMENT_MANIFEST, manifest)
    print(json.dumps({"status": batch["status"], "batch_id": BATCH_ID,
                      "physical_solve_count": 3, "solver_invoked": False,
                      "raw_sha256_by_run": {item["run_id"]: item["raw_sha256"] for item in batch["runs"]},
                      "analysis_sha256": batch["analysis_sha256"],
                      "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2), flush=True)
    return 0


def main() -> int:
    if sys.argv[1:] == ["--prepare-preflight"]:
        try:
            return prepare_preflight()
        except Exception as exc:
            print(f"PREFLIGHT_FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    if sys.argv[1:] == ["--run-batch"]:
        try:
            return run_batch()
        except Exception as exc:
            print(f"BATCH_STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    if sys.argv[1:] == ["--repair-analysis"]:
        try:
            return repair_analysis()
        except Exception as exc:
            print(f"ANALYSIS_REPAIR_STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    print("usage: cb_carry_buffer_all_batch.py --prepare-preflight | --run-batch | --repair-analysis", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
