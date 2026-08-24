# Pilot disposition

The first numerical batch is retained as raw pilot evidence and is not
silently rewritten. Its positive/reverse fixture classifications were
qualitatively consistent, but the pilot implementation was not sufficient for
a numerical freeze:

- raw JoSIM `P(...)` is already the phase trace used by this fixture and the
  strict successor must not apply an additional `np.unwrap` transform;
- the pilot did not bind the generated input snapshot and all source hashes in
  a pre-run manifest before execution;
- the pilot coupled the pre and post window perturbations instead of testing
  them as independent registered views;
- its post-extra-event check did not cover the complete simulation tail.

Disposition: `PILOT_INCONCLUSIVE_PENDING_STRICT_REPLAY`.

The pilot raw and report remain available for traceability. The strict
hash-bound successor is a new exploration and will carry its own preregistration,
raw outputs, analysis, and final verdict.
