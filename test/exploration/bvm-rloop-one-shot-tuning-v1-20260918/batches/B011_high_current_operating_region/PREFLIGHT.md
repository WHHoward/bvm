# B011 — BVM high-current one-shot operating-region map

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Status: PRE-REGISTERED / PASSIVE ONLY / NO QB-JTL MODIFICATION

Parent HEAD at registration: `adae6d48`.

Fixed execution scope:

- `MODE=passive`, `MASKS=0001,1111` only.
- No N2/N3/full-population runs and no CLOSED follow-up.
- No modification to QB, JTL, terminal, stimulus, DT, STOP, or registered BVM
  source models.
- Group A, Group B, and Group C are independent; no cross-group combinations.
- Existing raw may be reused only after exact mode/mask/parameter/stimulus/DT/
  STOP/source-hash/raw-QA verification. Reuse references are recorded without
  copying raw bytes.

The registered logical matrix is 23 variants × 2 masks = 46 logical points:

- Group A: A00 plus A110-0/A110-H/A110-M/A110-J2,
  A120-0/A120-H/A120-M/A120-J2, and A130-0/A130-H/A130-M/A130-J2 (13).
- Group B: LM3 = 8.5p, 8.6p, 8.7p, 8.8p, 8.9p, 9.0p (6).
- Group C: RSL = 12, 10, 8, 6 ohm (4).

The preflight fingerprint audit permits 12 strict logical reuses from B010:
B0/A00/Group-B 8.5p/Group-C RSL12 → U040, A110-0 → U045, Group-B 9.0p →
U043, and Group-C RSL10 → U044, for an expected 34 new physical solves.

Required evidence: immutable raw/deck/log/provenance, raw and plot QA, actual
stored-grid arithmetic, Gate-S/R/Z registered metrics, and explicit
Observed/Derived/Inference/Unknown labels. This preflight does not authorize
automatic CLOSED follow-up, parameter combinations, ranking by a composite
score, or a final production winner.
