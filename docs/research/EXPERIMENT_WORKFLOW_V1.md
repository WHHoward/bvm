# JoSIM 实验工作流 V1

## 1. 目的与适用范围

本文是项目未来新建 JoSIM/BVM 实验的规范性流程与目录结构。它冻结的是
实验执行、证据保存、可视化和人工审阅的工作顺序，不改变任何已经完成的
历史实验、raw、报告、指标定义或科学结论。

本文不替代以下更高层或专门的约束：

- docs/HANDOVER.md 与 memory/project-todo.md；
- research/WORKFLOW.md 以及冻结的 josim-handoff/v1；
- 已接受的 metric、source、实验合同和独立审计；
- 现有历史实验目录中的原始协议。

旧实验不因本规范发布而批量迁移。若旧实验需要补图或补分析，应在原实验
语义和原始证据不变的前提下，建立明确的 task-local 修订记录。

## 2. 默认生命周期

所有未来的新实验默认按下列顺序推进：

    QUESTION
      → PREREGISTER
      → GENERATE / FREEZE DECKS
      → STATIC PREFLIGHT
      → PREREGISTRATION COMMIT
      → CLEAN WORKTREE
      → PHYSICAL RUN
      → RAW / POST-RUN QA
      → STANDALONE VISUALIZATION
      → STANDALONE VISUAL QA
      → COMPARISON VISUALIZATION
      → ANALYSIS
      → ADVERSARIAL / NUMERICAL REVIEW
      → REPORT
      → HUMAN REVIEW GATE
      → STOP / NEXT AUTHORIZATION

顺序有三条硬约束：

1. 只有冻结并已登记的 executed deck 才能进入物理运行；
2. 每个 condition 先有独立的 standalone visualization 和 QA，之后才做
   comparison visualization；
3. 到达 HUMAN REVIEW GATE 后必须停止。代理不得因为结果“看起来符合预期”
   自动扩展参数、改变路线或启动下一项实验。

普通 Exploration 可以使用本流程的完整证据结构，但结果仍然只能保持在
相应证据等级；本流程本身不会把 Exploration 自动提升为 Candidate、Formal
或 Authority。

## 3. experiment.yaml：运行前的最小合同

每个新实验必须在运行前写入 experiment.yaml，至少包含：

- experiment_id：稳定、唯一的实验标识；
- question：一个可判定的主要科学问题；
- source_class：canonical、historical、exploratory 或其它明确来源类别；
- authority_boundary：哪些文件/结果可以作为证据，哪些不能外推；
- run_set：完整 condition 列表和每个 condition 的唯一名称；
- changed / frozen：本轮改变项和明确保持不变的项；
- topology、器件参数、模型、刺激语义、极性和负载；
- 时间步长、停止时间、保存起点和时间窗口；
- 精确 probes、单位、方向和预期的 raw QA；
- standalone/comparison visualization 的 visual authority；
- interpretation_ceiling：本轮最多允许支持到什么结论；
- prohibited_followups：人工审阅前禁止的后续动作；
- human gate 的初始状态。

推荐的最小写法如下，具体物理语义必须按实验填写，不能照抄占位值：

    experiment_id: <stable-id>
    question: <one primary question>
    source_class: historical | canonical | exploratory
    authority_boundary:
      evidence: [raw, analysis]
      not_proven: [<explicit limits>]
    run_set:
      - condition: <condition-name>
        state: <state>
    changed: [<one or more preregistered changes>]
    frozen: [<topology, source, load, solver, timing, ...>]
    windows: []
    probes: []
    expected_qa: []
    interpretation_ceiling: <bounded statement>
    prohibited_followups: [<actions requiring new authorization>]
    visual_authority:
      renderer: scripts/josim-plot2.py
      layout: sep_comb
      color: dark
      phase: 2pi
    human_gate:
      state: AWAITING_USER_REVIEW
      user_reviewed: false
      next_step_authorized: false
      automatic_next_experiment: false
      next_action: STOP

