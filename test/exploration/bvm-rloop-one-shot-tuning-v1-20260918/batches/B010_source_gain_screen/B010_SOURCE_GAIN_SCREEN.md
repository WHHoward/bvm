# B010 — BVM source-gain sensitivity screen

Mechanical execution status: **PASS**

All seven registered variants ran PASSIVE N1 (`0001`) and N4 (`1111`). Raw and plot QA are recorded in `B010_EXECUTION_MANIFEST.json` and `B010_SOURCE_GAIN_SCREEN.csv`.

## Scientific review boundary

N1 source-gain metrics, Gate-S/Gate-R/Gate-Z classification, state-selective/delivery direction classification, gain-efficiency derivation, and CLOSED recommendations are intentionally **not computed here**. They remain `SCIENTIFIC_REVIEW_REQUIRED` until the explicit scientific-review authorization is supplied.

No QB/JTL/terminal source was modified. No CLOSED follow-up, 2-D sweep, or automatic ranking was performed.

## Mechanical variant table

| variant | case | changed parameter | new value | raw QA | plot QA | solves |
|---|---|---|---|---|---|---:|
| B0 | U040_b010_b0_baseline | NONE | baseline | PASS | PASS | 2 |
| G1 | U041_b010_g1_js1_area_046 | JS1_AREA | 0.46 | PASS | PASS | 2 |
| G2 | U042_b010_g2_lm3_8p0 | LM3 | 8.0p | PASS | PASS | 2 |
| G3 | U043_b010_g3_lm3_9p0 | LM3 | 9.0p | PASS | PASS | 2 |
| G4 | U044_b010_g4_rsl_10 | RSL | 10 | PASS | PASS | 2 |
| G5 | U045_b010_g5_se_110 | CONTROL_SE_AMP+READ_SE_AMP | 110u | PASS | PASS | 2 |
| G6 | U046_b010_g6_rs_3p5 | RS | 3.5 | PASS | PASS | 2 |
