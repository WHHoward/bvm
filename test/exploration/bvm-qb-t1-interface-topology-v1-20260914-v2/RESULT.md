# BVM -> QB -> T1 interface topology v1

## Evidence status

- Artifact status: `VALID`.
- Physical solves completed: `15` / `15` authorized.
- Completed runs: `jtl6_0000, jtl6_0001, jtl6_0011, jtl6_0111, jtl6_1111, jtl2_0000, jtl2_0001, jtl2_0011, jtl2_0111, jtl2_1111, direct_0000, direct_0001, direct_0011, direct_0111, direct_1111`.
- Stage A sanity: `PASS`.
- Scientific interpretation: `NOT_PERFORMED`; physical verdict: `NOT_ASSIGNED`; review state: `AWAITING_SCIENTIFIC_REVIEW`.

This file records raw observations and registered arithmetic only. P(...) is raw radians; derived turns are independently unwrapped radians divided by `2*pi` and are navigation, not SFQ counts. Voltage-area arithmetic uses the same JJ, direction, stored grid and half-open window.

## Registered scope

The canonical QB is the shared `circuits/qb/bq_parameterized_v1.cir` source. All three topologies retain the galvanic BVM/JSL↔QB loop and use the current unmodified T1 cell. No replay, passive capture, source scaling/filtering, parameter sweep, matching resistor, clock source, timing change or retry was authorized.

## Machine-readable evidence

- [PREFLIGHT.md](PREFLIGHT.md)
- [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)
- [provenance.json](provenance.json)
- [result.json](result.json)
- [mechanical_qa.json](mechanical_qa.json)
- [visualization_manifest.json](visualization_manifest.json)
- [visualization_qa.json](visualization_qa.json)

## Review boundary

The raw data do not by themselves certify SFQ counts, JJ switching, downstream reception, an interface Gate, T1 logic, mechanism, convergence, hardware behavior, parameter ranking, or a follow-up experiment.

EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
