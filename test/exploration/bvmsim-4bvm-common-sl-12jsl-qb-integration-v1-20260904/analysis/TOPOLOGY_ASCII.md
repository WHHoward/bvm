# Static topology preflight — common-SL 12-JSL QB integration

本页是生成 deck 前的静态连线记录。它描述实际被 include 的
`bvm_jm2_connected.cir`、`BVMSim/BQ.cir` 和
`BVMSim/library_josim/jtl2.cir`，不是从论文图反推的示意图。

## Actual BVM output endpoint

每个实际 BVM 的末端保持不变：

```text
N7 / LPSL first node
        │
        ▼
L_PSL  (0.5 pH)
        │
        ▼
R_SL   (12.0 ohm, internal BVM resistor; one per BVM)
        │
        ▼
L_SL   (0.4 pH)
        │
        ▼
SL port = COMMON_SL
```

本轮没有在 BVM 外部再加 RSL。四条内部路径分别是
`LPSL → RSL → LSL → COMMON_SL`。

## New four-BVM common-SL connectivity

```text
XBVM1 WL1 BL1 SE1 COMMON_SL BVM ─┐
XBVM2 WL2 BL2 SE2 COMMON_SL BVM ─┤
XBVM3 WL3 BL3 SE3 COMMON_SL BVM ─┼── COMMON_SL
XBVM4 WL4 BL4 SE4 COMMON_SL BVM ─┘       │
                                         │
                                  B_JSL01
                                         │
                                  B_JSL02
                                         │
                                    ...
                                         │
                                  B_JSL12
                                         │
                                        QBIN
                                         │
                                  XBQ1 ... BQ
                                         │ QBOUT
                                  XJTL1 ... XJTL6
                                         │ JTL6_OUT
                                  R_TERM = 10 ohm
                                         │
                                        GND
```

## Frozen receiver internals

```text
QBIN → Lin → BJs/BJ1/BJ2 internal BQ network → QBOUT
QB source: BVMSim/BQ.cir, subckt BQ IN OUT

QBOUT → XJTL1 → XJTL2 → XJTL3 → XJTL4 → XJTL5 → XJTL6
       each stage is the exact `jtl` subckt in BVMSim/library_josim/jtl2.cir
       each stage retains its internal 280 uA bias source
```

## Static exclusions

- no per-cell JSL branch;
- no second load branch;
- no `B_LD*`, `BVMout`, `SL1..SL4` or residual daisy segment;
- no external duplicate `R_SL`/RSL;
- no canonical `circuits/bvm/bvm_cell.cir`;
- no QB bypass around the 12-JSL stack;
- no extra input L/R, matching network, shunt, transformer or termination.

The machine proof is in `analysis/topology_preflight.json` and must pass before
the physical run.
