# PREFLIGHT — delta4 replay sensitivity

> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Status: PASS; AWAITING_USER_REVIEW
- Experiment: bvmsim-jm2-delta4-replay-sensitivity-v1-20260908
- Study phase: EXPLORATION; mode: QUICK
- Setup time: 2026-09-08T10:31:52+08:00
- HEAD at setup: 2a3e3caeaefd511aa6e555dff18e596bd968f3a2
- Worktree at setup: clean
- Scope: exactly four new ideal-current replay solves; no N5/N6, no tuning, no T1
- Historical docs/HANDOVER.md and memory/project-todo.md were read only;
  neither will be modified by this Exploration.

## 1. Question and interpretation ceiling

The question is whether the incomplete N4 fourth progression is more
consistent, within this fixed replay fixture, with timing/recovery sensitivity
or with insufficient effective marginal stimulus/front-end acceptance.

I_N4_PASSIVE(B_JSL8) - I_N3_PASSIVE(B_JSL8) is registered only as a
marginal source contribution / mathematical counterfactual component under
the matched N3/N4 fixture. It is not an independent SFQ, independent BVM
current source, physically separable pulse, or circuit-equivalent source
reconstruction.

Allowed labels are only OBSERVED, DERIVED, BOUNDED_RESULT and UNKNOWN.
No result may be written as root cause, dead-time limited, saturation, proves
mechanism, hardware measurement, universal mechanism, or formal SFQ PASS.
Any complete-looking progression remains a bounded simulation observation.

## 2. Immutable controls and source identity

Existing controls are read-only and are not rerun:

| role | path | SHA-256 |
|---|---|---|
| N3 replay control | test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/runs/n3_replay/raw.csv | 555e850fde892da7fd2328d2ac34081b45459ab48e8181a8e95d7cd531e7c225 |
| N4 replay control | test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/runs/n4_replay/raw.csv | 5cac782aa9dfa5d467d81e2988e772f1978abfe8313d7896089d5dfa84517b28 |
| N3 passive raw | test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/runs/n3_passive/raw.csv | f966077641779f90c5043bf7f5d9a4beaba9b13214977cc26cb399e1f6d90273 |
| N4 passive raw | test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/runs/n4_passive/raw.csv | ea9e1e123c80dfc38a0d3b061d8eb68f9ed76133db07490da616cb3bf5b70ba0 |
| N3 JSL8 source snapshot | test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/data/n3_passive_JSL8_source.csv | 93e41cf604bd373ad63f8fce2eadfd88d735b481fffc2e5e6434b0ff4ce7b586 |
| N4 JSL8 source snapshot | test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/data/n4_passive_JSL8_source.csv | f917c119fb9920a167188c45bd31f93895720f71e5ebe35f753181307860e2e6 |

The source signal is I(B_JSL8) on passive branch B_JSL8 JSL_NODE7 0.
The replay orientation is direct I_REPLAY 0 QBIN; no sign correction is
allowed.

## 3. Delta construction and exact reconstruction

Both snapshots must have the same actual stored Decimal timestamp grid:
1999 samples, 0.0 through 199.9 ps, with only the recorded 0.1/0.2 ps
intervals. The machine preflight must verify:

    delta_I4(t) = I_N4_PASSIVE(B_JSL8,t) - I_N3_PASSIVE(B_JSL8,t)
    I_N3_PASSIVE(B_JSL8,t) + delta_I4(t) = I_N4_PASSIVE(B_JSL8,t)

The reconstruction tolerance is 1.0e-21 A; source values and residuals are
kept as exact Decimal values in the machine record. Original raw files and
source snapshots are never overwritten.

## 4. Exact authorized run matrix

| run ID | replay current |
|---|---|
| DELTA4_DELAY_3PS | I_N3(t) + delta_I4(t - 3 ps) |
| DELTA4_DELAY_6PS | I_N3(t) + delta_I4(t - 6 ps) |
| DELTA4_GAIN_1P25 | I_N3(t) + 1.25 * delta_I4(t) |
| DELTA4_GAIN_1P50 | I_N3(t) + 1.50 * delta_I4(t) |

No other condition is authorized. N3/N4 controls remain immutable.

### Delay transformation

Only delta_I4 is moved. Each target timestamp uses an exact Decimal lookup
of target_time - delay in the original source map. There is no
interpolation, smoothing, resampling, fitting, waveform reconstruction or
nearest-neighbor substitution. If the exact timestamp is absent, including
the existing source-grid gap, the shifted delta is zero. If the argument is
outside the original source range, the shifted delta is zero.

### Signed gain transformation

Only the signed delta_I4 value is multiplied by 1.25 or 1.50.
Positive and negative values are scaled together. There is no rectification,
clipping or reshaping, and timestamps are unchanged.

## 5. Tail decision before solve

The preflight uses the fixed quiet-tail window [190,199.9] ps, inclusive of
the terminal stored sample for this endpoint check, and checks
absolute last value <=1.0 uA, p2p <=1.0 uA, and maximum adjacent stored
step <=0.1 uA. The read-only source check observed:

| source | last value | p2p in [190,199.9] | max adjacent step |
|---|---:|---:|---:|
| N3 | -0.02882568 uA | 0.17378300 uA | 0.022579749 uA |
| N4 | -0.04059690 uA | 0.24814940 uA | 0.032272000 uA |

This passes a bounded quiet-tail criterion but does not assert an exact
constant or physical equilibrium. Therefore every new run uses:

- .tran 0.1p 206p;
- output source grid through 205.9 ps;
- N3 background copied exactly through 199.9 ps;
- N3 background held at its final stored value only outside the original
  source domain, through the tail extension;
