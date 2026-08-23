# QB-Q2C — uniform junction-scale bracketing under frozen canonical replay

## Research question

With the Q2A canonical logical1/logical0 source-isolated voltage replay held fixed, does uniformly scaling the three QB junction areas and central bias create a selective BJL1/BJL2 complete-event region while logical0 and READ=0 controls remain zero?

## Primary hypothesis and alternatives

- Primary hypothesis: reducing all junction/current classes together may move the already state-selective BJs response into a BJL1/BJL2 quantizing regime.
- Alternative 1: the uniform scaling preserves the same dynamic mismatch, so BJs remains active while BJL1/BJL2 stay sub-turn.
- Alternative 2: fixed external RJ1/RJ2/RB and inductances break scale similarity and cause read0/control activity, multifire or free-running before selective output appears.

## Frozen conditions

- Canonical source-isolated logical1/logical0 replay snapshots are copied byte-for-byte from QB-Q2A; no physical BVM is connected.
- `Lin=.8 pH`, `L0=1.323 pH`, `L1=L2=3.91 pH`.
- `RJ1=33 Ω`, `RJ2=22 Ω`, `RB=6 Ω`, output load `10 Ω`.
- Same `jjmit.cir` model as QB-Q0/Q1/Q2A/Q2B.
- s=1 is an existing Q2A/Q2B reference and is not rerun.
- No transformer, DCSFQ, JTL, T1, rectifier, hold or source reshaping.

## New points and execution order

Only these new scales are authorized, in descending order:

```text
s=0.85: BJs/BJL1/BJL2 AREA = 0.425/0.306/0.459; IBIAS = 29.75 µA
s=0.70: BJs/BJL1/BJL2 AREA = 0.350/0.252/0.378; IBIAS = 24.50 µA
s=0.55: BJs/BJL1/BJL2 AREA = 0.275/0.198/0.297; IBIAS = 19.25 µA
```

For each scale, run in this order:

1. logical1 + READ=0 control;
2. logical0 + READ=0 control;
3. logical1 + canonical READ replay;
4. logical0 + canonical READ replay.

If either READ=0 control shows startup/free-running or a complete BJs/BJL1/BJL2 event, stop that direction and do not continue to a smaller scale. If a completed scale is nonselective or multifires, do not add points.

## Measurements and event rule

For BJs/BJL1/BJL2 record direct `P(...)`, same-JJ direct `V(...)`, `I(...)`, Lin/L0/L1/L2/RB/RJ1/RJ2 branches, input/output branches and continuous unwrapped phase. A complete local event requires a continuous monotonic same-JJ phase segment of at least one turn, same-segment direct voltage-area consistency using the actual CSV time column, and bounded post behavior. Current above Ic, voltage peak and phase activity alone are not event evidence.

## Predeclared outcomes

- `UNIFORM_SCALE_SELECTIVE_EVENT`: read1 has a bounded complete BJL1/BJL2 event, read0 and controls have zero complete events.
- `UNIFORM_SCALE_MULTIEVENT`: read1 has more than one complete BJL1/BJL2 event or is unbounded.
- `UNIFORM_SCALE_NONSEL_OR_FREE_RUNNING`: read0/control has a complete event, free-runs or loses the required separation.
- `UNIFORM_SCALE_NO_OUTPUT_EVENT`: all tested new scales remain bounded with no complete read1 BJL1/BJL2 event.
- `INCONCLUSIVE`: artifact, direction, phase/area or post-window evidence is insufficient.

This is an Exploration result, not a candidate or physical-BVM claim. No automatic AREA/bias/routing modification follows it.
