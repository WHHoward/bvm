# CLEANUP_PHASE3_RESULT

## 执行结果

- 执行前 HEAD：`91711d9cb45db70933249e9931c04165d3c68ec1`（`master`，执行后 HEAD 未变；后续仅新增本报告并提交）。
- 核验范围：`CLEANUP_PHASE2_ACTIONS.csv` 中 `SAFE_LOCAL_CLEANUP` 的精确路径白名单；161 条唯一记录，总逻辑大小 `3,350,950,641` 字节。
- 结果：161 个 HTML 删除成功，0 跳过，0 失败（2×2：155；4×4：5；R-loop：1）。
- 每个文件在 unlink 前均再次核对：仍是白名单内的普通 `.html` 文件、文件大小与 SHA-256 符合审计 CSV、Git ignored 且未跟踪、非硬链接；对应 raw SHA 与审计记录、plot manifest、QA 一致，QA 状态通过，共享 Plotly JS 路径及 SHA 正确。每个精确路径仅调用一次文件级 unlink。
- V0–V9 未触及。未删除目录；未操作 raw、deck、stimulus、日志、模型、manifest、源码、Git 历史/LFS、D 盘或 Google Drive；未运行 JoSIM。

## 空间变化

| 口径 | 释放空间 |
|---|---:|
| 文件逻辑大小 | 3,350,950,641 B |
| 按文件系统分配块统计 | 3,351,359,488 B |
| 文件系统可用空间读数变化 | 3,351,359,488 B |

通过 `shutil.disk_usage` 读取的执行前后可用空间分别为 735,415,205,888 B 和 738,766,565,376 B。分配块数比逻辑字节多 408,847 B，符合文件系统块分配取整。

## 保留证据核验

- 关联 32 个唯一 raw 均重新计算 SHA-256，与审计 CSV 中的原始 SHA 完全一致；逐文件清单见下表。
- 受影响 run 目录内除这 161 个精确 HTML 外的 909 个保留文件，执行前后路径/大小/SHA 聚合校验一致：`99167dfdc484755a04f5030b0064c594d0bd3835825219097c4cc9f4b07bb5d7`。
- `CLEANUP_PHASE2_ACTIONS.csv` 与 `CLEANUP_PHASE2_REPORT.md` 清理前后未变；清理时工作树无未提交修改，当前分支仍为 `master`。
- 原 plot manifest/QA 文件按要求保留原样；它们记录的是清理前 HTML 的生成与 QA 证据。被清理 HTML 可在原始 raw、绘图脚本及共享 Plotly 资源仍在的条件下重建。

## 文件级清理记录

下表每一行均为成功删除；共同原因/依据为：精确白名单命中，执行前即时 SHA/大小/ignored/未跟踪检查通过，且关联 raw/manifest/QA 复核通过。SHA 与字节数对应删除前文件。

