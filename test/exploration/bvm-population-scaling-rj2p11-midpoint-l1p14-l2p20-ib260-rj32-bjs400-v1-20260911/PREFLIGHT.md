# RJ2=11 midpoint — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911`
- Preflight HEAD: `de853f9dd0acf231a120316bd8566040acd0bda4`
- Latest remote/source HEAD was rechecked before registration.
- Frozen working point: L1=1.4pH, L2=2.0pH, IBias=260uA, RJ1=32ohm, RJ2=11ohm, BJS area=4/Ic=400uA.
- Sole physical parameter delta from the RJ2=12 authority: RJ2 12ohm -> 11ohm.

## Exact matrix

- Fresh physical solves: `0001`, `0011`, `0111`, `1111` only.
- Four RJ2=12 reference cases are byte-exact comparison evidence only; no RJ2=12 raw is reused as an RJ2=11 physical case.
- Total new physical solves: exactly 4; no other masks, RJ2 values or timestep values.

## Frozen protocol

- IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; mask-selective FINAL READ 110–121ps; TAIL 121–200ps.
- Amplitude 100uA; 1ps rise/fall; 9ps plateau; `.tran 0.1p 200p`; bit order b3b2b1b0=BVM1/BVM2/BVM3/BVM4.

## Evidence ceiling

- Raw waveform files are the scientific authority for later review.
- Phase landmarks use raw radians converted by `/ (2*pi)` for navigation only; no phase turn, area, current peak, L1 crossing or terminal pulse is an SFQ count.
- The generalized oracle and mechanical checker are subordinate QA/navigation tools; conflicts with raw evidence remain visible.

- Authority package equality: `PASS_GIT_DRIVE_SHA_AND_BYTES`; exact references: `PASS`; deck checks: `PASS`.
- Physical execution has not started at preflight.
