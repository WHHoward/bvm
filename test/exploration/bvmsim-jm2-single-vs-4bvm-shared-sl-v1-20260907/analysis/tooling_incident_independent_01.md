# Tooling incident INDEPENDENT-01

- First independent-check attempt: `2026-09-07T13:21:xx+08:00` (review script run after analysis).
- Failure: the cross-check loop indexed the top-level production mapping instead of the current signal record.
- Effect: no independent-check JSON or review file was written; raw/deck/log artifacts were untouched.
- Correction: index `production[name][metric]` for the current signal.
