# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — Phase B report

## Verdict

`PAPER_JSL_WSTAR_SOURCE_VALID`: the W*=12 ps external 12-JSL source stage remains bounded and state-selective, so it passes the registered gate into Phase C ideal replay. This is not a QB event claim and not physical BVM→JSL→QB closure.

## JSL local evidence

| case | JSL current spread | largest B_LD1 segment (turns) | same-segment area (Phi0) | all-JSL complete units | read1/read0 source separation |
|---|---:|---:|---:|---:|---|
| 9ps-logical1-read | 0 µA | -0.0543798 | -0.0543884 | 0 | see source table |
| 9ps-logical0-read | 0 µA | 0.00370884 | 0.00370977 | 0 | see source table |
| 9ps-logical1-read0-control | 1e-12 µA | -2.6477e-05 | -2.64829e-05 | 0 | see source table |
| 9ps-logical0-read0-control | 1e-12 µA | 2.6477e-05 | 2.64829e-05 | 0 | see source table |
| 12jsl-12ps-logical1-read | 0 µA | -0.0501151 | -0.0501233 | 0 | see source table |
| 12jsl-12ps-logical0-read | 0 µA | -0.00281489 | -0.00281556 | 0 | see source table |

## Source table

| case | I(L_SL) min..max (µA) | I(L_SL) post p2p (µA) | V(SL) p2p (µV) | V(N6) p2p (µV) | JM1 post-pre (turns) | JM2 post-pre (turns) |
|---|---:|---:|---:|---:|---:|---:|
| 9ps-logical1-read | -20.0366..79.0668 | 2.61378 | 2544.44 | 2836.85 | 1.51197e-05 | 0.000209114 |
| 9ps-logical0-read | -4.19892..3.63586 | 0.264438 | 223.1 | 254.833 | -3.66056e-06 | 7.21211e-05 |
| 9ps-logical1-read0-control | -0.00972477..0.00864419 | 0.000338361 | 1.53595 | 1.50639 | 1.59155e-06 | -5.24734e-05 |
| 9ps-logical0-read0-control | -0.00864419..0.00972477 | 0.000338361 | 1.53595 | 1.50639 | -1.59155e-06 | 5.24734e-05 |
| 12jsl-12ps-logical1-read | -21.0247..79.0668 | 3.381 | 2700.15 | 3055.49 | 3.26268e-05 | 0.000242966 |
| 12jsl-12ps-logical0-read | -3.51369..3.63586 | 0.180982 | 162.099 | 199.654 | -4.13803e-06 | 7.47471e-05 |

## Observed

- The W*=12 ps JSL decks retain the accepted external-series topology and only shift the registered active READ transition in the existing source fixture.
- All twelve JSL columns remain non-switching; local event claims use continuous unwrapped phase and same-JJ same-segment voltage area.
- The W*=12 ps logical1 source remains clearly separated from logical0 and READ=0 controls in the source current and SL/N6 activity, while the storage/source guards remain bounded.

## Derived

- Absence of a complete JSL segment is a source-stage bounded observation; it does not certify the downstream QB response.
- The Phase-B gate is therefore satisfied for the registered W*=12 ps source replay into frozen QB.

## Inference

- The external 12-JSL load can serve as a bounded, state-selective source interface for the Phase-C requirements test. The Phase-C result separately shows that the resulting ideal replay improves QB margin but remains subthreshold.

## Unknown

- This report does not establish physical BVM→12-JSL→QB closure, exactly-one QB quantization, or downstream SFQ delivery.
