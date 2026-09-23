# Numerical-method review (pre-solve)

Scope: preregistered arithmetic and raw-processing code for v2. This review
does not classify a physical outcome.

| Check | Status | Evidence / boundary |
|---|---|---|
| Units | PASS | CSV time is parsed as stored seconds; phase `P(...)` is raw radians; turns are an explicit `rad/(2π)` display/navigation value; voltage areas are V·s and then divided by Φ0. |
| Phase reduction | PASS | JoSIM P is treated as already-unwrapped raw phase; no modulo or additional unwrap is applied. A synthetic 7 rad endpoint delta remains 7 rad. |
| Window edges | PASS | Decimal parsing selects exact half-open windows `[start,end)`; tests include 110 ps and exclude 121 ps from `[110,121)`. |
| Integration | PASS | Trapezoid uses exact Decimal differences between stored time tokens, multiplied by raw voltage values; no fixed-DT assumption, interpolation, or resampling. An irregular-grid synthetic integral is independently recomputed. |
| Same-JJ comparison | PASS as registered arithmetic | Each metric mapping identifies direct P/V columns, source device pin order, `voltage_to_phase_sign`, and `reporting_direction`; phase and voltage area use identical raw endpoints and run/window. Mapping authority remains UNVERIFIED for this fixture. |
| Independent arithmetic | PASS on synthetic test | `independent_verify.py` independently parses raw time/voltage/phase tokens with Decimal and checks pipeline outputs. Its frozen tolerances in REGRESSION_MATRIX.json are implementation-reproduction tolerances only, not physical acceptance tolerances. |
| Data health | REGISTERED | Required columns, duplicate headers, finite values, exact increasing time, start coverage, `STOP-DT` endpoint coverage, and at least two samples per registered JJ/terminal window are checked. |
| Timestep convergence / solver sensitivity | UNKNOWN | Only the authorized `DT=0.01p` is planned; no convergence or sensitivity sweep is authorized. |
| Physical classification | NOT PERFORMED | No SFQ/event count, truth-table verdict, failure localization, or phase-area pass/fail is assigned; phase-area acceptance tolerance remains UNFROZEN. |

The classic plot smoke test confirmed `-j 2pi` converts synthetic 0, 2π, 4π
raw phase samples to 0, 1, 2 turns while preserving the input CSV hash. It is a
plotting QA check, not physical evidence.
