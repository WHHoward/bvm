#!/usr/bin/env python3
"""Regression tests for quantitative_analysis_verifier + report renderer.

Negative fixtures (AC3): wrong Phi0, phase-area sign, integration method,
forbidden interpolation/resampling, S2-style affine interpolation, and
registered-threshold mismatch must all be rejected.  Renderer determinism
and report-consistency rejection (AC4) are covered here too.  All checks use
minimal synthetic data; no historical evidence is edited.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
VERIFIER = REPO / 'scripts/quantitative_analysis_verifier.py'
RENDERER = REPO / 'scripts/render_structured_report.py'

TAU = 6.283185307179586


def make_raw(path: pathlib.Path) -> None:
    rows = ['time,"P(B_J1|XB1)","V(B_J1|XB1)","V(SL1)"']
    for i in range(1001):
        t = i * 1e-13  # 0..100 ps
        p = 1.0 + 0.1 * (t / 1e-10)
        v = 1e-3 if 40e-12 <= t < 60e-12 else 0.0
        rows.append(f'{t:.6e},{p:.9e},{v:.9e},{v * 12:.9e}')
    path.write_text('\n'.join(rows) + '\n', encoding='utf-8')


def base_spec(raw_rel: str) -> dict:
    return {
        'schema_version': 'quantitative-analysis-spec-v1',
        'spec_id': 'synthetic-test',
        'raw_path': raw_rel,
        'timestamp_rule': 'exact_decimal_zero_tolerance',
        'interpolation': 'prohibited',
        'windows': {'pre': [0, 40], 'activity': [40, 60], 'source': [40, 100],
                    'post': [80, 100]},
        'columns': {'P_J1': 'P(B_J1|XB1)', 'V_J1': 'V(B_J1|XB1)',
                    'V_SL1': 'V(SL1)'},
        'metrics': [
            {'id': 'peak_v', 'kind': 'baseline_subtracted_peak',
             'column': 'V(SL1)', 'window': 'source', 'baseline_window': 'pre',
             'compare_tolerance': 1e-9},
            {'id': 'phase_area_residual', 'kind': 'phase_area',
             'column': 'P(B_J1|XB1)', 'window': 'activity',
             'compare_tolerance': 1e-9},
        ],
        'integration': {'actual_time': True, 'phi0_wb': 2.067833848e-15,
                        'method': 'trapezoid'},
        'same_jj': {'phase_column': 'P(B_J1|XB1)',
                    'voltage_column': 'V(B_J1|XB1)', 'window': 'activity',
                    'reporting_direction': 1, 'voltage_to_phase_sign': 1,
                    'residual_definition': 'phase_turns_minus_area_turns'},
    }


def run_verifier(raw: pathlib.Path, spec: dict, structured: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as td:
        spec_p = pathlib.Path(td) / 'spec.json'
        struct_p = pathlib.Path(td) / 'structured.json'
        spec_p.write_text(json.dumps(spec), encoding='utf-8')
        struct_p.write_text(json.dumps(structured), encoding='utf-8')
        proc = subprocess.run(
            [sys.executable, str(VERIFIER), str(raw), str(spec_p),
             str(struct_p)],
            capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr


class VerifierPositiveTests(unittest.TestCase):
    def test_matches_correct_structured(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            raw = pathlib.Path(td) / 'raw.csv'
            make_raw(raw)
            spec = base_spec(raw.name)
            # discrete-window semantics (0.1 ps grid, [40,60) ps = 200 samples):
            # P slope 0.1 rad/100ps -> dlt = P(59.9) - P(40.0) = 0.0199 rad
            area_turns = (199 * 1e-13 * 1e-3) / 2.067833848e-15
            phase_delta_turns = 0.0199 / TAU
            residual = phase_delta_turns - area_turns
            structured = {'metrics': {'peak_v': 0.012,
                                      'phase_area_residual': residual}}
            code, out = run_verifier(raw, spec, structured)
            self.assertEqual(code, 0, out)


class VerifierNegativeTests(unittest.TestCase):
    def _expect_fail(self, spec_mutator, structured_mutator=None) -> None:
        with tempfile.TemporaryDirectory() as td:
            raw = pathlib.Path(td) / 'raw.csv'
            make_raw(raw)
            spec = base_spec(raw.name)
            spec_mutator(spec)
            area_turns = (199 * 1e-13 * 1e-3) / 2.067833848e-15
            phase_delta_turns = 0.0199 / TAU
            structured = {'metrics': {
                'peak_v': 0.012,
                'phase_area_residual': phase_delta_turns - area_turns}}
            if structured_mutator:
                structured_mutator(structured)
            code, out = run_verifier(raw, spec, structured)
            self.assertNotEqual(code, 0, f'must fail, got: {out}')

    def test_rejects_wrong_phi0(self) -> None:
        def mut(spec):
            spec['integration']['phi0_wb'] = 2.07e-15  # wrong constant
        self._expect_fail(mut)

    def test_rejects_wrong_phase_area_sign(self) -> None:
        def mut(spec):
            spec['same_jj']['voltage_to_phase_sign'] = -1
        self._expect_fail(mut)

    def test_rejects_structured_threshold_mismatch(self) -> None:
        def mut(struct):
            struct['metrics']['peak_v'] = 0.013  # 1e-3 off, tol 1e-9
        self._expect_fail(lambda s: None, mut)

    def test_rejects_interpolation_enabled(self) -> None:
        def mut(spec):
            spec['interpolation'] = 'linear_allowed'  # violates spec
        self._expect_fail(mut)

    def test_rejects_s2_affine_interpolation_spec(self) -> None:
        """AC3: the old ambiguous affine_residual metric kind (with its
        interpolate-across-loads affine_endpoint config) is rejected."""
        def mut(spec):
            spec['affine_endpoint'] = {
                'endpoint_loads': [1, 50], 'interior_loads': [12, 25],
                'floors': {'V': 5e-6}, 'band_fraction': 0.01,
                'interpolation': 'interpolate_across_all_loads'}
            spec['metrics'] = [{'id': 's2_affine', 'kind': 'affine_residual',
                                'column': 'V(SL1)'}]
        self._expect_fail(mut)


class EndpointVITests(unittest.TestCase):
    """AC3/AC4: endpoint-VI affine fit from simultaneous endpoint V/I at
    preregistered exact timestamp tokens; affine_residual is rejected and
    cross-run matching never interpolates/resamples timestamps."""

    VTH = 2e-3
    RHAT = -20.0
    TOKENS_PS = [45.0, 55.0]

    def _make_run(self, td: pathlib.Path, name: str, v: float, i: float,
                  offset_ps: float = 0.0) -> None:
        rows = ['time,"V(LD)","I(LD)"']
        for k in range(1001):
            t = k * 1e-13 + offset_ps * 1e-12
            rows.append(f'{t:.6e},{v:.9e},{i:.9e}')
        (td / name).write_text('\n'.join(rows) + '\n', encoding='utf-8')

    def _evi_spec(self, raw_rel: str,
                  runs: dict) -> dict:
        spec = base_spec(raw_rel)
        spec['endpoint_vi'] = {
            'runs': runs,
            'endpoint_loads': [1, 50],
            'interior_loads': [12, 25],
            'tokens_ps': self.TOKENS_PS,
        }
        spec['metrics'] = [{'id': 'evi', 'kind': 'endpoint_vi',
                            'compare_tolerance': 1e-12}]
        return spec

    def _run(self, td: pathlib.Path, spec: dict,
             structured: dict) -> tuple[int, str]:
        spec_p = td / 'spec.json'
        struct_p = td / 'structured.json'
        spec_p.write_text(json.dumps(spec), encoding='utf-8')
        struct_p.write_text(json.dumps(structured), encoding='utf-8')
        proc = subprocess.run(
            [sys.executable, str(VERIFIER), str(td / 'main.csv'),
             str(spec_p), str(struct_p)],
            capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def _aligned_runs(self, td: pathlib.Path) -> dict:
        # all runs share the same 0.1 ps grid -> tokens exist exactly
        self._make_run(td, 'run1.csv', 1e-3, 5e-5)
        self._make_run(td, 'run50.csv', 2e-4, 9e-5)
        self._make_run(td, 'run12.csv', 6e-4, 7e-5)
        self._make_run(td, 'run25.csv', 8e-4, 6e-5)
        return {str(k): {'raw_path': f'run{k}.csv', 'v_column': 'V(LD)',
                         'i_column': 'I(LD)'}
                for k in (1, 50, 12, 25)}

    def test_endpoint_vi_passes_with_exact_tokens(self) -> None:
        """AC3/AC4 positive: Rhat/Vth/e_L from simultaneous endpoint V/I at
        exact preregistered tokens verify against structured."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            self._make_run(td, 'main.csv', 0.0, 0.0)
            spec = self._evi_spec('main.csv', self._aligned_runs(td))
            structured = {'metrics': {'evi': {
                'rhat': self.RHAT, 'vth': self.VTH, 'e_L': 0.0}}}
            code, out = self._run(td, spec, structured)
            self.assertEqual(code, 0, out)

    def test_affine_residual_kind_rejected(self) -> None:
        """AC3: the ambiguous affine_residual metric kind no longer exists;
        a spec using it is schema-rejected."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            self._make_run(td, 'main.csv', 0.0, 0.0)
            spec = self._evi_spec('main.csv', self._aligned_runs(td))
            spec['metrics'] = [{'id': 'evi', 'kind': 'affine_residual',
                                'column': 'I(LD)'}]
            code, out = self._run(td, spec, {'metrics': {}})
            self.assertNotEqual(code, 0,
                                f'affine_residual must be rejected: {out}')

    def test_cross_run_token_mismatch_rejected(self) -> None:
        """AC4: a run whose time axis does not contain the exact token is
        rejected; no interpolation or resampling is applied."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            self._make_run(td, 'main.csv', 0.0, 0.0)
            runs = self._aligned_runs(td)
            self._make_run(td, 'run12.csv', 6e-4, 7e-5, offset_ps=0.05)
            spec = self._evi_spec('main.csv', runs)
            structured = {'metrics': {'evi': {
                'rhat': self.RHAT, 'vth': self.VTH, 'e_L': 0.0}}}
            code, out = self._run(td, spec, structured)
            self.assertNotEqual(code, 0, 'token mismatch must fail')
            self.assertIn('exact timestamp token', out)

    def test_interpolated_e_l_rejected(self) -> None:
        """AC4: an e_L computed by independent load interpolation (the old
        ambiguous semantics) must fail against the endpoint-VI value."""
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            self._make_run(td, 'main.csv', 0.0, 0.0)
            spec = self._evi_spec('main.csv', self._aligned_runs(td))
            structured = {'metrics': {'evi': {
                'rhat': self.RHAT, 'vth': self.VTH, 'e_L': 1e-4}}}
            code, out = self._run(td, spec, structured)
            self.assertNotEqual(code, 0,
                                f'interpolated e_L must fail: {out}')


