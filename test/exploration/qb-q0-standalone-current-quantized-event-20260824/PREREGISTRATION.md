# QB-Q0 — standalone QB current-to-quantized-event re-audit

## Scope and question

- Tier: Exploration / historical re-audit; no parameter optimization.
- Parent HEAD: `f43422507195860075d077a5f692e41bf50cc0b0`.
- Main question: under the current phase/radian and same-JJ voltage-area reading, what local phase activity and event candidates does the repository scaled QB produce for ideal current inputs 0, 45, 68.4, and 90 µA?
- No canonical BVM, transformer, DCSFQ, JTL, or T1 is connected.
- Existing final/history files are copied as immutable input snapshots; no existing evidence is overwritten.

## Frozen fixtures

### Current scaled QB (primary)

The primary fixture is the current `circuits/qb/bq_cell.cir`, with its actual `jjmit` model snapshot:

```text
BJs  AREA=.50  (nominal Ic=50 µA)
BJL1 AREA=.36  (nominal Ic=36 µA)
BJL2 AREA=.54  (nominal Ic=54 µA)
Lin=.8 pH, L0=1.323 pH, L1=L2=3.91 pH
RJ1=33 Ω, RJ2=22 Ω, RB=6 Ω, Rload=10 Ω
IBIAS=35 µA
```

The 35 µA bias and the pulse definition reproduce the current `test/final/qb/test_qb_final.cir` reference fixture. The four input levels are the only primary independent variable: `0`, `45`, `68.4`, and `90 µA`.

### Paper-original read-only comparison

The comparison uses the current `circuits/qb/bq_cell_paper.cir` unchanged:

```text
BJs=133 µA, BJL1=112 µA, BJL2=189 µA
Lin=.8 pH, L0=1.323 pH, L1=L2=3.91 pH
RJ1=33 Ω, RJ2=22 Ω, RB=8.5 Ω, Rload=10 Ω
```

Its `IBIAS=90 µA` comes from the repository historical/reference fixture `test/final/single_bvm_qb/test_bvm_paper_bq.cir`. In this Q0 comparison the BVM chain is replaced by the same ideal-current input fixture; this is a provenance-controlled comparison, not a claim that the paper used this standalone ideal-current test.

Paper comparison cases are `0`, `68.4`, and `90 µA`; 68.4 and 90 µA are mandatory reference input levels.

## Stimulus and timing

Every nonzero input uses exactly the historical periodic source:

```text
pulse(0 IIN 10p 1p 1p 5p 50p)
```

The 300 ps stop time reproduces `test_qb_final.cir` and therefore contains six pulse starts at 10, 60, 110, 160, 210, and 260 ps. This is explicitly a periodic regression/re-audit, not a single isolated-pulse proof.

All runs use `.tran 0.1p 300p`, the same output load, model snapshot, bias ramp, and probes. No timestep refinement or parameter sweep is authorized in Q0; therefore the physical classification remains exploratory and is not a global convergence Gate.

Predeclared windows for each pulse start `s`:

- pre: `[s−10 ps, s−1 ps)`;
- pulse activity: `[s, s+25 ps)`;
- post/retrap diagnostic: `[s+25 ps, min(s+49 ps, 300 ps))`.

The same windows are used for the zero-input controls. The final pulse's truncated post window is reported with its actual selected endpoints.

## Probes and phase/area mapping

For each run, directly record `P`, `V`, and `I` for `BJs`, `BJL1`, and `BJL2`, with the element declaration direction used for both phase and direct junction voltage. Also record `IIN`, `IBIAS`, `Lin/L0/L1/L2`, `RB`, `RJ1/RJ2`, `V(OUT)`, and load current.

For every JJ and every pulse activity window:

1. retain raw phase in radians;
2. calculate endpoint `Δphase_rad` and `Δphase_turns=Δphase_rad/(2π)`;
3. split the unwrapped trajectory into monotonic segments;
4. integrate the same direct JJ `V(B...)` over the same segment and actual CSV time;
5. report signed `area_turns` and `area−phase` residual;
6. inspect post behavior and pulse-to-pulse repeatability.

For descriptive Q0 counting only, a `phase/area candidate` requires `|Δphase| ≥ 1 turn`, matching area sign, and residual within the task-local diagnostic rule `max(0.05 turn, 10% of |Δphase|)`. This rule is explicitly `UNFROZEN` and cannot be promoted to a universal SFQ tolerance. Segments failing it remain reported as activity/phase candidates, not accepted events.

## Output categories

The core table reports `N_phase/area_candidates` per input level and JJ, followed by a descriptive output classification:

- `ZERO_EVENT`: no qualifying BJL2 candidate in the six pulse windows and no qualifying zero-input event;
- `EXACTLY_ONE`: one qualifying BJL2 candidate in every nonzero pulse window, no post/free-running candidate, and phase/area evidence is consistent;
- `MULTI_EVENT`: more than one qualifying BJL2 candidate in a pulse window or more than one propagated local candidate where one was requested;
- `FREE_RUNNING`: qualifying events occur without an input pulse or post windows do not return to a bounded state;
- `NONREPEATABLE`: pulse windows disagree (some zero, some one, or varying counts);
- `INCONCLUSIVE_AREA`: phase candidates exist but the area cross-check fails the task-local diagnostic rule;
- `NO_COMPLETE_EVENT`: valid runs with only sub-turn responses.

These are local exploratory labels. `EXACTLY_ONE` here means one local BJL2 phase/area candidate per ideal input pulse; it does not mean downstream SFQ delivery and does not restore the superseded historical `fast_events` claim.

## Stop and interpretation rules

- Do not use `scripts/sfq_metrics.py`, `fast_events`, old JSON, voltage peaks, or current-above-Ic as event evidence.
- Do not alter AREA, bias, inductance, resistance, load, pulse timing, or model.
- Do not infer a universal threshold from the four scaled input points.
- A scaled exactly-one window is evidence for a frozen Q0 point and permits a separately authorized QB-Q1 BVM cascade; it is not itself a BVM receiver result.
- If no exactly-one window appears, report the measured bounded result and stop. Do not automatically sweep or retune.
