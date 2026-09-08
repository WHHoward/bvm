#!/usr/bin/env python3
"""Independent checker for the delta4_v2 visualization package.

This checker uses only the standard library. It rereads N4/intervention raw
files, independently unwraps phase, and recomputes pairwise CSV deltas.
It never invokes JoSIM and never changes raw or visualization files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = REPO / "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907"
OLD = EXP
NEW = REPO / "test/exploration/bvmsim-jm2-delta4-replay-sensitivity-v1-20260908"
V2_MANIFEST = NEW / "analysis/visualization_manifest_v2.json"
V2_QA = NEW / "analysis/viz_qa_v2.json"
RUNS = (
    "DELTA4_DELAY_3PS",
    "DELTA4_DELAY_6PS",
    "DELTA4_GAIN_1P25",
    "DELTA4_GAIN_1P50",
)
RAW_PATHS = {
    "N4_REPLAY": OLD / "runs/n4_replay/raw.csv",
    **{run_id: NEW / "runs" / run_id / "raw.csv" for run_id in RUNS},
}
EXPECTED_RAW_HASHES = {
    "N4_REPLAY": "5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28",
    "DELTA4_DELAY_3PS": "da0239d7134be2c212f6de07fe99b609a55fee01bcab27c30b0b3b601a11278a",
    "DELTA4_DELAY_6PS": "285078256918fda077767fc4368dcdd394f86cc36641789a25c31f2ffa1691b6",
    "DELTA4_GAIN_1P25": "9a20400bde72c81f45f3ca8f72fc7b560298cc8ee1be1f2e542d52f2360429ba",
    "DELTA4_GAIN_1P50": "624a67de1d9e19f3a9f863122adcc72fbf7eb3209af2b068d17563243a89bf36",
}
EXPECTED_SOURCE_HASHES = {
    "N3_PASSIVE": "f966077641779f90c5043bf7f5d9a4beaba9b13214977cc26cb399e1f6d90273",
    "N4_PASSIVE": "ea9e1e123c80dfc38a0d3b061d8eb68f9ed76133db07490da616cb3bf5b70ba0",
}
SOURCE_RAW_PATHS = {
    "N3_PASSIVE": OLD / "runs/n3_passive/raw.csv",
    "N4_PASSIVE": OLD / "runs/n4_passive/raw.csv",
}
QB_FULL = (
    "I(I_REPLAY)",
    "V(QBIN)",
    "I(LIN|XBQ1)",
    "V(LIN|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "I(L1|XBQ1)",
    "V(L1|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "I(RJ1|XBQ1)",
    "V(RJ1|XBQ1)",
    "I(L2|XBQ1)",
    "V(L2|XBQ1)",
    "I(IB|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(RJ2|XBQ1)",
    "V(RJ2|XBQ1)",
    "I(L3|XBQ1)",
    "V(L3|XBQ1)",
    "V(QBOUT)",
)
JTL_FULL = tuple(
    label
    for stage in range(1, 7)
    for label in (
        f"P(B01|XJTL1_{stage})",
        f"V(B01|XJTL1_{stage})",
        f"I(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})",
        f"V(B02|XJTL1_{stage})",
        f"I(B02|XJTL1_{stage})",
        f"V(JTL{stage}_OUT)",
    )
) + ("I(R_TERM)",)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_raw(path: Path) -> tuple[list[str], list[dict[str, str]], dict[Decimal, dict[str, str]], dict[Decimal, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    by_time: dict[Decimal, dict[str, str]] = {}
    tokens: dict[Decimal, str] = {}
    for row in rows:
        time_ps = Decimal(row["time"]) * Decimal("1e12")
        by_time[time_ps] = row
        tokens[time_ps] = row["time"]
    return fields, rows, by_time, tokens


def unwrap(values: list[float]) -> list[float]:
    output = [float(values[0])]
    previous = float(values[0])
    tau = 2.0 * math.pi
    for value in values[1:]:
        current = float(value)
        delta = current - previous
        while delta > math.pi:
            delta -= tau
        while delta < -math.pi:
            delta += tau
        output.append(output[-1] + delta)
        previous = current
    return output


def phase_delta_token(value: float) -> str:
    return f"{value:.17e}"


def pairwise_check(
    page: dict[str, object],
    labels: tuple[str, ...],
    failures: list[str],
) -> dict[str, object]:
    run_id = str(page["run_id"])
    pair = page["pairwise_data"]
    path = REPO / str(pair["path"])
    fields, rows, _, _ = load_raw(path)
    control_fields, control_rows, control_by_time, control_tokens = load_raw(RAW_PATHS["N4_REPLAY"])
    run_fields, run_rows, run_by_time, _ = load_raw(RAW_PATHS[run_id])
    control_times = [Decimal(row["time"]) * Decimal("1e12") for row in control_rows]
    run_times = [Decimal(row["time"]) * Decimal("1e12") for row in run_rows]
    control_phase: dict[str, dict[Decimal, float]] = {}
    run_phase: dict[str, dict[Decimal, float]] = {}
    for label in labels:
        if not label.startswith("P("):
            continue
        control_unwrapped = unwrap([float(row[label]) for row in control_rows])
        run_unwrapped = unwrap([float(row[label]) for row in run_rows])
        control_phase[label] = dict(zip(control_times, control_unwrapped))
        run_phase[label] = dict(zip(run_times, run_unwrapped))
    expected_times = sorted(
        time
        for time in set(control_by_time) & set(run_by_time)
        if Decimal("110.0") <= time < Decimal("200.0")
    )
    csv_times = [Decimal(row["time"]) * Decimal("1e12") for row in rows]
    if csv_times != expected_times:
        failures.append(f"{run_id}/{page['name']}: CSV time grid differs from exact raw intersection")
    if len(rows) != 900:
        failures.append(f"{run_id}/{page['name']}: expected 900 pairwise rows, got {len(rows)}")
    for label in labels:
        control_column = next((field for field in fields if field.startswith(f"{label} | N4_REPLAY | raw |")), None)
        run_column = next((field for field in fields if field.startswith(f"{label} | {run_id} | raw |")), None)
        delta_column = next((field for field in fields if field.startswith(f"{label} | {run_id}_MINUS_N4 | derived delta |")), None)
        if not control_column or not run_column or not delta_column:
            failures.append(f"{run_id}/{page['name']}: missing three tracks for {label}")
            continue
        for row, time_ps in zip(rows, csv_times):
            if row[control_column] != control_by_time[time_ps][label]:
                failures.append(f"{run_id}/{page['name']}: N4 raw mismatch at {time_ps} for {label}")
                break
            if row[run_column] != run_by_time[time_ps][label]:
                failures.append(f"{run_id}/{page['name']}: intervention raw mismatch at {time_ps} for {label}")
                break
            if label.startswith("P("):
                expected = phase_delta_token(run_phase[label][time_ps] - control_phase[label][time_ps])
                if row[delta_column] != expected:
                    failures.append(f"{run_id}/{page['name']}: independently unwrapped P delta mismatch at {time_ps} for {label}")
                    break
            else:
                expected = Decimal(run_by_time[time_ps][label]) - Decimal(control_by_time[time_ps][label])
                if Decimal(row[delta_column]) != expected:
                    failures.append(f"{run_id}/{page['name']}: raw delta mismatch at {time_ps} for {label}")
                    break
    return {
        "run_id": run_id,
        "page": page["name"],
        "status": "PASS" if not any(item.startswith(f"{run_id}/{page['name']}:") for item in failures) else "FAIL",
        "labels_checked": len(labels),
        "sample_count": len(rows),
        "phase_delta_method": "independent complete-trace unwrap per case, then intervention minus N4",
        "wrapped_phase_subtraction": False,
    }


def window_check(page: dict[str, object], failures: list[str]) -> dict[str, object]:
    metadata = page["window_data"]
    path = REPO / str(metadata["path"])
    _, rows, by_time, _ = load_raw(path)
    declared = [Decimal(value) for value in metadata["declared_window_ps"]]
    times = sorted(by_time)
    page_name = f"{page['run_id']}/{page['name']}"
    if len(rows) != int(metadata["actual_sample_count"]):
        failures.append(f"{page_name}: window sample count mismatch")
    if not times or times[0] != Decimal(metadata["actual_time_start_ps"]) or times[-1] != Decimal(metadata["actual_time_last_sample_ps"]):
        failures.append(f"{page_name}: window endpoint metadata mismatch")
    if any(time < declared[0] or time >= declared[1] for time in times):
        failures.append(f"{page_name}: sample outside half-open declared window")
    if metadata["uses_full_raw_as_plot_input"]:
        failures.append(f"{page_name}: full raw used as zoom input")
    return {
        "run_id": page["run_id"],
        "page": page["name"],
        "declared_window_ps": metadata["declared_window_ps"],
        "actual_start_ps": metadata["actual_time_start_ps"],
        "actual_last_sample_ps": metadata["actual_time_last_sample_ps"],
        "sample_count": len(rows),
        "status": "PASS" if not any(item.startswith(page_name + ":") for item in failures) else "FAIL",
    }


def main() -> int:
    manifest = json.loads(V2_MANIFEST.read_text(encoding="utf-8"))
    base_qa = json.loads(V2_QA.read_text(encoding="utf-8"))
    pages = manifest["pages"]
    failures: list[str] = []
    page_map = {(page["run_id"], page["name"]): page for page in pages}
    expected_names = {
        "BVM_SOURCE_REFERENCE",
        "INPUT_COMPONENTS",
        "QB_FULL_INTERNAL",
        "JTL_FULL_CHAIN",
        "QB_INTERNAL_CRITICAL_ZOOM",
        "JTL_DOWNSTREAM_ZOOM",
        "N4_VS_RUN_QB_RAW_DELTA",
        "N4_VS_RUN_JTL_RAW_DELTA",
    }
    if set(manifest["run_directories"]) != set(RUNS):
        failures.append("manifest does not contain exactly four run directories")
    for run_id in RUNS:
        run_page_names = {
            name
            for (page_run, name) in page_map
            if page_run == run_id
        }
        if run_page_names != expected_names:
            failures.append(f"{run_id}: incomplete run page set")
        for name in expected_names:
            page = page_map.get((run_id, name))
            if page is None:
                continue
            output = REPO / str(page["output"])
            if not output.is_file():
                failures.append(f"{run_id}/{name}: missing HTML")
            if sha256(output) != page["output_sha256"]:
                failures.append(f"{run_id}/{name}: HTML hash mismatch")
        bvm = page_map.get((run_id, "BVM_SOURCE_REFERENCE"))
        if bvm:
            if bvm["source_kind"] != "IMMUTABLE_PASSIVE_SOURCE_REFERENCE / NOT REPLAY-RUN RAW":
                failures.append(f"{run_id}: BVM source kind mismatch")
            if "IMMUTABLE_PASSIVE_SOURCE_REFERENCE / NOT REPLAY-RUN RAW" not in bvm["title"]:
                failures.append(f"{run_id}: BVM source marker missing from title")
            for source_name, source_path in SOURCE_RAW_PATHS.items():
                if bvm["source_raw_hashes"][source_name] != EXPECTED_SOURCE_HASHES[source_name]:
                    failures.append(f"{run_id}: BVM source hash mismatch for {source_name}")
        critical = page_map.get((run_id, "QB_INTERNAL_CRITICAL_ZOOM"))
        if critical:
            if set(critical["labels"]) != set(QB_FULL):
                failures.append(f"{run_id}: critical QB labels are not complete")
        jtl = page_map.get((run_id, "JTL_DOWNSTREAM_ZOOM"))
        if jtl:
            if set(jtl["labels"]) != set(JTL_FULL):
                failures.append(f"{run_id}: downstream JTL labels are not complete")
        for name, labels in (
            ("N4_VS_RUN_QB_RAW_DELTA", QB_FULL),
            ("N4_VS_RUN_JTL_RAW_DELTA", JTL_FULL),
        ):
            page = page_map.get((run_id, name))
            if page:
                pairwise_check(page, labels, failures)
                provenance = page["phase_delta_provenance"]
                if provenance["wrapped_phase_subtraction"] is not False:
                    failures.append(f"{run_id}/{name}: wrapped phase subtraction is enabled")
    window_records = []
    for page in pages:
        if "window_data" in page:
            window_records.append(window_check(page, failures))
    raw_hashes = {}
    for case, path in RAW_PATHS.items():
        actual = sha256(path)
        raw_hashes[case] = {"sha256": actual, "expected": EXPECTED_RAW_HASHES[case], "unchanged": actual == EXPECTED_RAW_HASHES[case]}
        if actual != EXPECTED_RAW_HASHES[case]:
            failures.append(f"{case}: raw hash mismatch")
    for source_name, path in SOURCE_RAW_PATHS.items():
        actual = sha256(path)
        if actual != EXPECTED_SOURCE_HASHES[source_name]:
            failures.append(f"{source_name}: passive source hash changed")
    if not base_qa.get("raw_hashes_unchanged") or not base_qa.get("delta4_v1_unchanged"):
        failures.append("base v2 visualization QA does not report raw/v1 immutability")
    record = {
        "schema": "jm2-delta4-independent-visualization-v2-check-v1",
        "experiment_id": NEW.name,
        "head": manifest["head_at_visualization"],
        "status": "PASS" if not failures else "FAIL",
        "run_directory_count": len(RUNS),
        "pairwise_pages_checked": len(RUNS) * 2,
        "pairwise_phase_delta_method": "independent complete-trace unwrap per case, then intervention minus N4",
        "wrapped_phase_subtraction": False,
        "window_checks": window_records,
        "raw_hashes": raw_hashes,
        "passive_source_hashes": {
            name: {"sha256": sha256(path), "expected": EXPECTED_SOURCE_HASHES[name]}
            for name, path in SOURCE_RAW_PATHS.items()
        },
        "base_visualization_qa": {
            "status": base_qa.get("status"),
            "page_count": base_qa.get("page_count"),
            "raw_hashes_unchanged": base_qa.get("raw_hashes_unchanged"),
            "delta4_v1_unchanged": base_qa.get("delta4_v1_unchanged"),
        },
        "failures": failures,
    }
    output = NEW / "analysis/viz_qa_v2_independent_check.json"
    write_once(output, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "pairwise_pages_checked": record["pairwise_pages_checked"], "failures": failures}, ensure_ascii=False))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
