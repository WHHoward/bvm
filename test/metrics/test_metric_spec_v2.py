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
import math
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


# --- executable structural oracle (C05/C04 rework) ------------------------
# The guard is a reusable function over the RAW document (not a normalized
# copy), so it can do both whole-document substring checks and bounded
# section parsing. Tests assert its structured return value for valid and
# poisoned inputs; deleting the guard fails the tests.

REQUIRED_CONTRACT_FRAGMENTS = (
    "metric_spec_path",
    "metric_spec_version",
    "metric_spec_sha256",
    "schema_version",
    "provenance",
    "windows",
    "mappings",
    "namespaces: signal, zero_input_control, control_corrected",
    "phase_rad AND phase_turns",
)

PROHIBITED_SEMANTICS = (
    # Assertive candidate/Gate/route criteria must never appear anywhere.
    # (Bare "interface Gate"/"system Gate" nouns appear legitimately only
    # inside the §12 exclusion list, which tests assert separately.)
    "candidate PASS", "candidate FAIL", "route decision", "success criterion",
    "read1 must", "read0 must", "PASS threshold", "FAIL threshold",
    "interface Gate must", "system Gate must", "Gate PASS", "Gate FAIL",
)

# Structured key/value success-claim forms: `candidate: PASS`, `read1: 1`,
# `route: BQ`, `gate: success`, ... These are YAML-ish assertions that must
# never appear anywhere in the document, in any section.
STRUCTURAL_CLAIM_KEYS = (
    "candidate:",
    "read1:",
    "read0:",
    "route:",
    "gate:",
    "success criterion:",
)

# Fields that must exist INSIDE the §11 output-schema block specifically,
# even if the word appears elsewhere in the document.
REQUIRED_SCHEMA_BLOCK_FIELDS = (
    "metric_spec:",
    "schema_version",
    "study_phase:",
    "provenance:",
    "windows:",
    "mappings:",
    "namespaces:",
    "values:",
    "activity:",
    "cross_check:",
    "convergence:",
    "unknown/na:",
)


def _extract_schema_block(raw_doc: str) -> str:
    """Extract the '## 11. Output schema' section body (up to next '## ')."""
    marker = "## 11. Output schema"
    start = raw_doc.find(marker)
    if start == -1:
        return ""
    body_start = start + len(marker)
    nxt = raw_doc.find("\n## ", body_start)
    return raw_doc[body_start:nxt] if nxt != -1 else raw_doc[body_start:]


def _extract_claim_keys(raw_doc: str) -> list[str]:
    """YAML-like claim keys found in the document.

    Parses each line, strips leading whitespace, case-folds the key name, and
    keeps it when it ends with ':' and its case-folded name is a claim key.
    This rejects indented forms ('  candidate: PASS') and case variants
    ('Gate: PASS') that a column-zero, lower-case-only matcher would miss.
    """
    folded = {k[:-1].lower(): k for k in STRUCTURAL_CLAIM_KEYS}  # key name w/o colon
    found: list[str] = []
    for line in raw_doc.splitlines():
        stripped = line.lstrip()
        if not stripped:
            continue
        key = stripped.split(":", 1)[0].strip().lstrip("-").strip().lower()
        if key in folded:
            found.append(folded[key])
    return found


def spec_guard(raw_doc: str) -> dict:
    """Structured guard over the RAW document.

    Returns {'passed', 'missing_required', 'prohibited_hits',
    'structural_claim_hits', 'missing_schema_block_fields'}.

    Rejects when:
    - any required whole-document fragment is missing,
    - any assertive prose semantic appears anywhere,
    - any structured key/value claim key (candidate:/read1:/route:/gate:/...)
      appears anywhere, regardless of leading whitespace or key case, or
    - any required field is missing from the bounded §11 schema block.
    """
    norm = re.sub(r"\s+", " ", raw_doc).replace("`", "").replace("**", "")
    missing = [f for f in REQUIRED_CONTRACT_FRAGMENTS if f not in norm]
    hits = [p for p in PROHIBITED_SEMANTICS if p in norm]
    struct_hits = _extract_claim_keys(raw_doc)
    schema_block = _extract_schema_block(raw_doc)
    missing_schema = [f for f in REQUIRED_SCHEMA_BLOCK_FIELDS if f not in schema_block]
    return {
        "passed": not (missing or hits or struct_hits or missing_schema),
        "missing_required": missing,
        "prohibited_hits": hits,
        "structural_claim_hits": struct_hits,
        "missing_schema_block_fields": missing_schema,
    }


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
        self.assertIn("freeze_task: JH-20260813-M9-004", SPEC_NORM)

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


