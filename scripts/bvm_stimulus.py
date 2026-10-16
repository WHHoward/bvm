#!/usr/bin/env python3
"""Stimulus builders for the frozen two-read fixture and the V9 4x4 platform.

The legacy profile remains byte-compatible with the two-read fixture. The V9
profile generates 4 shared row-WL, 4 shared column-BL, 4 shared row-SE, and 8
complete clock PWL generators (D0-D6 and DFF). This module never runs JoSIM or
performs Git operations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

CHANNELS = tuple(f'D{i}' for i in range(7)) + ('DFF',)
OUTPUT_PROBES = tuple(f'V(S_D{i}_OUT)' for i in range(7)) + ('V(DFF_O)',)
CLOCK_PROBES = tuple(f'V(CLK_{c})' for c in CHANNELS)
INCLUDE = re.compile(r'^(\s*\.include\s+)([^\s]+)(\s*(?:\*.*)?)$', re.I)
CLK_LINE = re.compile(r'^\s*V_TRIG_CLK_(D[0-6]|DFF)\s+CLK_RAW_\1\s+0\s+PWL\s*\(.*\)\s*$', re.I)
TRAN = re.compile(r'^\s*\.tran\b[^\n]*$', re.I)
PRINT = re.compile(r'^\s*\.print\b', re.I)
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt(x: float) -> str:
    if abs(x-round(x)) < 1e-9:
        return str(round(x))
    return f'{x:.9f}'.rstrip('0').rstrip('.')


def pulse(events: list[float], amplitude: str, rise: float, hold: float, fall: float,
          end: float, label: str) -> str:
    """Create piecewise source with explicit return-to-zero; no adjacent overlap."""
    times = [(0., '0')]
    for s in events:
        if s < 0 or s + rise + hold + fall >= end:
            raise ValueError(f'{label}: pulse outside [0,stop]')
        times.extend([(s,'0'),(s+rise,amplitude),(s+rise+hold,amplitude),
                      (s+rise+hold+fall,'0')])
    for i in range(1,len(times)):
        if times[i][0] <= times[i-1][0]:
            raise ValueError(f'{label}: overlapping pulse or duplicate time near {fmt(times[i][0])}ps')
    times.append((end, '0'))
    return 'PWL(' + ' '.join(f'{fmt(t)}p {v}' if t else f'0 {v}' for t,v in times) + ')'


def parse_4bit(value: str) -> int:
    v = int(value, 0) if value.startswith(('0x','0b')) else int(value)
    if not 0 <= v <= 15: raise argparse.ArgumentTypeError('operands must be 0..15')
    return v


def parse_round_cases(value: str, rounds: int, read_times: list[float],
                      clock_times: list[float]) -> list[dict]:
    entries = [item.strip() for item in value.split(',')]
    if len(entries) != rounds:
        raise ValueError(f'ROUND_CASES has {len(entries)} entries, but ROUNDS={rounds}')
    cases = []
    for index, entry in enumerate(entries):
        pair = entry.split(':')
        if len(pair) != 2 or not all(part.strip() for part in pair):
            raise ValueError(f'invalid ROUND_CASES entry {index + 1}: {entry!r}; expected A:B')
        try:
            a, b = (parse_4bit(part.strip()) for part in pair)
        except (argparse.ArgumentTypeError, ValueError) as exc:
            raise ValueError(f'invalid ROUND_CASES entry {index + 1}: {entry!r}: {exc}') from exc
        product = a * b
        cases.append({
            'round': index + 1,
            'a': a,
            'b': b,
            'expected_product': product,
            'expected_bits_msb_first': format(product, '08b'),
            'expected_bits_d0_to_dff': ''.join(str((product >> bit) & 1) for bit in range(8)),
            'row_bits': ''.join(str((a >> bit) & 1) for bit in range(4)),
            'col_bits': ''.join(str((b >> (3-bit)) & 1) for bit in range(4)),
            'read_start_ps': read_times[index],
            'clock_pwl_start_ps': clock_times[index],
        })
    return cases


def params(ns):
    a,b = ns.a,ns.b
    T=ns.read_interval_ps
    clkT=ns.clock_period_ps if ns.clock_period_ps is not None else T
    delay=ns.se_clock_delay_ps if ns.se_clock_delay_ps is not None else T
    if any(not math.isfinite(v) for v in [T,clkT,delay,ns.first_read_ps,ns.write_start_ps,ns.dt_ps,ns.tail_ps]):
        raise ValueError('all times must be finite')
    if ns.rounds<1 or T<=0 or clkT<=0 or delay<0 or ns.dt_ps<=0 or ns.tail_ps<=0:
        raise ValueError('invalid rounds, intervals, delay, timestep or tail')
    if ns.first_read_ps <= ns.write_start_ps+11:
        raise ValueError('first read must start after WRITE1 pulse ends')
    if T <= 11 or clkT <= 4:
        raise ValueError('period too short to fit 11ps SE/WL or 4ps CLOCK pulse')
    reads=[ns.first_read_ps + n*T for n in range(ns.rounds)]
    clocks=[ns.first_read_ps + delay + n*clkT for n in range(ns.rounds)]
    if clocks[0] <= ns.write_start_ps+11:
        raise ValueError('clock overlaps WRITE1 initialization')
    stop=ns.stop_ps if ns.stop_ps is not None else math.ceil((max(reads[-1]+11,clocks[-1]+4)+ns.tail_ps)/10)*10
    if stop < max(reads[-1]+11,clocks[-1]+4)+ns.dt_ps:
        raise ValueError('STOP ends before last pulse has returned to zero')
    result = dict(a=a,b=b,expected=a*b,row_bits=''.join(str((a>>i)&1) for i in range(4)),
      col_bits=''.join(str((b>>(3-i))&1) for i in range(4)),rounds=ns.rounds,
      read_interval_ps=T,clock_period_ps=clkT,se_clock_delay_ps=delay,
      first_read_ps=ns.first_read_ps,write_start_ps=ns.write_start_ps,
      read_times_ps=reads,clock_times_ps=clocks,dt_ps=ns.dt_ps,stop_ps=stop,
      read_pulse_duration_ps=11,clock_pulse_duration_ps=4,
      warnings=(['clock_period_ps differs from read_interval_ps: clocks can no longer be assumed to correspond to same-numbered reads'] if abs(clkT-T)>1e-9 else []))
    if ns.round_cases:
        result['round_cases'] = parse_round_cases(ns.round_cases, ns.rounds, reads, clocks)
        result['pre_clock_window_ps'] = [0.0, clocks[0]]
        for i, case in enumerate(result['round_cases']):
            case['output_window_ps'] = [clocks[i], clocks[i+1] if i+1 < len(clocks) else stop]
        result['expected'] = result['round_cases'][0]['expected_product']
    return result


def make_stimulus(p):
    stop=p['stop_ps']; write=[p['write_start_ps']]; reads=p['read_times_ps']; clocks=p['clock_times_ps']
    cases=p.get('round_cases')
    lines=[
      '* GENERATED by bvm_stimulus.py. All voltage/current SIGNAL SOURCES are here.',
      '* SINGLE WRITE1 of all 16 cells; NO WRITE0, READ0, or inter-read writes.',
      ("* ROUND_CASES=" + '; '.join(f"R{c['round']}={c['a']}:{c['b']}->{c['expected_product']}" for c in cases)
       if cases else f"* operands A={p['a']} B={p['b']} expected={p['expected']}; row R1=LSB, col C1=MSB"),
      ("* Per-round ROW_BITS/COL_BITS are recorded in CASE_CONFIG.json; SE active iff both bits are 1"
       if cases else f"* ROW_BITS={p['row_bits']} COL_BITS={p['col_bits']}; SE active iff row bit AND col bit"),
      f"* reads={','.join(map(fmt,reads))}ps; clocks PWL start={','.join(map(fmt,clocks))}ps",
      '* Clock PWL start is NOT actual JJ CLK arrival time (DCSFQ2+JTL2 introduce delay).',
      '* WRITE1: all WL and BL +400u; no SE. READ: selected WL +400u, BL 0, selected SE +100u.',
    ]
    for row in range(1,5):
        if cases:
            row_reads=[reads[c['round']-1] for c in cases if (c['a']>>(row-1))&1]
        else:
            r_on=(p['a']>>(row-1))&1
            row_reads=reads if r_on else []
        events=write + row_reads
        lines.append(f'I_WL_R{row} 0 WL_R{row} '+pulse(events,'400u',1,9,1,stop,f'WL_R{row}'))
    for col in range(1,5):
        lines.append(f'I_BL_C{col} 0 BL_C{col} '+pulse(write,'400u',1,9,1,stop,f'BL_C{col}'))
    for row in range(1,5):
        for col in range(1,5):
            src=f'I_SE_R{row}C{col}'
            if cases:
                active_reads=[reads[c['round']-1] for c in cases
                              if ((c['a']>>(row-1))&1) and ((c['b']>>(4-col))&1)]
            else:
                active=bool(((p['a']>>(row-1))&1) and ((p['b']>>(4-col))&1))
                active_reads=reads if active else []
            lines.append(f'{src} 0 SE_R{row}C{col} '+pulse(active_reads,'100u',1,9,1,stop,src))
    for channel in CHANNELS:
        src=f'V_TRIG_CLK_{channel}'
        lines.append(f'{src} CLK_RAW_{channel} 0 '+pulse(clocks,'1.2m',1,2,1,stop,src))
    assert len(lines)==7+4+4+16+8
    return '\n'.join(lines)+'\n'


def _multi_amplitude_pwl(events: list[tuple[float, str]], rise: float, hold: float,
                         fall: float, end: float, label: str) -> str:
    """Render non-overlapping PWL pulses whose amplitudes may differ by event."""
    if any(not math.isfinite(value) for value in (rise, hold, fall, end)):
        raise ValueError(f'{label}: non-finite timing parameter')
    if rise <= 0 or hold <= 0 or fall <= 0 or end <= 0:
        raise ValueError(f'{label}: rise/hold/fall/stop must be positive')
    points: list[tuple[float, str]] = [(0.0, '0')]
    previous_end = -math.inf
    for start, amplitude in sorted(events, key=lambda item: item[0]):
        if not math.isfinite(start) or start < 0 or start + rise + hold + fall >= end:
            raise ValueError(f'{label}: pulse outside [0, stop]')
        if start <= previous_end:
            raise ValueError(f'{label}: overlapping PWL pulse near {fmt(start)} ps')
        points.extend(((start, '0'), (start + rise, amplitude),
                       (start + rise + hold, amplitude),
                       (start + rise + hold + fall, '0')))
        previous_end = start + rise + hold + fall
    points.sort(key=lambda item: item[0])
    for left, right in zip(points, points[1:]):
        if right[0] <= left[0]:
            raise ValueError(f'{label}: overlapping pulse or duplicate PWL time at {fmt(right[0])} ps')
    points.append((end, '0'))
    return 'PWL(' + ' '.join(
        f'{fmt(time)}p {value}' if time else f'0 {value}' for time, value in points
    ) + ')'


def make_v9_stimulus(p: dict) -> tuple[str, list[dict]]:
    """Generate V9 shared-row-SE / shared-column-BL stimulus sources.

    Expected keys: a, b, write_start_ps, read_times_ps, clock_times_ps,
    stop_ps, wl_write_amplitude, bl_write_amplitude, bl_read_amplitude,
    se_read_amplitude, io_rise_ps/io_hold_ps/io_fall_ps, and
    clock_rise_ps/clock_hold_ps/clock_fall_ps/clock_amplitude.
    """
    a, b = int(p['a']), int(p['b'])
    if not 0 <= a <= 15 or not 0 <= b <= 15:
        raise ValueError('V9 operands must be 0..15')
    reads = [float(value) for value in p['read_times_ps']]
    clocks = [float(value) for value in p['clock_times_ps']]
    if not reads or len(reads) != len(clocks):
        raise ValueError('V9 read and clock schedules must have the same nonzero length')
    if any(right <= left for left, right in zip(reads, reads[1:])):
        raise ValueError('V9 read starts must be strictly increasing')
    if any(right <= left for left, right in zip(clocks, clocks[1:])):
        raise ValueError('V9 clock starts must be strictly increasing')
    write_start = float(p['write_start_ps'])
    stop = float(p['stop_ps'])
    io_rise, io_hold, io_fall = (float(p[key]) for key in
                                  ('io_rise_ps', 'io_hold_ps', 'io_fall_ps'))
    clk_rise, clk_hold, clk_fall = (float(p[key]) for key in
                                     ('clock_rise_ps', 'clock_hold_ps', 'clock_fall_ps'))
    row_bits = ''.join(str((a >> bit) & 1) for bit in range(4))  # R1 is A's LSB.
    col_bits = ''.join(str((b >> (3 - bit)) & 1) for bit in range(4))  # C1 is B's MSB.
    lines = [
        '* GENERATED by scripts/bvm_stimulus.py; profile=V9_SHARED_ROW_SE_BL.',
        '* One WRITE1 initializes all 16 cells; there is no WRITE0, READ0, or re-write.',
        f'* A={a} B={b} product={a*b}; row R1=LSB, column C1=MSB.',
        f'* ROW_BITS={row_bits} COL_BITS={col_bits}; read starts={",".join(map(fmt, reads))} ps.',
        f'* Clock PWL starts={",".join(map(fmt, clocks))} ps; source start is not internal CLK arrival.',
        '* READ: all WL rows are quiet; selected BL columns and selected SE rows are driven together.',
    ]
    drivers: list[dict] = []

    def append_source(name: str, node: str, branch: str,
                      events: list[tuple[float, str]], rise: float, hold: float, fall: float,
                      cells: list[str]) -> None:
        lines.append(f'{name} 0 {node} ' +
                     _multi_amplitude_pwl(events, rise, hold, fall, stop, name))
        drivers.append({'source': name, 'node': node, 'branch': branch,
                        'cells': cells, 'pwl_pulse_count': len(events)})

    # WL is write-only; no active read pulses are generated on any row.
    for row in range(1, 5):
        append_source(f'I_WL_R{row}', f'WL_R{row}', 'WL',
                      [(write_start, p['wl_write_amplitude'])],
                      io_rise, io_hold, io_fall,
                      [f'R{row}C{col}' for col in range(1, 5)])

    # BL carries WRITE1 and selected-column read pulses.
    for col in range(1, 5):
        selected = (b >> (4 - col)) & 1
        events = [(write_start, p['bl_write_amplitude'])]
        if selected:
            events.extend((read, p['bl_read_amplitude']) for read in reads)
        append_source(f'I_BL_C{col}', f'BL_C{col}', 'BL', events,
                      io_rise, io_hold, io_fall,
                      [f'R{row}C{col}' for row in range(1, 5)])

    # Four shared row-SE buses are independently gated by A.
    for row in range(1, 5):
        selected = (a >> (row - 1)) & 1
        events = [(read, p['se_read_amplitude'] if selected else '0') for read in reads]
        append_source(f'I_SE_R{row}', f'SE_R{row}', 'SE', events,
                      io_rise, io_hold, io_fall,
                      [f'R{row}C{col}' for col in range(1, 5)])

    # Every T1/DFF receives an independent clock source with the same schedule.
    for channel in CHANNELS:
        events = [(clock, p['clock_amplitude']) for clock in clocks]
        lines.append(f'V_TRIG_CLK_{channel} CLK_RAW_{channel} 0 ' +
                     _multi_amplitude_pwl(events, clk_rise, clk_hold, clk_fall,
                                          stop, f'V_TRIG_CLK_{channel}'))
        drivers.append({'source': f'V_TRIG_CLK_{channel}', 'node': f'CLK_RAW_{channel}',
                        'branch': 'CLK', 'cells': [channel], 'pwl_pulse_count': len(events),
                        'direction': f'CLK_RAW_{channel} to clock shaper/receiver'})

    source_lines = [line for line in lines if re.match(r'^(?:I_|V_TRIG_CLK_)', line)]
    if len(source_lines) != 20:
        raise AssertionError(f'V9 stimulus must contain exactly 20 sources; got {len(source_lines)}')
    return '\n'.join(lines) + '\n', drivers


def get_topology(template: Path, dest: Path, probes: str):
    template=template.resolve();dest=dest.resolve()
    original=template.read_text(encoding='utf-8')
    if re.search(r'^\s*XMERGE_D6\s',original,re.M|re.I):
        raise ValueError('D6 MERGE is active; expected two-CB topology')
    for name in ('XCB_D6_L1','XCB_CARRY_D6'):
        if not re.search(r'^\s*'+name+r'\s',original,re.M|re.I):
            raise ValueError(f'D6 required CB instance missing: {name}')
    if len(re.findall(r'^\s*V_TRIG_CLK_',original,re.M|re.I))!=8:
        raise ValueError('template must contain exactly eight inline clock-source definitions')
    if len(re.findall(r'^\s*\.include\s+stimulus\.inc\s*$',original,re.M|re.I))!=1:
        raise ValueError('template must include stimulus.inc exactly once')
    srcs={};rewritten=[];foundclk=set();foundtran=0
    for line in original.splitlines():
        if (m:=CLK_LINE.fullmatch(line)):
            foundclk.add(m.group(1).upper());continue
        if line.lstrip().upper().startswith('V_TRIG_CLK_'):
            raise ValueError('unrecognized CLK source; refusing to rewrite: '+line[:160])
        if (m:=INCLUDE.match(line)):
            rel=m.group(2).strip('"\'');
            if rel.lower()=='stimulus.inc':
                rewritten.append('.include stimulus.inc');continue
            p=(template.parent / rel).resolve()
            if not p.is_file():raise FileNotFoundError(f'missing .include dependency {rel}, resolved {p}')
            n=f'{len(srcs):02d}_{p.name}'
            # Protect against an alias leading to two copies under different names.
            srcs[n]=p
            rewritten.append(f'.include sources_frozen/{n}');continue
        if TRAN.match(line):
            foundtran+=1;rewritten.append('.tran 0.01p 500p');continue
        if PRINT.match(line):
            continue # selected probes added below; no circuit topology change
        if line.lstrip().lower()=='.end':
            ps=OUTPUT_PROBES+(CLOCK_PROBES if probes=='outputs-clocks' else ())
            rewritten.extend('.print '+q for q in ps)
            rewritten.append(line);continue
        rewritten.append(line)
    if foundclk!=set(CHANNELS):raise ValueError(f'CLOCK source mismatch: {foundclk}')
    if foundtran!=1:raise ValueError('expected exactly one .tran')
    # Ensure original doesn't contain any other current or voltage source on CLK_RAW.
    tmp='\n'.join(rewritten)+'\n'
    for ch in CHANNELS:
        assert f'CLK_RAW_{ch}' in tmp
        assert not re.search(r'^\s*V_TRIG_CLK_'+ch+r'\b',tmp,re.M)
    dest.mkdir(parents=True,exist_ok=False)
    (dest/'sources_frozen').mkdir()
    manifest=[]
    for name,p in srcs.items():
        target=dest/'sources_frozen'/name
        shutil.copy2(p,target)
        manifest.append({'source_file':str(p),'snapshot':f'sources_frozen/{name}','sha256':SHA(target)})
    (dest/'deck.template.cir').write_text(tmp,encoding='utf-8')
    (dest/'SOURCE_MANIFEST.json').write_text(json.dumps({
        'original_deck':str(template),'original_deck_sha256':SHA(template),
        'deck_template_sha256':SHA(dest/'deck.template.cir'),
        'frozen_include_files':manifest,'probes':probes,'d6_topology':'two-CB'
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return len(srcs)


def atomic(path: Path, body: str):
    temp=path.with_name(path.name+'.writing')
    if temp.exists():raise ValueError('temporary output exists; investigate: '+str(temp))
    try:
        temp.write_text(body,encoding='utf-8')
        temp.replace(path)
    finally:
        if temp.exists():temp.unlink()


def apply(ns):
    dest=ns.dir.resolve()
    template=dest/'deck.template.cir'
    provenance=dest/'SOURCE_MANIFEST.json'
    if not template.is_file() or not provenance.is_file():
        raise ValueError('run init first; missing deck.template.cir or SOURCE_MANIFEST.json')
    meta=json.loads(provenance.read_text())
    if SHA(template)!=meta['deck_template_sha256']:
        raise ValueError('frozen netlist template changed; stop')
    for rec in meta['frozen_include_files']:
        if SHA(dest/rec['snapshot'])!=rec['sha256']:
            raise ValueError('frozen model SHA changed: '+rec['snapshot'])
    if (dest/'raw.csv').exists() or (dest/'data_tran.csv').exists():
        raise ValueError('raw already exists in this directory; create a NEW directory for a new run')
    p=params(ns)
    stim=make_stimulus(p)
    deck=re.sub(r'^\s*\.tran\b[^\n]*$',f".tran {fmt(p['dt_ps'])}p {fmt(p['stop_ps'])}p",
                template.read_text(encoding='utf-8'),flags=re.M|re.I)
    if deck.count('.tran ')!=1:raise ValueError('deck .tran update failed')
    for ch in CHANNELS:
        assert stim.count('V_TRIG_CLK_'+ch+' ')==1
    intended={'stimulus.inc':stim,'deck.cir':deck,
        'CASE_CONFIG.json':json.dumps(p,ensure_ascii=False,indent=2)+'\n'}
    if not ns.overwrite and any((dest/name).exists() for name in intended):
        raise ValueError('outputs already exist: use --overwrite ONLY if no solve has been run')
    # Archive previous text sources before replacement (tiny; not raw).
    for name in intended:
        target=dest/name
        if target.is_file() and target.read_text(encoding='utf-8')!=intended[name]:
            old_sha=SHA(target)[:12]
            backup=dest/f'{name}.previous-{old_sha}'
            if not backup.exists(): shutil.copy2(target,backup)
    for name,body in intended.items():atomic(dest/name,body)
    record={'deck_sha256':SHA(dest/'deck.cir'),'stimulus_sha256':SHA(dest/'stimulus.inc'),
            'template_sha256':meta['deck_template_sha256'],'expected':p['expected'],
            'expected_bits':format(p['expected'],'08b'),
            'run_clock_actual_arrival_requires_raw_check':True}
    if 'round_cases' in p:
        record['round_cases'] = p['round_cases']
        record['pre_clock_window_ps'] = p['pre_clock_window_ps']
        record['timing'] = {
            'write_start_ps': p['write_start_ps'],
            'read_interval_ps': p['read_interval_ps'],
            'clock_period_ps': p['clock_period_ps'],
            'se_clock_delay_ps': p['se_clock_delay_ps'],
            'read_times_ps': p['read_times_ps'],
            'clock_pwl_times_ps': p['clock_times_ps'],
            'dt_ps': p['dt_ps'],
            'stop_ps': p['stop_ps'],
        }
    atomic(dest/'RUN_MANIFEST.json',json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'generated':str(dest),'expected':p['expected'],'bits':record['expected_bits'],
      'read_ps':p['read_times_ps'],'clock_pwl_ps':p['clock_times_ps'],
      'read_period_ps':p['read_interval_ps'],'clock_period_ps':p['clock_period_ps'],
      'stop_ps':p['stop_ps'],'warnings':p['warnings']},ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    subs=ap.add_subparsers(dest='command',required=True)
    ini=subs.add_parser('init',help='snapshot a frozen deck/model hierarchy and move all 8 clock PWLs to stimulus.inc')
    ini.add_argument('--template',type=Path,required=True)
    ini.add_argument('--dir',type=Path,required=True)
    ini.add_argument('--probes',choices=['outputs','outputs-clocks'],default='outputs')
    s=subs.add_parser('set',help='generate ONE stimulus.inc for WL/BL/SE/CLOCK and adjusted simulation stop')
    s.add_argument('--dir',type=Path,required=True)
    s.add_argument('--a',type=parse_4bit,required=True,help='A 0..15; ROW_BITS R1=LSB')
    s.add_argument('--b',type=parse_4bit,required=True,help='B 0..15; COL_BITS C1=MSB')
    s.add_argument('--read-interval-ps',type=float,default=70,help='work/read interval; successive SE starts')
    s.add_argument('--clock-period-ps',type=float,help='successive clock-source starts; default read interval')
    s.add_argument('--se-clock-delay-ps',type=float,help='first clock PWL start minus first SE start; default read interval')
    s.add_argument('--rounds',type=int,default=3)
    s.add_argument('--round-cases',help='optional per-round A:B list, e.g. 15:7,0:0,0:0')
    s.add_argument('--write-start-ps',type=float,default=50)
    s.add_argument('--first-read-ps',type=float,default=110)
    s.add_argument('--dt-ps',type=float,default=0.01)
    s.add_argument('--stop-ps',type=float,help='optional simulation stop; default automatic')
    s.add_argument('--tail-ps',type=float,default=70)
    s.add_argument('--overwrite',action='store_true')
    ns=ap.parse_args()
    try:
        if ns.command=='init':
            n=get_topology(ns.template,ns.dir,ns.probes)
            print(f'INIT PASS: {ns.dir}; frozen {n} included source files; wrote deck.template.cir')
        else:apply(ns)
    except (ValueError,OSError,AssertionError) as e:
        ap.error(str(e))

if __name__=='__main__':main()