class RendererTests(unittest.TestCase):
    def test_deterministic_render_and_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            struct = {'metadata': {'title': 't', 'run_id': 'r', 'spec_id': 's'},
                      'metrics': {'a': 1.5, 'b': 2.5e-3},
                      'windows': {'pre': [0, 40]}, 'notes': ['n1']}
            s_p = pathlib.Path(td) / 's.json'
            r_p = pathlib.Path(td) / 'r.md'
            s_p.write_text(json.dumps(struct), encoding='utf-8')
            p1 = subprocess.run([sys.executable, str(RENDERER), str(s_p),
                                 str(r_p)], capture_output=True, text=True)
            self.assertEqual(p1.returncode, 0, p1.stderr)
            first = r_p.read_bytes()
            p2 = subprocess.run([sys.executable, str(RENDERER), str(s_p),
                                 str(r_p)], capture_output=True, text=True)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(first, r_p.read_bytes(), 'determinism')
            r_p.write_text(r_p.read_text().replace('1.500000000e+00',
                                                   '9.900000000e+00'))
            p3 = subprocess.run([sys.executable, str(RENDERER), str(s_p),
                                 str(r_p), '--check'], capture_output=True,
                                text=True)
            self.assertNotEqual(p3.returncode, 0, 'tampered headline must fail')


if __name__ == '__main__':
    unittest.main()
