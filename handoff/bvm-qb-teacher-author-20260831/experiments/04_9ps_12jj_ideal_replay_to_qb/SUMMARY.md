# PAPER-SL-Q1 summary

## Verdict

`PAPER-SL_QB_SUBTHRESHOLD`

The accepted paper-JSL external-load logical1 current replay produced strong
nonlinear BJs activity, but the frozen scaled QB did not produce a complete
BJL1 or BJL2 phase/area-consistent event. The logical0 replay and both READ=0
controls produced zero complete events. The Q0 68.4 µA standalone positive
control reproduced the expected six bounded BJL2 one-event pulses.

## Main comparison

| input | BJs complete units | BJL1 complete units | BJL2 complete units | BJL2 largest segment / area | result |
|---|---:|---:|---:|---:|---|
| Q0 68.4 µA ideal pulse | 94 total | 6 total | 6 total | 1.09601 / 1.09652 turn | positive control valid |
| paper-JSL logical1 + READ | 14 | 0 | 0 | 0.892527 / 0.892537 turn | subthreshold at BJL2 |
| paper-JSL logical0 + READ | 0 | 0 | 0 | 0.0065587 / 0.00656041 turn | zero complete event |
| paper-JSL logical1 + READ=0 | 0 | 0 | 0 | −2.5051e−5 / −2.5055e−5 turn | zero complete event |
| paper-JSL logical0 + READ=0 | 0 | 0 | 0 | 2.50351e−5 / 2.50412e−5 turn | zero complete event |

The Q0 BJs total is intentionally not used as a one-shot system criterion:
the standalone positive fixture is only the registered check that the frozen
QB can reproduce its accepted BJL2 local event. This Exploration has no JTL,
so no result is downstream SFQ-delivery evidence.

## Interpretation boundary

Observed: raw PAPER-SL-L0 JSL branch current was copied point-for-point and
the twelve series branch-current columns were equal within the recorded
floating-point tolerance. No rectification, hold, rescaling, normalization,
or polarity change was applied.

Derived: the paper-JSL-shaped logical1 waveform is sufficient to drive the
front BJs into multi-turn local activity in the frozen replay fixture, but its
largest BJL2 monotonic segment remains below one turn. The logical0/control
separation remains clear.

Inference: the loaded paper-JSL waveform does not match the frozen scaled
QB's bounded one-shot input window under this ideal current replay. This is a
waveform-compatibility result, not evidence that the physical
`BVM -> 12 JSL -> QB` interface will have the same source impedance or loading.

Unknown: the combined physical BVM/JSL/QB load-line, source back-action, and
whether an internal-LSL realization differs from this accepted external-load
waveform were not tested.

## Visualization

The previous PAPER-SL-L0 four cases were visualized in
`plots/paper-sl-l0-classic/` with the repository classic `josim-plot2.py`
`sep_comb`, dark-theme, `-j 2pi` convention. The plots are descriptive only
and do not alter the accepted raw evidence or event verdict.
