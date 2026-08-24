#!/usr/bin/env python3
"""Validate BVM READ protocol semantics and source-lineage labels.

This validator is deliberately independent of JoSIM execution and of waveform
visualization.  It parses the current source PWLs in a deck, or consumes an
explicit inherited protocol signature for ideal replay decks.  A filename such
as ``logical0-read.cir`` is never sufficient evidence for a canonical logical0
READ.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
READ_CUTOFF_PS = 50.0
EPS = 1e-9


def _number(token: str, *, time: bool = False) -> float:
    token = token.strip().replace("+", "")
    match = re.fullmatch(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)([a-zA-Z]*)", token)
    if not match:
        raise ValueError(f"cannot parse numeric token {token!r}")
    value = float(match.group(1))
    suffix = match.group(2).lower()
    factors = {"": 1.0, "p": 1e-12, "n": 1e-9, "u": 1e-6,
               "m": 1e-3, "k": 1e3, "meg": 1e6}
    if suffix not in factors:
        raise ValueError(f"unsupported suffix {suffix!r} in {token!r}")
    scaled = value * factors[suffix]
    return scaled / 1e-12 if time else scaled / 1e-6


def _pwl_points(text: str, source: str) -> list[tuple[float, float]]:
    pattern = re.compile(
        rf"^\s*I_{re.escape(source)}\b[^\n]*?pwl\(([^)]*)\)",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return []
    tokens = match.group(1).replace("\n", " ").split()
    if len(tokens) % 2:
        raise ValueError(f"odd PWL token count for I_{source}")
    points = []
    for i in range(0, len(tokens), 2):
        points.append((_number(tokens[i], time=True), _number(tokens[i + 1])))
    return points


def _first_nonzero(points: list[tuple[float, float]], after: float = -math.inf) -> tuple[float, float] | None:
    for t, value in points:
        if t >= after and abs(value) > EPS:
            return t, value
    return None


def _last_nonzero(points: list[tuple[float, float]], after: float = -math.inf) -> tuple[float, float] | None:
    found = None
    for t, value in points:
        if t >= after and abs(value) > EPS:
            found = (t, value)
    return found


def _pulse_shape(points: list[tuple[float, float]], after: float) -> dict[str, Any] | None:
    first = _first_nonzero(points, after)
    last = _last_nonzero(points, after)
    if first is None or last is None:
        return None
    first_i = next(i for i, point in enumerate(points) if point == first)
    last_i = max(i for i, point in enumerate(points) if point == last)
    previous_t = points[first_i - 1][0] if first_i else first[0]
    next_t = points[last_i + 1][0] if last_i + 1 < len(points) else last[0]
    return {
        "amplitude_uA": round(first[1], 9),
        "onset_ps": round(first[0], 9),
        "end_ps": round(last[0], 9),
        "plateau_ps": round(last[0] - first[0], 9),
        "rise_ps": round(first[0] - previous_t, 9),
        "fall_ps": round(next_t - last[0], 9),
        "nonzero_points": [[round(t, 9), round(v, 9)] for t, v in points if t >= after and abs(v) > EPS],
    }


def _initialization_protocol(
    wl: list[tuple[float, float]],
    bl: list[tuple[float, float]],
    read_onset: float | None,
) -> dict[str, Any]:
    """Describe the stored-state initialization before the READ pulse.

    Looking only at the first non-zero sample is unsafe: a fixture can start
    with a negative initialization and then reverse polarity before READ.
    Such a waveform must not be accepted as a canonical negative state.
    """
    cutoff = read_onset if read_onset is not None else READ_CUTOFF_PS

    def channel(points: list[tuple[float, float]]) -> dict[str, Any]:
        nonzero = [(t, v) for t, v in points if 0.0 <= t < cutoff and abs(v) > EPS]
        signs = sorted({1 if v > 0 else -1 for _, v in nonzero})
        magnitudes = [abs(v) for _, v in nonzero]
        first = nonzero[0] if nonzero else None
        last = nonzero[-1] if nonzero else None
        return {
            "first_uA": round(first[1], 9) if first else None,
            "last_uA": round(last[1], 9) if last else None,
            "onset_ps": round(first[0], 9) if first else None,
            "end_ps": round(last[0], 9) if last else None,
            "signs": signs,
            "sign": ("positive" if signs == [1] else
                     "negative" if signs == [-1] else
                     "mixed" if signs else "none"),
            "nonzero_points": [[round(t, 9), round(v, 9)] for t, v in nonzero],
            "magnitude_min_uA": round(min(magnitudes), 9) if magnitudes else None,
            "magnitude_max_uA": round(max(magnitudes), 9) if magnitudes else None,
        }

    wl_info = channel(wl)
    bl_info = channel(bl)
    same_single_sign = (
        wl_info["sign"] in {"positive", "negative"}
        and wl_info["sign"] == bl_info["sign"]
    )
    magnitudes = [
        value
        for info in (wl_info, bl_info)
        for value in (info["magnitude_min_uA"], info["magnitude_max_uA"])
        if value is not None
    ]
    magnitude_consistent = bool(magnitudes) and max(magnitudes) - min(magnitudes) <= 1e-6
    sign_reversal = any(info["sign"] == "mixed" for info in (wl_info, bl_info))
    return {
        "read_cutoff_ps": round(cutoff, 9),
        "wl": wl_info,
        "bl": bl_info,
        "plateau_consistent": bool(same_single_sign and magnitude_consistent),
        "sign_reversal": sign_reversal,
        "valid": bool(same_single_sign and magnitude_consistent and not sign_reversal),
        "error": None if same_single_sign and magnitude_consistent and not sign_reversal
                  else "INITIALIZATION_PROTOCOL_MISMATCH",
    }


def _initial_state(
    wl: list[tuple[float, float]], bl: list[tuple[float, float]], read_onset: float | None
) -> str:
    profile = _initialization_protocol(wl, bl, read_onset)
    if not profile["valid"]:
        return "unknown"
    if profile["wl"]["sign"] == "positive":
        return "logical1"
    if profile["wl"]["sign"] == "negative":
        return "logical0"
    return "unknown"


def _load_topology(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]
    jsl_count = sum(1 for line in lines if re.match(r"B_LD\d+\s", line))
    has_replay = any(re.match(r"I_REPLAY\b", line) for line in lines)
    has_jtl = any("JTL" in line.upper() or re.search(r"XJTL\b", line, re.IGNORECASE) for line in lines)
    loads = []
    for line in lines:
        if re.match(r"(?:R_LD|R_LOAD|RISO|LISO)\b", line, re.IGNORECASE):
            loads.append(re.sub(r"\s+", " ", line))
    if jsl_count == 12:
        kind = "external_series_12x_JSL"
    elif has_replay:
        kind = "ideal_current_replay_to_QB"
    elif has_jtl:
        kind = "JTL_or_receiver_fixture"
    else:
        kind = "direct_BVM_or_unknown"
    return {"kind": kind, "jsl_count": jsl_count, "loads": loads}


def protocol_signature(parsed: dict[str, Any]) -> dict[str, Any]:
    read = parsed.get("read_protocol", {})
    if not read:
        return {"has_read": False}
    wl = read.get("wl") or {}
    se = read.get("se") or {}
    return {
        "has_read": bool(read.get("has_read")),
        "wl_amplitude_uA": wl.get("amplitude_uA"),
        "se_amplitude_uA": se.get("amplitude_uA"),
        "onset_ps": read.get("onset_ps"),
        "plateau_ps": wl.get("plateau_ps") if wl else (se.get("plateau_ps") if se else None),
        "rise_ps": wl.get("rise_ps") if wl else (se.get("rise_ps") if se else None),
        "fall_ps": wl.get("fall_ps") if wl else (se.get("fall_ps") if se else None),
        "wl_points": wl.get("nonzero_points", []),
        "se_points": se.get("nonzero_points", []),
    }


def classify_parsed(parsed: dict[str, Any]) -> dict[str, Any]:
    state = parsed["stored_state"]
    read = parsed["read_protocol"]
    if not parsed.get("initialization_protocol", {}).get("valid", False):
        parsed["case_role"] = "SUPERSEDED_INVALID_INIT_FIXTURE"
        parsed["classification"] = "INITIALIZATION_PROTOCOL_MISMATCH"
        parsed["current_validity"] = "SUPERSEDED_INVALID_INIT_FIXTURE"
        return parsed
    if not read.get("has_read"):
        parsed["case_role"] = f"{state}_no_read_control" if state in {"logical0", "logical1"} else "NO_READ_CONTROL"
        parsed["classification"] = "NO_READ_CONTROL"
        parsed["current_validity"] = "VALID_WITH_RELABELED_CONTROL"
        return parsed
    wl = read.get("wl") or {}
    se = read.get("se") or {}
    wl_amp = float(wl.get("amplitude_uA", 0.0))
    se_amp = float(se.get("amplitude_uA", 0.0))
    canonical = (
        abs(wl_amp - 100.0) < 1e-6
        and abs(se_amp - 100.0) < 1e-6
        and read.get("onset_ps") is not None
        and read.get("wl", {}).get("onset_ps") == read.get("se", {}).get("onset_ps")
        and read.get("wl", {}).get("plateau_ps") == read.get("se", {}).get("plateau_ps")
        and read.get("wl", {}).get("rise_ps") == read.get("se", {}).get("rise_ps")
        and read.get("wl", {}).get("fall_ps") == read.get("se", {}).get("fall_ps")
    )
    if state == "logical1" and canonical:
        parsed["case_role"] = "logical1_read"
        parsed["classification"] = "CANONICAL_LOGICAL1_READ_V1"
        parsed["current_validity"] = "CURRENT_VALID"
    elif state == "logical0" and canonical:
        parsed["case_role"] = "logical0_read"
        parsed["classification"] = "CANONICAL_LOGICAL0_READ_V1"
        parsed["current_validity"] = "CURRENT_VALID"
    elif state == "logical0" and abs(wl_amp - 100.0) < 1e-6 and abs(se_amp) < 1e-6:
        parsed["case_role"] = "WL_ONLY_NEGATIVE_STATE_DIAGNOSTIC"
        parsed["classification"] = "NONCANONICAL_WL_ONLY_LOGICAL0_SOURCE"
        parsed["current_validity"] = "LOGICAL0_GATE_NOT_TESTED"
    elif abs(wl_amp + 100.0) < 1e-6 or abs(se_amp + 100.0) < 1e-6:
        parsed["case_role"] = "NEGATIVE_POLARITY_READ_DIAGNOSTIC"
        parsed["classification"] = "NEGATIVE_POLARITY_READ"
        parsed["current_validity"] = "VALID_WITH_RELABELED_CONTROL"
    else:
        parsed["case_role"] = "READ_PROTOCOL_DIAGNOSTIC"
        parsed["classification"] = "NONCANONICAL_READ_PROTOCOL"
        parsed["current_validity"] = "LOGICAL0_GATE_NOT_TESTED" if state == "logical0" else "VALID_WITH_RELABELED_CONTROL"
    return parsed


def parse_deck(path: str | Path, *, inherited_protocol: dict[str, Any] | None = None,
               lineage: list[str] | None = None, role_hint: str | None = None) -> dict[str, Any]:
    deck_path = Path(path)
    text = deck_path.read_text(encoding="utf-8")
    wl = _pwl_points(text, "WL1")
    bl = _pwl_points(text, "BL1")
    se = _pwl_points(text, "SE1")
    if inherited_protocol is not None:
        read = {"has_read": bool(inherited_protocol.get("has_read")), "inherited": True}
        stored_state = "logical0" if "logical0" in (role_hint or deck_path.name).lower() else "logical1"
    else:
        wl_read = _pulse_shape(wl, READ_CUTOFF_PS)
        se_read = _pulse_shape(se, READ_CUTOFF_PS)
        onset_candidates = [p["onset_ps"] for p in (wl_read, se_read) if p]
        onset = min(onset_candidates) if onset_candidates else None
        read = {
            "has_read": bool(wl_read or se_read),
            "onset_ps": onset,
            "wl": wl_read,
            "se": se_read,
        }
        stored_state = _initial_state(wl, bl, onset)
        initialization_protocol = _initialization_protocol(wl, bl, onset)
    if inherited_protocol is not None:
        initialization_protocol = {
            "inherited": True,
            "valid": True,
            "plateau_consistent": True,
            "sign_reversal": False,
        }
    parsed = {
        "path": str(deck_path),
        "stored_state": stored_state,
        "initialization": {
            "wl_first_uA": next((round(v, 9) for t, v in wl if t < READ_CUTOFF_PS and abs(v) > EPS), None),
            "bl_first_uA": next((round(v, 9) for t, v in bl if t < READ_CUTOFF_PS and abs(v) > EPS), None),
        },
        "initialization_protocol": initialization_protocol,
        "read_protocol": read,
        "protocol_signature": inherited_protocol if inherited_protocol is not None else None,
        "load_topology": _load_topology(text),
        "source_lineage": lineage or [str(deck_path)],
        "role_hint": role_hint,
    }
    if inherited_protocol is None:
        parsed["protocol_signature"] = protocol_signature(parsed)
    if inherited_protocol is not None:
        # Replay decks have no WL/SE sources; their role and validity are
        # determined by the inherited source chain, not by their filename.
        parsed["case_role"] = role_hint or "INHERITED_REPLAY"
        parsed["classification"] = "INHERITED_PROTOCOL"
        parsed["current_validity"] = "CURRENT_VALID" if parsed["case_role"] != "logical0_read" else "LOGICAL0_GATE_NOT_TESTED"
        if parsed["case_role"] in {"logical1_no_read_control", "logical0_no_read_control"}:
            parsed["current_validity"] = "VALID_WITH_RELABELED_CONTROL"
        return parsed
    return classify_parsed(parsed)


def _norm(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def protocols_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return _norm(a) == _norm(b)


def validate_pair(logical1: dict[str, Any], logical0: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if logical1.get("case_role") != "logical1_read":
        errors.append("logical1 case is not classified as logical1_read")
    if logical0.get("case_role") != "logical0_read":
        errors.append("logical0 case is not classified as canonical logical0_read")
    if logical1.get("protocol_signature") is not None and logical0.get("protocol_signature") is not None:
        if not protocols_match(logical1["protocol_signature"], logical0["protocol_signature"]):
            errors.append("READ_PROTOCOL_MISMATCH")
    for field in ("load_topology",):
        if _norm(logical1.get(field)) != _norm(logical0.get(field)):
            errors.append(f"READ_PROTOCOL_MISMATCH:{field}")
    return errors


def validate_manifest(manifest: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    cases = {case["id"]: case for case in manifest.get("cases", [])}
    for case_id, case in cases.items():
        path = root / case["path"] if not Path(case["path"]).is_absolute() else Path(case["path"])
        if not path.exists():
            errors.append(f"missing fixture: {case_id}: {path}")
        inherited = bool(case.get("read_protocol", {}).get("inherited"))
        if case.get("case_role") == "logical0_read" and not inherited and case.get("classification") != "CANONICAL_LOGICAL0_READ_V1":
            errors.append(f"logical0 labeled canonical without canonical classification: {case_id}")
        if case.get("classification") == "NONCANONICAL_WL_ONLY_LOGICAL0_SOURCE" and case.get("case_role") == "logical0_read":
            errors.append(f"WL-only logical0 mislabeled as logical0_read: {case_id}")
    for pair in manifest.get("matched_pairs", []):
        l1 = cases.get(pair["logical1_read"])
        l0 = cases.get(pair["logical0_read"])
        if not l1 or not l0:
            errors.append(f"missing matched-pair member: {pair}")
            continue
        errors.extend(f"{pair.get('id', 'pair')}: {message}" for message in validate_pair(l1, l0))
    for pair in manifest.get("mismatched_pairs", []):
        l1 = cases.get(pair["logical1_read"])
        l0 = cases.get(pair["logical0_read"])
        if not l1 or not l0:
            errors.append(f"missing mismatch-pair member: {pair}")
            continue
        pair_errors = validate_pair(l1, l0)
        if "READ_PROTOCOL_MISMATCH" not in " ".join(pair_errors) and l0.get("case_role") == "logical0_read":
            errors.append(f"expected noncanonical pair was not detected: {pair.get('id', 'pair')}")
        if l0.get("current_validity") == "CURRENT_VALID":
            errors.append(f"noncanonical logical0 pair was left current-valid: {pair.get('id', 'pair')}")
    for edge in manifest.get("lineage_edges", []):
        child = cases.get(edge.get("child"))
        parent = cases.get(edge.get("parent"))
        if not child or not parent:
            errors.append(f"lineage edge references missing case: {edge}")
        elif child.get("case_role") == "logical0_read" and parent.get("current_validity") == "LOGICAL0_GATE_NOT_TESTED" and child.get("current_validity") == "CURRENT_VALID":
            errors.append(f"inherited noncanonical logical0 must not be canonical: {edge.get('child')}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "case_count": len(cases), "matched_pair_count": len(manifest.get("matched_pairs", []))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=ROOT / "docs/BVM_READ_SEMANTICS_MANIFEST.yaml")
    ap.add_argument("--output", type=Path, default=ROOT / "bvm-read-semantics-validation.json")
    args = ap.parse_args()
    data = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    result = validate_manifest(data)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
