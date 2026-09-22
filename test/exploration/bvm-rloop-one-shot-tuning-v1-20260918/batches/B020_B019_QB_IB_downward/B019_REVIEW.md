# B019 QB_IB downward — mechanical evidence review

No scientific interpretation performed. `terminal_candidate` is a positive-current locator, not an SFQ count. P(...) values are raw radians; turn columns are independently unwrapped navigation metrics.

## Authorized matrix

- Normal closed sweep: `QB_IB=220u,230u,240u,250u,260u`; masks `0000,0001,0011`.
- Logical runs: 15; new physical solves and strict reuse are recorded in `BATCH_QA.json`.
- Control-only: only C0/C1 at `QB_IB=260u` were authorized before this sweep. Other IB control-only fixtures were not run.

## C0/C1 gate

- `C0` `U143_B019_CONTROL_ONLY_C0`: raw QA `PASS`, registered pattern match `True`, terminal candidates `0`, first peak `None ps`, peak `None A`.
- `C1` `U144_B019_CONTROL_ONLY_C1`: raw QA `PASS`, registered pattern match `True`, terminal candidates `1`, first peak `94.19999999999999 ps`, peak `0.0001243786 A`.

## Per-IB rows

See `B019_METRICS.csv`. CONTROL rows for 220–250u are explicitly `NOT_RUN_IN_AUTHORIZED_MATRIX`; normal-protocol control-window metrics are retained separately and are not treated as isolated CONTROL evidence.

## Evidence status

- Mechanical/raw evidence only.
- No operating-window, mechanism, causal, or Gate conclusion is assigned.
- No follow-up sweep was started.
