#!/usr/bin/env python3
"""按 A 侧最新 visual authority 生成 standalone 和 focused A/B 图。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
A_ROOT = REPO / "test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903"
RENDERER = REPO / "scripts/josim-plot2.py"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")
ONE_HOT = ("1000", "0100", "0010", "0001")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sl_probes import historical_sensing_line_endpoint_probes  # noqa: E402
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_array_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite visualization artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_generated(path: Path, content: str) -> None:
    """更新可再生成的索引/manifest，不触碰 raw 或 plot HTML 内容。"""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def b_raw(state: str) -> Path:
    return EXP / "runs" / state / "raw.csv"


def a_raw(state: str) -> Path:
    return A_ROOT / "runs_sl_endpoints" / state / "raw.csv"


def individual_specs() -> list[tuple[str, list[str], str]]:
    controls = [f"I(I_{control}{number})" for number in range(1, 5) for control in ("WL", "BL", "SE")]
    bvm_jj = [f"{kind}(B_{junction}|XBVM{number})" for number in range(1, 5) for junction in ("JM1", "JM2", "JS1", "JS2") for kind in ("P", "V", "I")]
    bvm_state = bvm_jj + [*(f"V(SL{number})" for number in range(1, 5)), *(f"I(L_SL|XBVM{number})" for number in range(1, 5))]
    endpoint = list(flatten_probe_labels(historical_sensing_line_endpoint_probes())) + [
        "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)", "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)"
    ]
    qb = [
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
        "I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)",
    ]
    jtl = [
        *(f"{kind}(B02|XJTL1_{stage})" for stage in range(1, 7) for kind in ("P", "V")),
        *(f"{kind}(B01|XJTL1_{stage})" for stage in range(1, 7) for kind in ("P", "V")),
    ]
    return [
        ("CONTROL_TIMING", controls, "control timing"),
        ("BVM_STATE", bvm_state, "all BVM JJ P/V/I and SL telemetry"),
        ("BVM_INTERNAL_PVI", bvm_jj, "all BVM internal JJ P/V/I"),
        ("BVMOUT_QB_INPUT", endpoint, "all BVM SL endpoints, BVMout and QB input/output"),
        ("QB_INTERNAL", qb, "QB internal observables"),
        ("JTL_TRANSPORT", jtl, "six-stage JTL P/V observables"),
    ]


def ensure_labels(trace: RawTrace, labels: list[str], source: Path) -> None:
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{source}: missing plot labels {missing}")


def run_plot(input_path: Path, output_path: Path, title: str, labels: list[str]) -> dict[str, object]:
    trace = read_csv(input_path)
    ensure_labels(trace, labels, input_path)
    command = [sys.executable, str(RENDERER), str(input_path), "-x", str(output_path), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-s", *labels, "-w", title]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"plot2 failed: {output_path}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"not HTML: {output_path}")
    if re.search(r'"title":\{"text":"Unknown"', html):
        raise RuntimeError(f"Unknown axis label in {output_path}")
    phase = any(label.startswith("P(") for label in labels)
    if phase and ("Phase (turns)" not in html or "2pi" not in html):
        raise RuntimeError(f"phase unit QA failed: {output_path}")
    return {
        "path": output_path.relative_to(REPO).as_posix(),
        "input": input_path.relative_to(REPO).as_posix(),
        "input_sha256": digest(input_path),
        "output_sha256": digest(output_path),
        "title": title,
        "labels": labels,
        "command": command,
        "phase_unit_check": "PASS" if phase else "NOT_APPLICABLE",
    }


def raw_rows(path: Path) -> tuple[RawTrace, list[dict[str, str]]]:
    trace = read_csv(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return trace, rows


def write_derived(path: Path, series: list[tuple[str, Path, str, tuple[float, ...]]]) -> list[str]:
    if not series:
        raise ValueError("derived CSV needs series")
    traces = [read_csv(source) for _, source, _, _ in series]
    base_time = traces[0].time
    if any(trace.time != base_time for trace in traces[1:]):
        raise RuntimeError(f"derived comparison time grid mismatch: {path}")
    labels = [label for label, _, _, _ in series]
    lines = io.StringIO(newline="")
    writer = csv.writer(lines, lineterminator="\n")
    writer.writerow(["time", *labels])
    values_by_series = [values for _, _, _, values in series]
    for index, time in enumerate(base_time):
        writer.writerow([f"{time:.17g}", *(f"{values[index]:.17g}" for values in values_by_series)])
    write_once(path, lines.getvalue())
    return labels


def raw_values(path: Path, label: str) -> tuple[float, ...]:
    return read_csv(path).column(label)  # type: ignore[return-value]


def same_side_delta(path: Path, baseline: Path, label: str, *, center_pre: bool = False) -> tuple[float, ...]:
    trace = read_csv(path)
    base = read_csv(baseline)
    if trace.time != base.time:
        raise RuntimeError(f"delta grid mismatch: {path} vs {baseline}")
    values, reference = trace.column(label), base.column(label)
    if not center_pre:
        return tuple(float(a) - float(b) for a, b in zip(values, reference))
    pre = [index for index, value in enumerate(trace.time) if 105.0e-12 <= value < 110.0e-12]
    left_center = median(float(values[index]) for index in pre)
    right_center = median(float(reference[index]) for index in pre)
    return tuple((float(a) - left_center) - (float(b) - right_center) for a, b in zip(values, reference))


def aggregate_series() -> list[tuple[str, Path, list[tuple[str, Path, str, tuple[float, ...]]], str]]:
    aggregates: list[tuple[str, Path, list[tuple[str, Path, str, tuple[float, ...]]], str]] = []
    weight1: list[tuple[str, Path, str, tuple[float, ...]]] = []
    for state in ONE_HOT:
        for label in ("V(QBIN)", "I(LIN|XBQ1)"):
            weight1.append((f"{label} [{state} connected]", b_raw(state), label, raw_values(b_raw(state), label)))
    aggregates.append(("WEIGHT1_QBIN_INPUT_JM2C", EXP / "plots/comparison/WEIGHT1_QBIN_INPUT_JM2C.csv", weight1, "JM2-connected four one-hot states — QBIN voltage and LIN input current"))

    ab: list[tuple[str, Path, str, tuple[float, ...]]] = []
    for state in ONE_HOT:
        for side, path_function, suffix in (("omitted", a_raw, "JM2 omitted"), ("connected", b_raw, "JM2 connected")):
            for label in ("V(QBIN)", "I(LIN|XBQ1)"):
                ab.append((f"{label} [{state} {suffix}]", path_function(state), label, raw_values(path_function(state), label)))
    aggregates.append(("WEIGHT1_POSITION_OMITTED_VS_CONNECTED", EXP / "plots/comparison/WEIGHT1_POSITION_OMITTED_VS_CONNECTED.csv", ab, "four one-hot positions — JM2 omitted vs connected QB input"))

    zero: list[tuple[str, Path, str, tuple[float, ...]]] = []
    for state in ONE_HOT:
        for number, bit in enumerate(state, start=1):
            if bit == "1":
                continue
            label = f"I(L_SL|XBVM{number})"
            for path_function, suffix in ((a_raw, "JM2 omitted"), (b_raw, "JM2 connected")):
                path = path_function(state)
                baseline = path_function("0000")
                values = same_side_delta(path, baseline, label, center_pre=True)
                zero.append((f"I(Delta_LSL|XBVM{number}) [{state} {suffix} centered]", path, label, values))
    aggregates.append(("ZERO_BVM_INDUCED_RESPONSE_OMITTED_VS_CONNECTED", EXP / "plots/comparison/ZERO_BVM_INDUCED_RESPONSE_OMITTED_VS_CONNECTED.csv", zero, "zero-cell READ-associated Delta I_LSL — PRE_READ1-centered JM2 omitted vs connected"))
    return aggregates


def write_index(records: list[dict[str, object]]) -> None:
    links = []
    for record in records:
        path = Path(str(record["path"]))
        relative = path.relative_to(EXP.relative_to(REPO) / "plots").as_posix()
        links.append(f'<li><a href="{relative}">{record["title"]}</a></li>')
    content = "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>JM2-connected Quick plots</title></head><body>\n<h1>JM2-connected 4-BVM six-state A/B Quick</h1>\n<ul>\n" + "\n".join(links) + "\n</ul>\n<p>Standalone plots are generated before comparisons. P(...) uses JoSIM rad/(2*pi) and is displayed as turns; plots are descriptive only.</p>\n<p>这 39 个 Plotly HTML 是工作区生成文件，因体积按仓库 .gitignore 不纳入 Git；本索引在已生成的工作区中链接有效。提交快照绑定 plot manifest，重新生成命令见 analysis/TEST_COMMANDS.md。</p>\n</body></html>\n"
    write_generated(EXP / "plots/INDEX.html", content)
    overview = "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>RESULT OVERVIEW</title></head><body>\n<h1>JM2-connected 4-BVM A/B Quick — result overview</h1>\n<p>重点：一个 one-hot active BVM 对其他 commanded-0、task-local retention-stable BVM 的 READ-associated response、JM2 omitted/connected 差异，以及 position-dependent QB input。</p>\n<p><a href=\"../analysis/REPORT.md\">分析报告</a> · <a href=\"INDEX.html\">全部图索引</a> · <a href=\"../analysis/metrics.json\">metrics.json</a> · <a href=\"../analysis/plot_manifest.json\">plot manifest</a></p>\n<ul>\n" + "\n".join(links) + "\n</ul>\n<p>上面的 39 个详细图均由本轮 renderer 生成；由于单张图内嵌 Plotly、体积较大，按 .gitignore 作为可再生成的工作区 HTML，不纳入 Git。提交快照保留本页、原始 raw、derived CSV、metrics 和 manifest；重新生成详细图的命令见 analysis/TEST_COMMANDS.md。</p>\n</body></html>\n"
    write_generated(EXP / "plots/RESULT_OVERVIEW.html", overview)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=EXP / "analysis/plot_manifest.json")
    args = parser.parse_args()
    b_before = {state: digest(b_raw(state)) for state in STATES}
    a_before = {state: digest(a_raw(state)) for state in STATES}
    records: list[dict[str, object]] = []
    # 先输出与 A 侧完全同名、同顺序的 per-state standalone plots。
    for state in STATES:
        for name, labels, description in individual_specs():
            records.append(run_plot(b_raw(state), EXP / "plots/runs" / state / f"{name}.html", f"JM2-connected {state} — {description}", labels))
    # standalone 全部成功后，再生成三个 focused derived comparison。
    for name, path, series, title in aggregate_series():
        labels = write_derived(path, series)
        records.append(run_plot(path, path.with_suffix(".html"), title, labels))
    if {state: digest(b_raw(state)) for state in STATES} != b_before or {state: digest(a_raw(state)) for state in STATES} != a_before:
        raise RuntimeError("A/B raw hash changed during visualization")
    manifest = {
        "schema": "bvmsim-4bvm-jm2-connected-state-position-ab-plot-manifest-v1",
        "renderer": RENDERER.relative_to(REPO).as_posix(),
        "renderer_sha256": digest(RENDERER),
        "plot_driver": Path(__file__).relative_to(REPO).as_posix(),
        "plot_driver_sha256": digest(Path(__file__)),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "standalone_before_comparison": True,
        "connected_raw_sha256_before": b_before,
        "connected_raw_sha256_after": {state: digest(b_raw(state)) for state in STATES},
        "omitted_endpoint_raw_sha256_before": a_before,
        "omitted_endpoint_raw_sha256_after": {state: digest(a_raw(state)) for state in STATES},
        "raw_unchanged": b_before == {state: digest(b_raw(state)) for state in STATES} and a_before == {state: digest(a_raw(state)) for state in STATES},
        "plots": records,
    }
    write_generated(args.manifest, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_index(records)
    print(json.dumps({"status": "PASS", "plot_count": len(records), "raw_unchanged": manifest["raw_unchanged"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
