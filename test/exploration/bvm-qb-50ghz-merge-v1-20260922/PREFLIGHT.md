# BVM -> QB 50 GHz repeated-read and MERGE integration preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Identity

- Experiment: `bvm-qb-50ghz-merge-v1-20260922`
- Parent HEAD: `57241ff6d837b679b2cc2c2008991619fb56d429`
- Solver: `build/josim-cli`, `JoSIM v2.7.2837d13`
- Solver SHA256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- `DT=0.1p` for every authorized solve.
- No historical raw is modified or copied into this experiment.
- Preflight revision 2: candidate BVM/QB top decks use the existing U190
  `jtl2.cir` closure (`.subckt jtl`); the standalone MERGE fixture and Phase D
  use `circuits/standard/JTL.cir` (`.subckt THmitll_JTL`).

## Candidate closure

All three fan-in candidates use `JS1_AREA=0.90`, `JS2_AREA=0.90`,
`RSH_JS1=OPEN`, `RSH_JS2=OPEN`, the current U190-class BVM storage values,
and the following independent QB parameter groups:

| candidate | BVM JS area | QB LIN/BJS/L1/L2 | QB BJ1/RJ1 | QB BJ2/RJ2/L3/IB |
|---|---:|---|---|---|
| `QB_1X1` | 0.90 | 1.5p/4.0/1.4p/2.0p | 1.0/32 | 2.0/12/1.3p/260u |
| `QB_2X1` | 0.90 | 1.5p/4.0/1.4p/2.0p | 0.85/32 | 2.0/12/1.3p/260u |
| `QB_3X1` | 0.86 | 1.5p/4.0/1.4p/2.0p | 0.85/32 | 2.0/12/1.3p/260u |

The numerically equal QB values in `QB_2X1` and `QB_3X1` remain separate
parameter groups in provenance and are not treated as one candidate.

## Authorized solve matrix

### Phase A — repeated-read

One physical solve per listed mask, with one write/control/write sequence and
five final reads at `[110,121)`, `[130,141)`, `[150,161)`, `[170,181)`, and
`[190,201)` ps. Read start-to-start cadence is exactly 20 ps. The stop time is
240 ps. The final read is active only on the mask-selected BVM cells; the
existing write/control protocol is unchanged.

- `QB_1X1`: `0`, `1` (2 solves)
- `QB_2X1`: `00`, `01`, `10`, `11` (4 solves)
- `QB_3X1`: `000`, `001`, `010`, `011`, `100`, `101`, `110`, `111` (8 solves)

### Phase B — rewrite/read repeatability

One physical solve per sequence. Each state is created by the registered
negative WRITE0 reset followed by a positive WRITE1 only on target-one cells;
then a read is applied only to target-one cells. Pulse widths remain 11 ps,
with 1 ps ramps and the existing 9 ps plateau. No parameter optimization is
authorized.

- `QB_1X1`: `0 -> 1 -> 0 -> 1`
- `QB_2X1`: `00 -> 01 -> 11 -> 00 -> 01`
- `QB_3X1`: `000 -> 001 -> 011 -> 111 -> 000`

### Phase C — standalone MERGE collision characterization

Use only the current `circuits/standard/MERGE.cir`, with the standard-test
1.5 mV / 3 ohm / 0.5p injection fixture and one standard JTL load. Authorized
cases: A-only, B-only; all registered collision deltas 0, +/-0.5, +/-1,
 +/-2, +/-3, +/-4, +/-6 ps; same-input A/B doublets at 6 ps; 2+1 at offsets
0, 3, 6 ps; and 2+2 aligned plus skews 0.5, 1, 2, 3, 4 ps. There are 26
registered solves. `MERGET.cir` is prohibited.

### Phase D — conditional integration

Only if the Phase C direct-MERGE mechanical gate is PASS, run the seven
registered masks `0000`, `0001`, `0100`, `0011`, `0101`, `0111`, `1101`,
`1111` through two independent 2x1 branches and one MERGE. Pair mapping is
`b3b2 | b1b0 = (BVM1,BVM2) | (BVM3,BVM4)`. Phase D is not run after a
direct-MERGE gate failure.

## Registered mechanical metrics

- Raw time monotonicity, finite values, actual stored grid, sample count and
  SHA256 before/after analysis.
- Terminal positive-voltage response candidates: contiguous samples with
  `V(R_TERM) >= 0.1 mV`, split only when the actual time gap exceeds 0.5 ps.
  This is a registered navigation/mechanical locator, not an SFQ declaration.
- Terminal response windows for Phase A: `[read_start+15, read_start+45)` ps.
- Terminal signed/absolute actual-grid voltage area and peak are recorded.
- Same-JJ phase/voltage-area arithmetic is recorded for QB BJ1/BJ2 where the
  direct P/V columns are present; phase remains raw radians and turns are only
  `rad/(2*pi)` navigation values.
- Storage-state vectors use medians from registered post-read windows and
  report raw component deltas; no percentage threshold is invented.
- MERGE gate requires the registered response-candidate multiplicities and no
  extra candidate in the registered output window for every required case.

## Interpretation ceiling and stop rules

All result summaries state `scientific_interpretation = NOT_PERFORMED` and stop
at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`. A raw/artifact failure
stops the affected phase. A failed direct-MERGE gate stops Phase D. No timing
threshold, amplitude, BVM parameter, QB parameter, LS3/RS value or event
definition may be changed after a result is observed.

## Expected artifacts

Each solve has an immutable `raw.csv`, `actual_deck.cir`, `stimulus.inc`,
`metadata.json`, `run.log`, `source_manifest.json`, and `qa/raw_qa.json`.
Each run receives a standalone descriptive HTML plot. Phase summaries include
the exact run matrix, raw hashes, timing tables, count-gate navigation and
UNKNOWN fields. No physical conclusion is frozen by this preflight.
