# BVM 存储清理审计清单

审计日期：2026-10-14  
仓库：`WHHoward/bvm`（本地 `/home/howard/JoSIM`）  
审计时 HEAD：`a719c77ba1576f27f4d60839529e7eb058e187e5`  
审计开始时 Git 状态：`master...bvm/master`，无已修改或未跟踪文件。  
本审计只读；没有删除、移动、仿真、Git maintenance、历史重写或 Drive 写入。最终只生成此文件和 `CLEANUP_CANDIDATES.csv`。

## 1. 空间现状（分层统计，不重复相加）

| 范围 | 实际/列示大小 | 说明 |
|---|---:|---|
| 当前工作区 | 约 107 GiB（`du -sh .`） | 实际占用；包含 .git、test 等子项 |
| `.git` | 约 18 GiB | 已包含在工作区；对象 pack 11.43 GiB、loose objects 2.28 GiB、LFS 3.7 GiB |
| `test/exploration` | 约 88 GiB | 已包含在工作区；实验目录及图表 |
| D: 本地 `BVM_Backages` 镜像 | 11,671,456,802 B（约 10.88 GiB） | 独立挂载的本地镜像，不属于仓库工作区 |
| Google Drive `BVM_Backages` 文件夹 | 11,671,479,003 B（约 10.88 GiB） | Drive 元数据列举所得；不是整个 Drive 账户配额/占用 |
| 文件系统 `/dev/sdd` | 1,007 GiB 总量，271 GiB 已用，686 GiB 可用 | 系统级用量，不能与目录/镜像数字相加 |

仓库内扩展名逻辑大小（不是分配块，也不能与 `du` 混算）：CSV 4,059 个 / 25,734,401,633 B；HTML 19,165 个 / 58,111,665,106 B；ZIP 284 个 / 8,534,843,140 B。Git 跟踪 32,498 路径、当前逻辑大小 52,618,548,154 B；ignored 19,223 个文件、43,043,712,602 B；其中 tracked HTML 3,218 个 / 18,119,470,240 B，ignored HTML 15,947 个 / 39,992,194,866 B。审计开始时没有普通未跟踪文件。

## 2. 主要占用来源

- `test/exploration/bvm-4x4-diagonal-array-v1-20261009` 约 41 GiB：runs 9.3 GiB、plots 29 GiB（其中 plots/runs 约 28 GiB、plots/comparison 约 998 MiB）、handoff 2.5 GiB、analysis 134 MiB。子目录互相包含，不能重复计数。
- `bvm-qb-cb-array-topology-v1-20260924` 约 9.0 GiB；`bvm-rloop-one-shot-tuning-v1-20260918` 约 6.5 GiB；`bvm-2x2-rowcol-selection-v1-20260928` 约 4.7 GiB；`sfq_clock_two_read_v1` 约 1.7 GiB。
- 当前最大文件包括：`.git/objects/pack/pack-cb8752fe429b565f842cc9bdcc57b90146ba5599.pack` 7,622,126,243 B；`bvm-qb-cb-array-topology-v1-20260924_delta_U005-U012_20260924.zip` 2,026,365,221 B；另一个 Git pack 1,585,324,831 B。4×4 单次 raw 常见约 95–98 MB。
- 其他：根目录 `handoff` 约 409 MiB、`research` 约 366 MiB、`build` 约 29 MiB、`arti` 约 23 MiB、`analysis` 约 12 KiB；两个调试目录各约 8 KiB。

## 3. Git、冻结源与当前配置

- `.git` 有 7 个 pack（11.43 GiB）、约 2.28 GiB loose objects、约 3.7 GiB LFS；记录有 260 个 LFS 跟踪文件，以及一个约 21.34 MiB 的临时对象。此任务没有运行 gc/prune；删除工作树文件也不会回收历史 Git pack 中的对象。
- V9 的 `SOURCE_MANIFEST.json` 列出 11 个冻结模型源；当前对应源文件 SHA-256 与该 manifest 一致。V9 的 11 个 `sources_frozen` 快照 SHA 也与 manifest 一致。保护 `scripts/bvm_stimulus.py` 及 V0/V9 的 `configure.sh`、`run.sh`；审计时 SHA-256 为：`scripts/bvm_stimulus.py` `4c1a14f05c889df75d576c9d9e99cd58d23ae5459c4016b3128513ef005754b2`，V0/V9 `run.sh` `4c9fc01d1aaf56e844f1498f33c9dad434155bc5f24a4f687828cf42c61f779b`，V9 `configure.sh` `55151938426e5d23389e1e735cd6fe56910e4bb896f9fac8b8d29ed181b56274`。没有修改它们。
- **配置差异需在下一批运行前核对：** `test/exploration/sfq_clock_two_read_v1/final_runs/USER_CASE.env` 与 V9 配置当前为 `READ_INTERVAL_PS=75`、`CLOCK_PERIOD_PS=75`、`SE_CLOCK_DELAY_PS=63`；这与任务背景提到的 80/68 ps 不一致。本次未更改配置。
- V0–V9 全部作为 KEEP。不能从“存在 ZIP”推定某一 run 的唯一 raw、deck、stimulus、manifest 已有完整且可恢复的副本；应逐 run 核验 package 清单和内容 SHA 后才考虑任何后续归档策略。

## 4. Drive 清单与完整性边界

