# D3 Carry timing A040/A041 — mechanical evidence brief

Status: both authorized solves completed; artifact validity and mechanical QA are `VALID / PASS`. Scientific interpretation, event classification, SFQ counting, and product-bit decoding were **NOT PERFORMED**. A036 is a read-only reference; no historical run was modified.

| Run | D3 PRE-CB sJTL count | Probes | Raw bytes | Samples | Raw SHA-256 |
|---|---:|---:|---:|---:|---|
| A036 (reference) | 1 | 234 | 94,506,907 | 29,999 | `586ba6eafa62d25bf6cd7a7ea8b533903826616b4b5575a9023f7393b74faf75` |
| A040 | 0 | 212 | 85,514,801 | 29,999 | `3c3ec6904b900e6a3a2c8bbac82431eca05150b3aad58c52feec10b29bf7ae61` |
| A041 | 2 | 222 | 89,494,895 | 29,999 | `e1037690671ff9457b9e032a65332cedf6d0c4f93af55ae44dfc3124521d7792` |

All three use the same stored time extent, 0–299.99 ps; observed stored Δt range is approximately 0.01–0.02 ps. Each new run has solver exit 0, raw hash unchanged by analysis, and standalone plot QA PASS.

## D3 arithmetic in PRE_CLOCK `[121,200)`

`ΔP/(2π)` is navigation arithmetic only. The voltage-area column is the same junction, direction, raw rows, and window divided by Φ₀. These values are not switching or event counts.

| Run | Array last-CB BJ1 ΔP/2π / area Φ₀ | Carry-CB BJ1 ΔP/2π / area Φ₀ | D3 T1 B_J1 ΔP/2π / area Φ₀ | D3 T1 B_J11 ΔP/2π / area Φ₀ | S3 area Φ₀ | C3 area Φ₀ |
|---|---:|---:|---:|---:|---:|---:|
| A036 | 3.917307 / 3.917310 | 1.996821 / 1.996821 | 4.985649 / 4.985648 | 2.012260 / 2.012260 | 0.084644 | 2.007778 |
| A040 | 3.918561 / 3.918562 | 1.997076 / 1.997076 | 4.985824 / 4.985825 | 2.012254 / 2.012253 | 0.084695 | 2.007773 |
| A041 | 3.917005 / 3.917008 | 1.996742 / 1.996742 | 4.985602 / 4.985602 | 2.012262 / 2.012262 | 0.084631 | 2.007779 |

Carry sJTL BJ1 same-JJ phase/area arithmetic in the same window:

- A036 D3 sJTL1: `1.999284 / 1.999284`.
- A040: no D3 Carry sJTL is instantiated.
- A041 D3 sJTL1: `1.999808 / 1.999809`; sJTL2: `1.999262 / 1.999262`.

The D3 T1 B_J2/B_J9/B_J10 raw probes are absent from A036 and therefore remain `UNKNOWN` for that baseline. Their A040/A041 same-JJ arithmetic is in `D3_CARRY_TIMING_SAME_JJ_PHASE_AREA.csv`.

For A040/A041, the additional D3 JJ navigation arithmetic is:

| Run | T1 B_J2 ΔP/2π / area Φ₀ | T1 B_J9 ΔP/2π / area Φ₀ | T1 B_J10 ΔP/2π / area Φ₀ |
|---|---:|---:|---:|
| A040 | 0.026806 / 0.026806 | 0.084656 / 0.084656 | 2.047287 / 2.047286 |
| A041 | 0.026789 / 0.026789 | 0.084591 / 0.084591 | 2.047312 / 2.047312 |

Actual D3 branch-current extrema and charge in the same PRE_CLOCK window are:

| Run | Branch | Direction | Min/Max (µA) | Charge (fC) |
|---|---|---|---:|---:|
| A036 | `I(V_CBU_A_D3)` | DOUT_D3→JOIN | −56.151 / 270.058 | 3.232461 |
| A036 | `I(V_CARRY_IN_D3)` | C_D2→PRE-CB path | −42.643 / 204.337 | 0.164478 |
| A036 | `I(V_CBU_B_D3)` | Carry CB→JOIN | −54.686 / 268.769 | 1.601946 |
| A036 | `I(V_T1_LINK_D3)` | JOIN→T1_D3.I | −38.495 / 345.871 | 4.834407 |
| A040 | `I(V_CBU_A_D3)` | DOUT_D3→JOIN | −47.507 / 263.785 | 3.486203 |
| A040 | `I(V_CARRY_IN_D3)` | C_D2→CB | −60.693 / 169.824 | 0.110548 |
| A040 | `I(V_CBU_B_D3)` | Carry CB→JOIN | −70.806 / 235.259 | 1.246363 |
| A040 | `I(V_T1_LINK_D3)` | JOIN→T1_D3.I | −40.949 / 277.455 | 4.732565 |
| A041 | `I(V_CBU_A_D3)` | DOUT_D3→JOIN | −56.893 / 270.955 | 3.416779 |
| A041 | `I(V_CARRY_IN_D3)` | C_D2→PRE-CB path | −40.483 / 208.032 | 0.103389 |
| A041 | `I(V_CBU_B_D3)` | Carry CB→JOIN | −53.723 / 249.956 | 1.454973 |
| A041 | `I(V_T1_LINK_D3)` | JOIN→T1_D3.I | −45.316 / 311.257 | 4.871753 |

