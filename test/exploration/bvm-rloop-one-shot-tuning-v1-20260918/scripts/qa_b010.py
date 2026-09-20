#!/usr/bin/env python3
"""Mechanical QA and execution manifest for B010.

This script intentionally records execution/artifact facts only. It does not
compute or interpret the registered gain/Gate metrics; those require an
explicit scientific review authorization.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


SERIES = Path(__file__).resolve().parents[1]
BATCH = SERIES / "batches" / "B010_source_gain_screen"
RUNS = SERIES / "runs"
VARIANTS = [
    ("B0", "b010_b0_baseline", None, None),
    ("G1", "b010_g1_js1_area_046", "JS1_AREA", "0.46"),
    ("G2", "b010_g2_lm3_8p0", "LM3", "8.0p"),
    ("G3", "b010_g3_lm3_9p0", "LM3", "9.0p"),
    ("G4", "b010_g4_rsl_10", "RSL", "10"),
    ("G5", "b010_g5_se_110", "CONTROL_SE_AMP+READ_SE_AMP", "110u"),
    ("G6", "b010_g6_rs_3p5", "RS", "3.5"),
]
MASKS = ("PASSIVE_N1_0001", "PASSIVE_N4_1111")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def main() -> int:
    rows = []
    manifest_variants = []
    errors = []
    baseline = load_env(BATCH / "configs" / "B0.env")
    for variant, name, changed, value in VARIANTS:
        matches = sorted(RUNS.glob(f"U*_{name}"))
        if len(matches) != 1:
            errors.append(f"{variant}: expected one case for {name}, found {len(matches)}")
            continue
        case = matches[0]
        result = json.loads((case / "result.json").read_text(encoding="utf-8"))
        raw_qa = json.loads((case / "qa" / "raw_qa.json").read_text(encoding="utf-8"))
        plot_qa = json.loads((case / "qa" / "plot_qa.json").read_text(encoding="utf-8"))
        case_manifest = json.loads((case / "case_manifest.json").read_text(encoding="utf-8"))
        config = load_env(BATCH / "configs" / f"{variant}.env")
        expected_changes = []
        for key in ("JM1_AREA", "JM2_AREA", "RJM1", "RJM2", "LM1", "LM2", "LM3", "LPM", "JS1_AREA", "JS2_AREA", "RSH_JS1", "RSH_JS2", "LS1", "LS2", "LS3", "RS", "LPSL", "RSL", "LSL", "RBL", "LPBL", "RWL", "LPWL", "RSE", "LPSE", "CONTROL_SE_AMP", "READ_SE_AMP"):
            if config.get(key) != baseline.get(key):
                expected_changes.append(key)
        expected_count = 0 if variant == "B0" else 2 if variant == "G5" else 1
        if len(expected_changes) != expected_count:
            errors.append(f"{variant}: expected {expected_count} physical knob changes, found {expected_changes}")
        run_rows = []
        for mask in MASKS:
            run_id = mask
            raw_path = case / "cases" / mask / "raw.csv"
            metadata_path = case / "cases" / mask / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            raw_row = next((item for item in raw_qa.get("rows", []) if item.get("run_id") == mask), None)
            if raw_row is None or raw_row.get("status") != "PASS":
                errors.append(f"{variant}/{mask}: raw QA missing or not PASS")
            if metadata.get("execution_status") != "RUN_PASS":
                errors.append(f"{variant}/{mask}: execution status is not RUN_PASS")
            run_rows.append({"run_id": run_id, "raw_path": str(raw_path.relative_to(SERIES)), "raw_sha256": raw_row.get("sha256") if raw_row else None, "status": raw_row.get("status") if raw_row else "MISSING"})
        row = {
            "variant": variant,
            "case_id": case.name,
            "changed_parameter": changed or "NONE",
            "old_value": baseline.get(changed, "NONE") if changed and "+" not in changed else (f"{baseline.get('CONTROL_SE_AMP')}/{baseline.get('READ_SE_AMP')}" if changed else "NONE"),
            "new_value": value or "baseline",
            "mode": case_manifest.get("parameters", {}).get("MODE"),
            "masks": ",".join(case_manifest.get("parameters", {}).get("MASKS", [])),
            "physical_solve_count": result.get("physical_solve_count"),
            "raw_qa_status": raw_qa.get("status"),
            "plot_qa_status": plot_qa.get("status"),
            "raw_immutable": raw_qa.get("raw_immutable"),
            "scientific_review_status": "SCIENTIFIC_REVIEW_REQUIRED",
            "metrics_status": "NOT_COMPUTED_PENDING_SCIENTIFIC_REVIEW",
            "gate_s_status": "SCIENTIFIC_REVIEW_REQUIRED",
            "gate_r_status": "SCIENTIFIC_REVIEW_REQUIRED",
            "gate_z_status": "SCIENTIFIC_REVIEW_REQUIRED",
        }
        rows.append(row)
        manifest_variants.append({**row, "runs": run_rows, "case_path": str(case.relative_to(SERIES))})
    if len(rows) != len(VARIANTS):
        errors.append(f"expected {len(VARIANTS)} variants, found {len(rows)}")
    if any(row["physical_solve_count"] != 2 for row in rows):
        errors.append("every B010 variant must have exactly two physical solves")
    status = "PASS" if not errors and all(row["raw_qa_status"] == "PASS" and row["plot_qa_status"] == "PASS" for row in rows) else "FAIL"
    execution = {"schema": "bvm-rloop-source-gain-screen-execution-v1", "batch_id": "B010_source_gain_screen", "status": status, "authorized_variant_count": 7, "variant_count": len(rows), "authorized_mask_count": 2, "new_physical_solve_count": sum(row["physical_solve_count"] or 0 for row in rows), "qb_jtl_modified": False, "automatic_closed_followup": False, "scientific_interpretation_performed": False, "scientific_review_status": "SCIENTIFIC_REVIEW_REQUIRED", "errors": errors, "variants": manifest_variants}
    (BATCH / "B010_EXECUTION_MANIFEST.json").write_text(json.dumps(execution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = list(rows[0]) if rows else []
    with (BATCH / "B010_SOURCE_GAIN_SCREEN.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# B010 — BVM source-gain sensitivity screen",
        "",
        f"Mechanical execution status: **{status}**",
        "",
        "All seven registered variants ran PASSIVE N1 (`0001`) and N4 (`1111`). Raw and plot QA are recorded in `B010_EXECUTION_MANIFEST.json` and `B010_SOURCE_GAIN_SCREEN.csv`.",
        "",
        "## Scientific review boundary",
        "",
        "N1 source-gain metrics, Gate-S/Gate-R/Gate-Z classification, state-selective/delivery direction classification, gain-efficiency derivation, and CLOSED recommendations are intentionally **not computed here**. They remain `SCIENTIFIC_REVIEW_REQUIRED` until the explicit scientific-review authorization is supplied.",
        "",
        "No QB/JTL/terminal source was modified. No CLOSED follow-up, 2-D sweep, or automatic ranking was performed.",
        "",
        "## Mechanical variant table",
        "",
        "| variant | case | changed parameter | new value | raw QA | plot QA | solves |",
        "|---|---|---|---|---|---|---:|",
    ]
    lines.extend(f"| {row['variant']} | {row['case_id']} | {row['changed_parameter']} | {row['new_value']} | {row['raw_qa_status']} | {row['plot_qa_status']} | {row['physical_solve_count']} |" for row in rows)
    (BATCH / "B010_SOURCE_GAIN_SCREEN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "variants": len(rows), "new_physical_solve_count": execution["new_physical_solve_count"], "errors": errors, "scientific_review_status": execution["scientific_review_status"]}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
