# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — Phase C report

## Verdict: `WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD`

This is an ideal-current replay of the recorded 12-JSL + W*=12 ps source into the frozen scaled QB. It is not physical BVM→JSL→QB closure.

| case | BJs activity (turns) | BJL1 activity (turns) | BJL2 largest segment (turns) | BJL2 same-segment area (Phi0) | BJL2 complete units | classification |
|---|---:|---:|---:|---:|---:|---|
| wstar12-logical1-read | 20.0742 | 1.20997 | 0.975402 | 0.975411 | 0 | `NO_COMPLETE_EVENT` |
| wstar12-logical0-read | 0.029151 | 0.0187866 | -0.00528549 | -0.00528686 | 0 | `NO_COMPLETE_EVENT` |
| wstar12-logical1-read0-control | 0.000180388 | 7.16993e-05 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` |
| wstar12-logical0-read0-control | 0.000180388 | 7.16993e-05 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` |
| q1-9ps-paper-j1-logical1-read | 14.3749 | 1.07308 | 0.892527 | 0.892537 | 0 | `NO_COMPLETE_EVENT` |
| q1-9ps-paper-j0-logical0-read | 0.0344871 | 0.0230758 | 0.0065587 | 0.00656041 | 0 | `NO_COMPLETE_EVENT` |
| q1-9ps-paper-j1-logical1-read0-control | 0.000180388 | 7.16993e-05 | -2.5051e-05 | -2.5055e-05 | 0 | `NO_COMPLETE_EVENT` |
| q1-9ps-paper-j0-logical0-read0-control | 0.000180388 | 7.16993e-05 | 2.50351e-05 | 2.50412e-05 | 0 | `NO_COMPLETE_EVENT` |

## Observed

- The W*=12 ps source replay retains the recorded time grid, polarity, amplitude, and waveform shape; no normalization, rectification, hold, smoothing, or resampling was applied.
- Q1 9 ps rows are accepted comparator raw; Q0 positive-control status is inherited from PAPER-SL-Q1 and is not reinterpreted here.

## Derived

- Event counts use only continuous unwrapped phase, same-JJ same-segment direct voltage area, and the registered activity/post windows.
- A BJL2 phase range above one would not alone count as an event; the table uses the largest monotonic segment.

## Inference

- The W*=12 ps replay changes the frozen QB operating trajectory only within this ideal source fixture; it does not prove physical current transfer or acceptable back-action.

## Unknown

- No timestep/repeat closure has been run for a candidate point; those are reserved for a later generation gate only if a candidate appears.
