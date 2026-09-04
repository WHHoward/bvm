# Static topology preflight — common-SL variant

本文件在生成物理 deck 之前建立。它描述的 BVM 是
`test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir`
中的 historical JM2-connected variant，不是 `circuits/bvm/bvm_cell.cir`。

## Actual BVM endpoint

实际子电路的输出端点是 `L_PSL -> R_SL -> L_SL -> SL`：

```text
WL+BL -> N1 ->+-- B_JM1 || R_JM1 -> LM1 -> GND
             |
             +-- LM2 -> B_JM2 -> N2 -> LM3 -> N5 -> LPM -> GND
                                  |
                                  +-> LS1 -> B_JS1 -> N3
SE -> R_SE -> LPSE ----------------+
N3 ->+-- R_S ------------------+
     +-- LS3 -------------------+-> N6
N5 -> LS2 -> B_JS2 -------------> N6
N6 -> LPSL -> R_SL (12 ohm) -> N8 -> LSL -> SL (external endpoint)
```

关键原始端点行：

```text
L_PSL   10  11  0.5P
R_SL    11  12  12.0
L_SL    12  SL  0.4P
```

因此本实验中每颗 BVM 的内部 `R_SL=12 ohm` 保留；顶层不得再放一个
外部 RSL。

## Proposed 4-BVM common-SL connectivity

```text
XBVM1 WL1 BL1 SE1 COMMON_SL BVM -- internal LPSL-R_SL-LSL --+
XBVM2 WL2 BL2 SE2 COMMON_SL BVM -- internal LPSL-R_SL-LSL --+-- COMMON_SL
XBVM3 WL3 BL3 SE3 COMMON_SL BVM -- internal LPSL-R_SL-LSL --+
XBVM4 WL4 BL4 SE4 COMMON_SL BVM -- internal LPSL-R_SL-LSL --+
                                                               |
                                                               +-- B_COL_LOAD01 COMMON_SL COL01 jjmit area=5.0
                                                               +-- B_COL_LOAD02 COL01 COL02 jjmit area=5.0
                                                               |       ...
                                                               +-- B_COL_LOAD12 COL11 0 jjmit area=5.0
```

`jjmit` 的共享基准 `ICRIT=0.1 mA`，仓库 area convention 下
`area=5.0 -> Ic=0.5 mA=500 uA`；因此这里只有一条、共 12 个元件的共享
负载链。`COMMON_SL` 的直接 shared-load current authority 是
`I(B_COL_LOAD01)`，四个 BVM 输出电流的独立观测是
`I(L_SL|XBVM1..4)`，二者另以 KCL 比较。

## Forbidden connectivity checked by the static script

- 顶层不出现 `R_SL`/其它外部 RSL；每个 BVM 只通过 variant 内部的一个 `R_SL` 输出。
- 顶层不出现 `B_LD*`、`BVMout` 或任何 per-cell 12-JJ stack。
- 只出现一个 `B_COL_LOAD01..12` 连续串联栈，末端接地。
- 不出现 `SL1..SL4` 之间的 daisy segment 或 `nld*` 中间链。
- 不出现 QB、JTL、10-ohm termination 或相关 include。
- 四个 BVM 的外部连接除实例/源命名外完全相同，SL 端都为 `COMMON_SL`。

最终 machine-readable 结果见 `analysis/topology_preflight.json`；该文件必须为
`PASS` 后才允许运行 `run.sh`。
