# RJ2=10 weight-3 diagnostic — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911`
- Preflight HEAD: `b8b93640b56eda3cbbaadf54914c9538ccf01492`
- Latest remote `WHHoward/bvm` and latest Drive canonical packages were rechecked before registration.
- Frozen point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, RJ2=10ohm, BJS area=4/Ic=400uA.
- Exactly one new physical solve: mask `0111`; no other mask, RJ2, timestep or READ duration.

## Immutable references

- RJ2=10: `0001`, `0011`; RJ2=11: `0011`, `0111`; RJ2=12: `0011`, `0111`.
- All six references are comparison-only exact bytes; no reference is rerun.

## Frozen protocol

- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- Amplitude 100uA; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`; bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.

## Evidence ceiling

- Raw waveform is the scientific authority; mechanical checker labels are subordinate.
- Candidate responses, phase navigation, terminal areas, pulse areas, current crossings and voltage peaks are not SFQ counts.
- The 0111 fourth-candidate focus is [121,130)ps and retains BJ1/BJ2/QBOUT/JTL/terminal plus source/receiver state metrics.

- Authority packages: `PASS_GIT_DRIVE_PACKAGE_SHA_AND_BYTES`; references: `PASS`; deck: `PASS`.
- Physical execution has not started at preflight.
