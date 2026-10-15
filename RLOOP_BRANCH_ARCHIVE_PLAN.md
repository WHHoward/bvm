# R-loop 历史分支与 master 精简方案

状态：只读审计与方案；**没有**创建分支/标签、删除/移动文件、提交或推送，也没有运行 JoSIM。

## 冻结点与范围

- 本地 `master` HEAD：`3848f73bc32685a7d59e62f8b7bdb1a03fd72551`。
- 远端 `bvm/master` 当前指向同一完整 commit SHA；本地工作区在本次审计开始时干净。
- 建议归档分支：`archive/rloop-20261015`。
- 建议不可变 annotated tag：`archive-rloop-20261015`，直接指向上述完整 commit SHA。当前本地/远端均未发现同名分支或标签；本轮没有创建它们。
- 精确审阅范围是 213 个 run 目录：`A000_CANONICAL`、`A001`～`A003`，以及 `U001`～`U209`。目录齐全，没有缺号或额外 run 目录。
- Phase 6 文件清单中的 12,747 个 R-loop 文件本轮重新核对；缺失 0、SHA 相对 Phase 6 漂移 0、符号链接 0。分类结果见三份 CSV。`RUN_SUMMARY` 行用于逐 run 审阅，字节汇总只计算 `FILE` 行。

## 建议分类

### KEEP_MAIN

- `A000_CANONICAL`、`A001`、`A002`、`A003`：Stage-A 的 20 个 passive、五 mask 基线/对照 raw 及相应网表、刺激、manifest、QA。每个 run 5 个 case/raw。
- `U039_closed_cons_12_20_full`：明确保护的 U039 核心 BVM baseline；5 个 case/raw 及 provenance/snapshot。
- 小型平台入口、配置、说明、QA、根级 provenance，以及 `scripts/`、`circuits/`、`config/`。保留这些文件成本很小，也避免切断可重复运行入口。
- `analysis/PACKAGE_CHECKPOINTS.json`、`analysis/PACKAGE_QA.json` 和最新注册 checkpoint `handoff/bvm-rloop-one-shot-tuning-v1-20260918_delta_B029-3bvm-rloop-qb-BJ1-area-sweep.zip`。这是当前 series-local delta submit 工具可用的最小 checkpoint 闭包。
- 所有与 A000～A003、U039 对应且 tracked 的小型图页/导航页。

注意：U039 的 5 个 `run.log` 是 ignored 本地文件，均未在本地 ZIP 联集中命中 SHA，故不会由 archive branch 保存；它们仍在本地并列于 direct-review 清单，后续须单独决定如何冷归档。

当前 4×4 实验平台没有发现对 R-loop 目录内模板或脚本的直接引用；4×4 的 canonical source 在本目录外。**仍有两个旧接口平台依赖本目录**：

- `bvm-qb-50ghz-merge-v1-20260922` 的 preflight 固定校验 `circuits/bvm_tunable.cir`、`circuits/bq_tunable.cir`，其 runner 从本目录加载旧 runner。
- `bvm-qb-repeatability-v1-20260923` 的 preflight/common 直接引用 `scripts/run_candidate.py`、`scripts/fan_in.py`、`circuits/bvm_tunable.cir`、`circuits/bq_tunable.cir`、`circuits/closed_top.cir`。

因此这些脚本/模板在子平台迁移依赖或一起归档之前应留在 master。`memory/LUNA_EXECUTOR_MEMORY.md` 还把该目录作为历史执行参考；归档后应把它的路径指向固定 archive tag，而不是删除历史记录。

### ARCHIVE_ONLY

- U001～U209 中除 U039 外的完整 tracked run 证据；包括失败、控制、独立参数点及重复输入案例，不因较旧或结果失败而丢弃。
- 与这些 runs 对应的 tracked batches、aggregate analysis、旧的 tracked plot pages 及其余 handoff ZIP。
- `U170`、`U171` 都有 `CLOSED_N0_000` case 的 deck/stimulus/log 记录但没有 raw；应以“无 raw 的失败尝试”保留，不得补造 raw 或误标为完整 solve。

CSV 中每个 run 都有独立 `RUN_SUMMARY`，包含目录名、实验阶段、配置快照摘要、case/raw 数、raw SHA、归档闭包状态和风险；每个文件另有精确路径、SHA、Git 状态与字节数。

### DIRECT_DELETE_REVIEW / UNKNOWN

