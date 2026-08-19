# R1a numerical and adversarial review

Review timestamp: 2026-08-19T13:23:31+08:00
Scope: R1a series pickup / passive isolated secondary only

## Disposition

**PASS for the preregistered R1a passive-transfer criterion, with bounded
back-action explicitly retained as a limitation.**

This is an Exploration result. It is not a Candidate, SFQ-delivery result,
JTL result, one-shot result, or BVM state-preservation Gate.

## Numerical checks

| Check | Result |
|---|---|
| Solver provenance | build/josim-cli v2.7.2837d13; recorded binary hash |
| Matched matrix | Four cases, same receiver and requested dt |
| Raw artifact QA | 13,599 rows/case; finite; increasing time; required columns present |
| Actual CSV spacing | 0.0125–0.025 ps; requested condition was 0.0125 ps |
| Phase units | Raw P is radians; turns are delta/(2π) |
| Unwrapping | Adjacent-sample continuous unwrap; raw phase retained |
| Monotonicity | Adjacent phase-delta signs define each segment; no smoothing |
| Switching criterion | Segment phase delta only, with explicit 2π threshold |
| Voltage check | Same B_TRIG segment, same endpoints, actual CSV time, divided by Φ0 |
| Secondary baseline | Each case uses its own 80–90 ps PRE median |
| Secondary controls | Both READ=0 controls analyzed through 170 ps and 20–170 ps full check |
| Independent phase/secondary cross-check | All comparisons pass |
| R0b comparison | Independent raw read of R0b and R1a CSVs; trigger/source/storage comparison present |

The independent cross-check reports all comparisons true for read1, read0,
logical1 READ=0, and logical0 READ=0. The independent R0b comparison confirms
the R1a trigger segments, same-segment voltage areas, source activity, and
JM1/JM2 storage medians from the raw CSVs.

## Hidden-failure probes

| Possible hidden failure | Probe | Disposition |
|---|---|---|
| Canonical fixture drift | Canonical BVM and JJ model hashes compared with manifest | PASS; fixture hashes match recorded sources |
| Series branch not actually inserted | Direct I(R_IN), I(L_TX), N_PICK/N_TRIG probes | PASS; series currents match and netlist includes L_TX |
| Secondary is floating or unobserved | V(N_SEC), I(L_SEC), I(R_SEC_LOAD), grounded L_SEC and load | PASS; passive KCL-consistent transient observed |
| Secondary is a startup artifact | Per-case PRE medians plus two READ=0 controls | PASS; controls remain at the probe floor |
| Current threshold mislabeled as switching | Complete flag comes only from monotonic phase segment | PASS |
| Voltage peak mislabeled as switching | Same-JJ area uses B_TRIG P/V segment endpoints | PASS |
| Multi-turn range mislabeled as one event | Report says trigger remains multi-turn; no event count is claimed | PASS |
| Read0 edge excursion hidden by window | Read0 analyzed over 94–170 ps and broad control window | PASS; largest read0 segment is 0.184757 turns |
| Control free-running | Controls checked over 20–170 ps | PASS; largest control segments below 0.07 turns |
| BVM loading hidden by trigger-only result | SL, N6, input, JM1/JM2, and JS1/JS2 are directly probed | PASS with bounded JM2 caveat |
| JM2 back-action silently discarded | R0b and R1a storage medians compared directly | CAVEAT retained; read1 JM2 drift changes direction |
| Local trigger upgraded to SFQ delivery | No output JJ/JTL; report explicitly excludes SFQ claim | PASS |

## Storage/back-action interpretation

The R1a read1 post-read storage signs remain logical1-like and read0 signs
remain logical0-like. This supports the declared bounded criterion. It does
not establish that the pickup is storage-invisible: read1 JM2 post–pre drift
changes from approximately −0.003931 turns in R0b to +0.005032 turns in R1a.
That difference is recorded as an observed loading effect and must be revisited
before any future state-preservation or system-level claim.

## Final review conclusion

The raw evidence supports R1a PASS for the narrow question:

    canonical SL → series pickup → passive isolated secondary

preserves read1 complete local B_TRIG discrimination from read0 and both
READ=0 controls while producing a clear read1-dominant secondary transient.
The result is bounded to this single model/operating point and does not
authorize or implement R1b.
