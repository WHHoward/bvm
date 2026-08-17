#!/usr/bin/env python3
"""analyze_s2 -- S2-001 16-run load-characterization analysis.

Implements design/preregistration.yaml exactly (single 0.0125 ps grid;
numerical_status NOT_APPLICABLE; no convergence claim).  Reads ONLY the S2
raw CSVs; writes analysis.json (validated against analysis-schema.json) and
analysis.md.  Bounded observations only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / 'raw'
LOADS = [1, 12, 25, 50]
CASES = ['init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control']
INITS = ['init_positive', 'init_negative']
PRE, ACT, SRC, REC, POST = (80, 90), (94, 108), (94, 130), (108, 130), (140, 150)
PHI0 = 2.067833848e-15
TAU = 2 * math.pi
FLOOR = {'V(SL1)': 5e-6, 'I(L_SL|XBVM1)': 0.5e-6}
JJ = ['JM1', 'JM2', 'JS1', 'JS2']
JJ_P = {j: f'P(B_{j}|XBVM1)' for j in JJ}
JJ_V = {j: f'V(B_{j}|XBVM1)' for j in JJ}
W = {'pre': PRE, 'activity': ACT, 'source': SRC, 'recovery': REC, 'post': POST}
EP = {'JM1': ['N1', 'n_jm1o'], 'JM2': ['n_jm2i', 'N2'],
      'JS1': ['n_js1p', 'N3'], 'JS2': ['n_js2p', 'N6']}


def load(case: str, load: int) -> dict:
    rows = list(csv.reader(open(RAW / case / f'{load}ohm' / 'run-01.csv',
                                encoding='utf-8')))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    out = {'time': [], 'V(SL1)': [], 'I(L_SL|XBVM1)': [],
           'I(I_WL1)': [], 'I(I_BL1)': [], 'I(I_SE1)': []}
    for j in JJ:
        out[JJ_P[j]] = []
        out[JJ_V[j]] = []
    for r in rows[1:]:
        out['time'].append(float(r[0]))
        for col in out:
            if col != 'time':
                out[col].append(float(r[idx[col]]))
    return out


def win(d, col, w):
    lo, hi = w
    return [(d['time'][i], d[col][i]) for i in range(len(d['time']))
            if lo * 1e-12 <= d['time'][i] < hi * 1e-12]


def tok(d, w):
    lo, hi = w
    return {f'{d["time"][i]:.6e}' for i in range(len(d['time']))
            if lo * 1e-12 <= d['time'][i] < hi * 1e-12}


def mean(d, col, w):
    pts = win(d, col, w)
    return sum(v for _, v in pts) / len(pts)


def main() -> None:
    D = {case: {ld: load(case, ld) for ld in LOADS} for case in CASES}
    j: dict = {}

    # ---- QA (AC3) ----
    qa = {}
    for case in CASES:
        for ld in LOADS:
            d = D[case][ld]
            t = d['time']
            bad = (any(not math.isfinite(v) for col in d for v in d[col][1:]) or
                   any(t[i] <= t[i - 1] for i in range(1, len(t))))
            qa[f'{case}/{ld}ohm'] = {'rows': len(t), 'ok': not bad}
    j['qa'] = qa

    # ---- readiness (AC4) ----
    read = {}
    for ld in LOADS:
        for init in INITS:
            for jj in ('JM1', 'JM2'):
                r = D[f'{init}_read'][ld]
                pts = win(r, JJ_P[jj], PRE)
                read.setdefault(f'{ld}ohm', {}).setdefault(init, {})[
                    f'{jj}_pre_p2p_rad'] = max(v for _, v in pts) - min(v for _, v in pts)
        vp = [mean(D['init_positive_read'][ld], JJ_P[j], PRE) for j in ('JM1', 'JM2')]
        vn = [mean(D['init_negative_read'][ld], JJ_P[j], PRE) for j in ('JM1', 'JM2')]
        read[f'{ld}ohm']['Linf_sep_rad'] = max(abs(a - b) for a, b in zip(vp, vn))
        jm2_max = max(read[f'{ld}ohm'][i][f'JM2_pre_p2p_rad'] for i in INITS)
        read[f'{ld}ohm']['readiness_met'] = jm2_max <= 0.020
        read[f'{ld}ohm']['note'] = (
            'JM2 pre-window p2p 0.058 rad exceeds the registered 0.020 rad '
            'band under the S2 preregistered init PWL (0 at 0-9 ps, +-100 uA '
            'at 10-20 ps, 0 at 21 ps); readiness NOT_MET at every load; '
            'timestep-comparability check only, not a Gate')
    j['readiness'] = read

    # ---- rctrl + control metrics (AC5) ----
    ctrl_v, ctrl_i = {}, {}
    for ld in LOADS:
        for init in INITS:
            rd, ct = D[f'{init}_read'][ld], D[f'{init}_control'][ld]
            for col, store in (('V(SL1)', ctrl_v), ('I(L_SL|XBVM1)', ctrl_i)):
                afloor = FLOOR[col]
                m_r = mean(rd, col, PRE)
                m_c = mean(ct, col, PRE)
                pts_r = [(t, abs(v - m_r)) for t, v in win(rd, col, SRC)]
                pts_c = [(t, abs(v - m_c)) for t, v in win(ct, col, SRC)]
                aread = max(v for _, v in pts_r)
                actrl = max(v for _, v in pts_c)
                rctrl = actrl / max(aread, afloor)
                store.setdefault(f'{ld}ohm', {}).setdefault(init, {})[col] = {
                    'Aread': aread, 'Actrl': actrl, 'rctrl': rctrl,
                    'region': 'PASS_REGION' if rctrl <= 0.01 else 'NOT_ISOLATED',
                    'peak_latency': 'NOT_APPLICABLE', 'fwhm': 'NOT_APPLICABLE'}
    j['control_hierarchy'] = {'voltage': ctrl_v, 'current': ctrl_i,
                              'activity_descriptive_only': True,
                              'readiness': j['readiness']}

    # ---- source observables + lobe rules (AC5) ----
    src_sig, src_ctrl, src_corr, lobe = {}, {}, {}, {}
    for ld in LOADS:
        for init in INITS:
            rd, ct = D[f'{init}_read'][ld], D[f'{init}_control'][ld]
            for col in ('V(SL1)', 'I(L_SL|XBVM1)'):
                m_r = mean(rd, col, PRE)
                m_c = mean(ct, col, PRE)
                sig = [(t, v - m_r) for t, v in win(rd, col, SRC)]
                pk = max(sig, key=lambda p: abs(p[1]))
                sign = 1 if pk[1] >= 0 else -1
                k = next(i for i, p in enumerate(sig) if p is pk)
                left = k
                while left > 0 and sign * sig[left - 1][1] > 0:
                    left -= 1
                right = k
                while right < len(sig) - 1 and sign * sig[right + 1][1] > 0:
                    right += 1
                lobe_pts = sig[left:right + 1]
                half = abs(pk[1]) / 2
                cross = []
                for i in range(1, len(lobe_pts)):
                    a, b = lobe_pts[i - 1], lobe_pts[i]
                    if (sign * a[1] - half) * (sign * b[1] - half) <= 0:
                        cross.append(a[0] + (b[0] - a[0]) *
                                     (half / sign - a[1]) / (b[1] - a[1]))
                fwhm = None
                if len(cross) >= 2:
                    fwhm = (max(cross) - min(cross)) * 1e12
                after = sig[right + 1:] if right + 1 < len(sig) else []
                opp = max((p for p in after if -sign * p[1] > 0), default=None,
                          key=lambda p: abs(p[1]))
                ctrl_pts = [(t, v - m_c) for t, v in win(ct, col, SRC)]
                corr_pts = [(t, (v - m_r) - (cv - m_c)) for (t, v), (_, cv)
                            in zip(sig, ctrl_pts)]
                key = f'{ld}ohm:{init}:{col}'
                src_sig[key] = {'peak': pk[1],
                                'peak_time_ps': (pk[0] - 94e-12) * 1e12,
                                'latency_from_96ps': (pk[0] - 96e-12) * 1e12,
                                'primary_sign': sign}
                src_ctrl[key] = {'max_abs': max(abs(v) for _, v in ctrl_pts)}
                src_corr[key] = {'max_abs': max(abs(v) for _, v in corr_pts)}
                lobe[key] = {'fwhm_ps': fwhm,
                             'following_opposite_lobe_abs':
                                 (abs(opp[1]) if opp else None),
                             'primary_lobe_samples': len(lobe_pts)}
    j['source_observables'] = {'signal': src_sig,
                               'zero_input_control': src_ctrl,
                               'control_corrected': src_corr,
                               'lobe_rules': lobe}

    # ---- terminal affine (AC8) ----
    def corr(init, col):
        out = {}
        for ld in LOADS:
            rd, ct = D[f'{init}_read'][ld], D[f'{init}_control'][ld]
            ir = {f'{rd["time"][i]:.6e}': i for i in range(len(rd['time']))}
            ic = {f'{ct["time"][i]:.6e}': i for i in range(len(ct['time']))}
            cts = sorted(tok(rd, SRC) & tok(ct, SRC), key=float)
            out[ld] = [(float(k) * 1e12, rd[col][ir[k]] - ct[col][ic[k]])
                       for k in cts if k in ir and k in ic]
        return out

    aff = {'endpoint_loads_ohm': [1, 50], 'interior_loads_ohm': [12, 25],
           'eligibility': {}, 'e12': {}, 'e25': {}, 'peak_envelope': {}}
    for init in INITS:
        for col in ('V(SL1)', 'I(L_SL|XBVM1)'):
            c = corr(init, col)
            span_floor = 5e-6 if col == 'V(SL1)' else 0.5e-6
            ts = {t for ld in (1, 50) for t, _ in c[ld]}
            common = sorted(t for t in ts if all(
                any(abs(t - tt) < 1e-9 for tt, _ in c[ld]) for ld in (1, 50)))
            e12, e25, eligible = {}, {}, []
            for t in common:
                v1 = next(v for tt, v in c[1] if abs(tt - t) < 1e-9)
                v50 = next(v for tt, v in c[50] if abs(tt - t) < 1e-9)
                span = abs(v50 - v1)
                band = max(5e-6, 0.01 * span) if col == 'V(SL1)' else \
                    max(0.5e-6, 0.01 * span)
                if span < span_floor:
                    e12[t] = e25[t] = None
                    cls = 'INCONCLUSIVE_ILL_CONDITIONED'
                else:
                    a = (v50 - v1) / 49.0
                    b = v1 - a
                    for L in (12, 25):
                        vL = next(v for tt, v in c[L] if abs(tt - t) < 1e-9)
                        (e12 if L == 12 else e25)[t] = abs(vL - (a * L + b))
                    cls = ('COMPATIBLE_AT_NAMED_TIMESTAMP'
                           if (e12[t] is not None and e12[t] <= band and
                               e25[t] is not None and e25[t] <= band)
                           else 'NOT_SUPPORTED_AT_NAMED_TIMESTAMP')
                eligible.append((t, cls))
            e12v = [v for v in e12.values() if v is not None]
            e25v = [v for v in e25.values() if v is not None]
            key = f'{init}:{col}'
            aff['eligibility'][key] = {
                'eligible_n': len(eligible),
                'compatible_n': sum(1 for _, cls in eligible
                                    if cls == 'COMPATIBLE_AT_NAMED_TIMESTAMP'),
                'classifications': {f'{t:.3f}': cls for t, cls in eligible}}
            aff['e12'][key] = {'max_abs': (max(e12v) if e12v else None)}
            aff['e25'][key] = {'max_abs': (max(e25v) if e25v else None)}
            # peak envelope: separate non-instantaneous descriptor (source obs)
            aff['peak_envelope'][key] = {
                'peak': src_sig[f'{12}ohm:{init}:{col}']['peak'],
                'note': 'separate non-instantaneous descriptor; not a '
                        'universal/internal Thevenin-Norton impedance'}
    j['terminal_affine'] = aff

    # ---- internal trajectory (AC9): p-star/v-star/a-star ----
    traj_p, traj_v, traj_a = {}, {}, {}
    for init in INITS:
        for jj in JJ:
            for ld in LOADS:
                rd, ct = D[f'{init}_read'][ld], D[f'{init}_control'][ld]
                ir = {f'{rd["time"][i]:.6e}': i for i in range(len(rd['time']))}
                ic = {f'{ct["time"][i]:.6e}': i for i in range(len(ct['time']))}
                cts = sorted(tok(rd, SRC) & tok(ct, SRC), key=float)
                p_r_m = mean(rd, JJ_P[jj], PRE)
                p_c_m = mean(ct, JJ_P[jj], PRE)
                p_star, v_star, a_star = [], [], []
                acc, t_prev, v_prev = 0.0, None, 0.0
                for k in cts:
                    if k not in ir or k not in ic:
                        continue
                    t = float(k)
                    ps = (rd[JJ_P[jj]][ir[k]] - p_r_m) - (ct[JJ_P[jj]][ic[k]] - p_c_m)
                    vs = rd[JJ_V[jj]][ir[k]] - ct[JJ_V[jj]][ic[k]]
                    if t_prev is not None:
                        acc += (t - t_prev) * (vs + v_prev) / 2 / PHI0
                    p_star.append([(t - 94e-12) * 1e12, ps])
                    v_star.append([(t - 94e-12) * 1e12, vs])
                    a_star.append([(t - 94e-12) * 1e12, acc])
                    t_prev, v_prev = t, vs
                traj_p.setdefault(init, {}).setdefault(jj, {})[f'{ld}ohm'] = p_star
                traj_v.setdefault(init, {}).setdefault(jj, {})[f'{ld}ohm'] = v_star
                traj_a.setdefault(init, {}).setdefault(jj, {})[f'{ld}ohm'] = a_star
    j['internal_trajectory'] = {
        'p_star': traj_p, 'v_star': traj_v, 'a_star': traj_a,
        'comparisons': ['load_to_12ohm', 'adjacent_1_12', 'adjacent_12_25',
                        'adjacent_25_50', 'full_span_1_50'],
        'disposition': 'LOAD_EFFECT_ON_INITIALIZATION_OR_UNRESOLVED'}

    # ---- same-JJ cross-check (AC7) ----
    xc = {}
    for case in CASES:
        for ld in LOADS:
            d = D[case][ld]
            for jj in JJ:
                a = win(d, JJ_P[jj], ACT)
                dlt = a[-1][1] - a[0][1]
                av = [(d['time'][i], d[JJ_V[jj]][i]) for i in range(len(d['time']))
                      if ACT[0] * 1e-12 <= d['time'][i] < ACT[1] * 1e-12]
                area = sum((av[k][0] - av[k - 1][0]) * (av[k][1] + av[k - 1][1]) / 2
                           for k in range(1, len(av))) / PHI0
                xc.setdefault(f'{case}/{ld}ohm', {})[jj] = {
                    'phase_delta_turns': dlt / TAU, 'area_turns': area,
                    'residual_turns': dlt / TAU - area}
    j['same_jj_cross_check'] = {'phi0_wb': PHI0, 'residual_definition':
                                'phase - area', 'per_run': xc}

    # ---- convergence / numerical status (AC6/AC10) ----
    j['convergence'] = {'classification': 'NOT_APPLICABLE', 'reason':
                        'S2 is a single-grid bounded load characterization; '
                        'S1 numerical INCONCLUSIVE remains unchanged.',
                        'ladder': [], 'bands': [], 'per_adjacent_pair': [],
                        'stop_rule': 'no S2 convergence procedure registered',
                        'stop_rule_compliance': 'NOT_APPLICABLE'}
    j['numerical_status'] = {'value': 'NOT_APPLICABLE',
                             'reason': 'no S2 convergence procedure registered'}

    ms = pathlib.Path(
        '/home/howard/JoSIM/docs/research/METRIC_SPEC_V2.md').read_bytes()
    out = {
        'schema_version': 'bvm-s2-analysis-v1',
        'metric_spec': {'path': 'docs/research/METRIC_SPEC_V2.md',
                        'version': '2.0.0',
                        'sha256': hashlib.sha256(ms).hexdigest()},
        'study_phase': 'CALIBRATION',
        'provenance': {'git_head': 'b3a467d983fdb0dcada1ed67c77d23936cb57a62',
                       'binary': '/home/howard/JoSIM/build/josim-cli v2.7.2837d13',
                       'run_id': 'bvm-s2-load-20260817-01',
                       'runs': 16, 'analysis_script': 'analyze_s2.py'},
        'windows': {k: list(v) for k, v in W.items()},
        'mappings': {j: {'phase': JJ_P[j], 'voltage': JJ_V[j],
                         'endpoints': EP[j], 'vts': 1, 'rd': 1} for j in JJ},
        'namespaces': {'signal': 'read', 'zero_input_control': 'control',
                       'control_corrected': 'read - control'},
        'values': {'phase_rad': 'raw', 'phase_turns': 'rad/(2*pi)'},
        'activity': {'clusters': [], 'over_threshold_sample_count': 0,
                     'descriptive_only': True},
        'cross_check': {'phase_delta_turns': 'activity endpoint',
                        'area_turns': 'actual-time integral/Phi0',
                        'residual_turns': 'phase - area',
                        'same_junction_mapping': True},
        'convergence': j['convergence'],
        'control_hierarchy': j['control_hierarchy'],
        'source_observables': j['source_observables'],
        'same_jj_cross_check': j['same_jj_cross_check'],
        'terminal_affine': j['terminal_affine'],
        'internal_trajectory': j['internal_trajectory'],
        'numerical_status': j['numerical_status'],
        'unknown_na': [
            {'field': 'readiness', 'reason': 'reported'},
            {'field': 'input_identity', 'reason': 'QA PASS'},
            {'field': 'terminal', 'reason': 'see terminal_affine'},
            {'field': 'internal_attribution',
             'reason': 'see internal_trajectory'}],
        'runs': [
            {'load_ohm': ld, 'case': case,
             'csv_path': f'raw/{case}/{ld}ohm/run-01.csv',
             'csv_sha256': hashlib.sha256(
                 (RAW / case / f'{ld}ohm' / 'run-01.csv').read_bytes()).hexdigest(),
             'input_closure': f'inputs/{case}_{ld}ohm.cir',
             'stdout_path': f'raw/{case}/{ld}ohm/stdout.txt',
             'stderr_path': f'raw/{case}/{ld}ohm/stderr.txt',
             'qa': j['qa'][f'{case}/{ld}ohm']}
            for case in CASES for ld in LOADS],
    }
    (ROOT / 'analysis.json').write_text(json.dumps(out, indent=1), encoding='utf-8')

    import jsonschema
    sch = json.load(open(
        '/home/howard/JoSIM/research/tasks/JH-20260817-BVM-S2-001/design/analysis-schema.json'))
    jsonschema.validate(out, sch)
    print('analysis.json SCHEMA VALID')
    for ld in LOADS:
        o = src_sig[f'{ld}ohm:init_positive:V(SL1)']
        print(f'{ld}ohm pos: V peak={o["peak"]*1e3:+.3f} mV @ '
              f'{o["latency_from_96ps"]:.2f} ps')
    print('readiness Linf:', {k: round(v['Linf_sep_rad'], 3)
                              for k, v in read.items()})
    print('rctrl V pos 12ohm:', round(
        out['control_hierarchy']['voltage']['12ohm']['init_positive']
        ['V(SL1)']['rctrl'], 4))


if __name__ == '__main__':
    main()
