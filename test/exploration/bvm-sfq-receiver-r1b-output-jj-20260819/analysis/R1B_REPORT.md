# R1b minimum output-JJ activation Exploration

## Verdict

**R1b FAIL (valid bounded Exploration).**

The accepted R1a series pickup and the R0b trigger discrimination remain
functional, but the tested minimum output-JJ topology does not produce a
complete B_OUT transition in read1.  Therefore the required local output-JJ
activation criterion is not met.  This is not a failure of the BVM, SL route,
or B_TRIG R0b guard.

The Exploration used exactly two operating-point fixtures:

1. The preregistered initial point, whose raw matrix is retained as a
   diagnostic failure.
2. One root-cause topology correction, with the same output AREA, bias,
   damping, pickup values, and four matched cases.

No parameter sweep, self-quench loop, JTL, T1, or R1c implementation was
performed.

## Topology and parameters

The retained front end is:

```text
canonical BVM SL -> R_IN 12 ohm -> L_TX 0.20 pH -> B_TRIG
                                      |
                                      K=0.80
                                      |
                         L_SEC 2 pH -> R_SEC_LOAD 12 ohm -> ground
```

The output branch tested at the corrected point is:

```text
I_OUT_BIAS 7 uA -> B_OUT(N_OUT,N_SEC) || R_OUT_DAMP 100 ohm
                                   |
                         L_SEC N_SEC -> OUT_PORT -> R_SEC_LOAD -> ground
```

The actual `jjmit` model is
`jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)`.
For `AREA=0.10`, the derived output parameters are `Ic=10 uA`,
`RN=160 ohm`, `R0=1600 ohm`, and `C=7 fF`.  The output bias is `7 uA`; the
local parallel damping resistor is `100 ohm`.  The intrinsic model
`beta_c` is `5.4450545`; the simple RN-parallel damping estimate is
`0.8054814`.  These are model-derived quantities, not switching criteria.

The initial point instead used a grounded `L_SEC/R_SEC_LOAD` and consequently
made the output JJ a common-mode observer.  Its raw data is preserved under
`raw/l010-b07-rd100/`.  The corrected fixture is
`inputs/r1b_output_jj_l010_b07_rd100_loop.cir` and its raw data is under
`raw/l010-b07-rd100-loop/`.

## Matched-case results

All phase values below come directly from `P(...)` in radians, unwrapped only
for adjacent-sample trajectory analysis.  Turns are phase delta divided by
`2*pi`.  Voltage-area values use the same JJ, the same monotonic segment, the
same endpoints, and actual CSV timestamps.

### B_OUT corrected fixture

| case | raw phase range (rad) | unwrapped range (turns) | monotonic segments | complete 2*pi | same-segment voltage area |
|---|---:|---:|---:|---|---|
| read1 | 0.7753975 to 0.7753975 | 0 | 0 | no | undefined: no segment |
| read0 | 0.7753975 to 0.7753975 | 0 | 0 | no | undefined: no segment |
| logical1 READ=0 | 0.7753975 to 0.7753975 | 0 | 0 | no | undefined: no segment |
| logical0 READ=0 | 0.7753975 to 0.7753975 | 0 | 0 | no | undefined: no segment |

The direct same-JJ B_OUT voltage ranges over 94--170 ps were approximately
`[-4.38e-18, 4.28e-21] V` for read1, `[-8.71e-18, 1.30e-17] V` for read0,
`[-4.67e-18, 1.73e-17] V` for logical1 READ=0, and
`[-8.71e-18, 1.14e-17] V` for logical0 READ=0.  These are numerical-zero
levels, not voltage-pulse evidence.  `I(B_OUT)` stayed at `7.000 uA` in every
case; this observation is only a mechanism diagnostic and was not used as the
event criterion.

### B_TRIG guard

| case | monotonic segment | phase delta (turns) | same-JJ voltage area (turns) | area residual (turns) | result |
|---|---|---:|---:|---:|---|
| read1 | 102.9375--110.7000 ps, increasing | 3.9130310 | 3.9130585 | +0.0000275 | complete |
| read0 | 106.5875--108.2125 ps, increasing | 0.1849065 | 0.1849299 | +0.0000233 | incomplete |
| logical1 READ=0 | 94.8125--96.3500 ps, decreasing | -0.00008427 | -0.00008428 | -0.000000003 | incomplete |
| logical0 READ=0 | 94.0375--95.5750 ps, increasing | 0.00025419 | 0.00025422 | +0.000000037 | incomplete |

Thus the trigger guard passes.  Relative to accepted R1a raw evidence, the
corrected loaded read1 B_TRIG segment changed from `3.9437708` to
`3.9130310` turns, while read0 changed from `0.1847573` to `0.1849065` turns.
The independent R1a comparison and the independent raw cross-check both pass.

