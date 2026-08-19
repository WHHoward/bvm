# BVM → SFQ receiver R1a non-invasive transfer Exploration

Created: 2026-08-19T13:23:31+08:00
Tier: Exploration / EXPLORATORY
Parent R0b checkpoint: fc0f3d9466ff1533ec9f85e83a82c3503b961c16
Accepted preceding R1 failure: a93ba3bb0923a6ff4ecc12c35bceaf405304dcd4

## Verdict

**R1a PASS, bounded to passive state-dependent transfer.**

At the single preregistered operating point, a series pickup preserves the
logical1 complete local B_TRIG transition and logical0/READ=0 negative
behavior, while a passive isolated secondary has a large state-dependent
transient. This closes the question of trigger-to-isolated-signal extraction
for this Exploration.

The word non-invasive is used here in the limited sense of preserving the
R0b trigger discrimination and complete-transition criterion. It does not mean
zero BVM back-action: the JM1/JM2 logical signs remain distinct, but the
read1 JM2 post-read drift changes relative to the R0b reference. That bounded
storage transient is recorded below and is not upgraded to a state-preservation
Gate.

No output JJ, self-quench loop, JTL, T1, or R1b topology was implemented.
The passive secondary transient is not called an SFQ event or SFQ delivery.
This result is not a Candidate upgrade.

## 1. Question and preregistered scope

The question was whether the canonical SL trigger path could feed an isolated,
state-dependent passive signal without using the parallel low-resistance
N_TRIG feedback branch that failed in the preceding R1 Exploration.

The only operating point was l020-k080. The stop rule was to run this point
once, classify the failure mode if it failed, and open a separately named
Exploration for any topology-level change. No parameter sweep was performed.

The four matched cases were:

| Case | BVM state | READ |
|---|---:|---|
| read1 | logical 1 | canonical positive READ |
| read0 | logical 0 | canonical positive READ |
| logical1-read0-control | logical 1 | READ=0 |
| logical0-read0-control | logical 0 | READ=0 |

The canonical BVM source was copied into the fixture for provenance only; its
topology and source file were not modified.

## 2. Receiver topology and actual model parameters

The primary route is:

    BVM SL1 → R_IN → N_PICK → L_TX → N_TRIG → B_TRIG → ground
                                      │
                                      └ +15 µA independent trigger bias

The isolated passive pickup is:

    L_TX -- K_TX=0.80 -- L_SEC
                            │
                     N_SEC ─┴─ ground
                            │
                    R_SEC_LOAD=12 Ω to ground

The actual netlist uses L_SEC=2.0 pH from N_SEC to ground and a parallel
12 Ω load from N_SEC to ground. There is no secondary JJ. The primary series
pickup values are:

| Element | Value |
|---|---:|
| R_IN | 12 Ω |
| L_TX | 0.20 pH |
| B_TRIG AREA | 0.50 |
| B_TRIG bias | +15 µA |
| L_SEC | 2.0 pH |
| R_SEC_LOAD | 12 Ω |
| K_TX | 0.80 |
| mutual inductance M | 0.5059644 pH |

The included actual JJ model is:

    .model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)

For AREA=0.50, the JoSIM model semantics give:

| Quantity | Actual value |
|---|---:|
| Ic | 50 µA |
| RN | 32 Ω |
| R0 | 320 Ω |
| C | 35 fF |
| beta_c | 5.4450545 |

AREA was not treated as an Ic-only knob. The model scales Ic and C by AREA
and divides RN and R0 by AREA. The preregistered L_TX order estimate gives
about 0.48 Ω reactance near the trigger characteristic frequency, small
relative to R_IN=12 Ω; this is only a physics-informed initial estimate, not a
replacement for the transient result.

## 3. Solver and artifact QA

All cases used build/josim-cli v2.7.2837d13, binary SHA-256
48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2.
The requested numerical condition was dt=0.0125 ps and stop=170 ps.

