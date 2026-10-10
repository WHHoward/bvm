#!/usr/bin/env bash
# Manual BVM 4x4 CARRY4 functional regression. No source edits; physical solves only in 'run' mode.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

mode="${1:-plan}"
PRESET='D3_PRE_CB_SJTL_2_ALL_200'
TAG='C4R28_210'
OUT="manual_batches/${TAG}"
BASELINE='runs/A045_MANUAL_CARRY4_15x15_210/deck.cir'
BASE_DECK_SHA='a88cf11f514e2b93fc56c676f2f1e8b9ba2fd3bdd2d04d2ee9f7990aeadf31a5'

# 28 new input pairs; three previously successful anchors are excluded: 15x15, 11x13, 3x3.
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
    --set 'SE_ENABLE_MASK=ALL'
    --set 'CARRY_POST_CB_SJTL_COUNT=0'
    --set 'CARRY_SJTL_POSITION=PRE_CB'
    --set 'CARRY_SJTL_STAGE_MASK=111111'
    --set 'CARRY_SJTL_COUNT_BY_STAGE=1,1,4,1,1,1'
    --set 'T1_CHAIN_CLOCK_MODE=GLOBAL_ONESHOT'
    --set 'T1_CHAIN_CLK_START=210p'
    --set 'SJTL_COUNT_D3=1,2,2,1'
    --set 'ROW_WL_WRITE_AMPLITUDE=400u'
    --set 'COL_BL_WRITE_AMPLITUDE=400u'
    --set 'ROW_WL_READ_AMPLITUDE=400u'
    --set 'COL_SE_READ_AMPLITUDE=100u'
    --set 'DT=0.01p' --set 'STOP=300p'
  )
}

# Prevent accidentally treating a previous failed/inconsistent run as a resumable PASS.
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
  python3 - "${paths[0]}" "$(row_bits "$a")" "$(col_bits "$b")" <<'PY'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1]); row, col = sys.argv[2:4]
try:
    result = json.loads((p/'result.json').read_text())
    qa = json.loads((p/'qa.json').read_text())
    env = dict(line.split('=', 1) for line in (p/'USER_CASE.snapshot.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
    raw = p/'raw.csv'
    assert result['artifact_status'] == 'VALID' and qa['status'] == 'PASS'
    assert result['qa_status'] == 'PASS' and raw.is_file()
    assert env['ROW_BITS'] == row and env['COL_BITS'] == col
    assert env['CARRY_SJTL_COUNT_BY_STAGE'] == '1,1,4,1,1,1'
    assert env['CARRY_SJTL_POSITION'] == 'PRE_CB' and env['T1_CHAIN_CLK_START'] == '210p'
    assert env['SJTL_COUNT_D3'] == '1,2,2,1'
    assert hashlib.sha256((p/'deck.cir').read_bytes()).hexdigest() == 'a88cf11f514e2b93fc56c676f2f1e8b9ba2fd3bdd2d04d2ee9f7990aeadf31a5'
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == result['raw_sha256']
except Exception as e:
    print(f'ERROR: existing {p} failed provenance/QA verification ({e}); stop without rerunning', file=sys.stderr)
    sys.exit(2)
print(p)
PY
}

if [[ "$mode" == 'plan' || "$mode" == 'status' ]]; then
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
  echo 'Usage: bash run_carry4_functional_28.sh plan|preflight|run|status' >&2; exit 2
fi
[[ -x './try.sh' ]] || { echo 'ERROR: put script in BVM experimental root beside try.sh' >&2; exit 2; }
[[ -f "$BASELINE" ]] || { echo "ERROR: missing A045 candidate deck: $BASELINE" >&2; exit 2; }
sha="$(sha256sum "$BASELINE" | awk '{print $1}')"
[[ "$sha" == "$BASE_DECK_SHA" ]] || { echo 'ERROR: A045 candidate deck identity differs; stop' >&2; exit 2; }
mkdir -p "$OUT"

# Re-render each candidate independently, before actual JoSIM invocation, and compare
# generated circuit topology SHA against immutable A045 reference. Input PWLs differ,
# but their topological deck should be byte-identical for this defined experiment.
check_deck() {
  local expected="$BASE_DECK_SHA"
  python3 - "$expected" "${ARGS[@]}" <<'PY'
import hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import diagonal_platform as dp
expected, *arg = sys.argv[1:]
preset = arg[arg.index('--preset')+1]
sets = [arg[i+1] for i in range(len(arg)-1) if arg[i] == '--set']
c, s, p = dp.load_config(preset, sets)
rendered = dp.render(c, s, p, dp.RUNS/'_PREVIEW_ONLY')
actual = hashlib.sha256(rendered['deck'].encode('utf-8')).hexdigest()
if actual != expected:
    raise SystemExit(f'ERROR: candidate deck differs from A045: {actual} != {expected}')
assert rendered['static_qa']['status'] == 'PASS'
print(f'DECK_IDENTITY_PASS {actual}')
PY
}

if [[ "$mode" == 'preflight' ]]; then
  rm -f "$OUT/preflight.ok"
  echo 'Preflighting all 28 cases; no transient JoSIM solve will run.'
  i=0
  for pair in "${PAIRS[@]}"; do
    read -r a b <<< "$pair"; i=$((i+1)); case_name="${TAG}_${a}x${b}"
    make_args "$a" "$b" "$case_name"
    echo "[$i/${#PAIRS[@]}] PREVIEW $case_name"
    ./try.sh "${ARGS[@]}" --dry-run > "$OUT/preflight_${case_name}.log" 2>&1 || { cat "$OUT/preflight_${case_name}.log"; exit 2; }
    grep -q 'DRY RUN PASS' "$OUT/preflight_${case_name}.log" || { echo "ERROR: preview did not confirm PASS: $case_name"; exit 2; }
    check_deck
  done
  printf '%s\t%s\n' "$(sha256sum "$0" | awk '{print $1}')" "$(git rev-parse HEAD)" > "$OUT/preflight.ok"
  echo "ALL PREFLIGHT PASS (${#PAIRS[@]} cases), no physics solved. Start with: bash $(basename "$0") run"
  exit 0
fi

[[ -f "$OUT/preflight.ok" ]] || { echo 'ERROR: run preflight first.' >&2; exit 2; }
IFS=$'\t' read -r locked_script locked_head < "$OUT/preflight.ok"
[[ "$locked_script" == "$(sha256sum "$0" | awk '{print $1}')" ]] || { echo 'ERROR: script changed since preflight.' >&2; exit 2; }
[[ "$locked_head" == "$(git rev-parse HEAD)" ]] || { echo 'ERROR: Git HEAD changed since preflight; rerun preflight.' >&2; exit 2; }

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
  # The pipeline propagates any JoSIM or QA failure (pipefail); no automatic reruns.
  ./try.sh "${ARGS[@]}" 2>&1 | tee "$OUT/run_${case_name}.log"
  verified="$(existing_run "$case_name" "$a" "$b")"
  [[ -n "$verified" ]] || { echo "ERROR: completed case lacks QA-passing run directory: $case_name" >&2; exit 2; }
  echo "PASS / ARCHIVE LOCALLY: $verified"
done
echo "ALL ${#PAIRS[@]} REGISTERED MANUAL CASES COMPLETE. No GitHub/Drive package uploaded automatically."