## 4. 默认目录结构

新的实验默认使用下列结构：

    test/exploration/<experiment>/
    ├── experiment.yaml
    ├── generate_decks.py
    ├── run.sh
    ├── runs/
    │   └── <condition>/
    │       ├── deck.cir
    │       ├── raw.csv
    │       ├── run.log
    │       └── metadata.json
    ├── analysis/
    │   ├── analyze.py
    │   ├── metrics.json
    │   ├── REPORT.md
    │   └── human-gate.yaml
    ├── plots/
    │   ├── runs/
    │   └── comparison/
    └── provenance.json

目录名和 condition 名必须能从 experiment.yaml 反查。优先把哈希、命令、
solver、时间步长、artifact 状态和来源写进 metadata.json 与
provenance.json，不再为每个普通 Quick 机械地堆叠
command.txt、hashes.sha256、raw-sha256sums 和大量重复 QA 碎片。
若某个正式合同另有要求，以该合同为准。

### 4.1 Executed deck 的唯一权威

solver 实际执行的网表必须是：

    runs/<condition>/deck.cir

未来 run.sh 直接执行这个冻结 deck。不得先把
inputs/<condition>.cir 复制到别处再执行，也不得让 run.sh 在执行前
静默修改、补写或重排 runs/<condition>/deck.cir。若需要重新生成 deck，
必须建立新 attempt 或新实验，并重新完成预注册和提交。

## 5. 两阶段 preflight

### 5.1 Static preflight（运行前）

static preflight 必须在 physical run 前检查：

- 工作树是否满足本轮要求；
- Git HEAD、source identity、模型和 solver identity；
- 所有 condition 的 runs/<condition>/deck.cir 是否已存在；
- include、模型、节点、probe、单位、极性、时间步长和停止时间；
- experiment.yaml 与 deck 的 changed/frozen 内容是否一致；
- 输出 raw/log 是否已存在，是否会造成覆盖；
- 预注册的 QA、窗口和解释上限是否可机械执行。

static preflight 失败时不得运行物理仿真。失败应先修复合同或建立新
attempt，不能把失败状态掩盖成“运行成功”。

### 5.2 Post-run preflight（运行后）

每个 run 完成后，必须独立检查：

- solver exit code；
- raw 是否存在、非空、可解析；
- 时间列单调、单位和网格是否符合预注册；
- header/probe 是否完整、没有未声明的重复列；
- deck/raw/log/metadata 的 hash 链是否一致；
- 仿真过程中是否出现未声明的 solver/model warning；
- standalone plot 所需信号是否全部存在。

post-run preflight 失败的 artifact 必须标记为 ARTIFACT_INVALID，保留
原始文件，并禁止进行物理解释。修复分析或工具后，只能对不可变 raw
重新 QA；不能因为分析程序此前退出 1 就重跑物理仿真。

## 6. run.sh 最小要求

新的 run.sh 至少应具备：

    set -euo pipefail

并按顺序执行 solver 检查、clean-worktree 检查、冻结 deck 检查和
static preflight。它必须：

- 使用项目记录的 build/josim-cli，记录版本和 binary hash；
- 拒绝覆盖已存在的 raw、log 或 metadata；
- 记录实际 command、exit code 和运行时间；
- 不生成新的 deck，不修改冻结 deck；
- 在没有明确授权时不扩大 run set。

run.sh 可以调用共享脚本，但科学判断和实验语义必须在
experiment.yaml/task-local analysis 中可读地保留。

## 7. 每个 run 的 metadata.json

