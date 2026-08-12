# M11B preflight — Scientific Reconstruction Baseline

## Authority and scope

- Parent authority: `memory/project-todo.md` M11 and its Source/Receiver and
  provenance discipline in section I.
- This is a `CALIBRATION`, `CRITICAL`, `FROZEN` reconstruction-state freeze.
  It records the current repository knowledge state; it must not improve a
  circuit, tune a candidate, define `INTERFACE_GATE_V1`, or run JoSIM.
- The pass object is the completeness and honesty of the frozen knowledge
  inventory, not physical completeness, published reproduction, or candidate
  validation.

## Required structured object inventory

The attempt-local baseline must contain at least BVM, published modified-QB,
original/reference BQ, canonical JTL receiver, canonical DCSFQ when included as
a reference fixture, BVM source characterization, and receiver
characterization. Each object has machine-readable fields for:

`source_reference`, `parameter_provenance`, `reproduction_status`,
`characterization_status`, `unknown_inferred_items`, `evidence`,
`claim_limitation`, and `upgrade_discriminator`.

An `UNKNOWN` item is valid only if it records its exact missing field, reviewed
source set/date/search boundary, impact, and the discriminator that could
resolve it. A project value and an unknown reference value must be separate
fields. `[INFERRED]`, `[DESIGNED]`, and `[TUNED]` can never silently become
`[PUBLISHED]`.

## Reproduction semantics

Levels are cumulative and per-object: R0 topology; R1 published nominal
parameters; R2 behavior after R0+R1 plus predeclared behavioral criteria; R3
independent full reproduction with model closure, testbench, provenance,
numerics, observation tolerance, and independent review. A behaviorally similar
project-tuned implementation is `behavioral_analogue_with_nonpublished_parameters`,
not published R2. `R0`, `PARTIAL_R1`, `UNKNOWN`, and `NOT_CHARACTERIZED` are
permitted final states.

## No hidden reconstruction

Existing evidence may be catalogued and downgraded honestly. If any desired
field or status requires a new circuit run, the executor must stop and report
the exact missing discriminator. A separate preregistered task is required;
this contract does not authorize it.