Each raw CSV contains 13,599 finite rows from 0 to 169.9875 ps, with strictly
increasing time. The actual CSV spacings are 0.0125–0.025 ps. All four solver
stderr files are empty, and all required probes are present.

The canonical fixture and JJ model hashes are:

| Fixture | SHA-256 |
|---|---|
| inputs/bvm_cell.cir | ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4 |
| inputs/jjmit.cir | 19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336 |

The four raw CSV hashes are recorded in manifest.yaml and
analysis/sha256sums.txt.

## 4. Trigger phase and same-JJ voltage-area evidence

The switching criterion uses raw P(B_TRIG|XTRIG) in radians, adjacent-sample
continuous unwrapping, and sign-consistent monotonic segments. A segment is
complete only when its absolute phase delta reaches 2π. For the same segment,
V(B_TRIG|XTRIG) is integrated with the actual CSV time and divided by Φ0.
Current above Ic, voltage peak, phase range alone, and derivative activity are
not used as switching criteria.

The 94–130 ps continuous ranges are activity summaries, not event counts. The
decisive segment results are:

| Case | Segment / direction | Raw P endpoints (rad) | Continuous delta | Same-JJ V area | Complete |
|---|---|---:|---:|---:|---|
| read1 | 102.950–110.900 ps, increasing | 2.612737 → 27.392180 | 24.779443 rad = 3.94377084 turns | 3.94379356 turns | YES |
| read0 | 106.5875–108.2125 ps, increasing | −0.3205408 → 0.8403237 | 1.1608645 rad = 0.18475732 turns | 0.18478065 turns | NO |
| logical1 READ=0 | 94.825–96.350 ps, decreasing | 0.3049705 → 0.3044415 | −0.0005290 rad = −0.00008419 turns | −0.00008421 turns | NO |
| logical0 READ=0 | 94.0375–95.575 ps, increasing | 0.3038687 → 0.3054680 | 0.0015993 rad = 0.00025454 turns | 0.00025457 turns | NO |

For read1, the same-segment area-minus-phase residual is
2.2718×10⁻⁵ turns. For read0 it is 2.3323×10⁻⁵ turns. Thus the phase and
same-JJ voltage evidence agree on the complete versus non-complete
classification.

The broad 20–170 ps control check also finds no complete segment. The largest
control monotonic segments are 0.06347 turns and 0.06982 turns. The read1
130–170 ps post window has a largest segment of 0.19354 turns, so this
receiver remains a multi-turn trigger rather than a one-shot circuit.

## 5. Secondary transient

For each case and each passive secondary signal, the amplitude A is the
maximum absolute deviation in 94–130 ps from that case's 80–90 ps PRE median.
The thresholds were preregistered as A[V(N_SEC)]≥10 µV, A[I(R_SEC_LOAD)]≥1 µA,
read1≥2×read0, and read1≥5×both controls.

| Case | A[V(N_SEC)] | A[I(R_SEC_LOAD)] |
|---|---:|---:|
| read1 | 66.7685 µV | 5.56404 µA |
| read0 | 13.7241 µV | 1.14367 µA |
| logical1 READ=0 | 0.0005157 µV | 0.00004297 µA |
| logical0 READ=0 | 0.0006909 µV | 0.00005757 µA |

The read1/read0 ratio is 4.8651 for both voltage and load current. Relative
to the larger of the two controls, read1 is about 9.66×10⁴ larger for both
signals. The L_SEC current is equal and opposite to the load-current
direction at the passive secondary node, as expected from the grounded
parallel branch. The controls show no spontaneous secondary output.

This establishes passive signal extraction, not quantization. There is no
output JJ whose phase could be counted in this Exploration.

## 6. Pickup loading and BVM back-action

The direct series check gives I(R_IN)=I(L_TX) in the raw probes. In the
94–130 ps activity window, the R1a read1 and read0 absolute input-current
peaks are 54.19963 µA and 22.16104 µA. The corresponding R0b reference values
are 54.20765 µA and 22.24402 µA. Thus the series pickup preserves the input
current scale to the resolution of this comparison.