These are branch-current extrema/charge arithmetic, not transported-event counts.

## Timing descriptors and boundaries

The platform's registered local voltage-lobe descriptors give D3 last-input candidates of 166.49 ps (A036), 169.06 ps (A040), and 167.83 ps (A041), corresponding to configured-clock-start margins of 33.51, 30.94, and 32.17 ps. These are descriptive waveform candidates—not JJ switching times, transmitted-event times, or event counts. The raw tables and HTML preserve separate array branch current, previous Carry, each configured sJTL boundary, Carry-CB, JOIN, and T1-input signals; A036/A040/A041 D3 P/V arithmetic is same-JJ and same-window.

| Run | Previous Carry candidate (ps) | D3 Carry-CB output candidate (ps) | D3 T1 input candidate (ps) | DFF data candidate (ps) | DFF candidate margin to 200 ps start (ps) |
|---|---:|---:|---:|---:|---:|
| A036 | 161.12 | 166.49 | 166.49 | 179.05 | 20.95 |
| A040 | 167.10 | 169.06 | 169.06 | 179.09 | 20.91 |
| A041 | 161.15 | 167.83 | 167.83 | 179.06 | 20.94 |

For A041 the two sJTL boundary descriptors are `CARRY_SJTL_IN_D3 = 161.15 ps`, first-sJTL output = no candidate, second-sJTL output / Carry-CB input = `165.83 ps`, Carry-CB output / JOIN / T1 input = `167.83 ps`. A040 has no D3 sJTL probes by design. The T1/DFF clock-voltage peaks remain 202.83/201.00 ps. All these times are the platform's fixed descriptive lobe-candidate navigation, not event or switching times.

For D4–D6, PRE_CLOCK T1 B_J1 ΔP/2π / same-JJ area Φ₀ was:

| Run | D4 | D5 | D6 |
|---|---:|---:|---:|
| A036 | 4.985722 / 4.985723 | 3.994628 / 3.994629 | 2.989622 / 2.989621 |
| A040 | 4.985723 / 4.985723 | 3.994629 / 3.994629 | 2.989620 / 2.989621 |
| A041 | 4.985722 / 4.985723 | 3.994628 / 3.994629 | 2.989622 / 2.989621 |

PRE_CLOCK T1 B_J11 and S/C voltage-area arithmetic for D4–D6 is in the stage CSV. Rounded S/C values are nearly identical across the three rows: D4 `S=0.084648`, `C=2.007929`; D5 `S=−0.000218`, `C=1.999642`; D6 `S=0.084517`, `C≈0.990147` Φ₀ arithmetic.

| Run | DFF_IN area Φ₀ PRE_CLOCK / TOTAL | DFF_O area Φ₀ PRE_CLOCK / CLOCK_EDGE / POST_CLOCK / TOTAL |
|---|---:|---:|
| A036 | 0.990148 / 1.089242 | 0.042076 / 0.181355 / 0.775064 / 1.131988 |
| A040 | 0.990146 / 1.089242 | 0.042074 / 0.181355 / 0.775066 / 1.131988 |
| A041 | 0.990148 / 1.089242 | 0.042076 / 0.181355 / 0.775065 / 1.131988 |

These are signed voltage-area/Φ₀ arithmetic only, not decoded product bits.

DFF input descriptive candidates are 179.05, 179.09, and 179.06 ps for A036/A040/A041; configured global clock start is 200 ps. These are navigation descriptors only. DFF input/output areas by registered window are recorded in the stage table and per-run `metrics.json`.

## Evidence links

- Detailed waveform/current arithmetic: [D3_CARRY_TIMING_SIGNAL_METRICS.csv](D3_CARRY_TIMING_SIGNAL_METRICS.csv), [D3_CARRY_TIMING_STAGE_METRICS.csv](D3_CARRY_TIMING_STAGE_METRICS.csv), [D3_CARRY_TIMING_SAME_JJ_PHASE_AREA.csv](D3_CARRY_TIMING_SAME_JJ_PHASE_AREA.csv).
- Same-schema A036/A040/A041 comparison figures and A040/A041 extended D3 JJ figure are local under `plots/comparison/`; per-run standalone classic plots remain under each run's `plots/`.
- Raw SHA and reconstruction inputs: [RAW_ANALYSIS_HANDOFF_MANIFEST.json](RAW_ANALYSIS_HANDOFF_MANIFEST.json), [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json), [EVIDENCE_MANIFEST.md](EVIDENCE_MANIFEST.md).

Next state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`. No follow-up solve is authorized.
