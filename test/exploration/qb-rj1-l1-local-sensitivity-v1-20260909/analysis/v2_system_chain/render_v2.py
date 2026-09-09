#!/usr/bin/env python3
"""Generate the versioned V2 system-chain visualization from immutable raw."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[5]
EXP = Path(__file__).resolve().parents[2]
V2_ANALYSIS = EXP / "analysis/v2_system_chain"
V2_PLOTS = EXP / "plots/v2_system_chain"
V21_ANALYSIS = V2_ANALYSIS / "v2_1"
V21_PLOTS = V2_PLOTS / "v2_1"
PLOT2 = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


RUNS = {
    "NOMINAL": ("nominal", 12.0, 2.0),
    "L1_DOWN": ("l1_down", 12.0, 1.9),
    "L1_UP": ("l1_up", 12.0, 2.1),
    "RJ1_UP_05": ("rj1_up_05", 12.5, 2.0),
    "RJ1_UP_10": ("rj1_up_10", 13.0, 2.0),
}
FAMILIES = {
    "L1": ["L1_DOWN", "NOMINAL", "L1_UP"],
    "RJ1": ["NOMINAL", "RJ1_UP_05", "RJ1_UP_10"],
}

STANDALONE_WINDOWS = {
    "01_SIGNAL_TIMING": {"FULL_0_200ps": (0.0, 200.0), "FINAL_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0)},
    "02_BVM_STATE": {"STATE_90_140ps": (90.0, 140.0), "FINAL_101_135ps": (101.0, 135.0)},
    "03_JSL_CHAIN": {"CHAIN_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0)},
    "04_QB_STATE": {"STATE_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0), "QB_110_130ps": (110.0, 130.0)},
    "05_JTL_CHAIN": {"CHAIN_110_140ps": (110.0, 140.0)},
}
COMPARISON_WINDOWS = {
    "01_SIGNAL_TIMING": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0)},
    "02_BVM_STATE": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0)},
    "03_JSL_CHAIN": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0)},
    "04_QB_STATE": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0), "QB_110_130ps": (110.0, 130.0)},
    "05_JTL_CHAIN": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0), "QB_JTL_110_130ps": (110.0, 130.0)},
}


def raw_path(run_id: str) -> Path:
    return EXP / "runs" / RUNS[run_id][0] / "raw.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_raw_tokens(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        return next(reader), list(reader)


def add_pvi(labels: list[str], name: str) -> None:
    labels.extend((f"P({name})", f"V({name})", f"I({name})"))


def add_iv(labels: list[str], name: str) -> None:
    labels.extend((f"I({name})", f"V({name})"))


def category_labels() -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {}
    timing = ["I(I_WL1)", "I(I_BL1)", "I(I_SE1)"]
    timing.extend(f"I(I_{control}{instance})" for instance in range(2, 5) for control in ("WL", "BL", "SE"))
    timing.extend(["I(L_SL|XBVM1)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)"])
    timing.extend(f"V(JTL{stage}_OUT)" for stage in range(1, 7))
    timing.append("I(R_TERM)")
    labels["01_SIGNAL_TIMING"] = timing

    bvm: list[str] = []
    for jj in ("B_JM1", "B_JM2"):
        add_pvi(bvm, f"{jj}|XBVM1")
    for branch in ("L_M1", "L_M2", "L_M3", "L_PM"):
        add_iv(bvm, f"{branch}|XBVM1")
    for jj in ("B_JS1", "B_JS2"):
        add_pvi(bvm, f"{jj}|XBVM1")
    for branch in ("L_S1", "L_S2", "L_S3", "R_S", "L_PSL", "R_SL", "L_SL"):
        add_iv(bvm, f"{branch}|XBVM1")
    for instance in range(2, 5):
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            bvm.append(f"P({jj}|XBVM{instance})")
        bvm.extend((f"I(L_PM|XBVM{instance})", f"I(L_SL|XBVM{instance})"))
    labels["02_BVM_STATE"] = bvm

    jsl: list[str] = []
    for quantity in ("P", "V", "I"):
        jsl.extend(f"{quantity}(B_JSL{index})" for index in range(1, 9))
    labels["03_JSL_CHAIN"] = jsl

    qb: list[str] = ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)"]
    qb.extend(("P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)"))
    qb.extend(("P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)"))
    qb.extend(("I(L1|XBQ1)", "V(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "V(IB|XBQ1)"))
    qb.extend(("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "V(RJ2|XBQ1)"))
    qb.extend(("I(L3|XBQ1)", "V(L3|XBQ1)", "V(QBOUT)"))
    labels["04_QB_STATE"] = qb

    jtl: list[str] = []
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        for jj in ("B01", "B02"):
            jtl.extend((f"P({jj}|{h})", f"V({jj}|{h})", f"I({jj}|{h})"))
        jtl.append(f"V(JTL{stage}_OUT)")
    jtl.extend(("I(R_TERM)", "V(JTL6_OUT)"))
    labels["05_JTL_CHAIN"] = jtl
    return labels


CATEGORY_LABELS = category_labels()


def snapshot_historical() -> dict[str, object]:
    excluded = (V2_ANALYSIS.resolve(), V2_PLOTS.resolve())
    records = {}
    for path in EXP.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if any(resolved == root or root in resolved.parents for root in excluded):
            continue
        records[str(path.relative_to(EXP))] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    raw_qa = json.loads((EXP / "analysis/raw_qa.json").read_text(encoding="utf-8"))
    raw = {run_id: {"path": str(raw_path(run_id)), "sha256": raw_qa["post_analysis_sha256"][run_id]} for run_id in RUNS}
    return {
        "schema": "qb-rj1-l1-local-sensitivity-v2-raw-reference-v1",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment_id": EXP.name,
        "raw_authority": raw,
        "historical_snapshot_before_v2": records,
        "old_result_brief_sha256": sha256(EXP / "RESULT_BRIEF.md"),
        "old_visualization_manifest_sha256": sha256(EXP / "analysis/visualization_manifest.json"),
        "v2_read_only_scope": True,
    }


def ensure_raw_reference() -> dict[str, object]:
    path = V2_ANALYSIS / "raw_reference.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    record = snapshot_historical()
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def display_label(run_id: str, label: str) -> str:
    # Keep the first character P/V/I so josim-plot2 assigns the correct axis.
    return f"{label[0]}({run_id}|{label})"


def make_view_csv(run_ids: list[str], labels: list[str], window: tuple[float, float], output: Path, *, comparison: bool) -> dict[str, object]:
    raw_data = {}
    for run_id in run_ids:
        path = raw_path(run_id)
        header, rows = read_raw_tokens(path)
        trace = read_csv(path)
        if len(set(header)) != len(header):
            raise RuntimeError(f"duplicate raw headers: {path}")
        if len(rows) != trace.sample_count:
            raise RuntimeError(f"raw token/sample mismatch: {path}")
        raw_data[run_id] = {"path": path, "header": header, "rows": rows, "trace": trace, "positions": {name: index for index, name in enumerate(header)}}
    base_time = [row[0] for row in raw_data[run_ids[0]]["rows"]]
    for run_id in run_ids[1:]:
        if [row[0] for row in raw_data[run_id]["rows"]] != base_time:
            raise RuntimeError(f"exact time grid mismatch in comparison: {run_id}")
    actual_by_run = {}
    missing_by_run = {}
    for run_id in run_ids:
        positions = raw_data[run_id]["positions"]
        actual_by_run[run_id] = [label for label in labels if label in positions]
        missing_by_run[run_id] = [label for label in labels if label not in positions]
    phase_values = {}
    for run_id in run_ids:
        trace = raw_data[run_id]["trace"]
        phase_values[run_id] = {label: continuous_unwrap(tuple(trace.column(label))) for label in actual_by_run[run_id] if label.startswith("P(")}
    selected_labels = [label for label in labels if all(label in actual_by_run[run_id] for run_id in run_ids)]
    output_header = ["time"]
    if comparison:
        output_header.extend(display_label(run_id, label) for label in selected_labels for run_id in run_ids)
    else:
        output_header.extend(selected_labels)
    output_rows = []
    for index, time_token in enumerate(base_time):
        time_ps = float(time_token) * 1e12
        if not (window[0] <= time_ps < window[1]):
            continue
        row = [time_token]
        if comparison:
            for label in selected_labels:
                for run_id in run_ids:
                    pos = raw_data[run_id]["positions"][label]
                    if label.startswith("P("):
                        value = phase_values[run_id][label][index]
                        row.append(f"{value:.17g}")
                    else:
                        row.append(raw_data[run_id]["rows"][index][pos])
        else:
            for label in selected_labels:
                pos = raw_data[run_ids[0]]["positions"][label]
                if label.startswith("P("):
                    row.append(f"{phase_values[run_ids[0]][label][index]:.17g}")
                else:
                    row.append(raw_data[run_ids[0]]["rows"][index][pos])
        output_rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(output_header)
        writer.writerows(output_rows)
    return {
        "selected_original_labels": selected_labels,
        "missing_by_run": missing_by_run,
        "output_header": output_header,
        "sample_count": len(output_rows),
        "time_start_ps": float(output_rows[0][0]) * 1e12 if output_rows else None,
        "time_end_ps": float(output_rows[-1][0]) * 1e12 if output_rows else None,
        "phase_labels_independently_unwrapped": [label for label in selected_labels if label.startswith("P(")],
    }


def run_plot2(input_csv: Path, output_html: Path, labels: list[str], title: str) -> list[str]:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOT2), str(input_csv), "-x", str(output_html), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    subprocess.run(command, cwd=REPO, check=True)
    return command


def entry(stage: str, mode: str, category: str, window_name: str, window: tuple[float, float], run_ids: list[str], input_csv: Path, output_html: Path, command: list[str], view: dict[str, object]) -> dict[str, object]:
    phase = view["phase_labels_independently_unwrapped"]
    return {
        "stage": stage,
        "mode": mode,
        "category": category,
        "window_name": window_name,
        "window_ps": list(window),
        "run_ids": run_ids,
        "input_csv": str(input_csv),
        "input_sha256": sha256(input_csv),
        "output_path": str(output_html),
        "output_sha256": sha256(output_html),
        "command": command,
        "signal_order_requested": CATEGORY_LABELS[category],
        "signal_order_actual": view["selected_original_labels"],
        "missing_signals_by_run": view["missing_by_run"],
        "sample_count": view["sample_count"],
        "actual_window_first_ps": view["time_start_ps"],
        "actual_window_last_ps": view["time_end_ps"],
        "source_raw_paths": [str(raw_path(run_id)) for run_id in run_ids],
        "source_raw_sha256": [sha256(raw_path(run_id)) for run_id in run_ids],
        "units": {"time": "seconds in CSV; declared window in ps", "P": "raw rad in source; independently unwrapped then plot2 displays rad/(2*pi) turns", "I": "A", "V": "V"},
        "phase_convention": "independent continuous unwrap per run before rad/(2*pi) display; never SFQ count",
        "transformation": "exact half-open stored-row window slice; P columns independently unwrapped for display only; no interpolation/resampling/smoothing/filtering/alignment",
        "renderer": str(PLOT2),
    }


def render_stage(stage: str) -> list[dict[str, object]]:
    raw_reference = ensure_raw_reference()
    if stage == "comparison":
        qa = V2_ANALYSIS / "visualization_qa_standalone.json"
        if not qa.is_file() or json.loads(qa.read_text(encoding="utf-8")).get("status") != "PASS":
            raise RuntimeError("standalone V2 visualization QA must PASS before comparison rendering")
        previous = json.loads((V2_ANALYSIS / "manifest_standalone.json").read_text(encoding="utf-8"))
        entries = list(previous["standalone_entries"])
        for family, run_ids in FAMILIES.items():
            for category, windows in COMPARISON_WINDOWS.items():
                for window_name, window in windows.items():
                    input_csv = V2_ANALYSIS / "derived" / "comparison" / family.lower() / category / f"{window_name}.csv"
                    view = make_view_csv(run_ids, CATEGORY_LABELS[category], window, input_csv, comparison=True)
                    selected = [display_label(run_id, label) for label in view["selected_original_labels"] for run_id in run_ids]
                    output_html = V2_PLOTS / f"compare_{family.lower()}" / category / f"{window_name}.html"
                    command = run_plot2(input_csv, output_html, selected, f"{family} {category} {window_name}; same signal order; raw/independently unwrapped display")
                    entries.append(entry("comparison", "comparison", category, window_name, window, run_ids, input_csv, output_html, command, view))
        manifest = {
            "schema": "qb-rj1-l1-local-sensitivity-v2-system-chain-manifest-v1",
            "experiment_id": EXP.name,
            "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "raw_reference_path": str(V2_ANALYSIS / "raw_reference.json"),
            "standalone_entries": previous["standalone_entries"],
            "comparison_entries": entries[len(previous["standalone_entries"]):],
            "jsl_current_consistency_path": str(V2_ANALYSIS / "jsl_current_consistency.json"),
            "no_new_physical_solve": True,
            "status": "PASS",
        }
        (V2_ANALYSIS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return entries
    entries = []
    for run_id, (directory, _, _) in RUNS.items():
        for category, windows in STANDALONE_WINDOWS.items():
            for window_name, window in windows.items():
                input_csv = V2_ANALYSIS / "derived" / "standalone" / directory / category / f"{window_name}.csv"
                view = make_view_csv([run_id], CATEGORY_LABELS[category], window, input_csv, comparison=False)
                selected = view["selected_original_labels"]
                output_html = V2_PLOTS / "standalone" / directory / category / f"{window_name}.html"
                command = run_plot2(input_csv, output_html, selected, f"{run_id} {category} {window_name}; system-chain raw view")
                entries.append(entry("standalone", "standalone", category, window_name, window, [run_id], input_csv, output_html, command, view))
    manifest = {
        "schema": "qb-rj1-l1-local-sensitivity-v2-system-chain-standalone-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "raw_reference_path": str(V2_ANALYSIS / "raw_reference.json"),
        "standalone_entries": entries,
        "no_new_physical_solve": True,
        "status": "PASS",
    }
    (V2_ANALYSIS / "manifest_standalone.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return entries


def write_jsl_consistency() -> None:
    windows = {"FULL_0_200ps": (0.0, 200.0), "CHAIN_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0)}
    result = {
        "schema": "qb-rj1-l1-local-sensitivity-v2-jsl-current-consistency-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "formula": "max_t |I(B_JSLk,t)-I(B_JSL1,t)| for k=2..8",
        "unit": "A (display uA)",
        "raw_only": True,
        "not_an_sfq_criterion": True,
        "runs": {},
    }
    for run_id in RUNS:
        trace = read_csv(raw_path(run_id))
        currents = {index: tuple(trace.column(f"I(B_JSL{index})")) for index in range(1, 9)}
        result["runs"][run_id] = {}
        for name, (start_ps, end_ps) in windows.items():
            indices = tuple(index for index, value in enumerate(trace.time) if start_ps * 1e-12 <= value < end_ps * 1e-12)
            result["runs"][run_id][name] = {
                f"JSL{index}_minus_JSL1": {
                    "max_abs_A": max(abs(currents[index][row] - currents[1][row]) for row in indices),
                    "max_abs_uA": max(abs(currents[index][row] - currents[1][row]) for row in indices) * 1e6,
                }
                for index in range(2, 9)
            }
    (V2_ANALYSIS / "jsl_current_consistency.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def v21_signal(display: str, raw: str | None = None) -> dict[str, str]:
    return {"display": display, "raw": raw if raw is not None else display}


def v21_pvi(name: str) -> list[dict[str, str]]:
    return [v21_signal(f"{quantity}({name})") for quantity in ("P", "V", "I")]


def v21_iv(name: str) -> list[dict[str, str]]:
    return [v21_signal(f"I({name})"), v21_signal(f"V({name})")]


def v21_category_specs() -> tuple[dict[str, list[dict[str, str]]], dict[str, dict[str, list[dict[str, str]]]]]:
    """Return ordered semantic groups for V2.1.

    Boundary aliases deliberately make repeated JSL boundary tracks unique in
    the derived CSV while retaining the exact raw source label in ``raw``.
    """
    categories: dict[str, list[dict[str, str]]] = {}
    semantics: dict[str, dict[str, list[dict[str, str]]]] = {}

    timing_input = [v21_signal(f"I(I_{control}{instance})") for instance in range(1, 5) for control in ("WL", "BL", "SE")]
    timing_internal = [v21_signal("I(L_SL|XBVM1)"), v21_signal("I(B_JSL8)")]
    timing_output = [v21_signal("V(QBIN)"), v21_signal("V(QBOUT)")]
    timing_output += [v21_signal(f"V(JTL{stage}_OUT)") for stage in range(1, 7)]
    timing_output.append(v21_signal("I(R_TERM)"))
    semantics["01_SIGNAL_TIMING"] = {"input_boundary": timing_input, "internal_state": timing_internal, "output_boundary": timing_output}
    categories["01_SIGNAL_TIMING"] = timing_input + timing_internal + timing_output

    bvm_input = [v21_signal(f"I(I_{control}{instance})") for instance in range(1, 5) for control in ("WL", "BL", "SE")]
    bvm_internal: list[dict[str, str]] = []
    for jj in ("B_JM1", "B_JM2"):
        bvm_internal += v21_pvi(f"{jj}|XBVM1")
    for branch in ("L_M1", "L_M2", "L_M3", "L_PM"):
        bvm_internal += v21_iv(f"{branch}|XBVM1")
    for jj in ("B_JS1", "B_JS2"):
        bvm_internal += v21_pvi(f"{jj}|XBVM1")
    for branch in ("L_S1", "L_S2", "L_S3", "R_S", "L_PSL", "R_SL"):
        bvm_internal += v21_iv(f"{branch}|XBVM1")
    for instance in range(2, 5):
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            bvm_internal.append(v21_signal(f"P({jj}|XBVM{instance})"))
        bvm_internal += [v21_signal(f"I(L_PM|XBVM{instance})"), v21_signal(f"I(L_SL|XBVM{instance})")]
    # Quiet-cell L_SL currents remain in the internal shared-bus context above;
    # keep BVM_OUT as the explicit active-target boundary plus COMMON_SL.
    bvm_output = [v21_signal("I(L_SL|XBVM1)"), v21_signal("V(L_SL|XBVM1)"), v21_signal("V(COMMON_SL)")]
    semantics["02_BVM_STATE"] = {"input_boundary": bvm_input, "internal_state": bvm_internal, "output_boundary": bvm_output}
    categories["02_BVM_STATE"] = bvm_input + bvm_internal + bvm_output

    jsl_input = [v21_signal("V(COMMON_SL)"), v21_signal("I(JSL_INPUT|B_JSL1)", "I(B_JSL1)")]
    jsl_internal: list[dict[str, str]] = []
    for index in range(1, 9):
        jsl_internal += v21_pvi(f"B_JSL{index}")
    jsl_output = [v21_signal("I(JSL_OUTPUT|B_JSL8)", "I(B_JSL8)"), v21_signal("V(QBIN)")]
    semantics["03_JSL_CHAIN"] = {"input_boundary": jsl_input, "internal_state": jsl_internal, "output_boundary": jsl_output}
    categories["03_JSL_CHAIN"] = jsl_input + jsl_internal + jsl_output

    qb_input = [v21_signal("V(QBIN)"), v21_signal("I(LIN|XBQ1)"), v21_signal("V(LIN|XBQ1)")]
    qb_input += v21_pvi("BJS|XBQ1")
    qb_internal = v21_pvi("BJ1|XBQ1") + v21_iv("RJ1|XBQ1")
    qb_internal += v21_iv("L1|XBQ1") + [v21_signal("I(IB|XBQ1)"), v21_signal("V(IB|XBQ1)")]
    qb_internal += v21_iv("L2|XBQ1") + v21_pvi("BJ2|XBQ1") + v21_iv("RJ2|XBQ1")
    qb_output = v21_iv("L3|XBQ1") + [v21_signal("V(QBOUT)"), v21_signal("P(B01|XJTL1_1)"), v21_signal("V(B01|XJTL1_1)"), v21_signal("I(B01|XJTL1_1)")]
    semantics["04_QB_STATE"] = {"input_boundary": qb_input, "internal_state": qb_internal, "output_boundary": qb_output}
    categories["04_QB_STATE"] = qb_input + qb_internal + qb_output

    jtl_input = [v21_signal("V(QBOUT)")]
    jtl_internal: list[dict[str, str]] = []
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        for jj in ("B01", "B02"):
            jtl_internal += v21_pvi(f"{jj}|{h}")
        if stage < 6:
            jtl_internal.append(v21_signal(f"V(JTL{stage}_OUT)"))
    jtl_output = [v21_signal("V(JTL6_OUT)"), v21_signal("I(R_TERM)")]
    semantics["05_JTL_CHAIN"] = {"input_boundary": jtl_input, "internal_state": jtl_internal, "output_boundary": jtl_output}
    categories["05_JTL_CHAIN"] = jtl_input + jtl_internal + jtl_output
    return categories, semantics


V21_CATEGORY_LABELS, V21_SEMANTICS = v21_category_specs()
V21_STANDALONE_WINDOWS = {
    "01_SIGNAL_TIMING": {"OVERVIEW_0_200ps": (0.0, 200.0), "FINAL_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0)},
    "02_BVM_STATE": {"OVERVIEW_0_200ps": (0.0, 200.0), "STATE_90_140ps": (90.0, 140.0), "FINAL_101_135ps": (101.0, 135.0)},
    "03_JSL_CHAIN": {"OVERVIEW_0_200ps": (0.0, 200.0), "CHAIN_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0)},
    "04_QB_STATE": {"OVERVIEW_0_200ps": (0.0, 200.0), "STATE_101_135ps": (101.0, 135.0), "READ_110_121ps": (110.0, 121.0), "QB_110_130ps": (110.0, 130.0)},
    "05_JTL_CHAIN": {"OVERVIEW_0_200ps": (0.0, 200.0), "CHAIN_110_140ps": (110.0, 140.0)},
}
V21_COMPARISON_WINDOWS = {
    "01_SIGNAL_TIMING": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0)},
    "02_BVM_STATE": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0)},
    "03_JSL_CHAIN": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0)},
    "04_QB_STATE": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0), "QB_110_130ps": (110.0, 130.0)},
    "05_JTL_CHAIN": {"OVERVIEW_0_200ps": (0.0, 200.0), "SYSTEM_CRITICAL_101_135ps": (101.0, 135.0), "FINAL_READ_110_121ps": (110.0, 121.0), "QB_JTL_110_130ps": (110.0, 130.0)},
}


def v21_display_label(run_id: str, display: str) -> str:
    return f"{display[0]}({run_id}|{display})"


def ensure_v21_raw_reference() -> dict[str, object]:
    path = V21_ANALYSIS / "raw_reference.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    parent_manifest = V2_ANALYSIS / "manifest.json"
    parent_reference = V2_ANALYSIS / "raw_reference.json"
    raw_qa = json.loads((EXP / "analysis/raw_qa.json").read_text(encoding="utf-8"))
    record = {
        "schema": "qb-rj1-l1-local-sensitivity-v2-1-raw-reference-v1",
        "version": "V2.1",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment_id": EXP.name,
        "parent_v2_manifest": {"path": str(parent_manifest), "sha256": sha256(parent_manifest)},
        "parent_v2_raw_reference": {"path": str(parent_reference), "sha256": sha256(parent_reference)},
        "raw_authority": {run_id: {"path": str(raw_path(run_id)), "sha256_before_v21": raw_qa["post_analysis_sha256"][run_id], "sha256_at_v21_start": sha256(raw_path(run_id))} for run_id in RUNS},
        "historical_preservation_source": str(parent_reference),
        "read_only_scope": True,
        "physics_solve_count": 0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def make_v21_view_csv(run_ids: list[str], specs: list[dict[str, str]], window: tuple[float, float], output: Path, *, comparison: bool) -> dict[str, object]:
    raw_data = {}
    for run_id in run_ids:
        path = raw_path(run_id)
        header, rows = read_raw_tokens(path)
        trace = read_csv(path)
        if len(set(header)) != len(header):
            raise RuntimeError(f"duplicate raw headers: {path}")
        raw_data[run_id] = {"path": path, "header": header, "rows": rows, "trace": trace, "positions": {name: index for index, name in enumerate(header)}}
    base_times = [row[0] for row in raw_data[run_ids[0]]["rows"]]
    for run_id in run_ids[1:]:
        if [row[0] for row in raw_data[run_id]["rows"]] != base_times:
            raise RuntimeError(f"exact time grid mismatch in V2.1 comparison: {run_id}")
    actual_by_run = {}
    missing_by_run = {}
    for run_id in run_ids:
        positions = raw_data[run_id]["positions"]
        actual_by_run[run_id] = [spec for spec in specs if spec["raw"] in positions]
        missing_by_run[run_id] = [{"display": spec["display"], "raw": spec["raw"]} for spec in specs if spec["raw"] not in positions]
    selected_specs = [spec for spec in specs if all(spec in actual_by_run[run_id] for run_id in run_ids)]
    phase_values = {}
    for run_id in run_ids:
        trace = raw_data[run_id]["trace"]
        phase_values[run_id] = {spec["raw"]: continuous_unwrap(tuple(trace.column(spec["raw"]))) for spec in selected_specs if spec["raw"].startswith("P(")}
    output_header = ["time"]
    if comparison:
        output_header.extend(v21_display_label(run_id, spec["display"]) for spec in selected_specs for run_id in run_ids)
    else:
        output_header.extend(spec["display"] for spec in selected_specs)
    output_rows = []
    for index, token in enumerate(base_times):
        time_ps = float(token) * 1e12
        if not (window[0] <= time_ps < window[1]):
            continue
        row = [token]
        if comparison:
            for spec in selected_specs:
                for run_id in run_ids:
                    pos = raw_data[run_id]["positions"][spec["raw"]]
                    row.append(f"{phase_values[run_id][spec['raw']][index]:.17g}" if spec["raw"].startswith("P(") else raw_data[run_id]["rows"][index][pos])
        else:
            for spec in selected_specs:
                pos = raw_data[run_ids[0]]["positions"][spec["raw"]]
                row.append(f"{phase_values[run_ids[0]][spec['raw']][index]:.17g}" if spec["raw"].startswith("P(") else raw_data[run_ids[0]]["rows"][index][pos])
        output_rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(output_header)
        writer.writerows(output_rows)
    return {
        "selected_specs": selected_specs,
        "selected_original_labels": [spec["raw"] for spec in selected_specs],
        "selected_display_labels": [spec["display"] for spec in selected_specs],
        "missing_by_run": missing_by_run,
        "output_header": output_header,
        "sample_count": len(output_rows),
        "time_start_ps": float(output_rows[0][0]) * 1e12 if output_rows else None,
        "time_end_ps": float(output_rows[-1][0]) * 1e12 if output_rows else None,
        "phase_labels_independently_unwrapped": [spec["display"] for spec in selected_specs if spec["raw"].startswith("P(")],
    }


def v21_entry(stage: str, mode: str, category: str, window_name: str, window: tuple[float, float], run_ids: list[str], input_csv: Path, output_html: Path, command: list[str], view: dict[str, object]) -> dict[str, object]:
    return {
        "version": "V2.1",
        "stage": stage,
        "mode": mode,
        "category": category,
        "window_name": window_name,
        "window_ps": list(window),
        "run_ids": run_ids,
        "input_csv": str(input_csv),
        "input_sha256": sha256(input_csv),
        "output_path": str(output_html),
        "output_sha256": sha256(output_html),
        "command": command,
        "signal_order_requested": [spec["display"] for spec in V21_CATEGORY_LABELS[category]],
        "signal_order_actual": view["selected_display_labels"],
        "signal_raw_labels_actual": view["selected_original_labels"],
        "semantic_groups": {group: [spec["display"] for spec in specs] for group, specs in V21_SEMANTICS[category].items()},
        "missing_signals_by_run": view["missing_by_run"],
        "sample_count": view["sample_count"],
        "actual_window_first_ps": view["time_start_ps"],
        "actual_window_last_ps": view["time_end_ps"],
        "source_raw_paths": [str(raw_path(run_id)) for run_id in run_ids],
        "source_raw_sha256": [sha256(raw_path(run_id)) for run_id in run_ids],
        "units": {"time": "seconds in CSV; declared window in ps", "P": "raw rad in source; independently unwrapped then plot2 displays rad/(2*pi) turns", "I": "A", "V": "V"},
        "phase_convention": "independent continuous unwrap per run before rad/(2*pi) display; never SFQ count",
        "transformation": "exact half-open stored-row window slice; P columns independently unwrapped for display only; no interpolation/resampling/smoothing/filtering/alignment",
        "renderer": str(PLOT2),
    }


def render_v21(stage: str) -> int:
    reference = ensure_v21_raw_reference()
    raw_before = {run_id: sha256(raw_path(run_id)) for run_id in RUNS}
    if stage == "comparison":
        qa_path = V21_ANALYSIS / "visualization_qa_standalone.json"
        if not qa_path.is_file() or json.loads(qa_path.read_text(encoding="utf-8")).get("status") != "PASS":
            raise RuntimeError("V2.1 standalone QA must PASS before comparison rendering")
        previous = json.loads((V21_ANALYSIS / "manifest_standalone.json").read_text(encoding="utf-8"))
        comparison_entries = []
        for family, run_ids in FAMILIES.items():
            for category, windows in V21_COMPARISON_WINDOWS.items():
                for window_name, window in windows.items():
                    input_csv = V21_ANALYSIS / "derived" / "comparison" / family.lower() / category / f"{window_name}.csv"
                    view = make_v21_view_csv(run_ids, V21_CATEGORY_LABELS[category], window, input_csv, comparison=True)
                    selected = [v21_display_label(run_id, spec["display"]) for spec in view["selected_specs"] for run_id in run_ids]
                    output = V21_PLOTS / f"compare_{family.lower()}" / category / f"{window_name}.html"
                    command = run_plot2(input_csv, output, selected, f"V2.1 {family} {category} {window_name}; INPUT -> INTERNAL -> OUTPUT")
                    comparison_entries.append(v21_entry("comparison", "comparison", category, window_name, window, run_ids, input_csv, output, command, view))
        manifest = {
            "schema": "qb-rj1-l1-local-sensitivity-v2-1-system-chain-manifest-v1",
            "version": "V2.1",
            "experiment_id": EXP.name,
            "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "parent_v2_manifest": reference["parent_v2_manifest"],
            "parent_v2_raw_reference": reference["parent_v2_raw_reference"],
            "semantic_completeness": {category: {group: [spec["display"] for spec in specs] for group, specs in groups.items()} for category, groups in V21_SEMANTICS.items()},
            "standalone_entries": previous["standalone_entries"],
            "comparison_entries": comparison_entries,
            "physics_solve_count": 0,
            "status": "PASS",
        }
        (V21_ANALYSIS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_v21_run_summaries()
        entries = previous["standalone_entries"] + comparison_entries
    else:
        entries = []
        for run_id, (directory, _, _) in RUNS.items():
            for category, windows in V21_STANDALONE_WINDOWS.items():
                for window_name, window in windows.items():
                    input_csv = V21_ANALYSIS / "derived" / "standalone" / directory / category / f"{window_name}.csv"
                    view = make_v21_view_csv([run_id], V21_CATEGORY_LABELS[category], window, input_csv, comparison=False)
                    output = V21_PLOTS / "standalone" / directory / category / f"{window_name}.html"
                    command = run_plot2(input_csv, output, view["selected_display_labels"], f"V2.1 {run_id} {category} {window_name}; INPUT -> INTERNAL -> OUTPUT")
                    entries.append(v21_entry("standalone", "standalone", category, window_name, window, [run_id], input_csv, output, command, view))
        manifest = {
            "schema": "qb-rj1-l1-local-sensitivity-v2-1-system-chain-standalone-manifest-v1",
            "version": "V2.1",
            "experiment_id": EXP.name,
            "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "parent_v2_manifest": reference["parent_v2_manifest"],
            "parent_v2_raw_reference": reference["parent_v2_raw_reference"],
            "semantic_completeness": {category: {group: [spec["display"] for spec in specs] for group, specs in groups.items()} for category, groups in V21_SEMANTICS.items()},
            "standalone_entries": entries,
            "physics_solve_count": 0,
            "status": "PASS",
        }
        (V21_ANALYSIS / "manifest_standalone.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raw_after = {run_id: sha256(raw_path(run_id)) for run_id in RUNS}
    if raw_before != raw_after:
        raise RuntimeError("raw hash changed during V2.1 rendering")
    print(json.dumps({"status": "PASS", "version": "V2.1", "stage": stage, "entry_count": len(entries), "raw_unchanged": True}, ensure_ascii=False))
    return 0


def write_v21_run_summaries() -> None:
    summary_dir = V21_ANALYSIS / "run_summaries"
    for run_id, (directory, rj1, l1) in RUNS.items():
        base = "../../../plots/v2_system_chain/v2_1"
        text = f"""# {run_id} — V2.1 system-chain summary\n\nV2.1 is a read-only presentation revision; RJ1={rj1:g} ohm, L1={l1:g} pH.\n\n## 1. SIGNAL_TIMING\n\n[overview]({base}/standalone/{directory}/01_SIGNAL_TIMING/OVERVIEW_0_200ps.html) · [final]({base}/standalone/{directory}/01_SIGNAL_TIMING/FINAL_101_135ps.html) · [read]({base}/standalone/{directory}/01_SIGNAL_TIMING/READ_110_121ps.html)\n\n## 2. BVM_STATE\n\n[overview]({base}/standalone/{directory}/02_BVM_STATE/OVERVIEW_0_200ps.html) · [state]({base}/standalone/{directory}/02_BVM_STATE/STATE_90_140ps.html) · [final]({base}/standalone/{directory}/02_BVM_STATE/FINAL_101_135ps.html)\n\n## 3. JSL_CHAIN\n\n[overview]({base}/standalone/{directory}/03_JSL_CHAIN/OVERVIEW_0_200ps.html) · [chain]({base}/standalone/{directory}/03_JSL_CHAIN/CHAIN_101_135ps.html) · [read]({base}/standalone/{directory}/03_JSL_CHAIN/READ_110_121ps.html)\n\n## 4. QB_STATE\n\n[overview]({base}/standalone/{directory}/04_QB_STATE/OVERVIEW_0_200ps.html) · [state]({base}/standalone/{directory}/04_QB_STATE/STATE_101_135ps.html) · [read]({base}/standalone/{directory}/04_QB_STATE/READ_110_121ps.html) · [110–130 ps]({base}/standalone/{directory}/04_QB_STATE/QB_110_130ps.html)\n\n## 5. JTL_CHAIN\n\n[overview]({base}/standalone/{directory}/05_JTL_CHAIN/OVERVIEW_0_200ps.html) · [chain]({base}/standalone/{directory}/05_JTL_CHAIN/CHAIN_110_140ps.html)\n\n## 6. OBSERVED\n\nV2.1 exposes INPUT -> INTERNAL -> OUTPUT boundaries in each subsystem view. Existing metric values are unchanged.\n\n## 7. UNKNOWN\n\nV2.1 does not add event detection or physical interpretation. `V(IB|XBQ1)` remains un-emitted/UNKNOWN, and system-level classification remains UNKNOWN/INCONCLUSIVE.\n"""
        summary_dir.mkdir(parents=True, exist_ok=True)
        (summary_dir / f"{run_id}.md").write_text(text, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"standalone", "comparison", "v2_1_standalone", "v2_1_comparison"}:
        raise SystemExit("usage: render_v2.py {standalone|comparison|v2_1_standalone|v2_1_comparison}")
    if sys.argv[1].startswith("v2_1_"):
        return render_v21("standalone" if sys.argv[1] == "v2_1_standalone" else "comparison")
    raw_before = {run_id: sha256(raw_path(run_id)) for run_id in RUNS}
    if sys.argv[1] == "standalone":
        write_jsl_consistency()
    entries = render_stage(sys.argv[1])
    raw_after = {run_id: sha256(raw_path(run_id)) for run_id in RUNS}
    if raw_before != raw_after:
        raise RuntimeError("raw hash changed during V2 rendering")
    print(json.dumps({"status": "PASS", "stage": sys.argv[1], "entry_count": len(entries), "raw_unchanged": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
