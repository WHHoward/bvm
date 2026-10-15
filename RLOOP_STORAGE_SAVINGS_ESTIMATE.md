# R-loop master 精简与空间收益估算

本报告是 `archive/rloop-20261015` 方案的只读空间估算，不授权删除、移动、建分支、推送、Git GC 或 LFS prune。字节统计基于当前 HEAD `3848f73bc32685a7d59e62f8b7bdb1a03fd72551` 及 12,747 个文件逐项 SHA/大小复核。

## 结论先行

- 本批实际释放空间：**0 B**。没有删除或移动任何文件。
- 若之后建立 archive branch，并仅在 master 的后续 commit 中移除 `RLOOP_ARCHIVE_ONLY.csv` 的 8,598 个 tracked 文件，现有工作树预计可释放 **4,761,657,344 B allocated**（4.762 GB / 4.435 GiB），逻辑文件大小 **4,739,759,559 B**（4.740 GB / 4.414 GiB）。这是文件分配块上限估算，不是本轮实测释放值。
- 原始数据和 `.git`/LFS 历史仍由 archive branch/tag 可达；所以该工作树收益**不是 Git 历史或 GitHub LFS 存储回收**。在不重写历史、不 prune 的边界内，GitHub 仓库对象空间收益按 **0 B** 估算。
- `RLOOP_DIRECT_DELETE_REVIEW.csv` 中 3,838 个 ignored 项共 **2,009,305,088 B allocated**（2.009 GB / 1.872 GiB），但绝大部分不满足安全删除条件。唯一低风险可再生成类是 20 个 `.pyc`，潜在 524,288 B allocated（0.5 MiB），本轮仍未删除。
- Direct-review CSV 另有 39 行 `RAW_DUPLICATE_CROSS_REFERENCE`；它们引用已在 KEEP_MAIN/ARCHIVE_ONLY 文件分区中的 raw 路径，不是新增文件，也不计入 direct-review 空间合计。

## 当前 R-loop 文件树分配

| 拟议层级 | 文件数 | Logical bytes | Allocated bytes | 解释 |
|---|---:|---:|---:|---|
| KEEP_MAIN | 311 | 180,229,165 | 180,973,568 | A000–A003、U039、平台/必要脚本模型、最小 checkpoint 闭包 |
| ARCHIVE_ONLY | 8,598 | 4,739,759,559 | 4,761,657,344 | tracked 历史 runs、批次/分析/旧包及非代表性 tracked pages |
| ignored / direct-review local files | 3,838 | 2,000,839,205 | 2,009,305,088 | 3,299 HTML、516 run.log、20 PYC、1 JS、2 ZIP；不在 master Git tree |
| 合计文件 | 12,747 | 6,920,827,929 | 6,951,936,000 | allocated 为文件 `st_blocks` 合计，不含目录自身块 |

`du -s` 的目录树 allocated snapshot 为 6,961,168,384 B；比文件块合计多 9,232,384 B，主要是目录元数据/块。文件级 CSV 不重复计算目录父子大小。

## ignored local-only 内容细分

| 类型 | 文件数 | Logical bytes | Allocated bytes | 建议 |
|---|---:|---:|---:|---|
| HTML | 3,299 | 1,931,026,524 | 1,937,604,608 | UNKNOWN/保留；SHA 全唯一，绘图 QA 与审阅替代关系尚未闭合 |
| Plotly JS | 1 | 4,763,993 | 4,767,744 | 保留；本地 HTML 相对资源依赖 |
| run.log | 516 | 268,213 | 2,113,536 | 保留；只有 29 个在 ZIP 联集中 SHA 命中，487 个缺归档匹配 |
| PYC | 20 | 489,814 | 524,288 | 可再生成的直接删除审阅候选；最多约 0.5 MiB，不是重要空间来源 |
| ZIP | 2 | 64,290,661 | 64,294,912 | UNKNOWN；ignored，不在 Git/LFS；Drive 仅元数据同名同大小，内容 SHA 未知 |

3,529 个 HTML SHA 均互不相同；3,294 个现存页有 manifest 映射且当前 HTML SHA 与 manifest 匹配。205 个 run-level `plot_qa.json` 均报告 grouped plot set PASS；这不是逐页面复现/审阅 QA。Phase 5 的 page-level QA 只有 100/3,294 PASS，3,194 个缺 page-QA 或 QA 未通过；另有 235 个现存 HTML 没有当前 manifest 路径。故 1,937,604,608 B 虽是大块 local-only 空间，当前没有可证明安全的批量清理白名单。

