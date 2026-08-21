# R4-A weak-mutual fluxoid capture-only — execution report

**Tier:** Exploration / EXPLORATORY
**Preregistration:** `manifest.yaml` at checkpoint `573c779` (analytic precheck `R4A_SINGLE_POINT_WORTH_TESTING`; mailbox-only commit `b5b3421` does not alter the contract)
**Head before experiment:** `b5b3421`
**Solver:** `build/josim-cli` v2.7.2837d13, SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

## Main verdict

**`R4A_INCONCLUSIVE` — simulation formulation failure; no physics result exists.**

The preregistered floating capture loop (L_H=100 pH in series with J_SET AREA=0.05, +3 µA floating bias branch, mutually coupled to L_TX with |K|=0.80) is **not solvable by JoSIM as specified**: the modified-nodal-analysis matrix is singular because the two-node loop island (N_CAP1/N_CAP2) has no DC path to ground through any resistive element. All four matched cases abort identically before producing any CSV.

## What happened, exactly

1. Fixture built per manifest: R0b front end unchanged; L_H+B_SET floating loop added; `K_TX_LH L_TX L_H -0.80` (negative sign implements the preregistered additive winding polarity for the raw read1 negative I(L_TX) lobe); bias source placed across the J_SET terminals as a floating branch (`I_SET_BIAS N_CAP2 N_CAP1 pwl(... 3U ...)`).
2. First run attempt failed on a netlist naming issue (JoSIM junctions require the `B` prefix; `J_SET` renamed to `B_SET` — syntax fix only, no semantic change).
3. Second attempt: all four cases abort with
   - `W: Controls / Unknown device/node B_SET|XCAP` (probe store fails because simulation never built the device list), and
   - `E: Simulation / Matrix is singular. Matrix will have no solution.`
4. No raw CSV was produced for any case.

## Why the matrix is singular

The island {N_CAP1, N_CAP2} contains only L_H (inductor), B_SET (junction: ideal supercurrent + internal RN/R0 between its own two nodes), and the bias current source. Every element is a two-terminal branch *between the same two floating nodes*; no branch connects either node to the grounded part of the circuit except the mutual inductance, which couples flux but provides no galvanic reference. In MNA, the two node-voltage unknowns are then determined only up to a common offset — the stiffness matrix has a null direction — and JoSIM correctly reports singularity.

Physically this is a gauge redundancy (absolute node voltage inside an isolated superconducting island is meaningless; only the phase difference across B_SET matters). The circuit is meaningful physics but is not expressible in JoSIM's grounded-reference MNA without adding some reference element.

## Why we stopped instead of fixing

The manifest explicitly pre-registered this decision point:

> "external_resistors: none in the initial point; use only the instantiated jjmit damping **unless execution preflight reports an invalid floating-loop formulation, in which case stop rather than add damping**."

The preflight did report exactly that condition. Adding a ground-reference resistor (even a 1 GΩ gauge-fixing bleed) would change the declared single point and belongs to a revised preregistration, not to silent execution-time repair. Per the failure boundary, this outcome falsifies nothing about fluxoid capture physics — it is `INCONCLUSIVE`, not `NO_PERSISTENT_READ1_STATE`.

## Failure boundary

- Falsified: the current formulation of the initial point (floating two-node loop without a reference element) as directly expressible in JoSIM.
- Not falsified: weak-mutual fluxoid capture as a concept; the analytic margin estimate (read1 worst-case additive lobe 5.217 µA vs Ic=5 µA; read0 3.791 µA); any other architecture family.
- Guards: not evaluable (no simulation ran); canonical BVM untouched; no existing artifacts modified.

## Required follow-up decision (owner: user/Luna+Sol)

Any retry needs one preregistered amendment choosing among:

1. **Gauge resistor:** one large-valued resistor from N_CAP1 (or N_CAP2) to ground, value preregistered (e.g., 1 GΩ) with a stated bound on its current-draw perturbation (~V/1GΩ ≈ fA-scale at µV node voltages);
2. **Capacitive reference:** a small capacitor to ground (pure AC reference, no DC path) — may still leave the DC problem unsolved in MNA;
3. **Galvanic tie re-interpretation:** connect the loop intentionally to the N_TRIG side through a designated high-impedance element, changing the topology class (no longer "floating").

Option 1 is the standard SPICE practice and physically inert at the µV scale; options 2–3 change the contract more substantively. This choice must be made before any rerun; it is not made here.

## Artifacts

- Preregistration: `manifest.yaml` (unchanged, at `573c779`)
- Inputs: `inputs/r4a-receiver.cir` + four case netlists (as-built, including the `B_SET` syntax fix)
- Logs: four stderr files recording the singular-matrix aborts (preserved as evidence)
- Raw: none produced (aborts before output)
- Analysis: this report; no summary JSON metrics exist because no simulation data exist
