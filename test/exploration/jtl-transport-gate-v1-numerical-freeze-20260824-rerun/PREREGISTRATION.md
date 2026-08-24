# JTL_TRANSPORT_GATE_V1 strict numerical replay

**Recorded:** `2026-08-24T13:31:00+08:00`  
**Parent accepted HEAD:** `8bb86f61c3243655467d61f00680977349b41cf3`  
**Status:** preregistered successor to the retained pilot

## Scientific question

Within the three frozen fixture sources, does the JTL transport classification
remain numerically stable under the registered timestep ladder and under
independent small perturbations of the settled pre and post windows?

This is a fixture-level numerical gate only. It is not a physical BVM→JTL
interface claim, a global JTL tolerance, or a T1 result.

## Frozen fixtures and provenance

Only these source decks are allowed:

1. R11 standard-JTL positive control;
2. accepted Q0 pulse-5 original-polarity ideal replay;
3. the same pulse-5 replay with its registered reverse polarity.

The repository `JTL.cir`, `jjmit.cir`, source decks, and replay polarity are
copied byte-for-byte or rewritten only for the registered `.tran` timestep.
The parent source hashes and the generated input snapshot hashes must be
recorded in `inputs/manifest.json` and `inputs/PRE_RUN_SHA256SUMS.txt` before
the first JoSIM process starts. No circuit parameter, source amplitude,
topology, bias, load, or polarity may change.

## Numerical ladder

Each fixture runs independently at exactly `0.025 ps`, `0.0125 ps`, and
`0.00625 ps`, with the original stop times (`170 ps` for R11 and `300 ps` for
the two replays). The actual CSV time axis is used for all integrations and
onset interpolation.

## Registered windows

The activity windows remain fixed:

| fixture | pre base | activity | post base | tail guard |
|---|---:|---:|---:|---:|
| R11 | `[8,10)` ps | `[10,35)` ps | `[35,60)` ps | `[35,170)` ps |
| pulse-5 replay | `[208,210)` ps | `[210,235)` ps | `[235,260)` ps | `[235,300)` ps |

Pre and post perturbations are independent. For each raw trace, all nine
combinations of:

- pre `minus=[base_start−0.5,base_end)`, `base`, `plus=[base_start+0.5,base_end)`;
- post `minus=[base_start,base_end−0.5)`, `base`, `plus=[base_start+0.5,base_end)`

are evaluated against the same fixed activity window. No window is selected
after inspecting a result.

## Evidence and numerical rules

- Raw `P(...)` is used directly as radians; no additional unwrap transform is
  applied. Turns are phase differences divided by `2*pi`.
- Strict local segments are reported with same-JJ, same-segment direct
  voltage area. A local complete segment requires at least one turn, matching
  sign, and task-local phase/area consistency.
- Settled transport is a separate evidence layer. A positive transport vector
  requires each stage to show a pre→post `+1` well, stable pre/post p2p, full
  activity phase/area consistency, interpolated `t50`, and causal onset order.
- The post/tail guard scans the full remaining simulation tail for extra
  complete monotonic segments; it is not limited to the short post well window.
- The reverse replay is checked for both signed directions. It must not form a
  four-stage `+1` or `−1` settled transport chain, and its final stage must not
  settle at either signed one-well result.
- No voltage peak, current threshold, total phase range, or legacy fast-event
  count is an event criterion.

## Pre-registered numerical stability bands

These are local bands for this fixture gate, not universal device specs. For
each positive fixture, each JJ, and adjacent timestep pairs, the following
must remain within the stated absolute differences:

- pre→post mean and median well: `0.002 turn`;
- largest strict-segment turns and same-segment area: `0.002 turn`;
- full-window phase and area: `0.002 turn`;
- phase/area residual: `2e-4 turn` at each point;
- pre/post p2p: `0.002 turn`;
- interpolated `t50` and adjacent onset delay: `0.10 ps`.

Across all nine independent pre/post window combinations, the baseline
comparison must remain within `0.002 turn` for well/full phase/area metrics,
`0.005 turn` for settled p2p, and `0.10 ps` for interpolated onset. The
positive fixture transport class and reverse non-transport class must not
change across these variants.

## Freeze decision

Freeze `JTL_TRANSPORT_GATE_V1` at fixture level only if R11 and pulse-5
original satisfy the positive transport vector, all numerical and window
bands, full-tail no-extra-event guard, and artifact QA at every timestep;
reverse satisfies the signed non-transport oracle at every timestep/window.
Otherwise report `INCONCLUSIVE` or `FAIL` and do not freeze.

## Stop rules

No additional timestep, window, JTL parameter, QB/interface parameter,
transformer, conditioner, T1, or physical BVM connection is permitted.
