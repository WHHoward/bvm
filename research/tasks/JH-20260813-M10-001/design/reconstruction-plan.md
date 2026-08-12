# M10 preregistration — historical metric reconstruction

## Purpose and boundary

M10 corrects the **representation and provenance** of four historical CSV
families.  It creates new immutable `metrics_v2/` JSON summaries beside the
raw files without changing those raw files or treating them as new circuit
experiments.  The output is limited to raw phase endpoint arithmetic and its
known evidence gaps.  It does not make an SFQ, fluxoid, downstream-reception,
candidate, route, or `INTERFACE_GATE_V1` decision.

The governing measurement contract is
`docs/research/METRIC_SPEC_V2.md` v2.0.0, SHA-256
`f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`.

## Fixed calculation procedure

For every listed CSV and every listed `P(...)` column:

1. Verify the header, finite numeric values, and strictly increasing actual
   `time` column.  Record its SHA-256.
2. Select the declared full-record provenance interval `[0, run_end + dt)`.
   This includes the first and last actual CSV samples; it is **not** a
   pre/post stability window and is never labelled a platform result.
3. Report only `endpoint_delta_rad = P_last - P_first` and
   `endpoint_delta_turns = endpoint_delta_rad/(2*pi)`, preserving sign and
   raw radians.  Do not round or call the result an event/SFQ/fluxoid.
4. Where a named matched zero-input control is declared below, report each
   run first and then `control_corrected_endpoint_delta` as signal minus
   control.  The control relation is a historical regression pairing, not a
   new proof of netlist-closure equivalence; record that limitation.
5. Do not report activity clusters, `fast_events`, event counts, platform
   deltas, voltage-area values, residual acceptance, or convergence verdicts.
   The selected historical CSV families lack the predeclared stable windows,
   fully demonstrated matched controls, direct same-JJ P/V mapping, or
   convergence evidence needed for those claims.

## Fixed input inventory

| Family / output | Raw inputs | P columns | control relationship |
|---|---|---|---|
| BASELINE | `test/final/single_bvm_qb/data/test_bvm_bq_baseline.csv` | `P(B_JM1|XBVM1)`, `P(B_JM2|XBVM1)`, `P(BJS|XBQ)`, `P(BJL1|XBQ)`, `P(BJL2|XBQ)` | none |
| P0 bump | `test/final/interface/data/test_dcsfq_behavior_bump_{0,1u4,20u,40u,68u,100u,150u,300u}.csv` | `P(B1|XDCSFQ)`, `P(B2|XDCSFQ)`, `P(B3|XDCSFQ)` | `bump_0` is the declared historical zero-input comparator for every nonzero bump file |
| P0 sustained | `test/final/interface/data/test_dcsfq_behavior_sustained_{68u,150u,300u}.csv` | `P(B1|XDCSFQ)`, `P(B2|XDCSFQ)`, `P(B3|XDCSFQ)` | none (no matched sustained zero-input CSV is committed) |
| P2 | `test/final/bvm/data/test_bvm_multivortex{,_wl80,_wl120}.csv` | `P(B_JM1|XBVM1)`, `P(B_JM2|XBVM1)` | none |
| BQ v4 | `test/final/qb/data/bq_v4_sweep{70,90,110,130,150}.csv`, `test/final/qb/data/bq_v4_sfq.csv` | `P(BJS|XBQ)`, `P(BJL1|XBQ)`, `P(BJL2|XBQ)`, `P(B1|XJTL)`, `P(B2|XJTL)` | none |

The BQ v4 lists must not silently substitute `V(OUT1)` or `V(JTLQ)` for a
direct JJ voltage.  BQ/BVM same-JJ P/V mappings remain `UNKNOWN` under
METRIC_SPEC_V2 §3.5.

## Required output and historical-document treatment

The four generated JSON files must contain: schema/version marker, generator
version/hash, metric-spec path/version/hash, generation timestamp, this plan
path/hash, per-input raw SHA-256, declared interval and selected timestamps,
per-column signed rad/turn endpoint quantities, control fields when applicable,
and machine-readable `limitations` / `not_applicable` entries.

The central correction table must link every JSON, state the rad-to-turn
correction, and state that each family remains below any physical Gate claim.
Only a compact `SUPERSEDED` banner/link may be appended to the four named
historical overview documents; their old tables and narrative must remain
verbatim.

## Stop rule

Stop rather than guessing if any listed input is missing, has a different
header, lacks finite/strictly increasing time data, does not contain its
declared P column, conflicts with the fixed control pairing, or requires a
different input/window/mapping.  Preserve the partial attempt and report it as
`BLOCKED` or `DEVIATED`; do not widen the inventory after inspecting outputs.
