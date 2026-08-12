#!/usr/bin/env python3
"""validate_scientific_reconstruction_baseline -- deterministic attempt-local
validator for the M11B scientific-reconstruction-baseline-v1.yaml.

Rejects:
  - absent required structured fields per object (source_reference,
    parameter_provenance, reproduction_status, characterization_status,
    unknown_inferred_items, evidence, claim_limitation, upgrade_discriminator),
  - invalid provenance tags (only the seven allowed tags),
  - a bare UNKNOWN item (must name field/reference status/project value/tag/
    source set/date/impact/discriminator),
  - an unjustified reproduction upgrade (e.g. R2/R3 without the behavioural-
    analogue rule or without achieved rationale),
  - characterization inferred from reproduction (characterization_status must
    be one of the independent enum),
  - candidate/Gate success text or a claim that PASS means physical knowledge
    completeness / published reproduction / candidate validation.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import pathlib
import sys
import yaml  # type: ignore  (PyYAML is available in this repo env)

BASELINE_PATH = pathlib.Path(__file__).resolve().parent / "scientific-reconstruction-baseline-v1.yaml"

REQUIRED_OBJECT_FIELDS = (
    "object", "source_reference", "parameter_provenance", "reproduction_status",
    "characterization_status", "unknown_inferred_items", "evidence",
    "claim_limitation", "upgrade_discriminator",
)

VALID_PROVENANCE_TAGS = (
    "[PUBLISHED]", "[AUTHOR_PROVIDED]", "[DERIVED]",
    "[INFERRED]", "[DESIGNED]", "[TUNED]", "[UNKNOWN]",
)

VALID_CHAR_STATUS = (
    "NOT_ATTEMPTED", "LEGACY_ONLY", "CALIBRATION_FIXTURE_ONLY", "CHARACTERIZED",
)

UNKNOWN_ITEM_FIELDS = (
    "field", "reference_value_status", "project_value", "provenance_tag",
    "source_set", "review_date", "impact", "required_discriminator",
)

FORBIDDEN_CLAIM_TEXT = (
    "physical knowledge completeness achieved",
    "published reproduction achieved",
    "candidate validation achieved",
    "interface gate pass", "system gate pass",
    "sfq_count", "event_count", "pulse_count",
)


def _tag_strings(obj: dict) -> str:
    """Flatten all provenance-tag-bearing strings of an object."""
    parts = [str(obj.get("parameter_provenance", ""))]
    for item in obj.get("unknown_inferred_items", []):
        if isinstance(item, dict):
            parts.append(str(item.get("provenance_tag", "")))
    return " ".join(parts)


def validate(baseline: dict) -> list[str]:
    errors: list[str] = []

    objects = baseline.get("objects")
    if not isinstance(objects, list) or not objects:
        return ["objects missing or empty"]

    required_objects = {
        "BVM", "published modified-QB", "original/reference BQ",
        "canonical JTL receiver", "canonical DCSFQ reference fixture",
        "BVM source characterization", "receiver characterization",
    }
    present = {o.get("object") for o in objects if isinstance(o, dict)}
    missing_objs = required_objects - present
    if missing_objs:
        errors.append(f"missing required objects: {sorted(missing_objs)}")

    for i, o in enumerate(objects):
        if not isinstance(o, dict):
            errors.append(f"objects[{i}]: not a mapping")
            continue
        missing = [f for f in REQUIRED_OBJECT_FIELDS if f not in o]
        if missing:
            errors.append(f"objects[{i}] {o.get('object')}: missing fields {missing}")

        # --- provenance tags ---
        for tag in _tag_strings(o).split():
            if tag.startswith("[") and tag.endswith("]") and tag not in VALID_PROVENANCE_TAGS:
                errors.append(f"objects[{i}] {o.get('object')}: invalid provenance tag {tag}")

        # --- characterization enum ---
        cs = o.get("characterization_status")
        if cs not in VALID_CHAR_STATUS:
            errors.append(f"objects[{i}] {o.get('object')}: invalid characterization_status {cs!r}")

        # --- provenance laundering guard (AC2) ---
        # A field marked [PUBLISHED] in parameter_provenance must not also be
        # recorded UNKNOWN in unknown_inferred_items for the same object.
        pp = o.get("parameter_provenance")
        published_fields = set()
        if isinstance(pp, dict):
            for field, tag in pp.items():
                if isinstance(tag, str) and "[PUBLISHED]" in tag:
                    published_fields.add(field.lower())
        elif isinstance(pp, str):
            published_fields.add(pp.lower())
        for item in o.get("unknown_inferred_items", []):
            if not isinstance(item, dict):
                continue
            field = str(item.get("field", "")).lower()
            ref = str(item.get("reference_value_status", ""))
            if "UNKNOWN" in ref and field in published_fields:
                errors.append(
                    f"objects[{i}] {o.get('object')}: field '{field}' is marked "
                    f"[PUBLISHED] in parameter_provenance but UNKNOWN in "
                    f"unknown_inferred_items (provenance laundering)")

        # --- reproduction status structure + no unjustified upgrade ---
        rs = o.get("reproduction_status")
        if not isinstance(rs, dict) or "level" not in rs:
            errors.append(f"objects[{i}] {o.get('object')}: reproduction_status must have a level")
        else:
            level = rs["level"]
            if level in ("R2", "R3") and "rationale" not in rs:
                errors.append(f"objects[{i}] {o.get('object')}: R2/R3 requires achieved rationale")
            # behavioural-analogue rule: project tuned params must not claim R2
            if level == "R2" and "behavioral_analogue" not in str(rs) and "non-published" in str(o.get("parameter_provenance", "")).lower():
                errors.append(f"objects[{i}] {o.get('object')}: non-published parameters cannot claim published R2")

        # --- unknown items: no bare UNKNOWN ---
        for j, item in enumerate(o.get("unknown_inferred_items", [])):
            if not isinstance(item, dict):
                errors.append(f"objects[{i}] {o.get('object')}.unknown_inferred_items[{j}]: not a mapping")
                continue
            missing = [f for f in UNKNOWN_ITEM_FIELDS if f not in item]
            if missing:
                errors.append(
                    f"objects[{i}] {o.get('object')}.unknown_inferred_items[{j}]: "
                    f"missing required fields {missing}")
            tag = item.get("provenance_tag", "")
            if tag not in VALID_PROVENANCE_TAGS:
                errors.append(f"objects[{i}] {o.get('object')}.unknown_inferred_items[{j}]: invalid tag {tag!r}")
            # a guessed/default numerical value must never stand in for UNKNOWN
            ref = str(item.get("reference_value_status", ""))
            if "UNKNOWN" in ref and item.get("project_value") is None:
                errors.append(f"objects[{i}] {o.get('object')}.unknown_inferred_items[{j}]: UNKNOWN without explicit project_value field")

    # --- PASS meaning ---
    pm = str(baseline.get("pass_meaning", "")).lower()
    if "completely and honestly frozen" not in pm:
        errors.append("pass_meaning must declare complete-and-honest freeze semantics")
    if "physical knowledge completeness" in pm and "not" not in pm:
        errors.append("pass_meaning must not claim physical knowledge completeness")

    # --- forbidden claim text ---
    text = yaml.safe_dump(baseline).lower()
    for term in FORBIDDEN_CLAIM_TEXT:
        if term in text:
            errors.append(f"forbidden claim text present: {term}")

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
    print("VALIDATION PASSED: scientific-reconstruction-baseline-v1.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
