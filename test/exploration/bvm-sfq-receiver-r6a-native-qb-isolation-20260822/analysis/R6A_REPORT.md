# R6-A weak-mutual transformer isolation into native paper-QB

## Verdict

**`ISOLATION_PRESERVED_STATE_SELECTIVE_QB_ACTIVITY`**

The selected transformer interface preserves the canonical BVM source/read1
behavior against the committed no-receiver source raw, removes the large
direct-SL native-QB post-window ringing, and retains a measurable read1-over-
read0/native-control QB response. This is a positive isolation-feasibility
result.

`ISOLATED_NATIVE_QB_LOCAL_PASS` is **not met**: read1 BJL2 has no complete
one-turn same-JJ phase/area-consistent segment.

The absolute read1 JS1/JS2 phase change remains approximately `-3 turns`, but
the no-receiver canonical BVM raw has the same read1 multi-turn source behavior.
For this isolation review, the guard is therefore the **additional loaded
post-window disturbance**, not the removal of canonical read1 running itself.

## Frozen interface and native-QB closure

```text
canonical BVM SL1 ── R_PRI 12 Ω ── L_PRI 0.20 pH ── ground
                                      ║ K=0.50
                         L_SEC 2.0 pH ║
native QB IN = QB_IN ─────────────────┘
                         QB_IN ↔ ground through the secondary winding
```

The actual secondary branch is `L_SEC QB_IN 0 2.0p`; `QB_IN` is the native
`BQ_PAPER IN` port. The primary has an explicit passive current return. The
canonical BVM internal SL termination was not removed or replaced.

Native QB was copied unchanged:

| Element | Frozen value |
|---|---:|
| BJs / BJL1 / BJL2 AREA | 1.33 / 1.12 / 1.89 |
| Lin / L0 / L1 / L2 | 0.8 / 1.323 / 3.91 / 3.91 pH |
| RJ1 / RJ2 / RB | 33 / 22 / 8.5 Ω |
| RB bias | 90 µA |
| OUT load | 10 Ω |
| New mutual point | `L_PRI=0.20 pH`, `L_SEC=2.0 pH`, `K=0.50` |

Thus `M=0.316227766 pH`. No JJ, native bias, native inductance, shunt, or
output load was changed.

## Analytic precheck versus measured isolated primary

The precheck used direct-SL `I(L_SL|XBVM1)` as a proxy. The actual isolated
run measured:

| Case | Direct-SL proxy peak (µA) | Measured `I(R_PRI)` peak (µA) | Measured `I(L_PRI)` peak (µA) |
|---|---:|---:|---:|
| read1 | 84.84 | 75.39 | 75.39 |
| read0 | 31.45 | 26.23 | 26.23 |
| logical1 READ=0 | 0.00176 | 0.000892 | 0.000892 |
| logical0 READ=0 | 0.00173 | 0.000891 | 0.000891 |

The proxy correctly predicted the scale and polarity, but the new measured
primary current is the authoritative interface result.

Measured secondary activity:

| Case | `V(L_SEC)=V(QB_IN)` peak (µV) | `I(L_SEC)` activity range (µA) | `V(OUT_Q)` peak (µV) |
|---|---:|---:|---:|
| read1 | 53.79 | 10.899..20.566 | 6.480 |
| read0 | 15.85 | 14.837..17.043 | 1.978 |
| logical1 READ=0 | 0.000576 | 16.001..16.001 | 0.0000069 |
| logical0 READ=0 | 0.000576 | 16.001..16.001 | 0.0000092 |

The secondary is therefore not a no-op: read1/read0 voltage separation is
about `3.39×`, while controls are near the numerical baseline.

## Native-QB phase and voltage-area evidence

Raw `P(...)` is radians. Continuous unwrapped phase is segmented in the
preregistered `[94,130)` ps activity window. `largest` is the largest
monotonic segment; `area` is the direct same-JJ voltage integral divided by
`Phi0`. A complete local event requires `|largest| >= 1 turn` and the local
phase/area residual within the task-local 0.05-turn diagnostic tolerance.

| Case | JJ | Activity range (turn) | Largest (turn) | Same-JJ area (turn) | Residual (turn) | Complete |
|---|---|---:|---:|---:|---:|:---:|
| read1 | BJs | 0.012519 | -0.012505 | -0.012508 | +0.00000324 | no |
| read1 | BJL1 | 0.012049 | -0.009342 | -0.009346 | +0.00000350 | no |
| read1 | BJL2 | 0.002885 | -0.001585 | -0.001585 | +0.000000376 | no |
| read0 | BJs | 0.003469 | -0.001847 | -0.001847 | +0.000000346 | no |
| read0 | BJL1 | 0.003209 | +0.001397 | +0.001397 | -0.000000302 | no |
| read0 | BJL2 | 0.000755 | -0.000364 | -0.000364 | +0.000000123 | no |
| logical1 READ=0 | BJs | 2.86e-7 | +2.23e-7 | +2.12e-7 | +1.04e-8 | no |
| logical1 READ=0 | BJL1 | 0 | 0 | +5.70e-10 | -5.70e-10 | no |
| logical1 READ=0 | BJL2 | 0 | 0 | +1.39e-10 | -1.39e-10 | no |
| logical0 READ=0 | BJs | 2.71e-7 | -2.23e-7 | -2.08e-7 | -1.52e-8 | no |
| logical0 READ=0 | BJL1 | 0 | 0 | -7.55e-10 | +7.55e-10 | no |
| logical0 READ=0 | BJL2 | 0 | 0 | -1.89e-10 | +1.89e-10 | no |

