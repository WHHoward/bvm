#!/usr/bin/env bash
# Manual BVM 4x4 CARRY5 functional regression. No source edits; physical solves only in 'run' mode.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

mode="${1:-plan}"
PRESET='D3_PRE_CB_SJTL_2_ALL_200'
TAG='C5R28_210'
OUT="/tmp/josim_manual_batches/${TAG}"
DOCS="manual_batches/${TAG}"
BASE_RUN='runs/A077_MANUAL_CARRY5_15x15_210'
BASELINE="${BASE_RUN}/deck.cir"
BASE_RAW="${BASE_RUN}/raw.csv"
BASE_DECK_SHA='469247887bd0be999cc39acaad4277191e9aa426273b719615b9b5ddf0cd3a42'
BASE_RAW_SHA='e4477449666543784e978cc86e258aa48eee2fce4edcbd540ceb266a11a4c016'
CARRY_COUNTS='1,1,5,1,1,1'

# Preserve the C4R28 input order. Every input pair is a new solve in this batch.
PAIRS=(
  '15 14' '14 15' '14 14' '15 13' '13 15' '15 11' '11 15'
  '15 7'  '7 15'  '7 7'   '7 14'  '14 7'  '9 13'  '13 9'
  '5 10'  '10 5'  '1 1'   '1 15'  '15 1'  '2 15'  '15 2'
  '4 15'  '15 4'  '8 15'  '15 8'  '0 0'   '0 15'  '15 0'
)

row_bits() { local n="$1"; printf '%d%d%d%d' "$(( (n >> 0) & 1 ))" "$(( (n >> 1) & 1 ))" "$(( (n >> 2) & 1 ))" "$(( (n >> 3) & 1 ))"; }
col_bits() { local n="$1"; printf '%d%d%d%d' "$(( (n >> 3) & 1 ))" "$(( (n >> 2) & 1 ))" "$(( (n >> 1) & 1 ))" "$(( (n >> 0) & 1 ))"; }

make_args() {
  local a="$1" b="$2" case_name="$3"
  ARGS=(
    --preset "$PRESET"
    --set "CASE=$case_name"
    --set "ROW_BITS=$(row_bits "$a")"
    --set "COL_BITS=$(col_bits "$b")"
    --set 'DRIVE_MODE=SHARED'
    --set 'SE_TOPOLOGY=CELL'
    --set 'SE_GATE_MODE=CROSSPOINT'
    --set 'OUTPUT_MODE=DIAGONAL_T1_CHAIN'
    --set 'T1_MODE=CHAIN'
    --set 'T1_CLK_MODE=PULSE'
    --set 'CBU_CHAIN_TOPOLOGY=CB_CARRY_BUFFER_ALL'
    --set 'CBU_MODE=PHYSICAL_TWO_INPUT'
    --set 'CBU_OVERRIDE_D1=NONE'
    --set 'CARRY_MODE=RIPPLE'
    --set 'CARRY_POST_CB_SJTL_COUNT=0'
    --set 'CARRY_SJTL_POSITION=PRE_CB'
    --set 'CARRY_SJTL_STAGE_MASK=111111'
    --set "CARRY_SJTL_COUNT_BY_STAGE=${CARRY_COUNTS}"
    --set 'T1_CHAIN_CLOCK_MODE=GLOBAL_ONESHOT'
    --set 'T1_CHAIN_CLK_START=210p'
    --set 'ROW_WL_WRITE_AMPLITUDE=400u'
    --set 'COL_BL_WRITE_AMPLITUDE=400u'
    --set 'ROW_WL_READ_AMPLITUDE=400u'
    --set 'COL_SE_READ_AMPLITUDE=100u'
    --set 'SE_ENABLE_MASK=ALL'
    --set 'SJTL_COUNT_D3=1,2,2,1'
    --set 'FOCUS_DIAGONAL=D3'
    --set 'DT=0.01p' --set 'STOP=300p'
    --set 'PROBE_PROFILE=t1_chain_focus' --set 'FOCUS_STAGE=D3'
  )
}

