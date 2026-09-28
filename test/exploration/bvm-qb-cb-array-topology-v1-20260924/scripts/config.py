"""Strict env parsing and SI-unit helpers for the array platform."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path


class ConfigError(ValueError):
    pass


NUMBER_RE = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)$")
SCALE = {
    "": Decimal("1"), "f": Decimal("1e-15"), "p": Decimal("1e-12"),
    "n": Decimal("1e-9"), "u": Decimal("1e-6"), "m": Decimal("1e-3"),
    "k": Decimal("1e3"), "meg": Decimal("1e6"), "g": Decimal("1e9"),
    "t": Decimal("1e12"),
}

BVM_AREA_KEYS = {"BVM_JM1_AREA", "BVM_JM2_AREA", "BVM_JS1_AREA", "BVM_JS2_AREA"}
BVM_RESISTANCE_KEYS = {
    "BVM_RJM1", "BVM_RJM2", "BVM_RJS1", "BVM_RJS2", "BVM_RS", "BVM_RSL",
    "BVM_RBL", "BVM_RWL", "BVM_RSE",
}
BVM_INDUCTANCE_KEYS = {
    "BVM_LM1", "BVM_LM2", "BVM_LM3", "BVM_LPM", "BVM_LS1", "BVM_LS2",
    "BVM_LS3", "BVM_LPSL", "BVM_LSL", "BVM_LPBL", "BVM_LPWL", "BVM_LPSE",
}
QB_AREA_KEYS = {"QB_BJ1_AREA", "QB_BJ2_AREA", "QB_BJ3_AREA"}
QB_RESISTANCE_KEYS = {"QB_RJ1", "QB_RJ2", "QB_RJ3"}
QB_INDUCTANCE_KEYS = {"QB_LIN", "QB_L1", "QB_L2", "QB_L3"}
QB_CURRENT_KEYS = {"QB_IB"}
CB_AREA_KEYS = {"CB_BJ1_AREA", "CB_BJ2_AREA"}
CB_RESISTANCE_KEYS = {"CB_RJ1", "CB_RJ2"}
CB_INDUCTANCE_KEYS = {"CB_L1", "CB_L2", "CB_L3", "CB_L4"}
CB_CURRENT_KEYS = {"CB_IB"}
SJTL_AREA_KEYS = {"SJTL_BJ1_AREA"}
SJTL_RESISTANCE_KEYS = {"SJTL_RJ1"}
SJTL_INDUCTANCE_KEYS = {"SJTL_L1", "SJTL_L2"}
SJTL_CURRENT_KEYS = {"SJTL_IB"}
BIAS_RISE_KEYS = {"QB_BIAS_RISE", "CB_BIAS_RISE", "SJTL_BIAS_RISE"}
T1_BIAS_KEYS = {"T1_BIAS1", "T1_BIAS2", "T1_BIAS3"}
T1_LOAD_KEYS = {"T1_R_S", "T1_R_C", "T1_CLK_R"}
T1_KEYS = T1_BIAS_KEYS | T1_LOAD_KEYS | {"T1_CLK_MODE", "T1_BIAS3_SOURCE"}
T1_DEFAULTS = {
    "T1_BIAS1": "1.67m", "T1_BIAS2": "1.67m", "T1_BIAS3": "35u",
    "T1_BIAS3_SOURCE": "CURRENT", "T1_R_S": "12", "T1_R_C": "12",
    "T1_CLK_MODE": "QUIET", "T1_CLK_R": "5",
}
COMPONENT_KEYS = (BVM_AREA_KEYS | BVM_RESISTANCE_KEYS | BVM_INDUCTANCE_KEYS
                  | QB_AREA_KEYS | QB_RESISTANCE_KEYS | QB_INDUCTANCE_KEYS | QB_CURRENT_KEYS
                  | CB_AREA_KEYS | CB_RESISTANCE_KEYS | CB_INDUCTANCE_KEYS | CB_CURRENT_KEYS
                  | SJTL_AREA_KEYS | SJTL_RESISTANCE_KEYS | SJTL_INDUCTANCE_KEYS
                  | SJTL_CURRENT_KEYS | BIAS_RISE_KEYS)
TOPOLOGY_SOLVER_KEYS = {
    "NAME", "ARRAY_SIZE", "MASKS", "QB_CB", "SJTL_COUNT", "POST_SJTL_CB",
    "OUTPUT_MODE", "TERM_R", "DT", "STOP", "PROBE_PROFILE",
}
USER_CASE_KEYS = TOPOLOGY_SOLVER_KEYS | COMPONENT_KEYS | T1_KEYS
STIMULUS_KEYS = {
    f"{stage}_{field}"
    for stage, fields in {
        "WRITE0": ("START", "RISE", "HOLD", "FALL", "WL", "BL", "SE"),
        "READ0": ("START", "RISE", "HOLD", "FALL", "WL", "BL", "SE"),
        "WRITE1": ("START", "RISE", "HOLD", "FALL", "WL", "BL", "SE"),
        "READ": ("START", "RISE", "HOLD", "FALL", "ACTIVE_WL", "ACTIVE_BL",
                 "ACTIVE_SE", "INACTIVE_WL", "INACTIVE_BL", "INACTIVE_SE"),
    }.items()
    for field in fields
}


def load_env(path: str | Path, expected_keys: set[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_no, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"{path}:{line_no}: expected KEY=VALUE")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key not in expected_keys:
            raise ConfigError(f"{path}:{line_no}: unknown key {key!r}")
        if key in values:
            raise ConfigError(f"{path}:{line_no}: duplicate key {key}")
        if not value:
            raise ConfigError(f"{path}:{line_no}: empty value for {key}")
        values[key] = value
    missing = sorted(expected_keys - values.keys())
    if missing:
        raise ConfigError(f"{path}: missing required keys: {', '.join(missing)}")
    return values


def parse_quantity(token: str, *, label: str) -> Decimal:
    match = NUMBER_RE.fullmatch(token.strip())
    if not match:
        raise ConfigError(f"{label}: invalid numeric value {token!r}")
    number = Decimal(match.group(1))
    suffix = match.group(2).lower()
    if suffix not in SCALE:
        raise ConfigError(f"{label}: unsupported SI suffix in {token!r}")
    if not number.is_finite():
        raise ConfigError(f"{label}: value must be finite")
    return number * SCALE[suffix]


def parse_array(value: str, *, label: str, size: int) -> list[str]:
    entries = [item.strip() for item in value.split(",")]
    if len(entries) != size or any(not item for item in entries):
        raise ConfigError(f"{label}: expected exactly {size} comma-separated values")
    return entries


def validate_user_case(values: dict[str, str]) -> dict[str, object]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", values.get("NAME", "")):
        raise ConfigError("NAME must match [A-Za-z0-9_-]+")
    try:
        size = int(values["ARRAY_SIZE"])
    except (ValueError, KeyError) as exc:
        raise ConfigError("ARRAY_SIZE must be a positive integer") from exc
    if size < 1 or str(size) != values["ARRAY_SIZE"].strip():
        raise ConfigError("ARRAY_SIZE must be a positive integer without extra syntax")

    masks = [item.strip() for item in values["MASKS"].split(",")]
    if not masks or any(not re.fullmatch(rf"[01]{{{size}}}", mask) for mask in masks):
        raise ConfigError(f"MASKS: each mask must contain exactly {size} binary digits")
    if len(set(masks)) != len(masks):
        raise ConfigError("MASKS: duplicate masks are not allowed")

    qb_cb = parse_array(values["QB_CB"], label="QB_CB", size=size)
    post_cb = parse_array(values["POST_SJTL_CB"], label="POST_SJTL_CB", size=size)
    sjtl_tokens = parse_array(values["SJTL_COUNT"], label="SJTL_COUNT", size=size)
    for index, token in enumerate(qb_cb, 1):
        if token not in {"0", "1"}:
            raise ConfigError(f"QB_CB[{index}] must be 0 or 1")
    for index, token in enumerate(post_cb, 1):
        if token not in {"0", "1"}:
            raise ConfigError(f"POST_SJTL_CB[{index}] must be 0 or 1")
    counts: list[int] = []
    for index, token in enumerate(sjtl_tokens, 1):
        if not re.fullmatch(r"\d+", token):
            raise ConfigError(f"SJTL_COUNT[{index}] must be a nonnegative integer")
        counts.append(int(token))

    output_mode = values["OUTPUT_MODE"]
    if output_mode not in {"TERMINAL", "T1"}:
        raise ConfigError("OUTPUT_MODE must be exactly 'TERMINAL' or 'T1'")
    probe_profile = values.get("PROBE_PROFILE")
    if probe_profile not in {"core", "debug"}:
        raise ConfigError("PROBE_PROFILE must be exactly 'core' or 'debug'")
    if values["T1_BIAS3_SOURCE"] not in {"CURRENT", "VOLTAGE"}:
        raise ConfigError("T1_BIAS3_SOURCE must be exactly 'CURRENT' or 'VOLTAGE'")
    term = parse_quantity(values["TERM_R"], label="TERM_R")
    dt = parse_quantity(values["DT"], label="DT")
    stop = parse_quantity(values["STOP"], label="STOP")
    if (output_mode == "TERMINAL" and term <= 0) or dt <= 0 or stop <= 0:
        raise ConfigError("TERM_R must be positive in TERMINAL mode; DT and STOP must be positive")
    if output_mode == "T1":
        if values["T1_CLK_MODE"] != "QUIET":
            raise ConfigError("T1_CLK_MODE currently supports only 'QUIET'; clock pulses are not implemented")
        for key in ("T1_BIAS1", "T1_BIAS2", "T1_BIAS3", "T1_R_S", "T1_R_C", "T1_CLK_R"):
            quantity = parse_quantity(values[key], label=key)
            if quantity <= 0:
                raise ConfigError(f"{key}: must be positive")
    for key in sorted(BVM_AREA_KEYS | QB_AREA_KEYS | CB_AREA_KEYS | SJTL_AREA_KEYS):
        _parse_positive_scalar(values[key], key)
    for key in sorted(BVM_INDUCTANCE_KEYS | QB_INDUCTANCE_KEYS
                      | CB_INDUCTANCE_KEYS | SJTL_INDUCTANCE_KEYS):
        quantity = parse_quantity(values[key], label=key)
        if quantity <= 0:
            raise ConfigError(f"{key}: must be positive")
    for key in sorted(BVM_RESISTANCE_KEYS | QB_RESISTANCE_KEYS
                      | CB_RESISTANCE_KEYS | SJTL_RESISTANCE_KEYS):
        if values[key] != "OPEN":
            quantity = parse_quantity(values[key], label=key)
            if quantity <= 0:
                raise ConfigError(f"{key}: must be positive or OPEN")
    for key in sorted(QB_CURRENT_KEYS | CB_CURRENT_KEYS | SJTL_CURRENT_KEYS):
        parse_quantity(values[key], label=key)
    for key in sorted(BIAS_RISE_KEYS):
        quantity = parse_quantity(values[key], label=key)
        if quantity <= 0:
            raise ConfigError(f"{key}: must be positive")
    return {
        "NAME": values["NAME"],
        "ARRAY_SIZE": size, "MASKS": masks,
        "QB_CB": [int(value) for value in qb_cb],
        "SJTL_COUNT": counts,
        "POST_SJTL_CB": [int(value) for value in post_cb],
        "OUTPUT_MODE": output_mode, "TERM_R": values["TERM_R"],
        "DT": values["DT"], "STOP": values["STOP"],
        "PROBE_PROFILE": probe_profile,
        **{key: values[key] for key in T1_KEYS},
        "TERM_R_OHM": term,
        "DT_SECONDS": dt,
        "STOP_SECONDS": stop,
    }


def load_user_case_snapshot(path: str | Path, *, legacy_profile: str = "debug") -> dict[str, str]:
    """Load a run/batch snapshot, mapping pre-profile snapshots to their old detail mode.

    Live USER_CASE.env is loaded strictly with load_env(USER_CASE_KEYS); this
    compatibility helper is only for immutable historical snapshots.
    """
    snapshot_lines = [
        line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    present_keys = {line.partition("=")[0].strip() for line in snapshot_lines}
    profile_present = "PROBE_PROFILE" in present_keys
    output_mode = next((line.split("=", 1)[1].strip() for line in snapshot_lines
                        if line.partition("=")[0].strip() == "OUTPUT_MODE"), None)
    missing_t1 = T1_KEYS - present_keys
    # Historical T1 Scheme-A snapshots predate the explicit source selector.
    # Their recorded 35u BIAS3 is unambiguously CURRENT; only that key gets a
    # compatibility default. Other missing T1 fields remain invalid in T1 mode.
    legacy_source_key = {"T1_BIAS3_SOURCE"}
    missing_required_t1 = missing_t1 - legacy_source_key
    if missing_required_t1 and output_mode != "TERMINAL":
        raise ConfigError(
            f"{path}: T1 snapshots are missing required keys: {', '.join(sorted(missing_required_t1))}"
        )
    expected = USER_CASE_KEYS - missing_t1
    if not profile_present:
        expected = expected - {"PROBE_PROFILE"}
    values = load_env(path, expected)
    for key in missing_t1:
        values[key] = T1_DEFAULTS[key]
    if legacy_profile not in {"core", "debug"}:
        raise ConfigError(f"invalid legacy probe profile {legacy_profile!r}")
    if not profile_present:
        values["PROBE_PROFILE"] = legacy_profile
    validate_user_case(values)
    return values


def _parse_positive_scalar(token: str, label: str) -> Decimal:
    match = NUMBER_RE.fullmatch(token.strip())
    if not match or match.group(2):
        raise ConfigError(f"{label}: expected a positive unitless number, got {token!r}")
    number = Decimal(match.group(1))
    if not number.is_finite() or number <= 0:
        raise ConfigError(f"{label}: must be positive and finite")
    return number


def format_time(seconds: Decimal) -> str:
    value = seconds / Decimal("1e-12")
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}p"
