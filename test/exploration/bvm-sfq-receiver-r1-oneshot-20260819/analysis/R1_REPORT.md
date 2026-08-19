# BVM -> SFQ receiver R1 one-shot / self-quench Exploration

## Verdict

**R1 FAIL for the tested minimal receiver topology.**

The four matched cases were run at four deliberately local operating points.
The logical1 B_TRIG excursion never reached one complete 2π monotonic phase
transition, and the output JJ remained in its static subcritical state in every
case. Therefore the required logical1 exactly-one output event was not
observed. The zero output activity in logical0 and READ=0 controls is real but
is not sufficient for a one-shot PASS when read1 also has zero output events.

This is a bounded Exploration result. It is not an SFQ-delivery claim, a
Candidate result, or a statement that another receiver topology cannot work.

## Research question and frozen criterion

The question was whether the R0b canonical-SL receiver could be extended so
that read1 produces exactly one complete local output-JJ event while read0 and
both READ=0 controls produce zero complete output events.

Before running, the criterion was frozen in `manifest.yaml`:

- use raw `P(B_OUT|XTRIG)` in radians;
- unwrap adjacent samples continuously, retaining the raw phase column;
- split only at a sign change in the unwrapped phase delta;
- count complete units as `floor(abs(monotonic phase delta)/(2*pi))`, so a
  5-turn monotonic segment cannot be counted as one event;
- integrate `V(B_OUT|XTRIG)` over the exact same segment and compare it with
  the phase delta;
- require exactly one complete unit in the read-trigger window, area residual
  no greater than 0.05 turn, and no complete unit in POST;
- require zero complete output units over the full window for read0 and both
  READ=0 controls.

No event was inferred from current above Ic, a voltage peak, or phase range
alone. No local transition was called downstream SFQ delivery.

## Receiver topology

The canonical BVM was not edited. All cases used the canonical `SL1` route and
`R_IN=12 ohm`:

```text
SL1 -- R_IN -- N_TRIG -- B_TRIG(AREA=0.50) -- ground
                    |
                    +-- L_Q -- N_Q -- R_Q -- ground
                    |
                    +-- mutual K=0.80 -- L_SEC -- OUT_PORT -- R_LOAD -- ground

N_OUT -- B_OUT(AREA=0.50) -- N_SEC
  |
  +-- I_OUT_BIAS=35 uA to N_OUT
  +-- R_OUT_DAMP=20 ohm to N_SEC
```

The first point used `L_Q=1 pH`, `R_Q=15 ohm`, `L_SEC=2 pH`, and `R_LOAD=12
ohm`. Three local follow-ups changed only the feedback branch:

| point | `L_Q` | `R_Q` | unchanged output elements |
|---|---:|---:|---|
| `a050-b15` | 1 pH | 15 ohm | `L_SEC=2 pH`, `K=0.80`, `B_OUT AREA=0.50`, 35 uA, 20 ohm, 12 ohm |
| `a050-b15-rq100` | 1 pH | 100 ohm | same |
| `a050-b15-rq1k` | 1 pH | 1000 ohm | same |
| `a050-b15-lq10` | 10 pH | 15 ohm | same |

The BQ-v4 and paper-like BQ files are preserved as references only; the full
BQ topology was not copied.

## Actual JJ model and parameters

The frozen model was read from `inputs/jjmit.cir` and interpreted according to
the repository's JoSIM implementation:

```text
.model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)
```

For both B_TRIG and B_OUT, `AREA=0.50` gives:

| quantity | actual value |
|---|---:|
| Ic | 50 uA |
| RN | 32 ohm |
| R0 | 320 ohm |
| C | 35 fF |
| beta_c before added dynamic shunts | 5.4450545 |

AREA scales Ic and C upward and divides RN and R0; it does not only change Ic.
The 35 uA output bias is subcritical relative to the 50 uA output Ic. For
reference, the initial 15 ohm shunt gives an approximate dynamic `RN || R_Q`
of 10.21 ohm and an approximate parallel-shunt beta estimate of 0.554. These
are mechanism estimates, not replacements for the transient model. The output
20 ohm shunt gives `RN || R_OUT_DAMP` of about 12.31 ohm.

## Matched raw results

The table reports the largest B_TRIG monotonic segment in
`TRIGGER_ANALYSIS`. The voltage area is integrated over that same segment and
has the same sign and direction as the phase delta. None is a complete 2π
transition.

| point / case | B_TRIG segment (ps) | phase delta (turns) | same-JJ V area (turns) | complete output units |
|---|---|---:|---:|---:|
| `a050-b15/read1` | 101.6000–102.9375 | -0.211572417 | -0.211614196 | 0 |
| `a050-b15/read0` | 106.7250–108.3375 | +0.084413172 | +0.084424073 | 0 |
| `a050-b15-rq100/read1` | 108.4500–109.9375 | +0.341663168 | +0.341716787 | 0 |
| `a050-b15-rq100/read0` | 106.6625–108.2500 | +0.163302919 | +0.163324495 | 0 |
| `a050-b15-rq1k/read1` | 103.1125–105.3625 | +0.919537896 | +0.919583254 | 0 |
| `a050-b15-rq1k/read0` | 106.6000–108.2250 | +0.183048493 | +0.183071722 | 0 |
| `a050-b15-lq10/read1` | 102.9875–104.7500 | +0.372471173 | +0.372532782 | 0 |
| `a050-b15-lq10/read0` | 106.6625–108.0500 | +0.111513805 | +0.111533621 | 0 |

The controls remained at approximately `2e-5 turns` or less in the largest
listed B_TRIG segment. The full raw trajectories and all smaller segments are
in `r1-analysis.json`; no short segment is promoted to a switching event.

