# QB-Q1 — canonical BVM → frozen scaled QB compatibility

## Scope and question

- Tier: Exploration; one frozen receiver point, no optimization or sweep.
- Parent HEAD: `f800df0eab8c9402ec521d0c9e96fbc6d7a79e32`.
- Main question: what unmodified canonical BVM SL waveform and source loading does the frozen QB-Q0 scaled cell actually receive, and does it produce selective local BJL2 quantization?
- Canonical BVM and its logical/read semantics are not modified.
- No transformer, rectifier, hold element, normalization, DCSFQ, JTL, or T1 is connected.

## Frozen source semantics

The canonical definitions come from `docs/research/BVM_LOGICAL_SEMANTICS_V1.md`:

- logical 1: WL and BL initialization at `+100 µA`;
- logical 0: WL and BL initialization at `−100 µA`;
- canonical READ: positive WL/SE read, with the frozen `96–105 ps` plateau;
- READ=0 controls omit the read pulse while retaining the same state initialization.

The four cases use the same source PWL timing as the accepted BVM read fixtures:

1. `logical1-read0-control` — run first;
2. `logical1-read` — run only if the first control is bounded and source-stable;
3. `logical0-read`;
4. `logical0-read0-control`.

## Frozen QB point

The exact scaled cell from QB-Q0 is used without changes:

```text
BJs AREA=.50       Ic=50 µA
BJL1 AREA=.36      Ic=36 µA
BJL2 AREA=.54      Ic=54 µA
Lin=.8 pH, L0=1.323 pH, L1=L2=3.91 pH
RJ1=33 Ω, RJ2=22 Ω, RB=6 Ω, IBIAS=35 µA
R_LOAD OUT_Q 0 10 Ω
```

The actual `jjmit` model snapshot is included in `inputs/jjmit.cir`; AREA also changes C, RN and R0 according to that model. No Q0 input waveform is replayed or reshaped.

## Topology and loading

The only interface is direct galvanic connection:

```text
canonical BVM SL1 ── QB IN/Lin ── BJs/BJL1/BJL2 loop ── OUT_Q/R_LOAD
```

The BVM internal `R_SL=12 Ω` and `L_SL=0.4 pH` remain in the canonical BVM. There is no added SL termination or matching element. `V(SL1)` is both the BVM output node and the QB input-node voltage; `I(Lin|XBQ)` is the QB input branch current, directed from QB `IN` toward its internal node `1`.

## Simulation and windows

- `.tran 0.0125p 170p`;
- pre/settled reference window: `[80,90) ps`;
- causal READ activity window: `[94,130) ps`;
- post/retrap window: `[150,170] ps`;
- all four cases use identical timestep, stop time, model, load and probes.

For each BJs/BJL1/BJL2, retain raw continuous phase, direct same-JJ voltage/current, unwrapped phase, monotonic segments, same-segment `∫Vdt/Φ0`, onset and post behavior. A local candidate uses the Q0 exploratory diagnostic rule: `|Δturn|≥1`, matching phase/area sign, and residual within `max(0.05, 0.10|Δturn|)` turn. This is local and unfrozen, not a universal SFQ tolerance.

## Source/storage guards

Record `V(SL1)`, `V(N6|XBVM1)`, `I(L_SL|XBVM1)`, `JM1/JM2`, and `JS1/JS2`. Compare each loaded case to the copied canonical no-receiver references in `reference/canonical/`:

- logical 1 + READ;
- logical 0 + READ;
- logical 1 + READ=0;
- logical 0 + READ=0.

The comparison is differential to the canonical baseline; absolute JS1/JS2 running in canonical logical1+READ is not by itself receiver back-action.

## Stop rule and dispositions

If `logical1-read0-control` shows startup/free-running, a complete BJL2 control event, or obvious source/storage instability, stop before running the other three cases. Otherwise complete the matched matrix.

Possible local Exploration dispositions:

- `QB_BVM_LOCAL_ONE_SHOT_PASS`: read1 BJL2 exactly one complete local phase/area event, read0/control zero, bounded post behavior, and source/storage guards acceptable;
- `QB_BVM_SUBTHRESHOLD`: read1 remains below a complete BJL2 event;
- `QB_BVM_MULTIEVENT`: read1 produces more than one complete BJL2 event;
- `QB_BVM_NONSEL`: read0 or controls produce complete event(s);
- `QB_SOURCE_BACKACTION_FAILURE`: receiver loading materially damages canonical source/storage behavior;
- `FREE_RUNNING` or `INCONCLUSIVE` as applicable.

These labels apply only to this frozen model, direct galvanic interface, input timing, load, timestep and local diagnostic rule. No automatic parameter change or follow-up QB sweep is authorized.
