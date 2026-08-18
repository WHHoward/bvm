# Independent numerical and adversarial review

**Review created:** 2026-08-19T04:52:36+08:00
**Scope:** R0b Exploration only; this is not a Copilot/Sol audit and not a
Candidate/Gate review.

## Review question

Does the first attempted point (`AREA=0.50`, `R_IN=12 ohm`, `+15 uA`) satisfy
the direct complete-trigger criterion without hiding a current-only or
voltage-peak-only oracle?

The cross-check was recomputed directly from the four raw CSV files by
`analysis/independent_crosscheck.py`, not by reading
`analysis/r0b-analysis.json`.

## Independent raw cross-check

| Case | Activity phase range | Activity V area | Largest monotonic segment | Same-segment area | Complete |
|---|---:|---:|---:|---:|---|
| read1 | 33.6437215 rad | 5.0106041 turns | 4.9974563 turns | 4.9974806 turns | **YES** |
| read0 | 1.1902876 rad | 0.0252076 turns | 0.1852812 turns | 0.1853045 turns | NO |
| logical1 READ=0 | 0.0005305 rad | 0.0000033684 turns | -0.00008443 turns | -0.00008444 turns | NO |
| logical0 READ=0 | 0.0015956 rad | 0.000136026 turns | 0.00025395 turns | 0.00025399 turns | NO |

The independent read1 segment is the same `102.9875–113.7625 ps` increasing
segment found by the primary analyzer. Its phase/area residual is
`+2.42765e-5 turns`; the read0 residual is `+2.33661e-5 turns`.

## Hidden-failure probes

| Hidden-error hypothesis | Independent probe | Disposition |
|---|---|---|
| Stale canonical fixture | SHA-256 fixture BVM/model against recorded canonical hashes | PASS; hashes match |
| Phase samples mistaken for events | Raw P trajectory, continuous unwrap, sign-consistent segments | PASS; only read1 has a >=2*pi segment |
| Current threshold used as switching oracle | Complete flag is computed only from phase delta; current is reported separately | PASS |
| Voltage peak used as switching oracle | Same-segment voltage area is integrated with actual CSV time and same endpoints | PASS |
| Hidden receiver branch or sign error | Direct KCL and `I(R_IN)` versus `I(L_SL)` check in 94–130 ps | PASS; see below |
| READ=0 accidentally contains READ | Inspect matched netlists and analyze both controls through 170 ps | PASS; no complete segment |
| Trigger-induced BVM collapse | Recheck SL/N6, JS1/JS2, and JM1/JM2 post states | PASS for bounded discrimination/back-action; not a preservation Gate |
| Damped ring miscalled self-quench/free-running | Compare post early/late voltage/current and post phase segments | PASS for no observed sustained free-running; R1 one-shot remains unknown |
| Local phase transition upgraded to SFQ delivery | Report explicitly excludes SFQ count, output JJ, JTL, and exact-one claims | PASS |

Independent current consistency results:

- maximum `|I(B_TRIG) - I(R_IN) - I(I_TRIG_BIAS)|` in 94–130 ps: `5.0e-12 A`;
- maximum `|I(R_IN) - I(L_SL)|` in 94–130 ps: `1.0e-17 A` (display precision);
- raw rows: 13,599 per case; time 0–169.9875 ps; actual dt 0.0125–0.025 ps;
- all four solver stderr files are empty.

## Numerical review checklist

| Check | Disposition | Evidence |
|---|---|---|
| Units | PASS | P is rad; turns divide by 2*pi; time is converted from CSV seconds; area divides by Phi0 |
| Same-junction endpoints | PASS | B_TRIG P and B_TRIG V use the same segment indices and N_TRIG -> 0 direction |
| Monotonicity | PASS | Adjacent-sample continuous phase signs define the segments; no smoothing or event count is used |
| Area integration | PASS | Trapezoidal integration over actual CSV time, not nominal dt |
| Operating-point order | PASS | First point passed; later points were not run under the declared stop rule |
| AREA semantics | PASS | Ic/C scale with AREA; RN/R0 divide by AREA; actual values are documented |
| Timestep convergence | UNKNOWN | Only the requested 0.0125 ps condition was run |
| Parameter/load margin | UNKNOWN | No sensitivity sweep was authorized or run |

## Review disposition

**PASS for the declared R0b local complete-trigger criterion, with
Exploration-bounded scope.** The raw evidence supports R0b PASS at the first
point. It does not support exactly-one-SFQ, downstream delivery, self-quench,
JTL reception, convergence robustness, or a hardware claim.
