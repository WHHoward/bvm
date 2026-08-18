# BVM -> SFQ receiver R0b complete-trigger closure Exploration

**Created:** 2026-08-19T04:49:22+08:00
**Parent:** c760c13c685d16bcbe3977e1df535e48bf45711b
**Tier:** Exploration / EXPLORATORY
**Route:** canonical BVM `SL` output; `R_IN=12 ohm`
**Solver:** `build/josim-cli` v2.7.2837d13
**Solver SHA-256:** `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
**Requested numerical condition:** `dt=0.0125 ps`, stop `170 ps`
**R0b verdict:** **PASS** at the first attempted point, `AREA=0.50`, `bias=+15 uA`

This is a local complete-trigger result. It is not an exactly-one-SFQ result,
not SFQ delivery, not a JTL result, not a self-quench result, and not a
Candidate or system Gate. The original c760c13 raw evidence remains corrected
as `R0-A PASS / R0-B NOT_YET`; this independent R0b run closes the missing
R0-B criterion at a new operating point.

## 1. Question, scope, and stopping rule

The only question was whether the unchanged SL receiver can produce at least
one complete `2*pi` phase transition for logical1 +READ while logical0 +READ
and both matched READ=0 controls produce none.

The preregistered order was:

1. `AREA=0.50`, `bias=15 uA`;
2. `AREA=0.50`, `bias=20 uA`;
3. only if both failed, `AREA=0.45`, `bias=20 uA`;
4. only if still needed, `AREA=0.40`, `bias=20 uA`.

The first point passed all required checks, so the sequence stopped there. The
other three operating points were not run; no blind sweep and no N6 route was
performed.

The four matched circuits were identical in receiver topology and timestep:

| Case | BVM state | READ |
|---|---:|---|
| `read1` | logical 1, +100 uA WL+BL initialization | canonical +100 uA WL+SE, 96–105 ps |
| `read0` | logical 0, -100 uA WL+BL initialization | the same canonical positive READ |
| `logical1-read0-control` | logical 1 | READ amplitude zero |
| `logical0-read0-control` | logical 0 | READ amplitude zero |

No canonical BVM file or internal topology was modified.

## 2. Receiver topology and actual JJ parameters

```text
canonical BVM SL -- R_IN=12 ohm -- N_TRIG -- B_TRIG -- ground
                                           ^
                                  +15 uA independent bias
