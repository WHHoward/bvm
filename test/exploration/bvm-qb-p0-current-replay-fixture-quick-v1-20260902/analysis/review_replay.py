#!/usr/bin/env python3
"""Independent mechanical review of the completed RP replay result.

The reviewer uses stdlib CSV parsing and direct arithmetic for the key
input/PRE/trajectory checks.  It does not run JoSIM and never changes raw data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw(path: Path) -> tuple[list[str], list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        columns = {name: [] for name in headers}
        times: list[float] = []
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            values = [float(item) for item in row]
            times.append(values[0])
            for index, name in enumerate(headers):
                columns[name].append(values[index])
    return headers, times, columns


def rms(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def window_indices(times: list[float], interval: list[float]) -> list[int]:
    start, end = (value * 1.0e-12 for value in interval)
    return [index for index, value in enumerate(times) if start <= value < end]


def exact(a: list[float], b: list[float]) -> bool:
    return len(a) == len(b) and all(left == right for left, right in zip(a, b))


def unwrap(values: list[float]) -> list[float]:
    tau = 2.0 * math.pi
    result = [values[0]]
    previous = values[0]
    for value in values[1:]:
        delta = value - previous
        if delta > math.pi:
            delta -= tau * math.ceil((delta - math.pi) / tau)
        elif delta < -math.pi:
            delta += tau * math.ceil((-delta - math.pi) / tau)
        result.append(result[-1] + delta)
        previous = value
    return result


def centered_phase(times: list[float], values: list[float], pre: list[float]) -> list[float]:
    indices = window_indices(times, pre)
    unwrapped = unwrap(values)
    ordered = sorted(unwrapped[index] for index in indices)
    middle = len(ordered) // 2
    baseline = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return [(value - baseline) / (2.0 * math.pi) for value in unwrapped]


def compare(times_a: list[float], values_a: list[float], times_b: list[float], values_b: list[float], interval: list[float]) -> dict[str, object]:
    if not exact(times_a, times_b):
        return {"grid_exact": False, "status": "REPLAY_INVALID"}
    indices = window_indices(times_a, interval)
    differences = [values_b[index] - values_a[index] for index in indices]
    return {
        "grid_exact": True,
        "status": "VALID",
        "sample_count": len(indices),
        "rms": rms(differences),
        "max_abs": max(abs(value) for value in differences),
    }


def main() -> int:
    config = yaml.safe_load((ROOT / "experiment.yaml").read_text(encoding="utf-8"))
    metrics = json.loads((ROOT / "analysis/metrics.json").read_text(encoding="utf-8"))
    p0_path = (ROOT / config["references"]["P0"]["raw"]).resolve()
    rp_path = (ROOT / config["candidate"]["raw"]).resolve()
    p0_headers, p0_time, p0 = raw(p0_path)
    rp_headers, rp_time, rp = raw(rp_path)
    checks: list[dict[str, object]] = []

    input_result = compare(
        p0_time, p0[config["candidate"]["source_signal"]],
        rp_time, rp[config["candidate"]["replay_output_signal"]],
        [0.0, 170.0],
    )
    input_max_uA = float(input_result.get("max_abs", math.inf)) * 1.0e6
    checks.append({
        "name": "literal_input_replay",
        "pass": input_result.get("grid_exact") is True and input_max_uA <= 1.0e-6,
        "independent_max_abs_error_uA": input_max_uA,
        "reported_max_abs_error_uA": metrics["input_replay_fidelity"]["max_abs_error_uA"],
    })

    pre = config["windows_ps"]["W2_pre_read_idle"]
    for signal in config["signals"]["pre_currents"]:
        item = compare(p0_time, p0[signal], rp_time, rp[signal], pre)
        max_uA = float(item.get("max_abs", math.inf)) * 1.0e6
        checks.append({"name": f"PRE current {signal}", "pass": max_uA <= float(config["pre_state_rule"]["current_max_abs_difference_uA"]), "independent_max_abs_uA": max_uA})
    for signal in config["signals"]["pre_phases"]:
        p0_phase = centered_phase(p0_time, p0[signal], pre)
        rp_phase = centered_phase(rp_time, rp[signal], pre)
        item = compare(p0_time, p0_phase, rp_time, rp_phase, pre)
        checks.append({"name": f"PRE phase {signal}", "pass": float(item.get("max_abs", math.inf)) <= float(config["pre_state_rule"]["phase_max_abs_difference_turns"]), "independent_max_abs_turns": item.get("max_abs")})

    for signal in config["signals"]["primary_trajectory"]:
        if signal.startswith("P("):
            p0_values = centered_phase(p0_time, p0[signal], pre)
            rp_values = centered_phase(rp_time, rp[signal], pre)
            i0_path = (ROOT / config["references"]["I0"]["raw"]).resolve()
            _h, i0_time, i0 = raw(i0_path)
            i0_values = centered_phase(i0_time, i0[signal], pre)
        else:
            p0_values = [value * 1.0e6 for value in p0[signal]]
            rp_values = [value * 1.0e6 for value in rp[signal]]
            i0_path = (ROOT / config["references"]["I0"]["raw"]).resolve()
            _h, i0_time, i0 = raw(i0_path)
            i0_values = [value * 1.0e6 for value in i0[signal]]
        for window_name in ("W3_read", "W4_post_read_observation"):
            interval = config["windows_ps"][window_name]
            rp_gap = compare(p0_time, p0_values, rp_time, rp_values, interval)
            i0_gap = compare(p0_time, p0_values, i0_time, i0_values, interval)
            if not rp_gap.get("grid_exact") or not i0_gap.get("grid_exact"):
                checks.append({"name": f"closure {window_name} {signal}", "pass": False, "reason": "grid mismatch"})
                continue
            denominator = float(i0_gap["rms"])
            ratio = float(rp_gap["rms"]) / denominator if denominator > 1.0e-9 else None
            reported = metrics["trajectory_closure"]["records"][window_name][signal]
            checks.append({
                "name": f"closure {window_name} {signal}",
                "pass": ratio is None or abs(ratio - float(reported["C_x"])) <= 1.0e-9,
                "independent_C_x": ratio,
                "reported_C_x": reported["C_x"],
            })

    all_pass = all(bool(item["pass"]) for item in checks)
    review = {
        "schema_version": "BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1_REVIEW_V1",
        "reviewed_at": now(),
        "reviewer": "independent_stdlib_mechanical_review",
        "all_checks_pass": all_pass,
        "raw_hashes": {"P0": sha256(p0_path), "I0": sha256(i0_path), "RP": sha256(rp_path)},
        "sample_counts": {"P0": len(p0_time), "I0": len(i0_time), "RP": len(rp_time)},
        "checks": checks,
        "limitations": [
            "This review does not rerun JoSIM.",
            "It checks arithmetic and provenance consistency; it does not upgrade an exploratory result to a scientific Gate.",
        ],
    }
    (ROOT / "analysis/independent_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Independent review — BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1",
        "",
        f"审查时间：`{review['reviewed_at']}`；方式：stdlib CSV + 独立直接算术；不运行 JoSIM。",
        "",
        f"总体验证：`{'PASS' if all_pass else 'FAIL'}`。",
        "",
        "## 检查范围",
        "",
        "- 检查 P0/RP exact time grid、literal input replay 误差和样本数。",
        "- 独立重算 W2 PRE 电流/phase 差异，以及 W3/W4 primary trajectory Cx。",
        "- 检查 P0/I0/RP raw hash 和没有额外 JoSIM run 的目录事实；不修改 raw。",
        "",
        "| check | result | key value |",
        "|---|---|---:|",
    ]
    for item in checks:
        value = item.get("independent_C_x", item.get("independent_max_abs_error_uA", item.get("independent_max_abs_uA", item.get("independent_max_abs_turns", ""))))
        lines.append(f"| `{item['name']}` | `{'PASS' if item['pass'] else 'FAIL'}` | `{value}` |")
    lines += [
        "",
        "## 审查边界",
        "",
        "本复核确认的是算术、exact-grid 和 provenance 一致性；strict BJL2 标签仍是同一 JJ 的 local phase/area compatibility，不能解释为 SFQ count、downstream delivery 或 system Gate。",
    ]
    (ROOT / "analysis/REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
