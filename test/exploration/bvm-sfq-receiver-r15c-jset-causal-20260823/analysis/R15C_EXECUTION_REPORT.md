# R15-C execution report

Verdict: **`CAUSAL_NEAR_THRESHOLD`**

The fixture contains canonical BVM + frozen R0b B_DET + finite-impedance J_SET current-summing return. J_Q/J_OUT/DCSFQ/JTL/T1 are absent.

Artifact QA: all four JoSIM runs exited 0 with 13,599 rows. The median output step is 0.0125 ps; each run has one 0.025 ps gap at 1.8375--1.8625 ps, identical to the matching R15-B raw schedule and outside all analysis windows.

## Matched-case result

| case | B_DET largest segment (turn) | B_SET largest segment (turn) | B_SET same-JJ area (turn) | B_SET event candidates | I_JSET activity min..max (uA) | KCL max abs (uA) |
|---|---:|---:|---:|---:|---:|---:|
| logical1-read | 4.973019 | 0.224437 | 0.224483 | 0 | 2.097131..9.128855 | 5e-07 |
| logical0-read | 0.184724 | 0.033851 | 0.033859 | 0 | 4.888101..6.282439 | 5e-07 |
| logical1-read0-control | -0.000083 | -0.000001 | -0.000001 | 0 | 5.599984..5.600017 | 4.99898e-07 |
| logical0-read0-control | 0.000256 | -0.000002 | -0.000002 | 0 | 5.599981..5.600019 | 4.99864e-07 |

## Verdict boundary

- `I(I_SET)=I(R_BIAS)+I(B_SET)` is checked directly from the same raw run.
- Event evidence requires continuous phase, same-JJ/same-segment voltage area, phase/area consistency and bounded post behavior.
- Current above `Ic`, voltage peak and phase range alone are not event evidence.
- Source comparison is against the matching R15-B raw case; any extra SL/N6/JM/JS disturbance is reported separately.

## Source/back-action comparison (post window, R15-C minus R15-B p2p)

The comparison below uses the same post window in the matching R15-C and R15-B raw runs. It is a differential guard, not an absolute canonical-source claim.

| case | V(SL) (uV) | V(N6) (uV) | I(L_SL) (uA) | P(JM1) (rad) | P(JM2) (rad) | P(JS1) (rad) | P(JS2) (rad) |
|---|---:|---:|---:|---:|---:|---:|---:|
| logical1-read | -46.903 | -44.7225 | -0.0177439 | -0.003858 | -0.0850407 | -0.07525 | -0.10085 |
| logical0-read | +0.02568 | +0.00775 | +0.00070512 | +6e-06 | +2.19e-05 | -7.61e-05 | +5.46e-05 |
| logical1-read0-control | -0.000544796 | -0.000544887 | +6.008e-08 | +0 | -5e-07 | -8e-07 | -8e-07 |
| logical0-read0-control | +0.00021785 | +0.00021765 | +1.4303e-07 | +0 | -4e-07 | +2e-07 | +4e-07 |

For the read1 case, all listed post-window p2p changes are non-positive relative to R15-B; this does not erase the bounded extra back-action already present in R15-B, and absolute running-phase offsets remain a separate interpretation question.

## Observed / Derived / Unknown

- **Observed:** finite-impedance J_SET current is state dependent; read1 has a 0.224-turn B_SET segment and read0 has a 0.034-turn segment; controls are at numerical baseline; all four raw runs completed.
- **Derived:** read1/read0 J_SET modulation p2p ratio and KCL residual are recorded in `r15c-execution-metrics.json`; B_SET phase and same-segment voltage area agree for the observed sub-turn excursion.
- **Inference:** the causal fixture transfers the B_DET state into the J_SET current degree of freedom and brings read1 closer to threshold, but does not establish a complete J_SET event.
- **Unknown:** whether a different active-stage mechanism can convert this causal sub-turn response into a bounded one-shot; no J_Q/J_OUT/DCSFQ was tested here.
