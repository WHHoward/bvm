# Sol XHigh 只读科学复核

## Verdict

`NEED_REVISION`；不要求重跑 JoSIM，也不改变本轮 human gate。

## 必须修订的交付层问题

1. 将 `commanded/stored-0`、`active→zero` 限定为 commanded-0、且通过本轮
   task-local PRE_READ1→TAIL retention 检查的 state-conditioned response；没有
   READ=0/no-read 控制，不能宣称 active-1 或 READ 的唯一因果作用。
2. 明确 A/B 的 `4 SIMILAR / 4 SMALLER / 4 LARGER` 只适用于 `Delta I(L_SL)`；
   `Delta V(SL)` 的 `max_abs` 关系是 `8 SIMILAR / 4 LARGER / 0 SMALLER`。
3. 明示 BJ2 六状态 clean-separated event count 全为 0；连续多圈轨迹不能当作
   SFQ count，strict segmentation 只是 post-hoc exploratory diagnostic。
4. 修复 `plots/INDEX.html` 和 `plots/RESULT_OVERVIEW.html` 的相对链接，并明确
   39 个内嵌 Plotly HTML 按 `.gitignore` 作为可再生成的工作区文件，不属于 Git
   提交；本页、manifest、raw 和分析结果属于提交快照。
5. 将 four-track exact-grid 检查做成 hard gate，并在 provenance 中绑定独立
   checker、独立 JSON、报告和 plot manifest 的哈希。

## 处理结果

上述五项均已修订；修订只改变分析/索引/元数据，不改变六个 connected raw、A
side raw 或 solver 输入。最终分类仍为 `NO_CLEAR_STRICT_CLASSIFICATION` /
`QUICK_AMBIGUOUS`，状态仍为 `AWAITING_USER_REVIEW`。
