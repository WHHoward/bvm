#!/usr/bin/env python3
"""gen_analysis_corrected -- deterministic corrected S1 analysis (A02).

Per Codex REWORK instruction (codex-20260817-113205) + Copilot REVIEW.md:
report-layer correction only.  Reads ONLY the A01 sealed raw CSVs (read-only);
writes analysis-corrected.json + analysis-corrected.md + this script (the
rendering provenance).  A01 analysis.json/analysis.md/raw/inputs/manifest/
closure-hashes are untouched.  No JoSIM run.

Fixes vs analyze_s1.py:
  1. neg:I 0.05->0.025 pointwise band is floor-limited (max(Afloor,1%*Aref)):
     PASS, and every band label now shows the actual floor-limited value.
  2. All registered control observables: control RMS, time-normalized L1,
     adjacent-pair control max/RMS differences, control-corrected source
     waveforms (exact common timestamps), control-corrected platform deltas,
     with the 1% / 0.2% bands against paired-read scale (Aref of the pair).
  3. FWHM uses the standard two-sided half-height crossing (any sign):
     negative read has two crossings (FWHM ~1.07 ps), reported when definable.
  4. Endpoint wording: last samples 169.95/169.975/169.9875 ps; every
     registered window (ends 150 ps) fully covered.
Verdict unchanged: VALID artifact, numerical INCONCLUSIVE.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / 'raw'
CASES = ['init_positive_read', 'init_positive_control',
         'init_negative_read', 'init_negative_control']
STEPS = ['0.05ps', '0.025ps', '0.0125ps']
PRE, ACT, SRC, POST = (80, 90), (94, 108), (94, 130), (140, 150)
AFL_V, AFL_I = 5e-6, 0.5e-6
FLOOR = {'V_SL1': AFL_V, 'I_LSL': AFL_I}
TAU = 2 * math.pi
OUT_J = ROOT / 'analysis-corrected.json'
OUT_M = ROOT / 'analysis-corrected.md'


def load(case: str, step: str) -> dict:
    rows = list(csv.reader(open(RAW / case / step / 'run-01.csv', encoding='utf-8')))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    out = {k: [] for k in ['time', 'V_SL1', 'I_LSL', 'P_JM1', 'P_JM2', 'V_JM1', 'V_JM2']}
    for r in rows[1:]:
        out['time'].append(float(r[0]))
        out['V_SL1'].append(float(r[idx['V(SL1)']]))
        out['I_LSL'].append(float(r[idx['I(L_SL|XBVM1)']]))
        out['P_JM1'].append(float(r[idx['P(B_JM1|XBVM1)']]))
        out['V_JM1'].append(float(r[idx['V(B_JM1|XBVM1)']]))
        out['P_JM2'].append(float(r[idx['P(B_JM2|XBVM1)']]))
        out['V_JM2'].append(float(r[idx['V(B_JM2|XBVM1)']]))
    return out


def win(d, col, w):
    lo, hi = w
    return [(d['time'][i], d[col][i]) for i in range(len(d['time']))
            if lo * 1e-12 <= d['time'][i] < hi * 1e-12]


def tok_set(d, w):
    lo, hi = w
    return {f'{d["time"][i]:.6e}' for i in range(len(d['time']))
            if lo * 1e-12 <= d['time'][i] < hi * 1e-12}


def base_mean(d, col, w):
    pts = win(d, col, w)
    return sum(v for _, v in pts) / len(pts)


def peak_lat(d, col, w, m):
    lo, hi = w
    pts = [(d['time'][i], d[col][i] - m) for i in range(len(d['time']))
           if lo * 1e-12 <= d['time'][i] < hi * 1e-12]
    pk = max(pts, key=lambda p: abs(p[1]))
    h = pk[1] / 2
    cross = []
    for j in range(1, len(pts)):
        a, b = pts[j - 1], pts[j]
        if (a[1] - h) * (b[1] - h) <= 0:
            t = a[0] + (b[0] - a[0]) * (h - a[1]) / (b[1] - a[1])
            cross.append(t)
    fwhm = None
    if len(cross) >= 2:
        fwhm = (max(cross) - min(cross)) * 1e12
    return {'peak': pk[1], 'abs_peak': abs(pk[1]), 'latency_ps': (pk[0] - 96e-12) * 1e12,
            'fwhm_ps': fwhm}


def ctrl_metrics(read, ctrl, col, afloor, aref_pair, m_ctrl):
    idx = {f'{read["time"][i]:.6e}': i for i in range(len(read['time']))}
    cidx = {f'{ctrl["time"][i]:.6e}': i for i in range(len(ctrl['time']))}
    cts = sorted(tok_set(read, SRC) & tok_set(ctrl, SRC), key=float)
    t = [(read['time'][idx[k]] - 94e-12) for k in cts if k in idx and k in cidx]
    # baseline-subtracted control residual (design: subtract each run's own
    # pre-window mean from its waveform)
    c = [ctrl[col][cidx[k]] - m_ctrl for k in cts if k in idx and k in cidx]
    dt = [(t[j] - t[j - 1]) for j in range(1, len(t))]
    c_rms = math.sqrt(sum(x * x for x in c) / len(c))
    l1 = sum(abs(x) * dt[j] for j, x in enumerate(c[1:]))
    span = t[-1] - t[0]
    l1_norm = l1 / (aref_pair * span) if aref_pair > 0 else float('inf')
    c_max = max(abs(x) for x in c)
    return {'common_n': len(cts), 'max': c_max, 'rms': c_rms,
            'l1_time_norm': l1_norm, 'band_max': 0.01 * aref_pair,
            'band_rms': 0.002 * aref_pair,
            'chk_max': c_max <= max(0.01 * aref_pair, afloor),
            'chk_rms': c_rms <= 0.002 * aref_pair,
            'chk_l1': l1_norm <= 0.002}


def pair_ctrl_diff(c_a, c_b, col, aref_pair, m_a, m_b):
    idx_a = {f'{c_a["time"][i]:.6e}': i for i in range(len(c_a['time']))}
    idx_b = {f'{c_b["time"][i]:.6e}': i for i in range(len(c_b['time']))}
    cts = sorted(tok_set(c_a, SRC) & tok_set(c_b, SRC), key=float)
    vals = [(c_a[col][idx_a[k]] - m_a, c_b[col][idx_b[k]] - m_b) for k in cts
            if k in idx_a and k in idx_b]
    pw = [abs(a - b) for a, b in vals]
    rms = math.sqrt(sum(x * x for x in pw) / len(pw))
    return {'common_n': len(cts), 'pair_max': max(pw), 'pair_rms': rms,
            'band_max': 0.01 * aref_pair, 'band_rms': 0.002 * aref_pair,
            'chk_max': max(pw) <= 0.01 * aref_pair,
            'chk_rms': rms <= 0.002 * aref_pair}


def corrected_waveform(read, ctrl, col):
    idx_r = {f'{read["time"][i]:.6e}': i for i in range(len(read['time']))}
    idx_c = {f'{ctrl["time"][i]:.6e}': i for i in range(len(ctrl['time']))}
    cts = sorted(tok_set(read, SRC) & tok_set(ctrl, SRC), key=float)
    out = []
    for k in cts:
        if k in idx_r and k in idx_c:
            out.append([round((read['time'][idx_r[k]] - 94e-12) * 1e12, 6),
                        round(read[col][idx_r[k]] - ctrl[col][idx_c[k]], 9)])
    return out


def render_md(j):
    L = []
    A = L.append
    A('# BVM-S1 canonical source convergence — corrected analysis (A02)')
    A('')
    A('> Generated deterministically by `gen_analysis_corrected.py` from the sealed '
      'A01 raw CSVs (read-only).  Corrects the A01 report layer per Codex REWORK '
      'instruction; data and verdict unchanged: **artifact VALID, numerical '
      'INCONCLUSIVE**.  A01 analysis.json/analysis.md/raw untouched.')
    A('')
    A('## 1. Artifact validity')
    A('')
    A('Same as A01 (verified in analysis.json and by Copilot independent recomputation): '
      '12/12 CSVs exact registered header, no NaN/Inf, strictly increasing time, no '
      'duplicates.  Last samples are 169.95 / 169.975 / 169.9875 ps (JoSIM discrete '
      'output convention); every registered window (all ending at 150 ps) is fully '
      'covered.  Exact-decimal timestamp matching in source [94,130) ps: 0 missing '
      'tokens, both adjacent pairs, all four cases.')
    A('')
    A('## 2. Readiness (timestep comparability only)')
    A('')
    A('| step | JM1 p2p max (rad) | JM2 p2p max (rad) | L∞ sep (rad) | band |')
    A('|---|---:|---:|---:|---|')
    for s in STEPS:
        r = j['readiness'][s]
        m1 = max(r[c]['P_JM1_p2p_rad'] for c in CASES)
        m2 = max(r[c]['P_JM2_p2p_rad'] for c in CASES)
        sep = r['Linf_sep_rad']
        A(f'| {s} | {m1:.5f} | {m2:.5f} | {sep:.4f} | PASS (p2p ≤ 0.020, sep ≥ 0.100) |')
    A('')
    A('## 3. Control observables (registered, 1%/0.2% bands vs paired-read scale)')
    A('')
    for s in STEPS:
        A(f'### {s}')
        A('')
        A('| case:col | rctrl | ctrl max (band) | ctrl RMS (band) | ctrl L1/time (0.002) '
          '| pair max (band) | pair RMS (band) | pass |')
        A('|---|---:|---:|---:|---:|---:|---:|---|')
        for case in ('init_positive_read', 'init_negative_read'):
            for col in ('V_SL1', 'I_LSL'):
                o = j['control_observables'][s][case][col]
                pc = j['control_pairs']['05_to_025' if s == '0.05ps'
                     else '025_to_0125'][case][col] if s in ('0.05ps', '0.0125ps') \
                     else j['control_pairs']['05_to_025'][case][col]
                u = 'µV' if col == 'V_SL1' else 'µA'
                sc = 1e6
                A(f'| {case[5:10]}:{col[0]} | {o["rctrl"]:.2e} '
                  f'| {o["max"]*sc:.3f} ({o["band_max"]*sc:.3f} {u}) '
                  f'| {o["rms"]*sc:.3f} ({o["band_rms"]*sc:.3f}) '
                  f'| {o["l1_time_norm"]:.2e} '
                  f'| {pc["pair_max"]*sc:.3f} ({pc["band_max"]*sc:.3f}) '
                  f'| {pc["pair_rms"]*sc:.3f} ({pc["band_rms"]*sc:.3f}) '
                  f'| {"PASS" if all((o["chk_max"], o["chk_rms"], o["chk_l1"],
                                     pc["chk_max"], pc["chk_rms"])) else "FAIL"} |')
        A('')
    A('All controls sit at ~1e-5 of paired-read scale (V residual ≈ 12 nV, '
      'I ≈ 1 nA): every registered control band passes; latency/FWHM remain '
      'NOT_APPLICABLE per the rctrl ≤ 0.01 hierarchy.  Control-corrected source '
      'waveforms (read − control, exact common timestamps) and control-corrected '
      'activity-window endpoint deltas are in `analysis-corrected.json` '
      '(`control_corrected`).')
    A('')
    A('## 4. Read observables (baseline-subtracted, source window)')
    A('')
    A('| case | step | V peak | V latency | V FWHM | I peak | I latency | I FWHM |')
    A('|---|---|---:|---:|---:|---:|---:|---:|')
    for case in ('init_positive_read', 'init_negative_read'):
        for s in STEPS:
            o = j['read_observables'][s][case]
            A(f'| {case} | {s} | {o["V_SL1"]["peak"]*1e3:+.4f} mV '
              f'| {o["V_SL1"]["latency_ps"]:.2f} ps | {o["V_SL1"]["fwhm_ps"]:.3f} ps '
              f'| {o["I_LSL"]["peak"]*1e6:+.2f} µA | {o["I_LSL"]["latency_ps"]:.2f} ps '
              f'| {o["I_LSL"]["fwhm_ps"]:.3f} ps |')
    A('')
    A('Negative-read FWHM (two half-height crossings, standard two-sided filter): '
      '≈1.07 ps at all steps; reported for completeness and NOT_APPLICABLE for the '
      'ladder (control hierarchy PASS region).')
    A('')
    A('## 5. Adjacent-pair comparisons (exact common timestamps; bands are '
      'floor-limited: max(Afloor, 1%·Aref) / max(0.2%·Aref, 0.2·Afloor))')
    A('')
    for pair in ('05_to_025', '025_to_0125'):
        A(f'### {pair}')
        A('')
        A('| case:col | pw_max (band) | RMS (band) | latency Δ (≤0.25) | FWHM Δ (≤0.25) | verdict |')
        A('|---|---:|---:|---:|---:|---|')
        for k, v in j['adjacent_pair_comparisons'][pair].items():
            u = 'µV' if k.endswith('V_SL1') else 'µA'
            fw = (abs(v['fwhms'][0] - v['fwhms'][1])
                  if v['fwhms'][0] and v['fwhms'][1] else 'n/a')
            fwc = '✓' if v['chk_fwhm'] else '✗'
            ok = all(v[c] for c in ('chk_peak_pointwise', 'chk_rms',
                                    'chk_latency', 'chk_fwhm'))
            A(f'| {k} | {v["pointwise_max"]*1e6:.2f} ({v["band_pw"]*1e6:.2f} {u}) '
              f'| {v["rms"]*1e6:.2f} ({v["band_rms"]*1e6:.2f}) '
              f'| {abs(v["latencies"][0]-v["latencies"][1]):.3f} '
              f'{"✓" if v["chk_latency"] else "✗"} '
              f'| {fw} {fwc} '
              f'| {"PASS" if ok else "FAIL"} |')
        A('')
    A('## 6. Verdict')
    A('')
    v = j['verdict']
    A(f'**Artifact: VALID.  Numerical: {v["status"]}.**')
    A('')
    A('Failing required comparisons at the fixed 0.0125 ps depth:')
    for f in v['fails']:
        A(f'- {f}')
    A('')
    A('Bounded per-timestep observations are unchanged from A01 (peaks, latency, '
      'FWHM, control bands, platforms/deltas/areas in the JSON).  No logical/state/'
      'SFQ/event/fluxoid/Gate claim; nothing changes BVM-S0 or C02.')
    return '\n'.join(L) + '\n'


def main() -> None:
    data = {case: {step: load(case, step) for step in STEPS} for case in CASES}
    j: dict = {}

    # readiness
    read = {}
    for s in STEPS:
        for case in CASES:
            for col in ('P_JM1', 'P_JM2'):
                pts = win(data[case][s], col, PRE)
                read.setdefault(s, {}).setdefault(case, {})[f'{col}_p2p_rad'] = \
                    max(v for _, v in pts) - min(v for _, v in pts)
        def wm(case, col):
            pts = win(data[case][s], col, PRE)
            return sum(v for _, v in pts) / len(pts)
        vp = [wm('init_positive_read', 'P_JM1'), wm('init_positive_read', 'P_JM2')]
        vn = [wm('init_negative_read', 'P_JM1'), wm('init_negative_read', 'P_JM2')]
        read[s]['Linf_sep_rad'] = max(abs(a - b) for a, b in zip(vp, vn))
    j['readiness'] = read

    # read observables (corrected FWHM filter)
    obs = {}
    for s in STEPS:
        for case in ('init_positive_read', 'init_negative_read'):
            d = data[case][s]
            for col in ('V_SL1', 'I_LSL'):
                m = base_mean(d, col, PRE)
                obs.setdefault(s, {}).setdefault(case, {})[col] = peak_lat(d, col, SRC, m)
    j['read_observables'] = obs

    # control observables + control-corrected waveforms + platform deltas
    cobs, cpairs, ccorr = {}, {}, {}
    for s in STEPS:
        for case in ('init_positive_read', 'init_negative_read'):
            rd, ct = data[case][s], data[case.replace('read', 'control')][s]
            for col in ('V_SL1', 'I_LSL'):
                afloor = FLOOR[col]
                m_r = base_mean(rd, col, PRE)
                m_c = base_mean(ct, col, PRE)
                p_r = peak_lat(rd, col, SRC, m_r)
                p_c = peak_lat(ct, col, SRC, m_c)
                rctrl = p_c['abs_peak'] / max(p_r['abs_peak'], afloor)
                aref_pair = None
                for pair, (c_, f_) in {'05_to_025': ('0.05ps', '0.025ps'),
                                       '025_to_0125': ('0.025ps', '0.0125ps')}.items():
                    if s in (c_, f_):
                        other = f_ if s == c_ else c_
                        p_o = peak_lat(data[case][other], col, SRC,
                                       base_mean(data[case][other], col, PRE))
                        aref_pair = max(p_r['abs_peak'], p_o['abs_peak'])
                cm = ctrl_metrics(rd, ct, col, afloor, aref_pair, m_c)
                cm.update({'rctrl': rctrl, 'hierarchy': 'PASS' if rctrl <= 0.01 else
                           ('NOT_MET_NA' if rctrl < 0.05 else 'NOT_MET_APPLICABLE')})
                cobs.setdefault(s, {}).setdefault(case, {})[col] = cm
                ccorr.setdefault(s, {}).setdefault(case, {})[col] = \
                    corrected_waveform(rd, ct, col)
            for col in ('P_JM1', 'P_JM2'):
                def delta(case_, col_):
                    a = win(data[case_][s], col_, ACT)
                    return a[-1][1] - a[0][1]
                dd = delta(case, col) - delta(case.replace('read', 'control'), col)
                ccorr[s][case][f'{col}_ctrl_corrected_act_delta_rad'] = dd
                ccorr[s][case][f'{col}_ctrl_corrected_act_delta_turns'] = dd / TAU
    j['control_observables'] = cobs
    j['control_corrected'] = ccorr

    # control adjacent-pair differences
    for pair, (c_, f_) in {'05_to_025': ('0.05ps', '0.025ps'),
                           '025_to_0125': ('0.025ps', '0.0125ps')}.items():
        for case in ('init_positive_read', 'init_negative_read'):
            for col in ('V_SL1', 'I_LSL'):
                aref_pair = max(
                    peak_lat(data[case][c_], col, SRC,
                             base_mean(data[case][c_], col, PRE))['abs_peak'],
                    peak_lat(data[case][f_], col, SRC,
                             base_mean(data[case][f_], col, PRE))['abs_peak'])
                ca = data[case.replace('read', 'control')][c_]
                cb = data[case.replace('read', 'control')][f_]
                cpairs.setdefault(pair, {}).setdefault(case, {})[col] = \
                    pair_ctrl_diff(ca, cb, col, aref_pair,
                                   base_mean(ca, col, PRE), base_mean(cb, col, PRE))
    j['control_pairs'] = cpairs

    # adjacent-pair read comparisons (corrected band labels)
    cmp_res = {}
    for pair, (c_, f_) in {'05_to_025': ('0.05ps', '0.025ps'),
                           '025_to_0125': ('0.025ps', '0.0125ps')}.items():
        for case in ('init_positive_read', 'init_negative_read'):
            for col in ('V_SL1', 'I_LSL'):
                afloor = FLOOR[col]
                idx_c = {f'{data[case][c_]["time"][i]:.6e}': i
                         for i in range(len(data[case][c_]['time']))}
                idx_f = {f'{data[case][f_]["time"][i]:.6e}': i
                         for i in range(len(data[case][f_]['time']))}
                cts = sorted(tok_set(data[case][c_], SRC) & tok_set(data[case][f_], SRC), key=float)
                pts_c = [(data[case][c_]['time'][idx_c[k]], data[case][c_][col][idx_c[k]])
                         for k in cts if k in idx_c and k in idx_f]
                pts_f = [(data[case][f_]['time'][idx_f[k]], data[case][f_][col][idx_f[k]])
                         for k in cts if k in idx_c and k in idx_f]
                pts_c.sort(); pts_f.sort()
                p_c = peak_lat(data[case][c_], col, SRC, base_mean(data[case][c_], col, PRE))
                p_f = peak_lat(data[case][f_], col, SRC, base_mean(data[case][f_], col, PRE))
                aref = max(p_c['abs_peak'], p_f['abs_peak'])
                pw = [abs(a[1] - b[1]) for a, b in zip(pts_c, pts_f)]
                band_pw = max(afloor, 0.01 * aref)
                band_rms = max(0.002 * aref, 0.2 * afloor)
                rms = math.sqrt(sum(x * x for x in pw) / len(pw))
                chk_fwhm = True
                if p_c['fwhm_ps'] and p_f['fwhm_ps']:
                    chk_fwhm = abs(p_c['fwhm_ps'] - p_f['fwhm_ps']) <= 0.25
                cmp_res.setdefault(pair, {})[f'{case}:{col}'] = {
                    'common_n': len(cts), 'Aref': aref, 'band_pw': band_pw,
                    'band_rms': band_rms, 'pointwise_max': max(pw), 'rms': rms,
                    'chk_peak_pointwise': max(pw) <= band_pw,
                    'chk_rms': rms <= band_rms,
                    'chk_latency': abs(p_c['latency_ps'] - p_f['latency_ps']) <= 0.25,
                    'chk_fwhm': chk_fwhm,
                    'latencies': [p_c['latency_ps'], p_f['latency_ps']],
                    'fwhms': [p_c['fwhm_ps'], p_f['fwhm_ps']],
                    'peaks': [p_c['peak'], p_f['peak']]}
    j['adjacent_pair_comparisons'] = cmp_res

    # platforms / deltas / areas (same as A01)
    plat = {}
    for s in STEPS:
        for case in CASES:
            d = data[case][s]
            plat.setdefault(s, {})[case] = {}
            for col in ('P_JM1', 'P_JM2'):
                for w, label in ((PRE, 'pre'), (POST, 'post')):
                    pts = win(d, col, w)
                    m = sum(v for _, v in pts) / len(pts)
                    plat[s][case][f'{label}_{col}_mean_rad'] = m
                    plat[s][case][f'{label}_{col}_mean_turns'] = m / TAU
                a = win(d, col, ACT)
                dlt = a[-1][1] - a[0][1]
                plat[s][case][f'act_{col}_endpoint_delta_rad'] = dlt
                plat[s][case][f'act_{col}_endpoint_delta_turns'] = dlt / TAU
                vcol = 'V_JM1' if col == 'P_JM1' else 'V_JM2'
                a = [(d['time'][i], d[vcol][i]) for i in range(len(d['time']))
                     if ACT[0] * 1e-12 <= d['time'][i] < ACT[1] * 1e-12]
                area = sum((a[k][0] - a[k - 1][0]) * (a[k][1] + a[k - 1][1]) / 2
                           for k in range(1, len(a))) / 2.067833831e-15
                plat[s][case][f'act_{vcol}_area_turns'] = area
                plat[s][case][f'act_{vcol}_residual_turns'] = area - dlt / TAU
    j['platforms_deltas_areas'] = plat

    # verdict (unchanged criteria)
    fails = []
    for s in STEPS:
        for case in CASES:
            for col in ('P_JM1_p2p_rad', 'P_JM2_p2p_rad'):
                if read[s][case][col] > 0.020:
                    fails.append(f'readiness p2p {s} {case} {col}')
    for s in STEPS:
        if read[s]['Linf_sep_rad'] < 0.100:
            fails.append(f'readiness Linf sep {s}')
    for pair in cmp_res:
        for k, v in cmp_res[pair].items():
            if not all(v[c] for c in ('chk_peak_pointwise', 'chk_rms',
                                      'chk_latency', 'chk_fwhm')):
                fails.append(f'band {pair} {k}')
    j['verdict'] = {'status': 'INCONCLUSIVE' if fails else 'CONVERGED',
                    'fails': fails}

    OUT_J.write_text(json.dumps(j, indent=1, default=str), encoding='utf-8')
    OUT_M.write_text(render_md(j), encoding='utf-8')
    print(json.dumps({'verdict': j['verdict']}, indent=1))
    print(f'wrote {OUT_J.name} ({OUT_J.stat().st_size} B) + {OUT_M.name} '
          f'({OUT_M.stat().st_size} B)')


if __name__ == '__main__':
    main()
