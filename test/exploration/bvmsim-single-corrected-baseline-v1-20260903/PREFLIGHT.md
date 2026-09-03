# Corrected historical BVMSim single-BVM baseline — preflight

## Scope

本轮只运行四个 task-local corrected single-BVM cases：
`S0-R-CORRECTED`、`S1-R-CORRECTED`、`S0-J-CORRECTED`、
`S1-J-CORRECTED`。不运行 4-BVM、margin、canonical BVM、timestep sweep、
T1 或 QB 参数变更。

旧 single-BVM raw 不覆盖、不删除、不重解释；它们继续作为
`ARTIFACT_INVALID` 的历史记录，原因是旧 READ 为 SE-only 且日志有 model
fallback。

## Repository and solver

- task start HEAD: `62cc2130bf0a0157ffe6f2d5a8de7ebf075d0c00`
- task-start `git status --short`: clean（在本轮任何修改之前确认）
- solver: `build/josim-cli`
- solver version: `v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- solver SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- preflight timestamp: `2026-09-03T15:25:04+08:00`

`run.sh` 在实际运行前再次要求 working tree clean；setup 必须先提交。

## Frozen source hashes

| source | SHA-256 |
|---|---|
| `BVMSim/bvm_cell.cir` | `009e0683c7d4ffe14e2582c6d0a807669cc9b290639af7298d290ff7bbb43125` |
| `BVMSim/BQ.cir` | `f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd` |
| `BVMSim/library_josim/jtl2.cir` | `ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a` |
| `circuits/models/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `scripts/josim-plot2.py` | `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6` |
| `docs/research/BOUNDARY_SPEC_V2.md` | `6426365f452f59d9e332476cf5d560c1c7ab4c913177ac919a956de7b8a33313` |
| `docs/research/METRIC_SPEC_V2.md` | `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470` |
| `docs/research/BVMSIM_0P1PS_OPERATIONAL_PROFILE_V1.md` | `5a9308c2d7966636555e256cc79688756c8765955022d5570563fef35dab539a` |

The profile typo `RJ2 2 0 4` was corrected to the actual
`RJ2 4 0 4`; `BVMSim/BQ.cir` itself was not changed.

## Historical invalid single-BVM reference

These files are read-only references and remain invalid artifacts:

| condition | old deck SHA-256 | old raw SHA-256 |
|---|---|---|
| `S0-R` | `8b8265c79a64b7158d47f187e7e82573b9643da2f3677081d48fd1b9ac2dbe1f` | `c8ef9d91739e4c10c79bd6352812445145881b091697e7d686c9f3b427b7e559` |
| `S1-R` | `69002d4c3597f998ed63c781980604244ad01ddae35008fbdc1492bee8a452d8` | `7c0838d2fc2cc429eb3537f36c62d1ea72ccb2e491661eb98bc1dbb154092124` |
| `S0-J` | `4a2652a933bccda5d3543e9b1b26cb05ad5cc2b4c6976240afe61d2b4d5042c8` | `481c986b3defcca304ff0afc77d3aa209c925c1d165cd4b63c06c9785aedc128` |
| `S1-J` | `6be7b0171241b89c647f9e902d9a15cc5724f7f4654fea0179c5a1614b24b40d` | `d6075fe4639ca5fd5cd0d882f2d60bcd45482abfde2a1ed5b61f48ba45c838f1` |

Reference directory:
`test/exploration/bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903/runs/single/`.

## Corrected task-local setup hashes

| file | SHA-256 |
|---|---|
| `inputs/S0-R-CORRECTED.cir` | `b59577c95f3beba66e912bf8b60b119f614de8ef906b519febabd50991d3d1f3` |
| `inputs/S1-R-CORRECTED.cir` | `99c2817dd006e09d3bc6fd594cfce6933cf5d1934f69cf5f4a018771d05b0cba` |
| `inputs/S0-J-CORRECTED.cir` | `3ef4f88372438899b201806dd70e6a8d3ef8347857bc33b7b5509fdd218c6102` |
| `inputs/S1-J-CORRECTED.cir` | `c063214cc5edd9e72fb9bf21aae23ab74c8e4af0ce702d34536587941467612a` |
| `inputs/generate_corrected_decks.py` | `ed708c46c1ce091fa881821ea7289a4ffbf0b0cc8c76cb7f2b928a2dc4bdcdf7` |
| `run.sh` | `8b32e6e41084a1b06239553b9c5b6fcb52f6466e377e1633be0a791cbd252d3d` |
| `experiment.yaml` | `140e9653badf8f566bd5c436a1a9a6125e5b211395aa9ac2f1289132bd7db8a3` |

## Closure and protocol checks

- one historical `BVMSim/bvm_cell.cir` BVM instance;
- exactly `B_LD4_01`–`B_LD4_11` plus `BVMout`, all `area=3.2`;
- original `BVMSim/BQ.cir` active `BQ IN OUT`, nominal `RJ1=12 ohm`,
  `RJ2=4 ohm`, internal `IB=250 uA`;
- top-level `circuits/models/jjmit.cir` is explicitly included before BVM and
  terminal JJ devices; QB and JTL retain their historical local model closures;
- `WRITE [50,62) ps`: WL and BL have the same `±100 uA` polarity;
- `READ [70,82) ps`: both logical states use WL=`+100 uA`, SE=`+100 uA`,
  BL=`0`;
- direct runs use a 10-ohm load; JTL runs use six historical JTL cells followed
  by a 10-ohm load;
- `.tran 0.1p 200p`; no interpolation or timestep refinement.

## Authority boundary

This is a historical BVMSim source-class characterization. It cannot be
interpreted as canonical BVM compatibility. The plots are descriptive; raw
CSV, deck, log, solver identity and the analysis record are the evidence.
