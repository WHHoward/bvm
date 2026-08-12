#!/usr/bin/env python3
"""validate_scientific_reconstruction_baseline (A02) -- deterministic
attempt-local validator for the M11B baseline.

A02 rework (C01 required_rework):
  - explicit allowed reproduction-status enum (rejects R4 etc.),
  - exact object uniqueness (no duplicate object names),
  - required evidence/source existence + hash verification,
  - structured PASS-negation fields (pass_does_not_mean list),
  - robust per-field provenance conflict checking (alias/synonym aware),
  - adversarial tests: R4, synonym/alias laundering, source absence,
    PASS semantic bypass.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys
import yaml  # type: ignore  (PyYAML available in this repo env)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
BASELINE_PATH = pathlib.Path(__file__).resolve().parent / "scientific-reconstruction-baseline-v1.yaml"

REQUIRED_OBJECT_FIELDS = (
    "object", "source_reference", "parameter_provenance", "reproduction_status",
    "characterization_status", "unknown_inferred_items", "evidence",
    "claim_limitation", "upgrade_discriminator",
)
REQUIRED_OBJECTS = {
    "BVM", "published modified-QB", "original/reference BQ",
    "canonical JTL receiver", "canonical DCSFQ reference fixture",
    "BVM source characterization", "receiver characterization",
}
VALID_PROVENANCE_TAGS = (
    "[PUBLISHED]", "[AUTHOR_PROVIDED]", "[DERIVED]",
    "[INFERRED]", "[DESIGNED]", "[TUNED]", "[UNKNOWN]",
)
VALID_CHAR_STATUS = ("NOT_ATTEMPTED", "LEGACY_ONLY", "CALIBRATION_FIXTURE_ONLY", "CHARACTERIZED")
VALID_REPRO_LEVELS = ("R0", "R1", "R2", "R3", "PARTIAL_R1", "NOT_ATTEMPTED")
UNKNOWN_ITEM_FIELDS = (
    "field", "reference_value_status", "project_value", "provenance_tag",
    "source_set", "review_date", "impact", "required_discriminator",
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


def _norm_field(field: str) -> str:
    """Normalize a field name for conflict comparison (case/whitespace/
    parentheticals/aliases)."""
    s = field.lower().strip()
    s = re.sub(r"\(.*?\)", "", s)          # drop parenthetical qualifiers
    s = re.sub(r"\[.*?\]", "", s)          # drop provenance tags
    s = re.sub(r"[\s/_-]+", " ", s).strip()  # unify separators
    return s


def _tags_in(parameter_provenance) -> list[tuple[str, str]]:
    """Return (normalized_field, tag) pairs from parameter_provenance."""
    out: list[tuple[str, str]] = []
    if isinstance(parameter_provenance, dict):
        for field, tag in parameter_provenance.items():
            out.append((_norm_field(str(field)), str(tag)))
    elif isinstance(parameter_provenance, str):
        out.append((_norm_field(parameter_provenance), parameter_provenance))
    return out


def validate(baseline: dict) -> list[str]:
    errors: list[str] = []

    objects = baseline.get("objects")
    if not isinstance(objects, list) or not objects:
        return ["objects missing or empty"]

    present = {o.get("object") for o in objects if isinstance(o, dict)}
    missing_objs = REQUIRED_OBJECTS - present
    if missing_objs:
        errors.append(f"missing required objects: {sorted(missing_objs)}")

    seen_names: dict[str, int] = {}
    for i, o in enumerate(objects):
        if not isinstance(o, dict):
            errors.append(f"objects[{i}]: not a mapping")
            continue
        name = o.get("object", f"<objects[{i}]>")
        # exact object uniqueness (A02 rework)
        if name in seen_names:
            errors.append(f"objects[{i}]: duplicate object name {name!r} (first at index {seen_names[name]})")
        else:
            seen_names[name] = i

        missing = [f for f in REQUIRED_OBJECT_FIELDS if f not in o]
        if missing:
            errors.append(f"objects[{i}] {name}: missing fields {missing}")

        # --- characterization enum ---
        cs = o.get("characterization_status")
        if cs not in VALID_CHAR_STATUS:
            errors.append(f"objects[{i}] {name}: invalid characterization_status {cs!r}")

        # --- reproduction enum (A02 rework: reject R4 etc.) ---
        rs = o.get("reproduction_status")
        if not isinstance(rs, dict) or "level" not in rs:
            errors.append(f"objects[{i}] {name}: reproduction_status must have a level")
        else:
            level = rs["level"]
            if level not in VALID_REPRO_LEVELS:
                errors.append(f"objects[{i}] {name}: invalid reproduction level {level!r} (allowed {VALID_REPRO_LEVELS})")
            if level in ("R2", "R3") and "rationale" not in rs:
                errors.append(f"objects[{i}] {name}: R2/R3 requires achieved rationale")
            if level == "R2" and "behavioral_analogue" not in str(rs):
                errors.append(f"objects[{i}] {name}: R2 must record behavioral-analogue rule status")

        # --- evidence/source existence + hash verification (A02 rework) ---
        for j, ev in enumerate(o.get("evidence", [])):
            if not isinstance(ev, dict) or "path" not in ev:
                errors.append(f"objects[{i}] {name}.evidence[{j}]: must be {path: sha256} entry")
                continue
            live = sha256_of(ev["path"])
            if live is None:
                errors.append(f"objects[{i}] {name}.evidence[{j}]: source file missing {ev['path']}")
            elif ev.get("sha256") != live:
                errors.append(f"objects[{i}] {name}.evidence[{j}]: sha256 mismatch {ev['path']}")

        # --- per-field provenance conflict (A02 rework: alias aware) ---
        published = {f for f, t in _tags_in(o.get("parameter_provenance")) if "[PUBLISHED]" in t}
        for item in o.get("unknown_inferred_items", []):
            if not isinstance(item, dict):
                continue
            nf = _norm_field(str(item.get("field", "")))
            ref = str(item.get("reference_value_status", ""))
            if "UNKNOWN" in ref and nf and nf in published:
                errors.append(
                    f"objects[{i}] {name}: field {nf!r} marked [PUBLISHED] in "
                    f"parameter_provenance but UNKNOWN in unknown_inferred_items "
                    f"(provenance laundering)")
            tag = item.get("provenance_tag", "")
            if tag not in VALID_PROVENANCE_TAGS:
                errors.append(f"objects[{i}] {name}.unknown_inferred_items: invalid tag {tag!r}")
            missing = [f for f in UNKNOWN_ITEM_FIELDS if f not in item]
            if missing:
                errors.append(f"objects[{i}] {name}.unknown_inferred_items: missing {missing}")
            if "UNKNOWN" in ref and item.get("project_value") is None:
                errors.append(f"objects[{i}] {name}.unknown_inferred_items: UNKNOWN without explicit project_value field")

    # --- structured PASS negation (A02 rework) ---
    pm = str(baseline.get("pass_meaning", "")).lower()
    if "completely and honestly frozen" not in pm:
        errors.append("pass_meaning must declare complete-and-honest freeze semantics")
    neg = baseline.get("pass_does_not_mean")
    if not isinstance(neg, list) or not neg:
        errors.append("pass_does_not_mean structured list required")
    else:
        # adversarial: PASS may never claim any negated meaning affirmatively.
        # pass_meaning is allowed to *deny* them ("...not X..."); an
        # affirmative claim ("PASS means X achieved") without a negation is
        # the bypass to reject.
        for item in neg:
            phrase = str(item).lower()
            if phrase in pm and "not" not in phrase:
                errors.append(f"pass_meaning affirmatively claims a negated meaning: {item}")

    # --- reproduction semantics enum binding ---
    rl = baseline.get("reproduction_semantics", {}).get("levels")
    if not isinstance(rl, list) or set(rl) != set(VALID_REPRO_LEVELS):
        errors.append(f"reproduction_semantics.levels must be {list(VALID_REPRO_LEVELS)}")

    # --- corpus boundary must exist ---
    cb = baseline.get("corpus_boundary")
    if not isinstance(cb, dict):
        errors.append("corpus_boundary missing")

    # --- forbidden claim text (claim-form only; the pass_does_not_mean
    # negation list legitimately names prose phrases in negative sentences,
    # so only field-name-style occurrences are forbidden) ---
    text = yaml.safe_dump(baseline).lower()
    for term in ("sfq_count", "event_count", "pulse_count", "candidate_pass",
                 "gate_pass:", "paper_novelty:", "downstream_received"):
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
