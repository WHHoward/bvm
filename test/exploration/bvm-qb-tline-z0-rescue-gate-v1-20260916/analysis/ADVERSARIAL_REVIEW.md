# Adversarial review probes

The probes below test whether the rescue result could be made to look correct by a stale deck, weak oracle, or hidden transformation.

- No-op/wrong-branch probe: `{"Z0_12_0011": "previous Z0=6, TD=0.3 deck with only T_BVM_QB Z0 token changed", "Z0_24_0011": "previous Z0=6, TD=0.3 deck with only T_BVM_QB Z0 token changed"}`; each new deck is byte-identical to the prior TLINE deck except the registered Z0 token.
- Weak-oracle probe: ordered candidate count uses internal BJ1, BJ2, JTL1..JTL6 phase-navigation chronology; terminal is corroboration only. Gate result: `TLINE_Z0_RESCUE_FAILED`.
- Stale-artifact probe: current/raw and read-only reference before/after hashes equal: `True`.
- Boundary probe: actual stored grid and half-open windows were retained; no interpolation, resampling, smoothing, scaling, or time shifting was used.
- Overclaim probe: no incident/reflected decomposition, no 2*TD measured-return claim, no SFQ count, no matching-value claim, and no hardware extrapolation.

Residual uncertainty: waveform distortion and dynamic loading are described but not separated into a reflection coefficient or a physical interface impedance.