- 3,299 个 ignored HTML 的 SHA 全部唯一；没有字节级重复 HTML。当前 manifest 能映射 3,294 个现存 HTML 并且这些 HTML SHA 与 manifest 一致；205 个 run-level `plot_qa.json` 对 grouped plot set 均报告 PASS，但这不是 page-specific QA。Phase 5 的 per-page audit 仅有 100/3,294 PASS，另有 3,194 个缺 page-QA 或未通过；另有 235 个现存 HTML 没有 manifest 路径（含 plot 目录外页面）。这些页面尚不能作为安全删除候选。CSV 将 run-level/page-level QA 分开记录。
- 516 个 ignored `run.log` 里只有 29 个能在本地 39 个 ZIP 联集中找到同 SHA；其余 487 个仍是本地-only 证据，尤其要保留失败记录。
- 两个 ignored ZIP 为 `..._raw_handoff.zip` 和 `..._raw_handoff_v2.zip`。它们不是 Git/LFS 文件。D 盘同名文件 SHA 与本地文件匹配，Drive 文件 ID 存在且名称/大小匹配，但 Drive 未提供云端内容 SHA；在 member/云端字节未完成独立核验前归 `UNKNOWN`。
- 20 个 `.pyc` 是唯一低风险的可再生成删除审阅项，合计 489,814 B logical / 524,288 B allocated；本轮没有删除。
- 514 个 raw 有 491 个唯一 SHA；16 组、23 个额外路径与其他 run raw SHA 完全相同。6 组的有效 deck/stimulus/source snapshot/solver 参数签名一致，但对应 run logs 不同，可能是独立重复求解；其余组的有效输入签名不同。raw 相同不等于 run 可互换。所有 39 条关联只作为 `RAW_DUPLICATE_CROSS_REFERENCE` 列入 direct-review CSV，不选“保留副本”、不建议删除任何 raw。理论去掉每组多余 raw 的上限约 154,979,724 B logical / 155,029,504 B allocated，**当前安全回收量为 0**。

## 备份闭包核验

### Git / LFS

- 远端分支与本地 HEAD 相同；`git ls-tree` 在当前 commit 中找到该目录 8,909 个 tracked 路径。因此拟归档分支在创建时指向该 commit，可保持完整 tracked tree，而非仅保存 LFS 指针文本。
- 37 个 tracked handoff ZIP 的本地文件 SHA 与 Git LFS OID 全部匹配；对 37 个 OID 的远端 LFS batch `download` 元数据请求均返回可下载对象动作。未下载 LFS payload；这证明远端对象按 OID 可获取，但未在独立机器重新哈希字节。
- 另外 2 个 ignored ZIP 不在该 Git tree，也不属于 37 个 LFS OID，归档分支不会保存它们。

### 本地 ZIP 成员

只读检查了本地 39 个 handoff ZIP：11,836 个成员、5,513,672,765 B 解压内容，CRC 错误 0。按 ZIP 成员路径解压流并对 SHA 与现行文件逐项比对：

- raw：514/514 精确 SHA member match；
- `actual_deck.cir`：721/721；`stimulus.inc`：721/721；
- `source_manifest.json`：213/213；`snapshot/sources/*`：845/845；
- tracked 非 ZIP 文件中 8,870/8,872 精确匹配 ZIP 联集；两个未匹配项是 `analysis/PACKAGE_CHECKPOINTS.json` 和 `analysis/PACKAGE_QA.json`，它们在当前 remote Git tree 中，归档分支仍能恢复；
- 516 个 ignored run logs 中仅 29 个有精确 ZIP member，487 个没有；
- 516 个 case 目录中 514 个有 raw，另两个正是 U170/U171 的失败 case。

所有 39 个本地 D 盘 ZIP mirror 的当前 SHA 均与仓库 handoff ZIP 一致。此项只验证本地 D 副本，不推导 Drive 内容 SHA。

### Google Drive

39 个 ZIP 的 Drive file ID 均能读取到元数据，名称和大小 39/39 与本地索引一致，总 metadata size 为 833,587,149 B。Drive metadata 未暴露 SHA-256，且本轮没有下载 ZIP；所以“Drive 文件对象存在”已确认，“云端字节与本地逐字节一致”仍为 UNKNOWN。

**完整实验恢复测试尚未执行**：归档分支还不存在，本轮不建分支/下载或展开 ZIP。应在授权后用独立临时 clone 检查 pinned commit、8,909 个 tracked 路径、SHA manifest、全部 raw/deck/stimulus/source manifests/snapshots；再验证 37 个 LFS OID 的实际下载内容。操作步骤见下文。

## 建议操作顺序（均等待后续明确授权）

1. 在同一个 `3848f73bc32685a7d59e62f8b7bdb1a03fd72551` commit 上创建 `archive/rloop-20261015`，并创建不可变 tag `archive-rloop-20261015`；推送后检查远端 refs 指向的仍是该完整 SHA。
2. 在独立临时目录从远端 archive branch/tag clone/checkout。验证每个 tracked 文件 SHA、514 个 raw、deck/stimulus/source manifest/snapshot closure、LFS OID 及关键 run ID；不运行 JoSIM。失败/缺失时不得从 master 移除对应路径。
3. 对 487 个未被 ZIP 联集覆盖的 ignored `run.log`、两个 ignored ZIP、以及未通过 plot QA 的 HTML 作单独保留决定。archive branch 不包含 ignored 文件。
4. 用户审阅 `RLOOP_ARCHIVE_ONLY.csv` 后，才生成 master 精确路径移除 commit；不改写历史、不 force-push、不执行 Git GC 或 LFS prune。归档 branch/tag 保持可恢复。
5. 提交后在新轻量工作副本验证 4×4 当前工具。优先试 `--single-branch --branch master --filter=blob:none` 的新 clone；验证 GitHub 实际支持的 partial clone 行为及 LFS lazy/smudge 设置。若只用既有本地 clone 的新 worktree，`.git` 和 LFS 对象仍共享、不会释放；若新 clone，在旧工作区未由用户另行处置前，总磁盘占用反而会暂时增加。

## 当前停止状态

无物理求解、无文件移动/删除、无 branch/tag 创建、无 commit/push、无 Drive 写入。五份方案文件留在本地待审阅；所有历史 run 和 raw 仍原位。