class TestM7EvidenceBinding(unittest.TestCase):
    """C03/C04 rework: XDUT mapping bound to M7; XLOAD must NOT be verified."""

    def test_m7_audit_cited_in_spec(self) -> None:
        self.assertIn("research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md", SPEC_NORM)

    def test_m7_binds_canonical_jtl_direct_probes(self) -> None:
        # The spec must tie the canonical-JTL XDUT mapping to M7's direct
        # same-JJ probes.
        self.assertIn("V(B1|XDUT)", SPEC_NORM)
        self.assertIn("P(B1|XDUT)", SPEC_NORM)
        self.assertIn("M7B", SPEC_NORM)

    def test_m6_and_m7_evidence_cited_in_order(self) -> None:
        # M6 (DCSFQ) and M7 (canonical JTL XDUT) evidence both cited in order.
        idx_m6 = SPEC_NORM.find("JH-20260812-M6-002/audits/C01/verdict.yaml")
        idx_m7 = SPEC_NORM.find("M7-LITE-001/attempts/A02/CODEX-AUDIT.md")
        idx_m8 = SPEC_NORM.find("JH-20260812-M8-002/audits/C01/verdict.yaml")
        self.assertGreater(idx_m6, 0)
        self.assertGreater(idx_m7, idx_m6)
        self.assertGreater(idx_m8, idx_m7)

    def test_xload_not_in_verified_mappings(self) -> None:
        # C04: M7's direct-P/V evidence covers XDUT only; the verified bullets
        # (before the "not verified" paragraph) must not list XLOAD.
        block = SPEC_NORM.split("3.4 Verified calibration mappings")[1].split("3.5")[0]
        verified_bullets = block.split("Canonical-JTL XLOAD junctions")[0]
        self.assertNotIn("XLOAD", verified_bullets)

    def test_xload_marked_unverified_with_reason(self) -> None:
        # The spec must explicitly state XLOAD is not verified and why, and
        # require new accepted evidence or an UNVERIFIED label.
        self.assertIn("XLOAD", SPEC_NORM)
        self.assertIn("are not verified P/V mappings", SPEC_NORM)
        self.assertIn("UNVERIFIED", SPEC_NORM)

    def test_m8_downstream_platform_is_phase_diagnostic_only(self) -> None:
        # The accepted M8 XLOAD observable is a phase-platform diagnostic,
        # not a verified P/V identity mapping.
        self.assertIn("downstream_platform_phase_turns", SPEC_NORM)
        self.assertIn("phase-platform diagnostic", SPEC_NORM)