Read1 activity is approximately `3.6–3.8×` read0 activity across BJs/BJL1/BJL2
and orders of magnitude above the READ=0 controls. It is state selective but
sub-turn. No BJL2 event is called from current or voltage peak alone.

## Source and storage guard comparison

The most important guard is a comparison against the existing canonical
no-receiver source raw, not just against the previous direct-SL QB-loaded raw.

| Read1 observable | Canonical BVM source | Direct SL → native QB | R6-A isolated QB |
|---|---:|---:|---:|
| peak `I(L_SL)` (µA) | 75.341 | 84.839 | 75.393 |
| peak `V(SL1)` (µV) | 904.091 | 1174.104 | 903.312 |
| peak `V(N6)` (µV) | 1814.477 | 1497.448 | 1816.279 |
| JM1 post-pre (turn) | +0.0000779 | +0.0000407 | +0.0000816 |
| JM2 post-pre (turn) | +0.0000575 | +0.0008507 | +0.0000409 |
| JS1 post p2p (turn) | 0.05604 | 0.22693 | 0.05598 |
| JS2 post p2p (turn) | 0.00554 | 0.24426 | 0.00557 |

R6-A reproduces the no-receiver source scale and JS post-window behavior while
removing the direct-QB post ringing. The read1 JS1/JS2 net change remains about
`-3 turns` in both canonical and isolated runs because it is the canonical
READ response itself. Treating that absolute read1 phase running as receiver
back-action would incorrectly reject the no-receiver source baseline.

The actual storage elements JM1/JM2 remain bounded and the isolated JM2 drift
is much smaller than in the direct-SL QB-loaded run. READ=0 controls remain
quiet. Native BJL2 post-window p2p is below `1e-6 turn` for read1/read0, with
no free-running signature in the finite post window.

## Evidence classification

### Observed

- All four matched simulations completed with finite, monotonic, complete raw
  CSVs and the required primary, secondary, native-QB, source, and storage
  probes.
- The primary return carries state-dependent read1/read0 current.
- The secondary produces a clear read1/read0 voltage transient.
- Native QB BJs/BJL1/BJL2 activity is separated for read1 versus read0 and
  controls, but all activity remains sub-turn.
- The isolated read1 BVM source and post waveform match the canonical source
  raw much more closely than the direct-SL QB-loaded raw.
- No read0/control complete event or free-running BJL2 behavior is observed.

### Derived

- The weak mutual interface satisfies the preregistered isolation-feasibility
  criterion A: state-selective QB activity with preserved source/storage
  behavior.
- It does not satisfy criterion B because read1 BJL2 has no complete segment.
- The result is not `TRANSFER_STARVATION` under the preregistered definition:
  read1 activity does not collapse to read0/control levels. It is, however, a
  low-margin sub-turn transfer point.

### Inference

- Galvanic SL→QB coupling was the source of the extra direct-QB loading seen
  previously; weak mutual coupling removes that extra loading at this point.
- The native QB loop receives a real state-dependent transient, but the chosen
  weak point does not yet drive quantization.

### Unknown

- Whether a stronger isolated interface can produce a complete BJL2 event
  without losing the source guard; no K/L sweep is authorized by this run.
- Whether native-QB activation requires a separately defined BVM-scaled input
  impedance/current class.
- Time-step convergence and robustness of this single point.
- Any downstream JTL/T1 reception; neither was connected.

## Layered verdict

| Layer | Verdict | Reason |
|---|---|---|
| A `ISOLATION_PRESERVED_STATE_SELECTIVE_QB_ACTIVITY` | **PASS** | Source/storage behavior matches canonical no-receiver baseline; read1 QB activity remains separated. |
| B `ISOLATED_NATIVE_QB_LOCAL_PASS` | **NOT MET** | Zero complete BJL2 events, including read1. |
| C `TRANSFER_STARVATION` | **Not primary** | Activity is low but does not collapse to read0/control. |
| C `REFLECTED_LOAD_BACK_ACTION_FAILURE` | **Not observed at this point** | Comparative source/storage guard is preserved. |
| C `NONSELECTIVE_ACTIVITY` | **Not observed** | Read0/controls remain inactive and non-running. |
| C `INCONCLUSIVE` | **Not primary** | Artifact and bounded A-level comparison are resolvable; convergence remains an explicit Unknown. |

This is an Exploration result only. It does not modify canonical BVM or native
QB, does not change AREA/bias/RJ values, and does not authorize JTL/T1.
