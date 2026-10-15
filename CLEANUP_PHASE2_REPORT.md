# BVM 存储清理第二阶段报告

审计日期：2026-10-14
仓库：WHHoward/bvm；工作区：/home/howard/JoSIM
HEAD：fc41c5d584754950f55915d7f26f24c935882e9f（master 与 bvm/master 对齐；审计前工作区干净）

## 结论摘要

- 本批实际释放空间：**0 B**。未删除、移动或改写项目证据；未启动 JoSIM。
- 精确 HTML 白名单为 **161 个 ignored 页面、3,350,950,641 B（约 3.12 GiB）**。逐页路径、raw SHA、HTML SHA、manifest 与恢复依据列在 CLEANUP_PHASE2_ACTIONS.csv；清理仍须后续明确批准。
- 2×2 run-local 的155页单独占2,982,148,703 B，逐页 plot QA、HTML SHA、raw SHA、plotter 和共享 Plotly asset 均匹配；四种页面类型的代表样本重建通过，33个证据 ZIP 均不含HTML。
- 2×2 的676个tracked非HTML run文件（1,659,742,802 B）是 sparse-checkout 候选；8个被忽略的 T1 run.log 未包含在 D 包成员哈希中，必须留在本地。whole runs/ 不是已闭合的冷归档。
- 当前活动4×4基线必须保留。QB/CB topology 和 R-loop 包链还不能证明完整远端可恢复性，不建议整目录移出。
- Drive 同名同大小 ZIP 仍未逐个云端 SHA 验证。D盘本地 SHA 相同不代表云端字节相同。

## 空间现状（各层不重复相加）

| 范围 | 实测大小 | 说明 |
|---|---:|---|
| 工作区 | 114,537,472,000 B | 包含 .git 与 test/exploration |
| .git | 18,699,214,848 B | 已含在工作区；7 packs=11.43 GiB，loose=2.28 GiB，260 个 LFS files |
| test/exploration | 94,438,936,576 B | 已含在工作区 |
| D:/BVM_Backages | 11,672,293,376 B | 独立本地归档镜像 |
| Google Drive BVM_Backages | 11,671,479,003 B | Drive 文件夹级元数据，不代表账号总配额 |
| /dev/sdd | 1,007 GiB 总量，271 GiB 已用，686 GiB 可用 | 系统级空间，不与目录数字相加 |

当前 tracked paths 数为32,500；审计前工作树干净。HTML总量19,165个/58,111,665,106 B，其中tracked 3,218个/18,119,470,240 B、ignored 15,947个/39,992,194,866 B。稀疏检出只减少工作树，不减少Git历史。本批未运行 git clean、gc、LFS prune、filter-repo 或 force-push。

重点目录 allocated usage：4×4 43,298,820,096 B；QB/CB topology 9,570,643,968 B；R-loop 6,962,212,864 B；2×2 5,015,158,784 B。D盘和Drive分别列示，不与工作区相加。

## HTML 可重建性审查

共检查10个代表样本：4×4五页、R-loop一页、2×2四页。使用现有 scripts/josim-plot2.py 和平台既有 render_plots，仅针对 immutable raw 临时生成；比较 ordered trace 的Plotly data/layout/config。raw 与原HTML保持不变，临时输出已清理。

| 样本 | 原HTML大小 | traces / stored rows | 复现 |
|---|---:|---:|---|
| A108 4×4 02_carry | 92,778,464 B | 132 / 29,999 | PASS，figure data/layout相同 |
| A085 4×4 02_carry | 92,770,918 B | 132 / 29,999 | PASS |
| A089 4×4 02_carry | 92,748,482 B | 132 / 29,999 | PASS |
| A107 4×4 D3 focus | 43,186,643 B | 62 / 29,999 | PASS |
| A084 4×4 T1 focus | 46,275,483 B | 66 / 29,999 | PASS |
| U131 R-loop JTL1–3 | 1,041,948 B | 21 / manifest raw grid | PASS，figure payload/config相同 |
| A018 2×2 QB | 61,530,167 B | 104 / 24,999 | PASS |
| A017 2×2 column2 | 48,068,189 B | 82 / 24,999 | PASS |
| A020 2×2 frontend C1 | 46,620,340 B | 79 / 24,999 | PASS |
| A013 2×2 BVM | 30,129,242 B | 52 / 24,999 | PASS |

