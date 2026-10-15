# Exploration 历史实验清理结果

## 执行范围

- 执行前 HEAD：`47aafe0e6501e8dbda34618759189fac1d2758b2`；`master`、`bvm/master` 一致，工作树干净。
- 冻结标签 `exploration-precleanup-20261015` 本地及远端均可读取：tag object `4344348d4e0d138baf6aaf44acdc841e82e6fe40`，peeled commit `e290f69c8259ff389a7dc1d457b869ee06891d26`。
- 删除白名单外 **156 个本地直属实验目录**，只保留 `bvm-4x4-diagonal-array-v1-20261009`、`bvm-qb-test-1013`、`sfq_clock_two_read_v1`。Tracked 删除已在清理提交 `a7dee7d0b7af5f95771a70a8aad3e850d0dfcf26` 中完成；它是执行前 HEAD 的直接子提交。
- 提交前目标范围完整复核，0 个新增/缺失/哈希不符文件、0 个跳过、0 个失败；全部目录路径都在仓库内，无符号链接或特殊文件。
- 本报告、路径清单和 QA 随后的报告提交会作为清理提交的直接子提交推送；最终仓库 HEAD 见交接摘要。

## 目录差异与删除内容

清理前本地有 **159** 个直属目录，当前 GitHub `master` 树有 **158** 个。差异是本地独有的 `bvm-read-semantics-audit-and-jsl-width-bracket-v1`：它不在 Git 中，且本地仅有 root 与 `reference/` 两个空目录，无文件；它已随其他白名单外目录移除。其余 158 个目录与 HEAD 对应。直属文件 `receiver-architecture-comparison.md` 不属于目录删除范围，保持原样。

| 内容 | 数量 | 逻辑字节 | 文件分配块字节 |
|---|---:|---:|---:|
| Tracked 文件 | 25,640 | 37,828,372,223 | 37,891,248,128 |
| Ignored 文件 | 5,599 | 8,358,765,900 | 8,371,056,640 |
| 普通 untracked 文件 | 0 | 0 | 0 |
| **文件合计** | **31,239** | **46,187,138,123** | **46,262,304,768** |
| 目标目录自身及内部目录分配块 | 9,773 个目录节点 | — | 40,144,896 |
| **工作树目标合计** | **156 个直属目录** | **46,187,138,123** | **46,302,449,664** |

Ignored 文件逐个按 Phase 6 的 SHA-256 和大小复核后精确 unlink；tracked 文件通过 `git rm` 删除。Tracked 文件与 `exploration-precleanup-20261015` 中 25,640 个路径及 Git blob OID 完全一致。Ignored 文件不在冻结标签或 Git 中；用户已接受其数据不可从 Git 恢复。未执行 GC、LFS prune 或历史重写。

## 磁盘变化

| 测量项 | 清理前 | 清理后 | 变化 |
|---|---:|---:|---:|
| `test/exploration` 分配空间 | 49,390,006,272 B | 3,087,556,608 B | **−46,302,449,664 B** |
| `.git` 分配空间 | 18,745,135,104 B | 18,740,523,008 B | −4,612,096 B |
| `/dev/sdd` 可用空间 | 779,899,838,464 B | 826,187,345,920 B | +46,287,507,456 B |

`test/exploration` 的 `du` 差值与按目标文件/目录 `st_blocks` 汇总完全相同。本次 `.git` 变化主要是索引/目录状态变化；Git pack、对象历史和冻结标签仍在，没有回收历史 Git/LFS 对象。系统级 `df` 的观测在 QA 测试后完成，与目标 `du` 回收量相差 14,942,208 B；该差值不归因于清理对象。D 盘和 Google Drive 均未访问、移动或修改。

## 依赖与停止边界

- 三个保留平台的活动入口、deck include 与资源均闭合在仓库 `circuits/`、`scripts/`、`assets/vendor/plotly.min.js` 及各自保留目录内；没有活动 include 指向此次退休目录。
- 4×4 Plotly 资源仍由 `assets/vendor/plotly.min.js` 提供。
- 仓库 `scripts/` 下有 21 个历史分析/重绘脚本含指向旧实验的显式路径。这些脚本未删除、未修改，也未被三个保留平台的 `try.sh`、`submit.sh` 或 `configure.sh` 调用；对应的旧实验专用分析/重绘功能按用户授权退役，若再次调用可能因数据缺失而失败。
- 没有运行 JoSIM、没有生成 ZIP、没有执行 256 组测试，也没有清理其他目录或云端归档。

精确删除目录与文件、删除前 SHA、Git blob 与删除结果见 [EXPLORATION_FINAL_PRUNE_PATHS.csv](EXPLORATION_FINAL_PRUNE_PATHS.csv)；平台和保护文件 QA 见 [EXPLORATION_FINAL_POST_QA.md](EXPLORATION_FINAL_POST_QA.md)。
