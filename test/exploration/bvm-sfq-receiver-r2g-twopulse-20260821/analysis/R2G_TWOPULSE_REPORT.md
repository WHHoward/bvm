# R2-G two-pulse retrigger at the h20 operating point

**Tier:** Exploration / EXPLORATORY
**Parent exploration:** `test/exploration/bvm-sfq-receiver-r2f-dwell-20260821` (checkpoint `ebd518aa5ab6dfff2b1ef6b7c42c21c71d79e115`)
**Head before experiment:** `ebd518aa5ab6dfff2b1ef6b7c42c21c71d79e115`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`, `.tran 0.0125p 300p` (stop extended for the two-event question — recorded deviation), PHASE analysis.

## Verdict

**`REPEATABLE_TWO_PULSE_SINGLE_SLIP`.**

Two identical h20 trapezoids (4.5 µA peak, 20 ps rise/fall, 20 ps flat-top hold, envelope gap 60 ps) each produced **exactly one qualifying complete 2π slip**, with a clean retrap/rearm in between:

- Pulse 1: one complete segment, Δφ = 1.033314 turn (83.8–138.5 ps), area residual +3e-08 turn;
- Inter-pulse gap: zero segments >0.02 turn; phase settles back to exactly equilibrium+1 turn (1.1234) with V → −0.000 µV by 200 ps;
- Pulse 2: one complete segment, Δφ = 1.033315 turn (200.0–258.5 ps), area residual −6e-07 turn;
- Total: exactly two slips; final settled phase 2.1234 turn = initial equilibrium + 2 turns;
- No missed second event, no multi-fire, no free-running, no incomplete rearm;
- Storage preserved (JM1 = +5.911 rad, JM2 = +0.317 rad at 280–295 ps).

The two events are numerically near-identical (Δφ differs by 1e-06 turn between pulses), indicating no history-dependent threshold shift at this separation.

## Separation choice (measured, not arbitrary)

From R2-F raw h20: after the ~132.4 ps crossing, phase deviation from final decays to +0.0055 turn by 150 ps, +0.0013 turn by 156 ps, +0.0005 turn by 160 ps; |V| < 0.3 µV by 160 ps. The first envelope ends at 144.51 ps; a 60 ps end-to-start gap therefore provides ≥40 ps of fully quiet rearm time — safely beyond the observed settling (~15 ps). Not swept further, per plan.

## Recorded deviation

Simulation stop extended from 170 ps to 300 ps (two-event question cannot fit in 170 ps); analysis windows redefined per pulse (P1 [80,165], gap [145,204], P2 [200,290], post [265,300]). All other numerical settings unchanged. This deviation is declared in the manifest and does not touch any accepted artifact.

## Answers to the required questions

1. Pulse 1 exactly one complete local 2π slip? **Yes** (1 qualifying complete segment).
2. Retrap after pulse 1? **Yes** (settled 1.1240 turn @160 ps → 1.1234 @200 ps, V → 0).
3. Same local operating condition before pulse 2 (mod 2π)? **Yes** (phase = equilibrium+1 turn = initial + 2π·1; V = 0).
4. Pulse 2 again exactly one complete slip? **Yes**.
5. Total exactly two slips? **Yes** (final phase = initial + 2 turns exactly).
6. Missed second event / multi-fire / free-running / incomplete rearm / history-dependent threshold shift: **none observed** (gap and post windows contain zero segments >0.02 turn).

## Observed

1. Both pulses produce single qualifying slips with nearly identical Δφ (1.033314 vs 1.033315 turn).
2. Both transitions complete during their drive's fall edge (~138.5 ps and ~258.5 ps segment ends), consistent with the R2-F creep-completion picture.
3. Inter-pulse window is completely quiet; rearm is exact modulo 2π.
4. Peak |I(B_OUT)| across the run: 10.010 µA (same as R2-F h20).

## Derived

1. Slip-count fidelity: 2 pulses → 2 slips (ratio exactly 1:1 at this operating point and separation).
2. Phase bookkeeping closes exactly: final = initial + 2.0000 turns within 2e-04 turn.

## Inference (falsifiable)

At this operating point the output stage behaves as a repeatable single-slip element under separated identical drives: the post-event state is equivalent to the pre-event state plus one flux quantum on the junction phase, and the switching condition is restored. Within direct-drive scope, the "one input pulse → one local phase slip" primitive now has two-pulse evidence. What remains unproven is everything downstream: delivery of such a drive by a real transformer chain, SFQ pulse shaping, JTL reception, and cascade behavior.

## Unknown

1. Minimum safe separation (only 60 ps tested; settling data suggests ≥~40 ps, untested below that).
2. Behavior at higher pulse counts (2 tested; N-pulse endurance unknown).
3. Whether the real transformer chain can deliver the required ~4.5 µA/20 ps-hold drive profile at all (R2-B says it is far away).
4. Timestep convergence of both events (single dt setting).
5. Parameter-margin robustness of the dwell requirement.

## Next step (per directive: transition to architecture comparison)

Per the exploration directive, R2-H (further direct-drive tuning) is not started. The next work item is a **receiver architecture comparison** — direct receiver vs lightweight accumulation/quantizing adapter vs paper-style QB — assessed against the now-calibrated output-stage requirement (≈4.5 µA-class effective junction drive with ≈20 ps near-critical hold). That comparison is a new task and requires its own preregistration; it is not started here.

## Artifacts

- Manifest (preregistered): `manifest.yaml`
- Inputs: `inputs/tp60.cir`, `inputs/tp60-receiver.cir`
- Raw: `raw/tp60/run-01.csv` (23,999 rows)
- Analysis: `analysis/r2g-summary.json`
- Hashes: `analysis/sha256sums.txt`
