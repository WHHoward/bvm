#!/usr/bin/env python3
"""validate_scope_correct_object_matrix -- deterministic attempt-local
validator for the M11B-003 scope-correct matrix + pointer.

Verifies AC1-AC5:
  - exact seven object_ids + required fields,
  - evidence existence/hash/scope + output-as-evidence prohibition,
  - [PUBLISHED] requires reviewed local source,
  - exact status enums, structured UNKNOWN entries,
  - freeze_task / W5B closure bound to M11B-003,
  - pointer integrity (short, no nonexistent file, no second register,
    no early W5B completion),
  - final task identity.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys
import yaml  # type: ignore  (PyYAML available in this repo env)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
A = pathlib.Path(__file__).resolve().parent
MATRIX_PATH = REPO_ROOT / "docs/research/SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml"
POINTER_PATH = REPO_ROOT / "docs/research/REFERENCE_PROVENANCE.md"

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
OUTPUT_DOCS = ("docs/research/SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml",
               "docs/research/REFERENCE_PROVENANCE.md")

AUTHORIZED_PATHS = {
    "docs/HANDOVER.md", "docs/research/METRIC_SPEC_V2.md",
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


def validate(matrix: dict, pointer_text: str) -> list[str]:
    errors: list[str] = []

    # --- exact seven-object set ---
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
            errors.append(f"objects[{i}]: duplicate object_id {oid!r}")
        seen[oid] = i
        missing = [f for f in REQUIRED_OBJECT_FIELDS if f not in o]
        if missing:
            errors.append(f"objects[{i}] {oid}: missing fields {missing}")

        # status enums
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

        # evidence: scope/existence/hash + OUTPUT-AS-EVIDENCE PROHIBITION
        for j, ev in enumerate(o.get("current_evidence", [])):
            if not isinstance(ev, dict) or "path" not in ev:
                errors.append(f"objects[{i}] {oid}.current_evidence[{j}]: must be a source entry")
                continue
            p = ev["path"]
            if p in OUTPUT_DOCS:
                errors.append(f"objects[{i}] {oid}: output document used as factual evidence: {p}")
                continue
            if p.startswith("arti/"):
                if not pathlib.Path(REPO_ROOT / p).is_file():
                    errors.append(f"objects[{i}] {oid}: arti source missing {p}")
                continue
            if p not in AUTHORIZED_PATHS:
                errors.append(f"objects[{i}] {oid}: evidence path outside read scope {p}")
            live = sha256_of(p)
            if live is None:
                errors.append(f"objects[{i}] {oid}: evidence file missing {p}")
            elif ev.get("sha256") != live:
                errors.append(f"objects[{i}] {oid}: evidence sha256 mismatch {p}")
            for req in ("source_role", "review_state", "locator"):
                if req not in ev:
                    errors.append(f"objects[{i}] {oid}: evidence entry missing {req} for {p}")

        # [PUBLISHED] requires reviewed source
        pp = o.get("parameter_provenance", {})
        published_claimed = any("[PUBLISHED]" in str(v) for v in pp.values())
        reviewed = any(isinstance(ev, dict) and ev.get("review_state") == "REVIEWED"
                       for ev in o.get("current_evidence", []))
        if published_claimed and not reviewed:
            errors.append(f"objects[{i}] {oid}: [PUBLISHED] needs at least one REVIEWED evidence source")

        # structured UNKNOWN + laundering
        published_fields = {_norm_field(str(f)) for f, v in pp.items() if "[PUBLISHED]" in str(v)}
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
            nf = _norm_field(str(item.get("field", "")))
            if "UNKNOWN" in str(item.get("reference_status", "")) and nf and nf in published_fields:
                errors.append(f"objects[{i}] {oid}: field {nf!r} [PUBLISHED] but UNKNOWN in unknowns (laundering)")

    # --- freeze_task / W5B bound to M11B-003 (AC3) ---
    ft = str(matrix.get("freeze_task", ""))
    if ft != "JH-20260813-M11B-003":
        errors.append(f"freeze_task must be JH-20260813-M11B-003, got {ft!r}")
    wb = matrix.get("w5b_boundary")
    if not isinstance(wb, dict) or "JH-20260813-M11B-003" not in str(wb.get("closure_eligible", "")):
        errors.append("w5b closure must be bound to JH-20260813-M11B-003 audit acceptance")
    for key in ("w5a", "w5c"):
        if key not in wb or "independent" not in str(wb.get(key, "")):
            errors.append(f"w5b_boundary.{key} must declare independence")

    # --- PASS semantics ---
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

    # --- pointer integrity (AC4) ---
    pt = pointer_text
    if "SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml" not in pt:
        errors.append("pointer must reference the canonical matrix")
    # no nonexistent working-tree file
    for m in re.finditer(r"`?([\w./-]+\.(?:md|yaml))`?", pt):
        name = m.group(1)
        if name == "SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml":
            continue
        if not (REPO_ROOT / name).is_file():
            errors.append(f"pointer names nonexistent file: {name}")
    # no second register: pointer must not contain a parameter table
    if "| 参数" in pt or "| 对象 |" in pt or "| 关键参数 |" in pt:
        errors.append("pointer must not contain a second parameter register table")
    # no early W5B completion
    if re.search(r"W5B.{0,40}(已|标记).{0,20}完成", pt) and "ACCEPTED" not in pt.split("W5B")[1][:80] if "W5B" in pt else False:
        errors.append("pointer marks W5B complete without audit acceptance gate")

    return errors


def main() -> int:
    with open(MATRIX_PATH, encoding="utf-8") as f:
        matrix = yaml.safe_load(f)
    pointer = POINTER_PATH.read_text(encoding="utf-8")
    errors = validate(matrix, pointer)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("VALIDATION PASSED: scope-correct matrix + pointer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
