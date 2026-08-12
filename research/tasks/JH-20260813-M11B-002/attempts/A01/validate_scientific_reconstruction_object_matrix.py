#!/usr/bin/env python3
"""validate_scientific_reconstruction_object_matrix -- deterministic
attempt-local validator for SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml.

Rejects (AC6):
  - missing/duplicate object IDs (exact seven-object set),
  - out-of-scope/missing/hash-mismatched evidence sources,
  - [PUBLISHED] parameters supported only by INVENTORIED_UNREVIEWED evidence,
  - bare UNKNOWN items,
  - undeclared reproduction/characterization status values,
  - provenance laundering by canonical field id,
  - physical/PASS semantic bypass,
  - W5B/W5A/W5C conflation.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys
import yaml  # type: ignore  (PyYAML available in this repo env)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
MATRIX_PATH = REPO_ROOT / "docs/research/SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml"

EXACT_OBJECT_IDS = (
    "bvm_storage", "bvm_source_output", "published_qb", "bq_v4",
    "standard_dcsfq", "dcsfq_bvm", "canonical_jtl",
)
REQUIRED_OBJECT_FIELDS = (
    "object_id", "current_evidence", "observable", "parameter_provenance",
    "characterization_status", "reproduction_status", "unknowns",
    "claim_limitation", "next_discriminator",
)
VALID_REPRO = ("NOT_ATTEMPTED", "R0", "PARTIAL_R1", "R1", "R2", "R3")
VALID_CHAR = ("NOT_ATTEMPTED", "LEGACY_ONLY", "CALIBRATION_FIXTURE_ONLY", "CHARACTERIZED")
VALID_TAGS = ("[PUBLISHED]", "[AUTHOR_PROVIDED]", "[DERIVED]", "[INFERRED]", "[DESIGNED]", "[TUNED]", "[UNKNOWN]")
UNKNOWN_FIELDS = ("field", "reference_status", "project_value", "provenance_tag",
                  "reviewed_source_boundary", "impact", "next_discriminator")

# Authorized read scope (request read_paths, exact file list portion)
AUTHORIZED_PATHS = {
    "docs/HANDOVER.md", "docs/research/METRIC_SPEC_V2.md",
    "docs/research/REFERENCE_PROVENANCE.md",
    "docs/research/HISTORICAL_METRICS_V2_CORRECTION_TABLE.md",
    "circuits/bvm/bvm_cell.cir", "circuits/qb/bq_cell.cir",
    "circuits/qb/bq_cell_paper.cir", "circuits/qb/bq_cell_v4.cir",
    "circuits/standard/DCSFQ.cir", "circuits/standard/JTL.cir",
    "circuits/models/jjmit.cir", "circuits/interface/DCSFQ_BVM.cir",
    "test/final/single_bvm_qb/test_bvm_bq_baseline.cir",
    "test/metrics/m7_canonical_jtl.cir",
    "test/final/single_bvm_qb/data/metrics_v2/baseline-v2.json",
    "test/final/interface/data/metrics_v2/p0-v2.json",
    "test/final/bvm/data/metrics_v2/p2-v2.json",
    "test/final/qb/data/metrics_v2/bq-v4-v2.json",
    "research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml",
    "research/tasks/M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md",
    "research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml",
    "research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md",
    "research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml",
    "research/tasks/JH-20260813-M9-004/audits/C01/verdict.yaml",
    "research/tasks/JH-20260813-M10-004/audits/C01/verdict.yaml",
    "research/tasks/JH-20260813-M11A-001/audits/C02/verdict.yaml",
    "research/tasks/JH-20260813-M11B-001/",
}


def sha256_of(path: str) -> str | None:
    full = REPO_ROOT / path
    if not full.is_file():
        return None
    digest = hashlib.sha256()
    with open(full, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _norm_field(field: str) -> str:
    s = field.lower().strip()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"[\s/_-]+", " ", s).strip()
    return s


def validate(matrix: dict) -> list[str]:
    errors: list[str] = []

    # --- exact seven-object set (AC1/AC6) ---
    objects = matrix.get("objects")
    if not isinstance(objects, list):
        return ["objects missing"]
    ids = [o.get("object_id") for o in objects if isinstance(o, dict)]
    if sorted(ids) != sorted(EXACT_OBJECT_IDS):
        errors.append(f"object_ids must be exactly {list(EXACT_OBJECT_IDS)}, got {ids}")
    seen: dict[str, int] = {}
    for i, o in enumerate(objects):
        if not isinstance(o, dict):
            errors.append(f"objects[{i}]: not a mapping")
            continue
        oid = o.get("object_id", f"<objects[{i}]>")
        if oid in seen:
            errors.append(f"objects[{i}]: duplicate object_id {oid!r} (first at {seen[oid]})")
        seen[oid] = i
        missing = [f for f in REQUIRED_OBJECT_FIELDS if f not in o]
        if missing:
            errors.append(f"objects[{i}] {oid}: missing fields {missing}")

        # --- status enums (AC3/AC6) ---
        cs = o.get("characterization_status")
        if cs not in VALID_CHAR:
            errors.append(f"objects[{i}] {oid}: invalid characterization_status {cs!r}")
        rs = o.get("reproduction_status")
        if not isinstance(rs, dict) or rs.get("level") not in VALID_REPRO:
            errors.append(f"objects[{i}] {oid}: invalid reproduction level {rs!r}")
        elif rs["level"] in ("R2", "R3") and "rationale" not in rs:
            errors.append(f"objects[{i}] {oid}: R2/R3 requires rationale")
        if rs and rs.get("level") == "R2" and "behavioral" not in str(rs.get("rationale", "")):
            errors.append(f"objects[{i}] {oid}: R2 must carry behavioral-analogue rationale")

        # --- evidence: scope/existence/hash/review (AC2/AC6) ---
        for j, ev in enumerate(o.get("current_evidence", [])):
            if not isinstance(ev, dict) or "path" not in ev:
                errors.append(f"objects[{i}] {oid}.current_evidence[{j}]: must be a source entry")
                continue
            p = ev["path"]
            if p.startswith("arti/"):
                if not pathlib.Path(REPO_ROOT / p).is_file():
                    errors.append(f"objects[{i}] {oid}: arti source missing {p}")
                continue  # arti/ allowed by read scope (arti/*.pdf)
            if p not in AUTHORIZED_PATHS and not p.startswith("research/tasks/JH-20260813-M11B-001"):
                errors.append(f"objects[{i}] {oid}: evidence path outside read scope {p}")
            live = sha256_of(p)
            if live is None:
                errors.append(f"objects[{i}] {oid}: evidence file missing {p}")
            elif ev.get("sha256") != live:
                errors.append(f"objects[{i}] {oid}: evidence sha256 mismatch {p}")
            for req in ("source_role", "review_state", "locator"):
                if req not in ev:
                    errors.append(f"objects[{i}] {oid}: evidence entry missing {req} for {p}")

        # --- [PUBLISHED] requires reviewed local source (AC2/AC6) ---
        pp = o.get("parameter_provenance", {})
        published_claimed = any("[PUBLISHED]" in str(v) for v in pp.values())
        reviewed = any(
            isinstance(ev, dict) and ev.get("review_state") == "REVIEWED"
            for ev in o.get("current_evidence", []))
        if published_claimed and not reviewed:
            errors.append(f"objects[{i}] {oid}: [PUBLISHED] parameters need at least one REVIEWED evidence source")

        # --- bare UNKNOWN (AC2/AC6) ---
        for k, item in enumerate(o.get("unknowns", [])):
            if not isinstance(item, dict):
                errors.append(f"objects[{i}] {oid}.unknowns[{k}]: not a mapping")
                continue
            missing = [f for f in UNKNOWN_FIELDS if f not in item]
            if missing:
                errors.append(f"objects[{i}] {oid}.unknowns[{k}]: missing {missing}")
            tag = item.get("provenance_tag", "")
            if tag not in VALID_TAGS:
                errors.append(f"objects[{i}] {oid}.unknowns[{k}]: invalid tag {tag!r}")
            if "UNKNOWN" in str(item.get("reference_status", "")) and item.get("project_value") is None:
                errors.append(f"objects[{i}] {oid}.unknowns[{k}]: UNKNOWN without project_value field")

        # --- provenance laundering by canonical field id (AC6) ---
        published_fields = {_norm_field(str(f)) for f, v in pp.items() if "[PUBLISHED]" in str(v)}
        for item in o.get("unknowns", []):
            if not isinstance(item, dict):
                continue
            nf = _norm_field(str(item.get("field", "")))
            if "UNKNOWN" in str(item.get("reference_status", "")) and nf and nf in published_fields:
                errors.append(f"objects[{i}] {oid}: field {nf!r} [PUBLISHED] but UNKNOWN in unknowns (laundering)")

    # --- PASS semantics (AC4/AC6) ---
    pm = str(matrix.get("pass_object", "")).lower()
    if "complete and honest" not in pm and "knowledge-state freeze" not in pm:
        errors.append("pass_object must declare complete-and-honest knowledge-state freeze")
    ex = matrix.get("pass_exclusions")
    if not isinstance(ex, list) or not ex:
        errors.append("pass_exclusions list required")
    else:
        for item in ex:
            phrase = str(item).lower()
            if phrase in pm and "not" not in phrase:
                errors.append(f"pass_object affirmatively claims excluded meaning: {item}")

    # --- W5B/W5A/W5C conflation (AC5/AC6) ---
    wb = matrix.get("w5b_boundary")
    if not isinstance(wb, dict):
        errors.append("w5b_boundary missing")
    else:
        if "closure_eligible" not in wb or "audit acceptance" not in str(wb.get("closure_eligible", "")):
            errors.append("w5b closure must be gated on audit acceptance")
        for key in ("w5a", "w5c"):
            if key not in wb or "independent" not in str(wb.get(key, "")):
                errors.append(f"w5b_boundary.{key} must declare independence")

    return errors


def main() -> int:
    with open(MATRIX_PATH, encoding="utf-8") as f:
        matrix = yaml.safe_load(f)
    errors = validate(matrix)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("VALIDATION PASSED: SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
