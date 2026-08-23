# QB-Q2B — central-bias bracketing under frozen canonical replay

## Main question

With the Q2A canonical source-isolated voltage replay held fixed, does a local `IBIAS` bracket around 35 µA create a selective read1 BJL1 complete transition while logical0 and READ=0 controls remain zero?

## Frozen conditions

- QB-Q2A scaled `bq_cell.cir` and `jjmit.cir` unchanged;
- BJs AREA `.50`, BJL1 AREA `.36`, BJL2 AREA `.54`;
- `Lin=.8 pH`, `L0=1.323 pH`, `L1=L2=3.91 pH`;
- `RJ1=33 Ω`, `RJ2=22 Ω`, `RB=6 Ω`, output load `10 Ω`;
- canonical source-isolated voltage replay waveforms unchanged;
- no BVM, transformer, DCSFQ, JTL or T1;
- only independent variable: `IBIAS`.

## Selected points

The analytic precheck selected only `IBIAS=30 µA` and `IBIAS=40 µA`. The accepted Q2A `35 µA` result is the reference baseline and is not rerun.

## Matched cases and order

For each bias point, the order is:

1. logical1 + READ=0 canonical control;
2. logical0 + READ=0 canonical control;
3. logical1 + canonical READ replay;
4. logical0 + canonical READ replay.

The first two controls are the guard cases. If either control is unstable, free-running or has a complete BJL1/BJL2 transition, stop that bias point and do not run its READ cases.

## Measurements and event rule

For BJs/BJL1/BJL2 record raw continuous `P/V/I`, unwrapped phase, monotonic segments, same-JJ same-segment `∫Vdt/Φ0`, onset and post behavior. Also record `I(RB)`, `I(L1)`, `I(L2)`, `I(Lin)`, `I(RJ1)`, `I(RJ2)`, `V(IN)`, `V(OUT)`.

Complete event evidence requires a continuous monotonic same-JJ phase segment of at least one turn, same-sign same-segment voltage area consistency, and bounded post/retrap. `I>Ic`, voltage peak and phase activity alone are not event evidence.

## Dispositions

- `BJL1_SELECTIVE_EVENT` — read1 has a bounded complete BJL1 event; read0 and controls have zero complete BJL1/BJL2 events;
- `BIAS_BRACKET_NO_BJL1_EVENT` — selected points remain subthreshold with bounded controls;
- `NONSELECTIVE_OR_FREE_RUNNING` — control/read0 event or unbounded activity;
- `INCONCLUSIVE` — artifact, phase/area or post-window evidence is insufficient.

No automatic BJL1 AREA, BJs AREA, BJL2, load, inductance or further bias sweep follows this point set.
