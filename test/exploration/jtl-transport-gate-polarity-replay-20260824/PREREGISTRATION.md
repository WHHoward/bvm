# JTL transport-gate reconciliation + single-pulse polarity replay closure

## Scope

Parent HEAD: `090b8268132b9d5d4ae2e81a0131cafc458c24c1`.

本 Exploration 停止 M1–M5 的参数延伸，只回答两个相邻问题：

1. 将 R11、M1、M5-PC 的相位/面积证据统一拆成严格连续单调段与
   full-window/pre-post settled-well 两个层次后，哪些主张仍然成立；
2. accepted Q0+10Ω 的 pulse 5 完整 `V(OUT,t)` 在标准两-cell JTL 上，原极性
   与反极性是否产生不同的逐级 transport-gate 结果。

## Frozen inputs

- Standard topology: `circuits/standard/JTL.cir`, unchanged.
- Model: `circuits/models/jjmit.cir`, unchanged.
- JoSIM: recorded `build/josim-cli`, `dt=0.0125 ps`, stop `300 ps`.
- Source: accepted Q0 scaled `IIN=68.4 µA` + `10 Ω` raw;
  `inputs/source/pulse5_vout.csv` is the exact raw subset `200 ps <= t < 260 ps`.
- Replay uses every source sample at its original absolute time. No resampling,
  amplitude scaling, polarity shaping, rectification, hold, or JTL/QB change.
- The reverse case negates every voltage sample and changes no other quantity.
- JTL input is an ideal diagnostic replay port, not a physical Q0-to-JTL
  interface claim. The source is held at zero after the registered pulse window.

## Matched replay cases

| case | input | JTL topology | expected use |
|---|---|---|---|
| original | pulse-5 `V(OUT,t)` as saved | frozen standard two-cell JTL | polarity closure |
| reverse | exact negative of the same trace | same frozen JTL | polarity closure |

The JTL has 200 ps of pre-pulse simulation time for bias settling. No new
positive control is run in this batch; R11 remains the accepted standard-JTL
positive-control reference.

## Evidence windows

For the existing single-pulse replays and the new pulse-5 replays, the common
absolute windows are:

- pre settled well: `[208, 210) ps`;
- activity/full-window comparison: `[210, 235) ps`;
- post settled well: `[235, 260) ps`.

R11/M5-PC positive controls use their existing registered `[8,10)`, `[10,35)`
and `[35,60)` ps windows. Existing M1/M5 raw are not regenerated.

## Event evidence boundary

For each of the four JTL junctions, report raw phase in radians and derived
turns (`Δphase/(2π)`). A strict local event requires one continuous monotonic
segment with absolute phase change at least one turn, same-JJ/same-segment
direct voltage area with matching sign and bounded residual, and post-event
bounded/retrap behavior. Total activity-window phase change, phase range,
voltage peak, or over-critical current alone is not an event.

Separately report full-window endpoint/net phase and direct voltage area, plus
pre/post median phase, p2p and voltage RMS. These full-window quantities are
not substituted for strict monotonic event evidence.

## Stop rule

After the two replay runs and unified report, stop. Do not sweep JTL/QB bias,
inductance, junction area, damping, source amplitude, timing, or polarity
other than the registered exact reversal. Do not attach T1 or modify canonical
BVM/QB circuits.
