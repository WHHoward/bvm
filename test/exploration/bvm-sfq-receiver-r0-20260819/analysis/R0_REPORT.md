# BVM -> SFQ receiver R0 trigger-discrimination Exploration

> **VERDICT CORRECTION (2026-08-19):** This report's original `R0 PASS`
> wording is superseded by [R0_VERDICT_CORRECTION.md](R0_VERDICT_CORRECTION.md).
> The raw CSV artifacts are unchanged. The current result is `R0 PARTIAL`:
> `R0-A threshold discrimination PASS`; `R0-B complete trigger switching
> NOT_YET`. The read1 B_TRIG activity range is only 3.672452 rad = 0.584488889
> turns, and no monotonic segment reaches 2pi.

**Created:** 2026-08-19T04:17:52+08:00
**Tier:** Exploration / EXPLORATORY
**Route:** primary canonical SL output
**Solver:** build/josim-cli v2.7.2837d13, SHA-256
48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2
**Numerical condition:** requested dt=0.0125 ps, stop=169.9875 ps
**Current local verdict:** **R0 PARTIAL**; see the correction above

This is not a Candidate result, not an INTERFACE_GATE_V1 result, and not an
SFQ-count or downstream-JTL claim.

## 1. Research question and scope

Question: can a minimum biased-JJ receiver clearly switch for canonical logical
1 +READ while logical 0 +READ does not switch, with matched READ=0 controls?

Only threshold discrimination was tested. Exactly one SFQ, self-quench, output
JTL reception, robustness, and hardware behavior were deliberately left for
R1 or later work. The canonical BVM topology was not edited. The copied
inputs/bvm_cell.cir hash is identical to circuits/bvm/bvm_cell.cir.

The four matched cases were:

| Case | Frozen BVM state | READ |
|---|---:|---|
| read1 | logical 1 (+100 uA WL+BL init) | canonical +100 uA WL+SE, 96–105 ps |
| read0 | logical 0 (-100 uA WL+BL init) | the same canonical positive READ |
| logical1-read0-control | logical 1 | READ amplitude zero |
| logical0-read0-control | logical 0 | READ amplitude zero |

## 2. Topology

    canonical BVM SL -- R_IN=12 ohm -- N_TRIG -- B_TRIG -- ground
                                          ↑
                               I_TRIG_BIAS = +10 uA

B_TRIG is the only receiver junction. Its direct same-junction probes are
P(B_TRIG|XTRIG) and V(B_TRIG|XTRIG); I(B_TRIG|XTRIG),
I(R_IN|XTRIG), and I(I_TRIG_BIAS|XTRIG) are also recorded.

No external parallel shunt was added. The 12 ohm element is the series input
resistance; the trigger's intrinsic RCSJ model supplies its normal/subgap
damping.

## 3. Actual JJ model and parameter basis

The included model is:

    .model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)

JoSIM's AREA implementation in src/JJ.cpp multiplies Ic and C, and divides
RN and R0; an explicit IC= would replace the area multiplier. Therefore the
designed trigger instance is:

| Quantity | Value | Provenance |
|---|---:|---|
| AREA | 0.50 | designed initial point |
| Ic | 50 uA | 0.1 mA × AREA |
| RN | 32 ohm | 16 ohm / AREA |
| R0 | 320 ohm | 160 ohm / AREA |
| C | 35 fF | 0.07 pF × AREA |
| external input resistance | 12 ohm | designed load interface |
| bias current | +10 uA | designed; below Ic |
| explicit parallel shunt | none | topology fact |

Using the actual model values, the derived RCSJ damping parameter
beta_c = 2*pi*Ic*RN^2*C/Phi0 is approximately 5.4451 for the trigger. The
earlier `0.0544` value in the historical c760c13 text was an arithmetic error.
This is a model-derived damping calculation, not a new frozen acceptance
tolerance.

For reference, the unchanged BVM instances are JM1 AREA=1.2
(Ic=120 uA), JM2 AREA=1.4 (Ic=140 uA), and JS1/JS2 AREA=0.74
(Ic=74 uA), with the same area scaling.

## 4. Analytic initial point

The prior matched 12-ohm BVM observations supplied the design midpoint:

| Quantity | Prior observed value |
|---|---:|
| logical 1 SL current scale | about 75.3 uA |
| logical 0 SL current scale | about 26.4 uA |
| predicted logical 1 drive including bias | about 85.3 uA |
| predicted logical 0 drive including bias | about 36.4 uA |
| trigger Ic | 50 uA |

The loaded reruns, rather than those prior values, determine the actual
discrimination. No global or blind sweep was run.

## 5. Raw artifact QA

All four JoSIM runs exited successfully through run_cases.sh; all four stderr
files are empty. Each CSV has 13,599 data rows, a strictly increasing time
column, finite values, and the expected 0–169.9875 ps span. The actual CSV
spacing is 0.0125–0.025 ps; the voltage-area calculation uses that actual
time column. Artifact status is **VALID** for all four cases.

Raw files and the structured calculation are under:

