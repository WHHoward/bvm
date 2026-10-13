#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$RUN_DIR/../../../../.." && pwd)"
REL_RUN_DIR="${RUN_DIR#"$REPO_ROOT"/}"
MODE="${1:-run}"

fail() { echo "ERROR: $*" >&2; exit 2; }
[[ $# -le 1 ]] || fail "usage: ./run.sh [--html|--html-only|--check]"
case "$MODE" in run|--html|--html-only|--check) ;; *) fail "unknown mode: $MODE" ;; esac

DECK="$RUN_DIR/deck.cir"
STIMULUS="$RUN_DIR/stimulus.inc"
RAW="$RUN_DIR/raw.csv"
LOG="$RUN_DIR/run.log"
RUN_MANIFEST="$RUN_DIR/RUN_MANIFEST.json"
SOURCE_MANIFEST="$RUN_DIR/SOURCE_MANIFEST.json"
CONFIG="$RUN_DIR/CASE_CONFIG.json"
PLOTTER="$REPO_ROOT/scripts/josim-plot2.py"

static_check() {
python3 - "$RUN_DIR" "$REPO_ROOT" <<'PY'
import hashlib, json, re, sys
from pathlib import Path
run=Path(sys.argv[1]); repo=Path(sys.argv[2])
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok, msg):
    if not ok: raise SystemExit("STATIC_QA_FAIL: "+msg)
sm=json.loads((run/'SOURCE_MANIFEST.json').read_text())
rm=json.loads((run/'RUN_MANIFEST.json').read_text())
cfg=json.loads((run/'CASE_CONFIG.json').read_text())
deck=(run/'deck.cir').read_text(); stim=(run/'stimulus.inc').read_text()
template=run/'deck.template.cir'
need(sha(template)==sm['deck_template_sha256']==rm['template_sha256'], 'deck template SHA')
need(sha(run/'deck.cir')==rm['deck_sha256'], 'deck SHA')
need(sha(run/'stimulus.inc')==rm['stimulus_sha256'], 'stimulus SHA')
for rec in sm['frozen_include_files']:
    p=run/rec['snapshot']
    need(p.is_file() and sha(p)==rec['sha256'], 'frozen source SHA: '+rec['snapshot'])
need(len(sm['frozen_include_files'])==11, 'expected 11 frozen include files')
tool_ids=rm.get('tool_provenance',{})
for key in ('stimulus_generator','output_area_screen_reference','classic_plotter','repo_build_solver'):
    rec=tool_ids.get(key)
    need(bool(rec and rec.get('path') and rec.get('sha256')), 'tool provenance: '+key)
    need(sha(repo/rec['path'])==rec['sha256'], 'tool SHA: '+rec['path'])
