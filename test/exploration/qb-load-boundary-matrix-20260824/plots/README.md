# QB load-boundary matrix 可视化

图形直接读取 `raw-v2` 的 A–E fixtures。A–C 是 whitespace 格式的历史 JoSIM 输出，绘图时只在临时目录建立格式入口，原始文件未改动；Q0+10 Ω reference 位于 QB-Q0，未复制到本目录。

- `q0-q0-open.html`、`q0-q0-jtl-only.html`、`q0-q0-10ω----jtl.html`：Q0 OPEN、JTL-only、10 Ω||JTL。
- `D-q5-open-*.html`、`E-q5-jtl-only-*.html`：Q5 的四 matched cases，分别对应 OPEN 与 JTL-only。
- `q0-boundary-comparison.html`、`q5-open-vs-jtl-read1.html`：边界对照。

主要曲线为 BJL1/BJL2 phase、BJL2 voltage、OUT、L0，以及存在时的四颗 JTL phase。phase 单位是 `rad/2π` turns，不是 SFQ count。正式 load-boundary 结论仍以本目录 `REPORT.md` 为准。
