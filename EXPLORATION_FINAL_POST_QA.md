# Exploration 清理后 QA

## 目录与 Git 范围

- `test/exploration` 直属目录精确为：`bvm-4x4-diagonal-array-v1-20261009`、`bvm-qb-test-1013`、`sfq_clock_two_read_v1`。
- 156 个白名单外直属目录全部不存在；一个本地独有的空目录也按精确路径移除。直属文件 `receiver-architecture-comparison.md` 保留。
- 清理提交只包含 25,640 个目标 tracked 删除；与 Phase 6 文件清单按 156 个精确目录前缀比较，路径集合完全一致。报告提交仅添加本次三份报告/清单。
- 已删除的 5,599 个 ignored 文件在清理前均与 Phase 6 的路径、大小、SHA-256 一致；其中每个文件的 SHA 在 unlink 前再次校验。Ignored 数据不在 Git/冻结标签中，恢复能力不作声称。
- 目标范围内 symlink=0、special file=0、untracked non-ignored=0；没有跟随任何链接。
- 冻结标签与删除前 Git 树的目标文件集合及 blob OID 完全一致（25,640/25,640）；标签只覆盖 tracked 内容。

## 三个保留平台的重要身份

以下身份在清理前后复核一致：

| 文件 | SHA-256 |
|---|---|
| `circuits/bvm/bvm_cell_0923_v9_bse.cir` | `76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489` |
| `assets/vendor/plotly.min.js` | `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770` |
| 4×4 `experiment_manifest.json` | `f9e195f4c966c69b4ae0886bee0ef5ba55eff1dde29faa579a3231171b4d8a15` |
| QB `CLOSED_N4_1111/actual_deck.cir` | `376bf48b756f1da141485b03fc7bdd4dec2a5342f379997442dce4fe29263df5` |
| QB `CLOSED_N4_1111/raw.csv` | `6c49367e5e798a69e5ac999d7465d0a78027fb6dac53dc29d1743b2b2b950827` |
| V9_analysis `deck.cir` | `474a254f4511fb46bea6afd36500aa28111323f23f1be66b720170ee297ccb70` |
| V9_analysis `stimulus.inc` | `824eb8c5fe7adf2369721c87b76ec66c39165d4eacb8c72fefb45b90df877211` |
| V9_analysis `raw.csv` | `03c2af990bd87c1c8cbe355245127f9edb619d8740c1cbe0679cef4b61420339` |

V9_analysis 冻结的 11 个 source 也逐个核对一致：

