# QB_TO_JTL_LOAD_BACKACTION_CAUSAL_AUDIT_V1 — preregistration

**Recorded:** `2026-08-24T13:16:46+08:00`  
**Parent accepted HEAD:** `8bb86f61c3243655467d61f00680977349b41cf3`  
**Mode:** bounded causal evidence audit; no parameter sweep

## Scientific question

How does the downstream output boundary repartition the Q0 QB node-4 current
before BJL2 crossing, during the crossing, and during retrap, when compared
with the accepted 10-ohm operating point?

The report must not collapse the nonlinear interface into one scalar impedance
unless the measured current partition supports that approximation.

## Frozen matched cases

Use existing accepted raw wherever the required probes exist:

1. accepted Q0 + `10 ohm`;
2. Q0 `OPEN`;
3. Q0 `JTL-only`;
4. Q0 `10 ohm || JTL`;
5. M3 Q0 → series `10 ohm` → JTL.

The Q0 cases use the registered Q0 pulse train; the comparison is aligned to
the registered pulse-5 interval and the accepted BJL2 event onset. M3 uses
the accepted series-10-ohm Q0 fixture and is retained as a distinct boundary,
not silently merged with the parallel matrix.

No circuit parameter, source waveform, QB model, JTL parameter, or load value
may be changed. If a required probe is absent, only a probe-only rerun of the
minimum matching parent fixture is allowed; no such rerun is presumed before
the probe audit.

## Required observations

For each case and registered phase interval, report where available:

- `I(L2)`, `I(L0)`, `I(BJL2)`, `I(RJ2)`;
- BJL2 continuous unwrapped phase, direct same-JJ voltage, strict segments and
  same-segment voltage area;
- `V(OUT)`;
- JTL input branch current and output/interface branch currents;
- dissipative energy in `RJ2`, the 10-ohm load, and the M3 series resistor
  when the direct current probe exists.

Use the node-4 KCL in the declared current directions:

`I(L2) = I(L0) + I(BJL2) + I(RJ2)`

Report the residual rather than assuming it is zero. For any added load branch,
report its own KCL contribution and direction separately.

## Registered temporal regions

For Q0 pulse 5, use the existing matrix timing and align the regions to the
accepted BJL2 event onset from the 10-ohm reference:

- **pre-crossing:** from the registered pulse-5 pre window start to the first
  registered BJL2 monotonic-event onset. (For the accepted reference the
  onset is exactly at activity start, so this explicitly preserves the
  non-empty `[208,210) ps` settled pre interval.)
- **crossing:** the same BJL2 strict segment endpoints in the accepted 10-ohm
  reference, mapped to the matched trace time axis;
- **retrap/post:** from that segment end through the registered post window.

The exact onset and endpoints are read from the accepted reference artifact,
not selected separately for each load case. If a case has no complete event,
the reference endpoints are still used for a matched current-partition
comparison and the case is not assigned a fabricated event window.

## Local evidence rules

An event claim requires continuous unwrapped phase, a monotonic segment of at
least one turn, same-JJ/same-segment direct voltage area, and bounded post
behavior. `I>Ic`, voltage peaks, total phase range, or legacy fast-event
counts are not event evidence.

## Required mechanism classification

End with exactly one bounded classification:

`LOAD_DIVERSION_BEFORE_SWITCH`  
`SWITCH_TRAJECTORY_BACKACTION`  
`RETRAP_BOUNDARY_DOMINANT`  
`MIXED_DYNAMIC_LOADING`  
`INCONCLUSIVE`

The classification is limited to these frozen fixtures, source pulses,
models, loads, time steps, and windows. It is not a universal claim about
QB/JTL interfaces.

## Stop rules

Do not design or tune transformer/R/L/Ic/bias, do not attach T1, do not connect
physical BVM, and do not add an unregistered parameter point. Commit this
package separately from the JTL numerical-freeze package.
