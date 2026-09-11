# BVM QB L3 high-side selective-window experiment

This experiment tests only L3=1.8 pH and, if H1 is not a clean 2/3 point,
L3=2.0 pH. Each executed point uses masks 0011 and 0111 in the real
BVM1..4 -> COMMON_SL/JSL -> QB -> six-stage JTL -> terminal topology.
L3=1.6 pH is an immutable reference and is not rerun.

CONTROL/history uses complete downstream propagation only in the registered
70–110 ps windows. FINAL/Tail phase rollback is a separate diagnostic. P(...)
is raw radians; rad/(2*pi) is navigation/display only, never an SFQ count.
N1/N4 population validation is reserved for later authorization and is not
automatically executed here.

The completed bounded screening used four new physical solves. H1 (L3=1.8 pH)
and H2 (L3=2.0 pH) both remained CLEAN with N2=2. Each 0111 run had four raw
response candidates, while strict full-chain ordering was ambiguous for
candidates 3 and 4, matching the immutable L3=1.6 pH reference. The registered
fourth-response diagnostics showed no material weakening, so both points are
class B (`STILL_2_TO_4`) and the stopping outcome is
`L3_HIGHSIDE_NO_SELECTIVE_WINDOW_IN_TESTED_RANGE`.
