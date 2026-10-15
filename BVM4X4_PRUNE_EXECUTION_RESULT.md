# BVM 4×4 历史实验第一批精简结果

## 执行边界与基线

- 执行前 HEAD：`98513618ce54b8201e42b3b4a7c307bff66d1c5d`，分支 `master`，与 `bvm/master` 一致；执行前工作树干净。
- 冻结标签 `exploration-precleanup-20261015`：本地 tag ref `4344348d4e0d138baf6aaf44acdc841e82e6fe40`，指向 commit `e290f69c8259ff389a7dc1d457b869ee06891d26`；清理开始前本地和远端均可读取，且冻结 commit 是执行前 HEAD 的祖先。
- 唯一删除选择来自 `BVM4X4_REVISED_PRUNE_CANDIDATES.csv` 的三个精确筛选条件：`RUN_DIRECTORY + DELETE_OBSOLETE`、`HTML_PAGE + DELETE_GENERATED`、`HANDOFF_ZIP + DELETE_GENERATED`。
- 没有删除 `MANUAL_BATCH_*`、`PACKAGE_QA.json`、9 个参考 run/HTML、其他 Exploration 目录或任何 Drive/D 盘文件。
- 没有运行 JoSIM、生成 raw、执行 256 组测试或创建归档 ZIP。

## 执行结果

| 阶段 | 目标 | 删除结果 | 逻辑字节 | 实测分配块字节 |
|---|---:|---:|---:|---:|
| 1 — HTML | 591 个 ignored HTML | 591 删除，0 跳过 | 21,543,531,925 | 21,545,263,104 |
| 2 — run 目录 | 99 个目录 | 99 删除；目录内 3,042 个跟踪文件（含 99 个 raw） | 9,147,484,249 | 文件 9,155,002,368；目录项 761,856；合计 9,155,764,224 |
| 3 — handoff ZIP | 138 个 ZIP | 138 删除，0 跳过 | 2,669,482,925 | 2,669,780,992 |
| **合计** | **828 个批准目标** | **全部完成** | **33,360,499,099** | **33,370,808,320** |

分配块回收约 **33.371 GB / 31.079 GiB**；逻辑文件字节约 **33.360 GB / 31.069 GiB**。每个 HTML、ZIP 及 99 个 raw 均在删除前按候选记录重新计算 SHA-256 并匹配；99 个 run 目录与 HEAD 中的 Git tree 一致，目录内没有额外 ignored/untracked 文件。每个 ZIP 的 Git blob OID 也与候选一致。逐项路径和身份记录见 `BVM4X4_PRUNE_EXECUTED_PATHS.csv`。

4×4 根目录当前 `du`：逻辑 `1,277,659,811 B`，分配 `1,279,377,408 B`。Phase 6 报告的清理前根目录分配大小为 `34,650,099,712 B`，两次目录快照差为 `33,370,722,304 B`，与逐目标 `st_blocks` 汇总相差 `86,016 B`；该小差异的精确来源为 **UNKNOWN**，不将它计入或抵扣逐目标测量值。

Phase 6 曾记录整个 `/dev/sdd` 可用空间 `747,096,711,168 B`；本次完成后读数为 `779,901,861,888 B`，跨快照增量 `32,805,150,720 B`。该起始快照不是删除前即时读数，不能把这项系统级差值全部归因于本批清理。报告的本批回收量以删除目标的删除前实际分配块为准。

## 保留与恢复边界

- 9 个 `KEEP_REFERENCE` run 目录和 raw 全部保留，9 个 raw SHA-256 在 [BVM4X4_POST_PRUNE_QA.md](BVM4X4_POST_PRUNE_QA.md) 列出。
- 9 张参考 HTML 保持原样；实际 SHA 与候选表的 `current_sha256` 相符，且每页引用的公共 Plotly 资源解析到 `assets/vendor/plotly.min.js`（SHA-256 `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`）。
- `experiment_manifest.json` 未改动：SHA-256 `f9e195f4c966c69b4ae0886bee0ef5ba55eff1dde29faa579a3231171b4d8a15`；108 个 run ID 均保留且唯一。
- 下一普通 run ID 为 `A109`，不会复用 A001–A108。
- 三个受保护直属实验目录仍存在；4×4 内部仅上述批准的三个类别变化。
- `.git` 当前分配大小约 `18,744,954,880 B`。未执行 GC、历史重写或 LFS prune；历史对象仍在 Git 历史/冻结标签中，因此本批缩减的是当前工作树，不承诺缩减 `.git`、远端 Git 历史、LFS、D 盘或 Drive 占用。

## 提交范围

执行前远端 HEAD 与基线一致。最终提交仅包括批准目标产生的 tracked 删除以及本次三个审计交付文件；忽略文件 HTML 删除由审计 CSV 记录。没有创建 ZIP 或修改 Drive。最终提交 SHA 和推送状态由本次交接摘要报告。
