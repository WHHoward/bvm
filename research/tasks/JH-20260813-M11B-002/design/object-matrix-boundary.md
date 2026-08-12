# M11B-002 design — unified scientific reconstruction object matrix

## Supersession and purpose

This request supersedes `JH-20260813-M11B-001`, whose A01/A02 and C01 are
immutable rework history. It does not change M11A C02, candidate-route state,
or the frozen measurement contract.

The new canonical object matrix is the single provenance/reconstruction/
characterization entry point for M11B and W5B. `REFERENCE_PROVENANCE.md` is a
historical start-point until audit acceptance, and must then become only a
pointer/index to the canonical matrix rather than a competing register.

## Exact object set

The matrix must have exactly these unique `object_id` values:

1. `bvm_storage`
2. `bvm_source_output`
3. `published_qb`
4. `bq_v4`
5. `standard_dcsfq`
6. `dcsfq_bvm`
7. `canonical_jtl`

Each object is a current-fact record, not a candidate verdict. It must carry
structured `current_evidence`, `observable`, `parameter_provenance`,
`characterization_status`, `reproduction_status`, `unknowns`,
`claim_limitation`, and `next_discriminator` fields.

## Provenance and status semantics

- A source entry always has repository path, SHA-256, source role, review state,
  and locator. `INVENTORIED_UNREVIEWED` means it was hash-inventoried only; its
  contents cannot support a `[PUBLISHED]` parameter assertion.
- A parameter tagged `[PUBLISHED]` requires a reviewed local source and a
  locator. `[AUTHOR_PROVIDED]`, `[DERIVED]`, `[INFERRED]`, `[DESIGNED]`,
  `[TUNED]`, and `[UNKNOWN]` keep their existing meanings and are never silently
  upgraded.
- `UNKNOWN` is a structured record: field id, reference status, project value
  (if any), tag, reviewed source set/boundary, impact, and next discriminator.
- Reproduction level is per object and cumulative. Permitted values are
  `NOT_ATTEMPTED`, `R0`, `PARTIAL_R1`, `R1`, `R2`, `R3`; no field may use an
  undeclared status. Characterization status is independent and limited to
  `NOT_ATTEMPTED`, `LEGACY_ONLY`, `CALIBRATION_FIXTURE_ONLY`, or
  `CHARACTERIZED`.
- A new circuit run is never implicit. If a higher status requires one, record
  it as the `next_discriminator` and stop; a separate preregistered contract is
  required.

## W5B boundary

W5B can be marked complete only if the accepted matrix is a complete provenance
registry for the exact seven-object set, including open UNKNOWN/INFERRED items.
It does not complete W5A literature-boundary work, W5C author inquiry, published
full reproduction, physical characterization, candidate validation, or paper
novelty claims.
