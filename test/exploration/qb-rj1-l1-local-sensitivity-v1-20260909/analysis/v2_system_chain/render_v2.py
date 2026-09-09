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


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"standalone", "comparison"}:
        raise SystemExit("usage: render_v2.py {standalone|comparison}")
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
