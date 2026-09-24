"""Render frozen 0923 component sources from the effective USER_CASE values."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from config import (
    BVM_AREA_KEYS, BVM_INDUCTANCE_KEYS, BVM_RESISTANCE_KEYS, BIAS_RISE_KEYS,
    CB_AREA_KEYS, CB_CURRENT_KEYS, CB_INDUCTANCE_KEYS, CB_RESISTANCE_KEYS,
    COMPONENT_KEYS, ConfigError, QB_AREA_KEYS, QB_CURRENT_KEYS, QB_INDUCTANCE_KEYS,
    QB_RESISTANCE_KEYS, SJTL_AREA_KEYS, SJTL_CURRENT_KEYS, SJTL_INDUCTANCE_KEYS,
    SJTL_RESISTANCE_KEYS, parse_quantity, validate_user_case,
)
from topology import SOURCE_FILES, parse_subcircuits


SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
REFERENCE_PATH = SERIES / "config" / "component_reference.env"
SNAPSHOT_NAMES = {
    "BVM": "bvm_tunable.cir", "QB": "BQ_tunable.cir",
    "CB": "CB_tunable.cir", "SJTL": "sJTL_tunable.cir",
}
SOURCE_HASH_KEYS = {role: f"SOURCE_{role}_SHA256" for role in SOURCE_FILES}
REFERENCE_KEYS = COMPONENT_KEYS | set(SOURCE_HASH_KEYS.values())
GROUP_KEYS = {
    "BVM": BVM_AREA_KEYS | BVM_INDUCTANCE_KEYS | BVM_RESISTANCE_KEYS,
    "QB": QB_AREA_KEYS | QB_INDUCTANCE_KEYS | QB_RESISTANCE_KEYS | QB_CURRENT_KEYS | {"QB_BIAS_RISE"},
    "CB": CB_AREA_KEYS | CB_INDUCTANCE_KEYS | CB_RESISTANCE_KEYS | CB_CURRENT_KEYS | {"CB_BIAS_RISE"},
    "SJTL": SJTL_AREA_KEYS | SJTL_INDUCTANCE_KEYS | SJTL_RESISTANCE_KEYS | SJTL_CURRENT_KEYS | {"SJTL_BIAS_RISE"},
}

# Map canonical element designators to USER_CASE parameters. The model cards are
# deliberately absent: jjmit parameters remain source-defined/frozen.
ELEMENT_PARAMETERS: dict[str, dict[str, tuple[str, str]]] = {
    "BVM": {
        "R_BL": ("BVM_RBL", "resistance"), "L_PBL": ("BVM_LPBL", "inductance"),
        "R_WL": ("BVM_RWL", "resistance"), "L_PWL": ("BVM_LPWL", "inductance"),
        "B_JM1": ("BVM_JM1_AREA", "area"), "R_JM1": ("BVM_RJM1", "resistance"),
        "L_M1": ("BVM_LM1", "inductance"), "L_M2": ("BVM_LM2", "inductance"),
        "B_JM2": ("BVM_JM2_AREA", "area"), "R_JM2": ("BVM_RJM2", "resistance"),
        "L_M3": ("BVM_LM3", "inductance"), "L_PM": ("BVM_LPM", "inductance"),
        "L_S1": ("BVM_LS1", "inductance"), "B_JS1": ("BVM_JS1_AREA", "area"),
        "R_JS1": ("BVM_RJS1", "resistance"), "R_SE": ("BVM_RSE", "resistance"),
        "L_PSE": ("BVM_LPSE", "inductance"), "R_S": ("BVM_RS", "resistance"),
        "L_S3": ("BVM_LS3", "inductance"), "L_S2": ("BVM_LS2", "inductance"),
        "B_JS2": ("BVM_JS2_AREA", "area"), "R_JS2": ("BVM_RJS2", "resistance"),
        "L_PSL": ("BVM_LPSL", "inductance"), "R_SL": ("BVM_RSL", "resistance"),
        "L_SL": ("BVM_LSL", "inductance"),
    },
    "QB": {
        "LIN": ("QB_LIN", "inductance"), "L1": ("QB_L1", "inductance"),
        "L2": ("QB_L2", "inductance"), "L3": ("QB_L3", "inductance"),
        "BJ1": ("QB_BJ1_AREA", "area"), "RJ1": ("QB_RJ1", "resistance"),
        "BJ2": ("QB_BJ2_AREA", "area"), "RJ2": ("QB_RJ2", "resistance"),
        "BJ3": ("QB_BJ3_AREA", "area"), "RJ3": ("QB_RJ3", "resistance"),
        "IB2": ("QB_IB", "pwl"),
    },
    "CB": {
        "L1": ("CB_L1", "inductance"), "L2": ("CB_L2", "inductance"),
        "L3": ("CB_L3", "inductance"), "L4": ("CB_L4", "inductance"),
        "BJ1": ("CB_BJ1_AREA", "area"), "RJ1": ("CB_RJ1", "resistance"),
        "BJ2": ("CB_BJ2_AREA", "area"), "RJ2": ("CB_RJ2", "resistance"),
        "IB1": ("CB_IB", "pwl"),
    },
    "SJTL": {
        "L1": ("SJTL_L1", "inductance"), "L2": ("SJTL_L2", "inductance"),
        "BJ1": ("SJTL_BJ1_AREA", "area"), "RJ1": ("SJTL_RJ1", "resistance"),
        "IB1": ("SJTL_IB", "pwl"),
    },
}
BIAS_KEY = {"QB": "QB_BIAS_RISE", "CB": "CB_BIAS_RISE", "SJTL": "SJTL_BIAS_RISE"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_env(path: Path, keys: set[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"{path}:{line_no}: expected KEY=VALUE")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in keys or not value or key in values:
            raise ConfigError(f"{path}:{line_no}: invalid or duplicate reference key {key!r}")
        values[key] = value
    missing = sorted(keys - values.keys())
    if missing:
        raise ConfigError(f"{path}: missing reference keys: {', '.join(missing)}")
    return values


def load_reference(path: str | Path = REFERENCE_PATH) -> dict[str, str]:
    return _load_env(Path(path), REFERENCE_KEYS)


def verify_reference_sources(reference: dict[str, str], repo_root: str | Path = REPO) -> dict[str, dict[str, str]]:
    root = Path(repo_root)
    records = {}
    for role, relative in SOURCE_FILES.items():
        source = root / relative
        expected = reference[SOURCE_HASH_KEYS[role]]
        try:
            actual = sha256_file(source)
        except OSError as exc:
            raise ConfigError(
                f"REFERENCE_SOURCE_CHANGED: {role} canonical source is unavailable at {relative}; "
                "human review is required before changing component_reference.env"
            ) from exc
        if actual != expected:
            raise ConfigError(
                f"REFERENCE_SOURCE_CHANGED: {role} {relative} expected {expected}, got {actual}; "
                "human review is required before changing component_reference.env"
            )
        records[role] = {"path": relative.as_posix(), "sha256": actual}
    return records


def _prefix_and_body(line: str) -> tuple[str, str, bool]:
    match = re.match(r"^(\s*)(.*?)(\r?\n)?$", line)
    assert match is not None
    indent, remainder, ending = match.group(1), match.group(2), match.group(3) or ""
    if remainder.startswith("*"):
        comment_match = re.match(r"^\*\s*(.*)$", remainder)
        assert comment_match is not None
        return indent + "* ", comment_match.group(1), True
    return indent, remainder, False


def _same_numeric(left: str, right: str, kind: str) -> bool:
    if kind == "area":
        return left == right
    try:
        return parse_quantity(left, label="component") == parse_quantity(right, label="component")
    except ConfigError:
        return left == right


def _replace_line(line: str, designator: str, value: str, kind: str,
                  bias_rise: str | None = None) -> tuple[str, bool]:
    prefix, body, commented = _prefix_and_body(line)
    tokens = body.split()
    if not tokens or tokens[0].casefold() != designator.casefold():
        return line, False
    if kind == "resistance" and value == "OPEN":
        return (line if commented else prefix + "* " + body + ("\n" if line.endswith("\n") else "")), True
    if kind == "pwl":
        if len(tokens) < 4 or bias_rise is None:
            raise ConfigError(f"malformed bias source {designator}: {line.rstrip()}")
        expression = re.search(r"(?i)\bpwl\s*\(\s*0\s+0\s+(\S+)\s+(\S+)\s*\)", body)
        if expression is None:
            raise ConfigError(f"malformed bias PWL for {designator}: {line.rstrip()}")
        old_rise, old_current = expression.group(1), expression.group(2)
        if _same_numeric(old_rise, bias_rise, "time") and _same_numeric(old_current, value, "current"):
            return line, True
        rewritten = body[:expression.start(1)] + bias_rise + " " + value + body[expression.end(2):]
    elif kind == "area":
        expression = re.search(r"(?i)\barea\s*=\s*(\S+)", body)
        if expression is None:
            raise ConfigError(f"missing area= for {designator}: {line.rstrip()}")
        if _same_numeric(expression.group(1), value, "area"):
            return line, True
        rewritten = body[:expression.start(1)] + value + body[expression.end(1):]
    else:
        if len(tokens) < 4:
            raise ConfigError(f"malformed passive element {designator}: {line.rstrip()}")
        old_value = tokens[-1]
        if _same_numeric(old_value, value, kind) and not commented:
            return line, True
        last_index = body.rfind(old_value)
        rewritten = body[:last_index] + value + body[last_index + len(old_value):]
    prefix = re.match(r"^\s*", line).group(0)  # preserve source indentation when activating a branch
    return prefix + rewritten + ("\n" if line.endswith("\n") else ""), True


def render_source(role: str, source_text: str, parameters: dict[str, str]) -> str:
    if role not in ELEMENT_PARAMETERS:
        raise ConfigError(f"unknown component role: {role}")
    mapping = ELEMENT_PARAMETERS[role]
    seen: set[str] = set()
    output: list[str] = []
    for line in source_text.splitlines(keepends=True):
        prefix, body, _ = _prefix_and_body(line)
        tokens = body.split()
        designator = tokens[0] if tokens else ""
        entry = mapping.get(designator.upper())
        if entry is None:
            output.append(line)
            continue
        key, kind = entry
        rise = parameters[BIAS_KEY[role]] if role in BIAS_KEY and kind == "pwl" else None
        rewritten, matched = _replace_line(line, designator, parameters[key], kind, rise)
        if matched:
            seen.add(designator.upper())
        output.append(rewritten)
    missing = sorted(set(mapping) - seen)
    if missing:
        raise ConfigError(f"{role} canonical source is missing expected elements: {', '.join(missing)}")
    rendered = "".join(output)
    if role != "BVM" and ".model jjmit" not in rendered.lower():
        raise ConfigError(f"{role} source lost the frozen jjmit model card")
    return rendered


def render_components(values: dict[str, str], output_dir: str | Path, *,
                      repo_root: str | Path = REPO,
                      reference_path: str | Path = REFERENCE_PATH) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    validate_user_case(values)
    reference = load_reference(reference_path)
    canonical_records = verify_reference_sources(reference, repo_root)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    source_paths: dict[str, Path] = {}
    records: list[dict[str, Any]] = []
    for role, relative in SOURCE_FILES.items():
        canonical = Path(repo_root) / relative
        source_text = canonical.read_text(encoding="utf-8")
        effective = {key: values[key] for key in sorted(GROUP_KEYS[role])}
        if role in {"QB", "CB", "SJTL"}:
            effective[BIAS_KEY[role]] = values[BIAS_KEY[role]]
        rendered = render_source(role, source_text, values)
        snapshot = destination / SNAPSHOT_NAMES[role]
        snapshot.write_text(rendered, encoding="utf-8")
        source_paths[role] = snapshot
        records.append({
            "role": role,
            "canonical_source_path": relative.as_posix(),
            "canonical_source_sha256": canonical_records[role]["sha256"],
            "rendered_snapshot_path": snapshot.relative_to(Path(output_dir).parents[1]).as_posix()
            if len(Path(output_dir).parents) >= 2 else snapshot.name,
            "rendered_snapshot_sha256": sha256_file(snapshot),
            "effective_parameters": effective,
        })
    parse_subcircuits(source_paths)
    return source_paths, records


def parameter_manifest(values: dict[str, str], parsed: dict[str, object],
                       stimulus_values: dict[str, str], stimulus_snapshot_text: str) -> dict[str, Any]:
    return {
        "schema": "bvm-qb-cb-array-parameter-manifest-v1",
        "bvm": {key: values[key] for key in sorted(GROUP_KEYS["BVM"])},
        "qb": {key: values[key] for key in sorted(GROUP_KEYS["QB"])},
        "cb": {key: values[key] for key in sorted(GROUP_KEYS["CB"])},
        "sjtl": {key: values[key] for key in sorted(GROUP_KEYS["SJTL"])},
        "topology": {
            "ARRAY_SIZE": parsed["ARRAY_SIZE"], "MASKS": parsed["MASKS"],
            "QB_CB": parsed["QB_CB"], "SJTL_COUNT": parsed["SJTL_COUNT"],
            "POST_SJTL_CB": parsed["POST_SJTL_CB"],
        },
        "solver": {key: values[key] for key in ("OUTPUT_MODE", "TERM_R", "DT", "STOP")},
        "stimulus_reference": {
            "sha256": sha256_bytes(stimulus_snapshot_text.encode()),
            "values": dict(sorted(stimulus_values.items())),
        },
    }
