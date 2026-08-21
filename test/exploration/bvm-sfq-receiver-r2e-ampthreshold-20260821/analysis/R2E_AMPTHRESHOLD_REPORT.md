# R2-E quasi-static switching-amplitude threshold — recovered artifact package

**Tier:** Exploration / EXPLORATORY
**Parent exploration:** `test/exploration/bvm-sfq-receiver-r2d-duration-20260821` (checkpoint `32e1143cab52cfdbdcc15d49e2dfead1e7b24032`)
**Head before experiment:** `32e1143cab52cfdbdcc15d49e2dfead1e7b24032`
**Runs commit:** `8c95eb683333fbc982d60e245ab9d983e818fe25`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis.

## Recovery note

The runs commit `8c95eb6` contained raw CSVs, inputs, logs, and manifest but omitted the declared analysis artifacts (`r2e-summary.json`, this report, `REVIEW.md`). This package was regenerated **from the committed raw CSVs only; JoSIM was not re-run**. Raw SHA-256 values match the committed `sha256sums.txt` exactly (a40u0 `227581dc…`, a45u0 `62ba0dd1…`, a50u0 `91018c26…`), so the raw evidence is intact and no re-simulation was required.

## Verdict

**`NO_THRESHOLD_IN_BOUNDED_MATRIX`.**

No amplitude in {4.0, 4.5, 5.0} µA produced a complete 2π transition of B_OUT at FWHM = 20 ps. The junction asymptotically approaches Ic (gaps: 140 / 18 / 8 nA) but never crosses it. All three points were therefore executed — the sequential stop rule was **not violated**, because no earlier point qualified.

## Answers to the audit questions

### 1–3. Largest continuous B_OUT phase segments

| Point | amplitude | largest monotonic segment (turns) | span | same-segment V-area residual |
|---|---:|---:|---|---:|
| a40u0 | 4.0 µA | **0.101389** | 110.1–170.0 ps (decreasing leg) | −3.8e-08 turn |
| a45u0 | 4.5 µA | **0.123538** | 111.1–170.0 ps (decreasing leg) | −3.8e-08 turn |
| a50u0 | 5.0 µA | **0.154960** | 113.1–170.0 ps (decreasing leg) | −4.9e-08 turn |

Each is the relaxation leg of a reversible quasi-static excursion; the mirror-image rise legs during the pulse are comparable in magnitude (whole-run segments >0.02 turn are exactly three per run: initial bias establishment +0.1152, rise, fall).

### 4. First point satisfying Δφ/2π ≥ 1 with consistent area

**None.** Zero complete-2π segments exist in any of the three runs (`n_complete_2pi_segments = 0` everywhere); hence no qualifying event and no threshold within the matrix.

### 5. Complete-transition bookkeeping

Not applicable — zero complete transitions occurred anywhere:
- number of complete 2π transitions: **0** in every run;
- retrap after pulse: trivially clean — each run returns exactly to its pre-pulse equilibrium (net whole-run phase drift = +0.12341 turn in all three runs, which is solely the initial φ=0 → arcsin(0.7)/2π bias-point establishment);
- multi-turn: none;
- free-running: none;
- POST window (130–170 ps): phase range ≤ 0.0033 turn with V decaying monotonically to −0.00 µV — stable settling, not running.

### 6. Peak I(B_OUT) vs Ic

| Point | peak I(B_OUT) (µA) | gap to Ic=10 µA |
|---|---:|---:|
| a40u0 | 9.8601 | 139.9 nA |
| a45u0 | 9.9820 | 18.0 nA |
| a50u0 | 9.9920 | 8.0 nA |

The junction approaches Ic asymptotically but never reaches it. At the plateau the supercurrent channel sits at φ ≈ 80–85°, creeping toward π/2 at only ~1.3 turn/ns (V ≈ 2.7 µV). Closing the remaining 5–6° would need ~11–14 ps, but the triangular drive falls away within ~10 ps of the peak — **the drive decay wins the race against the phase creep**. This is why +25 % amplitude yields only logarithmic gap reduction (140 → 18 → 8 nA).

### 7. Dynamic current allocation at the I_BOUT peak instant

