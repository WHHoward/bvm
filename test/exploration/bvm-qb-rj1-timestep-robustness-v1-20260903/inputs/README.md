# Inputs

本目录的三个 QB 文件是本实验的唯一 RJ1 sweep source：

- `qb-rj1-12.cir`
- `qb-rj1-11p5.cir`
- `qb-rj1-11.cir`

它们从已提交的 `circuits/qb/bq_cell_bvmsim_v1.cir` 生成，保留
`BQ_BVMSIM_V1 IN OUT BIAS` 外部 bias 接口和全部原始元件值；三者唯一的
物理差异是 `RJ1 2 0 12/11.5/11`。`variant_diff_check.json` 保存机器校验。

24 个 deck 位于各自的 `runs/<RUN_ID>/deck.cir`，由
`generate_decks.py` 从已核对的历史 four-BVM T100、single-BVM S0-J/S1-J
夹具生成。运行时使用 deck 内相对 include，且不修改任何历史 source 或 raw。
