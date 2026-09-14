# BVM QB L1/L3/BJ2 targeted closure handoff

The experiment uses the real `4xBVM -> COMMON_SL -> JSL1..8 -> QB ->
JTL1..6 -> R_TERM` topology with the frozen 100 uA history and `.tran 0.1p
200p`. The only target changes are L1=1.2 pH, L3=2.0 pH and BJ2 area=2.2.

The two authorized cases are masks 0011 and 0111. `0001/1111` are reserved
for a later scientifically authorized validation task and are not run here.
Raw P(...) values remain radians; displayed turns are navigation only and are
not SFQ counts. The handoff stops at
`EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.

T01/T02 were both history/control CLEAN. T01 produced one ordered candidate;
T02 produced four raw candidates with order `{1:true,2:true,3:false,4:true}`.
The registered outcome is `N3_FOURTH_HANDOFF_BOUNDARY_CASE`; no validation solve
was authorized or run.
