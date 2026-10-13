#!/usr/bin/env python3
"""Prepare and mechanically audit compact 3-read BVM 4x4 multiplier cases.

Run from any working directory after copying to <repo>/scripts/. Never edits the
canonical deck or devices, starts a solve automatically, or deletes files.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

PHI0 = 2.067833848e-15
SOURCE = Path('test/exploration/sfq_clock_two_read_v1/sfq_clock_timesteptest/deck.cir')
CASES = {'15x15': (15, 15), '11x13': (11, 13), '15x7': (15, 7)}
CLOCK_RE = re.compile(r'^\s*(V_TRIG_CLK_(?:D[0-6]|DFF))\s+(CLK_RAW_(?:D[0-6]|DFF))\s+0\s+PWL\([^\n]*\)\s*$', re.I)
INCLUDE_RE = re.compile(r'^(\s*\.include\s+)([^\s]+)(.*)$', re.I)
ACTUAL_OUTPUTS = [f'V(S_D{i}_OUT)' for i in range(7)] + ['V(DFF_O)']
CLOCK_OUTPUTS = [f'V(CLK_D{i})' for i in range(7)] + ['V(CLK_DFF)']


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def num(n: float) -> str:
    return f'{n:.6f}'.rstrip('0').rstrip('.') if abs(n - round(n)) > 1e-8 else str(round(n))


def pulse_points(times: list[float], value: str) -> list[tuple[float, str]]:
    points: list[tuple[float, str]] = []
    for t in times:
        points += [(t, '0'), (t+1, value), (t+10, value), (t+11, '0')]
    return points


def source_line(device: str, node: str, ps: list[tuple[float, str]], stop: float) -> str:
    v = [(0.0, '0'), *ps, (stop, '0')]
    if any(v[i][0] > v[i+1][0] for i in range(len(v)-1)):
        raise ValueError(f'Invalid PWL ordering for {device}')
    return f"{device} 0 {node} PWL(" + ' '.join(f'{num(t)}p {val}' for t, val in v) + ')'


def stimulus(a: int, b: int, reads: list[float], stop: float, write_start: float = 50) -> str:
    write = pulse_points([write_start], '400u')
    wl = write + pulse_points(reads, '400u')
    rows = ''.join(str((a >> i) & 1) for i in range(4))
    cols = ''.join(str((b >> (3-i)) & 1) for i in range(4))
    lines = [f'* FINAL VALIDATION: {a}x{b}, ROW_BITS={rows} (R1 LSB), COL_BITS={cols} (C1 MSB)',
             '* One WRITE1 for all 16 cells. No WRITE0/READ0 preconditioning. Three selected reads, no intervening writes.',
             '* During counted reads WL active on all rows; BL=0; SE cell-local and active only when row_bit AND col_bit is 1.',
             '* WRITE1: shared WL=+400u, shared BL=+400u, SE=0. SE during read=+100u.',
             f'* Reads start (ps): {", ".join(num(t) for t in reads)}; all amplitudes are SOURCE values, not individual branch current.']
    for i in range(1, 5):
        lines.append(source_line(f'I_WL_R{i}', f'WL_R{i}', wl, stop))
    for i in range(1, 5):
        lines.append(source_line(f'I_BL_C{i}', f'BL_C{i}', write, stop))
    for i in range(1, 5):
        for j in range(1, 5):
            active = rows[i-1] == '1' and cols[j-1] == '1'
            lines.append(source_line(f'I_SE_R{i}C{j}', f'SE_R{i}C{j}', pulse_points(reads, '100u') if active else [], stop))
    return '\n'.join(lines) + '\n'


def rewrite_deck(original: str, clocks: list[float], stop: float, probe: str,
                 source_dir: Path, dest: Path, root: Path) -> dict[str, str]:
    include_paths: dict[str, str] = {}
    clock_ids = []
    lines = []
    for orig_line in original.splitlines():
        stripped = orig_line.lstrip()
        if stripped.lower().startswith('.print '):
            continue
        if stripped.lower().startswith('.tran '):
            lines.append(f'.tran 0.01p {num(stop)}p')
            continue
        m = INCLUDE_RE.match(orig_line)
        if m:
            inc = m.group(2).strip('"\'')
            if inc == 'stimulus.inc':
                lines.append('.include stimulus.inc')
                continue
            source = (source_dir / inc).resolve()
            if not source.is_file() or not source.is_relative_to(root.resolve()):
                raise ValueError(f'Unsafe/missing source include: {inc} -> {source}')
            target_name = f'{len(include_paths)+1:02d}_{source.name}'
            target = dest / 'sources_snapshot' / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            if any(line.strip().lower().startswith('.include ') for line in data.decode('utf8').splitlines()):
                raise ValueError(f'Nested include in {source}; requires explicit flattening')
            target.write_bytes(data)
            include_paths[str(source.relative_to(root))] = str(target.relative_to(dest))
            lines.append(f'.include {target.relative_to(dest).as_posix()}')
            continue
        m = CLOCK_RE.match(orig_line)
        if m:
            device, node = m.groups()
            points = [(0.0, '0')]
            for t in clocks:
                points += [(t, '0'), (t+1, '1.2m'), (t+3, '1.2m'), (t+4, '0')]
            points.append((stop, '0'))
            lines.append(f'{device} {node} 0 PWL(' + ' '.join(f'{num(t)}p {v}' for t,v in points) + ')')
            clock_ids.append(device)
        else:
            lines.append(orig_line)
    expected_ids = {f'V_TRIG_CLK_D{i}' for i in range(7)} | {'V_TRIG_CLK_DFF'}
    if set(clock_ids) != expected_ids or len(clock_ids) != 8:
        raise ValueError(f'Expected exactly 8 clock sources, got {clock_ids}')
    if not any(x.startswith('.tran ') for x in lines):
        raise ValueError('Missing .tran')
    # At freeze time the D6 input must contain both the D6 diagonal and D5 carry buffered branches.
    active = [x for x in lines if x.strip() and not x.lstrip().startswith('*')]
    required = ['XCB_D6_L1 SJTL_OUT_D6_L1 T1_I_D6 CB',
                'XCB_CARRY_D6 CARRY_CB_IN_D6 T1_I_D6 CB']
    for x in required:
        if x not in active:
            raise ValueError(f'D6 FINAL topology invalid/missing: {x}')
    if any(x.startswith('XMERGE_D6 ') for x in active):
        raise ValueError('D6 MERGE remains active; expected CB+CB')
    lines.extend(['', '* Compact output-only physical evidence; absence of a signal is not a formal internal JJ-state verdict.'])
    names = ACTUAL_OUTPUTS + (CLOCK_OUTPUTS if probe == 'outputs_clocks' else [])
    lines.extend('.print ' + x for x in names)
    return {'deck': '\n'.join(lines)+'\n', 'includes':include_paths}


def get_head(repo: Path) -> str:
    p = subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True)
    return p.stdout.strip() if p.returncode == 0 else 'UNKNOWN'


def resolve_cases(case: str) -> list[tuple[str,int,int]]:
    keys = list(CASES) if case == 'all' else [case]
    return [(k, *CASES[k]) for k in keys]


def prepare(ns: argparse.Namespace) -> int:
    repo = ns.repo.resolve()
    source = repo / SOURCE
    if not source.is_file():
        raise ValueError(f'Missing frozen source deck: {source}')
    original = source.read_text(encoding='utf8')
    if ns.period_ps <= 11:
        raise ValueError('period must exceed 11ps read pulse and clock drive duration')
    if ns.first_read_ps < ns.write_start_ps + 11 + 1:
        raise ValueError('Not enough gap after write; initial BVM settlement is unverified')
    reads = [ns.first_read_ps + i * ns.period_ps for i in range(ns.rounds)]
    clocks = [x + ns.period_ps for x in reads]
    stop = ns.stop_ps if ns.stop_ps is not None else max(500.0, clocks[-1]+130.0)
    if stop <= clocks[-1]+30:
        raise ValueError('STOP must extend at least 30ps beyond final clock source start')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', ns.tag):
        raise ValueError('Tag must be simple ASCII letters, numbers, underscore or dash')
    base = (repo / ns.output).resolve()
    def display_path(path: Path) -> str:
        return str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)
    jobs = []
    for key,a,b in resolve_cases(ns.case):
        tag = f'{ns.tag}_{key}_T{num(ns.period_ps).replace(".","p")}ps'
        out = base/tag
        if out.exists():
            raise FileExistsError(f'Run folder exists: {out} (immutable, never overwrite)')
        jobs.append((key,a,b,out))
    if ns.command == 'plan':
        print(json.dumps({'status':'PLAN_ONLY','head':get_head(repo), 'source_deck':str(SOURCE),
            'cases':[{'a':a,'b':b,'path':display_path(out)} for key,a,b,out in jobs],
            'read_se_ps':reads,'clock_pwl_ps':clocks,'read_period_ps':ns.period_ps,
            'clock_source_offset_ps':ns.period_ps,'dt_ps':0.01,'stop_ps':stop,
            'probe':ns.probes, 'writes':'one 400u WL+BL pulse at start; no preconditioning',
            'no_simulation_run':True},ensure_ascii=False,indent=2))
        return 0
    for key,a,b,out in jobs:
        out.mkdir(parents=True)
        try:
            generated = rewrite_deck(original, clocks, stop, ns.probes, source.parent, out, repo)
            (out/'deck.cir').write_text(generated['deck'], encoding='utf8')
            (out/'stimulus.inc').write_text(stimulus(a,b,reads,stop,ns.write_start_ps),encoding='utf8')
            runner = '''#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -e raw.csv || -e run.log ]]; then
  echo "Refusing to overwrite immutable raw.csv or run.log" >&2; exit 2
fi
if [[ -n "${JOSIM_CLI:-}" ]]; then
  JOSIM="$JOSIM_CLI"
elif command -v josim-cli >/dev/null 2>&1; then
  JOSIM="$(command -v josim-cli)"
else
  echo "Set JOSIM_CLI=/path/to/josim-cli" >&2; exit 2
fi
"$JOSIM" -o raw.csv deck.cir 2>&1 | tee run.log
'''
            (out/'run_manual.sh').write_text(runner,encoding='utf8')
            (out/'run_manual.sh').chmod(0o755)
            manifest = {'schema':'BVM_FINAL_3READ_V1','source_commit':get_head(repo),
                'source_deck':str(SOURCE),'source_deck_sha256':sha(source),
                'topology':'7 T1; D6 diagonal CB + carry CB; independent BQ; DFF D7',
                'a':a,'b':b,'expected_product':a*b,'expected_binary':f'{a*b:08b}',
                'row_bits':''.join(str((a>>i)&1) for i in range(4)),
                'col_bits':''.join(str((b>>(3-i))&1) for i in range(4)),
                'n_rounds':ns.rounds,'period_ps':ns.period_ps,
                'clock_source_offset_ps':ns.period_ps,'read_se_starts_ps':reads,
                'clock_pwl_starts_ps':clocks,'write_start_ps':ns.write_start_ps,
                'simulation_stop_ps':stop,'dt_ps':0.01,'probes':ns.probes,
                'source_includes':generated['includes'],
                'sha256':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
            (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n', encoding='utf8')
        except Exception:
            # Never leave a misleading partial case pretending to be usable.
            import shutil
            shutil.rmtree(out)
            raise
        print(f'PREPARED {display_path(out)} | {a}x{b}={a*b}; SE={reads}; CLK_PWL={clocks}')
    print('No JoSIM solve, git operation, or upload performed.')
    return 0


def audit(ns: argparse.Namespace) -> int:
    case_dir = ns.case_dir.resolve()
    m = json.loads((case_dir/'manifest.json').read_text())
    for key,digest in m['sha256'].items():
        p = case_dir / key
        if not p.is_file() or sha(p) != digest:
            raise ValueError(f'Source snapshot SHA mismatch {p}')
    raw = case_dir/'raw.csv'
    if not raw.is_file():
        raise ValueError('raw.csv not present: run run_manual.sh yourself first')
    clk = m['clock_pwl_starts_ps']; stop = m['simulation_stop_ps']
    windows = list(zip(clk, [*clk[1:],stop]))
    areas = [[0.0]*8 for _ in windows]
    abs_areas = [[0.0]*8 for _ in windows]
    pre_area = [0.0]*8
    total_rows = 0
    last = None
    with raw.open(newline='',encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream,skipinitialspace=True)
        if reader.fieldnames is None: raise ValueError('Empty raw')
        missing = [x for x in ACTUAL_OUTPUTS if x not in reader.fieldnames]
        if missing: raise ValueError(f'Missing output-only probes: {missing}')
        for row in reader:
            t = float(row['time'])*1e12
            voltage = [float(row[name]) for name in ACTUAL_OUTPUTS]
            if last is not None:
                tprev,vprev = last
                if t <= tprev: raise ValueError('raw time grid non-increasing')
                mid=(t+tprev)/2
                dt_sec=(t-tprev)*1e-12
                vals=[(vprev[i]+voltage[i])*0.5*dt_sec/PHI0 for i in range(8)]
                if t > m['write_start_ps'] + 11 and mid < clk[0]:
                    for i,v in enumerate(vals): pre_area[i] += v
                for j,(a,b) in enumerate(windows):
                    if a <= mid < b:
                        for i,v in enumerate(vals):
                            areas[j][i] += v
                            abs_areas[j][i] += abs(v)
                        break
            last=(t,voltage)
            total_rows+=1
    if last is None or last[0] < clk[-1]+30:
        raise ValueError('Raw stops before enough post-final-clock observation')
    expected=m['expected_product']
    results=[]
    for j in range(len(windows)):
        decoded=0; ok=True; bits=[]
        for i in range(8):
            want=(expected>>i)&1; got=areas[j][i]
            within=abs(got-want)<=ns.area_tolerance
            # Reject cancellation that happens to net to the expected area.
            no_cancel=abs_areas[j][i] <= (1.6 if want else 0.5)
            passed=within and no_cancel
            if got>0.5:decoded|=1<<i
            ok &=passed
            bits.append({'bit':i,'want':want,'flux_phi0':round(got,5),
                         'abs_area_phi0':round(abs_areas[j][i],5),'pass':passed})
        results.append({'round':j+1,'window_ps':windows[j], 'decoded':decoded,
                        'expected':expected,'bits':bits,'pass':ok})
    pre_ok=all(abs(x)<=ns.area_tolerance for x in pre_area)
    output={'schema':'BVM_OUTPUT_ONLY_MECHANICAL_V1','source_commit':m['source_commit'],
        'raw_sha256':sha(raw),'raw_bytes':raw.stat().st_size,'rows':total_rows,
        'expected':expected,'all_rounds_pass':all(x['pass'] for x in results) and pre_ok,
        'preclock_flux_phi0':[round(x,5) for x in pre_area],'preclock_pass':pre_ok,
        'area_tolerance_phi0':ns.area_tolerance,'rounds':results,
        'limits':'Output-only integrated flux is a functional screen, not a JJ-phase / convergence / physical reliability certification.'}
    dest=case_dir/'output_qa.json'
    if dest.exists() and not ns.print_only:
        raise FileExistsError('output_qa.json exists; refuse to overwrite, use --print-only')
    if not ns.print_only:
        dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'case':str(case_dir),'pass':output['all_rounds_pass'],
        'decoded':[x['decoded'] for x in results], 'expected':expected,
        'area_phi0':[[round(v,3) for v in row] for row in areas],
        'preclock_pass':pre_ok,'raw_sha256':output['raw_sha256']},ensure_ascii=False,indent=2))
    return 0 if output['all_rounds_pass'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('plan','prepare'):
        p=sub.add_parser(name)
        p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
        p.add_argument('--case',choices=[*CASES,'all'],default='all')
        p.add_argument('--period-ps',type=float,default=70)
        p.add_argument('--rounds',type=int,default=3,choices=[3])
        p.add_argument('--first-read-ps',type=float,default=110)
        p.add_argument('--write-start-ps',type=float,default=50)
        p.add_argument('--stop-ps',type=float)
        p.add_argument('--probes',choices=['outputs','outputs_clocks'],default='outputs')
        p.add_argument('--tag',default='V0')
        p.add_argument('--output',type=Path,default=Path('test/exploration/sfq_clock_two_read_v1/final_validation_runs'))
    a=sub.add_parser('analyze')
    a.add_argument('case_dir',type=Path)
    a.add_argument('--area-tolerance',type=float,default=0.30)
    a.add_argument('--print-only',action='store_true')
    ns=parser.parse_args()
    if ns.command in ('plan','prepare'):
        if ns.rounds!=3: raise ValueError('Three rounds are required in V0')
        return prepare(ns)
    if ns.command=='analyze': return audit(ns)
    return 2
if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError,FileExistsError,RuntimeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);raise SystemExit(2)