- shifted delta retained by exact timestamp lookup through the +6 ps
  shifted support; no delta extrapolation;
- primary response conclusions fixed to [110,200) ps.

Tail extension is registered because it follows the pre-solve quiet check; it
does not modify any original source sample.

Generated pre-solve artifacts are now frozen:

| artifact | SHA-256 |
|---|---|
| source/source_manifest.json | b16d0f7b97364ac8943e7e0171d1a23f013640c6af2911322277af1803020275 |
| data/delta4_source.csv | 07ca4a345239785a7ed251df8029f26757dc0054bc87739af01b7aa64f6094c0 |
| analysis/source_reconstruction.json | 3c9ab2bcfaf572f0786105d1b7abbc8575f3a33a3955b2d2e36eec48305f6749 |
| analysis/transformation_registry.json | d86d7484b18ee50042beb506e4ef9a59fd1987a4d2cbbc9c3c517097f11cd716 |

The four frozen deck hashes are recorded in the transformation registry:
DELTA4_DELAY_3PS is
667dde7e022a446827f61a75544af419ed4c37ef34206d95e5abd2545e332fbb;
DELTA4_DELAY_6PS is
26080f679668cd8680f8e0177976d143cfe8fc80520b6246fd5723d408698b64;
DELTA4_GAIN_1P25 is
35e5abf1cb698d4d256b8e022ceb975ffd1c239ffb34c4c4890f0f6eb201054e;
DELTA4_GAIN_1P50 is
c090955a26c2afaab970fe12c73de4cc49c3abbb8b11b35b04bbbffe4977d36.

## 5.1. Independent architect preflight review

Because the active controller is not Sol XHigh, a read-only
josim_architect review was requested before execution. The result was
CONDITIONAL_PASS. It found no need for an additional experiment, and required
the exact Decimal timestamp-key transformation, preserved source-grid gap,
explicit zero padding, signed gain, immutable N3/N4 controls, full QB/JTL
probes, internal-first timing and the interpretation ceiling recorded here.

Machine preflight: analysis/preflight.json, SHA-256
7b1646226b5b3989abe71dde4736bc7a0a12c63ea3bf2ab572f5c9138fe85d36.
Final pre-solve gate: analysis/pre_solve_gate.json, SHA-256
9d1fe5c9d8b600751769ff695e2efef2f0fba7dc75996c4f4438a4bd824c752e.

## 6. Frozen receiver, provenance and timing

All four decks use the exact existing replay receiver structure:

- BVMSim/BQ.cir, with RJ1=12 ohm, RJ2=4 ohm, IB=250 uA,
  BJS area=3, BJ1 area=0.9, BJ2 area=2;
- BVMSim/library_josim/jtl2.cir;
- six JTL stages, each with B01/B02 P/V/I and output voltage probes;
- R_TERM JTL6_OUT 0 10;
- circuits/models/jjmit.cir;
- build/josim-cli, nominal 0.1 ps, .tran 0.1p 206p.

The solver identity must be recorded before execution:

    build/josim-cli
    v2.7.2837d13
    SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2

The replay contains no BVM or passive JSL element. It is an ideal-current
waveform sufficiency oracle under the fixed receiver, not a physical source
network reconstruction.

## 7. Full probes

Every new deck must save:

- QBIN/input boundary and I(I_REPLAY);
- LIN, BJS, L1, BJ1, RJ1, L2, IB, BJ2, RJ2, L3 and QBOUT;
- for each QB JJ: available P/V/I;
- for each inductor/resistor: available I/V;
- JTL1 through JTL6: B01/B02 P/V/I and each stage output voltage;
- I(R_TERM).

If the solver omits a requested column, QA records it as UNKNOWN; no
missing signal is fabricated.

## 8. Fixed analysis windows and metrics

All windows are half-open [start,end):

| window | interval |
|---|---:|
| FINAL_READ_RESPONSE | [110,200) ps |
| QB_INTERNAL_CRITICAL | [118,140) ps |
| FOURTH_INTERNAL_SEARCH | [120,140) ps |
| DOWNSTREAM_ZOOM | [118,180) ps |
| TAIL_COMPLETENESS | [190,206) ps |

Internal timing is referenced first to BJ1/BJ2/QBOUT. JTL and terminal times
are downstream evidence only. All waveform area uses the actual stored time
column and trapezoid integration.

Activity thresholds are descriptive only: QBIN 0.25 mV, BJS 0.10 mV,
BJ1 0.30 mV, BJ2 0.50 mV, QBOUT 0.45 mV, JTL B01 0.50 mV, and
termination 5.0 uA, with two consecutive samples. Threshold samples or
clusters are never event counts.

P(...) remains raw radians. Each run is independently unwrapped before phase
comparison; display turns are rad/(2*pi). Same-JJ phase and direct voltage
area are cross-checked only with identical JJ, endpoints, direction and
window. No single phase, peak, area or threshold result is an SFQ count.

## 9. Machine gate and stop

Before solve, analysis/preflight.py must return PASS and write a
machine-readable record containing current HEAD, all source/control/model/
solver hashes, source grid QA, tail decision, exact delta reconstruction
requirements, exact four-run matrix, probes, windows, tolerances and
prohibited follow-ups.

After the four solves, the package must contain immutable raw/log/deck
artifacts, run metadata, transformation registry, source reconstruction
check, independent mechanical recomputation, metrics, standalone pages for
all four runs, controls/interventions comparisons, QB internal critical zoom,
JTL1–JTL6 full-chain view, visualization QA and this task's concise
RESULT_BRIEF.md.

After QA and evidence packaging the experiment stops at AWAITING_USER_REVIEW.
No tuning, convergence, physical BVM rerun, N5/N6 or T1 starts automatically.