For every one of the 16 raw runs:

- output complete-unit count over 20–200 ps: **0**;
- output complete-unit count in POST: **0**;
- output phase largest segment: `4.77464829e-8 turns`, a startup numerical
  settling segment, not a transition;
- output `P(B_OUT|XTRIG)` stays at its static value (about 0.7754 rad in the
  read1 example);
- output same-JJ voltage is at numerical-zero scale (read1 activity peak about
  `2.6e-17 V` in the primary point), with no output pulse area to validate as a
  one-turn event.

The output phase trajectory therefore fails the first logical1 R1 condition;
there is no legitimate output event count of one to report.

## Failure mechanism evidence

At the initial point, read1 has an R0-like input current peak of about 63.48
uA and the independent trigger bias is 15 uA, but the new `R_Q` branch carries
about 34.74 uA peak. B_TRIG consequently makes only 0.212 turn. Changing
`R_Q` to 100 ohm reduces its observed peak to about 7.80 uA and increases the
read1 B_TRIG segment to 0.342 turn. At 1 kohm the branch peak is about 1.71 uA
and B_TRIG reaches 0.920 turn, still below 2pi. Increasing `L_Q` to 10 pH
while restoring 15 ohm produces 0.372 turn and about 29.82 uA branch-current
peak.

This monotonic local response supports the bounded classification
**feedback/transfer branch dynamically loads or stores the trigger excursion;
the initial branch is too strong, and weakening it does not yet establish a
usable output transfer**. It does not prove a universal impossibility. The
output loop never departs from its 35 uA DC bias in any point, so
`output-too-weak/no-output` cannot be separated from `trigger-not-complete` in
this topology; that is why no output damping or coupling sweep was attempted.

The JoSIM logs confirm that the mutual-inductance stamping path was exercised.
This observation does not by itself establish a useful pulse transfer.

## BVM back-action and controls

Loaded BVM separation remains observable at the receiver input. At the initial
point, read1 has `V(SL1)` absolute peak 1.121568 mV, `V(N6)` absolute peak
1.879657 mV, and `I(R_IN)` absolute peak 63.48411 uA; read0 has corresponding
absolute peaks 0.422939 mV, 0.7121973 mV, and 22.87602 uA, with opposite SL/N6
signs. At the `L_Q=10 pH` point these are 1.217876 mV / 1.908347 mV / 57.33336
uA for read1 and 0.4248443 mV / 0.7003139 mV / 21.91500 uA for read0.

The storage signs remain separated in the initial point: before/after
medians are approximately `JM1=+5.911061/+5.910946 rad` and
`JM2=+0.3172004/+0.3132791 rad` for read1, versus
`JM1=-5.911061/-5.911029 rad` and `JM2=-0.3171923/-0.3170456 rad` for read0.
The largest reported storage deltas are bounded observations, not a storage
Gate. JS1/JS2 and all requested branch probes are retained in every CSV.

The two READ=0 controls show no complete trigger or output transition and no
free-running output trajectory over 20–200 ps. This satisfies the negative
control part of the test but cannot rescue the missing read1 event.

## Reset and self-quench assessment

No output event occurred, so a post-event self-quench/reset was not actually
tested. The POST output phase has zero complete units and bounded numerical
voltage/current samples, but this is a **no-event bounded state**, not evidence
that the proposed quench branch successfully retraps a running output JJ.
Likewise, the proposed mechanism “R_Q dissipates B_TRIG energy and the output
load reflects a transient damping path” remains an inference; no complete
trigger/output transition was available to establish its causal sequence.

## Evidence classification

### Observed

- 16 new raw CSV runs, four matched cases at each of four local points.
- All required phase, same-JJ voltage, input, feedback, output, BVM, storage,
  readout, and source probes are present and finite.
- Requested timestep is 0.0125 ps; actual CSV spacing is 0.0125–0.025 ps;
  each file has 15,999 intervals to 200 ps.
- B_TRIG never reaches a complete 2pi monotonic segment.
- B_OUT has zero complete transition units in read1, read0, and controls.
- The independent cross-check agrees with all primary raw hashes, B_TRIG
  largest-segment metrics, and output event counts.

### Derived

- Phase turns are raw-radian deltas divided by 2pi.
- Same-JJ voltage areas agree with the sub-turn B_TRIG phase segments, with
  the residuals shown in the table and the structured JSON.
- Output event count is zero under the frozen segment-unit rule.
- Loaded SL/N6 and storage-sign comparisons above.

### Inference

- The 1 pH branch plus low R_Q dynamically loads/stores enough trigger current
  to prevent the R0b trigger from running; increasing R_Q partially relieves
  this but does not produce a complete trigger or output event.
- The present isolated mutually coupled output loop is not demonstrated to
  receive a usable pulse.

### Unknown

- Timestep-converged one-shot behavior; no convergence rerun was authorized in
  this bounded Exploration.
- Whether a series-injection or differently isolated transformer topology can
  produce one output event while preserving the SL discrimination.
- Whether any complete output event would retrap exactly once under the actual
  model.
- Downstream JTL reception and SFQ delivery; neither was tested.

## Artifact locations

- preregistration and parameters: `manifest.yaml`
- raw inputs and model fixtures: `inputs/`
- raw CSV and simulator logs: `raw/` and `logs/`
- primary analysis: `analysis/r1-analysis.json`
- independent cross-check: `analysis/independent-crosscheck.json`
- review findings: `analysis/REVIEW.md`
- hash inventory: `analysis/sha256sums.txt`

No canonical BVM file, R0/R0b raw file, or prior frozen evidence was modified.
