# R5-B QB load-line / shunt necessity test — execution report

**Tier:** Exploration / EXPLORATORY
**Preregistration:** `manifest.yaml` (DRAFT `8ad2631`)
**Head before experiment:** `e5dd13aa1b0cfd4b13b1b2fc865e62f7093c39cf`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 170p`, PHASE analysis; four matched cases; two wiring iterations (both preserved).

## Main verdict

**`R5B_STILL_BOUNDED_OSCILLATION` — with a decisive structural finding.**

Adding the minimal load-line branch did not convert the read1 oscillation into a slip. In its functionally active wiring (shunt across B_SET), the branch acted as **plain extra junction damping**: the phase excursion *collapsed* from R5-A's [−0.25, +0.18] turn to [−0.07, 0] turn, J_SET current stayed within [−1.7, 0] µA vs Ic=5 µA, and zero complete segments occurred anywhere. The shunt-across-the-SET suppresses escape rather than enabling it.

## Execution history (both iterations preserved)

1. **v1 wiring (raw/):** shunt branch placed N_A→ground. Result: functionally absent — N_A is pinned by R_GAUGE+RJ1 to ~0 V, so the branch saw zero volts and carried ≤1.8e-22 A. Diagnosed as a wiring error: in paper QB, RJ1/BJL1 hang from the *dynamic* loop node.
2. **v2 wiring (raw-v2/):** shunt moved across B_SET itself (N_B→N_A). Functionally active (BJL1 up to 3.4 µA, RJ1 up to 1.43 µA) and decisive.

## Per-case results (v2, functionally active)

| Case | complete segs | qualifying | I_LQB held (µA) | \|BJL1\| max (µA) | \|V_SET\| max (µV) |
|---|---:|---:|---:|---:|---:|
| read1 | 0 | 0 | 0.7617 | 3.400 | 143.3 |
| read0 | 0 | 0 | 0.7612 | 2.632 | 58.0 |
| logical1 ctrl | 0 | 0 | 0.7612 | 2.441 | 58.0 |
| logical0 ctrl | 0 | 0 | 0.7612 | 2.432 | 58.0 |

read1 φ range collapsed to [−0.0695, 0] turn (net −0.0368); J_SET current within [−1.700, 0] µA vs Ic=5. Guards preserved everywhere (JM signs; SL/N6 ordering; B_TRIG read1 multi-turn 5.357 turns retained).

## R5-A vs R5-B comparison (required)

| metric | R5-A (no shunt) | R5-B (shunt across B_SET) |
|---|---|---|
| phase excursion | [−0.2496, +0.1844] turn | [−0.0695, 0] turn |
| V(B_SET) peak | 1087.5 µV | 143.3 µV |
| oscillation decay | sustained symmetric plasma oscillation | heavily damped small wobble |
| first escape | none | none |
| second-event risk | none observed | none observed |
| source back-action | none | none |

## Observed / Derived / Inference

**Observed:** the load-line branch, wired across the SET junction, monotonically suppressed every oscillation metric by factors of 3–8 while diverting up to 3.4 µA of signal current into itself.

**Derived:** a resistor directly parallel to the SET junction enters the RCSJ equation as additional damping (1/R_eff = 1/RN + 1/R_shunt + …) — it mathematically cannot lower the escape barrier of that junction.

**Inference:** my "minimal translation" mis-mapped the QB function. In paper QB, RJ1 does **not** sit across BJs; it runs from the dynamic loop node (node 2) to ground while BJs sits in the input arm — the damping applies to the *loop mode* through which bias RB feeds, and the SET junction's escape is enabled by the *bias placement*, not by a shunt across it. The functional unit "load-line" cannot be detached from the QB bias topology and pasted onto an arbitrary junction. A working biased quantizer needs the full three-junction core with its specific bias routing.

## Consequence (per preregistered interpretation plan)

`R5B_STILL_BOUNDED_OSCILLATION` → per plan: **return to full QB core / flux-bias architecture comparison**. Do not add output regeneration; do not iterate further on ad-hoc minimal variants. The R-series has now established, with single-variable evidence:

1. Direct pass-through fails by timescale starvation (R2-C);
2. Damping and coupling are not the bottlenecks (R2-B/R2-A);
3. Sustained near-critical drive works but requires idealized drive (R2-F/G);
4. Passive capture fails by flux shortfall (R4-A);
5. Un-shunted biased quantizer oscillates without escaping (R5-A);
6. Shunting the quantizer junction kills the dynamics entirely (R5-B).

The remaining unexplored region is precisely the full QB core topology with its native bias routing — now supported as the next candidate by elimination plus positive paper precedent.

## Artifacts

- Preregistration: `manifest.yaml` (`8ad2631`)
- Inputs: `inputs/r5b-receiver.cir` (final v2 wiring) + four case netlists
- Raw: `raw/` (v1, functionally-absent wiring) and `raw-v2/` (active wiring) — both preserved
- Analysis: `analysis/r5b-v2-summary.json`, `analysis/r5b-summary.json`
- Hashes: `analysis/sha256sums.txt`