class TestDualSignSemantics(unittest.TestCase):
    """C04 rework: exact dual-sign equations and orientation-only compatibility."""

    def test_signed_equation_terms_present(self) -> None:
        for term in (
            "phase_reported_turns",
            "area_reported_turns",
            "residual_reported_turns",
            "rd * phase_delta_rad / (2*pi)",
            "vts * trapezoid(V_jj, actual_time)",
            "rd * area_aligned_vs / Phi0",
        ):
            self.assertIn(term, SPEC_NORM)

    def test_dual_sign_fields_defined(self) -> None:
        self.assertIn("voltage_to_phase_sign", SPEC_NORM)
        self.assertIn("reporting_direction", SPEC_NORM)
        # Both strictly +1 or -1.
        self.assertIn("both strictly +1 or -1", SPEC_NORM)

    def test_rd_applies_to_all_three_quantities(self) -> None:
        # rd must multiply phase, area, and residual identically.
        self.assertIn("rd multiplies phase, area, and residual identically", SPEC_NORM)
        # vts enters only the voltage-area term.
        self.assertIn("vts enters only the voltage-area term", SPEC_NORM)

    def test_orientation_only_compatibility_boundary_declared(self) -> None:
        # M6 orientation-only output must be declared nonconformant / predecessor,
        # with an explicit migration path — never silently conformant.
        self.assertIn("predecessor format", SPEC_NORM)
        self.assertIn("nonconformant", SPEC_NORM)
        self.assertIn("legacy_orientation_only", SPEC_NORM)
        self.assertIn("vts = orientation, rd = +1", SPEC_NORM)

    def test_four_sign_combinations_identity(self) -> None:
        """The four (vts, rd) combinations apply the dual-sign contract exactly.

        With a voltage column generated from the same junction as P (vts=+1
        aligned), phase and area agree and the residual is the numerical
        residual; with vts=-1 the residual is the 2*rd sign artifact, proving
        the sign field changes the reported area as specified.
        """
        n = 400
        dt = 1e-13
        times = [i * dt for i in range(n)]
        # phi goes from 0 to exactly 2*pi across the window (raw rad, one turn).
        phi = [2.0 * math.pi * i / (n - 1) for i in range(n)]
        # V = (Phi0 / 2*pi) * dphi/dt, trapezoid over it equals Phi0 * turns.
        v = [
            (2.067833848e-15 / (2.0 * math.pi)) * (2.0 * math.pi) / (n - 1) / dt
            for _ in range(n)
        ]
        area_vs = sum(
            0.5 * (v[i] + v[i + 1]) * (times[i + 1] - times[i])
            for i in range(n - 1)
        )
        phase_delta_rad = phi[-1] - phi[0]
        for vts in (1, -1):
            for rd in (1, -1):
                phase_reported = rd * phase_delta_rad / (2.0 * math.pi)
                area_reported = rd * vts * area_vs / 2.067833848e-15
                residual = phase_reported - area_reported
                self.assertAlmostEqual(phase_reported, rd, places=12)
                self.assertAlmostEqual(area_reported, rd * vts, places=12)
                if vts == 1:
                    # aligned: residual is numerical only
                    self.assertAlmostEqual(residual, 0.0, places=12)
                else:
                    # misaligned: exact sign artifact 2*rd, not silently zero
                    self.assertAlmostEqual(residual, 2.0 * rd, places=12)

    def test_orientation_only_m6_output_flagged(self) -> None:
        # The accepted M6 implementation exposes only orientation on area; the
        # spec must not claim M6 output is already fully conformant.
        self.assertIn("applies it only to the area term", SPEC_NORM)
        self.assertIn("phase term lacks", SPEC_NORM)


class TestConvergenceApplicability(unittest.TestCase):
    """C05 rework: CONVERGED over applicable observables, preregistered N/A + reason."""

    def test_converged_applicable_registered_scalars(self) -> None:
        self.assertIn("every applicable registered scalar is computable", SPEC_NORM)
        self.assertNotIn("every registered scalar is computable", SPEC_NORM)

    def test_preregistered_na_requires_reason(self) -> None:
        self.assertIn("NOT_APPLICABLE", SPEC_NORM)
        self.assertIn("MUST carry an explicit preregistered reason", SPEC_NORM)

    def test_m8_downstream_count_na_regression(self) -> None:
        # M8 registered downstream_count as NOT_APPLICABLE with reason and its
        # CONVERGED classification is the accepted precedent (C05 finding).
        self.assertIn("downstream_count", SPEC_NORM)
        self.assertIn("M9 has not frozen a downstream", SPEC_NORM)


