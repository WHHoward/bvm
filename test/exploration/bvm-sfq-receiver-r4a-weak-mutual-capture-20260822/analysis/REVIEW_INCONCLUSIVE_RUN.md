# R4-A adversarial review of the INCONCLUSIVE disposition

## Scope

The claim under review: "the preregistered floating capture loop is not solvable in JoSIM as specified (singular MNA); execution stopped per the manifest's own preflight rule; verdict `R4A_INCONCLUSIVE` with no physics result." This review checks both the failure diagnosis and the decision to stop.

## Verification of the failure

1. All four matched cases abort with identical errors: probe-store warnings for `B_SET|XCAP` followed by `E: Simulation / Matrix is singular. Matrix will have no solution.` No CSV is produced. Logs preserved.
2. Topology audit of `inputs/r4a-receiver.cir`: the island {N_CAP1, N_CAP2} contains only L_H, B_SET, and I_SET_BIAS — all two-terminal branches between the same two nodes. The only coupling to the grounded circuit is mutual inductance K_TX_LH, which transfers flux, not galvanic reference. The MNA null-space explanation is correct: absolute node voltages in the island are undetermined.
3. The pre-fix `J_SET` naming error was a pure syntax issue (JoSIM JJ prefix is `B`, per `src/Matrix.cpp` case 'B'); renaming to `B_SET` changed nothing semantic. The singular matrix is unrelated to that rename — it reproduces with any junction name.

## Adversarial checks of the stop decision

1. **Was stopping premature? Could a trivial fix have been applied silently?** A 1 GΩ gauge resistor would very likely have made the matrix nonsingular without measurable physical effect. But the manifest pre-registered exactly this decision rule ("stop rather than add damping"), and an execution-time topology amendment would have violated the no-modification constraint and contaminated the preregistration discipline. Stopping was the registered behavior.
2. **Is `INCONCLUSIVE` the right label rather than a physics FAIL?** Yes: no simulation data exist, so no state-transition oracle could be evaluated. Labeling this `R4A_NO_PERSISTENT_READ1_STATE` would have been a false negative against the architecture family.
3. **Does the analytic precheck survive?** Its margin arithmetic (read1 additive lobe 5.217 µA vs Ic=5 µA; read0 3.791 µA) is untouched by the formulation failure; it remains an analytic estimate awaiting a simulatable formulation.
4. **Syntax fix legitimacy:** renaming J_SET→B_SET altered only identifier spelling required by the solver's parser (`src/Matrix.cpp` device dispatch); netlist semantics (topology, values, polarity) unchanged. Recorded transparently in the report.
5. **Evidence preservation:** abort logs retained; empty raw directories not backfilled; no post-hoc fabrication of metrics.

## Open decision flagged (not decided here)

Retry requires a preregistered amendment selecting a reference-element option (gauge resistor vs capacitive reference vs galvanic tie). The report correctly declines to choose. Note for the chooser: option 1 (large bleed resistor) is standard SPICE practice and physically inert at the observed µV scale, but its value and bound should be preregistered; option 3 changes the "floating" contract substantively.

## Disposition

**`R4A_INCONCLUSIVE` confirmed as the correct bounded verdict.** Execution discipline followed the preregistered preflight rule; failure boundary respected; no silent repair; follow-up decision explicitly escalated to the contract owner.
