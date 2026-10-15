# BVM_Backages 本地同步目录单文件试删结果

## 状态：已执行单文件测试；Trash 状态未验证；批量清理已停止

| 字段 | 结果 |
|---|---|
| Drive File ID | `1TcEQR5jVy1JJTYAq9CYxkxlNSNWVSix` |
| 名称 | `bvm-4x4-diagonal-array-v1-20261009_metadata_BVM4X4_20261009.zip` |
| 原父目录 | `BVM_Backages/superseded-metadata-v1-bvm-4x4-20261009` |
| 大小 | 43,299 B |
| 清单云端 SHA-256 | 未记录；该候选标为 `NOT_HASHED_SINGLETON` |
| 删除前 G: DriveFS 本地 SHA-256 | `B707ABBBA18F9381ED60BE0425EA5373630AD609CC48D1C46C8E38551891D30D` |
| 本地同步操作 | 对确切 G: DriveFS 路径使用普通 PowerShell `Remove-Item -LiteralPath`，未使用永久删除 API、`-Force` 或 D 盘路径 |
| 本地结果 | 文件路径已不存在 |
| Drive 原目录结果 | superseded-metadata 子文件夹当前 0 个文件；候选 File ID 不在原父目录列表 |
| Drive Trash 结果 | **未验证**。`get_file_metadata` 返回 404；可用 Search/Folder 工具未能列出 Trash 项目 |

官方说明 Drive for desktop 的 Stream/Mirror 删除会同步至 Trash，但本次没有可用接口确认这一具体 File ID 已进入 Trash。故结果是 `INCONCLUSIVE_TRASH_MEMBERSHIP`，不将其报告为已验证成功，也不继续处理其余候选。请在 Drive 网页版 Trash 中确认该文件；确认前不启动批量删除。

## 试验后留存集与剩余量

- 43 个保留 ZIP File ID：全部仍在原目录/子目录清单中。
- 两份 Markdown：全部仍在原目录清单中。
- 当前云端：**379 ZIP + 2 Markdown = 381 文件**，总大小 `11,671,435,704 B`。
- 剩余 336 个删除候选仍在原目录；本轮没有对它们执行删除。
- `DRIVE_LOCAL_DELETE_MAPPING.csv` 中 105 个同父目录重名项标记 `AMBIGUOUS`；7 个被 Drive summary 明确引用的候选标记 `SKIPPED_REFERENCE_RISK`。
- D 盘镜像没有被本次命令写入或删除；GitHub 实验文件没有提交或推送；未运行 JoSIM。

## 工作区状态

本次仅新增本地审计报告/映射文件；没有暂存或提交。执行前已存在的 `V9_analysis/raw.csv` 与 `V9_analysis/stimulus.inc` 用户修改保持未暂存、未改写。