# A case is resumable only if its complete raw/config/topology/plot QA is intact.
existing_run() {
  local case_name="$1" a="$2" b="$3"
  local paths=(runs/A[0-9][0-9][0-9]_"$case_name")
  if (( ${#paths[@]} == 0 )) || [[ ! -d "${paths[0]}" ]]; then
    printf '%s' ''
    return 0
  fi
  if (( ${#paths[@]} != 1 )); then
    echo "ERROR: multiple run directories for $case_name" >&2; return 2
  fi
  python3 - "${paths[0]}" "$(row_bits "$a")" "$(col_bits "$b")" "$BASE_DECK_SHA" "$CARRY_COUNTS" <<'PY'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1]); row, col, deck_sha, carry_counts = sys.argv[2:]
try:
    result = json.loads((p/'result.json').read_text())
    qa = json.loads((p/'qa.json').read_text())
    raw_qa = json.loads((p/'raw_qa.json').read_text())
    static_qa = json.loads((p/'static_qa.json').read_text())
    chain_qa = json.loads((p/'chain_qa.json').read_text())
    plot_qa = json.loads((p/'plot_qa.json').read_text())
    source = json.loads((p/'source_manifest.json').read_text())
    env = dict(line.split('=', 1) for line in (p/'USER_CASE.snapshot.env').read_text().splitlines()
               if '=' in line and not line.startswith('#'))
    raw = p/'raw.csv'; deck = p/'deck.cir'
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    assert result['artifact_status'] == 'VALID' and result['physical_solve_count'] == 1
    assert result['solver_exit_code'] == 0 and result['qa_status'] == 'PASS'
    assert qa['status'] == 'PASS' and raw_qa['status'] == 'PASS'
    assert static_qa['status'] == 'PASS' and chain_qa['status'] == 'PASS' and plot_qa['status'] == 'PASS'
    assert digest == result['raw_sha256'] == qa['raw_sha256_before_analysis'] == qa['raw_sha256_after_analysis']
    assert digest == raw_qa['raw_sha256_before'] == raw_qa['raw_sha256_after_analysis']
    assert result['raw_bytes'] == raw.stat().st_size
    assert hashlib.sha256(deck.read_bytes()).hexdigest() == result['deck_sha256'] == deck_sha
    assert env['ROW_BITS'] == row and env['COL_BITS'] == col
    assert env['DRIVE_MODE'] == 'SHARED' and env['SE_TOPOLOGY'] == 'CELL'
    assert env['SE_GATE_MODE'] == 'CROSSPOINT' and env['SE_ENABLE_MASK'] == 'ALL'
    assert env['OUTPUT_MODE'] == 'DIAGONAL_T1_CHAIN' and env['T1_MODE'] == 'CHAIN'
    assert env['T1_CLK_MODE'] == 'PULSE'
    assert env['CBU_CHAIN_TOPOLOGY'] == 'CB_CARRY_BUFFER_ALL' and env['CBU_MODE'] == 'PHYSICAL_TWO_INPUT'
    assert env['CBU_OVERRIDE_D1'] == 'NONE' and env['CARRY_MODE'] == 'RIPPLE'
    assert env['CARRY_SJTL_COUNT_BY_STAGE'] == carry_counts
    assert env['CARRY_SJTL_POSITION'] == 'PRE_CB' and env['CARRY_SJTL_STAGE_MASK'] == '111111'
    assert env['CARRY_POST_CB_SJTL_COUNT'] == '0'
    assert env['T1_CHAIN_CLOCK_MODE'] == 'GLOBAL_ONESHOT' and env['T1_CHAIN_CLK_START'] == '210p'
    assert env['SJTL_COUNT_D3'] == '1,2,2,1'
    assert env['DT'] == '0.01p' and env['STOP'] == '300p'
    assert env['ROW_WL_WRITE_AMPLITUDE'] == '400u' and env['COL_BL_WRITE_AMPLITUDE'] == '400u'
    assert env['ROW_WL_READ_AMPLITUDE'] == '400u' and env['COL_SE_READ_AMPLITUDE'] == '100u'
    assert env['FOCUS_DIAGONAL'] == 'D3'
    assert env['PROBE_PROFILE'] == 't1_chain_focus' and env['FOCUS_STAGE'] == 'D3'
    assert source['canonical_sources_modified'] is False
except Exception as e:
    print(f'ERROR: existing {p} failed strict provenance/QA verification ({e}); stop without rerunning', file=sys.stderr)
    sys.exit(2)
print(p)
PY
}

if [[ "$mode" == 'plan' || "$mode" == 'status' ]]; then
  printf 'BATCH=%s | BASE=%s | CARRY_SJTL_COUNT_BY_STAGE=%s | CLK=210p | DT=0.01p | STOP=300p\n' "$TAG" "$BASE_RUN" "$CARRY_COUNTS"
  printf '%-5s %-7s %-8s %-8s %-8s %s\n' 'No.' 'A x B' 'ROW_BITS' 'COL_BITS' 'EXPECTED' 'Run case / status'
  i=0
  for pair in "${PAIRS[@]}"; do
    read -r a b <<< "$pair"; i=$((i+1))
    case_name="${TAG}_${a}x${b}"
    if [[ "$mode" == 'status' ]]; then
      path="$(existing_run "$case_name" "$a" "$b")"
      status="${path:-PENDING}"
    else status="$case_name"; fi
    printf '%-5s %-7s %-8s %-8s %-8s %s\n' "$i" "${a}x${b}" "$(row_bits "$a")" "$(col_bits "$b")" "$((a*b))" "$status"
  done
  exit 0
fi

if [[ "$mode" != 'preflight' && "$mode" != 'run' ]]; then
  echo 'Usage: bash run_carry5_functional_28.sh plan|preflight|run|status' >&2; exit 2
fi
[[ -x './try.sh' ]] || { echo 'ERROR: put script in BVM experimental root beside try.sh' >&2; exit 2; }
[[ -f "$BASELINE" && -f "$BASE_RAW" ]] || { echo 'ERROR: missing A077 baseline deck/raw' >&2; exit 2; }
sha="$(sha256sum "$BASELINE" | awk '{print $1}')"
[[ "$sha" == "$BASE_DECK_SHA" ]] || { echo 'ERROR: A077 candidate deck identity differs; stop' >&2; exit 2; }
raw_sha="$(sha256sum "$BASE_RAW" | awk '{print $1}')"
[[ "$raw_sha" == "$BASE_RAW_SHA" ]] || { echo 'ERROR: A077 immutable raw identity differs; stop' >&2; exit 2; }
python3 - "$BASE_RUN" "$BASE_RAW_SHA" "$BASE_DECK_SHA" <<'PY'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1]); raw_sha, deck_sha = sys.argv[2:]
result = json.loads((p/'result.json').read_text()); qa = json.loads((p/'qa.json').read_text())
assert result['artifact_status'] == 'VALID' and result['qa_status'] == 'PASS'
assert result['raw_sha256'] == raw_sha and result['deck_sha256'] == deck_sha
assert qa['status'] == 'PASS' and qa['raw_sha256_before_analysis'] == raw_sha == qa['raw_sha256_after_analysis']
assert hashlib.sha256((p/'raw.csv').read_bytes()).hexdigest() == raw_sha
assert hashlib.sha256((p/'deck.cir').read_bytes()).hexdigest() == deck_sha
print('A077_BASE_IDENTITY_PASS')
PY
mkdir -p "$OUT"

check_deck() {
  python3 - "$BASE_DECK_SHA" "${ARGS[@]}" <<'PY'
import hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import diagonal_platform as dp
expected, *arg = sys.argv[1:]
preset = arg[arg.index('--preset')+1]
sets = [arg[i+1] for i in range(len(arg)-1) if arg[i] == '--set']
case, stimulus, params = dp.load_config(preset, sets)

def read_env(path):
    return {line.split('=', 1)[0]: line.split('=', 1)[1]
            for line in Path(path).read_text().splitlines()
            if '=' in line and not line.lstrip().startswith('#')}

baseline = Path('runs/A077_MANUAL_CARRY5_15x15_210')
baseline_case = read_env(baseline/'USER_CASE.snapshot.env')
allowed_input_changes = {'CASE', 'ROW_BITS', 'COL_BITS'}
if set(case) != set(baseline_case):
    raise SystemExit('ERROR: effective case schema differs from A077')
for key, value in baseline_case.items():
    if key not in allowed_input_changes and case.get(key) != value:
        raise SystemExit(f'ERROR: parameter drift from A077: {key}={case.get(key)!r} != {value!r}')
if stimulus != read_env(baseline/'STIMULUS.snapshot.env'):
    raise SystemExit('ERROR: stimulus configuration differs from A077')
baseline_params = {}
for filename in ('T1_PARAMS.snapshot.env', 'CBU_PARAMS.snapshot.env',
                 'DFF_PARAMS.snapshot.env', 'D0_JTL_PARAMS.snapshot.env'):
    baseline_params.update(read_env(baseline/filename))
if params != baseline_params:
    raise SystemExit('ERROR: T1/CBU/DFF/D0-JTL parameters differ from A077')

required = {
    'OUTPUT_MODE': 'DIAGONAL_T1_CHAIN', 'T1_MODE': 'CHAIN', 'T1_CLK_MODE': 'PULSE',
    'CBU_CHAIN_TOPOLOGY': 'CB_CARRY_BUFFER_ALL', 'CBU_OVERRIDE_D1': 'NONE',
    'CARRY_POST_CB_SJTL_COUNT': '0', 'CARRY_SJTL_POSITION': 'PRE_CB',
    'CARRY_SJTL_STAGE_MASK': '111111', 'CARRY_SJTL_COUNT_BY_STAGE': '1,1,5,1,1,1',
    'T1_CHAIN_CLOCK_MODE': 'GLOBAL_ONESHOT', 'T1_CHAIN_CLK_START': '210p',
    'ROW_WL_WRITE_AMPLITUDE': '400u', 'COL_BL_WRITE_AMPLITUDE': '400u',
    'ROW_WL_READ_AMPLITUDE': '400u', 'COL_SE_READ_AMPLITUDE': '100u',
    'SE_ENABLE_MASK': 'ALL', 'SJTL_COUNT_D3': '1,2,2,1',
    'DT': '0.01p', 'STOP': '300p', 'PROBE_PROFILE': 't1_chain_focus', 'FOCUS_STAGE': 'D3',
}
for key, value in required.items():
    if case.get(key) != value:
        raise SystemExit(f'ERROR: effective {key}={case.get(key)!r}, expected {value!r}')
rendered = dp.render(case, stimulus, params, dp.RUNS/'_PREVIEW_ONLY')
actual = hashlib.sha256(rendered['deck'].encode('utf-8')).hexdigest()
if actual != expected:
    raise SystemExit(f'ERROR: candidate deck differs from A077: {actual} != {expected}')
if rendered['static_qa']['status'] != 'PASS':
    raise SystemExit('ERROR: rendered static QA did not PASS')
print(f'DECK_IDENTITY_PASS {actual}')
PY
}

if [[ "$mode" == 'preflight' ]]; then
  if [[ -e "$OUT/preflight.ok" ]]; then
    echo "ERROR: preflight lock already exists; refusing to overwrite $OUT/preflight.ok" >&2; exit 2
  fi
  for old in "$OUT"/preflight_*.log "$OUT"/deck_*.log; do
    if [[ -e "$old" ]]; then
      echo "ERROR: prior preflight evidence exists; refusing to overwrite $old" >&2; exit 2
    fi
  done
  echo 'Preflighting all 28 C5 cases; no transient JoSIM solve will run.'
  i=0
  for pair in "${PAIRS[@]}"; do
    read -r a b <<< "$pair"; i=$((i+1)); case_name="${TAG}_${a}x${b}"
    make_args "$a" "$b" "$case_name"
    echo "[$i/${#PAIRS[@]}] PREVIEW $case_name"
    ./try.sh "${ARGS[@]}" --dry-run > "$OUT/preflight_${case_name}.log" 2>&1 || { cat "$OUT/preflight_${case_name}.log"; exit 2; }
    grep -q 'DRY RUN PASS' "$OUT/preflight_${case_name}.log" || { echo "ERROR: preview did not confirm PASS: $case_name"; exit 2; }
    check_deck > "$OUT/deck_${case_name}.log" 2>&1 || { cat "$OUT/deck_${case_name}.log"; exit 2; }
    grep -q "DECK_IDENTITY_PASS $BASE_DECK_SHA" "$OUT/deck_${case_name}.log" || { echo "ERROR: A077 deck identity mismatch: $case_name"; exit 2; }
  done
  printf '%s\t%s\t%s\t%s\n' \
    "$(sha256sum "$0" | awk '{print $1}')" \
    "$(git rev-parse HEAD)" \
    "$(sha256sum "$DOCS/experiment.yaml" | awk '{print $1}')" \
    "$(sha256sum "$DOCS/PREFLIGHT.md" | awk '{print $1}')" > "$OUT/preflight.ok"
  echo "ALL ${#PAIRS[@]} PREFLIGHT PASS; physical_solve_count=0. Run only after this lock is created."
  exit 0
fi

[[ -f "$OUT/preflight.ok" ]] || { echo 'ERROR: run preflight first.' >&2; exit 2; }
IFS=$'\t' read -r locked_script locked_head locked_experiment locked_preflight < "$OUT/preflight.ok"
[[ "$locked_script" == "$(sha256sum "$0" | awk '{print $1}')" ]] || { echo 'ERROR: script changed since preflight.' >&2; exit 2; }
[[ "$locked_head" == "$(git rev-parse HEAD)" ]] || { echo 'ERROR: Git HEAD changed since preflight; stop without solving.' >&2; exit 2; }
[[ "$locked_experiment" == "$(sha256sum "$DOCS/experiment.yaml" | awk '{print $1}')" ]] || { echo 'ERROR: experiment.yaml changed since preflight.' >&2; exit 2; }
[[ "$locked_preflight" == "$(sha256sum "$DOCS/PREFLIGHT.md" | awk '{print $1}')" ]] || { echo 'ERROR: PREFLIGHT.md changed since preflight.' >&2; exit 2; }

i=0
for pair in "${PAIRS[@]}"; do
  read -r a b <<< "$pair"; i=$((i+1)); case_name="${TAG}_${a}x${b}"
  prior="$(existing_run "$case_name" "$a" "$b")"
  if [[ -n "$prior" ]]; then
    echo "[$i/${#PAIRS[@]}] VERIFIED EXISTING -> SKIP: $prior"
    continue
  fi
  make_args "$a" "$b" "$case_name"
  echo "[$i/${#PAIRS[@]}] SOLVE $case_name ($a x $b = $((a*b)))"
  ./try.sh "${ARGS[@]}" 2>&1 | tee "$OUT/run_${case_name}.log"
  verified="$(existing_run "$case_name" "$a" "$b")"
  [[ -n "$verified" ]] || { echo "ERROR: completed case lacks strict QA-passing run directory: $case_name" >&2; exit 2; }
  echo "PASS / RAW PRESERVED: $verified"
done
echo "ALL ${#PAIRS[@]} C5R28 CASES COMPLETE. No analysis/Drive upload/package was performed by this runner."