need(len(re.findall(r'^\s*XBVM_\S+\s+',deck,re.M))==16, 'expected 16 BVMs')
need(len(re.findall(r'^\s*XBQ_\S+\s+',deck,re.M))==16, 'expected 16 independent BQs')
need(len(re.findall(r'^\s*XT1_D[0-6]\s+',deck,re.M))==7, 'expected seven T1s')
need(len(re.findall(r'^\s*XDFF\s+',deck,re.M))==1, 'expected one DFF')
need(bool(re.search(r'^\s*XCB_D6_L1\s+SJTL_OUT_D6_L1\s+T1_I_D6\s+CB\s*$',deck,re.M)), 'D6 array CB')
need(bool(re.search(r'^\s*XCB_CARRY_D6\s+CARRY_CB_IN_D6\s+T1_I_D6\s+CB\s*$',deck,re.M)), 'D6 carry CB')
need(not re.search(r'^\s*XMERGE_D6\s',deck,re.M), 'D6 MERGE must be inactive')
need(not re.search(r'^\s*V_TRIG_CLK_',deck,re.M), 'duplicate inline clock source in deck')
need(len(re.findall(r'^\.include stimulus\.inc\s*$',deck,re.M))==1, 'stimulus include count')
counts=[len(re.findall(p,stim,re.M)) for p in (r'^I_WL_R\d\s',r'^I_BL_C\d\s',r'^I_SE_R\dC\d\s',r'^V_TRIG_CLK_(?:D[0-6]|DFF)\s')]
need(counts==[4,4,16,8], f'source counts {counts}, expected [4,4,16,8]')
need(sum(counts)==32, 'expected 32 total signal sources')
need(cfg.get('a')==15 and cfg.get('b')==15 and cfg.get('expected')==225, 'operand config')
need(cfg.get('read_times_ps')==[110.0,180.0,250.0], 'read times')
need(cfg.get('clock_times_ps')==[180.0,250.0,320.0], 'clock PWL times')
need(cfg.get('rounds')==3 and cfg.get('dt_ps')==0.01 and cfg.get('stop_ps')==400, 'round/dt/stop config')
need(re.search(r'^\.tran\s+0\.01p\s+400p\s*$',deck,re.M|re.I), '.tran configuration')
required=[f'V(S_D{i}_OUT)' for i in range(7)]+['V(DFF_O)']+[f'V(CLK_D{i})' for i in range(7)]+['V(CLK_DFF)']
prints=re.findall(r'^\.print\s+(.+?)\s*$',deck,re.M|re.I)
need(all(signal in prints for signal in required), 'required output/clock probes')
need(len(prints)==len(required) and len(set(prints))==len(prints), 'unexpected/duplicate .print probes')
sources=re.findall(r'^\s*(?:I_|V_TRIG_CLK_)\S+\s+',stim,re.M)
need(len(sources)==32, 'source declaration count')
def parse_pwl(name):
    matches=re.findall(r'^\s*'+re.escape(name)+r'\s+[^\n]*?PWL\(([^)]*)\)\s*$',stim,re.M|re.I)
    need(len(matches)==1, 'PWL source count: '+name)
    pairs=re.findall(r'(?<!\S)(0|(?:\d+(?:\.\d*)?|\.\d+)p)\s+([^\s)]+)',matches[0])
    return [(0.0 if t=='0' else float(t[:-1]),v) for t,v in pairs]
def expected_pwl(starts,amp,hold):
    points=[(0.0,'0')]
    for t in starts: points.extend([(t,'0'),(t+1,amp),(t+1+hold,amp),(t+2+hold,'0')])
    points.append((float(cfg['stop_ps']),'0'))
    return points
def check_pwl(name,starts,amp,hold):
    actual=parse_pwl(name); expected=expected_pwl(starts,amp,hold)
    need(len(actual)==len(expected) and all(abs(a[0]-e[0])<1e-9 and a[1].lower()==e[1].lower() for a,e in zip(actual,expected)), 'PWL waveform: '+name)
for row in range(1,5): check_pwl(f'I_WL_R{row}',[50.0,110.0,180.0,250.0],'400u',9)
for col in range(1,5): check_pwl(f'I_BL_C{col}',[50.0],'400u',9)
for row in range(1,5):
    for col in range(1,5): check_pwl(f'I_SE_R{row}C{col}',[110.0,180.0,250.0],'100u',9)
for channel in [*(f'D{i}' for i in range(7)),'DFF']:
    check_pwl(f'V_TRIG_CLK_{channel}',[180.0,250.0,320.0],'1.2m',2)
print('STATIC_QA_PASS: topology=16 BVM/16 BQ/7 T1/1 DFF; D6=CB+CB; MERGE_D6=inactive')
print('STATIC_QA_PASS: 4 WL + 4 BL + 16 SE + 8 CLK; read=110/180/250 ps; CLK PWL=180/250/320 ps')
print('STATIC_QA_PASS: outputs-clocks probes; DT=0.01 ps; STOP=400 ps; 11 frozen includes verified')
PY
}

source_tool_check() {
  [[ -f "$REPO_ROOT/scripts/bvm_stimulus.py" ]] || fail "missing stimulus generator"
  [[ -f "$PLOTTER" ]] || fail "missing classic plotter"
  [[ -f "$DECK" && -f "$STIMULUS" && -f "$CONFIG" && -f "$RUN_MANIFEST" ]] || fail "frozen run inputs missing"
  static_check
}