通过已连接的 Google Drive 只读接口，递归列举 `BVM_Backages` 文件夹（ID `1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh`）及其子文件夹：385 个 Drive 对象（380 ZIP、2 Markdown、3 文件夹），共 11,671,479,003 B；所有根目录与子目录均已分页/完整列出。清单含每个对象的 Drive ID、名称、所在文件夹、大小、类型、URL 和时间戳，见 CSV。

**限制：** Drive 元数据接口没有返回文件内容 SHA-256/MD5，也没有整个账户配额/用量字段。本次未下载任何 ZIP。CSV 中 Drive 的 SHA 状态明确为不可从当前 metadata 取得；ZIP 成员数、raw/deck/stimulus/model 及 manifest 内容来自 D: 本地镜像的 central directory/manifest 检查，不代表远端内容已经按字节复核。Drive 与 D: 的 ZIP 名称/大小 multiset 一致（将 ` (1)` 重试后缀归一化），仅是元数据对应关系，不是云端 hash 证明。

D: 本地镜像中 380 个 ZIP 均可解析：301 个含 raw.csv（共 1,644 个 raw 成员实例），220 个含 deck 类成员（2,884 个）、164 个含 stimulus 类成员（3,265 个）、84 个含冻结模型类成员（627 个）；283 个有可识别 manifest，97 个没有，manifest 无解析错误。manifest 收集到 756 条 raw SHA 记录、642 个不同 hash；81 个 hash 在多个包中被引用（114 个额外引用）。这些都只是本地镜像内容盘点，不等于 Drive 云端字节校验。

Drive 中有 58 组同名且同大小 ZIP，按“每组多一份”估算约 1,320,886,648 B 的**候选**云端节省；但云端内容 hash 不可用，故不确认它们真是重复，也不建议现在删除。D: 本地镜像另有 58 组 SHA-256 已证明的完全相同 ZIP 副本，同样约 1,320,886,648 B 本地候选空间。两者是不同存储层，不能合并成一个已确认的可释放数字。仓库与 D: 间发现 276 组跨层相同归档内容；这属于冗余备份关系，不是同一层的释放量。

## 5. 分类与建议

- **KEEP：** 冻结电路及 11 个模型依赖、V0–V9 原始证据、实验合同/研究记录/SHA manifest、所有未核验完整备份的历史 run、当前构建工具、实验归档。
- **ARCHIVE：** Drive 中 `superseded-metadata-v1-bvm-4x4-20261009` 子目录的旧 metadata 包可作为归档候选；不移动、不删除，先确认它只记录过时 metadata 且无唯一证据。
- **DUPLICATE_CANDIDATE：** 本地精确重复 raw/HTML/ZIP，以及 Drive 同名同大小 ZIP。相同 SHA 只证明字节相同，不证明 run 路径/引用可移除；Drive 对象更未取得云端 SHA。
- **REGENERATABLE：** HTML（尤其 ignored HTML）是最大的本地候选：ignored 约 39.99 GB，全部 HTML 约 58.11 GB。但需逐项确认 immutable raw、probe 列表、绘图脚本/版本、参数和 HTML 外部依赖；V0–V9 当前全部保护。删除 tracked HTML 不会缩小 Git 历史。
- **UNKNOWN：** 根目录 `analysis`、`arti`、调试目录、无 manifest 的 97 个本地 ZIP，以及没有明确内容索引的任何对象，暂时全部保留。

### 分层估算（候选，不是已授权操作）

| 层 | 最大候选 | 预计可释放 | 可信度/注意 |
|---|---|---:|---|
| 工作区（ignored HTML） | 15,947 个 ignored HTML | 最多约 39.99 GB | 仅在 raw+渲染配方可复现后；不影响 Git 历史或云端 |
| 工作区（精确重复 raw） | 315 组 / 1,301 文件实例 | 字节额外量约 2.49 GB | 路径绑定证据，需保留每个 run 的身份和恢复映射 |
| 工作区（重复 HTML） | 16 组 / 32 文件 | 约 206 MB | 与 HTML 总量重叠，不能另行相加 |
| 工作区（重复 ZIP） | 2 组 | 约 14.0 MB | 两个 handoff 路径；先核验引用 |
| D: 本地包镜像 | 58 组 exact-SHA ZIP | 约 1.32 GB | 本地 SHA 已证；云端 SHA 未证，不代表可删云端 |
| Google Drive | 58 组同名同大小 ZIP | 约 1.32 GB | **未取得云端 SHA，纯候选**；禁止本次删除 |
| Git 历史 | Git pack / LFS | 当前无安全直接清理量 | 不运行 gc、prune、filter-repo 或 force-push；删工作树不会减少旧 pack |

这些候选之间有重叠或分属不同存储层，**不可求和为单一“可释放空间”**。

## 6. 推荐的下一步（待单独授权）

1. 先审阅 `CLEANUP_CANDIDATES.csv`，按 run ID 建立“raw/deck/stimulus/source SHA → package → Drive file ID”映射，特别确认 V0–V9 和失败 run 的可恢复性。
2. 先从 ignored HTML 中挑选少量明确可重建的页面做人工复现检查；确认后再单独授权精确路径清理。不要整目录删除。
3. 对 D: exact-SHA 重复 ZIP，逐个确认包内 manifest/引用并保留恢复路径；对 Drive 同名同大小项，在云端 hash 不可用前不删。
4. Git 历史占用另行评估；本次任务禁止的历史重写/GC 不应作为当前清理步骤。
5. 只有在你明确授权具体目标和操作后，才执行清理。本次审计至此停止。

