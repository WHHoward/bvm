# JM2-connected single-BVM A/B Quick — preflight

## Scope

本目录只建立并运行 single-BVM 的
`HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT`。历史
`BVMSim/bvm_cell.cir`、corrected single baseline 的 raw/deck/report/plot 均保持
不变；本轮不进入 4-BVM、参数扫描、timestep 扫描或 canonical BVM。

唯一允许的物理改动是 BVM variant 中：

```text
historical: L_M2  2 4 24.5P
connected:  L_M2  2 3 24.5P
```

该改动将 `node2 → L_M2 → node3 → B_JM2 → node4` 接成 intended series path。
其余参数、模型、激励、QB、JTL、负载、时间步和停止时间不变。

## Setup snapshot

| 项目 | 值 |
|---|---|
| HEAD before setup | `55632a7fe70bf7bab3cfb80ed768f9135582254c` |
| working tree before setup | clean |
| solver | `build/josim-cli`, JoSIM `v2.7.2837d13` compiled 2026-05-30 20:37:57 |
| solver SHA-256 | `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2` |
| classic renderer | `scripts/josim-plot2.py` |
| renderer SHA-256 | `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6` |
| visual authority | `bvmsim-single-corrected-baseline-v1-20260903` current plots and renderer |
| historical BVM SHA-256 | `009e0683c7d4ffe14e2582c6d0a807669cc9b290639af7298d290ff7bbb43125` |
| connected variant SHA-256 | `0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54` |
| historical QB SHA-256 | `f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd` |
| historical JTL SHA-256 | `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a` |
| shared jjmit SHA-256 | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |

`analysis/setup_qa.json` 记录的 variant diff QA 为 PASS：源文件与 variant 只有
第 37 行 `L_M2` 的第二节点 `4 → 3` 不同；四个 candidate deck 与对应 corrected
single reference 在移除 BVM include 路径和新增内部电感探针后逐行一致。

## Frozen fixture

- S0/S1 的 WRITE 分别为 `WL=BL=-100/+100 µA`，时间 50–61 ps；
- 两个逻辑态的 READ 完全相同：`WL=+100 µA`、`SE=+100 µA`、`BL=0`，时间 70–81 ps；
- original `BVMSim/BQ.cir`：`RJ1=12 Ω`、`RJ2=4 Ω`、`IB=250 µA`；
- terminal sensing line：11 个 `B_LD4_01..11` 加 `BVMout`，共 12 个 area=3.2 JJ；
- R case：直接 10 Ω；J case：六级 historical JTL（280 µA/cell）加 10 Ω；
- `.tran 0.1p 200p`，使用记录的 `build/josim-cli`。

## Required run set

只运行新 B-side：`S0-R-JM2C`、`S1-R-JM2C`、`S0-J-JM2C`、`S1-J-JM2C`。

A-side 只读取现有 immutable corrected baseline：direct 使用 `S0/S1-R-CORRECTED`，
JTL 使用带完整 JTL 探针的 `S0/S1-J-CORRECTED-RERUN`；不重新运行 A-side。

## Status

这是 preregistered setup，必须先提交并在 clean working tree 上运行。运行结束后
状态仍为 `AWAITING_USER_REVIEW`；本文件不授予任何后续实验授权。