每个 condition 至少记录以下字段：

    schema: <schema-version>
    condition: <condition-name>
    state: <state>
    source_class: <source-class>
    git_commit_before_run: <commit>
    created_at: <local timestamp with timezone>
    solver:
      path: <path>
      version: <version>
      sha256: <hash>
    command:
      argv: []
      exit_code: 0
    paths:
      deck: runs/<condition>/deck.cir
      raw: runs/<condition>/raw.csv
      log: runs/<condition>/run.log
    hashes:
      deck_sha256: <hash>
      raw_sha256: <hash>
      log_sha256: <hash>
    numerics:
      timestep: <value>
      stop_time: <value>
    model_warning: []
    artifact_status: VALID | ARTIFACT_INVALID

时间戳必须是真实创建时间，不得使用未来时间或事后伪造运行时间。

## 8. 共享测量逻辑与 task-local 结论

稳定、可复用的 raw 读取、时间网格、相位转换、波形比较、KCL 和严格事件
测量逻辑应优先下沉到 scripts/bvmtools/。实验特有的窗口、对照语义、
判定标签、解释上限和结论仍保留在 task-local 的 analysis/ 与报告中。

必须保持下列测量不变量：

- JoSIM 的 P(...) raw 值是弧度；
- 只有在数值上明确计算 phase_rad / (2*pi) 后，才能标成 phase turns；
- phase displacement、voltage-area、局部 activity 或 local JJ event
  都不能自动写成 SFQ count 或 downstream transport；
- comparison 只在同一 signal、同一方向、同一窗口和 exact time grid
  上进行；不允许为了画图静默插值；
- PASS、FAIL、INCONCLUSIVE 与 ARTIFACT_INVALID 必须保持区分。

## 9. 可视化规范

新实验采用 standalone-first：

1. 为每个 condition 生成独立的关键数据图；
2. 完成独立 visual QA；
3. 只有在 standalone 图可读且信号定义一致后，再生成 comparison 图；
4. comparison 图的 A/B 顺序、信号顺序、单位、命名和时间网格必须在
   manifest 中记录。

若项目已有 visual authority，新的图必须继承其 renderer、layout、theme、
signal order、phase unit 和 naming。BVM 默认 visual authority 为：

    renderer: scripts/josim-plot2.py
    layout: sep_comb
    color: dark
    phase: -j 2pi

也就是 P(...) 仍保留 raw radians，图中只有经过 rad/(2*pi) 数值转换
后的轴或标签才能写 turns；turns 不是 SFQ 数量。图只展示支持当前问题的
关键数据，不以全信号堆叠替代证据选择。

## 10. 历史 incident 规则

如果 solver exit 为 0，但由于 preflight 或 analyzer bug 导致分析退出 1：

1. 保留原 raw、deck、log 和当时 metadata；
2. 不重跑 physics；
3. 修复工具或分析代码；
4. 对同一个不可变 raw 重新执行 post-run QA；
5. 在报告中记录 incident、修复前后命令和新的 QA 结果。

工具修复不等于物理结果被重新验证；物理解释仍须以新的 QA 和审阅结果为
依据。

## 11. 人工理解门

实验完成后的默认状态是：

    state: AWAITING_USER_REVIEW
    user_reviewed: false
    next_step_authorized: false
    automatic_next_experiment: false
    next_action: STOP

只有用户明确审阅并授权，才能改变下一步。代理不能自行把
AWAITING_USER_REVIEW 写成 REVIEWED，不能把一个 Quick 结果升级成
Formal/Authority，也不能自动执行报告中列出的后续选项。

## 12. 提交纪律与非目标

预注册和流程改动应先形成独立、可审阅的 commit；在 clean worktree 上才
开始物理 run。实验完成后，代码、analysis、manifest 和报告的修改按主题
使用聚焦 commit；raw/deck/log 不得被 cosmetic 重写。

本规范不要求回头重构历史实验，也不授权任何具体的 canonical BVM 替换、
QB/JTL/T1 实验、参数优化、sweep、timestep convergence 或论文级结论。
这些都必须由新的明确授权、对应的预注册和人工审阅来决定。

当前规范状态：ACTIVE / V1。
