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

USER_CASE_KEYS = {
    "ARRAY_SIZE", "MASKS", "QB_CB", "SJTL_COUNT", "POST_SJTL_CB",
    "OUTPUT_MODE", "TERM_R", "DT", "STOP",
}
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

    if values["OUTPUT_MODE"] != "TERMINAL":
        raise ConfigError("OUTPUT_MODE must be TERMINAL in platform v1")
    term = parse_quantity(values["TERM_R"], label="TERM_R")
    dt = parse_quantity(values["DT"], label="DT")
    stop = parse_quantity(values["STOP"], label="STOP")
    if term <= 0 or dt <= 0 or stop <= 0:
        raise ConfigError("TERM_R, DT, and STOP must be positive")
    return {
        "ARRAY_SIZE": size, "MASKS": masks,
        "QB_CB": [int(value) for value in qb_cb],
        "SJTL_COUNT": counts,
        "POST_SJTL_CB": [int(value) for value in post_cb],
        "OUTPUT_MODE": values["OUTPUT_MODE"], "TERM_R": values["TERM_R"],
        "DT": values["DT"], "STOP": values["STOP"],
        "TERM_R_OHM": term,
        "DT_SECONDS": dt,
        "STOP_SECONDS": stop,
    }


def format_time(seconds: Decimal) -> str:
    value = seconds / Decimal("1e-12")
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}p"
