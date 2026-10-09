# T1 seven-stage ripple chain + global synchronous clock — preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Frozen identity and gate

- Work unit: `bvm-4x4-t1-chain-global-20261009`; risk `NORMAL`.
- Registered parent/source HEAD: `3a4636bdb1fd843a1bd217f3406bd7d259a47bea`.
- Historical base HEAD: `64b4e18e2d944fd982f5b200490f7b7575339b46`.
- Static QA: `STATIC_QA.json`, SHA-256 `8046f0b672db77aec8a20655d56801f531a3c456de8534984a879c2a2e50c819`.
- Exact per-run probe registry: `PROBE_MANIFEST.json`, 238 signals/run, SHA-256
  `2b2fa654c1ba25cfa1830ad5ae0c1ca37f3acc6967243b23643dad482325c459`.
- The QUIET and GLOBAL_ONESHOT probe sets differ only in their measured clock
  branch-current labels; the exact per-run manifests are bound in the registry.
- Platform runner SHA-256: `add8a056ea7d0b8d07cb69db09507abddba25d8ae5ca9f40f078f2a2ae76f745`.
- JoSIM: `/home/howard/JoSIM/build/josim-cli`, v2.7.2837d13, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Static Python topology QA: `PASS`; JoSIM `-s` syntax/sanity checks for all three
  registered decks: exit 0, no stderr. The `-s` commands are static-only and
  produced no raw; physical solve count so far is **0**.
- Legacy render-only compatibility: `DIAGONAL_TERMINAL` and
  `DIAGONAL_T1_INDEPENDENT` both `PASS`.
- A prior batch-gate attempt at HEAD `37c93d16` halted before JoSIM because one
  probe manifest was incorrectly reused across clock modes. It invoked no
  solver, created no run directory/raw, and used zero physical solves. The
  per-run probe registry fix is commit `feb8d505`; its full static revalidation
  is `PASS`. Machine record: `GATE_INCIDENT.json`.
- The preflight package will be committed before execution. The exact runtime
  HEAD is recorded by each run's metadata/provenance.

## Physical source and topology freeze

Canonical upstream closure is SHA-bound and unchanged:

