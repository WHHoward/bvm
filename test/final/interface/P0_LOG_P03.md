# P0.3 日志 — 确定性验证 (2026-08-06)

> 类型: 观察（确定性确认）

## md5 对比表（关键 CSV ×2 运行）

5 个关键网表各重跑 1 次（共 5 对），md5 与 SHA-256 双算法核对，均与初版一致；SHA-256 另与 `scripts/sfq_metrics.py` 产物 JSON 中嵌入的 sha256 交叉核对一致（初版 SHA 即 JSON 中值）。

| CSV | 初版 SHA-256 | 重跑 SHA-256 | 一致 |
|---|---|---|---|
| test_dcsfq_behavior_bump_68u.csv | f057a9603139970eafd2a2902aceae486d437929bc69fe1cb291b8b728ca46cf | f057a9603139970eafd2a2902aceae486d437929bc69fe1cb291b8b728ca46cf | ✅ |
| test_dcsfq_behavior_sustained_68u.csv | f082249001ada2e9dc4ba1b6ba85bac8481eb739465fb04aa6ac31e842174842 | f082249001ada2e9dc4ba1b6ba85bac8481eb739465fb04aa6ac31e842174842 | ✅ |
| bvm_load_12ohm.csv | 7baa0062a0b661f5fa9c794887ede26c1e6d63d33eafc4415cafbcd6a5e82600 | 7baa0062a0b661f5fa9c794887ede26c1e6d63d33eafc4415cafbcd6a5e82600 | ✅ |
| bvm_load_8jj.csv | 5b13fa2b9160c0fb7d65c11ee447f4e29339eb5d10216f7b8083b3a2a532307b | 5b13fa2b9160c0fb7d65c11ee447f4e29339eb5d10216f7b8083b3a2a532307b | ✅ |
| dcsfq_bvm_div.csv | f305488caaeebdbf20b5f38a4b30b530e1f4b0536e60e4ef3718209aee4fb579 | f305488caaeebdbf20b5f38a4b30b530e1f4b0536e60e4ef3718209aee4fb579 | ✅ |

**结论**: 5/5 md5 一致 → 固定步长仿真确定性确认（冻结口径, HANDOVER IRON RULE 5）

## 复现信息
- 命令: build/josim-cli -o <out> <netlist>（重跑文件在 /tmp 对比后已删除，md5 表即记录）
- 仿真器: build/josim-cli v2.7.2837d13
- 提交: （本行 SHA 由后续 docs 回填提交写入）
