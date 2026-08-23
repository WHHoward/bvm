# PAPER-SL-Q3 Stage-A analytic precheck

Generated from accepted raw only; no JoSIM execution was performed for this
stage.  Current units are uA, time is ps, and the selected windows are the
dominant paired BJL1 activity windows from the prior Q3-PRE audit.

## Inputs and provenance

| case | raw | SHA-256 | window |
|---|---|---|---|
| Q0_68p4 | `test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv` | `0b3fab3ba7357d2475ffadb174f0d48ad33b7e7c934962a687074d4739468bdb` | `[210.0, 216.5]` |
| Q1_35u | `test/exploration/paper-sl-q1-20260824/raw/paper-j1-logical1-read.csv` | `3280c7c134dc599bad5e0433ec2650ffb566af5cc37a6849eafb0b2c06b06f24` | `[102.6375, 109.125]` |
| Q2_40u | `test/exploration/paper-sl-q2-20260824/raw/40u/paper-j1-logical1-read.csv` | `c9ba678e26ac9c90da922f091457f263d5e3fe5dad7d8e811c98ecb953d65731` | `[102.525, 106.875]` |

## Measured branch split and KCL

The actual node-2 relation in the frozen QB topology is
`I(BJs) = I(L1) + I(BJL1) + I(RJ1)`.  `local` below means
`I(BJL1)+I(RJ1)`, evaluated from the raw branch currents.

| case | window | BJs min..max (uA) | L1 min..max (uA) | local min..max (uA) | ∫BJs dt (uA ps) | ∫L1 dt | ∫local dt | KCL RMS (uA) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Q0_68p4 | [210.0000, 216.5000) | 0.0000..68.4000 | -15.1217..85.2719 | -16.8719..57.7794 | 398.0880 | 246.4812 | 151.6068 | 0.000005 |
| Q1_35u | [102.6375, 109.1250) | -2.2381..79.0668 | -2.8216..54.7499 | -43.4805..53.8997 | 228.4881 | 183.6795 | 44.8086 | 0.000004 |
| Q2_40u | [102.5250, 106.8750) | 10.1513..79.0668 | 7.5909..78.7242 | -41.2102..48.0333 | 220.3545 | 172.1752 | 48.1792 | 0.000004 |

The corresponding local-current fractions from signed integrals are:

| case | F_local = ∫(BJL1+RJ1)dt / ∫BJs dt | complementary L1 fraction |
|---|---:|---:|
| Q0_68p4 | 0.380837 | 0.619163 |
| Q1_35u | 0.196109 | 0.803891 |
| Q2_40u | 0.218644 | 0.781356 |

These are signed-area diagnostics over different, case-specific dominant
windows; they are not event counts.  The Q1/Q2 replay sends most signed node-2
current into L1 (fractions about 0.804 and
0.781), whereas the successful Q0 reference sends a
larger fraction into the local BJL1/RJ1 branch (about
0.381).

## Dynamic direction check

For the existing `L1=3.91 pH`, the derivative diagnostic is
`V_L1,est = L1*dI(L1)/dt`.  Its values are derived from measured current and
actual CSV time.  A direct V(L1) column was not present in these accepted raw
files; the printed `V(BJL1)` is the node-2-to-ground voltage and is reported
separately, not substituted for V(L1).

| case | dI(L1)/dt min..max (uA/ps) | estimated V_L1 min..max (uV) | direct V(BJL1) min..max (uV) | peak derivative times (ps) |
|---|---:|---:|---:|---:|
| Q0_68p4 | -75.7435..48.6471 | -296.1573..190.2102 | -0.0000..679.3118 | min 215.0000, max 211.0000 |
| Q1_35u | -63.3456..33.2724 | -247.6813..130.0951 | 3.1258..552.5113 | min 107.3250, max 104.4625 |
| Q2_40u | -72.4076..54.6756 | -283.1137..213.7816 | -1.6025..762.2214 | min 105.4375, max 104.4500 |

The selected perturbation is **L1 = 4.50 pH**, a single modest increase of
15.09% from 3.91 pH.  At unchanged dI/dt it raises the inductive voltage
coefficient by the same 15.09% (an additional 0.59 pH term), so the local
node-2 branch is expected to receive a larger share of the rapid BJs current
than the measured Q1/Q2 split.  This is a dynamic-impedance hypothesis, not a
claim that a larger inductor always increases local DC current.

## Stage-A disposition

**`L1_DIRECTION_PRECHECK_PASS; NEXT_POINT_L1_4P50_PH`**

Observed: Q1/Q2 have large BJs activity but a smaller local signed-current
fraction than Q0; the directly measured branch KCL closes to the residuals
shown above.  Derived: the dominant replay interval is a few ps long and the
measured L1 derivative is large, so the L1 branch is a plausible fast diversion
path.  Inference: a modest L1 increase is the highest-information single
perturbation to test local BJL1 routing.  Unknown: the loaded nonlinear circuit
may redistribute static bias or alter BJL1 phase dynamics in a direction not
captured by the first-order coefficient.

This precheck does not certify an event and does not predict that BJL1 will
complete a turn.  It authorizes only the one preregistered 4.50 pH point.
