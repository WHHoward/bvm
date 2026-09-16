# Minimal Lin-coupled mutual-RL auxiliary feasibility — bvm-qb-lin-mutual-rl-aux-v1-20260916

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Frozen parent HEAD: `b904851be588ca88d40cf1700d5fef7ce3d889ed`; remote `bvm/master`: `b904851be588ca88d40cf1700d5fef7ce3d889ed`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; mechanical evidence only.
- Experiment B is independent of the LS3 timing-window experiment and does not read its results.

## Single question

Can a minimal passive mutual-RL auxiliary coupled to canonical QB `Lin=1.5 pH` reshape receiver back-action while retaining the canonical galvanic `JSL8 -> QBIN -> Lin -> BJs -> QB core` path?

## Frozen topology

- The canonical QB is not edited. Each deck uses an experimental QB clone with the original `Lin IN 1 1.5p`, BJs, BJ1/BJ2, L1/L2/L3, RJ1/RJ2 and bias unchanged.
- Added inside the clone only: `L_AUX AUX 0 10P`, `R_AUX 0 AUX 20`, `K_AUX Lin L_AUX K`.
- No added JJ, bias, capacitor, PTL, isolated receiver, transformer, or broken QBIN/Lin galvanic path.
- Full forward path remains BVM -> COMMON_SL -> JSL1..8 -> QBIN -> Lin -> BJs -> QB core -> QBOUT -> JTL1..6 -> terminal.
- `L_AUX/R_AUX = 0.5 ps` and 300 GHz impedance notes are engineering scales only.

## K registration

- Fixed `L_AUX=10 pH`, `R_AUX=20 Ω`; only positive K varies: `0.00`, `0.10`, `0.20`, `0.30`.
- `M=K*sqrt(1.5*10) pH`; matrix audit: `{"K000": {"K": 0.0, "M_pH": 0.0, "determinant_pH2": 15.0, "eigenvalues_pH": [1.5, 10.0], "matrix_positive_definite": true}, "K010": {"K": 0.1, "M_pH": 0.3872983346207417, "determinant_pH2": 14.85, "eigenvalues_pH": [1.482389427325872, 10.017610572674128], "matrix_positive_definite": true}, "K020": {"K": 0.2, "M_pH": 0.7745966692414834, "determinant_pH2": 14.4, "eigenvalues_pH": [1.4299884259414304, 10.070011574058569], "matrix_positive_definite": true}, "K030": {"K": 0.3, "M_pH": 1.161895003862225, "determinant_pH2": 13.65, "eigenvalues_pH": [1.3440381299879594, 10.15596187001204], "matrix_positive_definite": true}}`.
- JoSIM K syntax fixture audit: `PASS`; no negative-polarity sweep.

## Authorized solve protocol

- Stage B0: `K000_0011`, `K000_0111` no-op gate first.
- Only if B0 passes: `K010/K020/K030` × `0011/0111` (six further fixed cases).
- Only if a tested K has the registered mechanical candidate `N2=2` and `N3=3`, choose the smallest such K and add exactly `<K>_0001`, `<K>_1111`.
- Absolute maximum is 10 new solves. No other K, L_AUX, R_AUX, polarity, timestep or topology case.

## Registered probes and evidence

- Full BVM/JSL/QB/JTL probes; active JS1/JS2, JM1/JM2, L_SL, JSL8, COMMON_SL, Lin, QBIN, BJ1/BJ2, L1/L2, all JTL stages and terminal.
- Auxiliary `I/V(L_AUX)`, `I/V(R_AUX)`, `V(AUX)`, Lin, QBIN, BVM source and JSL8.
- `[110,121)` and `[121,130)` actual-grid auxiliary current/voltage extrema/RMS and R_AUX dissipation `∫I(R_AUX)^2 R_AUX dt`.
- P(...) is raw radians; turns are independent unwrap/(2π) navigation only, never SFQ counts.

## Unknowns and stop

K=0 is a fixture/no-op gate, not a physical success gate. Mutual reciprocity, passive-realizability beyond the exact linear RL model, solver convergence and any mechanism remain UNKNOWN. After packaging and commit, stop at `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW` with no automatic follow-up.
