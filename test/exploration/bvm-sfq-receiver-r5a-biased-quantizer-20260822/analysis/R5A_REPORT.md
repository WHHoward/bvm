# R5-A biased-quantizer single-point feasibility — execution report

**Tier:** Exploration / EXPLORATORY
**Preregistration:** `manifest.yaml` (DRAFT `538603e`; sanity check + oracle amendment `64f67f7`; degree-typo fix `73cefac`)
**Head before experiment:** `73cefac`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis; four matched cases, one run each, no sweeps.

## Main verdict

**`R5A_NO_SET_EVENT`.**

The biased quantizer ran cleanly at the preregistered operating point (bias 4.2 µA, φ_OP = −0.0829 turn), and read1 drove the quantizer state through a **large-amplitude plasma oscillation that crossed the analytic reverse-critical boundary** — but no complete phase slip occurred in any case. read0 and both controls are exactly clean. The threshold mechanism moved the state dramatically further than any previous architecture attempt, yet the crossing did not complete.

## Per-case results

| Case | complete segs (either dir) | qualifying events | I_LQB pre→held (µA) | JM1 post (rad) |
|---|---:|---:|---|---:|
| read1 | 0 | 0 | 1.7135 → 1.7175 | +5.912 |
| read0 | 0 | 0 | 1.7126 → 1.7130 | −5.911 |
| logical1 ctrl | 0 | 0 | 1.7135 → 1.7132 | +5.911 |
| logical0 ctrl | 0 | 0 | 1.7126 → 1.7132 | −5.911 |

Guards all preserved: gauge leakage ≤5.6e-22 A; SL/N6 ordering intact (read1 1.789/1.956 mV vs read0 0.444/0.722 mV); B_TRIG read1 multi-turn range 5.343 turns vs read0 0.189 — source behavior unchanged by the quantizer load.

## The decisive observation (read1)

The causal-window state trajectory:

- Phase excursion from OP: **[−0.2496, +0.1844] turn** — the negative swing **crossed the analytic reverse-critical distance** (−0.1672 turn);
- Loop-current excursion from OP: [−4.398, +4.943] µA;
- |V(B_SET)| peaked at **1087.5 µV** inside the window;
- Net V-area over [97,130): **−0.0265 turn** — zero net slip.

Adversarial reconciliation of the apparent contradiction ("past critical but no slip"): the −0.2496-turn minimum is a smooth plasma oscillation turning point — V passes through zero linearly, I_BSET steady at ~+2.4 µA, no running state. The 1087 µV voltage peak occurs at a *different* time (t=114.04 ps) at φ_rel ≈ −0.014 (near OP) and is the B_TRIG multi-turn burst coupling through C-less mutual coupling into the loop voltage, not a J_SET event. The junction swung hard, but its total energy never concentrated into a unidirectional phase run: the alternating lobes kept reversing the acceleration before escape velocity was reached.

## Why the analytic margin overestimated

The sanity-check angular-margin arithmetic treated the transient as a monotonic push toward the nearer critical angle. In reality the read1 drive is biphasic with ~±5 µA loop-current swings of *alternating sign*: the state oscillates around the OP rather than traveling monotonically. Peak displacement (0.25 turn) exceeded the static boundary (0.167 turn), but displacement ≠ escape — reaching the boundary instantaneously with reversing acceleration does not produce a slip unless the junction enters a sustained running state there.

## Observed / Derived / Inference / Unknown

**Observed:** zero complete events anywhere; read1 state excursion ±(0.18–0.25) turn; loop current swings ±(4.4–4.9) µA; V peak 1.09 mV; controls exactly clean; storage preserved; gauge nil.

**Derived:** net window V-area −0.0265 turn ≈ 0; peak-to-boundary ratio 0.2496/0.1672 = 1.49 (boundary crossed in displacement terms); oscillation is symmetric around OP within ±0.02 turn.

**Inference:** the missing ingredient is not amplitude or bias placement but **asymmetry**: a symmetric biphasic drive around a stable OP produces bounded oscillation regardless of how far the swing reaches. A working quantizer needs either (a) a drive whose net DC component shifts the basin itself (flux-biased digital-SQUID mode), or (b) damping/irreversibility at the crossing so the state cannot swing back — which is precisely the function of QB's BJL1/RJ1 shunt branch that this minimal version deliberately omitted. This is direct evidence for the paper-QB structure being functionally necessary, not incidental.

**Unknown:** whether adding the BJL1-class shunt (making it the full paper-QB core) converts this oscillation into a one-slip event at these flux levels; timestep convergence of the 1.09 mV coupled burst; exact lobe-by-lobe energy accounting.

## Rearm diagnostic

Not run — primary matrix did not PASS (`rearm = UNKNOWN`).

## Boundary

Falsified: the minimal three-element biased quantizer instance (loop + SET JJ + floating bias, no shunt branch) as a standalone threshold converter at this single point. Not falsified: biased-quantizer family with shunt/load-line elements (paper-QB core); output regeneration; JTL/T1 questions (out of scope).

## Artifacts

- Raw: `raw/<case>/run-01.csv` ×4
- Analysis: `analysis/r5a-raw-summary.json`, `analysis/r5a-summary.json`
- Sanity evidence: `analysis/SANITY_CHECK.md`, `analysis/sanity-k0-raw.csv`
- Hashes: `analysis/sha256sums.txt`
