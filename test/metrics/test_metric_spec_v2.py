#!/usr/bin/env python3
"""test_metric_spec_v2 -- deterministic guard rails for METRIC_SPEC_V2.md.

Pure-stdlib, read-only checks that the frozen measurement/reporting contract
stays at its canonical path, states its version, binds its content-hash
procedure, defines the required measurement semantics, keeps the fixture-local
M8 bands scoped, refuses to invent global tolerances, and never crosses into
INTERFACE_GATE_V1 / candidate-success territory.

These tests never execute JoSIM and never modify any file.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "research" / "METRIC_SPEC_V2.md"
SPEC = SPEC_PATH.read_text(encoding="utf-8")
# Content checks are semantic, not typographic: collapse whitespace and strip
# markdown backticks so line wrapping / emphasis never breaks a literal match.
SPEC_NORM = re.sub(r"\s+", " ", SPEC).replace("`", "").replace("**", "")


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestCanonicalityAndVersion(unittest.TestCase):
    """AC1: canonical path, version, content-hash procedure, evidence basis."""

    def test_canonical_path_is_docs_research_metric_spec_v2(self) -> None:
        self.assertEqual(SPEC_PATH.relative_to(REPO_ROOT).as_posix(),
                         "docs/research/METRIC_SPEC_V2.md")
        self.assertTrue(SPEC_PATH.is_file())

    def test_metric_spec_version_2_0_0(self) -> None:
        self.assertIn("metric_spec_version: 2.0.0", SPEC_NORM)

    def test_status_frozen_and_task_bound(self) -> None:
        self.assertIn("status: FROZEN", SPEC_NORM)
        self.assertIn("freeze_task: JH-20260813-M9-001", SPEC_NORM)

    def test_content_hash_procedure_bound(self) -> None:
        self.assertIn("metric_spec_sha256:", SPEC_NORM)
        self.assertIn("canonical_path: docs/research/METRIC_SPEC_V2.md", SPEC_NORM)

    def test_cites_accepted_m4_through_m8_evidence(self) -> None:
        for fragment in (
            "JH-20260811-M4-003/audits/C01/verdict.yaml",
            "M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md",
            "JH-20260812-M6-002/audits/C01/verdict.yaml",
            "JH-20260812-M8-002/audits/C01/verdict.yaml",
        ):
            self.assertIn(fragment, SPEC_NORM)

    def test_claim_limited_to_measurement_reporting(self) -> None:
        self.assertIn("claim_ceiling: measurement_semantics_and_reporting_contract_only_no_physical_gate", SPEC_NORM)


class TestRequiredSemantics(unittest.TestCase):
    """AC2: every required measurement semantic is precisely defined."""

    def test_raw_radian_preservation(self) -> None:
        self.assertIn("raw, unwrapped phase in radians", SPEC_NORM)
        self.assertIn("phase_delta_turns = phase_delta_rad / (2*pi)", SPEC_NORM)
        self.assertIn("No absolute value, integer rounding, or modulo operation", SPEC_NORM)

    def test_platform_and_endpoint_deltas_separate(self) -> None:
        self.assertIn("Platform result", SPEC_NORM)
        self.assertIn("mean(P_post) - mean(P_pre)", SPEC_NORM)
        self.assertIn("Endpoint result", SPEC_NORM)
        self.assertIn("P_last - P_first", SPEC_NORM)
        self.assertIn("MUST NOT be conflated", SPEC_NORM)

    def test_same_jj_pv_mapping_fields(self) -> None:
        for field in ("phase_column", "voltage_column", "branch_endpoints",
                      "voltage_to_phase_sign", "reporting_direction", "run", "window"):
            self.assertIn(field, SPEC_NORM)

    def test_distinct_sign_fields(self) -> None:
        self.assertIn("reporting_direction and voltage_to_phase_sign are distinct fields", SPEC_NORM)

    def test_direct_branch_voltage_preferred(self) -> None:
        self.assertIn("Direct V(B...|X...) branch voltages are preferred", SPEC_NORM)

    def test_half_open_windows(self) -> None:
        self.assertIn("half-open intervals [start, end)", SPEC_NORM)
        self.assertIn("start <= t < end", SPEC_NORM)

    def test_window_statistics_required(self) -> None:
        for stat in ("selected first/last times", "sample count", "mean", "min", "max", "peak-to-peak"):
            self.assertIn(stat, SPEC_NORM)

    def test_matched_control_and_netlist_closure(self) -> None:
        self.assertIn("matched zero-input control", SPEC_NORM)
        self.assertIn("netlist closure", SPEC_NORM)
        self.assertIn("corrected_delta_rad = direction * (signal_delta_rad - control_delta_rad)", SPEC_NORM)

    def test_activity_clusters(self) -> None:
        self.assertIn("abs(delta P_rad) > threshold_rad", SPEC_NORM)
        self.assertIn("strict >", SPEC_NORM)
        self.assertIn("gaps are never bridged", SPEC_NORM)
        self.assertIn("activity", SPEC_NORM)

    def test_actual_time_voltage_area(self) -> None:
        self.assertIn("trapezoidal integration", SPEC_NORM)
        self.assertIn("Phi0 = 2.067833848e-15 Wb", SPEC_NORM)
        self.assertIn("No fixed-dt assumption, resampling, or interpolation", SPEC_NORM)
        self.assertIn("area_turns", SPEC_NORM)

    def test_qa_and_invalid_inconclusive(self) -> None:
        self.assertIn("strictly increasing actual time", SPEC_NORM)
        self.assertIn("INVALID", SPEC_NORM)
        self.assertIn("INCONCLUSIVE", SPEC_NORM)
        self.assertIn("NaN/Inf", SPEC_NORM)

    def test_convergence_preregistration(self) -> None:
        self.assertIn("preregistered before execution", SPEC_NORM)
        for item in ("initial timestep", "refinement ratio", "maximum depth",
                     "matched controls", "observables", "comparison windows", "stop rule"):
            self.assertIn(item, SPEC_NORM)

    def test_versioned_output_schema(self) -> None:
        self.assertIn("schema_version", SPEC_NORM)
        self.assertIn("namespaces: signal, zero_input_control, control_corrected", SPEC_NORM)
        self.assertIn("phase_rad AND phase_turns", SPEC_NORM)


class TestNoGlobalTolerances(unittest.TestCase):
    """AC3: no universal/global acceptance tolerance is frozen."""

    def test_activity_threshold_descriptive_not_frozen(self) -> None:
        self.assertIn("descriptive and unfrozen", SPEC_NORM)
        self.assertIn("0.3 rad", SPEC_NORM)

    def test_no_frozen_global_acceptance_tolerances(self) -> None:
        for name in ("integer residual", "phase-area residual", "platform stability",
                     "BVM drift", "amplitude", "jitter"):
            self.assertIn(name, SPEC_NORM)
        # §8.1 explicitly refuses to freeze any global threshold.
        self.assertIn("does not freeze a universal activity threshold or any global"
                      " acceptance tolerance for", SPEC_NORM)
        # §13 registry marks each tolerance UNFROZEN; none are frozen.
        self.assertEqual(SPEC_NORM.count("| UNFROZEN |"), 6)

    def test_m8_bands_are_fixture_local_only(self) -> None:
        self.assertIn("m8_loaded_canonical_jtl_v1", SPEC_NORM)
        self.assertIn("fixture-local calibration profile", SPEC_NORM)
        self.assertIn("never be promoted into a universal candidate tolerance", SPEC_NORM)

    def test_missing_tolerance_yields_inconclusive(self) -> None:
        self.assertIn("UNFROZEN", SPEC_NORM)
        self.assertIn("INCONCLUSIVE", SPEC_NORM)

    def test_tolerance_registration_object(self) -> None:
        for field in ("id", "scope", "applies_to", "value", "status: FROZEN | UNFROZEN", "evidence"):
            self.assertIn(field, SPEC_NORM)


class TestOutputSchemaProhibitions(unittest.TestCase):
    """AC4: schema rejects NaN/Inf and event-count fields, requires provenance."""

    def test_rejects_nan_inf(self) -> None:
        self.assertIn("MUST reject JSON NaN/Inf", SPEC_NORM)

    def test_no_event_sfq_pulse_fluxoid_count_fields(self) -> None:
        self.assertIn("MUST NOT emit event/SFQ/pulse/fluxoid-count fields", SPEC_NORM)
        # The spec itself only names the prohibited terms in prohibition context.
        self.assertIn("fast_events", SPEC_NORM)
        self.assertIn("pulse_count", SPEC_NORM)
        self.assertIn("sfq_count", SPEC_NORM)
        self.assertIn("event_count", SPEC_NORM)

    def test_requires_provenance(self) -> None:
        self.assertIn("provenance", SPEC_NORM)
        self.assertIn("binary path/version/sha256", SPEC_NORM)

    def test_requires_unknown_not_applicable_reasons(self) -> None:
        self.assertIn("UNKNOWN", SPEC_NORM)
        self.assertIn("NOT_APPLICABLE", SPEC_NORM)
        self.assertIn("explicit reason", SPEC_NORM)


class TestExclusions(unittest.TestCase):
    """AC5: spec and tests exclude interface/candidate/success territory."""

    def test_excludes_interface_gate_v1(self) -> None:
        self.assertIn("INTERFACE_GATE_V1", SPEC_NORM)
        self.assertIn("outside this specification and MUST NOT be derived from it", SPEC_NORM)

    def test_excludes_candidate_success_criteria(self) -> None:
        self.assertIn("candidate success criteria", SPEC_NORM)
        for name in ("BQ", "DCSFQ", "BVM"):
            self.assertIn(name, SPEC_NORM)

    def test_excludes_read_repeat_state_route_paper(self) -> None:
        for term in ("read1/read0", "repeatability", "state preservation", "Route selection", "paper/hardware claims"):
            self.assertIn(term, SPEC_NORM)

    def test_spec_never_defines_success_threshold(self) -> None:
        # Guard against the document silently containing a numeric success gate.
        self.assertNotIn("success threshold", SPEC_NORM)


class TestHashProcedureDeterministic(unittest.TestCase):
    """The content-hash procedure is computable from the frozen file."""

    def test_sha256_computable(self) -> None:
        digest = file_sha256(SPEC_PATH)
        self.assertEqual(len(digest), 64)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", digest))

    def test_hash_changes_with_content(self) -> None:
        self.assertNotEqual(
            file_sha256(SPEC_PATH),
            hashlib.sha256((SPEC + "\n# mutated\n").encode()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
