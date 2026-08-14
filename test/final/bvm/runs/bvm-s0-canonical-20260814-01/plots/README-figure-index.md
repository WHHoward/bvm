# BVM-S0 figure index — 2026-08-15 (v2, active-netlist correct)

> **建议阅读路径（教学优先）**：先打开 **`bvm-s0-story.html`**（guided visual
> story，中文叙事，四幕：实验如何进行 → 观察到什么 → 内部机制（折叠）→ 为何
> INCONCLUSIVE + 结论边界），最后可用其附录 **Explore raw traces** 检查任意
> run/window。本文件是 provenance / figure documentation，不承担主要教学职责。
> 静态图 Look for：Source figure 看 positive/negative 响应的幅度、极性、描述性
> 时序差异；Storage figure 看 PRE separation 与 POST−PRE 是否出现 gross
> inversion；Control figure 看 control 处于极低幅 residual 但其 latency
> diagnostic 仍触发已注册数值 blocker；Convergence figure 看"接近"与"满足全部
> 判定条件"是两个不同命题。

## Data sources (all frozen, no JoSIM re-run)

- Raw CSVs: `test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/<case>/<step>/run-01.csv`
  (12 runs; 4 cases × 0.1/0.05/0.025 ps; 170 ps; closed by S0-002 evidence-seal 59 entries)
- Deterministic corrected data: `research/tasks/JH-20260814-BVM-S0-004/attempts/A01/corrected-analysis.json`
  (values verified byte-consistent with raw in S0-004; reconstruction_matches_frozen_json=true)
- Audit boundary: `research/tasks/JH-20260814-BVM-S0-004/audits/C02/verdict.yaml`
  (artifact VALID, scientific disposition INCONCLUSIVE)
- Generator: `plots/plot_bvm_s0.py` (stdlib + matplotlib; rerun `python3 plots/plot_bvm_s0.py` from repo root)

Every number shown was read from the CSVs/JSON at render time. The generator
embeds observed / derived / inference labels; no value is hand-filled.
Programmatic cross-checks (peaks, platform means, phase-area relations)
reproduce raw recomputation to 1e-12. Topology figures follow the **active
uncommented** `bvm_cell.cir` connectivity (SE→N3 via R_SE+L_PSE; WL/BL→N1;
no N4/N7; N3–N6 bridge is R_S//L_S3); verified programmatically against the
netlist.

## Core set (5 visuals — group-meeting front material)

| # | File | Scientific question | Data source | Can claim | Cannot claim |
|---|---|---|---|---|---|
| 1 | `fig1-timing-conceptual.png` | How was the experiment run (timing) and what is the conceptual structure? | frozen design (windows registered before execution) + active netlist | registered windows, write-like initialization labels, conceptual connectivity | logical 0/1 mapping, persistent storage proof |
| 2 | `fig2-source-response.png` | What V(SL1) follows the read pulse from each initialization vs matched controls? | raw CSV 0.025 ps + corrected peaks | state-conditioned source voltage response (positive ≈ +0.89–0.90 mV @5 ps; negative ≈ −0.31 mV @10 ps; controls 15–18 nV); I_load ≈ V(SL1)/12 Ω | logical read0/read1, resolution-independent baseline, receiver reception |
| 3 | `fig3-storage-signatures.png` | What are the PRE operational signatures and POST−PRE deltas per JJ/timestep? | corrected JSON (platform) | operational phase signatures; PRE separation; no gross inversion after read | logical 0/1, fluxoid number, state preservation |
| 4 | `fig4-timestep-comparison.png` | Do full read waveforms agree across 0.1/0.05/0.025 ps? | raw CSV, full [94,130) ps | full-waveform visual comparison per read case | convergence verdict (registered rule says INCONCLUSIVE) |
| 5 | `fig5-control-residual-blocker.png` | What is the matched-control residual and why is S0 INCONCLUSIVE? | raw CSV, nV/nA scale | controls are low-amplitude residuals (15–18 nV, 1.3–1.5 nA); their peak-latency shows grid sensitivity; the registered 0.1→0.05 ps latency difference 0.85 ps > 0.5 ps band is the sole INCONCLUSIVE blocker | changing the verdict or the registered rule; calling control latency a read response |

## Appendix / supporting materials

| # | File | Role |
|---|---|---|
| A1 | `figA1-detailed-topology.png` | Detailed ACTIVE netlist topology (SE→N3; no N4/N7; R_S//L_S3) — technical reference |
| A2 | `figA2-source-current.png` | I(L_SL) — Ohm/KCL-linked to V(SL1) via the fixed 12 Ω load (same source information) |
| A3 | `figA3-phase-area-identity.png` | Direct-JJ phase–area crosscheck — same-JJ Josephson-linked data-path consistency check, NOT independent physical evidence; residual view, no tolerance |
| A4 | `figA4-project-pipeline.png` | Project/status pipeline — historical accepted nodes solid, future/proposed dashed (no skip from current status to receiver) |

## Legend / conventions

- Read cases: warm hues (positive `#d1495b`, negative `#4f86c6`); controls:
  light tints (positive `#d9a0aa`, negative `#a9c3dd`); timesteps: same-hue
  ramp 0.1→0.025 ps (`#c7c7c7 → #333333`); JJs: JM1 blue `#1f6fb2`,
  JM2 orange `#e07b00`. Identity is never color-alone (labels + legend).
- All waveforms use the CSV actual time axis; source window `[94,130) ps`;
  phase windows `[80,90)` (pre), `[94,108)` (activity), `[140,150)` (post);
  probe directions per design doc (JM1 `N1→n_jm1o`, JM2 `n_jm2i→N2`,
  V(SL1) `SL1→0`, I(L_SL) `N8→SL1`), vts=+1, rd=+1.
- Phase values are raw radians (turns = rad/2π shown where labeled).
- In the fixed 12 Ω fixture, I(L_SL) ≈ V(SL1)/12 Ω (KCL/Ohm); the current
  figure is supporting, not an independent second evidence.

## Interactive story (self-contained HTML)

`bvm-s0-story.html` — guided visual story (中文叙事, four acts +
boundary + Explore raw traces appendix), generated by `generate_story.py`
(Plotly JS embedded; no CDN; all 12 frozen CSVs + corrected summary embedded).
Act 2 shows V(SL1) as the core source-result figure (I Ohm-linked, figA2);
Act 3 (JM1/JM2) is collapsed; Act 4 presents the 3-step INCONCLUSIVE decision
with control-residual wording (grid sensitivity; frozen criterion executed).

The `.html` is git-ignored (project rule `test/**/*.html`); regenerate locally:

```bash
cd /home/howard/JoSIM
python3 test/final/bvm/runs/bvm-s0-canonical-20260814-01/plots/generate_story.py
# -> test/final/bvm/runs/bvm-s0-canonical-20260814-01/plots/bvm-s0-story.html
```

Deterministic: same frozen inputs → byte-identical HTML (verified).

## Static figure regeneration

```bash
cd /home/howard/JoSIM
python3 test/final/bvm/runs/bvm-s0-canonical-20260814-01/plots/plot_bvm_s0.py
```

Deterministic: same frozen inputs → byte-identical PNGs (matplotlib fixed
seed not required; no randomness in the script).