The source separation remains present:

| Case | R0b | R1a |
|---|---:|---:|
| read1 abs peak V(SL1) | 1.812093 mV | 1.863837 mV |
| read1 abs peak V(N6) | 1.968229 mV | 2.106848 mV |
| read0 abs peak V(SL1) | 0.4406386 mV | 0.4424284 mV |
| read0 abs peak V(N6) | 0.7202232 mV | 0.7211924 mV |

Compared with R0b, the read1 largest complete trigger segment is reduced from
4.9974563 turns to 3.9437708 turns, about a 21.1% reduction, but remains
complete. The read0 largest segment changes only from 0.1852812 to
0.1847573 turns. This is the required trigger discrimination preservation,
not a claim that the series pickup is dynamically invisible.

The R1a storage medians are:

| Case | JM1 pre → post (rad) | JM2 pre → post (rad) |
|---|---:|---:|
| read1 | 5.911061 → 5.914553 | 0.3172284 → 0.3488454 |
| read0 | −5.911061 → −5.911085 | −0.3172223 → −0.3212199 |
| logical1 READ=0 | 5.911061 → 5.911075 | 0.3172284 → 0.3169240 |
| logical0 READ=0 | −5.911061 → −5.911075 | −0.3172223 → −0.3169240 |

The logical signs remain distinct after loading: JM1 is positive for read1
and negative for read0; JM2 is positive for read1 and negative for read0.
However, the read1 JM2 drift is not the same as the R0b reference. The
R0b-to-R1a read1 JM2 post–pre change is approximately −0.003931 turns to
+0.005032 turns, while the read0 value remains approximately
−0.000636 turns. This is a bounded back-action observation and a future
R1b storage-preservation concern, not evidence of logical-sign destruction.

The JS1/JS2 probes were also preserved. Their R1a read1 activity is
multi-turn and their read0 activity is edge-dominated, while both READ=0
controls remain near stationary. These phase ranges are reported as local
activity only and are not SFQ counts.

## 7. Evidence classification

### Observed

- Four valid, matched raw simulations ran at the single preregistered point.
- Read1 has a 3.94377084-turn increasing B_TRIG segment with matching
  same-JJ voltage area.
- Read0 and both READ=0 controls have no complete B_TRIG segment.
- The passive secondary voltage and load current are clear and strongly
  state-dependent.
- SL, N6, input current, JM1/JM2, and JS1/JS2 probes are present.
- Post-window and broad control checks show no complete control transition.

### Derived

- The declared R1a transfer criterion passes at L_TX=0.20 pH, K=0.80,
  L_SEC=2.0 pH, and R_SEC_LOAD=12 Ω.
- Read1/read0 secondary separation is 4.8651×; read1/control separation is
  about 9.66×10⁴.
- The direct series pickup reduces the R0b read1 trigger length by about 21.1%
  but leaves it above 2π; read0 remains below 2π.
- Logical storage signs are preserved, with bounded JM2 back-action.

### Inference

- For this JoSIM model, timestep, BVM source, and passive load, a series
  magnetic pickup provides a non-parallel, state-dependent trigger-path
  extraction that preserves the R0b discrimination criterion.
- A separately designed output-JJ stage can use this secondary as its input
  signal candidate.

### Unknown

- Timestep convergence and margin under parameter, load, temperature, or
  model variation.
- Whether an output JJ attached to this secondary can switch exactly once.
- Whether an R1b output stage can keep the JM2 back-action within an accepted
  storage-preservation bound.
- Any downstream JTL reception, SFQ quantization, or hardware behavior.

## 8. Next step

R1b may be opened as a new, independent Exploration that attaches the minimum
output-JJ stage to the passive secondary and preregisters a local output-JJ
one-event criterion. It should retain the same four cases and storage probes.
R1b is not implemented here; no JTL or self-quench result is implied.