- raw/<case>/run-01.csv
- analysis/r0-analysis.json
- inputs/*.cir
- logs/*.stdout.txt and logs/*.stderr.txt
- analysis/sha256sums.txt contains the final artifact hash inventory (excluding
  the inventory file itself).

The calculations preserve raw phase in radians. Derived turns are only
delta_phase_rad/(2*pi). The same-JJ voltage area uses the actual CSV time
column and V(B_TRIG|XTRIG) over the declared 94–130 ps activity window.
No scripts/sfq_metrics.py field is used.

## 6. Trigger discrimination

The table reports phase range as a switching-activity descriptor, not an
event count. phase net and V-area are signed net quantities over the same
activity window.

| Case | Trigger phase range | Trigger |V| peak | phase net | same-JJ V area | positive input peak | positive JJ drive |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 3.672 rad (0.5845 turns) | 0.908 mV @ 109.25 ps | +0.07736 rad (+0.01231 turns) | +0.01231 turns | +66.29 uA | +76.29 uA |
| read0 | 1.143 rad (0.1819 turns) | 0.370 mV @ 107.425 ps | +0.1508 rad (+0.02400 turns) | +0.02401 turns | +17.22 uA | +27.22 uA |
| logical1 READ=0 | 0.000493 rad | 0.169 uV | -0.000221 rad | -0.0000352 turns | +0.00020 uA | +10.0002 uA |
| logical0 READ=0 | 0.001210 rad | 0.431 uV | +0.000463 rad | +0.0000736 turns | +0.00045 uA | +10.0004 uA |

The loaded current relation is directly observed as:

    read0 positive drive = 27.22 uA < trigger Ic 50 uA
    read1 positive drive = 76.29 uA > trigger Ic 50 uA

In read1, the trigger develops a large, delayed multi-lobe voltage/phase
excursion and then returns toward its superconducting baseline. In read0, the
response is limited to a smaller edge-dominated transient. The read1
excursion is not a complete 2pi phase transition: its activity range is only
3.672452 rad = 0.584488889 turns, and its net phase and voltage area are only
about 0.0123 turns because positive and negative voltage lobes partly cancel.

The phase/area agreement is a local evidence check for the same B_TRIG
junction and the same window. It supports a real local transition rather than
an output-column naming artifact; it does not prove downstream delivery.

## 7. BVM output and back-action

With the trigger attached, the SL and N6 responses remain state-discriminating:

| Quantity in 94–130 ps | read1 | read0 |
|---|---:|---:|
| positive V(SL1) peak | +1.287 mV | +0.376 mV |
| positive I(L_SL|XBVM1) peak | +66.29 uA | +17.22 uA |
| positive V(N6|XBVM1) peak | +1.884 mV | +0.593 mV |
| P(JS1) activity range | 21.275 rad (3.386 turns) | 1.493 rad (0.238 turns) |
| P(JS2) activity range | 20.786 rad (3.308 turns) | 2.383 rad (0.379 turns) |

The negative read edge also appears in the signed traces
(I(L_SL) minimum about -28.38 uA for read1 and -22.32 uA for read0);
it is not treated as an additional trigger event.

Storage signatures in the declared PRE=[80,90] ps and
STORAGE_POST=[140,150] ps windows are:

| Case | JM1 post-pre | JM2 post-pre |
|---|---:|---:|
| read1 | -0.001401 rad | +0.005015 rad |
| read0 | -0.000008 rad | -0.004007 rad |
| logical1 READ=0 | +0.000014 rad | -0.000303 rad |
| logical0 READ=0 | -0.000014 rad | +0.000291 rad |

These are small relative to the stored phase signatures in this fixture and
do not show an obvious storage-state destruction. This is a bounded
back-action observation, not a state-preservation Gate.

## 8. Bias-only and free-running checks

Both READ=0 controls leave the trigger at the 10-uA bias level: trigger phase
range is below 0.0013 rad, and |V(B_TRIG)| stays below 0.431 uV in the
activity window. Thus the bias alone does not trigger the receiver.

After the read1 response, the trigger voltage decays: the absolute peak is
about 0.135 mV in 140–150 ps and 0.090 mV in 150–170 ps, while the input
branch current is sub-uA. This is a decaying ring in the recorded post-window,
not an observed sustained free-running oscillation. It is not evidence that
an R1 one-shot has been achieved.

## 9. Evidence classification

### Observed

- The four raw CSV artifacts are valid and matched in topology, model, bias,
  timing, and receiver.
- The loaded positive-drive current is above 50 uA for read1 and below 50 uA
  for read0.
- Direct same-JJ trigger voltage and phase show a much larger read1 excursion
  than read0, but not a complete 2pi monotonic phase segment.
- Both READ=0 controls remain at bias-only behavior.
- Loaded BVM SL/N6 and JS1/JS2 remain strongly separated between read1 and
  read0.
- JM1/JM2 post-minus-pre changes are small in the recorded windows.

### Derived

- At this operating point, the SL route supplies a usable trigger-level
  threshold margin: 27.22 < 50 < 76.29 uA.
- Same-JJ phase and voltage-area net values agree in the registered activity
  window to the displayed precision.
- The trigger response is not explained by bias-only startup in these controls.

### Inference

- The minimum SL receiver is sufficient for R0 trigger discrimination under
  the recorded model, load, timing, and timestep.
- The read1 response is a finite local phase/voltage excursion below the
  complete-switching criterion; the read0 response is edge-dominated and has
  no complete 2pi monotonic phase segment.

### Unknown

- Exactly-one-SFQ behavior and any SFQ count.
- Whether a downstream standard JTL receives a valid pulse.
- Self-quenching under an output load or for a longer simulation.
- Timestep/convergence stability and parameter/temperature/load margin.
- Whether a different receiver bias or N6 route is preferable.
- Hardware behavior or process-yield implications.

## 10. R0 verdict and R1 suggestion

**R0: PARTIAL.**

- **R0-A threshold discrimination: PASS.** The SL route separates loaded
  logical1/read1 from logical0/read0, both READ=0 controls remain inactive, and
  the bounded BVM back-action checks remain positive.
- **R0-B complete trigger switching: NOT_YET.** The read1 B_TRIG trace has no
  monotonic segment with at least 2pi phase evolution. A phase range below 2pi
  is not called complete switching.

R1 remains blocked until the separately defined R0b complete-trigger closure
criterion is met. Self-quench, output isolation, and JTL work are not
implemented here.
