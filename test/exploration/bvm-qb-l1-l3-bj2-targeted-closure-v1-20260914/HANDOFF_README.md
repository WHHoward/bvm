# BVM QB L1/L3/BJ2 targeted closure handoff

The experiment uses the real `4xBVM -> COMMON_SL -> JSL1..8 -> QB ->
JTL1..6 -> R_TERM` topology with the frozen 100 uA history and `.tran 0.1p
200p`. The only target changes are L1=1.2 pH, L3=2.0 pH and BJ2 area=2.2.

The two authorized cases are masks 0011 and 0111. `0001/1111` are reserved
for a later scientifically authorized validation task and are not run here.
Raw P(...) values remain radians; displayed turns are navigation only and are
not SFQ counts. The handoff stops at
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
