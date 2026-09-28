"""Manifest-driven closure and mechanical validation for scientific packages."""

from __future__ import annotations

import hashlib
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import ConfigError, T1_KEYS, load_user_case_snapshot, validate_user_case


PLOT_PATHS = {
    "plots/01_overview.html", "plots/02_bvm.html", "plots/03_qb.html",
    "plots/04_cb.html", "plots/05_acc_gap.html",
}
T1_PLOT_PATHS = PLOT_PATHS | {"plots/06_t1.html"}


def plot_paths_for_mode(output_mode: str) -> set[str]:
    if output_mode == "TERMINAL":
        return set(PLOT_PATHS)
    if output_mode == "T1":
        return set(T1_PLOT_PATHS)
    raise EvidenceError(f"unsupported output mode for plot closure: {output_mode!r}")
BATCH_FILES = (
    "batch_manifest.json", "parameter_manifest.json", "USER_CASE.effective.env",
    "STIMULUS.effective.env", "BATCH_SUMMARY.md",
)
RUN_FILES = (
    "PREFLIGHT.md", "RESULT_BRIEF.md", "USER_CASE.snapshot.env",
    "STIMULUS.snapshot.env", "actual_deck.cir", "stimulus.inc",
    "parameter_manifest.json", "topology_manifest.json", "probe_manifest.json",
    "source_manifest.json", "provenance.json", "result.json", "raw.csv", "run.log",
    "stdout.txt", "stderr.txt", "analysis/raw_qa.json",
    "analysis/mechanical_metrics.json", "analysis/plot_manifest.json",
    "analysis/plot_qa.json",
)


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PackageMember:
    source: Path
    archive_path: str
    category: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be a JSON object: {path}")
    return value


def safe_file(root: Path, relative: str, label: str) -> Path:
    unresolved = root / relative
    cursor = unresolved
    while cursor == root or root in cursor.parents:
        if cursor.is_symlink():
            raise EvidenceError(f"{label} path contains a symlink: {relative}")
        if cursor == root:
            break
        cursor = cursor.parent
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise EvidenceError(f"{label} path escapes its root: {relative}") from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise EvidenceError(f"{label} is missing or not a regular file: {relative}")
    return candidate


def _add_member(members: dict[str, PackageMember], root: Path,
                relative: str, category: str) -> PackageMember:
    source = safe_file(root, relative, "package evidence")
    member = PackageMember(source=source, archive_path=relative, category=category)
    previous = members.get(relative)
    if previous and (previous.source != member.source or previous.category != category):
        raise EvidenceError(f"conflicting package member mapping: {relative}")
    members[relative] = member
    return member


def _verify_hash(path: Path, expected: Any, label: str) -> str:
    actual = sha256(path)
    if not isinstance(expected, str) or expected != actual:
        raise EvidenceError(f"{label} SHA-256 mismatch: {path}")
    return actual


def _independent_t1_link_metric(raw_path: Path) -> tuple[float, int]:
    """Independently reproduce the report-only link max directly from CSV rows."""
    with raw_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise EvidenceError("T1 raw CSV is empty") from exc
        final_matches = [index for index, value in enumerate(headers) if value == "V(FINAL_OUT)"]
        input_matches = [index for index, value in enumerate(headers) if value == "V(T1_I)"]
        if len(final_matches) != 1 or len(input_matches) != 1:
            raise EvidenceError("T1 raw requires unique V(FINAL_OUT) and V(T1_I) columns")
        max_difference = 0.0
        count = 0
        for line_number, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(headers):
                raise EvidenceError(f"T1 raw row {line_number} has an inconsistent field count")
            try:
                final_value = float(row[final_matches[0]])
                input_value = float(row[input_matches[0]])
            except ValueError as exc:
                raise EvidenceError(f"T1 link voltage is non-numeric at raw row {line_number}") from exc
            if not math.isfinite(final_value) or not math.isfinite(input_value):
                raise EvidenceError(f"T1 link voltage is non-finite at raw row {line_number}")
            max_difference = max(max_difference, abs(final_value - input_value))
            count += 1
    if count < 2:
        raise EvidenceError("T1 raw link metric requires at least two stored rows")
    return max_difference, count


