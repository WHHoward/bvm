#!/usr/bin/env python3
"""Step 0 (GPT audit): reproducible SFQ metric extraction for JoSIM CSVs.

Usage:
    python3 scripts/sfq_metrics.py <sim.csv> [<phase_col>,...] [--peaks I(L_SL|XBVM1),V(OUT_Q)]

Output (stdout, JSON):
    test_name, sim_version?, n_samples, t_start, t_end,
    per junction: net_delta_sfq, max_excursion_sfq, total_variation_sfq,
                  fast_events (|dP| > 0.3 SFQ between 0.1ps samples),
                  max_dPdt_sfq_per_ps
    peaks: {column: (peak_abs_value, t_peak)}

Metric definitions (freeze):
    - SFQ units: JoSIM prints P() as accumulated phase / (2*pi)  [Φ0 units]
    - net_delta_sfq   = P(t_end) - P(t_start)
    - max_excursion  = max|P(t) - P(t_start)|
    - total_variation = sum|P(i+1) - P(i)|
    - fast_events     = count of samples where |P(i+1) - P(i)| > 0.3 SFQ
                        (a 2pi slip within 0.1ps; genuine SFQ pulses qualify,
                         slow voltage-state slip does not)
    - max_dPdt        = max|P(i+1)-P(i)| / dt  [SFQ/ps]
"""
import csv, json, sys, hashlib, subprocess

FAST_EVENT_THRESHOLD = 0.3   # SFQ per sample (0.1 ps)

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def git_head():
    try:
        return subprocess.check_output(
            ['git', '-C', __file__ and '/home/howard/JoSIM', 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return 'unknown'

def analyze(csv_path, phase_cols, peak_cols=()):
    rows = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    if not rows:
        return {'error': 'empty csv'}
    n = len(rows)
    t0 = float(rows[0]['time'])
    t1 = float(rows[-1]['time'])
    dt = (t1 - t0) / (n - 1) if n > 1 else 0.0

    result = {
        'csv': csv_path,
        'sha256': file_sha256(csv_path),
        'git_head': git_head(),
        'n_samples': n,
        't_start_s': t0,
        't_end_s': t1,
        'dt_s': dt,
        'junctions': {},
        'peaks': {},
    }

    for c in phase_cols:
        p = [float(r[c]) for r in rows]
        net = p[-1] - p[0]
        exc = max(abs(v - p[0]) for v in p)
        tv = sum(abs(p[i+1] - p[i]) for i in range(n-1))
        fast = sum(1 for i in range(n-1) if abs(p[i+1] - p[i]) > FAST_EVENT_THRESHOLD)
        max_dpdt = max(abs(p[i+1] - p[i]) for i in range(n-1)) / (dt * 1e12) if dt > 0 else 0.0
        result['junctions'][c] = {
            'net_delta_sfq': round(net, 6),
            'max_excursion_sfq': round(exc, 6),
            'total_variation_sfq': round(tv, 6),
            'fast_events': fast,
            'max_dPdt_sfq_per_ps': round(max_dpdt, 4),
        }

    for c in peak_cols:
        if c not in rows[0]:
            continue
        best = max(rows, key=lambda r: abs(float(r[c])))
        result['peaks'][c] = {
            'peak_abs': float(best[c]),
            't_peak_s': float(best['time']),
        }
    return result

if __name__ == '__main__':
    path = sys.argv[1]
    phases = sys.argv[2].split(',') if len(sys.argv) > 2 else []
    peaks = []
    if '--peaks' in sys.argv:
        peaks = sys.argv[sys.argv.index('--peaks')+1].split(',')
    print(json.dumps(analyze(path, phases, peaks), indent=2))
