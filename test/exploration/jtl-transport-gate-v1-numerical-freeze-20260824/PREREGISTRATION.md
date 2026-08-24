# JTL_TRANSPORT_GATE_V1 numerical freeze — preregistration

**Recorded:** `2026-08-24T13:16:46+08:00`  
**Parent accepted HEAD:** `8bb86f61c3243655467d61f00680977349b41cf3`  
**Mode:** bounded numerical validation / fixture-level calibration gate

## Scientific question

Does the existing JTL transport methodology remain numerically stable for the
three registered fixtures when the JoSIM timestep is refined by a factor of
two, and when only the pre/post analysis windows receive the registered small
perturbation?

This is a fixture-level transport-method validation. It is not a global
acceptance specification for every JTL, and it does not establish a physical
QB-to-JTL interface.

## Frozen fixtures

Only these three already accepted fixtures are used:

1. **R11 standard-JTL positive control** — the repository `THmitll_JTL` cells
   and accepted positive-current stimulus from R11-A.
2. **Q0 pulse-5 original-polarity ideal replay** — the accepted Q0 `V(OUT,t)`
   pulse-5 waveform replayed without scaling or shaping.
3. **Q0 pulse-5 reverse-polarity ideal replay** — the same waveform multiplied
   by `-1`, not a logical-0 control.

No JTL topology, JJ parameter, bias, load, source waveform, or polarity is
changed. Only the requested `.tran` timestep changes.

## Numerical ladder

Each fixture is run independently at exactly:

`0.025 ps`, `0.0125 ps`, `0.00625 ps`

with the original stop time and all direct JTL `P(...)`, `V(...)`, `I(...)`
probes retained. All output directories are immutable and private to one
fixture/timestep.

## Registered windows

The activity window is never changed:

| fixture | pre W0 | activity | post W0 |
|---|---:|---:|---:|
| R11 | `[8, 10) ps` | `[10, 35) ps` | `[35, 60) ps` |
| pulse 5 | `[208, 210) ps` | `[210, 235) ps` | `[235, 260) ps` |

The pre/post robustness check is registered before execution:

- **W−:** pre starts `0.5 ps` earlier; post ends `0.5 ps` earlier.
- **W0:** the table above.
- **W+:** pre starts `0.5 ps` later; post starts `0.5 ps` later.

The activity interval, signal directions, and event/transport rules are
identical for all three window variants. No endpoint may be selected after
inspection of a trace.

## Measurements

For each of the four standard JTL junctions, report from raw CSV using the
actual time column:

- strict local monotonic segments, including turns and same-segment direct
  voltage area;
- pre-to-post well delta (mean and median), full activity-window phase and
  same-window direct voltage area;
- phase-area residual;
- pre/post phase p2p and voltage RMS;
- post-window extra strict complete segments;
- `t50` onset: first activity sample at least `+0.5 turn` from the pre mean
  in the expected positive direction;
- causal onset order and its registered `0.5 ps` slack;
- strict local event vector and settled-well transport vector.

Raw `P(...)` is radians. Turns are always derived as `delta(phi)/(2*pi)`.
Voltage area is `trapz(V(JJ), actual_time)/Phi0` for the same JJ, endpoints,
direction and analysis segment. Legacy `fast_events` and voltage peaks are
not event evidence.

## Provisional task-local tolerances

These are carried unchanged from the accepted retrospective methodology and
are not claimed as global device tolerances:

- one adjacent well: `±0.02 turn`;
- same-window phase/area residual: `≤2e-4 turn`;
- pre p2p: `≤0.01 turn`;
- post p2p: `≤0.07 turn`;
- onset-order slack: `0.5 ps`;
- a strict local event requires a monotonic segment of at least one turn and
  phase/area consistency.

## Freeze decision

Freeze `JTL_TRANSPORT_GATE_V1` at fixture level only if, for every timestep and
every registered W−/W0/W+ variant:

- R11 retains four-stage `+1` settled-well transport;
- pulse-5 original retains four-stage `+1` settled-well transport;
- reverse polarity remains non-transport for the expected positive one-well
  chain;
- no artifact is invalid and no classification changes with timestep/window.

Otherwise classify the numerical result `INCONCLUSIVE` or `FAIL` as
appropriate and do not freeze the gate.

## Stop rules

No timestep outside the three registered values, no window tuning, no JTL
parameter changes, no QB/interface optimization, no T1 connection, and no
use of this fixture-level result as physical BVM-to-JTL evidence.
