# BVM_LOAD_QB_MATRIX_V1

## Purpose

This is an exploratory, four-operating-point matrix for the user-authorized
physical route:

BVM SL -> N series JSL junctions -> QB IN -> scaled QB -> R_LOAD

The matrix covers 9 ps and 13 ps positive READ widths with either 12
jjmit area=3.2 junctions (model nominal approximately 320 uA each) or 8
jjmit area=5.0 junctions (model nominal approximately 500 uA each).
There is no JSL bypass, magnetic coupling, JTL, or T1 in this Exploration.

## Study mode and question

- mode: exploratory
- primary question: Does the physical BVM -> JSL -> QB route preserve a
  state-dependent source waveform and produce a corresponding QB output at
  either registered read width and JSL load configuration?
- primary hypothesis: the 12x320 and 8x500 loads produce different source and
  QB trajectories; at least one physical point may show state-selective QB
  output activity.
- alternatives:
  - the JSL load changes the BVM source/load-line before the QB input;
  - the QB input network receives a state-dependent waveform but its internal
    transfer or output load does not produce a large output response;
  - a no-read control or read0 response is non-negligible, indicating a
    protocol, initialization, or free-running issue;
  - the result changes with timestep and is numerically inconclusive.

## Matrix

Operating points:

| read width | JSL load | JSL model | physical endpoint |
|---:|---:|---|---|
| 9 ps | 12 junctions | area=3.2 (~320 uA each) | GND for source fixture; QB IN for physical fixture |
| 9 ps | 8 junctions | area=5.0 (~500 uA each) | GND for source fixture; QB IN for physical fixture |
| 13 ps | 12 junctions | area=3.2 (~320 uA each) | GND for source fixture; QB IN for physical fixture |
| 13 ps | 8 junctions | area=5.0 (~500 uA each) | GND for source fixture; QB IN for physical fixture |

Each operating point has four matched roles:

1. logical1_read: +100 uA WL+BL initialization and canonical positive
   WL+SE READ;
2. logical0_read: -100 uA WL+BL initialization and the same positive
   WL+SE READ;
3. logical1_no_read_control: logical1 initialization with READ disabled;
4. logical0_no_read_control: logical0 initialization with READ disabled.

The READ starts at 96 ps. Its plateau ends at 105 ps or 109 ps for the 9 ps
or 13 ps condition, respectively; the fall is represented by the next 1 ps
knot. All cases use the same 170 ps stop time and requested 0.0125 ps step.

The three fixtures are:

1. source: BVM SL -> JSL -> GND; its I(B_LD1) is the source waveform;
2. ideal replay: the corresponding source I(B_LD1)(t) is copied into
   I_REPLAY at QB IN without reshaping, holding, scaling, or interpolation;
3. physical cascade: BVM SL -> JSL -> QB IN, with the JSL endpoint not
   separately grounded.

The basic matrix is 3 fixtures x 4 operating points x 4 roles = 48 runs.

## Frozen QB and numerical settings

The QB snapshot is the repository scaled cell:

- BJs/BJL1/BJL2 area = 0.50/0.36/0.54;
- Lin/L0/L1/L2 = 0.8/1.323/3.91/3.91 pH;
- RJ1/RJ2/RB = 33/22/6 ohm;
- IBIAS = 35 uA;
- R_LOAD = 10 ohm from OUT to ground.

The solver is the recorded build/josim-cli v2.7.2837d13. The primary
requested step is 0.0125 ps and the stop time is 170 ps. This Exploration does
not claim timestep convergence; if a candidate or boundary point is worth
promoting, a separate preregistered 0.025/0.0125/0.00625 ps check is required.

## Predeclared observations

The raw data must retain direct phase, voltage, and current columns for the
BVM, every JSL junction, and BJs/BJL1/BJL2, plus QB V(OUT) and I(R_LOAD).
The key views will show only the source branch, JSL endpoint/current, QB input,
the BJs->BJL1->BJL2 trajectory, and the QB output.

- VALID: solver/CSV/time/column/hash QA passes.
- FAIL: data are valid but a registered required observation is absent or a
  guard is explicitly violated.
- INCONCLUSIVE: missing/ambiguous signal mapping, unstable post window, or
  timestep-dependent classification.
- INVALID: failed artifact QA; this is not a circuit failure.

P(...) is raw phase in radians. Any displayed P/(2*pi) is continuous
phase turns and is not an SFQ counter. A local BJL2 phase excursion is not by
itself downstream SFQ delivery; the output has no JTL in this run.

