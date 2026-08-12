#!/usr/bin/env python3
"""validate_measurement_calibration_baseline -- deterministic attempt-local
validator for the M11A measurement-calibration-baseline-v1.yaml.

Rejects:
  - missing accepted-layer fields (layer, accepted_evidence, sha256,
    audit_disposition, study_phase, contribution, applicability_limit),
  - use of a non-accepted predecessor as acceptance evidence (accepted_layers
    entries must point at the sole accepted M4-M10 verdicts listed below),
  - absent provenance hashes (every raw/manifest/output entry needs sha256),
  - a global-tolerance claim (tolerance_status values must be UNFROZEN),
  - forbidden physical/Gate vocabulary.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import pathlib
import re
import sys
import yaml  # type: ignore  (PyYAML is available in this repo env)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
BASELINE_PATH = pathlib.Path(__file__).resolve().parent / "measurement-calibration-baseline-v1.yaml"

SOLE_ACCEPTED_EVIDENCE = {
    "M4": "research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml",
    "M5": "research/tasks/M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md",
    "M6": "research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml",
    "M7": "research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md",
    "M8": "research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml",
    "M9": "research/tasks/JH-20260813-M9-004/audits/C01/verdict.yaml",
    "M10": "research/tasks/JH-20260813-M10-004/audits/C01/verdict.yaml",
}

REQUIRED_LAYER_FIELDS = (
    "layer", "accepted_evidence", "sha256", "audit_disposition",
    "study_phase", "contribution", "applicability_limit",
)

# Claim-form vocabulary only: the baseline's own prohibition statements
# legitimately name sfq/fluxoid/candidate/gate in negative sentences, so only
# count/field-name-style occurrences are forbidden.
FORBIDDEN_VOCAB = (
    "sfq_count", "event_count", "pulse_count", "fast_events", "fluxoid_count",
    "candidate_pass", "candidate_fail", "interface_gate", "gate_pass",
    "physical_pass", "paper_novelty", "downstream_received",
)


def sha256_of(path: str) -> str | None:
    import hashlib
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

    # --- AC1: accepted layers ---
    layers = baseline.get("accepted_layers")
    if not isinstance(layers, list) or not layers:
        return ["accepted_layers missing or empty"]
    seen = set()
    for i, layer in enumerate(layers):
        missing = [f for f in REQUIRED_LAYER_FIELDS if f not in layer]
        if missing:
            errors.append(f"accepted_layers[{i}]: missing fields {missing}")
            continue
        lname = layer["layer"]
        if lname in seen:
            errors.append(f"accepted_layers[{i}]: duplicate layer {lname}")
        seen.add(lname)
        # non-accepted predecessor as acceptance evidence?
        if lname in SOLE_ACCEPTED_EVIDENCE:
            if layer["accepted_evidence"] != SOLE_ACCEPTED_EVIDENCE[lname]:
                errors.append(
                    f"accepted_layers[{i}]: {lname} must use sole accepted "
                    f"evidence {SOLE_ACCEPTED_EVIDENCE[lname]}, got "
                    f"{layer['accepted_evidence']}")
        else:
            errors.append(f"accepted_layers[{i}]: unknown layer {lname}")
        # hash must match the live file
        live = sha256_of(layer["accepted_evidence"])
        if live is None:
            errors.append(f"accepted_layers[{i}]: evidence file missing {layer['accepted_evidence']}")
        elif layer["sha256"] != live:
            errors.append(f"accepted_layers[{i}]: sha256 mismatch for {layer['accepted_evidence']}")
        if layer["audit_disposition"] != "ACCEPTED":
            errors.append(f"accepted_layers[{i}]: audit_disposition must be ACCEPTED")

    # --- AC2: metric-spec binding ---
    ms = baseline.get("metric_spec")
    if not isinstance(ms, dict) or ms.get("path") != "docs/research/METRIC_SPEC_V2.md":
        errors.append("metric_spec.path must be docs/research/METRIC_SPEC_V2.md")
    else:
        live = sha256_of(ms["path"])
        if live is None:
            errors.append("metric_spec file missing")
        elif ms.get("sha256") != live:
            errors.append("metric_spec.sha256 does not match the live file")

    # --- provenance hashes must exist and match ---
    rc = baseline.get("raw_control_inventory")
    if isinstance(rc, dict):
        for fam, blob in rc.items():
            for run in blob.get("runs", []):
                for key in ("manifest", "raw"):
                    if key not in run or "sha256" not in run and key == "manifest":
                        errors.append(f"{fam}: run {run.get('run_id')} missing {key}")
                if run.get("manifest"):
                    live = sha256_of(run["manifest"])
                    if live is None or run.get("sha256") != live:
                        errors.append(f"{fam}: manifest sha256 mismatch {run.get('run_id')}")
                if run.get("raw"):
                    live = sha256_of(run["raw"])
                    if live is None or run.get("raw_sha256") != live:
                        errors.append(f"{fam}: raw sha256 mismatch {run.get('run_id')}")
    rp = baseline.get("reconstruction_provenance")
    if isinstance(rp, dict):
        for out in rp.get("outputs", []):
            live = sha256_of(out["path"])
            if live is None or out.get("sha256") != live:
                errors.append(f"reconstruction output sha256 mismatch {out.get('path')}")

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
