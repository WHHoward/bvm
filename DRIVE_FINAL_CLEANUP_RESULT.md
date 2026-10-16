# BVM Drive 最终清理执行结果

**状态：因同步/同名组一致性检查触发 STOP，未完成 112 项清理。** 本轮完成 39 项精确普通删除；目标 13dW… 的临时改名后，目录同名组核对不一致，已恢复原名且未删除。其余项目（含 7 个 summary 引用 ZIP）未继续处理。

## 基线与最终活动目录

- 仓库：`WHHoward/bvm`
- 执行起始 HEAD：`3e420f1cfecdd042563ca3cecc6bc6307e8ef2d5`；`exploration-precleanup-20261015` 可读取。
- Drive 目录：`BVM_Backages`，Folder ID `1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh`
- 本轮开始时：157 个活动文件，逻辑长度 3,594,686,783 B。
- 停止后：**118 个活动文件，2,680,674,041 B**。Drive 活动列表与 G: DriveFS 递归文件数及逻辑长度相符；剩余 File ID 集合精确等于 45 个 KEEP + 66 个未删歧义候选 + 7 个未删引用候选，缺失 0、额外 0。
- 45 个 KEEP 项每批均核对名称、大小与 File ID，最终 45/45 仍在。D 盘镜像未操作。

| 批次 | 目标动作数 | 普通删除成功 | 批后活动文件数 | 保留集 | 结果 |
|---:|---:|---:|---:|---:|---|
| 1 | 20 | 20 | 137 | 45/45 PASS | 完成 |
| 2 | 20 | 19 | 118 | 45/45 PASS | STOP：第 20 个目标同名组核对不一致；已恢复原名、未删除 |
| **合计** | **40** | **39** | **118** | — | **部分完成** |

39 个文件从活动目录移除的清单逻辑长度为 **914,012,742 B**。这是活动目录大小变化，不代表已永久释放云配额：DriveFS 普通删除同步到 Trash；Trash 中的文件在永久删除前仍计入存储。[Google Drive for desktop 同步与 Trash 说明](https://support.google.com/drive/answer/2375102?hl=en)。本轮未调用永久删除 API、未清空 Trash；未直接读取 Trash 逐项清单，因此不声称逐 ID 核实其 Trash 成员身份。

## 首个重命名映射测试

- File ID `1X7G0o9bwnEVzPX1xh5zN7O-q5Ohp7O47`（153,903 B）按 ID 改名为 `…_DELETE_1X7G0o9b.zip`；云端 metadata 显示 ID、父目录、大小保持不变，G: DriveFS 出现唯一同名临时路径，另一同名 File ID 保持原名与大小。精确删除后，目标 ID 从原父目录消失、另一副本仍在，KEEP 45/45 完整。该映射测试通过。
- 本轮另有一次 `update_file` 调用返回超时，但随后按 File ID 读回确认重命名已生效，且 DriveFS 临时路径出现；该文件按核验后的精确路径删除。执行明细中保留了该情况。

## STOP 事件与已恢复状态

第二批第 20 个候选：

- 目标 File ID：`13dW9LBhcCHVGLaCAbi_CpLHXMxPwAtEw`
- 同组兄弟 ID：`1qhX4QoOXoMKLSHMD9ak4IYYpV-mSkAHN`
- 目标被临时改名后，metadata 与 G: 唯一路径都能对应到目标 ID；但同名组核对时，兄弟 ID 的 metadata 仍返回临时名记录，而它已不在活动父目录列表中。该跨接口状态未能在当时的同名组检查中闭合，因此停止后续清理。
- 目标 `13dW…` 已通过同一 File ID 恢复原名；恢复后云端 metadata 与 G: 原名路径、大小一致，目标未删除。兄弟 `1qhX…` 是此前本轮已处理项，现已不在活动父目录；报告不依据仍可读到的 metadata 推断其 Trash 状态。
- 本轮没有继续处理剩余 66 个歧义候选或 7 个 summary 引用项。

## 7 个 summary 引用 ZIP 的检查与影响

只读搜索了当前全局 `scripts`、正式 4×4 的脚本/`try.sh`/`submit.sh`/`USER_CASE.env`，以及 V9_analysis 的 `configure.sh`、`run.sh`、网表、stimulus 和 manifest：未找到这 7 个 Drive File ID 或 ZIP 文件名作为正常运行/提交输入的硬引用。6 个 A001–A006 ZIP 被旧 Drive summary File ID `1rv2zR0g6KBSMUE_aZFbgZRkM2AQ3gE3E` 引用；2×2 A001 snapshot 被 `1OvoDsAxSVXTSSetGnAoS3M25Fo6qXk-V` 引用。历史 summary 原样保留，未改写。

清单的旧分类仍把 A001–A006 标为 `KEEP_ACTIVE` / 当前 4×4 平台关系；这与用户本轮“实验已退役、仅旧 summary 链接可能失效”的明确决定不同。虽然代码和正常运行入口搜索没有发现硬依赖，STOP 条件已在 Part A 触发，因此这 7 个项目本轮**没有删除**。它们的历史链接目前仍有效。

## 保护与交付

- 没有运行 JoSIM；没有修改 V9、4×4 电路、stimulus、raw 或历史 summary。
- 没有操作 D 盘；没有调用永久删除 API；没有清空 Trash。
- 完整逐 ID 操作记录见 [DRIVE_FINAL_CLEANUP_IDS.csv](DRIVE_FINAL_CLEANUP_IDS.csv)。
- 45 个 KEEP 文件及其 ID/大小见 [DRIVE_FINAL_RETAINED_FILES.md](DRIVE_FINAL_RETAINED_FILES.md)。
- 已按用户设定的 STOP 条件终止后续删除；其余 73 项不在本轮继续操作，需另行决定后续处理。本报告只提交本轮已执行事实与未完成范围。
