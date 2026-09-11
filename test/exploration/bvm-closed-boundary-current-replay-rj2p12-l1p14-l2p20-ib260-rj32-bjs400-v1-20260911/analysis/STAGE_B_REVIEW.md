# Stage B N3 — direct raw scientific review

Stage A scientific gate: `PASS` (user-provided direct raw review, attachment hash-bound).

## Outcome

- Outcome code: `CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N3_FOUR_RESPONSE`
- Combined outcome: `CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N2_2_AND_N3_4`
- Review scope: exact recorded closed-loop `I(B_JSL8)(t)` current replay into isolated RJ2=12 QB/JTL.

## Direct raw evidence

- Source raw SHA-256: `1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75`
- Replay raw SHA-256: `18d1129e3c968e86f9e99e1752fd74f79756335408c2aaf6ddf943a3c2329bb8`
- Source/replay current mismatch: `0.0` A; all stored values equal: `True`.
- 109.9 ps pre-FINAL I(L1), I(L2), BJ1/BJ2 current and P values match exactly in the stored raw output.
- BJ1 and BJ2 each provide four cumulative phase landmarks; JTL1 through JTL6 each provide four ordered phase landmarks. These are phase navigation, not SFQ counts.
- QBOUT has dense raw lobes; its automatic cluster mapping is not used as sole authority. Raw lobe navigation and the ordered JTL/terminal evidence are retained.
- JTL6/terminal raw has four separated large positive lobes at approximately 132.3, 136.9, 141.1 and 145.6 ps; the auxiliary stored-sample valley segmentation gives four terminal pulses with total area approximately 4 Phi0.

## Candidate 4 navigation

| track | candidate 4 time |
|---|---:|
| `BJ1` | 124.19999999999999 ps |
| `BJ2` | 124.8 ps |
| `QBOUT_peak_time_ps` | 125.3 ps |
| `JTL1` | 126.39999999999999 ps |
| `JTL2` | 130.4 ps |
| `JTL3` | 134.1 ps |
| `JTL4` | 137.6 ps |
| `JTL5` | 140.9 ps |
| `JTL6` | 143.8 ps |
| `terminal_peak_time_ps` | 145.6 ps |

## Bounded interpretation

Within the tested ideal-current replay abstraction, the recorded closed-loop boundary current history is sufficient to reproduce the tested N2 two-response and N3 four-response regimes. Continued real-time source/receiver interaction is not required during replay once the corresponding closed-loop current history has been recorded.

This does not show that back-action was irrelevant: the replay waveform itself was formed while closed-loop interaction existed. The result is bounded to the declared models, 0.1 ps grid, 0–200 ps protocol, receiver, load and source histories. No hardware or universal mechanism claim follows.

Final state: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
