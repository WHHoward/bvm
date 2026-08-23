# R15-A AFQ-3 single-point execution report

## Verdict

**`PRECHECK_NO_GO`**

The AFQ-3 nominal point was stopped before any valid matched scientific case.
Gate 0 found that the shared `L_F` magnetic block is not a positive-definite
inductance matrix for `K_QF=K_FO=0.90`. This is a nominal-topology/model
closure failure, not evidence against B_DET, the active interstage idea, or the
frozen DCSFQ backend.

## Gate disposition

| Gate | Result | Meaning |
|---|---|---|
| 0 | **FAIL** | node KCL/DC paths are closed, but the `L_Q/L_F/L_CTL` mutual matrix has `det=-0.62` and `λmin=-0.2727922` |
| 1 | PASS | actual copied `jjmit` AREA reconstruction completed |
| 2 | NOT EXECUTED | no-input stability cannot be certified on an invalid constitutive network; `B_OUT=275/300=0.9167` remains the flagged risk |
| 3 | diagnostic pass | R1a-derived read1/read0 coupled-current estimate has `1.62104 µA` nominal margin; not event evidence |
| 4 | diagnostic only | hypothetical current steering bracket is `105.5–188.5 µA` depending on assumed 10–20 ps state, but it is not a loaded-network result |

The detailed calculations are in [GATE0_4_PRECHECK.md](GATE0_4_PRECHECK.md).

## Execution status

No valid raw CSV exists. One pre-correction diagnostic launch of
`logical1-read0-control` emitted only the JoSIM banner and was stopped after
Gate 0 was found to be invalid; its log is retained and explicitly excluded
from scientific evidence. The four matched cases were not run.

No canonical BVM, frozen DCSFQ circuit, or accepted evidence was modified.
No AREA, bias, K, L, R, or load was changed to rescue the point.

## Boundary

The current result falsifies only this AFQ-3 nominal magnetic formulation as a
valid pre-run point. A retry requires a separately preregistered,
physically-realizable multi-winding topology and a new Gate 0; it must not
silently alter the mutual coefficients or interpret this stop as a receiver
physics failure.
