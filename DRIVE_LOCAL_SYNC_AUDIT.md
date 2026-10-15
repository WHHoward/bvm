# BVM_Backages 本地 DriveFS 同步审计

## 结论

已确认 `/mnt/d/BVM_Backages` **不是** Google Drive for desktop 的同步目录，而是仓库提交工具的本地包镜像目标。可访问的 Google Drive for desktop 虚拟盘是 Windows `G:`；从 WSL 经 `powershell.exe` 可访问其路径，但 WSL 未挂载 `/mnt/g`，`wslpath` 不能将 G: 映射成 WSL 路径。

目标 Drive 文件夹 `BVM_Backages`（ID `1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh`）在 DriveFS 中的路径为：

```text
G:\.shortcut-targets-by-id\1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh\BVM_Backages
```

该路径包含 Folder ID 的快捷方式目录；Drive 元数据确认相同 ID 的名称为 `BVM_Backages`。DriveFS 本地枚举与云端文件清单匹配：清理前递归 **382 个文件、11,671,479,003 B**；根目录 377 个文件和 3 个子文件夹。DriveFS 进程正在运行，程序版本路径为 `C:\Program Files\Google\Drive File Stream\132.0.0.0\GoogleDriveFS.exe`；Windows `G:` 标签为 `Google Drive`。

## D 盘镜像与 rclone

- Windows `D:` 标签为 `Data`，由 WSL `/mnt/d` 以 DrvFs 访问。
- `scripts/submit.py` 将 `MIRROR_DEFAULT` 指向 `/mnt/d/BVM_Backages`，通过 `shutil.copy2` 复制已生成的 package 并校验 SHA；这是包镜像/备份流程，不是 G: DriveFS 的双向同步目录。
- 本次没有对 D: 执行写入或删除。试验 ZIP 在候选表列出的 D 盘路径当前不存在；不据此推断其历史同步状态。
- 未安装 `rclone`，没有可用 rclone remote；未读取任何认证配置或令牌。

## 同步删除语义与限制

Google 官方说明：Drive for desktop 使用 Mirror 或 Stream 时，将文件放入 Trash 的操作会同步到 Drive 和计算机。[Delete files in Drive for desktop](https://support.google.com/drive/answer/2375102?hl=en)

本次通过 PowerShell 对 G: DriveFS 中一份明确映射的 43,299 B ZIP 执行了单文件删除测试。文件从本地 DriveFS 路径消失，Drive 原父目录列表也不再包含该 File ID；但当前 Drive 连接器不能列出 Trash，`files.get` 对该 ID 返回 404，Trash 查询没有返回该文件。因此，官方文档说明了预期同步语义，但**不能据本轮连接器读回确认该特定 File ID 实际位于 Google Drive Trash**。批量删除必须暂停，等待用户网页端核验。

## 清单核验概况

- 当前云端完整列表：337 个删除候选 ID 均在删除前存在，且 ID、父文件夹、名称、大小、修改时间与审计清单相符。
- 本地路径映射：230 个精确名称/父目录匹配；另 2 个因 DriveFS `(1)` 后缀，经候选已有云 SHA-256 与本地 SHA-256 相符后确定映射；105 个在同一父目录存在重复名称，无法仅凭本地路径绑定到唯一 File ID，标记歧义。
- 清单中 7 个候选被 Drive summary 明确引用，标记引用风险并跳过后续删除。
- 43 个保留 ZIP ID 与两份 Markdown 在试验后仍全部出现在云端列表；没有观察到保留集缺失。
- 试验后同步树有 381 个文件、11,671,435,704 B（379 ZIP + 2 Markdown）；比试验前少一份 43,299 B 文件。

详细的 337 行 ID→路径映射见 [DRIVE_LOCAL_DELETE_MAPPING.csv](DRIVE_LOCAL_DELETE_MAPPING.csv)。
