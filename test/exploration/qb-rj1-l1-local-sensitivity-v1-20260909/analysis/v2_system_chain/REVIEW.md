# V2 numerical/adversarial review

## Review scope

This review covers only the versioned V2 presentation repair. It does not
recalculate the original experiment's registered metrics and does not create a
new physical interpretation.

| check | result | evidence |
|---|---|---|
| raw authority | PASS | all five current raw hashes equal the recorded post-analysis hashes |
| raw mutation | PASS | V2 rendering computes source hashes before/after and finds no change |
| old artifact preservation | PASS | pre-V2 snapshot finds no changed/deleted historical plot or result file |
| stale/wrong run | PASS | manifest contains exactly the five existing run IDs and their absolute raw paths |
| hidden signal loss | PASS | every V2 category records requested and actual signal order; JSL1..JSL8 are all present |
| BJS label mismatch | PASS | actual raw header label `BJS` is retained; no case-insensitive silent substitution is used |
| optional missing probe | UNKNOWN | `V(IB|XBQ1)` is explicitly recorded as absent; no proxy signal is fabricated |
| phase display | PASS | each phase view independently unwraps raw radians, then `josim-plot2 -j 2pi` displays turns |
| window boundary | PASS | every V2 input is checked against the exact half-open stored-row time set |
| comparison grid | PASS | comparison inputs require exact raw time-token identity; no interpolation or alignment is used |
| weak physical oracle | PASS | V2 contains no event detector, SFQ count, threshold, phase-plane, ranking or mechanism plot |
| physical solve count | PASS | V2 solve count is zero; original experiment execution summary remains exactly five solves |

## Residual uncertainty

The V2 pages are descriptive navigation artifacts. They cannot determine
convergence, event counts, system Gate status or mechanism. The existing
experiment's `UNKNOWN`/`INCONCLUSIVE` boundaries remain in force.