### Secondary and BVM back-action

The corrected output loop changes the passive secondary loading:

| case | `V(N_SEC)` activity peak | `I(R_SEC_LOAD)` activity deviation |
|---|---:|---:|
| read1 | 76.8387 uV | 0 |
| read0 | 44.7561 uV | 0 |
| logical1 READ=0 | 0.000490 uV | 0 |
| logical0 READ=0 | 0.000760 uV | 0 |

The accepted unloaded R1a values were approximately 66.7685 uV / 5.5640 uA
for read1 and 13.7241 uV / 1.1437 uA for read0.  In the corrected loop,
`I(L_SEC)` and `I(R_SEC_LOAD)` are held at the 7 uA output-bias loop current;
the voltage ratio is only about `1.72`, below the preregistered 2x secondary
guard.  This is evidence of receiver back-action, not evidence of output
activation.

The source probes still retain a read-dependent transient: corrected read1
versus read0 absolute activity peaks are approximately `1.886 mV` versus
`0.442 mV` at SL and `2.118 mV` versus `0.721 mV` at N6; both READ=0 controls
remain sub-microvolt at these probes.  These are activity/separation
observations, not event counts.

JM1/JM2 logical signs remain correct in all four cases.  However, read1 JM2
post-minus-pre changed from the accepted R1a value of about `+0.005032 turns`
to `-0.000459 turns` in this loaded corrected loop.  Its absolute post-state
remains positive, so the sign guard passes, but this drift change means exact
storage preservation is not established.

## Failure mechanism

The corrected raw traces show `V(N_OUT)` following `V(N_SEC)` while
`V(B_OUT)=V(N_OUT)-V(N_SEC)` remains at numerical zero.  At the same time,
`I(B_OUT)=I(I_OUT_BIAS)=7 uA` and `I(R_OUT_DAMP)` is numerical zero.  The
secondary therefore has a state-dependent node-voltage transient, but the
tested B_OUT branch sees it as common mode and receives no differential
drive.  With the output JJ remaining at its zero-voltage state, no phase
trajectory segment exists and no same-segment output voltage area can be
claimed.

This mechanism explains both the initial point and the single allowed
topology correction:

- Initial point: the grounded secondary directly made `V(N_OUT)` follow
  `V(N_SEC)`; `P(B_OUT)` was constant and `I(B_OUT)` was the 7 uA bias.
- Corrected loop: the passive loop was closed through `R_SEC_LOAD`, but the
  tested parallel B_OUT branch still tracked `N_SEC` at `N_OUT`; the output
  JJ remained common-mode and its current stayed at 7 uA.

## Evidence classification

### Observed

- Four solver-complete matched cases for the corrected point; all CSVs are
  finite and time-monotonic, with requested timestep 0.0125 ps and recorded
  intervals from approximately 0.0125 to 0.025 ps.
- B_TRIG read1 has one analyzed complete monotonic segment with phase/area
  agreement; read0 and both controls do not.
- B_OUT has zero unwrapped phase range and no monotonic segment in all four
  cases.
- Corrected B_OUT current is 7 uA in every case; direct B_OUT voltage is
  numerical zero.
- Independent raw cross-check reports `all_comparisons_pass=true`.

### Derived

- `AREA=0.10` output model parameters and damping estimates stated above.
- B_TRIG phase turns, same-segment areas, residuals, source/secondary
  amplitudes, and JM1/JM2 pre/post deltas.
- R1b verdict components: artifact validity PASS, B_TRIG guard PASS,
  storage-sign guard PASS, output activation FAIL, secondary 2x guard FAIL.

### Inference

- The tested output JJ is not differentially excited; its absence of phase
  transition is a topology/drive-path failure in this receiver fixture.
- The corrected output loop introduces bounded but non-negligible loading,
  including the observed read1 JM2 drift change.

### Unknown

- Whether a different series/transformer output topology or a different
  bias/damping point can activate B_OUT while restoring a useful secondary
  current margin.  That is a new R1b design question and was intentionally
  not explored here.
- Whether a later local B_OUT event would be accepted by any downstream JTL;
  no JTL was present.

## Boundary

This report does not call any local B_TRIG activity or hypothetical B_OUT
activity “SFQ delivery”.  No JTL, self-quench loop, T1, Candidate promotion,
or R1c exactly-one study was started.

Primary derived artifacts are `analysis/r1b-analysis.json`,
`analysis/r1a-comparison.json`, and `analysis/independent-crosscheck.json`.
The initial failed-point analysis is preserved as
`analysis/initial-point-analysis.json` and
`analysis/initial-r1a-comparison.json`.