| Point | I_DIR injected | I_BOUT | I_LSEC | I_R_DAMP | V(N_SEC) |
|---|---:|---:|---:|---:|---:|
| a40u0 | 2.90 µA | 9.860 µA | +1.12 µA | +0.14 µA | ~14 µV |
| a45u0 | 3.21 µA | 9.982 µA | +1.47 µA* | +0.18 µA* | ~17.9 µV |
| a50u0 | 4.60 µA | 9.992 µA | +1.80 µA* | +0.22 µA* | ~21.9 µV |

*KCL closes as i_BOUT = I_BIAS(7) + I_DIR − I_LSEC − I_RDAMP at every snapshot. The pattern: the junction absorbs current only up to its sin(φ) limit near π/2; beyond that, every extra microamp of injection is diverted into the L_SEC/R_SEC_LOAD branch (~12 Ω class) and the 100 Ω damper as the node voltage rises. The shunt network, not the junction, absorbs the amplitude increase.

### 8. Storage guard

Preserved in all runs: JM1 post median = +5.911 rad, JM2 = +0.31 rad class, logical-state signs intact; background is logical1-init/no-READ identical to R2-C/D.

### 9. Sequential stop-rule compliance

All three points executed because **no point qualified** — ascending order 4.0 → 4.5 → 5.0 with per-run qualifying checks; stop rule ("stop at first qualifying") never triggered. Compliance: **yes**.

## Observed

1. Largest monotonic segments grow sub-linearly with amplitude: 0.1014 / 0.1235 / 0.1550 turn for 4.0 / 4.5 / 5.0 µA.
2. Peak junction current saturates near Ic: 9.860 / 9.982 / 9.992 µA; gaps shrink by roughly one order of magnitude per +0.5 µA.
3. Plateau-phase creep is slow (~µV-scale V); drive decay arrives before π/2 is reached.
4. All excursions fully reversible; POST windows stable; storage preserved; no ringing/multi-turn/free-running.
5. Charges delivered: 80 / 90 / 100 uA·ps (= 0.08 / 0.09 / 0.10 fC).

## Derived

1. Amplitude-to-gap relation: log10(gap[nA]) falls from ~2.15 to ~0.9 across +1 µA — logarithmic convergence, no threshold crossing in sight within small increments.
2. Ceiling identity continues to hold: phi_max tracks arcsin(I_peak/Ic)/2π (e.g., a50u0: arcsin(0.9992)/2π = 0.2437 vs observed peak 0.2784-turn excursion including dynamic overshoot; plateau value matches).
3. Bounded comparison to the real transformer chain (R2-B): chain delivers +1.46 µA effective junction spike / 0.026 turn response — far below even the 4.0 µA direct-drive point's 0.101 turn; the output-stage requirement under this shape/topology/bias is "close the last nA-scale gap faster than the drive decays", which the chain does not approach.

## Inference (falsifiable)

Within this fixture the amplitude axis alone cannot switch the junction: past ~96 % of Ic the operating point becomes a creep race between phase advance (set by µV-scale node voltage) and drive decay (set by the 20 ps triangle). The binding constraints are the shunt diversion (L_SEC branch + damper) that caps junction current, and the falling drive. Switching requires changing the race conditions — flatter/longer drive top, reduced diversion, or a structurally different activation mechanism — not more amplitude of the same shape.

## Unknown

1. Whether a flat-top (trapezoidal) drive at 4.5 µA lets the creep reach π/2 (recommended single next test).
2. Post-switching retrap/one-shot behavior — still never observed in any R-series experiment.
3. Quantitative sensitivity of the diversion to R_SEC_LOAD (frozen here).
4. Timestep convergence of the near-critical creep (single dt setting).
5. jjmit R0-channel details in the near-critical regime.

## Artifacts

- Runs commit: `8c95eb683333fbc982d60e245ab9d983e818fe25` (raw/inputs/logs/manifest)
- This recovery commit: analysis/r2e-summary.json, R2E_AMPTHRESHOLD_REPORT.md, REVIEW.md, regenerated sha256sums.txt
- No raw, netlist, or manifest science content changed; no JoSIM re-run performed.
