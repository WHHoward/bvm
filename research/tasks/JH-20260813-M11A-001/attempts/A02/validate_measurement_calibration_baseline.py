#!/usr/bin/env python3
"""validate_measurement_calibration_baseline (A02) -- deterministic
attempt-local validator for the M11A baseline.

A02 rework (C01 required_rework):
  - exact M4--M10 layer set required (no missing/extra/duplicate layers),
  - M10 eleven-artifact inventory must be exact and hash-verified,
  - nonempty complete M6/M8/reconstruction inventories required,
  - negative tests deleting each mandatory class must be rejected.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import yaml  # type: ignore  (PyYAML available in this repo env)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
BASELINE_PATH = pathlib.Path(__file__).resolve().parent / "measurement-calibration-baseline-v1.yaml"

REQUIRED_LAYERS = ("M4", "M5", "M6", "M7", "M8", "M9", "M10")
SOLE_ACCEPTED_EVIDENCE = {
    "M4": "research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml",
    "M5": "research/tasks/M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md",
    "M6": "research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml",
    "M7": "research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md",
    "M8": "research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml",
    "M9": "research/tasks/JH-20260813-M9-004/audits/C01/verdict.yaml",
    "M10": "research/tasks/JH-20260813-M10-004/audits/C01/verdict.yaml",
}
REQUIRED_LAYER_FIELDS = ("layer", "accepted_evidence", "sha256", "audit_disposition",
                         "study_phase", "contribution", "applicability_limit")

M10_ARTIFACT_PATHS = [
    "scripts/rebuild_historical_metrics_v2.py",
    "test/metrics/test_rebuild_historical_metrics_v2.py",
    "test/final/single_bvm_qb/data/metrics_v2/baseline-v2.json",
    "test/final/interface/data/metrics_v2/p0-v2.json",
    "test/final/bvm/data/metrics_v2/p2-v2.json",
    "test/final/qb/data/metrics_v2/bq-v4-v2.json",
    "docs/research/HISTORICAL_METRICS_V2_CORRECTION_TABLE.md",
    "test/final/single_bvm_qb/BASELINE.md",
    "test/final/interface/P0_LOG.md",
    "test/final/bvm/P2_LOG.md",
    "test/final/single_bvm_qb/EXPERIMENT_LOG.md",
]

FORBIDDEN_VOCAB = (
    "sfq_count", "event_count", "pulse_count", "fast_events", "fluxoid_count",
    "candidate_pass", "candidate_fail", "interface_gate", "gate_pass",
    "physical_pass", "paper_novelty", "downstream_received",
)


def sha256_of(path: str) -> str | None:
    full = REPO_ROOT / path
    if not full.is_file():
        return None
    digest = hashlib.sha256()
    with open(full, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(baseline: dict) -> list[str]:
    errors: list[str] = []

    # --- AC1: EXACT M4--M10 layer set (A02 rework) ---
    layers = baseline.get("accepted_layers")
    if not isinstance(layers, list):
        return ["accepted_layers missing"]
    names = [l.get("layer") for l in layers if isinstance(l, dict)]
    if sorted(names) != sorted(REQUIRED_LAYERS):
        errors.append(f"accepted_layers must be exactly {list(REQUIRED_LAYERS)}, got {names}")
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(f"accepted_layers[{i}]: not a mapping")
            continue
        missing = [f for f in REQUIRED_LAYER_FIELDS if f not in layer]
        if missing:
            errors.append(f"accepted_layers[{i}]: missing fields {missing}")
            continue
        lname = layer["layer"]
        if lname not in REQUIRED_LAYERS:
            errors.append(f"accepted_layers[{i}]: unknown layer {lname}")
            continue
        if layer["accepted_evidence"] != SOLE_ACCEPTED_EVIDENCE[lname]:
            errors.append(f"accepted_layers[{i}]: {lname} must use sole accepted evidence")
        live = sha256_of(layer["accepted_evidence"])
        if live is None:
            errors.append(f"accepted_layers[{i}]: evidence file missing")
        elif layer["sha256"] != live:
            errors.append(f"accepted_layers[{i}]: sha256 mismatch")
        if layer["audit_disposition"] != "ACCEPTED":
            errors.append(f"accepted_layers[{i}]: audit_disposition must be ACCEPTED")

    # --- AC2: metric-spec binding ---
    ms = baseline.get("metric_spec")
    if not isinstance(ms, dict) or ms.get("path") != "docs/research/METRIC_SPEC_V2.md":
        errors.append("metric_spec.path must be docs/research/METRIC_SPEC_V2.md")
    else:
        live = sha256_of(ms["path"])
        if live is None or ms.get("sha256") != live:
            errors.append("metric_spec.sha256 does not match the live file")

    # --- AC2: EXACT M10 eleven-artifact inventory (A02 rework) ---
    m10 = baseline.get("m10_inventory")
    if not isinstance(m10, list):
        errors.append("m10_inventory missing")
    else:
        paths = [e.get("path") for e in m10 if isinstance(e, dict)]
        if sorted(paths) != sorted(M10_ARTIFACT_PATHS):
            errors.append(f"m10_inventory must be exactly the 11 artifacts, got {paths}")
        for e in m10:
            if not isinstance(e, dict) or "path" not in e or "sha256" not in e:
                errors.append(f"m10_inventory entry missing path/sha256: {e}")
                continue
            live = sha256_of(e["path"])
            if live is None:
                errors.append(f"m10_inventory: file missing {e['path']}")
            elif e["sha256"] != live:
                errors.append(f"m10_inventory: sha256 mismatch {e['path']}")

    # --- nonempty complete M6/M8 inventories (A02 rework) ---
    rc = baseline.get("raw_control_inventory")
    if not isinstance(rc, dict):
        errors.append("raw_control_inventory missing")
    else:
        m6 = rc.get("M6_same_jj", {}).get("runs")
        m8 = rc.get("M8_convergence", {}).get("runs")
        if not isinstance(m6, list) or len(m6) != 2:
            errors.append("M6_same_jj.runs must contain exactly 2 runs")
        if not isinstance(m8, list) or len(m8) != 6:
            errors.append("M8_convergence.runs must contain exactly 6 runs")
        for fam, blob in rc.items():
            for run in blob.get("runs", []):
                if run.get("manifest"):
                    live = sha256_of(run["manifest"])
                    if live is None or run.get("sha256") != live:
                        errors.append(f"{fam}: manifest sha256 mismatch {run.get('run_id')}")
                if run.get("raw"):
                    live = sha256_of(run["raw"])
                    if live is None or run.get("raw_sha256") != live:
                        errors.append(f"{fam}: raw sha256 mismatch {run.get('run_id')}")

    # --- AC4: tolerances UNFROZEN ---
    ts = baseline.get("tolerance_status")
    if not isinstance(ts, dict):
        errors.append("tolerance_status missing")
    else:
        for key in ("universal_activity_threshold", "integer_residual",
                    "phase_area_residual", "platform_stability", "bvm_drift",
                    "amplitude", "jitter"):
            if ts.get(key) != "UNFROZEN":
                errors.append(f"tolerance_status.{key} must be UNFROZEN")

    # --- forbidden vocabulary (claim-form) ---
    text = yaml.safe_dump(baseline).lower()
    for term in FORBIDDEN_VOCAB:
        if term in text:
            errors.append(f"forbidden vocabulary present: {term}")

    return errors


def main() -> int:
    with open(BASELINE_PATH, encoding="utf-8") as f:
        baseline = yaml.safe_load(f)
    errors = validate(baseline)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("VALIDATION PASSED: measurement-calibration-baseline-v1.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
