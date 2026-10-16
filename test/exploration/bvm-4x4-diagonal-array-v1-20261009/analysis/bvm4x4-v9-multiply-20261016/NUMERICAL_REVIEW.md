# Numerical QA review — V9 80/68 ps batch

Scope: mechanical numerical review only. No physical interpretation, event classification, mechanism claim, or solver rerun is performed here.

## Integrity and units

- All four run QA records report a valid immutable raw SHA before/after analysis, finite values, monotone stored time, exact registered probes, and no interpolation/resampling.
- Each raw contains 39,999 stored samples over 0.0–399.99 ps. The configured `.tran` step is 0.01 ps, while observed stored increments range from approximately 0.01 to 0.02 ps (`uniform_time_grid=false`); all derived integrals use those actual timestamps. This does not establish timestep convergence.
- JoSIM raw `P(...)` is retained in radians. Each column is independently unwrapped; `Δphase/(2π)` is shown only as navigation arithmetic.
- Voltage integrals use the raw time column in seconds and trapezoids over actual stored samples in the registered half-open `[start,end)` round windows. Signed, positive, and negative areas remain separate.
- Output bit order is LSB→MSB `[S_D0_OUT,…,S_D6_OUT,DFF_O]`; display order is MSB-first.
- Event classifier is absent. `event_count_per_bit=UNKNOWN`, `observed_bits=UNKNOWN`, and arithmetic/timing status is `INCONCLUSIVE` for all cases.
- The DFF internal B1/B7 P/V columns were not part of the frozen focus set; bit7 same-JJ phase/area cross-check is `UNKNOWN`.
- Timestep convergence and sensitivity are `UNKNOWN` (one registered DT only).

## Independent spot check

Independent Python `csv`/trapezoid re-read of A111 raw, using the raw timestamps and exactly `[110,190)` ps for `P(B_J9|XT1_D3)` / `V(B_J9|XT1_D3)`:

| Quantity | Independent recompute | Stored metrics | Check |
|---|---:|---:|---|
| Samples in window | 8,000 | 8,000 | PASS |
| Phase delta | 0.4221902 rad | 0.4221902 rad | PASS |
| Phase delta / 2π (navigation) | 0.06719365725495591 | 0.06719365725495591 | PASS |
| Same-JJ voltage area | 1.389453140781914e-16 V·s | 1.389453140781914e-16 V·s | PASS |
| Voltage area / Φ0 (navigation) | 0.06719365495084564 | 0.06719365495084564 | PASS |
| Phase-minus-area arithmetic | 2.3041102636955912e-9 turns | 2.3041102636955912e-9 turns | PASS |
| `V(S_D3_OUT)` signed area | 7.4976009472091755e-19 V·s | 7.4976009472091755e-19 V·s | PASS |

This arithmetic consistency is not an SFQ count or a product-bit classifier. The A111 raw SHA checked before and after the independent read was unchanged: `a264434b65361a184f5817efce42b25001b90203b309042ce84ad9f5c1cd2add`.

## A109 postprocess recovery

A109 solver exit code was 0 and its raw was preserved. The first postprocessor revision requested unregistered `P(B7|XDFF)` and failed. The run was not repeated. The failed `result.json`/`RUN_MANIFEST.json` are retained under `runs/A109_V9_A0_B0_80P68/postprocess_attempts/001/`; the corrected postprocessor marks the missing DFF internal cross-check `UNKNOWN`, re-QA'd the same raw, and verified the raw SHA remained `d46f0c8ccce28cff2aaf590089f07a878135bbcd5235489c99334856a6d1bbe6`.