class TestAdversarialNegativeGuards(unittest.TestCase):
    """C05/C06 rework: executable guard rejects poisoned documents, passes valid."""

    def test_valid_spec_passes_guard(self) -> None:
        # The real spec must pass the executable guard (return value asserted,
        # not a text demonstration).
        verdict = spec_guard(SPEC)
        self.assertTrue(verdict["passed"], f"missing={verdict['missing_required']} hits={verdict['prohibited_hits']}")
        self.assertEqual(verdict["missing_required"], [])
        self.assertEqual(verdict["prohibited_hits"], [])

    def test_poisoned_candidate_semantics_rejected(self) -> None:
        # Introducing candidate/read/route/Gate criteria must cause the guard
        # to reject (return passed=False with the hit reported).
        for poison in ("candidate PASS threshold 0.1",
                       "read1 must produce exactly one event",
                       "route decision: adopt BQ",
                       "success criterion: PASS",
                       "interface Gate must be satisfied",
                       "system Gate PASS required"):
            mutated = SPEC_NORM + " " + poison
            verdict = spec_guard(mutated)
            self.assertFalse(verdict["passed"], f"guard accepted poison: {poison}")
            self.assertTrue(verdict["prohibited_hits"], f"poison not reported: {poison}")

    def test_structural_key_value_claims_rejected(self) -> None:
        # Structured key/value success claims must be rejected by the guard
        # even though none of the prose PROHIBITED_SEMANTICS is present.
        for poison in ("candidate: PASS\n",
                       "read1: 1\n",
                       "read0: 0\n",
                       "route: BQ\n",
                       "gate: success\n",
                       "success criterion: PASS\n"):
            mutated = SPEC + "\n" + poison
            verdict = spec_guard(mutated)
            self.assertFalse(verdict["passed"], f"guard accepted structural poison: {poison!r}")
            self.assertTrue(verdict["structural_claim_hits"], f"structural poison not reported: {poison!r}")

    def test_indented_structural_claims_rejected(self) -> None:
        # Leading whitespace must not bypass the guard (C03: indented YAML).
        for poison in ("  candidate: PASS\n",
                       "  - read1: 1\n",
                       "    route: BQ\n",
                       "\tgate: success\n",
                       "  nested:\n    read0: 0\n"):
            mutated = SPEC + "\n" + poison
            verdict = spec_guard(mutated)
            self.assertFalse(verdict["passed"], f"guard accepted indented poison: {poison!r}")
            self.assertTrue(verdict["structural_claim_hits"], f"indented poison not reported: {poison!r}")

    def test_case_variant_structural_claims_rejected(self) -> None:
        # Capitalized keys must not bypass the guard (C03: Gate: PASS).
        for poison in ("Gate: PASS\n",
                       "CANDIDATE: PASS\n",
                       "Read1: 1\n",
                       "ROUTE: BQ\n",
                       "  Success Criterion: PASS\n"):
            mutated = SPEC + "\n" + poison
            verdict = spec_guard(mutated)
            self.assertFalse(verdict["passed"], f"guard accepted case-variant poison: {poison!r}")
            self.assertTrue(verdict["structural_claim_hits"], f"case-variant poison not reported: {poison!r}")

    def test_valid_spec_has_no_structural_claims(self) -> None:
        verdict = spec_guard(SPEC)
        self.assertEqual(verdict["structural_claim_hits"], [])

    def test_missing_provenance_schema_rejected(self) -> None:
        # Removing a required provenance/schema element must cause rejection.
        for required in ("metric_spec_path", "metric_spec_version", "metric_spec_sha256",
                         "schema_version", "provenance", "windows", "mappings"):
            self.assertIn(required, SPEC_NORM)
            stripped = SPEC_NORM.replace(required, "")
            verdict = spec_guard(stripped)
            self.assertFalse(verdict["passed"], f"guard accepted doc without {required}")
            self.assertIn(required, verdict["missing_required"])

    def test_schema_block_fields_required_inside_block(self) -> None:
        # Every required §11 field must exist inside the schema block itself,
        # not merely elsewhere in the document.
        block = _extract_schema_block(SPEC)
        self.assertTrue(block, "schema block not found")
        for field in REQUIRED_SCHEMA_BLOCK_FIELDS:
            self.assertIn(field, block, f"{field} missing from §11 schema block")

    def test_schema_block_removal_rejected_even_if_word_elsewhere(self) -> None:
        # Removing a required field from the §11 block must be rejected even
        # when the same word still occurs elsewhere in the document.
        marker = "## 11. Output schema"
        start = SPEC.find(marker)
        body_start = start + len(marker)
        nxt = SPEC.find("\n## ", body_start)
        end = nxt if nxt != -1 else len(SPEC)
        for field in REQUIRED_SCHEMA_BLOCK_FIELDS:
            if field not in SPEC[body_start:end]:
                continue
            # remove every occurrence inside the block (a field may appear
            # legitimately more than once there, e.g. schema_version)
            mutated = SPEC[:body_start] + SPEC[body_start:end].replace(field, "") + SPEC[end:]
            verdict = spec_guard(mutated)
            self.assertFalse(verdict["passed"], f"guard accepted §11 block without {field}")
            self.assertIn(field, verdict["missing_schema_block_fields"])

    def test_exclusion_block_names_read_semantics(self) -> None:
        # The §12 exclusion block must explicitly name read1/read0 semantics.
        self.assertIn("read1/read0 semantics", SPEC_NORM)


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
