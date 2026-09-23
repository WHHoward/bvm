# Evidence Manifest

Experiment: `bvm-bq-cb-gap-2x1-v2-20260923`

This package preserves all four authorized immutable raw CSVs, exact decks/stimuli, metadata, source snapshots, mechanical analysis, classic plots and comparison views.

V2 registered four new physical solves. The unretained v1 incident transient is excluded from this package; cumulative solver invocations across both attempts are five.
Independent Decimal arithmetic QA re-read each raw and reproduced the mechanical endpoint/area calculations.
## Runs

| Run | Mask | Raw bytes | Raw SHA-256 | Deck SHA-256 | Independent QA SHA-256 |
|---|---|---:|---|---|---|
| N0_00 | 00 | 59955700 | `3b364522d769bc500f7d5aeddfb6f41cc5e2eed1d90ea1c2214aa115da1740a9` | `7e920f16834a4382ae824dc370550464848af19d0a39e723be2aa80d34e20a1e` | `fb4d77b39381b68e3ef9b59be2fe942dad046799e02be5b0aef3aec209f28e12` |
| N1_01 | 01 | 59903118 | `935a6e76308004a0ba662b54aa7ec8f9078aa651a18dea969d71dae323a114cd` | `7e920f16834a4382ae824dc370550464848af19d0a39e723be2aa80d34e20a1e` | `4b8ee2baf9b0fd842953e91e2db28fb9758d2d89163dab4fdac391249450d784` |
| N1_10 | 10 | 59903125 | `cebce73fe814d065e7a203e1c8568751a898db5daeaeb4c6c1b29b8f1f360b37` | `7e920f16834a4382ae824dc370550464848af19d0a39e723be2aa80d34e20a1e` | `e6de5e594571de0243e177cd042138cdb2724bf6841521d82b898d32c05b1733` |
| N2_11 | 11 | 59928358 | `5df93fcfb94064aa26f4df61923be782d00b90fd3bc251c5f5a480b06bde0c95` | `7e920f16834a4382ae824dc370550464848af19d0a39e723be2aa80d34e20a1e` | `787e21a7f0b42110a36eb465e5edddc376fec6e6d3782f171b8240374be020fb` |

## Visualization

Standalone plot count: 80; comparison plot count: 15.
Renderer: `scripts/josim-plot2.py`; `sep_comb`, dark theme, `-j 2pi`. P is raw radians; phase turns are navigation only.
Excitation and outputs appear together in the classic whole-chain overview plots. Window plots use only stored samples in half-open registered windows; no interpolation or resampling.

## Interpretation boundary

Scientific interpretation was not performed. This evidence package does not classify SFQ delivery, count population outcomes, localize a failure, or assert a mechanism. Review is pending.
