# PAPER-SL-Q1 — replay paper-JSL-shaped sense current into frozen scaled QB

## Status and scope

This is a requirements/counterfactual Exploration.  It does not connect the
canonical BVM to QB, and it does not modify the canonical BVM, the paper-JSL
load fixture, or the frozen scaled QB cell.  The paper-JSL trajectories are
replayed by an ideal current source; this tests waveform compatibility only,
not a realizable BVM-to-QB interface.

Registration time: `2026-08-24T03:38:44+08:00`  
Parent HEAD: `0bf84c438d4890b7ed095fe526711eafab520ada`

## Question

Does the actual current waveform produced by the accepted external-series
`12 x AREA=3.2` paper-JSL load drive the frozen scaled QB into the same local
quantized regime as the standalone 68.4 µA positive control?

The primary comparison is:

```text
paper-JSL logical1 current -> N(BJs), N(BJL1), N(BJL2)
```

against logical0, both READ=0 controls, and the independent Q0 68.4 µA
positive control.

## Frozen QB

The exact scaled cell is copied from the accepted QB-Q2A/QB-Q0 fixture:

| element | value |
|---|---:|
| BJs AREA | 0.50 |
| BJL1 AREA | 0.36 |
| BJL2 AREA | 0.54 |
| IBIAS | 35 µA |
| Lin | 0.8 pH |
| L0 | 1.323 pH |
| L1, L2 | 3.91 pH |
| RJ1 | 33 Ω |
| RJ2 | 22 Ω |
| RB | 6 Ω |
| output load | 10 Ω |

The repository `jjmit.cir` model is copied byte-for-byte into `inputs/`.

## Input definitions

Five runs are registered: one separate positive control plus the four matched
paper-JSL cases.

1. **Q0 positive control:** the exact 68.4 µA ideal current pulse from
   `QB-Q0`, `pulse(0 68.4u 10p 1p 1p 5p 50p)`.
2. **logical1 + READ:** `I(B_LD1)` from
   `PAPER-SL-L0/raw/logical1-read/run-01.csv`.
3. **logical0 + READ:** `I(B_LD1)` from
   `PAPER-SL-L0/raw/logical0-read/run-01.csv`.
4. **logical1 + READ=0:** `I(B_LD1)` from
   `PAPER-SL-L0/raw/logical1-read0-control/run-01.csv`.
5. **logical0 + READ=0:** `I(B_LD1)` from
   `PAPER-SL-L0/raw/logical0-read0-control/run-01.csv`.

The source builder verifies that `I(B_LD1)` through `I(B_LD12)` are the same
series current to numerical precision, then copies every original time point
and current value into a replay snapshot.  No rectification, hold/stretch,
normalization, resampling, polarity change, or amplitude scaling is applied.
The positive-current convention is retained: positive JSL current leaves the
BVM-side `SL1` node and is replayed by `I_REPLAY 0 IN` into the QB input.

The four BVM-derived replays use the original `0.0125 ps` time grid and stop
at the original `170 ps`.  The Q0 positive control retains its original
`0.1 ps`, `300 ps` fixture.

## Measurements and event rule

For `BJs`, `BJL1`, and `BJL2`, record direct `P/V/I`, continuous unwrapped
phase, monotonic segments, and same-JJ/same-segment voltage area divided by
`Phi0`.  A complete local event requires a monotonic phase segment of at least
one turn with same-segment voltage-area consistency.  Voltage peak, current
peak, derivative activity, or phase range alone is not an event.

For every case also record post-window boundedness/retrap and any additional
complete segments.  The Q0 control must reproduce one bounded BJL2 event per
pulse before the paper-JSL cases are interpreted.

## Pre-registered dispositions

- `PAPER_JSL_WAVEFORM_MATCHES_QB_ONE_SHOT`: logical1 BJL2 exactly one,
  logical0 and both controls zero, bounded post behavior.
- `PAPER_JSL_QB_MULTIEVENT`: logical1 has more than one complete BJL2 event
  or additional complete post events.
- `PAPER_JSL_QB_NONSEL`: logical0 or a READ=0 control has a complete BJL2
  event.
- `PAPER_JSL_QB_SUBTHRESHOLD`: logical1 remains below a complete BJL2 event
  while all matched negatives remain zero.
- `REPLAY_FIXTURE_INVALID`: the independent Q0 positive control does not
  reproduce its accepted one-event-per-pulse behavior.
- `INCONCLUSIVE`: artifact, phase/area, or post-window evidence is not
  sufficient for one of the above.

No result is a claim about physical `BVM -> 12 JSL -> QB` operation.  No QB
parameter adjustment, JSL change, physical BVM connection, JTL, or T1 is
authorized by this registration.