def _normalize_raw_reference(series_root: Path, raw_path: str) -> str:
    value = raw_path.replace("\\", "/").lstrip("/")
    prefixes = (f"test/exploration/{series_root.name}/", f"{series_root.name}/")
    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    parts = Path(value).parts
    if len(parts) < 3 or parts[0] != "runs" or parts[-1] != "raw.csv":
        raise EvidenceError(f"invalid reused raw path: {raw_path!r}")
    return Path(*parts).as_posix()


def validate_complete_batch(batch_dir: Path, series_root: Path, *, include_plots: bool,
                            known_cases: dict[str, dict[str, str]] | None = None
                            ) -> dict[str, Any] | None:
    """Select only COMPLETE_MECHANICAL batches and runs they explicitly name.

    Non-complete attempts are skipped and remain untouched. A manifest that claims
    COMPLETE_MECHANICAL but fails closure/hash checks is a hard error.
    """
    series_root = series_root.resolve()
    batch_dir = batch_dir.resolve()
    manifest_path = batch_dir / "batch_manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = read_json(manifest_path, "batch_manifest.json")
    if manifest.get("status") != "COMPLETE_MECHANICAL":
        return None

    batch_id = str(manifest.get("batch_id", ""))
    if not batch_id or batch_dir.name != batch_id:
        raise EvidenceError(f"batch identity/path mismatch: {batch_dir}")
    run_rows = manifest.get("runs")
    masks = manifest.get("requested_masks")
    size = manifest.get("array_size")
    if not isinstance(size, int) or size < 1 or not isinstance(masks, list) or not masks:
        raise EvidenceError(f"{batch_id}: malformed array_size/requested_masks")
    if not isinstance(run_rows, list) or len(run_rows) != len(masks):
        raise EvidenceError(f"{batch_id}: COMPLETE batch does not have one run row per mask")
    try:
        user_path = batch_dir / "USER_CASE.effective.env"
        user = load_user_case_snapshot(user_path)
        parsed = validate_user_case(user)
    except (OSError, ValueError, KeyError) as exc:
        raise EvidenceError(f"{batch_id}: invalid effective USER_CASE: {exc}") from exc
    if (user.get("NAME") != manifest.get("name") or parsed["ARRAY_SIZE"] != size
            or parsed["MASKS"] != masks or user["PROBE_PROFILE"] != manifest.get("probe_profile", "debug")):
        raise EvidenceError(f"{batch_id}: manifest disagrees with effective USER_CASE snapshot")
    output_mode = str(parsed["OUTPUT_MODE"])
    expected_plot_paths = plot_paths_for_mode(output_mode)
    if manifest.get("output_mode", "TERMINAL") != output_mode:
        raise EvidenceError(f"{batch_id}: batch output mode disagrees with effective USER_CASE snapshot")

    for filename, hash_key in (
        ("USER_CASE.effective.env", "effective_user_case_sha256"),
        ("STIMULUS.effective.env", "effective_stimulus_sha256"),
        ("parameter_manifest.json", "parameter_manifest_sha256"),
    ):
        path = safe_file(batch_dir, filename, f"{batch_id} batch metadata")
        _verify_hash(path, manifest.get(hash_key), f"{batch_id}/{filename}")
    parameter_data = read_json(batch_dir / "parameter_manifest.json", "batch parameter manifest")
    acquisition = parameter_data.get("acquisition", {})
    if isinstance(acquisition, dict) and acquisition.get("probe_profile", "debug") != user["PROBE_PROFILE"]:
        raise EvidenceError(f"{batch_id}: parameter manifest PROBE_PROFILE mismatch")
    required_groups = {"bvm", "qb", "cb", "sjtl", "topology", "solver", "stimulus_reference"}
    if output_mode == "T1":
        required_groups.add("t1")
    if not required_groups.issubset(parameter_data):
        raise EvidenceError(f"{batch_id}: parameter manifest is missing required groups")
    if output_mode == "T1":
        snapshot_keys = {
            line.partition("=")[0].strip()
            for line in user_path.read_text(encoding="utf-8").splitlines()
            if "=" in line and not line.lstrip().startswith("#")
        }
        expected_t1 = {key: user[key] for key in sorted(T1_KEYS & snapshot_keys)}
        actual_t1 = parameter_data.get("t1")
        if not isinstance(actual_t1, dict) or actual_t1 != expected_t1:
            raise EvidenceError(f"{batch_id}: T1 parameter manifest disagrees with effective USER_CASE")

    members: dict[str, PackageMember] = {}
    for filename in BATCH_FILES:
        batch_relative = batch_dir.relative_to(series_root).as_posix()
        _add_member(members, series_root, f"{batch_relative}/{filename}", "batch_metadata")

    references: list[dict[str, str]] = []
    run_records: list[dict[str, Any]] = []
    solve_count = 0
    seen_masks: set[str] = set()
    seen_runs: set[str] = set()
    known_cases = known_cases or {}
    for row in run_rows:
        if not isinstance(row, dict):
            raise EvidenceError(f"{batch_id}: malformed run row")
        mask = str(row.get("mask", ""))
        run_id = str(row.get("run_id", ""))
        if mask not in masks or mask in seen_masks or not run_id or run_id in seen_runs:
            raise EvidenceError(f"{batch_id}: duplicate or unrequested run row {run_id!r}/{mask!r}")
        seen_masks.add(mask)
        seen_runs.add(run_id)

        reuse = row.get("reused_existing_case")
        if isinstance(reuse, dict):
            raw_path = _normalize_raw_reference(series_root, str(reuse.get("raw_path", "")))
            raw_sha = str(reuse.get("raw_sha256", ""))
            source_case = str(reuse.get("source_case", reuse.get("run_id", Path(raw_path).parts[1])))
            known = known_cases.get(raw_path) or known_cases.get(source_case)
            if not raw_path or not raw_sha or not known or known.get("raw_sha256") != raw_sha:
                raise EvidenceError(f"{batch_id}/{run_id}: reused raw lacks a verified base-package reference")
            if row.get("artifact_status") != "VALID":
                raise EvidenceError(f"{batch_id}/{run_id}: reused case is not marked VALID")
            local_raw = series_root / raw_path
            if local_raw.is_file() and sha256(local_raw) != raw_sha:
                raise EvidenceError(f"{batch_id}/{run_id}: reused raw SHA conflicts with local immutable raw")
            references.append({"source_case": source_case, "raw_path": raw_path,
                               "raw_sha256": raw_sha,
                               "source_package": known.get("source_package", "verified base chain")})
            run_records.append({"batch_id": batch_id, "run_id": run_id, "raw_path": raw_path,
                                "raw_sha256": raw_sha, "reused": True})
            if int(row.get("physical_solve_count", 0)) != 0:
                raise EvidenceError(f"{batch_id}/{run_id}: reused case must have physical_solve_count=0")
            continue

        if row.get("artifact_status") != "VALID" or row.get("solver_exit") != 0:
            raise EvidenceError(f"{batch_id}/{run_id}: run is not artifact-valid with solver exit 0")
        plot_row = row.get("plot_qa", {})
        if not isinstance(plot_row, dict) or plot_row.get("status") != "PASS":
            raise EvidenceError(f"{batch_id}/{run_id}: plot QA is not PASS")

        relative_run = str(row.get("path", ""))
        relative_parts = Path(relative_run).parts
        if len(relative_parts) != 2 or relative_parts[0] != "runs" or relative_parts[1] != run_id:
            raise EvidenceError(f"{batch_id}/{run_id}: unsafe or mismatched run path")
        run_dir = safe_file(series_root, f"{relative_run}/result.json", f"{batch_id}/{run_id}").parent
        if run_dir.name != run_id:
            raise EvidenceError(f"{batch_id}/{run_id}: run path/identity mismatch")
        if int(row.get("physical_solve_count", 0)) not in {0, 1}:
            raise EvidenceError(f"{batch_id}/{run_id}: invalid physical_solve_count")

        result = read_json(run_dir / "result.json", f"{run_id}/result.json")
        provenance = read_json(run_dir / "provenance.json", f"{run_id}/provenance.json")
        probe = read_json(run_dir / "probe_manifest.json", f"{run_id}/probe_manifest.json")
        raw_qa = read_json(run_dir / "analysis/raw_qa.json", f"{run_id}/raw_qa.json")
        plot_manifest = read_json(run_dir / "analysis/plot_manifest.json", f"{run_id}/plot_manifest.json")
        plot_qa = read_json(run_dir / "analysis/plot_qa.json", f"{run_id}/plot_qa.json")
        source_manifest = read_json(run_dir / "source_manifest.json", f"{run_id}/source_manifest.json")
        topology_manifest = read_json(run_dir / "topology_manifest.json", f"{run_id}/topology_manifest.json")
        mechanical_metrics = read_json(run_dir / "analysis" / "mechanical_metrics.json",
                                       f"{run_id}/mechanical_metrics.json")
        run_profile = str(probe.get("profile", "debug"))
        if run_profile != user["PROBE_PROFILE"]:
            raise EvidenceError(f"{batch_id}/{run_id}: run probe profile mismatch")
        if result.get("run_id") != run_id or result.get("mask") != mask:
            raise EvidenceError(f"{batch_id}/{run_id}: result identity mismatch")
        if result.get("artifact_status") != "VALID" or result.get("solver_exit_code") != 0:
            raise EvidenceError(f"{batch_id}/{run_id}: result is not artifact-valid")
        run_output_mode = str(topology_manifest.get("output_mode", "TERMINAL"))
        if run_output_mode != output_mode:
            raise EvidenceError(f"{batch_id}/{run_id}: topology output mode disagrees with batch")
        if output_mode == "T1":
            pulse_configured = all(key in snapshot_keys for key in {
                "T1_CLK_START", "T1_CLK_PERIOD", "T1_CLK_AMPLITUDE", "T1_CLK_RISE",
                "T1_CLK_WIDTH", "T1_CLK_FALL", "T1_CLK_R_SERIES",
            })
            clock_fields = (probe.get("clock_mode"), plot_manifest.get("clock_mode"),
                            plot_qa.get("clock_mode"), result.get("clock_mode"))
            clock_metadata_ok = all(
                value == user["T1_CLK_MODE"]
                or (value is None and user["T1_CLK_MODE"] == "QUIET" and not pulse_configured)
                for value in clock_fields
            )
            if (result.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW"
                    or result.get("output_mode") != "T1" or probe.get("output_mode") != "T1"
                    or plot_manifest.get("output_mode") != "T1"
                    or plot_qa.get("output_mode") != "T1"
                    or not clock_metadata_ok):
                raise EvidenceError(f"{batch_id}/{run_id}: T1 output-mode metadata is incomplete")
            link = mechanical_metrics.get("t1_link_consistency", {})
            if (not isinstance(link, dict) or link.get("status") != "MEASURED_REPORT_ONLY"
                    or link.get("left_signal") != "V(FINAL_OUT)"
                    or link.get("right_signal") != "V(T1_I)"
                    or link.get("units") != "V"
                    or link.get("uses_exact_stored_rows") is not True
                    or link.get("interpolation_or_resampling") is not False
                    or link.get("pass_fail_threshold_v") is not None
                    or not isinstance(link.get("max_abs_difference_v"), (float, int))
                    or isinstance(link.get("max_abs_difference_v"), bool)
                    or not math.isfinite(float(link.get("max_abs_difference_v")))
                    or float(link.get("max_abs_difference_v")) < 0
                    or link.get("sample_count") != raw_qa.get("sample_count")
                    or link.get("time_start_s") != raw_qa.get("time_start")
                    or link.get("time_end_s") != raw_qa.get("time_end")):
                raise EvidenceError(f"{batch_id}/{run_id}: T1 link arithmetic record is incomplete")
            mechanical_pointer = provenance.get("mechanical_metrics", {})
            mechanical_path = safe_file(run_dir, "analysis/mechanical_metrics.json",
                                        f"{run_id} mechanical metrics")
            if (not isinstance(mechanical_pointer, dict)
                    or mechanical_pointer.get("sha256") != sha256(mechanical_path)):
                raise EvidenceError(f"{batch_id}/{run_id}: mechanical metric provenance hash mismatch")
            raw_for_link = safe_file(run_dir, "raw.csv", f"{run_id} raw")
            independently_computed, independent_count = _independent_t1_link_metric(raw_for_link)
            if (independent_count != link.get("sample_count")
                    or independently_computed != float(link["max_abs_difference_v"])):
                raise EvidenceError(f"{batch_id}/{run_id}: T1 link metric does not reproduce from raw CSV")
            t1_pointer = provenance.get("t1_source", {})
            t1_rows = [item for item in source_manifest.get("sources", [])
                       if isinstance(item, dict) and item.get("role") == "T1"]
            if (len(t1_rows) != 1 or not isinstance(t1_pointer, dict)
                    or t1_pointer.get("sha256") != t1_rows[0].get("canonical_source_sha256")
                    or t1_rows[0].get("source_mode") != "DIRECT_CANONICAL_INCLUDE"):
                raise EvidenceError(f"{batch_id}/{run_id}: T1 direct-source provenance is incomplete")
            repository = next(
                (candidate for candidate in (series_root, *series_root.parents)
                 if (candidate / ".git").exists()), None
            )
            if repository is None:
                raise EvidenceError(f"{run_id}: cannot locate repository root for T1 source")
            t1_relative = Path(str(t1_rows[0].get("canonical_source_path", "")))
            if t1_relative.is_absolute() or ".." in t1_relative.parts:
                raise EvidenceError(f"{run_id}: unsafe T1 source path {t1_relative}")
            t1_path = safe_file(repository, t1_relative.as_posix(), f"{run_id} direct T1 source")
            _verify_hash(t1_path, t1_rows[0].get("canonical_source_sha256"),
                         f"{run_id}/{t1_relative.as_posix()}")
            if t1_pointer.get("sha256") != sha256(t1_path):
                raise EvidenceError(f"{run_id}: direct T1 source hash disagrees with provenance")
            deck = safe_file(run_dir, "actual_deck.cir", f"{run_id} deck")
            include_line = f".include {t1_rows[0].get('deck_include_path', '')}"
            if include_line not in deck.read_text(encoding="utf-8").splitlines():
                raise EvidenceError(f"{run_id}: actual deck does not directly include T1 source")
        physical = int(row.get("physical_solve_count", 0))
        if physical != int(result.get("physical_solve_count", 0)) or physical != int(provenance.get("physical_solve_count", 0)):
            raise EvidenceError(f"{batch_id}/{run_id}: physical_solve_count disagrees across manifests")

        for provenance_key, filename in (
            ("actual_deck", "actual_deck.cir"), ("stimulus", "stimulus.inc"),
            ("topology_manifest", "topology_manifest.json"), ("source_manifest", "source_manifest.json"),
            ("probe_manifest", "probe_manifest.json"), ("parameter_manifest", "parameter_manifest.json"),
        ):
            record = provenance.get(provenance_key, {})
            if isinstance(record, dict) and record.get("sha256"):
                _verify_hash(safe_file(run_dir, filename, f"{run_id} provenance input"),
                             record.get("sha256"), f"{run_id}/{filename}")

        raw_path = safe_file(run_dir, "raw.csv", f"{run_id} raw")
        raw_sha = sha256(raw_path)
        if (row.get("raw_sha256") != raw_sha or result.get("raw_sha256") != raw_sha
                or provenance.get("raw", {}).get("sha256") != raw_sha
                or raw_qa.get("sha256") != raw_sha
                or raw_qa.get("sha256_after_plot", raw_sha) != raw_sha
                or raw_qa.get("status") != "PASS" or raw_qa.get("raw_immutable") is not True):
            raise EvidenceError(f"{batch_id}/{run_id}: raw hash/immutability QA mismatch")
        if (plot_qa.get("status") != "PASS" or plot_qa.get("page_count") != len(expected_plot_paths)
                or plot_qa.get("raw_sha256_before") != raw_sha
                or plot_qa.get("raw_sha256_after") != raw_sha
                or plot_qa.get("raw_immutable") is not True
                or plot_manifest.get("raw_sha256") not in {None, raw_sha}):
            raise EvidenceError(f"{batch_id}/{run_id}: plot/raw QA mismatch")
        result_plot = result.get("plot_qa", {})
        if not isinstance(result_plot, dict) or result_plot.get("status") != "PASS":
            raise EvidenceError(f"{batch_id}/{run_id}: result.json does not record plot QA PASS")
        plot_pages = plot_qa.get("pages")
        manifest_pages = plot_manifest.get("pages")
        if (not isinstance(plot_pages, list) or not isinstance(manifest_pages, list)
                or len(plot_pages) != len(expected_plot_paths)
                or len(manifest_pages) != len(expected_plot_paths)):
            raise EvidenceError(f"{batch_id}/{run_id}: mode-specific plot manifest/QA entries are incomplete")
        plot_qa_by_path = {str(page.get("path")): page for page in plot_pages if isinstance(page, dict)}
        if set(plot_qa_by_path) != expected_plot_paths:
            raise EvidenceError(f"{batch_id}/{run_id}: plot QA page inventory is not canonical")
        if {str(page.get("file")) for page in manifest_pages if isinstance(page, dict)} != {
            path.removeprefix("plots/") for path in expected_plot_paths
        }:
            raise EvidenceError(f"{batch_id}/{run_id}: plot manifest page inventory is not canonical")
        if any(page.get("time_range") != "FULL_STORED_TIME_RANGE"
               for page in manifest_pages if isinstance(page, dict)):
            raise EvidenceError(f"{batch_id}/{run_id}: plot manifest does not use full stored time range")
        for plot_path in sorted(expected_plot_paths):
            qa_page = plot_qa_by_path[plot_path]
            if qa_page.get("status") not in {"PASS", "NO_COMPONENT_PRESENT"}:
                raise EvidenceError(f"{batch_id}/{run_id}: plot page QA failed for {plot_path}")
            page_file = safe_file(run_dir, plot_path, f"{run_id} derived plot")
            _verify_hash(page_file, qa_page.get("sha256"), f"{run_id}/{plot_path}")
        if plot_qa.get("shared_asset_reference_pass") is not True or plot_qa.get("full_stored_time_range") is not True:
            raise EvidenceError(f"{batch_id}/{run_id}: plot asset/time-range QA is incomplete")

        known = known_cases.get(relative_run + "/raw.csv")
        if known:
            if known.get("raw_sha256") != raw_sha:
                raise EvidenceError(f"{run_id}: base package raw hash conflicts with current raw")
            references.append({"source_case": run_id, "raw_path": relative_run + "/raw.csv",
                               "raw_sha256": raw_sha,
                               "source_package": known.get("source_package", "verified base chain")})
            run_records.append({"batch_id": batch_id, "run_id": run_id, "raw_path": relative_run + "/raw.csv",
                                "raw_sha256": raw_sha, "reused": True})
            continue

        if physical != 1:
            raise EvidenceError(f"{batch_id}/{run_id}: non-reused COMPLETE run must record one physical solve")

        for filename in RUN_FILES:
            relative_file = f"{relative_run}/{filename}"
            if filename == "raw.csv":
                category = "raw"
            elif filename in {"USER_CASE.snapshot.env", "STIMULUS.snapshot.env",
                              "actual_deck.cir", "stimulus.inc"}:
                category = "source_snapshots"
            else:
                category = "run_manifests_qa"
            _add_member(members, series_root, relative_file, category)
        for source in source_manifest.get("sources", []):
            if not isinstance(source, dict):
                raise EvidenceError(f"{run_id}: malformed source manifest entry")
            if source.get("source_mode") == "DIRECT_CANONICAL_INCLUDE":
                relative_source = Path(str(source.get("canonical_source_path", "")))
                if relative_source.is_absolute() or ".." in relative_source.parts:
                    raise EvidenceError(f"{run_id}: unsafe direct source path {relative_source}")
                repository = next(
                    (candidate for candidate in (series_root, *series_root.parents)
                     if (candidate / ".git").exists()), None
                )
                if repository is None:
                    raise EvidenceError(f"{run_id}: cannot locate repository root for direct source")
                direct_source = safe_file(repository, relative_source.as_posix(), f"{run_id} direct source")
                _verify_hash(direct_source, source.get("canonical_source_sha256"),
                             f"{run_id}/{relative_source.as_posix()}")
                deck = safe_file(run_dir, "actual_deck.cir", f"{run_id} deck")
                include_line = f".include {source.get('deck_include_path', '')}"
                if include_line not in deck.read_text(encoding="utf-8").splitlines():
                    raise EvidenceError(f"{run_id}: direct source include is absent from actual deck")
                continue
            snapshot_relative = str(source.get("rendered_snapshot_path", ""))
            snapshot = safe_file(run_dir, snapshot_relative, f"{run_id} source snapshot")
            _verify_hash(snapshot, source.get("rendered_snapshot_sha256"), f"{run_id}/{snapshot_relative}")
            _add_member(members, series_root, f"{relative_run}/{snapshot_relative}", "source_snapshots")
        if include_plots:
            for plot_path in sorted(expected_plot_paths):
                _add_member(members, series_root, f"{relative_run}/{plot_path}", "plots")
        solve_count += int(row.get("physical_solve_count", 0))
        run_records.append({"batch_id": batch_id, "run_id": run_id,
                            "raw_path": relative_run + "/raw.csv", "raw_sha256": raw_sha,
                            "reused": False})

    if seen_masks != set(masks):
        raise EvidenceError(f"{batch_id}: COMPLETE batch run rows do not cover requested masks")
    if sum(int(row.get("physical_solve_count", 0)) for row in run_rows) != manifest.get("total_physical_solve_count"):
        raise EvidenceError(f"{batch_id}: physical_solve_count total mismatch")
    return {
        "batch_id": batch_id,
        "array_size": size,
        "requested_masks": list(masks),
        "probe_profile": user["PROBE_PROFILE"],
        "total_physical_solve_count": int(manifest["total_physical_solve_count"]),
        "members": list(members.values()),
        "runs": run_records,
        "referenced_existing_cases": references,
    }


def discover_batch_manifests(series_root: Path) -> list[Path]:
    """Enumerate only direct batch directories, then trust their explicit manifests."""
    batches_root = series_root / "batches"
    if not batches_root.is_dir():
        return []
    manifests = []
    for directory in sorted(batches_root.iterdir()):
        if directory.is_dir() and (directory / "batch_manifest.json").is_file():
            manifests.append(directory / "batch_manifest.json")
    return manifests
