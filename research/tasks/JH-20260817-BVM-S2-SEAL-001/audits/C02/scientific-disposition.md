# BVM-S2 final independent scientific disposition

Authority: this is a read-only Codex scientific audit authorized after
S2-SEAL-001 C01 accepted the recursive evidence seal. It uses the sealed S2
raw package and frozen preregistration; no new JoSIM output exists. The
original S2 request/ACK baseline mismatch remains historical protocol metadata.

| Field | Result |
|---|---|
| artifact_status | VALID for the 16-run sealed raw/closure evidence package |
| readiness_status | NOT_MET |
| scientific_disposition | INCONCLUSIVE |
| numerical_status | NOT_APPLICABLE |
| audit_disposition | ACCEPTED |

## Independent validity checks

- The C01 seal supplies the 76-file provenance authority. All 16 CSVs have
  the registered header, finite values, strictly increasing literal CSV times,
  13,599 rows, and coverage through 169.9875 ps. All read/control and
  cross-load traces share identical literal timestamp sets: no interpolation,
  resampling, or time alignment was used.
- The recorded binary and copied BVM/jjmit closure hashes match frozen values.
  Direct same-JJ phase-area values were recomputed for all 16 runs times four
  junctions using actual CSV time, registered Phi0, and phase minus area. All
  64 records agree with analysis.json; no global residual acceptance band
  exists.
- analysis.json validates syntactically against its frozen schema. That schema
  pass does not alone prove every derived calculation follows preregistration.

## Readiness

The required JM2 PRE [80,90) ps p2p maximum is 0.020 rad.

| R_LD | JM1 p2p rad | JM2 p2p rad | positive-vs-negative L-infinity rad |
|---:|---:|---:|---:|
| 1 ohm | 0.003524 | 0.0583709 | 11.8219208 |
| 12 ohm | 0.003528 | 0.0584342 | 11.8219205 |
| 25 ohm | 0.003525 | 0.0583783 | 11.8219207 |
| 50 ohm | 0.003519 | 0.0582907 | 11.8219211 |

JM2 exceeds the frozen maximum by 0.03829 to 0.03843 rad at every load and
both operational initialization polarities. The passing JM1 and separation
subchecks do not compensate. The registered consequence is INCONCLUSIVE.

S2 WL/BL initialization rises from 9 to 10 ps; S1 rises from 10 to 11 ps.
S2 also shows the JM2 PRE oscillation above. Those are cross-study facts, not
evidence that the one-ps timing difference caused the oscillation.

## Bounded source observations

These independently recomputed own-PRE-baseline peaks are at the registered
0.0125 ps grid. Every source control has rctrl from 8.76e-5 to 6.05e-4, so
controls are in PASS_REGION and control latency/FWHM are NOT_APPLICABLE.

| R_LD | positive V mV | positive I uA | negative V mV | negative I uA |
|---:|---:|---:|---:|---:|
| 1 ohm | +0.100011 | +100.011 | -0.038866 | -38.866 |
| 12 ohm | +0.904619 | +75.385 | -0.317121 | -26.427 |
| 25 ohm | +1.822667 | +72.907 | -0.493293 | -19.732 |
| 50 ohm | +2.258803 | +45.176 | -0.677116 | -13.542 |

They are immutable fixed-closure, fixed-grid, matched-control-context
observations, not a converged source specification, logical readout,
state-preservation result, or receiver-compatible source claim.

## Terminal affine diagnostic

The frozen calculation requires Rhat = -(V50-V1)/(I50-I1),
Vth = V1 + Rhat*I1, and e_L = V_L - (Vth - Rhat*I_L), at exact common
timestamps. The supplied analyzer instead linearly interpolates voltage and
current separately against load. Its residual magnitudes and prose are not
authority here. Independent raw recomputation of the frozen V-I formula gives:

| initialization | eligible | compatible | NOT_SUPPORTED | ill-conditioned |
|---|---:|---:|---:|---:|
| positive | 2,594 | 87 | 2,507 | 286 |
| negative | 2,180 | 167 | 2,013 | 700 |

NOT_SUPPORTED_AT_NAMED_TIMESTAMP can therefore be retained only as a bounded
descriptive diagnostic. Readiness NOT_MET prevents it becoming a coherent
load-characterization result or any source-impedance conclusion.

## Internal trajectories and limits

JM1/JM2 maximum PRE mean spans across loads are 2.8875e-7 and 4.407125e-6
rad, below the registered 0.020-rad pre-state discriminator. Thus no load
effect on initialization is established by that criterion. The p-star,
v-star, and a-star traces remain fixed-grid records, but the report does not
establish every two-witness, persistence, control-envelope, floor, and
direction condition. The strongest allowed wording is unresolved
load-associated internal trajectory observations; it is not confirmed
read-time back-action, state transition/preservation, event/SFQ, fluxoid,
logic, or mechanism.

Numerical status remains NOT_APPLICABLE because S2 has no timestep ladder;
S1 numerical INCONCLUSIVE is unchanged. The human-readable analysis.md table
also contains source-peak values that disagree with raw recomputation (for
example 1-ohm positive current is +100.011 uA from raw, not +58.9 uA).
This audit does not modify historical artifacts and does not require report
repair to close S2 as INCONCLUSIVE. A future report-correction task would need
separate authorization if those artifacts are to be reused.
