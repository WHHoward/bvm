"""Shared configuration, source rendering, and provenance helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from stimulus import plan_stimulus

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
OLD_SERIES = REPO / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918"
OLD_SCRIPTS = OLD_SERIES / "scripts"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
JJ_SOURCE = REPO / "circuits" / "models" / "jjmit.cir"
JTL_SOURCE = REPO / "test" / "exploration" / "bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914" / "inputs" / "jtl2.cir"
USER_CASE = ROOT / "USER_CASE.env"
REFERENCE = ROOT / "REFERENCE.env"
PROFILES = ROOT / "candidate_profiles.json"
REGRESSION_MATRIX = ROOT / "REGRESSION_MATRIX.json"

BVM_KEYS = (
    "JM1_AREA", "JM2_AREA", "RJM1", "RJM2", "LM1", "LM2", "LM3", "LPM",
    "JS1_AREA", "JS2_AREA", "RSH_JS1", "RSH_JS2", "LS1", "LS2", "LS3", "RS",
    "LPSL", "RSL", "LSL", "RBL", "LPBL", "RWL", "LPWL", "RSE", "LPSE",
)
QB_KEYS = (
    "QB_LIN", "QB_BJS_AREA", "QB_L1", "QB_L2", "QB_BJ1_AREA", "QB_RJ1",
    "QB_BJ2_AREA", "QB_RJ2", "QB_L3", "QB_IB",
)
CIRCUIT_KEYS = BVM_KEYS + QB_KEYS
CONFIG_KEYS = {
    "NAME", "EXECUTION_SCOPE", "TEST_MODE", "CANDIDATE", "ARRAY_SIZE", "MASK",
    "READ_START_PS", "READ_PERIOD_PS", "READ_COUNT", "READ_WIDTH_PS",
    "READ_RISE_PS", "READ_FALL_PS", "READ_AMP_UA", "RECOVERY_TAIL_PS",
    "WRITE0_START_PS", "CONTROL_START_PS", "WRITE1_START_PS",
    "WRITE_WIDTH_PS", "WRITE_RISE_PS", "WRITE_FALL_PS", "WRITE_AMP_UA",
    "CONTROL_WIDTH_PS", "CONTROL_RISE_PS", "CONTROL_FALL_PS",
    "CONTROL_WL_AMP_UA", "CONTROL_BL_AMP_UA", "CONTROL_SE_AMP_UA",
    "REWRITE_START_PS", "STATE_SEQUENCE", "STATE_INTERVAL_PS",
    "RESET_TO_WRITE_DELAY_PS", "WRITE_TO_READ_DELAY_PS", "READ_TO_NEXT_RESET_DELAY_PS",
    "DT", "TAIL_MARGIN_MIN_PS", "TAIL_MARGIN_PERIODS",
    "BJ2_CANDIDATE_THRESHOLD_UV", "BJ2_CANDIDATE_GAP_PS",
    "TERMINAL_CANDIDATE_THRESHOLD_UV", "TERMINAL_CANDIDATE_GAP_PS",
    "LATENCY_MIN_PS", "LATENCY_MAX_PS", "PRE_WINDOW_PS", "POST_OFFSET_PS", "POST_WINDOW_PS",
    "SWEEP_ENABLED", "SWEEP_KEY", "SWEEP_VALUES",
    *CIRCUIT_KEYS,
}
TIME_KEYS = (
    "READ_START_PS", "READ_PERIOD_PS", "READ_WIDTH_PS", "READ_RISE_PS", "READ_FALL_PS",
    "RECOVERY_TAIL_PS", "WRITE0_START_PS", "CONTROL_START_PS", "WRITE1_START_PS",
    "WRITE_WIDTH_PS", "WRITE_RISE_PS", "WRITE_FALL_PS", "CONTROL_WIDTH_PS",
    "CONTROL_RISE_PS", "CONTROL_FALL_PS", "REWRITE_START_PS", "STATE_INTERVAL_PS",
    "RESET_TO_WRITE_DELAY_PS", "WRITE_TO_READ_DELAY_PS", "READ_TO_NEXT_RESET_DELAY_PS",
    "TAIL_MARGIN_MIN_PS", "PRE_WINDOW_PS", "POST_OFFSET_PS", "POST_WINDOW_PS",
    "BJ2_CANDIDATE_GAP_PS", "TERMINAL_CANDIDATE_GAP_PS", "LATENCY_MIN_PS", "LATENCY_MAX_PS",
)
AMP_KEYS = ("READ_AMP_UA", "WRITE_AMP_UA", "CONTROL_WL_AMP_UA", "CONTROL_BL_AMP_UA", "CONTROL_SE_AMP_UA",
            "BJ2_CANDIDATE_THRESHOLD_UV", "TERMINAL_CANDIDATE_THRESHOLD_UV")

if str(OLD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(OLD_SCRIPTS))
_spec = importlib.util.spec_from_file_location("repeatability_legacy_runner", OLD_SCRIPTS / "run_candidate.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load the one-shot BVM/QB renderer")
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
# Keep rendering behavior in one place while binding the templates to this experiment.
legacy.SERIES = ROOT
legacy.TUNABLE_TEMPLATE = ROOT / "circuits" / "bvm_tunable.cir"
legacy.QB_TUNABLE_TEMPLATE = ROOT / "circuits" / "bq_tunable.cir"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"invalid env entry at {path}:{line_number}")
        key, value = (part.strip() for part in stripped.split("=", 1))
        if key in values:
            raise ValueError(f"duplicate config key {key} at {path}:{line_number}")
        values[key] = value
    return values


def file_record(role: str, path: Path) -> dict[str, Any]:
    return {"role": role, "path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def git_snapshot() -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True)
    return {"head": head, "working_tree_dirty": bool(status), "status_porcelain": status}


def parse_ps(value: str, key: str) -> float:
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", str(value).strip()):
        raise ValueError(f"{key} must be unitless numeric picoseconds in USER_CASE.env")
    return float(value)


def parse_positive(value: str, key: str, allow_zero: bool = False) -> float:
    parsed = legacy.parse_number(str(value), key)
    if parsed < 0 or (parsed == 0 and not allow_zero):
        raise ValueError(f"{key} must be {'nonnegative' if allow_zero else 'positive'}")
    return parsed


def parse_overrides(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"override must be KEY=VALUE: {value!r}")
        key, val = value.split("=", 1)
        key = key.strip()
        if key in result:
            raise ValueError(f"duplicate override {key}")
        result[key] = val.strip()
    return result


def resolve_params(overrides: dict[str, str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    overrides = overrides or {}
    user = load_env(USER_CASE)
    reference = load_env(REFERENCE)
    unknown = (set(user) | set(overrides)) - CONFIG_KEYS
    if unknown:
        raise ValueError(f"unknown USER_CASE key(s): {', '.join(sorted(unknown))}")
    if set(overrides) - CONFIG_KEYS:
        raise ValueError(f"unknown override key(s): {', '.join(sorted(set(overrides) - CONFIG_KEYS))}")
    profile_data = read_json(PROFILES)
    candidate = overrides.get("CANDIDATE", user.get("CANDIDATE", ""))
    profiles = profile_data.get("profiles", {})
    if candidate not in profiles:
        raise ValueError(f"unknown CANDIDATE {candidate!r}; choose one of {', '.join(sorted(profiles))}")
    profile = profiles[candidate]
    if not isinstance(profile.get("parameters"), dict):
        raise ValueError(f"candidate profile {candidate} has no parameters object")

    values: dict[str, str] = dict(reference)
    values.update({key: str(val) for key, val in profile["parameters"].items()})
    values["ARRAY_SIZE"] = str(profile["ARRAY_SIZE"])
    values.update({key: val for key, val in user.items() if val.upper() != "AUTO"})
    values.update(overrides)
    values["CANDIDATE"] = candidate
    size = int(values["ARRAY_SIZE"])
    if size != int(profile["ARRAY_SIZE"]):
        raise ValueError(f"ARRAY_SIZE={size} does not match candidate {candidate} profile size {profile['ARRAY_SIZE']}")
    if size not in (1, 2, 3):
        raise ValueError("this registered platform currently supports candidate fan-in sizes 1, 2, and 3")
    mask = values.get("MASK", "")
    if len(mask) != size or any(bit not in "01" for bit in mask):
        raise ValueError(f"MASK must contain exactly ARRAY_SIZE={size} binary characters")
    mode = values.get("TEST_MODE", "")
    if mode not in {"REPEAT_READ", "RECOVERY_PROBE", "REWRITE_READ"}:
        raise ValueError("TEST_MODE must be REPEAT_READ, RECOVERY_PROBE, or REWRITE_READ")
    if values.get("EXECUTION_SCOPE", "REGRESSION_MATRIX") not in {"REGRESSION_MATRIX", "MANUAL"}:
        raise ValueError("EXECUTION_SCOPE must be REGRESSION_MATRIX or MANUAL")
    name = values.get("NAME", "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
        raise ValueError("NAME must be a filesystem-safe run identifier")

    for key in CIRCUIT_KEYS:
        if key not in values:
            raise ValueError(f"missing effective circuit parameter {key}")
    for key in ("JM1_AREA", "JM2_AREA", "JS1_AREA", "JS2_AREA", "LS1", "LS2", "LS3", "LPSL", "LSL",
                "LPBL", "LPWL", "LPSE", "LM1", "LM2", "LM3", "LPM", "QB_LIN", "QB_BJS_AREA", "QB_L1",
                "QB_L2", "QB_BJ1_AREA", "QB_BJ2_AREA", "QB_L3", "QB_IB", "RBL", "RWL", "RSE", "RSL", "RS",
                "QB_RJ1", "QB_RJ2"):
        if parse_positive(values[key], key) <= 0:
            raise ValueError(f"{key} must be positive")
    for key in ("RJM1", "RJM2", "RSH_JS1", "RSH_JS2"):
        if values[key].upper() != "OPEN" and parse_positive(values[key], key) <= 0:
            raise ValueError(f"{key} must be OPEN or positive")

    numeric_ps = [key for key in TIME_KEYS]
    for key in numeric_ps:
        if key in values and values[key].upper() != "AUTO":
            if parse_ps(values[key], key) < 0:
                raise ValueError(f"{key} must not be negative")
    for key in ("READ_PERIOD_PS", "READ_WIDTH_PS", "READ_RISE_PS", "READ_FALL_PS",
                "WRITE_WIDTH_PS", "WRITE_RISE_PS", "WRITE_FALL_PS",
                "CONTROL_WIDTH_PS", "CONTROL_RISE_PS", "CONTROL_FALL_PS",
                "TAIL_MARGIN_MIN_PS", "PRE_WINDOW_PS", "POST_WINDOW_PS",
                "BJ2_CANDIDATE_THRESHOLD_UV", "TERMINAL_CANDIDATE_THRESHOLD_UV"):
        if parse_ps(values[key], key) <= 0:
            raise ValueError(f"{key} must be positive")
    for key in ("BJ2_CANDIDATE_GAP_PS", "TERMINAL_CANDIDATE_GAP_PS"):
        if parse_ps(values[key], key) < 0:
            raise ValueError(f"{key} must be nonnegative")
    if parse_ps(values["LATENCY_MAX_PS"], "LATENCY_MAX_PS") <= parse_ps(values["LATENCY_MIN_PS"], "LATENCY_MIN_PS"):
        raise ValueError("LATENCY_MAX_PS must be greater than LATENCY_MIN_PS")
    for key in AMP_KEYS:
        parse_ps(values[key], key)
    for key in ("READ_COUNT", "TAIL_MARGIN_PERIODS"):
        try:
            integer = int(values[key])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{key} must be an integer") from exc
        if integer <= 0:
            raise ValueError(f"{key} must be positive")
    if values.get("SWEEP_ENABLED", "no").lower() not in {"yes", "no"}:
        raise ValueError("SWEEP_ENABLED must be yes or no")
    dt_seconds = legacy.parse_number(values["DT"], "DT")
    if dt_seconds <= 0:
        raise ValueError("DT must be positive")

    params: dict[str, Any] = dict(values)
    params.update({"ARRAY_SIZE": size, "MODE": "closed", "MASKS": [mask],
                   "BIT_ORDER": legacy.fan_in.bit_order(size), "TEST_MODE": mode,
                   "_DT_SECONDS": dt_seconds,
                   "_USER_CASE_SHA256": sha256(USER_CASE),
                   "_REFERENCE_SHA256": sha256(REFERENCE),
                   "_PROFILE_SHA256": sha256(PROFILES)})
    if mode == "REWRITE_READ":
        states = [item.strip() for item in str(params["STATE_SEQUENCE"]).split(",") if item.strip()]
        if not states or any(len(state) != size or any(bit not in "01" for bit in state) for state in states):
            raise ValueError("STATE_SEQUENCE must be a comma-separated list of ARRAY_SIZE-bit binary states")
        params["READ_COUNT"] = len(states)
    else:
        count = int(params["READ_COUNT"])
        if mode == "RECOVERY_PROBE" and count != 1:
            raise ValueError("RECOVERY_PROBE requires READ_COUNT=1")
        if count < 1:
            raise ValueError("READ_COUNT must be at least 1")
    if mode == "RECOVERY_PROBE" and parse_ps(str(params["RECOVERY_TAIL_PS"]), "RECOVERY_TAIL_PS") <= 0:
        raise ValueError("RECOVERY_TAIL_PS must be positive")
    if mode in {"REPEAT_READ", "RECOVERY_PROBE"}:
        preamble = ((parse_ps(params["WRITE0_START_PS"], "WRITE0_START_PS"), parse_ps(params["WRITE_WIDTH_PS"], "WRITE_WIDTH_PS")),
                    (parse_ps(params["CONTROL_START_PS"], "CONTROL_START_PS"), parse_ps(params["CONTROL_WIDTH_PS"], "CONTROL_WIDTH_PS")),
                    (parse_ps(params["WRITE1_START_PS"], "WRITE1_START_PS"), parse_ps(params["WRITE_WIDTH_PS"], "WRITE_WIDTH_PS")))
        if any(left[0] + left[1] > right[0] + 1e-9 for left, right in zip(preamble, preamble[1:])):
            raise ValueError("WRITE0, CONTROL, and WRITE1 pulse windows must be ordered and non-overlapping")
        if mode == "REPEAT_READ" and preamble[-1][0] + preamble[-1][1] > parse_ps(params["READ_START_PS"], "READ_START_PS") + 1e-9:
            raise ValueError("first READ must not overlap WRITE1")
    if mode == "REPEAT_READ" and parse_ps(params["READ_WIDTH_PS"], "READ_WIDTH_PS") > parse_ps(params["READ_PERIOD_PS"], "READ_PERIOD_PS"):
        raise ValueError("READ_WIDTH_PS must not exceed READ_PERIOD_PS")

    # Call planning once here so configuration errors stop before any directory or solve.
    plan = plan_stimulus(params)
    params["STOP_PS"] = plan["stop_ps"]
    params["STOP"] = f"{plan['stop_ps']:g}p"
    return params, plan


def public_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if not key.startswith("_")}


def snapshot_sources(run_dir: Path, params: dict[str, Any]) -> dict[str, Path]:
    sources = legacy.snapshot_sources(run_dir, params)
    return sources


def render_deck(run_dir: Path, params: dict[str, Any], sources: dict[str, Path], stimulus_path: Path) -> str:
    template = (ROOT / "circuits" / "top_template.cir").read_text(encoding="utf-8")
    replacements = {
        "{{JJ_INCLUDE}}": legacy.include_line(sources["JJ_MODEL"], run_dir, "JJ_MODEL"),
        "{{BVM_INCLUDE}}": legacy.include_line(sources["BVM"], run_dir, "BVM"),
        "{{QB_INCLUDE}}": legacy.include_line(sources["QB"], run_dir, "QB"),
        "{{JTL_INCLUDE}}": legacy.include_line(sources["JTL"], run_dir, "JTL"),
        "{{STIMULUS_INCLUDE}}": legacy.include_line(stimulus_path, run_dir, "STIMULUS"),
        "{{BVM_INSTANCES}}": legacy.fan_in.bvm_instances(params["ARRAY_SIZE"]),
        "{{PROBES}}": "\n".join(legacy.probe_lines("closed", params)),
        "{{DT}}": params["DT"], "{{STOP_TIME}}": params["STOP"],
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    if "{{" in template:
        raise ValueError("unresolved marker in rendered top deck")
    if any(token in template.upper() for token in ("MERGE", "MERGET")):
        raise ValueError("forbidden topology token found in generated deck")
    instance_lines = [line.strip() for line in template.splitlines()
                      if re.match(r"^XBVM\d+\s", line.strip())]
    if len(instance_lines) != int(params["ARRAY_SIZE"]):
        raise ValueError("rendered BVM instance count does not match ARRAY_SIZE")
    if "R_TERM JTL6_OUT 0 10" not in template:
        raise ValueError("rendered top deck is missing the registered terminal")
    return template


def source_manifest(run_dir: Path, params: dict[str, Any], sources: dict[str, Path],
                    reference_run: Path | None = None) -> dict[str, Any]:
    records = [file_record(role, path) for role, path in sources.items()]
    inputs = (
        ("BVM_TEMPLATE", ROOT / "circuits" / "bvm_tunable.cir"),
        ("QB_TEMPLATE", ROOT / "circuits" / "bq_tunable.cir"),
        ("TOP_TEMPLATE", ROOT / "circuits" / "top_template.cir"),
        ("USER_CASE", USER_CASE), ("REFERENCE", REFERENCE), ("CANDIDATE_PROFILES", PROFILES),
        ("ONE_SHOT_RENDERER", OLD_SCRIPTS / "run_candidate.py"),
        ("ARRAY_MASK_HELPER", OLD_SCRIPTS / "fan_in.py"),
        ("PLOTTER", PLOTTER),
    )
    records.extend(file_record(role, path) for role, path in inputs)
    if reference_run is not None:
        reference_raw = reference_run / "raw.csv"
        if not reference_raw.is_file():
            raise ValueError(f"reference raw missing: {reference_raw}")
        records.append(file_record("HISTORICAL_REFERENCE_RAW", reference_raw))
    return {
        "schema": "bvm-qb-repeatability-source-manifest-v1",
        "created_at": now(), "run_id": run_dir.name,
        "git": git_snapshot(), "raw_not_copied_from_history": True,
        "parameters": public_params(params), "sources": records,
        "rendered_bvm_snapshot": next((x for x in records if x["role"] == "BVM"), None),
        "rendered_qb_snapshot": next((x for x in records if x["role"] == "QB"), None),
        "jj_model_snapshot": next((x for x in records if x["role"] == "JJ_MODEL"), None),
        "jtl_snapshot": next((x for x in records if x["role"] == "JTL"), None),
        "reference_run": repo_rel(reference_run) if reference_run else None,
    }


def solver_identity() -> dict[str, Any]:
    version = subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True).strip()
    return {"path": repo_rel(SOLVER), "sha256": sha256(SOLVER), "version": version}


def safe_run_dir(params: dict[str, Any]) -> Path:
    runs = ROOT / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    base = str(params["NAME"])
    candidate = runs / base
    if not candidate.exists():
        return candidate
    attempt = 2
    while (runs / f"{base}_attempt{attempt}").exists():
        attempt += 1
    return runs / f"{base}_attempt{attempt}"


def resolve_run_dir(run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("RUN_ID must be a single filesystem-safe identifier under this experiment's runs/")
    runs_root = (ROOT / "runs").resolve()
    run_dir = (runs_root / run_id).resolve()
    if not run_dir.is_relative_to(runs_root) or run_dir.parent != runs_root:
        raise ValueError("RUN_ID escapes this experiment's runs/ directory")
    return run_dir