| Source | SHA-256 |
|---|---|
| `circuits/models/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `circuits/bvm/bvm_cell_0923.cir` | `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7` |
| `circuits/qb/BQ_0928.cir` | `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a` |
| `circuits/sJTL_0923.cir` | `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688` |
| `circuits/CB/CB_0928.cir` | `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370` |
| `circuits/t1/t1_cell.cir` | `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237` |
| `circuits/standard/MERGE.cir` | `2fdc5c24798c619eee97dee07d1dcb02b2e49e3b96bfa868f86ec978dca6f96e` |
| `circuits/standard/DFF.cir` | `e63473b890b67bd968ee9891518e7b4f9b52560cb49e20fa18fa50f03b6bc6f0` |

The array's `CB_0928` remains the one-input `.subckt CB IN OUT`; it is not the
CBU. The CBU candidate is the three-port ColdFlux `THmitll_MERGE a b q`.
Its local copy fixes only the active smart quote in `BiasCoef=0.7’`; default
body equivalence after that syntax-only correction is `true`. DFF is
`THmitll_DFF a clk q`. D0 uses one experiment-local `D0_JTL` copy with the
canonical sJTL default active values. Candidate details and residual
compatibility limits are recorded in `CBU_COMPATIBILITY.md` and `STATIC_QA.json`.

All seven T1 instances, six CBU instances, D0 JTL and one DFF coexist in each
deck. `DOUT_D0 -> D0_JTL -> T1_D0.I`; for k=1..6,
`DOUT_Dk -> CBU_Dk.A`, `C_D(k-1) -> CBU_Dk.B`, and `CBU_Dk.q -> T1_Dk.I`.
`S0..S6` are separate outputs; `C0..C5` directly drive the next CBU; `C6`
drives DFF data and `DFF_O` is bit7. DOUT terminations and carry resistors are
absent. Each Sum has 12 Ω load; DFF.O has the registered 12 Ω measurement-load
candidate. No ideal adder, ideal SFQ injection, carry short, CBU output merge,
CBU/DFF tuning, or canonical-source modification is used.

## Parameters, stimulus, timing, loads

Frozen upstream values are A019: shared WL/BL 400u source settings, cell SE
100u, `SE_ENABLE_MASK=ALL`, and per-diagonal sJTL counts
`D0=1; D1=1,1; D2=1,2,1; D3=1,2,2,1; D4=1,2,1; D5=1,1; D6=1`.
WRITE0/READ0/WRITE1/FINAL_READ PWL timing and polarity are unchanged from
`STIMULUS.env`. `DT=0.01p`; `STOP=300p`.

T1 Bias values are 1.8m on all three ports; S load 12 Ω. CBU parameters are
the values in `config/CBU_PARAMS.env`, default-equivalent to the inspected
candidate. DFF uses `config/DFF_PARAMS.env`; D0 JTL uses
`config/D0_JTL_PARAMS.env`. The DFF.O external 12 Ω load is a starting
measurement candidate only.

- A020 clock: `QUIET`; seven independent T1 5 Ω clamps plus one independent DFF
  5 Ω clamp; no floating clock node.
- A021/A022 clock: `GLOBAL_ONESHOT`, all eight branches independent, identical
  PWL `0→0 @ 200p, rise 1p to 1.2m @ 201p, hold through 203p, fall to 0 @ 204p`,
  series 2 Ω. No periodic repetition and no staggered start.
- A020/A021 use ROW/COL `1111/1111`, theoretical diagonal multiplicity
  `[1,2,3,4,3,2,1]`, theoretical T1 total-input multiplicity
  `[1,2,4,6,6,5,3]`, carry reference `[0,1,2,3,3,2,1]`; A022 uses
  `1101/1101`, diagonal `[1,1,1,3,1,1,1]`, T1 total-input
  `[1,1,1,3,2,2,2]`, carry reference `[0,0,0,1,1,1,1]`. These are theory
  references, never QA thresholds or software-decoded outputs.

## Exact authorized run matrix

| Run | Case | ROW/COL | Clock | Deck SHA-256 | Stimulus SHA-256 |
|---|---|---|---|---|---|
| A020 | CHAIN_ALL_QUIET | 1111/1111 | QUIET | `6a51a8fd7d1d5f44d2c75486d5e786bfe46ea0e3546b08a7dca3d826f8901a08` | `d149f6f4e83360d8a1b1671e655ed1c9ea241722ebbbc1de48ae4e9fc792f4e2` |
| A021 | CHAIN_ALL_GLOBAL_CLOCK | 1111/1111 | GLOBAL_ONESHOT@200p | `678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364` | `d149f6f4e83360d8a1b1671e655ed1c9ea241722ebbbc1de48ae4e9fc792f4e2` |
| A022 | CHAIN_PAPER_GLOBAL_CLOCK | 1101/1101 | GLOBAL_ONESHOT@200p | `678b08e181ecaba8b96b81f2798dc949309c76e3f14ead7ea2b7773bb0369364` | `d129cc80bceae1382a3d8011c3265dfc451993a2ae7211ed4f1a341ae9ca7926` |

A021/A022 have identical circuit decks and differ only in the registered
ROW/COL-dependent FINAL_READ PWL values (`I_WL_R3` and affected cell-local
`I_SE_*` branches); all time knots and preparation phases are equal. A020/A021
deck comparison differs only in independent clock branch devices and their
corresponding branch-current `.print` directives.

## Probe, metrics and artifact gates

The frozen `t1_chain_focus` manifest has 238 signals. It includes DOUT and last
array-CB BJ1 P/V; each T1 input/CLK/S/C; T1 B_J1/B_J2/B_J9/B_J10/B_J11 P/V;
all CBU A/B/OUT boundary voltages and branch currents plus B1/B4/B7 P/V;
D0 JTL input/output/current and BJ1 P/V; DFF data/CLK/O, output-load current
and B1/B2/B7 P/V; eight independent clock branch currents; representative
bias-current diagnostics. The three independent T1 Bias setpoints and all
CBU/DFF Bias values are preserved in the deck and run config snapshots.

The runner estimates `91,929,270` raw bytes/run using the registered estimator,
below the 100,000,000-byte single-file guard. No timestep reduction or lossy
sampling is permitted. Raw QA must verify exact probe header, finite values,
monotonic actual timestamps, sample count, time range and unchanged SHA.
Integrals use actual stored grid and half-open windows listed in
`METRIC_SPEC.json`. P(...) remains radians; same-JJ phase/voltage comparisons
use the exact same run, junction, direction, rows and window. Relative lobe
candidates are navigation only and never event/SFQ counts.

Every run must produce `deck.cir`, stimulus/config snapshots, all rendered
device-source snapshots, solver stdout/stderr/log, raw, source/topology/probe
manifests, metrics, raw/chain QA, provenance, result metadata and three local
classic Plotly pages. HTML stays local and is excluded from the DELTA ZIP.

## Stop rules and interpretation boundary

Only A020-A022 (three solves, sequentially) are authorized. Stop after the
first solver/raw/artifact hard failure. Preserve any valid physical negative
case and continue only when artifact/raw/mechanical QA pass. Do not retry,
sweep, tune, alter timing, or start another solve. No bit decoder threshold is
registered; actual multiplier-bit decoding is `NOT_PERFORMED`. No scientific
interpretation is authorized. After evidence package/commit/push, stop at
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
