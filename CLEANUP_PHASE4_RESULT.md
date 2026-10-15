# CLEANUP_PHASE4_RESULT

## 执行结果

HEAD前后为c261f7a0d54667faeec536b23a369d9571379759，未改变。
白名单10,651项：删除10651，跳过0，失败0；只对普通、ignored、未跟踪HTML执行逐文件unlink，无目录递归。
删除逻辑大小240,098,505 B；文件分配块266,383,360 B；即时free读数由738,908,172,288变为739,168,268,288 B，增加260,096,000 B。
逐文件原SHA/raw SHA/恢复位置/状态在CLEANUP_PHASE4_ACTIONS.csv。
Atlas恢复位置：/mnt/d/BVM_Backages/bvm-qb-current-baseline-n0-n4-closed-passive-replay-v1-20260917_v3_raw_handoff.zip，SHA-256 9d049b311f52c5e0a288572f287fd517a0fb227168d7c6d7e2eb53ea9be67348，ZIP CRC PASS；被删atlas及index成员SHA匹配。修复旧图可用保留raw与QA-passed替代页面恢复。

## 保留核验

- 15个baseline raw、plot manifest/QA、grouped pages/index、data.js、shared Plotly asset不变。
- 2×2 A001–A026归档映射列于HISTORICAL_EXPERIMENT_ARCHIVE_INDEX.csv；676 tracked文件只列候选未sparse-checkout；8个日志本地保留。
- V9用户修改（含raw.csv）、Phase2/Phase3报告、D文件均不变；Drive仅查metadata，无文件下载或写入。
- JoSIM solve 0；无raw/deck/stimulus/log/model/manifest/source删除；无Git/LFS历史清理；未commit/push。

## STOP

本阶段结束。稀疏检出、D/Drive去重和旧实验迁移均未执行，等待后续明确授权。