2×2 的155个run-local HTML逐页校验：plot QA为PASS，实际HTML SHA等于plot_qa，raw SHA与原CSV一致，renderer/asset hash一致；4个代表页重新渲染payload与现有页面一致。共用 Plotly asset SHA-256 为122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770。33个run/source ZIP均没有HTML成员。

R-loop U131原图使用相对路径 ../../assets/plotly.min.js，该资产存在且SHA匹配。直接CLI临时产物默认内嵌JS，体积大于旧文件，但图形data/layout/config一致，原页面字节未覆写。

### 精确 HTML 白名单与未验证项

- 2×2 runs下155页 / 2,982,148,703 B：全部加入CSV逐页白名单。
- 4×4 plots下共976页 / 30,505,175,926 B；只把5个样本页加入白名单，其余971页 / 30,137,415,936 B本批没有逐页重建，保持UNKNOWN。
- R-loop plots共3,530页 / 1,982,621,847 B；仅U131一页加入白名单，其余3,529页 / 1,981,579,899 B保持UNKNOWN。
- 2×2顶层 plots/comparison 五个比较图合计46,820,670 B，paired raw/manifest重建未核实，保持UNKNOWN。
- 白名单共161页 / **3,350,950,641 B**。具体路径均在CSV；V0–V9人类审阅证据不在其中，仍全数保留。

## 历史实验与备份闭包

| 目录 | 实测占用 | 本轮证据检查 | 建议 |
|---|---:|---|---|
| bvm-4x4-diagonal-array-v1-20261009 | 43,298,820,096 B | 108 raw/9,494,469,207 B；138 handoff ZIP/2,669,482,925 B；所有ZIP CRC通过，138 bundle manifests、130 delta manifests | KEEP：当前4×4基线及256-case平台 |
| bvm-qb-cb-array-topology-v1-20260924 | 9,570,643,968 B | 41 run dirs、38 raw/2,136,166,901 B；10 ZIP/2,620,146,596 B；本地包路径覆盖38/38 raw及核心deck/stimulus/source/provenance；9个delta manifests，1个full ZIP无标准bundle/delta manifest，无完整D/Drive SHA闭包 | UNKNOWN/KEEP：保留独立拓扑/失败对照 |
| bvm-rloop-one-shot-tuning-v1-20260918 | 6,962,212,864 B | 213 run dirs、514 raw/3,216,902,301 B；39 ZIP/833,587,149 B；raw路径在本地包union中514/514，ZIP CRC通过；7个旧full ZIP无标准manifest，run-log/package闭包不完整 | UNKNOWN/KEEP：保留参数对照、controls和失败历史 |
| bvm-2x2-rowcol-selection-v1-20260928/runs | 4,644,429,824 B | 26 raw/1,585,018,584 B；33 ZIP/311,600,048 B；33/33 PACKAGE_QA PASS、ZIP CRC PASS、D SHA逐包相同；702个non-HTML run files中694个hash匹配包清单，8个ignored run.log缺失 | COLD_ARCHIVE_CANDIDATE仅限tracked run data sparse-out；八个日志必须本地保留 |
| bvm-2x2-rowcol-selection-v1-20260928/全目录 | 5,015,158,784 B | 顶层comparison HTML未重建；平台配置/代码也在该目录 | KEEP：不整目录搬移 |

2×2的33个包均以A001 snapshot为基包，有bundle/delta manifest和独立PACKAGE_QA；D盘33/33 ZIP SHA与本地文件及QA相符。A001 Drive file ID 1bTXg56zs0NiJ14lpGXwLFzarN6jcGn45的实际流内容 SHA为90b174f0f7ea71c6d41bcf85db1d999af9c173c0b0ecbb8de31f1c96bb4e3f50，与本地一致。Drive metadata没有SHA字段。33个Drive对象均有ID且name/size匹配，但其余32个内容SHA未核验；批量流读耗时过长已停止，未保存本地副本。所有包ID和哈希状态列于CSV。

2×2 runs内共有857个文件：676 tracked / 1,659,742,802 B；155 ignored HTML / 2,982,148,703 B；26 ignored run.log，其中8个不在归档清单里。其余tracked run文件通过D package member hash核对。稀疏检出可以隐藏tracked数据但不缩小.git；如后续批准，应只排除tracked files，保留8个ignored logs，不要把这个建议描述成whole-directory cold archive。