| 文件 | SHA-256 |
|---|---|
| `00_jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `01_bvm_cell_0923.cir` | `76b7b90b4e58cc45d55adc24d1bc6e626957461a2abe21ca4a33319d58ac6489` |
| `02_BQ_0928.cir` | `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a` |
| `03_sJTL_0923.cir` | `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688` |
| `04_CB_0928.cir` | `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370` |
| `05_MERGE.cir` | `79b0d219db60ca41a03d732eaac82b436114b02436cf4dc8719e9b25d58940e0` |
| `06_dcsfq2.cir` | `76e9866ef32a73ac8bda2a4698ba1d39dc8e1c83312da168ba0aab8eee5fc280` |
| `07_jtl2.cir` | `9ec481453c5aa519dec18c07efc2c377b11f3ca0345c6e7971bd6806036455aa` |
| `08_t1_cell_tunable.cir` | `da7f1c5065081caccbd6cbd698630a9cf94019840e39e3beb0839b99e5e7bcdb` |
| `09_DFF.cir` | `e63473b890b67bd968ee9891518e7b4f9b52560cb49e20fa18fa50f03b6bc6f0` |
| `10_d0_jtl_tunable.cir` | `b242741e4630a54411db48de649361e8daedfd6a083358d675d2fdf657314039` |

## 4×4 保留 run 与页面

九组参考 raw 与九张 HTML 均在清理前后保持原 SHA；HTML 的相对引用仍解析到共享 Plotly 资源。

| Run | Raw SHA-256 | HTML SHA-256 |
|---|---|---|
| A018_T1_ALL_QUIET | `9a17cfe79805b16c7977aa23a766be9e2a7101a5553da6162f26d4a141123a1f` | `1dddf0399a000d6613197e7164fd794d2903256ca0125c942fed32550c18a14e` |
| A019_T1_ALL_PLUSE | `3cabda93970826369616d1749cb242f6e9a59576b49e55822126c2fb81212ecf` | `e1135f547ad250221db37575fde8e959998a7c352704f752fd530062e3fce216` |
| A027_FULL_CB_CHAIN_ALL_CLOCK | `939e6024928be84df809532ecd8b716b815a9b96ea498324fc5c30b712100e46` | `b47b862c07212750acf7528daec87773f6d8dccab121ccadfa50bcfd41d3a9b5` |
| A030_CARRY_POST_CB_SJTL_ALL_200 | `027bb32757c1b426b2876ad2d694b6560cea58e6d54a733fd821408538ae166b` | `cd258692d9289d23222436f976f5385d690d223706d63dac88b0ab621acba803` |
| A031_CARRY_POST_CB_SJTL_ALL_210 | `c796e9b13024720fc1f5e3268e4174b4064343ab83a57bed3967ac4ed2c3dddf` | `ce028376dfc31a3bbeebae322ff6a0343c1d516ea0621a718d743cee3950a362` |
| A032_CARRY_POST_CB_SJTL_PAPER_210 | `439e9444964adf59043d11b39808c33fcd4f29d63d45835af4fa8cb5333546b5` | `27c6c5e811f60105753718d94ba6bcf1404f23a9f9bdecfcc15e7b96b8143186` |
| A033_CARRY_POST_CB_SJTL_3X3_210 | `d4ed238cf7f7b113bb2e32c94b904d027ad5cf2c443502ae5183f3c4d3b1383c` | `f7643298d86b7861900ba7dcd1b6af577660400de04a112e76ee409c5d76fbd5` |
| A107_MANUAL_CARRY5_11x13_210 | `e68954a3745a2193140769eeddbfd740775d26615112aaad9165c11a2cb113ac` | `0dd4d7ae96dc61b5f67f2594593119de2033ae8325021819c47119762707873c` |
| A108_MANUAL_CARRY5_3x3_210 | `b67b567c37496716c6bf1c0355b87eb96a3ea06b5071185c296660e2843fdf16` | `19fd86f202eeb957189125b41c4a37cb3c509fddc943dc05bdefd39c5d1b0e17` |

Manifest 仍含 108 个唯一历史 run ID；下一普通编号为 **A109**。三个保留直属目录都存在且不是符号链接。

## 入口与测试

- 活动依赖检查：4×4 `try.sh`/`submit.sh` 使用其平台脚本与仓库公共源；QB 本地 deck 使用仓库 `circuits/` 和本地 snapshot；SFQ configure 使用仓库 `scripts/bvm_stimulus.py`，V9_analysis 使用其保护目录内冻结 source。未发现活动 include 指向退休目录。
- 根目录 `scripts/` 下 21 个历史分析脚本含旧实验路径。这些实验专用分析入口保留源码但已没有对应数据；它们不是三个平台的运行/提交入口，不能再用于退役案例。源脚本未修改。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q .../tests/test_platform.py .../tests/test_submit.py`：**45 passed**。
- 4×4 `./try.sh --dry-run`：**DRY RUN PASS**，`solver_invoked=false`、`physical_solve_count=0`，未创建 run 目录。
- 4×4 `./submit.sh EXPLORATION_FINAL_PRUNE --dry-run`：`NO_PENDING_RUNS`、`package_created=false`、`solver_invocations=0`。
- 没有 JoSIM 调用或新 raw；Drive/D 盘未访问。
