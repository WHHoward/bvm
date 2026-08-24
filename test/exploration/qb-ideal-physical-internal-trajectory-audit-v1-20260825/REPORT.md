# QB_IDEAL_PHYSICAL_INTERNAL_TRAJECTORY_AUDIT_V1

- analysis timestamp: `2026-08-25T01:35:13+08:00`
- analysis HEAD: `6e9cbedefeae8e8771299a8624bef081146494eb`
- solver execution: no new JoSIM run; frozen solver metadata is recorded only
- final disposition: `MECHANISM_AUDIT_INCONCLUSIVE`

## Artifact status

- C13 historical raw→snapshot→PWL chain: `HISTORICAL_REPLAY_SOURCE_CHAIN_CLOSED`; final-JSL source semantics: `INCONCLUSIVE`.
- D12 12×320: raw files are complete for descriptive recheck, but the four registered input-deck hashes are `RUN_INPUT_HASH_MISMATCH`; it cannot support certified mechanism ranking.
- E8 8×500: current tracked raw/input closure was rechecked descriptively; it cannot repair the C13 semantic boundary or D12 provenance defect.
- independent raw recheck: `PASS`.

## Key results

| pair / reference | status | key result |
|---|---|---|
| PRE C13.logical1_read vs D12.logical1_read | `PRE_STATE_MATCHED` | raw PRE feature comparison; phase uses relative turns plus sin/cos |
| PRE C13.logical1_read vs E8.logical1_read | `PRE_STATE_MATCHED` | raw PRE feature comparison; phase uses relative turns plus sin/cos |
| C13 ↔ D12 | `DESCRIPTIVE_RAW_OBSERVATION / PROVENANCE_INCONCLUSIVE` | first-divergence table retained but not certified |
| C13 ↔ E8 | `ANALYZED; total still INCONCLUSIVE` | representative earliest active/transition feature `source` at `95.012500 ps`, layer `TIE: input_port + bjs_trajectory + node2`; no unique layer order within `0.0125 ps` |
| Q0 scaled 45u | `TRAJECTORY_RESEMBLANCE_TO_SUBTHRESHOLD` | BJL2 local candidate counts `[0, 0, 0, 0, 0, 0]` across six pulse windows |
| Q0 scaled 68p4u | `TRAJECTORY_RESEMBLANCE_TO_QUANTIZED` | BJL2 local candidate counts `[1, 1, 1, 1, 1, 1]` across six pulse windows |

## Observed

- All five reference families have finite, strictly increasing raw time axes and the registered 13 ps cases share the native 0.0125 ps output grid; Q0 remains 0.1 ps and is not aligned to the 13 ps files.
- C13 snapshots contain only `time_ps,I_JSL_A`; exact replay closure uses the historical first `I(B_LD1)` occurrence at source-column index 14. The direct terminal `I(B_LD12)` index 51 is a separate diagnostic column.
- Physical E8 and D12 expose the QB port and internal BJs→BJL1→BJL2 branch signals needed for partition analysis; local phase trajectories and voltage-area diagnostics are retained separately from event claims.

## Derived

- `orientation-audit.json` reports the pre-registered source-vs-Lin and node2/node3/node4 residuals with fixed `abs_tol=1e-12 A`, `rel_tol=1e-6`, max/p95 and three-consecutive-sample criteria.
- `pre-bias-state.csv` reports the pre-registered feature-specific scale/limit comparison; a PRE mismatch is not relabeled as an ACTIVE root cause.
- For the C13↔E8 pair, the earliest active/transition classification is `TIE: input_port + bjs_trajectory + node2`; layer-specific first samples are recorded in `divergence-timeline.csv`: `input_port=95.012500ps, bjs_trajectory=95.012500ps, node2=95.012500ps, node3=95.237500ps, node4=95.162500ps`. Layers within `0.0125 ps` are treated as tied, not causally ordered.
- Q0 45 µA and 68.4 µA are six-pulse local references under their own windows; they do not establish a universal threshold or timestep convergence.

## Inference

- The strongest bounded mechanism classification is `TIE: input_port + bjs_trajectory + node2` / `coupled input-port/load-line plus BJs/node2 interface family; no unique first layer is established` for the C13 auxiliary-probe replay versus E8 physical drive, subject to the provenance boundary. This is a temporal/feature-level inference, not a unique physical root-cause proof.
- The E8 observation is conservatively described as `JSL8_LOADLINE_SHIFT_NO_DIRECTIONAL_RECOVERY`; the superseded directional wording `PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN` is not used.
- No local BJs multi-turn trajectory is called overdrive/failure, and no visualization or derivative sample is used as an event count.

## Unknown / unresolved

- C13 does not establish an ideal replay of the final physical JSL branch because its historical source selection is the auxiliary index-14 `I(B_LD1)` column. A new index-51 replay would be a different experiment and was not created.
- The D12 run-input hash mismatch prevents an authority-level C13↔D12 mechanism ranking. The missing historical `control-provenance.yaml` also limits READ/selectivity claims.
- One native timestep and these existing runs do not establish timestep convergence, parameter sensitivity, or a unique causal mechanism.

## Next parameter family recommendation (not executed)

- first divergence classification: `TIE: input_port + bjs_trajectory + node2`; recommended family: `coupled input-port/load-line plus BJs/node2 interface family; no unique first layer is established`.
- existing evidence: the first registered feature crossing occurs only after the fixed PRE subtraction and three-sample persistence rule; physical model: frozen BQ plus existing E8 BVM/JSL interface; target quantity: the layer's raw current/phase/voltage feature and its downstream partition.
- falsifiable hypothesis: changing only the nominated family should move the nominated feature and its downstream signature while leaving the matched controls and upstream layers within their registered bounds.
- controls: retain logical1 no-read, logical0 read, logical0 no-read, existing C13 historical replay, and no-magnetic-coupling boundary; do not change multiple families in one follow-up.
- decision tree: if the nominated layer moves first and downstream signatures follow, retain it as a candidate mechanism; if an upstream layer moves first, reclassify the divergence; if controls move comparably or orientation/KCL fails, mark `INCONCLUSIVE` and stop.
- stop rule: no sweep or parameter change is executed in this task; any future route, metric freeze, or paper claim requires renewed authorization and review.

## Evidence files

- `analysis/reference-integrity.json`
- `analysis/orientation-audit.json`
- `analysis/pre-bias-state.csv`
- `analysis/divergence-timeline.csv`
- `analysis/node-partition-summary.csv`
- `analysis/trajectory-audit.json`
- `analysis/independent-raw-recheck.json`
- key diagnostic plots are listed in `manifest.yaml` and each has a sidecar metadata JSON; plots are not Gate authority.

## Provenance and method

The analysis script reads the five registered reference families and current tracked netlist/provenance files only. It does not call `scripts/sfq_metrics.py`, `scripts/run_exp.sh`, or `build/josim-cli` to generate a run.