```

The receiver is the same one-JJ topology as the prior SL R0 fixture. There is
no self-quench loop, output JJ, JTL, or explicit parallel shunt.

The included model is:

```text
.model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)
```

`src/JJ.cpp` was checked directly: `AREA` multiplies `Ic` and `C`, and divides
`RN` and `R0`; no explicit `IC=` override is present. Thus the attempted point
has:

| Quantity | Actual value |
|---|---:|
| AREA | 0.50 |
| `Ic` | 50 uA |
| `RN` | 32 ohm |
| `R0` | 320 ohm |
| `C` | 35 fF |
| external `R_IN` | 12 ohm |
| independent bias | +15 uA |
| explicit parallel shunt | none |
| derived `beta_c = 2*pi*Ic*RN^2*C/Phi0` | 5.4450545 |

The unrun fallback points were also model-recomputed, not treated as Ic-only
changes: AREA=0.45 gives `Ic=45 uA`, `RN=35.5556 ohm`, `R0=355.5556 ohm`,
`C=31.5 fF`; AREA=0.40 gives `Ic=40 uA`, `RN=40 ohm`, `R0=400 ohm`,
`C=28 fF`. Their derived beta-c values remain 5.4450545 under this area
scaling.

## 3. Direct phase/voltage criterion

The analysis reads raw `P(B_TRIG|XTRIG)` in radians and independently creates
a continuous phase by adjacent-sample `2*pi` unwrapping. Raw phase is not
replaced. A complete transition requires one sign-consistent monotonic segment
with `abs(delta_phase) >= 2*pi`; the segment's voltage area is integrated over
the exact same B_TRIG endpoints using the actual CSV time column and divided by
`Phi0=2.067833848e-15 Wb`.

The primary trigger analysis window is 94–170 ps, and a qualifying read segment
must start no later than 130 ps. The 94–130 ps window is retained for the
read-edge activity summary. `I_total > Ic`, voltage peak, derivative samples,
and any SFQ count are not switching criteria.

### Raw trajectory and monotonic segments

All numbers below come from the independent `analyze_r0b.py` calculation and
the preserved raw CSVs. The activity range and endpoint/net area are not event
counts.

| Case | 94–130 phase range | endpoint delta | same-window V area | largest segment in 94–170 |
|---|---:|---:|---:|---:|
| `read1` | 33.6437215 rad = 5.3545646 turns | +5.0106021 turns | +5.0106041 turns | 4.9974563 turns |
| `read0` | 1.1902876 rad = 0.1894402 turns | +0.0252035 turns | +0.0252076 turns | 0.1852812 turns |
| logical1 READ=0 | 0.0005305 rad = 0.00008443 turns | +0.00000337 turns | +0.00000337 turns | 0.00008443 turns |
| logical0 READ=0 | 0.0015956 rad = 0.00025395 turns | +0.0001360 turns | +0.0001360 turns | 0.00025395 turns |

The decisive segment table is:

| Case | Segment time / direction | Raw phase endpoints (rad) | Continuous delta | Same-segment V area | Complete? |
|---|---|---:|---:|---:|---|
| `read1` | 102.9875–113.7625 ps, increasing | 2.548426 -> 33.948370 | +31.399944 rad = **+4.9974563 turns** | +4.9974806 turns | **YES** |
| `read0` | 106.5875–108.2125 ps, increasing | -0.3224221 -> 0.8417338 | +1.1641559 rad = +0.1852812 turns | +0.1853045 turns | NO |
| logical1 READ=0 | 94.825–96.350 ps, decreasing | 0.3049714 -> 0.3044409 | -0.0005305 rad = -0.00008443 turns | -0.00008444 turns | NO |
| logical0 READ=0 | 94.0375–95.575 ps, increasing | 0.3038708 -> 0.3054664 | +0.0015956 rad = +0.00025395 turns | +0.00025399 turns | NO |

For the read1 qualifying segment, the same-segment area is
`1.033395949e-14 Wb`, or `4.9974806 turns`; area minus phase is only
`+2.42765e-5 turns`. The read0 largest segment's area-minus-phase residual is
`+2.33661e-5 turns`. These are same-junction endpoint checks, not a claim of
quantization.

The READ=0 controls were also checked over the broader 20–170 ps control window
for startup/free-running activity. Their largest full-window monotonic segments
were only `0.0635124 turns` (logical1 control) and `0.0698705 turns` (logical0
control), with no complete segment.

## 4. Artifact QA and raw evidence

Each attempted case produced 13,599 finite data rows from 0 to 169.9875 ps,
with strictly increasing time and actual CSV spacing 0.0125–0.025 ps. All four
solver stderr files are empty. The raw hashes are:

| Case | Raw CSV SHA-256 |
|---|---|
| `read1` | `609efe406917f4f110b774fcc103aeef122e1428b0c79ed6f451aa5579cae9e6` |
| `read0` | `096fe02e28980d409de6932095300afef0b955d3a8be448c2781a90203a4e5cd` |
| logical1 READ=0 | `2264f0833f3d99dbe4f6feae7ec759a3720070bb456b996fc27bf9ea46852564` |
| logical0 READ=0 | `6815ddda22f74221e3acd7e263029360b1663e9276d38ba5e0585350de6286bc` |

The fixture BVM hash is
`ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4`, equal
to the canonical `circuits/bvm/bvm_cell.cir`. The fixture JJ model hash is
`19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`, equal
to the recorded canonical model.

## 5. Loaded BVM separation and back-action

The receiver does not remove the read distinction:

| 94–130 ps quantity | read1 | read0 |
|---|---:|---:|
| positive `V(SL1)` peak | +1.812093 mV | +0.3771494 mV |
| positive `V(N6)` peak | +1.968229 mV | +0.593131 mV |
| positive `I(L_SL)` peak | +54.20765 uA | +17.15898 uA |
| positive receiver drive (`I(R_IN)+bias`) | +69.20765 uA | +32.15898 uA |
| B_TRIG `Ic` | 50 uA | 50 uA |
| `P(JS1)` activity range | 40.1841982 rad | 1.5125030 rad |
| `P(JS2)` activity range | 40.7677589 rad | 2.4086074 rad |

The storage medians show no sign inversion or collapse:

| Case | JM1 pre -> post, delta rad | JM2 pre -> post, delta rad |
|---|---:|---:|
| read1 | 5.911061 -> 5.911101, +0.0000400 | 0.3172278 -> 0.2925266, -0.0247012 |
| read0 | -5.911061 -> -5.911091, -0.0000300 | -0.3172220 -> -0.3212181, -0.0039961 |
| logical1 READ=0 | 5.911061 -> 5.911075, +0.0000140 | 0.3172278 -> 0.3169241, -0.0003037 |
| logical0 READ=0 | -5.911061 -> -5.911075, -0.0000140 | -0.3172220 -> -0.3169241, +0.0002979 |

The JM2 read1 shift is larger than in the controls, so this is a bounded
back-action observation rather than a state-preservation Gate. Nevertheless,
the post-read logical signs remain distinct (`JM1` about ±5.911 rad and `JM2`
about +0.293 versus -0.321 rad), and the loaded SL/N6/readout separation
remains present.

## 6. Bias-only and post-event checks

Neither READ=0 control has a complete segment in either the read-trigger window
or the broader 20–170 ps check. Their trigger post-window voltage peaks are
below 0.111 uV and their largest post segments are below 0.000049 turns.

For read1, the post-read 130–170 ps largest monotonic segment is only
`0.1509123 turns` and is not complete. The trigger voltage peak decreases from
`383.945 uV` in 130–140 ps to `85.841 uV` in 160–170 ps; the absolute input
branch-current peak decreases from `3.153 uA` to `0.096 uA` over the same
windows while the applied bias remains 15 uA. This is a decaying ring in the
bounded stop window, not evidence of sustained free running.

## 7. Evidence classification

### Observed

- The first attempted matched operating point has valid raw phase and voltage
  data for all four cases.
- The logical1 read1 B_TRIG trajectory contains one increasing monotonic segment
  of 31.399944 rad, exceeding 2*pi, with a matching same-segment voltage area.
- Logical0 and both READ=0 controls have no complete monotonic segment.
- The loaded SL/N6/readout distinction remains present, and storage signs remain
  distinct.
- The post-read ring decays over the recorded window and has no complete post
  segment.

### Derived

- At AREA=0.50, bias=15 uA, the direct local complete-trigger criterion is met:
  `read0 effective drive < Ic < read1 effective drive` is observed as
  `32.15898 < 50 < 69.20765 uA`, while the verdict itself comes from phase
  segments, not current threshold crossing.
- The read1 same-segment phase delta and voltage area agree to
  `2.42765e-5 turns`.

### Inference

- The canonical SL route can form a complete local B_TRIG phase transition with
  logical1 +READ while the matched logical0 and READ=0 cases do not, under this
  model, load, bias, timing, and requested timestep.
- This operating point is a suitable bounded input for a separately designed R1
  self-quench study.

### Unknown

- Exactly-one behavior: the read1 segment spans about 5 turns and multiple
  additional damped excursions; no one-shot count is claimed.
- SFQ delivery to any downstream load or JTL.
- Timestep/convergence and parameter/load/temperature margin.
- Whether a self-quenching output stage can preserve the BVM storage state.
- Hardware behavior and process implications.

## 8. Verdict and next step

**R0b: PASS (Exploration-bounded complete local trigger).**

The success condition is satisfied at `AREA=0.50`, `R_IN=12 ohm`, and
`+15 uA` bias: read1 has a complete monotonic 2*pi phase segment; read0 and
both READ=0 controls do not; loaded BVM separation and bounded storage
back-action remain acceptable by the declared checks; and no complete
post-event control/free-running segment is observed.

Combined with the explicit correction of c760c13, the current split is now
`R0-A threshold discrimination PASS` plus `R0-B complete trigger switching
PASS` for this new operating point. This does not retroactively change the
old raw evidence or make it an exactly-one-SFQ result.

The smallest R1 proposal is to retain this SL front end and add one explicitly
defined self-quench/output-isolation feedback stage, initially without a JTL.
R1 should preregister the first-event trigger segment, post-event return/reset,
output-load response, and the same read1/read0/READ=0 controls. It should
directly probe both B_TRIG and the output junction with same-JJ phase/voltage
areas. R1 is proposed only; it is not implemented in this Exploration.
