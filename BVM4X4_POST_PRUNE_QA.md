# BVM 4×4 清理后 QA

## 文件与证据检查

- 精确候选不存在：99/99 个 obsolete run 目录、591/591 张 generated HTML、138/138 个 handoff ZIP。
- 运行目录清理前，99 个目录共 3,042 个跟踪文件，实际文件集合与 Git 跟踪集合完全相同；不存在目录内新增、ignored 或未跟踪文件。99 个 raw 的 SHA-256 均匹配候选记录。
- ZIP 清理前逐个核对路径、普通文件类型、大小、SHA-256 和 Git blob OID；138 个全部匹配。
- HTML 清理前逐个核对精确路径、普通文件类型、大小和 SHA-256；591 个全部匹配。使用精确文件 `unlink`，未递归删除 plots 目录。
- staged 删除集合严格等于 99 个已批准 run 目录在基线 HEAD 中的 3,042 个跟踪后代文件，加 138 个批准 ZIP；共 3,180 个 Git 路径，范围外为 0。
- `MANUAL_BATCH_*`、`PACKAGE_QA.json`、配置、manifest、冻结源、公共资产以及其他 156 个 Exploration 顶层目录不在 staged 删除集合。

## 保留 run 与 raw

| Run | Raw SHA-256 |
|---|---|
| A018_T1_ALL_QUIET | `9a17cfe79805b16c7977aa23a766be9e2a7101a5553da6162f26d4a141123a1f` |
| A019_T1_ALL_PLUSE | `3cabda93970826369616d1749cb242f6e9a59576b49e55822126c2fb81212ecf` |
| A027_FULL_CB_CHAIN_ALL_CLOCK | `939e6024928be84df809532ecd8b716b815a9b96ea498324fc5c30b712100e46` |
| A030_CARRY_POST_CB_SJTL_ALL_200 | `027bb32757c1b426b2876ad2d694b6560cea58e6d54a733fd821408538ae166b` |
| A031_CARRY_POST_CB_SJTL_ALL_210 | `c796e9b13024720fc1f5e3268e4174b4064343ab83a57bed3967ac4ed2c3dddf` |
| A032_CARRY_POST_CB_SJTL_PAPER_210 | `439e9444964adf59043d11b39808c33fcd4f29d63d45835af4fa8cb5333546b5` |
| A033_CARRY_POST_CB_SJTL_3X3_210 | `d4ed238cf7f7b113bb2e32c94b904d027ad5cf2c443502ae5183f3c4d3b1383c` |
| A107_MANUAL_CARRY5_11x13_210 | `e68954a3745a2193140769eeddbfd740775d26615112aaad9165c11a2cb113ac` |
| A108_MANUAL_CARRY5_3x3_210 | `b67b567c37496716c6bf1c0355b87eb96a3ea06b5071185c296660e2843fdf16` |

## 保留 HTML 与 Plotly

9 张保留页面在清理前后 SHA-256 不变，且共享资产引用均可解析：

| Run | HTML SHA-256 |
|---|---|
| A018_T1_ALL_QUIET | `1dddf0399a000d6613197e7164fd794d2903256ca0125c942fed32550c18a14e` |
| A019_T1_ALL_PLUSE | `e1135f547ad250221db37575fde8e959998a7c352704f752fd530062e3fce216` |
| A027_FULL_CB_CHAIN_ALL_CLOCK | `b47b862c07212750acf7528daec87773f6d8dccab121ccadfa50bcfd41d3a9b5` |
| A030_CARRY_POST_CB_SJTL_ALL_200 | `cd258692d9289d23222436f976f5385d690d223706d63dac88b0ab621acba803` |
| A031_CARRY_POST_CB_SJTL_ALL_210 | `ce028376dfc31a3bbeebae322ff6a0343c1d516ea0621a718d743cee3950a362` |
| A032_CARRY_POST_CB_SJTL_PAPER_210 | `27c6c5e811f60105753718d94ba6bcf1404f23a9f9bdecfcc15e7b96b8143186` |
| A033_CARRY_POST_CB_SJTL_3X3_210 | `f7643298d86b7861900ba7dcd1b6af577660400de04a112e76ee409c5d76fbd5` |
| A107_MANUAL_CARRY5_11x13_210 | `0dd4d7ae96dc61b5f67f2594593119de2033ae8325021819c47119762707873c` |
| A108_MANUAL_CARRY5_3x3_210 | `19fd86f202eeb957189125b41c4a37cb3c509fddc943dc05bdefd39c5d1b0e17` |

候选表旧字段 `sha256_recorded` 对这 9 页保留了 asset-path 修复前的值；清理前实际值与 `current_sha256` 一致（`current_sha_status=rehashed_after_asset_path_fix`）。本 QA 使用并复核当前值，没有重写或重新生成页面。

## 平台与提交工具回归

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q .../tests/test_platform.py .../tests/test_submit.py`：**45 passed**。
- 未禁用 pytest 插件自动加载的首次尝试因环境插件导入失败：`ModuleNotFoundError: No module named 'lark'`（来自 `/opt/ros/humble/.../launch_testing`）；禁用全局插件自动加载后项目测试通过，没有改动环境或依赖。
- 4×4 `./try.sh --dry-run`：**DRY RUN PASS**，`solver_invoked=false`、`physical_solve_count=0`、未创建 run 目录。
- 4×4 `./submit.sh PRUNE_POST_CLEANUP --dry-run`：`NO_PENDING_RUNS`、`package_created=false`、`solver_invocations=0`。
- 平台直接分配器返回下一编号 **A109**。
- manifest 仍有 108 个唯一编号，SHA-256 未变：`f9e195f4c966c69b4ae0886bee0ef5ba55eff1dde29faa579a3231171b4d8a15`。
- 没有调用 JoSIM，也没有生成实验 raw 或包。

## 剩余说明

- 原始数据删除后不会由当前工作树恢复；清理前冻结标签仍可从远端读取，Git 历史对象和 LFS 没有被压缩或 prune。此为 Git 版本历史恢复，不等于 Drive 归档检查。
- Drive ZIP 与 D 盘镜像均未访问或修改。
- pytest 生成或触及的 ignored 缓存不在本次批准范围，未清理。