| 状态 | 路径 | 删除前 HTML SHA-256 | 逻辑字节 |
|---|---|---|---:|
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/plots/01_outputs.html` | `6f9a928198372460579bffaa46d6a3778ca37d1b34233237da5e09e29b5d7cf3` | 4559076 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/plots/02_drive_currents.html` | `f7c830786458296b1724ffbc428841cd4255cbc733b6d73ba604be3f6d2832ea` | 20267154 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/plots/cells/R1C1.html` | `838a36e2f439db7445bc74265c2914ceb3d0cfc66deffedf0477442fdef1aa48` | 13554716 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/plots/cells/R1C2.html` | `c1dfd9b8f278fccb87ca0f5e6958738d0617d5088e079580325132f32e1bda20` | 13559656 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/plots/cells/R2C1.html` | `d89de9ac296cef7b0931b5b6469d9fbcfceea80101e91ea939804b247e48243c` | 13549781 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/plots/cells/R2C2.html` | `216bb29df6ac664407e5c4a982c042019efc584e944f7f1a612cfe3263b01043` | 13556286 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/plots/01_outputs.html` | `bb4c08e6ee2b5816d3cf80c79fc73abcc79dad59086b775bfbeb505235f94b9f` | 4543896 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/plots/02_drive_currents.html` | `c59a383fa79ecd1dd3b4b0f278efbdba3ea20c86892a24118546b1acd2cb169d` | 13653526 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/plots/cells/R1C1.html` | `fe8680bd55aa8af524a080813e4138f0e8bcbea852f8b257f9961203d62bb9b0` | 13442741 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/plots/cells/R1C2.html` | `b638bdaa570e1146d7910790f0364f738d784aa9a333fe4a621c910c91815b85` | 13429351 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/plots/cells/R2C1.html` | `b5738144e4050a48245f84dd71cfbf29ec44d20917d3893c6379299b0b1587e8` | 13440056 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/plots/cells/R2C2.html` | `558bf34cb2a0a660f7ee625fc2fba20466e12ba829674a517320b90d281267b2` | 13424891 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/plots/01_outputs.html` | `32558403e3ab7b5ef55a49eb39951111317d72d446e3f6535c711ce4476f8919` | 4559911 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/plots/02_drive_currents.html` | `a1aa72967cdc45025dd7ca306d91c2288d06fbaf20a5dc31c78a330ea69d0ba8` | 13660326 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/plots/cells/R1C1.html` | `54ccacca4d4af456de027035d05554a16aff5a9d2c240ae0637cff586d2d1ab8` | 13550336 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/plots/cells/R1C2.html` | `89694601efa37d18a2042f14ad9c44cdcac21ba61cad3baf920a6a9432d3776c` | 13564931 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/plots/cells/R2C1.html` | `148692e85243a94c92047915720f2646223074f7502b4e9dcd2f052ba810583b` | 13585656 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/plots/cells/R2C2.html` | `f94d8720f3a6e49da850f8ebcc1d684290d78cf2ee57efe51add3f9388e02892` | 13559496 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/plots/01_outputs.html` | `fa0b747745132bd85cd7a39b43d5866fc03085b27bf112ca2034eed1b00a7ef0` | 4603551 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/plots/02_drive_currents.html` | `af4199d9f7175f145d9441473cdc6affb44cbcb35c9c48360671050843b65b93` | 15856682 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/plots/cells/R1C1.html` | `f07b06695e0830de3022d9af1b3ff98064faf17f19a810d2462ce588b5437beb` | 13378886 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/plots/cells/R1C2.html` | `b263f90b19db7bcd3f2daec6c0841770300dacf0a0c24081bd8c2ea59f7583fe` | 13447981 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/plots/cells/R2C1.html` | `a434bc3a6cf4f73fd8703e9c606fd25d956f399a54e32049c3e774e4730d59e8` | 13444966 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/plots/cells/R2C2.html` | `78d211518cbae4f2ee061467e621c7356b4d045300b8f3fb05dd3eda0b8d172f` | 13448046 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/plots/01_outputs.html` | `5cf47ff29b4e5683ae87316768f4b8ecd6e8f28bbdf835bf6e120aa3f0094c9b` | 4551171 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/plots/02_drive_currents.html` | `1e06a5dd03b550a101ad7ee0d968f35bbfce9c529fba7f7509ae0c00d9950cf5` | 15851502 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/plots/cells/R1C1.html` | `27fd642d99870897729fba67f5620cea3f450e75d7bf2fb3d1dbb2c943696d9e` | 13550366 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/plots/cells/R1C2.html` | `8615010bd9a269bbd14c60bf0d699c3e78be34954bb6e9437c0065296536e8eb` | 13564376 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/plots/cells/R2C1.html` | `5a643a74ac9d306e1c8d98f0a81181b7f9953c2a2f99ed2b866702ea05b9c1d1` | 13557066 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/plots/cells/R2C2.html` | `7c078a7be529836c830f6e35abd838bfde886197bccacd85f88fa9a39513dcf8` | 13556686 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/plots/01_outputs.html` | `3e46ea4bd3b6385c869c1b3d4fc84d5d4b6de45d582ade5596f84e69ba9ee980` | 4559821 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/plots/02_drive_currents.html` | `34782bb556e49aac302315b4b142e84b53a314d8d34e20db0622b15593e474ab` | 15856677 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/plots/cells/R1C1.html` | `7048c64dd72047da4139d0eac2be0bd5faf56894aa5c8e49766fea8c243f2744` | 13550006 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/plots/cells/R1C2.html` | `3e53a25880b9763dba18e0436b1efb57a7cdf5f94f0dd750376ab7aa7fdc401c` | 13563191 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/plots/cells/R2C1.html` | `3b2344fb62ac7fe79d22ad946908a3e41e6c58612621093b827b96ba95950723` | 13549046 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/plots/cells/R2C2.html` | `3c8bf98f0d90f582ba05e5ea76a6e73f39a7b5f255c959a8c19cadf2cfd7a802` | 13558806 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/01_outputs.html` | `965d953c46c4f22cf98bf47c1f2477b03ff501c6c7999606dbccb3294c65b8a9` | 4563816 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/02_drive_currents.html` | `1bf8f38210f179d459d477e1897933baf92d9df9b37773b161f41c5283955753` | 15882947 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/cells/R1C1.html` | `282ad2dc1adb60f91d29e0d91dfaad88eaf4397c52e1e1328c4125422d1f7dc4` | 13560041 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/cells/R1C2.html` | `d0015d233f672265fb7ba0457b0d3a2dc5def65a4a56902e9d965d6e41d64686` | 13568441 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/cells/R2C1.html` | `19d8dae071290a333386cf9661be43468564a5d98062b07ec302760160ac1385` | 13576706 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/cells/R2C2.html` | `e53828633d7151fcb5d05c7cdfa7c721574fbc93d52e44391d84b5b4123cda71` | 13567166 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/windows/01_first_read_r2c1.html` | `996ec139df42ebd833929502bd8807ec1a27b554def34beb4583e6bef7581880` | 704749 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/windows/02_recovery_r2c1.html` | `1c817c3229158cce15cdfb63c90823119ea46e09e7b985072469e3e9c1473def` | 3107701 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/plots/windows/03_second_read_r2c1.html` | `633ee05bba60cc00cffef47745582256331805830df7d4ebd0f14486c6c42b32` | 720927 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/01_outputs.html` | `9f5e7f1b251716b76e30938f3791bfed6fb128f47cb254fed61a41de2c6ac1fb` | 4567741 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/02_drive_currents.html` | `abe6b471a1687f0f9364aaa7980f244e14f6932f756f48a2d8d60286ef837e52` | 15891342 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/cells/R1C1.html` | `82115453fdb6024e06be5df371ee592a9e6481530d6dfe494c7dc448edc3aa56` | 13559616 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/cells/R1C2.html` | `059a54dc4672d8bad11c40639085effd230da444ed4fb32b2825909323d98fa3` | 13566526 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/cells/R2C1.html` | `30c068ee5938edad3db93abdcdd085c58b5f83e0cb2344cf7ccbe8dc13f15962` | 13527986 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/cells/R2C2.html` | `9f45291b8b4e6cf7a7d22a56c8ba03ab35e9c2ca1eaf243aee95af18706a7dbf` | 13568086 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/windows/01_first_read_r2c1.html` | `33efef9274b04fa66aba65c3a0ea4599891bf6afcf0714bc6c4dea85d2af2b3d` | 717924 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/windows/02_recovery_r2c1.html` | `a8363808d3f9aaa9be2a1a0c749c7211f8bb8a62b4ab8b875a0ead5b5a492df8` | 3118706 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/plots/windows/03_second_read_r2c1.html` | `c23a2fd4ae543ec91cef9e3ad790efd678ff17f139a29c943ed56f803d2cd532` | 718797 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/01_outputs.html` | `4e2fc731095651faa4d7dc48ef8a3765d607a00691d2d57dcf244451c507e7fc` | 4569596 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/02_drive_currents.html` | `f3a9c3701a15260a1f1ca71b239d9af6a83d392b90c46c5a1fb2f6e583b275b0` | 15887737 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/cells/R1C1.html` | `4a739576449cebcf2a4a9c37368a7ad924e734ae37e4ea06a105d0c08880be30` | 13531806 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/cells/R1C2.html` | `66c18a250d5ea6abbd050be3ed73302ccdc61998e50573815940fb8048d90354` | 13565136 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/cells/R2C1.html` | `efa41364bf2688a05260c51984d411c2e62af2a77d9c21d9af1e026d30ae85d1` | 13565706 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/cells/R2C2.html` | `e83b8b67b317451e48e1b774ba9cadd18d7dcef245b420666b5dd5a615c0d469` | 13565411 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/windows/01_first_read_r2c1.html` | `3ab0ac710d67f5ac5dab1673cf522dd63e78f72c704d87e85355a6c04f2f4b57` | 705354 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/windows/02_recovery_r2c1.html` | `3b85f369fe712b07072cf5dc53d73c74bee61f80447916e26a984e7abb35aeeb` | 3107421 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/plots/windows/03_second_read_r2c1.html` | `abb3266df97f1922c018a08076eba927f79cf3a9e6937bbf4bf4288a64a79928` | 702212 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/01_outputs.html` | `bb271509e18ec04bf6531e92d3e5c4b5cf0006aaaa17a08852f4c3a3a607a499` | 4568921 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/02_drive_currents.html` | `4453e3aea216a566234066a92381f15c4b57bd32f2bc652840fb0e8ff1fda58a` | 15898217 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/cells/R1C1.html` | `046c21b89042682c2851809c6603bb54be563f52297d5770faa0f2c2133a2752` | 13531761 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/cells/R1C2.html` | `b364da22889c1988d581e9fe7b7d2a9c666965ff880ef7c39f14bfa670011478` | 13572751 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/cells/R2C1.html` | `33a987e0b03e846e26ad8374cba49f562d9e2ef1d88c97819399755348a7e5a7` | 13561116 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/cells/R2C2.html` | `ce02486a9c8275940db7fa692e8a39911bf06b7c0e5dfbc9389446488eb1244f` | 13568831 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/windows/first_read_response_R1C1.html` | `3993adcd1411084728c17428bd0b462cae8bf02a1ca28386b237c009de990f1d` | 3832326 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/windows/recovery_R1C1.html` | `bba21ec472fabdd2ddd2321584ee6ff80d87e4531578cfeef247dd9534dc4661` | 3117286 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/windows/second_read_response_R1C1.html` | `31e9668d8d3a601705332f75ef47d70f807586695a8180cdcc3ecb115ed7d013` | 5034181 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/plots/windows/first_read_response_R2C1.html` | `a2aa6d5ec641c8142b56d8176af48946a5047e7e554bb1c2834ef247d66405a5` | 3832516 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/01_outputs.html` | `0964837d2a85c050136bee2e0335dc39ceaaccc0123c0522b4ed5d5cc5b5335b` | 4577896 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/02_drive_currents.html` | `ee10c9d14639317ea7170ada5c1236d05d2cd72a32d229c7079f99b50cecd543` | 15867587 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/cells/R1C1.html` | `2df7579c5afe251c5ddb4336ee242b6c529dec0a1eabe7c1e0eb8e54c75e9dc4` | 13553566 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/cells/R1C2.html` | `267f7ba209b087a0c23eb7d1c7f94c2ea16b5ee5c3bf5ee0ff0f8be7d2b62521` | 13552051 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/cells/R2C1.html` | `97f2596530857ee701db803403d9b87899f6416046c6e2a93c3dc36a27e462d8` | 13552166 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/cells/R2C2.html` | `5f1061fa20e309be48df120b98be085ea30c778a2968fada08f3efd603d0c24f` | 13551986 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/windows/first_read_response_R1C1.html` | `644361f39b52b9e4a7d890e4fb7d0c817ec6977c4d8f3bf18550b7cfd7457ef7` | 8868075 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/windows/first_read_response_R1C2.html` | `1e80db9f4dbabcdd677a648bf4fe051d8613e067be644a83ac5aed9ecc09b658` | 8866865 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/windows/first_read_response_R2C1.html` | `f6c4eb6d26bd0a677ab2cc4d1e3bdbf2779cbe14cf1cc03f7de2be7a72e0b8ec` | 8866785 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/plots/windows/first_read_response_R2C2.html` | `789e3ce361e04a4a4bd17e1c978564162e1b74ca8d30f0bc1b021d2bd484a250` | 8866750 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/01_outputs.html` | `660369f05ecdd355ef42abc75a34cc47fb194d633b8d138c8a14f7c3a80aa9c7` | 5485702 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/02_drive_currents.html` | `783e979a124477c2aabfae51197e2426063329cd6292a3454abf07a9dc33edd2` | 19041528 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/cells/R1C1.html` | `042cfccbf4dde007373f867a795beea2a39c07c8470e93bd6000e8469f7fa666` | 16300367 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/cells/R1C2.html` | `4fec308ab539f64619e501309c2bacce1902172bbf0db268be1cb8042d1f0a6f` | 16319782 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/cells/R2C1.html` | `f10a9ece0993e1001be017f00b25a812481ea8432bda81ca9c8cc83ce7405f91` | 16319737 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/cells/R2C2.html` | `a4b95c291fee09d6cb368c69a6834635cef99bfe40a0a7c1fd73b3026c560d04` | 16300632 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/windows/first_read_response_R1C1.html` | `0d89cd85eba414ed81f5719c89ad55d252a7748eceac7810d3866fd2efba8379` | 8293698 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/windows/first_read_response_R1C2.html` | `3d995e0a43afbcec9e7027d9da37c6da8b082295ca561051cfde5c8fee32f237` | 8312303 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/windows/first_read_response_R2C1.html` | `10f66c8dd9d4df8e4860e8680c1edfb60a03cdbc1c1db1577d4dfd1caefa7c8a` | 8313038 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/plots/windows/first_read_response_R2C2.html` | `c1abe45d4b2ee4de48634b5150d61bbeb202e222a968d73fb2fd5f050790437e` | 8292808 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A013_SHARED_R00_C00/plots/01_overview.html` | `e2798cdead59db4a943ebd344279b440d369a56d0816d8c97f4ae60661ac38cc` | 12410732 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A013_SHARED_R00_C00/plots/02_bvm.html` | `fece5de923b17d3c847f4292d983f869016baf03bd755d21435a94c37017f787` | 30129242 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A013_SHARED_R00_C00/plots/03_qb.html` | `35ba3efe1d6489c7fa93b999f321e450182a4a0f06fd61a6979e5f329204c87c` | 61168337 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A013_SHARED_R00_C00/plots/04_column1.html` | `5c96305ad806dfb740a8db4e97e05ab1275cda97f4dc30a1831c66492358edfb` | 47898149 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A013_SHARED_R00_C00/plots/05_column2.html` | `8205cba2aac1af23050d227b32c4f709f1c2f6a42702e25310f3750c82130221` | 47891654 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A014_SHARED_R10_C10/plots/01_overview.html` | `b380ff232a7ab9a33517ae0291b0c164dd8758afd15b50500fa42aa313198fff` | 12442297 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A014_SHARED_R10_C10/plots/02_bvm.html` | `9e5f46fb8cab28499a0de0c4f00b4c795e7884370b4712e4c15465a56c445ea8` | 30125547 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A014_SHARED_R10_C10/plots/03_qb.html` | `4b1f6abd9aeda410695e92ac12aaf4fd6e29ba8d18ccc63ff9c5dd95e37939d0` | 61300442 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A014_SHARED_R10_C10/plots/04_column1.html` | `3c3b11251bcb6718c63cb1e77f6b3bc66d978960f0b17aa66e41177aa512eaad` | 48063804 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A014_SHARED_R10_C10/plots/05_column2.html` | `0a495208f2ee1f0ae3a37406856121b926df44f5f486e8bd3bedafbef4e7bf6e` | 47887709 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A015_SHARED_R01_C10/plots/01_overview.html` | `0dbc776f28081b697f7c0892d62d8f4ed35c52c3c995330ade1c3db474133dbc` | 12441387 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A015_SHARED_R01_C10/plots/02_bvm.html` | `83aa336c5b6c8ba4b1d97d29b8409f4146be6d0bb4070c3c24cbea44b83084be` | 30120977 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A015_SHARED_R01_C10/plots/03_qb.html` | `8d86d4464e6251f4f6b50cf706fdfe50c6193176c3fe1a28acd89d05ea2e4794` | 61196607 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A015_SHARED_R01_C10/plots/04_column1.html` | `7d7bb571845b104ffa5b4ebfda757a285d689aa0edb28db2e51c780bcdab0477` | 48037584 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A015_SHARED_R01_C10/plots/05_column2.html` | `96b78921d159428d3cb933ed144feace1e93b094274a62788d335621328a6205` | 47900089 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A016_SHARED_R11_C10/plots/01_overview.html` | `7cf88274eb4b93c26095db46d3697d5c59f39776ab21c50cdab28bc7a055fec8` | 12457722 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A016_SHARED_R11_C10/plots/02_bvm.html` | `dbec0e2474435aa3bf4f9d05e408866d42139acf80fb493196e7b85fdf680ff3` | 30097882 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A016_SHARED_R11_C10/plots/03_qb.html` | `be0d6f91a703d4b709f759d332021fbfd1569f5c3ae9df965c6c8581b9d38b27` | 61329277 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A016_SHARED_R11_C10/plots/04_column1.html` | `3ebce19ec3898051948c40f1737659b20ff529821326850bc408cac21e12d6ec` | 48057609 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A016_SHARED_R11_C10/plots/05_column2.html` | `80ef5904da594642f76d12c5611e79c731b98a28d2266a5bb7fd871e2ce7c15f` | 47908629 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A017_SHARED_R10_C11/plots/01_overview.html` | `7be06cab8cd8bc93c8e0cddf6c1327cdcfa386c9e5b6f54107aac610aab9bf2c` | 12468292 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A017_SHARED_R10_C11/plots/02_bvm.html` | `d5000f096a62f333e79f768ae27098d14a4869e75f08de5564407a7ca69b6259` | 30084837 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A017_SHARED_R10_C11/plots/03_qb.html` | `22587ffd35906a6c89f213479091a2f604be34d9af3f9197f93e7f5251710cb3` | 61492772 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A017_SHARED_R10_C11/plots/04_column1.html` | `86c636b717c1c88ed7f3a723fe2e29380f226e90bc77bff8388ad4220da1f05c` | 48065439 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A017_SHARED_R10_C11/plots/05_column2.html` | `bf08c8a1bcca80991c55b05d5f0e312ac02b251ab5070f2a35e90dda82fb924c` | 48068189 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A018_SHARED_R11_C11/plots/01_overview.html` | `5ad341a844b2e95cbb5244f81cb603cba75b4a71a8abf4087abe0e9d19359612` | 12490372 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A018_SHARED_R11_C11/plots/02_bvm.html` | `398f783fe1e989c19f9e74a9e04ea5ed7f687a941c707c6b936c2358abe4b6db` | 30017272 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A018_SHARED_R11_C11/plots/03_qb.html` | `aebb32b9efabcebd9bf83d2fbd33c2d0b1c87739d5e79d2df13c68cbd527b2c0` | 61530167 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A018_SHARED_R11_C11/plots/04_column1.html` | `3cd05d500c7c3f9dd7b01db58e6eba44b08824796fce342e6c29de3b8f72a6cc` | 48059019 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A018_SHARED_R11_C11/plots/05_column2.html` | `388b99c6343e12e7005a6044fe84b5a16e529a0cd0b16164c7b7c36e4b43efea` | 48058884 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A019_T1_C1_Q0/plots/01_overview.html` | `9b0f4546b1b809bafe0fd4b614f926d06d217c13187efe3c06fcbea0dc1fdd17` | 22600385 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A019_T1_C1_Q0/plots/02_frontend_c1.html` | `9253fd20f119c3495a2b8c9a70287bbf6f77865184fa85260606220960f5145c` | 46422925 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A019_T1_C1_Q0/plots/03_t1.html` | `1b720a0518508c528bbf875f9a7c4d1a6b2f69338cc424a3a822e249cddef0e3` | 20005794 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A019_T1_C1_Q0/plots/04_t1_output.html` | `54520afebaa58fdc8145ea797403a651d3cc686f415490d17ee2ca244f6eb386` | 6826698 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A020_T1_C1_Q1/plots/01_overview.html` | `ae7933147fc3ea6c61e48a97602f310dbae7e0b69de69b3e1de5cfba57791037` | 22603975 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A020_T1_C1_Q1/plots/02_frontend_c1.html` | `6eca64199daa9696b3a129348cfd837a527844a6adac7c197f5f00680c8d943d` | 46620340 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A020_T1_C1_Q1/plots/03_t1.html` | `57c8e7128c0b6d91091e6eb3abde88077b98bd12f2dc1f08addbd95d7275cac6` | 20105404 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A020_T1_C1_Q1/plots/04_t1_output.html` | `a251edea83279bf76cf2f41357bd99ef09f085b1c1df4185e5398edfe0afcebc` | 6878458 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A021_T1_C1_Q2/plots/01_overview.html` | `a3cdf13ecd0247f16e3fecb46b9f4f10a0d5d02fded5416ebc74957648930264` | 22602295 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A021_T1_C1_Q2/plots/02_frontend_c1.html` | `3e4426c45e4222474c6a0ecfca04588501c351e0eecb497c02b2ddd4564b58ef` | 46534395 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A021_T1_C1_Q2/plots/03_t1.html` | `de60b288d1477e2866aa60a65869387fafda68a1773768713d0901eaa289b5d0` | 20107689 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A021_T1_C1_Q2/plots/04_t1_output.html` | `1341dfc0cc7e3aab4391299ff22334c319a7ac1bdda01fca22187c3b6b1c03c8` | 6882558 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A022_T1_C1_Q3/plots/01_overview.html` | `59b9b131ece2bcd7f3cf89540aa8d7a40769a4e3d8372192c246bdf4ff93753d` | 22671860 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A022_T1_C1_Q3/plots/02_frontend_c1.html` | `6adf9c8bda9e25e4ef2d835252923ae0095a104f4d9d7772b03ca324e05e053b` | 46410795 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A022_T1_C1_Q3/plots/03_t1.html` | `83751b386121cacd21f04144b1e75b5c66dc6535e13ef28b9757efa772235083` | 20054229 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A022_T1_C1_Q3/plots/04_t1_output.html` | `1a3c3f57322893a98bd217f9856b793d7e69a9bc625e6fa53b3af14984ffa835` | 6861193 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A023_T1_C1_P0/plots/01_overview.html` | `d03b6f9f344db2e82843c436ec99700f46408e7da2008b2917cc9c6cbf64ba78` | 23180514 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A023_T1_C1_P0/plots/02_frontend_c1.html` | `1c141fa1daf9a69130cd40d0cbe9bd751d792d9e8f98757b084aeed304e95572` | 46525865 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A023_T1_C1_P0/plots/03_t1.html` | `cb60a8a9261841a2fb131ba4278a531d93d420345849295777415bfd5f63b082` | 20617858 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A023_T1_C1_P0/plots/04_t1_output.html` | `84b71fbbacd61b3f148a6d05b14a6d2d32a008c53ab79de3a20e2c15919e1629` | 7189749 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A024_T1_C1_P1/plots/01_overview.html` | `fb64ec8ffd6ae497d869ad28b7417bb8b540c7d34d1111ece69970b27c6237d0` | 23215519 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A024_T1_C1_P1/plots/02_frontend_c1.html` | `8e820d17a219966110a64fa54520f24b18241cd6a2ce87bdb3a29d07f2f0bf81` | 46601615 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A024_T1_C1_P1/plots/03_t1.html` | `fde916ea1f1eaf8ee1cc4ac137a7e354236833c82fcbfa76f29eeaaca702b351` | 20676278 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A024_T1_C1_P1/plots/04_t1_output.html` | `dbe0f56bf230d77610e233eaaa096018d7f2fb319e533dacef609491e933e886` | 7239399 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A025_T1_C1_P2/plots/01_overview.html` | `6b5b1c0aff651643d5d0c55b1ba5eff3f320fcbceefb1b69521829591e2ab441` | 23210539 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A025_T1_C1_P2/plots/02_frontend_c1.html` | `3bac5bb13c65402e1b0ec65194716ab59612f628b81774eb400ca9eba060df81` | 46568600 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A025_T1_C1_P2/plots/03_t1.html` | `c4c5055dfa3e6acd112a699ce4a3d212bb40d72cadeaeddc63c0186facc7fcec` | 20678868 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A025_T1_C1_P2/plots/04_t1_output.html` | `0b1440075bde5a0868097dbd2a55594e97c79ade790b9950ef87fc78cb478b24` | 7239209 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A026_T1_C1_P3/plots/01_overview.html` | `157400286178902327279a410812d49632a2dc99527cc9a349f3c975a71399ea` | 23245919 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A026_T1_C1_P3/plots/02_frontend_c1.html` | `4c75f24df498d1284f165e830c2a6aa0bc322b07d21ef427dd6a2134007a7f36` | 46460615 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A026_T1_C1_P3/plots/03_t1.html` | `8dd3020dde634bc4fc0790173b520f76e51664782d0a39be408140de77f42c28` | 20648538 |
| DELETED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A026_T1_C1_P3/plots/04_t1_output.html` | `44b5bda88a16d398069f3fa364799559dcb98b013651886c255c4e0f4d594b79` | 7238269 |
| DELETED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/plots/runs/A108_MANUAL_CARRY5_3x3_210/02_carry.html` | `108c0c047b276da6db606d677836c55251ea555af4a9878d500507f60793df2d` | 92778464 |
| DELETED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/plots/runs/A085_C5R28_210_11x15/02_carry.html` | `c08c87b803a4f901111ed1221291fce50638616cd3ac909003ad95083b95b540` | 92770918 |
| DELETED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/plots/runs/A089_C5R28_210_7x14/02_carry.html` | `63fe68cf76903df76c786f99146733fd7759019aa73a68f6d4dd5c1a2fc80841` | 92748482 |
| DELETED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/plots/runs/A107_MANUAL_CARRY5_11x13_210/05_stage_D3_focus.html` | `a26feb65212fb427473aee6fbcc45b3b77d05e28cf9c6add5ffaa4bcd076cf1b` | 43186643 |
| DELETED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/plots/runs/A084_C5R28_210_15x11/04_t1.html` | `ea4bf0c8fa8ab829e52173842338014c27b7b8668cf95c08dcf94f200f1fe6bd` | 46275483 |
| DELETED | `test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/plots/U131_QB_L1_screen_qb_l1_1p2p/groups/CLOSED_N0_0000_jtl_1_3.html` | `aae97cea9a15ecde12eb14152ff66fc16672339c50ffc76a6ab2935fa24a4216` | 1041948 |

