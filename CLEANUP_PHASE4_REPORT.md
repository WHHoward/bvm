# CLEANUP_PHASE4_REPORT

审计日期：2026-10-15  
仓库：WHHoward/bvm  
HEAD：c261f7a0d54667faeec536b23a369d9571379759（未改变）  
本批只清理已核验派生HTML并整理归档索引；JoSIM求解0；Drive/D/Git历史/LFS均未改。

## 结果摘要

- 精确白名单删除10,651个ignored、未跟踪HTML：atlas 10,620、atlas index 15、A007/A008旧页4、T1 A013–A016旧页12；跳过0、失败0。
- 文件逻辑大小240,098,505 B；inode分配块总计266,383,360 B；删除前后即时free读数增加260,096,000 B（738,908,172,288 → 739,168,268,288）。元数据/日志开销使两种口径不必相等。
- 每个被删文件的原SHA、关联raw路径/SHA、恢复位置和unlink状态都在CLEANUP_PHASE4_ACTIONS.csv。

## 存储分层，不重复相加

| 层 | 清理后读数 |
|---|---:|
| 工作区含.git | 110,881,738,752 B allocated；110,777,854,358 B logical |
| .git对象/LFS | 18,696,388,608 B allocated；未清理历史对象 |
| test/exploration | 90,779,357,184 B allocated |
| D:/BVM_Backages | 11,672,293,376 B allocated；11,671,479,003 B logical |
| Drive BVM_Backages | 11,636,642,487 B文件元数据；377文件，其中375 ZIP（另有3个文件夹） |

Phase3此前单独释放3,350,950,641 B，不计入本批；sparse-checkout不减少.git/LFS。

## HTML复现与保留

- Current baseline plot manifest的10,620 atlas页逐项SHA通过；15个raw SHA重核。D v3 ZIP CRC PASS，10,620 atlas、15 atlas index、15 raw成员的SHA与本地匹配。Phase2曾用冻结renderer临时重建36个代表页，字节级PASS。
- A007/A008旧图4个匹配responsive_v2替代图的信号、trace/sample；T1 A013–A016旧图12个匹配classic-layout替代图；均有QA PASS及不变raw。
- 其他4×4审阅页、R-loop review/group页、2×2比较图、V0–V9未纳入白名单，保留。剩余HTML目录统计在actions CSV。

## 历史目录占用（按互斥的test/exploration直属目录分类）

| 类别 | allocated | raw / HTML / ZIP |
|---|---:|---|
| ARRAY_PLATFORMS | 46,536,257,536 B | raw 147 / 11,281,504,113; HTML 1030 / 30,940,243,337; ZIP 178 / 3,006,870,226 |
| BVM_QB_INTERFACE | 19,954,507,776 B | raw 237 / 3,440,919,055; HTML 1861 / 11,036,652,786; ZIP 38 / 4,145,495,645 |
| BVM_READ_STATE_RECEIVER | 3,441,074,176 B | raw 0 / 0; HTML 113 / 1,452,202,979; ZIP 0 / 0 |
| BVM_RLOOP | 7,929,929,728 B | raw 557 / 3,514,151,780; HTML 4003 / 2,543,268,506; ZIP 39 / 833,587,149 |
| OTHER | 7,449,210,880 B | raw 187 / 1,108,553,237; HTML 756 / 4,843,493,473; ZIP 9 / 276,741,729 |
| QB_STANDALONE | 5,468,360,704 B | raw 164 / 1,193,053,050; HTML 528 / 3,203,267,718; ZIP 19 / 271,954,950 |

- 4×4平台当前占用42,709,225,472 B，KEEP。
- 2×2平台占用2,032,185,344 B；26 run归档链可定位；676个tracked非HTML只列未来sparse-checkout候选，8个日志保留。
- R-loop平台6,951,936,000 B allocated；历史参数/control/失败证据保留，归档闭包不完整。
- QB-CB array平台9,569,628,160 B allocated；raw部分有包但full manifest/Drive闭包未证。
- bvm-load-qb-matrix、qb-50ghz-merge、QB-T1 interface、BVM-BQ-CB gap与2x1实验仍保留为连接/失败对照；没有逐run完整恢复链，标UNKNOWN/KEEP。
- Phase2已知重复raw记录51条仍KEEP；不因SHA相同移除run路径。根目录raw/HTML/ZIP数量见Archive Index。

## 归档与重复候选

- 2×2：A001–A026的raw/deck/stimulus/source_manifest/provenance、solver版本/二进制SHA、PACKAGE_QA、D ZIP SHA和Drive ID见HISTORICAL_EXPERIMENT_ARCHIVE_INDEX.csv。D包计33个；Phase2临时目录恢复验证PASS；核心文件SHA与package member map重核。A001由成员路径SHA映射（旧QA未填raw_sha256_by_run）。8个run.log仍本地KEEP。
- Current baseline D v3 ZIP SHA 9d049b311f52c5e0a288572f287fd517a0fb227168d7c6d7e2eb53ea9be67348；raw 15/15、atlas 10620/10620成员通过；仍有240个grouped HTML/index不在ZIP，整套不是cold-archive closed。
- D盘找到54组byte-identical ZIP，额外副本候选1,286,093,431 B；未删移。
- Drive元数据找到54组同名同大小ZIP，估算额外1,286,093,431 B；无远端SHA，不能把候选当作已证实云端重复或可释放空间。无下载/写操作。

## 推荐方案与恢复

- 本批已证实安全释放：逻辑240,098,505 B；allocated 266,383,360 B；即时free读数+260,096,000 B。
- 下一阶段可在单独批准后，仅对2×2明确的676个tracked run文件配置sparse-checkout；这只缩小工作树，不缩小Git历史，8个未归档run.log需原样留下。
- D盘ZIP去重和Drive去重都未做；Drive先逐file ID验证远端字节和成员闭包，不能用本地D SHA代替。其他实验先补齐run→raw→deck/stimulus→frozen sources→solver→manifest→archive→Drive ID→restore链。

## 边界

- V9在操作前已有未提交用户修改。本批前后SHA一致，raw.csv存在且SHA=03c2af990bd87c1c8cbe355245127f9edb619d8740c1cbe0679cef4b61420339；没有覆盖或恢复用户文件。
- USER_CASE当前：READ_INTERVAL_PS=75, CLOCK_PERIOD_PS=75, SE_CLOCK_DELAY_PS=63, FIRST_READ_PS=110；80/80/68目标仅记录，未修改。
- Phase2/Phase3报告SHA不变；用户批准的visualization/index.md导航更新保留。HEAD未变，无stage/commit/push。无git clean/gc/LFS prune/filter-repo/force-push/sparse-checkout，无JoSIM。
