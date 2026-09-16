# BVM -> QB TLINE feedback dephasing — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Experiment: `bvm-qb-tline-feedback-dephasing-v1-20260916`
- Study phase: `EXPLORATORY`
- Role: `Experimental Operator + Evidence Packager`
- Registration HEAD: `cdd916a35ee3f28eea8b7d3524a5751fda6f6efd`
- Remote `bvm/master` at registration: `cdd916a35ee3f28eea8b7d3524a5751fda6f6efd`
- Canonical BVM/QB/JTL sources are hash-guarded and must not be modified.

## TLINE syntax evidence and smoke gate

The current JoSIM source/parser and repository documentation establish the
four-node ideal lossless transmission-line syntax:

```text
Tlabel Vi+ Vi- Vo+ Vo- TD=value Z0=value
```

Evidence retained in the source closure:

- `src/TransmissionLine.cpp` and `include/JoSIM/TransmissionLine.hpp` parse
  tokens 1–4 as the two port node pairs and parse `TD=` / `Z0=` from token 5
  onward.
- `src/Matrix.cpp` dispatches element type `T` as a four-node
  `TransmissionLine`; the component stores two port-current indices.
- `docs/comp_stamps.md` documents the lossless delayed equations and
  `k = TD/h`.
- `test/comp/tx.cir` is the repository syntax fixture:
  `T1 1 0 2 0 TD=200p Z0=2`.

Before any formal BVM/QB deck is created, run the registered smoke deck:

```text
smoke/tline_syntax/deck.cir
```

Smoke acceptance requires: parser acceptance, no missing-model/unknown-node
warning, a valid raw file, `TD=0.3p` at `.tran 0.1p` producing a 3-sample
near-to-far voltage landmark delay, and the expected common ground return
(`IN/0` to `OUT/0`). The smoke source/load are not a research case and are
excluded from the four-case physical solve matrix.

Smoke result: `PASS`.

- Solver: `build/josim-cli`, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`,
  version `v2.7.2837d13`.
- Raw header: `time,V(IN),V(OUT),I(T_SMOKE),I(RLOAD)`.
- Input landmark: `V(IN)` first becomes nonzero at `0.6 ps`.
- Far landmark: `V(OUT)` first becomes nonzero at `0.9 ps`.
- Measured delay: `0.3 ps = 3` stored samples.
- Smoke raw SHA-256:
  `ca6da2b9b408c389f8f448118dede1dfafbdabb58217554f14635f62085d7f21`.
- Smoke deck SHA-256:
  `d4b3080f86cad1fbf7bb011ec21c9003d99bf279bfb85f256c1c6a77a1c89493`.
- Smoke log has no missing-model, unknown-node, or error/warning lines.
- Formal BVM/QB decks were created only after this PASS.

## Formal experiment after smoke PASS

- Canonical topology/stimulus/QB/JTL/terminal unchanged.
- Only insertion: `B_JSL8 -> TLINE_IN -> T_BVM_QB -> QBIN`.
- Fixed engineering value: `Z0=6 ohm`; no Z0 sweep.
- Authorized cases only: `TLINE_TD_0P3` and `TLINE_TD_0P6`, each with masks
  `0011` and `0111`.
- Maximum new formal physical solves: 4.
- Time grid: `.tran 0.1p 200p`; no timestep sweep and no READ extension.
- No current-to-SFQ conversion, sentinel, amplitude scaling, QB parameter
  change, BVM change, LS3/RS change, matching network, or extra delay point.

## Port observability

- Upstream TLINE port: `V(TLINE_IN,0)` and `I(T_BVM_QB)`; the current follows
  the TLINE first-port direction `TLINE_IN -> 0`.
- Receiver-side TLINE port: `V(QBIN)` and `I(LIN|XBQ1)`; this is the current
  entering the QB input inductor from `QBIN` and is the KCL receiver-boundary
  current. JoSIM's public `I(Tlabel)` lookup exposes the first TLINE branch;
  the second internal branch index is not independently named by the print
  language, so it is not silently presented as a second TLINE branch probe.
- `V(COMMON_SL)`, `P/V/I(B_JSL1..8)`, all required QB/JTL/BVM probes and
  terminal probes remain present.
- The inherited canonical `.print I(IB|XBQ1) V(IB|XBQ1)` request is not in the
  required probe set and is not resolved by this JoSIM public print lookup;
  the resulting known `IB|XBQ1` warning is recorded as `UNKNOWN/NOT_SUPPORTED`
  in provenance. No formal metric uses that unavailable column.

## Interpretation boundary

The hypothesis is that finite propagation may disrupt closed-loop temporal
locking. `2*TD` is a design-scale hypothesis only, never a measured return
delay. Raw forward/return landmarks, distortion, reflection-like features and
overall chronology must be measured. Outcomes remain distinct:
`TLINE_FEEDBACK_DEPHASING_SUPPORTED`, `N2_FUNCTIONAL_FAIL`,
`NO_TIMING_EFFECT_OBSERVED`, and `IMPEDANCE_CONFOUNDED`.

No scientific conclusion is assigned before the smoke gate and four formal
raw runs are independently reviewed.