## 保留 raw SHA-256

| 状态 | Raw 路径 | SHA-256 |
|---|---|---|
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A001_INDEPENDENT_R10_C10/raw.csv` | `9f54462c24988cf2cf7b16332ba612a8b9ae0fed225aff75b20ddf34bc34df6c` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A002_SHARED_R10_C10/raw.csv` | `417b668f7e3a51f94b556e77808dba058aa232f0d01d9687f8959ec02443c38b` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A003_SHARED_R10_C10/raw.csv` | `3697dcc695e4241efe5cc1f2c84237a2c4ebe3e3ad1981e21450f717c05805e1` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A004_SHARED_R10_C10/raw.csv` | `3c97a4e1f5cc68f6700730ca8dd5065b4493af7a246c5cdfd26ee4ee1ee18907` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A005_SHARED_R10_C10/raw.csv` | `f91d87b5b60343111200e3e7527e70065cdaadf05aced1a7786d621924a873fb` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A006_SHARED_R10_C10/raw.csv` | `8889551700d77a1c5240456c4255583cebd96ab7da75ad7e509196663a5d9810` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A007_SHARED_R10_C10/raw.csv` | `1d45b918241aeb1f56d7a12d9f8010822b864426e820de8e81e1e4d7577f5816` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A008_SHARED_R10_C10/raw.csv` | `9fd5f6a8e5529d9f1fc7355dc62b54acec8afe89efbd33571a16059910554e7d` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A009_SHARED_R10_C11/raw.csv` | `26129172e539c340f9bde2f2f5b55414d90f7a4c25cee6a46ee30c2234e45cb9` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A010_SHARED_R11_C10/raw.csv` | `a9687368e8cf89ff18dc99c353cc4e001a241cc2d5780335f57fcc7786bdfadf` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A011_SHARED_R11_C11/raw.csv` | `b737b260d9854bb0e9a60dcce4d11024673c40a236b641667b0e5d4243241a44` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A012_SHARED_R11_C11/raw.csv` | `f20ca4a01bd79bc12e521c5171858c7a10b0f8009abe87270cbf1a4a59d2d9be` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A013_SHARED_R00_C00/raw.csv` | `2e9f8f9fcc322f2d95a49f91f4d5d2136dcff8f7dc3880b9b237e6ed9a84654e` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A014_SHARED_R10_C10/raw.csv` | `079a6f731c4ececb625665f2aed8a20aa202f8764a9c85d8fb2ea56a681b99dd` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A015_SHARED_R01_C10/raw.csv` | `12865d0e7a5046f9c62a9b48f893bb5da74fef3ae839d8a38b51d9262cbd79b7` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A016_SHARED_R11_C10/raw.csv` | `3a23533a3d8286bfd138e7a517ecb17fb7352c12e1aedd1c7c43741a0eb1fe66` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A017_SHARED_R10_C11/raw.csv` | `35bac0500aef70973c043db2d419ae580ccfc5b20548e235fad503b2f0e83a07` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A018_SHARED_R11_C11/raw.csv` | `5ce1430420117479ba3581b8f2f0234b00e545770ad9348b0bba81c07846dfe7` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A019_T1_C1_Q0/raw.csv` | `7a5b865cc087243e1d4189cadebc6ce6c2ccdc8f20c40744517ae3944c349b13` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A020_T1_C1_Q1/raw.csv` | `58a39f34eb364f1665b2b5374957ef1d1820b0523cd19dfb6e4fcc39ea1f0e37` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A021_T1_C1_Q2/raw.csv` | `5c711d54cd1c8a5466595b9b4c2cc4bd50959962a99f02bd9b8e003318fecd89` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A022_T1_C1_Q3/raw.csv` | `b84d57037580201a145d55148cca143aaf1b85ab44a35080a4bd68ef41610bb3` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A023_T1_C1_P0/raw.csv` | `b8ebafc5283bff0187e30a7984d9b4f7889533a6b23b50c0defb44e8463f2d61` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A024_T1_C1_P1/raw.csv` | `45a0dddf579adbfa8ff0ada085185f9983dba8448609a76286987b2d45d8498c` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A025_T1_C1_P2/raw.csv` | `e6d653c9e232ab7a5dd936bf8aec05ca3b210d9818ca08e62882881c4cd5c958` |
| UNCHANGED | `test/exploration/bvm-2x2-rowcol-selection-v1-20260928/runs/A026_T1_C1_P3/raw.csv` | `441bcc0cac88fe37a6e12d6f34b60ae4d7ad0f399acf4aa2b1a24bbd650bef74` |
| UNCHANGED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/runs/A084_C5R28_210_15x11/raw.csv` | `2a0c62c5087d67d98fc1214262997cd8b4b556c6ab429c2576579b066300cacd` |
| UNCHANGED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/runs/A085_C5R28_210_11x15/raw.csv` | `141bb964c7725958691f7f75d5749da827276e4b55d3c2e56b0dc5eff9231cd5` |
| UNCHANGED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/runs/A089_C5R28_210_7x14/raw.csv` | `065d771648fa7097ce47b9c7f3d08e212858139a026cea6e9734de9601bf4cdf` |
| UNCHANGED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/runs/A107_MANUAL_CARRY5_11x13_210/raw.csv` | `e68954a3745a2193140769eeddbfd740775d26615112aaad9165c11a2cb113ac` |
| UNCHANGED | `test/exploration/bvm-4x4-diagonal-array-v1-20261009/runs/A108_MANUAL_CARRY5_3x3_210/raw.csv` | `b67b567c37496716c6bf1c0355b87eb96a3ea06b5071185c296660e2843fdf16` |
| UNCHANGED | `test/exploration/bvm-rloop-one-shot-tuning-v1-20260918/runs/U131_QB_L1_screen_qb_l1_1p2p/cases/CLOSED_N0_0000/raw.csv` | `ff74075ff1c4dafa4a381a837cc0fb183acf3c25e9fb2a784976f6256d3e851d` |

跳过文件：无。失败文件：无。
