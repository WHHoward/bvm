# QB-Q2A source-decoupled waveform replay diagnosis

## Verdict: `QB_DYNAMIC_WINDOW_MISMATCH`

The source-isolated canonical logical1 replay remains below a complete BJL2 phase/area event under the frozen scaled QB.

This is a requirements/counterfactual replay result. B/C/C0 use ideal voltage-source replay and are not physical source-isolation hardware evidence.

## Core table

| case | BJs units | BJL1 units | BJL2 units | BJL2 largest Δturn | same-segment area (Φ0) | classification |
|---|---:|---:|---:|---:|---:|---|
| A-q0-68p4u-positive-control | 94 | 6 | 6 | 1.09601 | 1.09652 | `A_EXACTLY_ONE_POSITIVE_CONTROL` |
| B-q1-loaded-vsl-replay | 4 | 0 | 0 | -0.0980309 | -0.0980461 | `NO_COMPLETE_EVENT` |
| C-canonical-logical1-vsl-replay | 1 | 0 | 0 | 0.177618 | 0.177629 | `NO_COMPLETE_EVENT` |
| C0-canonical-logical0-vsl-replay | 0 | 0 | 0 | 0.0311286 | 0.0311293 | `NO_COMPLETE_EVENT` |

## Replay input actually delivered to QB

| case | V(IN) min..max (V) | I(Lin) min..max (A) | replay-source current min..max (A) |
|---|---:|---:|---:|
| A-q0-68p4u-positive-control | -0.00123683..0.00370946 | 0..6.84e-05 | 0..6.84e-05 |
| B-q1-loaded-vsl-replay | -0.00103648..0.0018663 | -3.91292e-05..6.04884e-05 | -6.04884e-05..3.91292e-05 |
| C-canonical-logical1-vsl-replay | -0.000541812..0.000904091 | -5.33992e-05..5.84793e-05 | -5.84793e-05..5.33992e-05 |
| C0-canonical-logical0-vsl-replay | -0.000316938..0.000272819 | -2.32591e-05..1.34165e-05 | -1.34165e-05..2.32591e-05 |

## Input provenance and source scale

| source | samples | time range (ps) | V(SL) min..max (V) | companion current min..max (A) |
|---|---:|---:|---:|---:|
| B-q1-loaded | 13599 | 0.0..169.9875 | -0.00103648..0.0018663 | -3.91291e-05..6.04884e-05 |
| C-canonical-logical1 | 13599 | 0.0..169.9875 | -0.000541812..0.000904091 | -4.5151e-05..7.53409e-05 |
| C0-canonical-logical0 | 13599 | 0.0..169.9875 | -0.000316938..0.000272819 | -2.64115e-05..2.27349e-05 |

## JJ phase/area detail

| case | JJ | activity p2p (turn) | largest Δturn | same-segment area (Φ0) | residual (turn) | complete units |
|---|---|---:|---:|---:|---:|---:|
| A-q0-68p4u-positive-control | BJs | 16.4233 | 16.4233 | 16.426 | 0.00267472 | 94 |
| A-q0-68p4u-positive-control | BJL1 | 1.22553 | 1.22553 | 1.22678 | 0.00124927 | 6 |
| A-q0-68p4u-positive-control | BJL2 | 1.09601 | 1.09601 | 1.09652 | 0.000501262 | 6 |
| B-q1-loaded-vsl-replay | BJs | 4.45505 | 4.3716 | 4.37164 | 4.27545e-05 | 4 |
| B-q1-loaded-vsl-replay | BJL1 | 0.365974 | -0.253797 | -0.253845 | -4.79416e-05 | 0 |
| B-q1-loaded-vsl-replay | BJL2 | 0.165495 | -0.0980309 | -0.0980461 | -1.52476e-05 | 0 |
| C-canonical-logical1-vsl-replay | BJs | 1.59846 | 1.22803 | 1.22808 | 5.22721e-05 | 1 |
| C-canonical-logical1-vsl-replay | BJL1 | 0.40007 | -0.339393 | -0.339436 | -4.29794e-05 | 0 |
| C-canonical-logical1-vsl-replay | BJL2 | 0.180525 | 0.177618 | 0.177629 | 1.06091e-05 | 0 |
| C0-canonical-logical0-vsl-replay | BJs | 0.130689 | -0.103503 | -0.103513 | -9.65848e-06 | 0 |
| C0-canonical-logical0-vsl-replay | BJL1 | 0.0827105 | -0.0593864 | -0.0593965 | -1.01376e-05 | 0 |
| C0-canonical-logical0-vsl-replay | BJL2 | 0.0347973 | 0.0311286 | 0.0311293 | 7.61141e-07 | 0 |

## BJL2 event evidence

The event candidate rule is local and exploratory: one same-JJ monotonic phase segment with `|Δturn|≥1`, same-sign direct voltage area, residual within `max(0.05,0.10|Δturn|)`, and bounded post behavior. Peaks, `I>Ic`, and activity range are not event counts.

| case | activity p2p (turn) | post p2p (turn) | post complete units |
|---|---:|---:|---:|
| A-q0-68p4u-positive-control | 1.09601 | 0 | 0 |
| B-q1-loaded-vsl-replay | 0.165495 | 0.000946797 | 0 |
| C-canonical-logical1-vsl-replay | 0.180525 | 9.7562e-05 | 0 |
| C0-canonical-logical0-vsl-replay | 0.0347973 | 1.51197e-06 | 0 |

## Observed

- A uses the Q0 68.4 µA ideal-current pulse and is a positive replay control; B/C/C0 are ideal voltage-source replays of committed source-port waveforms.
- The replay source values retain their original polarity and all source CSV points; no rectification, hold, normalization or amplitude scaling was applied.
- Direct BJs/BJL1/BJL2 P/V/I were saved for every case and the same-JJ phase/area segment analysis was applied.

## Derived

- `P()` is raw phase in radians; reported turns are `ΔP/(2π)`. Voltage areas use the actual CSV time column and the direct junction voltage column.
- A is valid only as a local positive-control replay if all six Q0 pulse windows produce one BJL2 unit and no post candidate.

## Inference

- The canonical waveform, as replayed at the source port, does not meet the frozen QB dynamic window in this counterfactual fixture; this does not prove a universal QB impossibility.

## Unknown / boundary

- Ideal replay removes the physical source impedance and cannot by itself establish a realizable buffer, transformer or conditioner.
- No QB parameter, source waveform, load, BVM, transformer, DCSFQ, JTL or T1 was optimized or modified.
- This bounded result does not establish a universal QB threshold or impossibility of the QB family.
