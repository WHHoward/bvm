# A109 postprocess recovery attempt 001

- Initial solver exit code: 0; initial raw SHA-256: `d46f0c8ccce28cff2aaf590089f07a878135bbcd5235489c99334856a6d1bbe6`.
- Initial artifact status: `ARTIFACT_INVALID` because the analyzer requested absent probe `P(B7|XDFF)`.
- Repair: bit7 same-JJ P/V fields are `UNKNOWN` when the DFF internal probe is not registered; the raw/deck/stimulus/probe set is unchanged.
- JoSIM invocation in this recovery: 0. Raw mutation: prohibited and checked.
