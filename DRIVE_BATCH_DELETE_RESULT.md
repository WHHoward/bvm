# Google Drive 批量清理执行结果

**状态：完成（224/224）**。本轮只使用 G: DriveFS 的精确文件路径执行普通删除；没有调用 Drive 永久删除 API，没有清空 Trash，没有操作 D 盘，也没有运行 JoSIM。

## 执行范围与验证

- 目标目录：`BVM_Backages`，Folder ID `1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh`
- 清单：`DRIVE_LOCAL_DELETE_MAPPING.csv` 中状态为 `NOT_DELETED; AWAITING_USER_CONFIRMATION_AFTER_TRIAL` 的 224 条；逐项按 Drive File ID、父目录、名称、大小、修改时间及映射的 G: 精确路径复核。没有扩大到 105 条歧义映射或 7 条引用风险项。
- 删除方式：Windows PowerShell 对每个已核验的 G: 路径使用 `Remove-Item -LiteralPath`；每个路径在操作前复核存在、名称、父目录和大小，操作后确认本地路径消失。
- 内容读取说明：第三批有 4 条映射带既有 SHA-256，本轮再次计算并与映射值匹配，总逻辑大小 34,793,217 B；其他 220 项未读取内容做哈希。对这 4 项的 G: 文件内容读取可能使 DriveFS 写入/保留流式缓存，本轮没有测量网络传输量或实际分配空间；没有调用 Drive connector 下载接口。
- Drive 同步：每批查询相应 Drive 父目录，确认本批 File ID 已从原目录消失；每批还重新核验 43 个保留 ZIP 与 2 份 Markdown。批后文件数与预期一致。
- 全量收尾：Drive 当前清单与预期剩余的 157 个 File ID 完全一致（缺失 0、意外 ID 0）；其中 45 个保留项、105 个歧义候选、7 个引用风险候选。G: DriveFS 本地递归枚举也是 157 个文件，逻辑长度合计与 Drive 清单相同。

| 批次 | 删除数 | 清单逻辑字节 | Drive 原目录同步轮询 | 批后活动文件数 | 保留集 |
|---:|---:|---:|---:|---:|---|
| 1 | 30 | 715,295,961 | 4 | 351 | 45/45 PASS |
| 2 | 30 | 462,668,164 | 3 | 321 | 45/45 PASS |
| 3 | 30 | 444,936,779 | 3 | 291 | 45/45 PASS |
| 4 | 30 | 2,856,840,335 | 4 | 261 | 45/45 PASS |
| 5 | 30 | 1,586,207,874 | 5 | 231 | 45/45 PASS |
| 6 | 30 | 728,786,334 | 5 | 201 | 45/45 PASS |
| 7 | 30 | 1,090,683,831 | 4 | 171 | 45/45 PASS |
| 8 | 14 | 191,329,643 | 4 | 157 | 45/45 PASS |
| **合计** | **224** | **8,076,748,921** | — | **157** | **每批通过** |

## 空间与可恢复性边界

- 224 个目标从活动 Drive 目录移除的逻辑长度：**8,076,748,921 B（约 7.52 GiB）**。
- 试删完成后、批量开始前的目录逻辑长度：11,671,435,704 B；本轮后：**3,594,686,783 B**。差值与 224 项清单大小完全相符。
- 上述是活动目录的逻辑文件大小变化，不是实测本机物理磁盘块回收量。
- 文件通过 DriveFS 普通删除后按用户确认的单文件试删行为进入 Trash；本轮没有逐一读取 Trash 清单，因此对 224 个文件的 Trash 成员身份不作逐 ID 独立声称。Google 文档说明 Drive for desktop 的删除会同步到云端；Trash 中的文件在永久删除前仍计入云存储。[Drive for desktop 删除说明](https://support.google.com/drive/answer/2375102?hl=en)。**本轮永久释放的 Google 配额为 0；未清空 Trash。**
- `/mnt/d/BVM_Backages` 是独立镜像路径，本轮未读写或删除其中任何 ZIP。

试删 ZIP `1TcEQR5jVy1JJTYAq9CYxqkxlNSNWVSix`（43,299 B）已在本轮之前由用户确认进入 Trash；它不属于上述 224 项。连同试删，活动目录相较原始 382 文件清单共少 225 个文件；本批正式执行数仍为 224。

## 保留候选及 V9_analysis

- 105 个 `AMBIGUOUS_DUPLICATE_TITLE_IN_SAME_PARENT` 和 7 个 `EXPLICIT_DRIVE_SUMMARY_REFERENCE` 均未删除。具体 ID、大小、重复组以及引用摘要见 [DRIVE_REMAINING_CANDIDATES.md](DRIVE_REMAINING_CANDIDATES.md)。
- 当前 7 个显式引用中，A001–A006 的六个 ZIP 被 Drive 文档 `bvm-4x4-diagonal-array-v1-20261009_BATCH_SUMMARY.md`（File ID `1rv2zR0g6KBSMUE_aZFbgZRkM2AQ3gE3E`）引用；2×2 A001 ZIP 被 `BATCH_SUMMARY.md`（File ID `1OvoDsAxSVXTSSetGnAoS3M25Fo6qXk-V`）引用。它们只因本次清单标为引用风险而保留，未据此推断必须永久保留。
- V9_analysis 的 BL_C3/SE_R3 关闭和 raw 更新按用户说明属于有意的手动 11×13 实验，用户已检查结果正常。本轮未恢复、覆盖或运行该实验。只读检查发现 `stimulus.inc` 注释及 `CASE_CONFIG.json` 仍写 15×15、`1111/1111`、75/63 ps；PWL 则在读取阶段将 BL_C3 和 SE_R3 置零。故当前文件的生成元数据与用户确认的 11×13 意图不一致；需维持独立实验身份，不能把旧 15×15 结果与这份手动实验合并。这个身份差异未在本轮修正。

## 仓库状态与交付

- 起始 HEAD：`5cf60fdb3866f080aaa35c534da1a89ec62b3616`；冻结标签 `exploration-precleanup-20261015` 可读取。
- 没有运行 JoSIM，没有修改 V9_analysis，没有提交或推送。本报告及配套 CSV 是本轮新增交付；仓库代码和用户数据未被本轮改写。
- 逐 File ID 执行明细：[DRIVE_BATCH_DELETE_EXECUTED_IDS.csv](DRIVE_BATCH_DELETE_EXECUTED_IDS.csv)。