16 组 raw hash 重复共涉及 39 个路径（23 个超出每组一份的额外路径）。按每组留一份计算的理论上限为 154,979,724 B logical / 155,029,504 B allocated。六组的 deck/stimulus/source snapshot/solver 参数签名相同但日志不同，可能是独立重复求解；其余组的有效输入签名不同。路径级 raw、run metadata 和日志仍有研究/重复性价值，**不计入安全回收值**。

## 存储层分开核算

| 存储层 | 当前审计值 | 本次或拟议 master 文件树变化 |
|---|---:|---|
| R-loop 当前文件树 | 6,920,827,929 B logical；文件 allocated 6,951,936,000 B | 实际变化 0 B；未来 master checkout 可能释放 ARCHIVE_ONLY 的 4,761,657,344 B 文件块 |
| `.git` 全体 | 18,737,349,107 B logical | 不变；分支保留原 commit，master 新删文件仍在祖先历史中 |
| `.git/lfs` | 3,918,524,121 B logical | 不变；本轮不 fetch payload、不 prune。37 个 R-loop ZIP OID 远端均返回可下载动作 |
| Git loose/packed objects | `git count-objects`: loose 2.32 GiB、pack 11.43 GiB；报告 21.34 MiB garbage | 不变；未执行 GC。该 garbage 不属于本次目标，不触碰 |
| D 盘本地 ZIP mirror（R-loop 39 包） | 833,587,149 B；39/39 SHA 与仓库副本匹配 | 不变；不移动或清理 |
| Google Drive（R-loop 39 ZIP metadata） | 39 个 ID，元数据 size 合计 833,587,149 B；名称/大小 39/39 匹配 | 不变；Drive 未暴露内容 SHA，因此云端逐字节一致性 UNKNOWN |

`.git/lfs` 是 `.git` 的子目录，不应把两项相加为额外仓库空间。D 盘与 Drive 也分别记账，不与工作树收益相加。37 个 tracked ZIP 共 769,296,488 B，两个 ignored ZIP 共 64,290,661 B；归档 branch 保持 tracked ZIP 的 LFS OID 可达，但不会把 ignored ZIP 自动纳入 branch。

## 未来轻量工作副本的收益边界

- 在当前 checkout 拉取 master 删除 commit，tracked archive-only 文件块预计释放约 4.762 GB；ignored HTML/log/JS/ZIP 不会因 Git checkout 自动清理，仍留在旧工作树。
- 一个新的干净 master checkout 不会包含这 3,838 个 ignored 文件；其 R-loop 部分约由 KEEP_MAIN 的 180,973,568 B tracked 内容构成。但新 clone 在旧目录尚未由用户处置前会增加一份工作树，不能把“新 clone 更轻”报告为当场磁盘释放。
- 普通 clone 会保留 master 可达历史；master 文件树变小并不等于 `.git` 变小。`--filter=blob:none` 的 partial clone 和 LFS lazy fetch 需要在授权后以独立临时 clone 验证。不得用浅克隆或历史重写来伪装回收。
- 冷归档分支/标签存在时，GitHub Git/LFS 对象继续保留；没有 filter-repo、force-push、GC/LFS prune 的情况下，不建议预期 GitHub 存储收费或对象容量下降。

## 另需人工决定的收益

| 审阅项 | 理论大小 | 当前安全值 | 主要缺口 |
|---|---:|---:|---|
| PYC 缓存 | 524,288 B allocated | 0 B（本轮未删除） | 需用户单独批准；收益仅 0.5 MiB |
| ignored HTML | 1,937,604,608 B allocated | 0 B | per-page replacement/review-link closure；大面积 QA 缺失/失败 |
| ignored logs | 2,113,536 B allocated | 0 B | 487/516 未在 ZIP 联集找到同 SHA |
| 两个 ignored ZIP | 64,294,912 B allocated | 0 B | Drive 内容 SHA 未知，且不在 Git/LFS |
| raw SHA 重复 | 155,029,504 B allocated 的组内额外副本理论上限 | 0 B | 相同 raw 并不能证明相同实验；每个 run 路径/日志均保留 |

本文件只做分层空间估算；具体删/移名单由用户和 ChatGPT 审阅后另行授权。
