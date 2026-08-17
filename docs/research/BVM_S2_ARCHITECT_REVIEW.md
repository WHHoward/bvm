# BVM-S2 Architect Review (revised, read-only)

Reviewer: `josim_architect` runtime role (Sol XHigh). Date: 2026-08-17. No source file was modified and no JoSIM command was run.

## Recommendation: four loads at one declared working timestep

Recommend the revised **16-run** design: external `R_LD={1,12,25,50} Ω`, each at 0.0125 ps for positive/negative read and their matched controls. Retain the BVM cell's internal 12 Ω `R_SL`; do not attach BQ, DCSFQ_BVM or JTL.

This replaces the earlier 14-run option (`1,12,50 Ω` plus two 0.00625 ps 12 Ω positive runs). The estimated sample-row cost is effectively equal: about `16×13,600=217,600` versus `12×13,600+2×27,200=217,600`. The revised option spends that budget on the actual S2 decision: it adds a second, independent interior test (25 Ω) of an endpoint affine reference. That makes a coincidental 12 Ω crossing and high-load-side curvature more visible.

The removed spot-check would be only a narrow positive/12 Ω diagnostic. A pass could not prove 0.0125 ps convergence for negative state, endpoint loads, or the whole waveform; a failure would not localize the cross-load relation. Therefore it has lower decision-relevant information gain for S2. The explicit cost is that S2 remains a **single-grid bounded characterization**. S1 stays numerically `INCONCLUSIVE`; absence of a S2 spot-check is not evidence that 0.0125 ps is converged or that load response is resolution-independent.

## Terminal behavior is distinct from internal behavior

At a pure resistor, `V(SL1)=R_LD I(L_SL|XBVM1)` is a port-QA identity, not source-impedance evidence. Use exact-time, matched-control-corrected source traces to create a 1 Ω/50 Ω endpoint affine reference, and independently report residuals for both 12 Ω and 25 Ω. Keep the simultaneous-peak fit separate as a peak-envelope descriptor: different load peaks need not occur at the same time, so this is never an instantaneous Thevenin parameter.

Because the BVM is a stateful nonlinear JJ network, a terminal affine-compatible curve cannot be interpreted as a fixed internal Thevenin impedance. The preregistration correctly adds direct JM1/JM2/JS1/JS2 P/V paths and compares their control-corrected trajectories at exact common timestamps. It reports PRE state dispersion, activity/recovery/POST phase and voltage path max/RMS, lobe ordering, phase excursions, and cumulative same-JJ voltage-area paths.

The proposed two-distinct-witness, persistence, control-envelope, and task-local effect-size discriminator is a useful reporting guard: it may label a resolved *load-associated internal trajectory difference*, but cannot claim a state transition, state preservation, mechanism, event/SFQ, fluxoid, or logical value. If PRE differs across loads, later differences are not assigned solely to read-time back-action. If the discriminator does not fire, report effect sizes rather than claim that internal dynamics are load-independent.

## Required limits before issuance

Freeze the 16-run maximum, source and direct-JJ probe headers/directions, exact-decimal timestamp rule, `METRIC_SPEC_V2` §11.1 provenance/schema, lobe segmentation/tie rules, control hierarchy, terminal conditioning floors, and internal effect-size discriminator before execution. Use `Phi0=2.067833848e-15 Wb` and `phase - area` for any same-JJ residual. Do not copy S1 A02's report metadata or residual defects.

A valid non-affine result can establish immutable per-load observations and show that this local terminal approximation is not supported at named features/times. Reserve `INCONCLUSIVE` for artifact, input/control/readiness, timestamp, numerical or conditioning ambiguity. No conclusion about receiver, route, Interface Gate, universal source impedance, hardware, paper reproduction, or formal timestep convergence is supported.
