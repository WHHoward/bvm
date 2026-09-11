# BVM QB L3/BJ2 targeted-combination handoff

The experiment uses the real `BVM1..4 -> COMMON_SL -> 8-JJ JSL -> QB ->
6-stage JTL -> R_TERM` topology with the frozen 100 uA history and `.tran 0.1p
200p`. The only new screening point changes exactly `L3` to 2.0 pH and `BJ2`
area to 2.2; all other parameters remain canonical.

`0011` and `0111` are the registered screening cases. `0001` and `1111` are
conditional validation cases only after a clean ordered 2/3 result. Raw P(...)
values remain radians; displayed turns are navigation only and are not SFQ
counts. This handoff stops at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