write_visual_qa() {
  python3 - "$RUN_DIR" "$REPO_ROOT" <<'PY'
import hashlib,json,sys
from pathlib import Path
run=Path(sys.argv[1]); repo=Path(sys.argv[2])
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rm=json.loads((run/'RUN_MANIFEST.json').read_text())
signals=[f'V(S_D{i}_OUT)' for i in range(7)]+['V(DFF_O)']
html=run/'res.html'
if not html.is_file() or html.stat().st_size==0: raise SystemExit('VISUAL_QA_FAIL: res.html missing/empty')
body=html.read_text(encoding='utf-8',errors='replace')
missing=[s for s in signals if s not in body]
if missing: raise SystemExit('VISUAL_QA_FAIL: HTML missing signals: '+', '.join(missing))
plotter=repo/'scripts/josim-plot2.py'
manifest={'schema':'josim-output-visualization-v1','raw_path':'raw.csv','raw_sha256':sha(run/'raw.csv'),
 'html_path':'res.html','html_sha256':sha(html),'renderer_path':'scripts/josim-plot2.py','renderer_sha256':sha(plotter),
 'argv':['python3','scripts/josim-plot2.py','raw.csv','-t','sep_comb','-c','dark','-j','2pi','-x','res.html','-s',*signals],
 'signals':signals,'scope':'eight final product outputs only','interpolation':False,'raw_mutated':False}
qa={'schema':'josim-output-visualization-qa-v1','status':'PASS','raw_sha256':sha(run/'raw.csv'),
 'html_sha256':sha(html),'html_bytes':html.stat().st_size,'renderer_sha256':sha(plotter),
 'all_registered_signals_present':True,'generated_html_in_package':False}
(run/'visualization_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(run/'visualization_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
print(f"VISUAL_QA_PASS: {html.stat().st_size} bytes; 8 output traces; raw SHA={qa['raw_sha256']}")
PY
}

make_plot() {
  [[ -f "$RAW" ]] || fail "raw.csv missing; --html-only never solves"
  [[ ! -e "$RUN_DIR/res.html" ]] || fail "res.html already exists; refusing overwrite"
  python3 "$PLOTTER" raw.csv -t sep_comb -c dark -j 2pi -x res.html -w "V0 15x15, 70 ps, final outputs" \
    -s "V(S_D0_OUT)" "V(S_D1_OUT)" "V(S_D2_OUT)" "V(S_D3_OUT)" \
       "V(S_D4_OUT)" "V(S_D5_OUT)" "V(S_D6_OUT)" "V(DFF_O)"
  write_visual_qa
}

audit_raw() {
  local action="$1"
  python3 - "$RUN_DIR" "$action" <<'PY'
import csv,hashlib,json,math,sys
from pathlib import Path
run=Path(sys.argv[1]); action=sys.argv[2]
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((run/'CASE_CONFIG.json').read_text())
rm=json.loads((run/'RUN_MANIFEST.json').read_text())
raw=run/'raw.csv'
if not raw.is_file() or raw.stat().st_size==0: raise SystemExit('RAW_QA_FAIL: raw.csv missing/empty')
raw_sha=sha(raw)
if rm.get('raw_sha256') and rm['raw_sha256']!=raw_sha: raise SystemExit('RAW_QA_FAIL: raw SHA differs from RUN_MANIFEST')
signals=[f'V(S_D{i}_OUT)' for i in range(7)]+['V(DFF_O)']
clock_signals=[f'V(CLK_D{i})' for i in range(7)]+['V(CLK_DFF)']
required=signals+clock_signals
times=[]; traces={s:[] for s in signals}; clocks={s:[] for s in clock_signals}
with raw.open(newline='',encoding='utf-8-sig') as f:
    reader=csv.DictReader(f,skipinitialspace=True)
    if reader.fieldnames is None: raise SystemExit('RAW_QA_FAIL: CSV header missing')
    missing=[s for s in required if s not in reader.fieldnames]
    if missing: raise SystemExit('RAW_QA_FAIL: required probes missing: '+', '.join(missing))
    for rownum,row in enumerate(reader,start=2):
        try: t=float(row['time'])*1e12
        except Exception as e: raise SystemExit(f'RAW_QA_FAIL: invalid time row {rownum}: {e}')
        if not math.isfinite(t) or (times and t<=times[-1]): raise SystemExit(f'RAW_QA_FAIL: nonfinite/nonmonotonic time row {rownum}')
        times.append(t)
        for s in signals+clock_signals:
            try: v=float(row[s])
            except Exception as e: raise SystemExit(f'RAW_QA_FAIL: invalid {s} row {rownum}: {e}')
            if not math.isfinite(v): raise SystemExit(f'RAW_QA_FAIL: nonfinite {s} row {rownum}')
            (traces if s in traces else clocks)[s].append(v)
if len(times)<2: raise SystemExit('RAW_QA_FAIL: fewer than 2 samples')
dt=[b-a for a,b in zip(times,times[1:])]
stop=float(cfg['stop_ps'])
if times[0]>1e-6 or times[-1] < stop-1e-6: raise SystemExit(f'RAW_QA_FAIL: time range [{times[0]},{times[-1]}] does not cover [0,{stop}] ps')
PHI0=2.067833848e-15
clock_starts=list(map(float,cfg['clock_times_ps']))
windows=[(clock_starts[i],clock_starts[i+1]) for i in range(len(clock_starts)-1)]+[(clock_starts[-1],stop)]
write_end=float(cfg['write_start_ps'])+11.0
area_tol=0.30
max_abs={0:0.5,1:1.6}
def areas_for_window(start,end):
    net={s:0.0 for s in signals}; absolute={s:0.0 for s in signals}
    for i,(t0,t1) in enumerate(zip(times,times[1:])):
        mid=(t0+t1)/2
        if start<=mid<end:
            dt_s=(t1-t0)*1e-12
            for s in signals:
                area=(traces[s][i]+traces[s][i+1])*0.5*dt_s/PHI0
                net[s]+=area; absolute[s]+=abs(area)
    return net,absolute
pre,pre_abs=areas_for_window(write_end,clock_starts[0])
pre_screen=all(abs(pre[s])<=area_tol and pre_abs[s]<=0.5 for s in signals)
rounds=[]; table=[]
expected=int(cfg['expected']); all_area_ok=pre_screen
for j,(a,b) in enumerate(windows,start=1):
    net,absolute=areas_for_window(a,b); bits=[]; area_ok=True
    for bit,s in enumerate(signals):
        want=(expected>>bit)&1; value=net[s]; abs_value=absolute[s]
        screen=(abs(value-want)<=area_tol and abs_value<=max_abs[want])
        status='PASS' if screen else 'FAIL'; area_ok &=screen
        bits.append({'bit_lsb0':bit,'signal':s,'expected_bit':want,'signed_area_over_phi0':value,
          'absolute_area_over_phi0':abs_value,'area_screen_status':status,
          'sfq_event_count':None,'sfq_event_count_status':'INCONCLUSIVE'})
        table.append((j,bit,s,want,value,abs_value,status,'INCONCLUSIVE'))
    rounds.append({'round':j,'window_ps_half_open':[a,b],'bits':bits,'area_screen_status':'PASS' if area_ok else 'FAIL'})
    all_area_ok &=area_ok
max_dt=max(dt); min_dt=min(dt)
output={'schema':'bvm-terminal-output-mechanical-qa-v1','artifact_status':'VALID','raw_sha256':raw_sha,
 'raw_bytes':raw.stat().st_size,'sample_count':len(times),'time_range_ps':[times[0],times[-1]],
 'actual_grid_ps':{'min_step':min_dt,'max_step':max_dt,'mean_step':sum(dt)/len(dt),'irregular_step_count':sum(abs(x-float(cfg['dt_ps']))>1e-7 for x in dt)},
 'required_probes_present':required,'window_rule':'adjacent-sample trapezoids use actual timestamps; each interval is assigned by midpoint to a half-open window; no interpolation',
 'phi0_wb':PHI0,'preclock_window_ps_half_open':[write_end,clock_starts[0]],
 'preclock_area_over_phi0':{s:pre[s] for s in signals},'preclock_absolute_area_over_phi0':{s:pre_abs[s] for s in signals},
 'preclock_area_screen_status':'PASS' if pre_screen else 'FAIL','area_tolerance_phi0':area_tol,
 'absolute_area_ceiling_phi0':{'expected_zero':max_abs[0],'expected_one':max_abs[1]},
 'rounds':rounds,'all_rounds_area_screen_status':'PASS' if all_area_ok else 'FAIL',
 'functional_verdict':'INCONCLUSIVE','sfq_event_count_status':'INCONCLUSIVE',
 'sfq_event_count_reason':'Only terminal output voltage and CLK probes are registered; terminal voltage-area screen is not an event counter.',
 'extra_sfq_status':'INCONCLUSIVE','late_output_observation_window_ps_half_open':windows[-1],
 'scientific_interpretation_performed':False,'solver_invocations_this_analysis':0,
 'limitations':['area screen is not a pulse/event count','no JJ phase/voltage event evidence at output stages','single dt; no convergence/sensitivity run']}
json_bytes=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
lines=['# Three-round per-bit output table','','`DERIVED` output voltage-area screen; Φ0-normalized terminal areas are not SFQ counts. Event count status is `INCONCLUSIVE`.','',
 '| round | window (ps) | bit | signal | expected | signed area / Φ0 | absolute area / Φ0 | area screen | SFQ event count |',
 '|---:|:---:|---:|---|---:|---:|---:|:---:|:---:|']
for r,bit,s,want,value,av,status,event in table:
    a,b=windows[r-1]
    lines.append(f'| {r} | [{a:g}, {b:g}) | {bit} | `{s}` | {want} | {value:.6f} | {av:.6f} | {status} | {event} |')
lines+=['','Area-screen thresholds are the pre-registered task-local rule: ±0.30 Φ0 from the expected bit, with absolute-area limits 0.5 Φ0 (expected 0) and 1.6 Φ0 (expected 1). `FAIL` is only a screen result, not a physical verdict.','']
table_bytes='\n'.join(lines)
if action=='write':
    if (run/'output_qa.json').exists() or (run/'THREE_ROUND_BIT_TABLE.md').exists(): raise SystemExit('REFUSING_TO_OVERWRITE: output QA already exists')
    (run/'output_qa.json').write_text(json_bytes)
    (run/'THREE_ROUND_BIT_TABLE.md').write_text(table_bytes)
elif action=='check':
    if not (run/'output_qa.json').is_file() or (run/'output_qa.json').read_text()!=json_bytes: raise SystemExit('QA_CHECK_FAIL: output_qa.json missing/stale')
    if not (run/'THREE_ROUND_BIT_TABLE.md').is_file() or (run/'THREE_ROUND_BIT_TABLE.md').read_text()!=table_bytes: raise SystemExit('QA_CHECK_FAIL: THREE_ROUND_BIT_TABLE.md missing/stale')
else: raise SystemExit('unknown audit mode')
print(f"RAW_QA_PASS: rows={len(times)} range={times[0]:.6f}..{times[-1]:.6f} ps raw_sha256={raw_sha}")
print('OUTPUT_AREA_SCREEN:',output['all_rounds_area_screen_status'],'; SFQ_EVENT_COUNT: INCONCLUSIVE; EXTRA_SFQ: INCONCLUSIVE')
PY
}

source_tool_check

if [[ "$MODE" == "run" || "$MODE" == "--html" ]]; then
  [[ ! -e "$RAW" && ! -e "$LOG" ]] || fail "raw.csv or run.log already exists; immutable run will not be overwritten"
  [[ ! -e "$RUN_DIR/output_qa.json" && ! -e "$RUN_DIR/THREE_ROUND_BIT_TABLE.md" ]] || fail "derived QA exists without raw; inspect the run directory"
  [[ ! -e "$RUN_DIR/res.html" ]] || fail "res.html already exists; refusing overwrite"
  [[ -z "$(git -C "$REPO_ROOT" status --porcelain --untracked-files=all -- "$REL_RUN_DIR")" ]] || fail "experiment scope is not clean; preserve artifacts and create a new attempt if needed"
  if [[ -n "${JOSIM_CLI:-}" ]]; then
    JOSIM="$JOSIM_CLI"
  elif [[ -x "$REPO_ROOT/build/josim-cli" ]]; then
    JOSIM="$REPO_ROOT/build/josim-cli"
  elif command -v josim-cli >/dev/null 2>&1; then
    JOSIM="$(command -v josim-cli)"
  else
    fail "josim-cli not found and repo build/josim-cli is unavailable"
  fi
  [[ -x "$JOSIM" ]] || fail "josim-cli not executable: $JOSIM"
  JOSIM="$(realpath "$JOSIM")"
  VERSION="$("$JOSIM" -v 2>&1)"
  SOLVER_SHA="$(sha256sum "$JOSIM" | awk '{print $1}')"
  STARTED="$(date --iso-8601=seconds)"
  START_EPOCH="$(date +%s)"
  printf 'run_id=V0_15x15_T70\nhead_before_run=%s\nsolver=%s\nsolver_sha256=%s\nsolver_version=%s\ncommand=%q -o raw.csv deck.cir\nstarted_at=%s\n' \
    "$(git -C "$REPO_ROOT" rev-parse HEAD)" "$JOSIM" "$SOLVER_SHA" "${VERSION//$'\n'/ | }" "$JOSIM" "$STARTED" > "$LOG"
  set +e
  "$JOSIM" -o raw.csv deck.cir 2>&1 | tee -a "$LOG"
  SOLVER_RC=${PIPESTATUS[0]}
  set -e
  ENDED="$(date --iso-8601=seconds)"
  ELAPSED="$(( $(date +%s) - START_EPOCH ))"
  printf '\nended_at=%s\nsolver_exit_code=%s\nelapsed_seconds=%s\n' "$ENDED" "$SOLVER_RC" "$ELAPSED" >> "$LOG"
  python3 - "$RUN_DIR" "$REPO_ROOT" "$JOSIM" "$SOLVER_SHA" "$VERSION" "$SOLVER_RC" "$STARTED" "$ENDED" "$ELAPSED" <<'PY'
import hashlib,json,sys
from pathlib import Path
run=Path(sys.argv[1]); repo=Path(sys.argv[2]); sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=run/'RUN_MANIFEST.json'; data=json.loads(p.read_text())
raw=run/'raw.csv'; log=run/'run.log'
data.update({'run_id':'V0_15x15_T70','execution_head':__import__('subprocess').check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
 'solver':{'path':sys.argv[3],'sha256':sys.argv[4],'version':sys.argv[5]},
 'command':{'argv':[sys.argv[3],'-o','raw.csv','deck.cir'],'exit_code':int(sys.argv[6])},
 'started_at':sys.argv[7],'ended_at':sys.argv[8],'elapsed_seconds':int(sys.argv[9]),
 'physical_solve_count':1,'scientific_interpretation_performed':False,'automatic_follow_up':False,
 'run_log_sha256':sha(log),'run_log_bytes':log.stat().st_size,
 'raw_sha256':sha(raw) if raw.is_file() else None,'raw_bytes':raw.stat().st_size if raw.is_file() else None})
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
PY
  if [[ "$SOLVER_RC" -ne 0 ]]; then echo "SOLVER_FAILURE: raw/log preserved; exit=$SOLVER_RC" >&2; exit "$SOLVER_RC"; fi
  [[ -s "$RAW" ]] || fail "solver exited zero but raw.csv is missing/empty"
  audit_raw write
  if [[ "$MODE" == "--html" ]]; then make_plot; fi
  exit 0
fi

if [[ "$MODE" == "--html-only" ]]; then
  [[ -s "$RAW" ]] || fail "raw.csv missing; no solver will be run by --html-only"
  audit_raw check
  make_plot
  exit 0
fi

if [[ "$MODE" == "--check" ]]; then
  [[ -s "$RAW" && -s "$LOG" ]] || fail "existing raw.csv/run.log required; no solver will be run by --check"
  [[ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["command"]["exit_code"])' "$RUN_MANIFEST")" == "0" ]] || fail "recorded solver exit code is not zero"
  audit_raw check
  if [[ -e "$RUN_DIR/res.html" ]]; then
    [[ -s "$RUN_DIR/visualization_manifest.json" && -s "$RUN_DIR/visualization_qa.json" ]] || fail "HTML exists without visualization manifests"
    python3 - "$RUN_DIR" "$REPO_ROOT" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]);repo=Path(sys.argv[2]);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((r/'visualization_manifest.json').read_text());q=json.loads((r/'visualization_qa.json').read_text())
assert m['raw_sha256']==sha(r/'raw.csv') and m['html_sha256']==sha(r/'res.html') and m['renderer_sha256']==sha(repo/'scripts/josim-plot2.py')
assert q['status']=='PASS' and q['raw_sha256']==sha(r/'raw.csv') and q['html_sha256']==sha(r/'res.html')
print('VISUAL_QA_PASS: raw/html/renderer SHA links consistent')
PY
  fi
  echo "CHECK_PASS: no JoSIM invocation; area screen reported separately from event count."
fi