其他较大实验：bvm-qb-50ghz-merge 1,964,834,816 B；bvm-load-qb-matrix 1,539,563,520 B；qb-rj1-l1 sensitivity 1,495,863,296 B；bvm-bq-cb-gap 1,129,943,040 B；timestep robustness 1,015,226,368 B；两版T1 interface topology约0.69GB；closed-loop QB screen 672,849,920 B。没有逐run打通完整raw/deck/stimulus/source/solver/version/manifest/Drive ID恢复链，全部列UNKNOWN/KEEP，不根据年代推断已被取代。

V0–V9、冻结电路及11个模型依赖、scripts/bvm_stimulus.py/configure.sh/run.sh、合同/研究记录/SHA manifest均保留。当前final_runs/USER_CASE.env仍为READ/CLOCK/SE-CLOCK 75/75/63 ps，而目标要求80/80/68 ps；未改动。历史4×4样本run记录JoSIM v2.7.2837d13；未来256-case须以v2.7.02a34ee单独preflight。

## Raw 与 ZIP 重复关系

四个重点目录共686个raw / 16,432,556,993 B；本轮重算SHA得到22组 / 51个文件重复，extra-copy逻辑大小673,412,490 B：

- 4组（380,351,436 B extra）同时有相同rendered deck、stimulus.inc与source-manifest SHA；仍保留每个run ID和路径，CSV中归为KEEP并注明可进一步审阅去重。
- 其余18组raw SHA相同，但deck/stimulus/source之一不同或不完整，应KEEP，不视为同参数/同激励实验。
- 所有22组路径、SHA、组内副本状态见CSV。
- 第一阶段记录的全工作区315组/1,301实例/2,490,730,482 B候选与本阶段目标目录重叠且范围不同，不能相加，也不代表safe deletion。

D盘有58组字节级相同ZIP。50组本地mirror manifest已解析（1,029,865,537 B候选extra copy），8组无可识别manifest（291,021,111 B）按要求标UNKNOWN。Drive也有58组同名同大小对象，但云端字节未逐组验证。D SHA不能证明Drive内容相同；没有ZIP被删或移动。

## 分层清理建议

| 层 | 条件候选 | 估计 | 边界 |
|---|---|---:|---|
| 工作区HTML白名单 | 161页 | 3,350,950,641 B | derived pages；须另行批准 |
| 2×2 tracked runs sparse-checkout | 676 tracked files | 1,659,742,802 B | 与HTML分列；8个ignored log留下；Git对象不缩小 |
| Raw重复组 | 4组输入一致、18组raw-only | 673,412,490 B raw excess | 不是已批准删除金额；保留run路径 |
| D盘重复ZIP | 50组manifest parsed，8组UNKNOWN | 1,029,865,537 B + 291,021,111 B UNKNOWN | 本地D层，不与云端相加 |
| Drive重复ZIP | 58组同名同大小 | 最多1,320,886,648 B metadata候选 | 云端SHA未证，不删除 |
| Git历史/LFS | 无安全直接释放 | 0 B | sparse-checkout只影响working tree |

建议顺序：先审阅CSV；如批准，只处理161个HTML精确路径；再单独批准对2×2 tracked run files的sparse-checkout，并保留8个logs。其他目录先补齐每run的raw/deck/stimulus/source/solver/version/manifest/Drive file ID对应关系；Drive重复项只有在远端SHA和成员校验通过后才进入清理候选。Git对象历史不做GC/重写。

回滚方式：已清理的白名单HTML可用保留的raw、plot_manifest/plot_qa、当前renderer与共享Plotly asset重新生成；恢复后核对raw和manifest SHA。若日后批准sparse-checkout，可用 git sparse-checkout add test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs 重新物化tracked文件，或禁用sparse-checkout恢复完整tracked工作树；此操作不会恢复/删除ignored的8个run.log，故这8个日志必须留在本地或先建立独立校验归档。Drive/D重复包如未来获准处置，应先保留一个经过SHA与成员验证的file ID/路径副本，验证可恢复后再考虑把另一份移入可恢复的回收站，不做永久删除。

## 本批执行记录

物理求解0；raw修改0；项目文件移动/删除0；Drive写操作0；Git GC/LFS prune/history rewrite 0。HTML复现只在临时目录生成并清理；原raw和HTML未变。输出仅新增本报告和CSV，未提交，等待审阅。

