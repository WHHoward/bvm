# LS3 timing-window vs. Lin-coupled mutual-RL auxiliary

This is a read-only cross-experiment comparison generated after both independent
experiments completed. It runs no JoSIM and assigns no scientific winner.

## Frozen provenance

- Common parent: `b904851be588ca88d40cf1700d5fef7ce3d889ed`.
- Experiment A commit: `100d1f52147994714e603c4d027a8021f664b930`.
- Experiment B commit: `f3b9cf0bfbc8322e11aa8bbdc32fb91cbeaa347f`.
- A and B used independent experiment directories, raw files, provenance and
  Drive packages. No result from one experiment was used to choose parameters
  in the other.
- All response values below are ordered phase-chain/navigation evidence plus
  registered downstream corroboration; they are not literal SFQ counts.

## Facts-only comparison

| route | physical/counterfactual | added complexity | N2 | N3 | N1/N4 if tested | first-handoff drift | key limitation |
|---|---|---|---:|---:|---|---|---|
| LS3 replay 0.2 ps | ideal instance-specific current replay | `L_S3` replay PWL; physical `R_S` retained | 2 | 4 | n/a | BJ1/BJ2 max 0.2 ps | counterfactual ideal source; only N2/N3 tested |
| LS3 replay 0.3 ps | ideal instance-specific current replay, reused | same LS3 replay fixture | 2 | 3 | 1-like / 4-like known from prior validation | N2 max 0.2 ps; N3 max 0.1 ps | active ideal source; reused raw, not rerun here |
| LS3 replay 0.4 ps | ideal instance-specific current replay | `L_S3` replay PWL; physical `R_S` retained | 2 | 3 | n/a | BJ1/BJ2 max 0.3 ps | counterfactual ideal source; only N2/N3 tested |
| mutual K=.1 | passive linear mutual-RL model inside experimental QB clone | `L_AUX=10 pH`, `R_AUX=20 Ω`, `K=.1`, `M=0.387298 pH` | 2 | 4 | not tested | 0 ps | fixed K point; no N1/N4 conditional trigger |
| mutual K=.2 | passive linear mutual-RL model inside experimental QB clone | `L_AUX=10 pH`, `R_AUX=20 Ω`, `K=.2`, `M=0.774597 pH` | 2 | 4 | not tested | 0 ps | fixed K point; no N1/N4 conditional trigger |
| mutual K=.3 | passive linear mutual-RL model inside experimental QB clone | `L_AUX=10 pH`, `R_AUX=20 Ω`, `K=.3`, `M=1.161895 pH` | 2 | 4 | not tested | 0 ps | fixed K point; no N1/N4 conditional trigger |

The LS3 `.3 ps` row is the prior accepted N2/N3 branch-decomposition evidence;
the `.2/.4 ps` rows are the new timing-window cases. Experiment B's K=0 no-op
gate passed, and all three positive-K fixed pairs retained the mechanical
N2=2 / N3=4 pattern, so the preregistered conditional N1/N4 pair was not run.

## Auxiliary-loop observations

For B's positive-K cases, the measured `I(L_AUX)` focus-window peak absolute
values increased across K in the registered raw records. The `R_AUX` signed
`V·I` energy and `I²R` energy were recorded on the actual stored grid and were
nonnegative within the registered numerical check. These are properties of the
finite simulated passive RL model; they do not establish directional isolation,
hardware realizability, or a physical delay implementation.

## Delivery records

| experiment | new physical solves | package SHA-256 | bytes | Drive ID |
|---|---:|---|---:|---|
| `bvm-rloop-ls3-delay-window-v1-20260916` | 4 | `2052fa76071ebbd399e0196a6512f99f028fd7a663a75c376c67cc70bd3fe0c7` | 8,334,460 | `1CY63ltyMrb47f5p_P5Guej52qHTsr-j5` |
| `bvm-qb-lin-mutual-rl-aux-v1-20260916` | 8 | `852b5955636603a05e79d09e4956f13bccf67d706873d03a5f29e16b9c58ebde` | 13,816,298 | `129mqIOyWwAF50Il4aO1FeJbHozrDkbVN` |

Both package QA records state `contains_all_new_run_raw=true`,
`contains_reference_raw_copies=false`, and `contains_delivery_manifest=false`.
The experiment-level result files remain `SCIENTIFIC_REVIEW_REQUIRED`; no final
winner, mechanism, physical solution or process-robustness claim is assigned.
