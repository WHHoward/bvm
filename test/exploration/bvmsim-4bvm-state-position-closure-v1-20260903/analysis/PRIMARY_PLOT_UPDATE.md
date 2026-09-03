# Primary per-run plot update

按用户要求，更新的是每个 run 原有的
`plots/runs/<state>/BVMOUT_QB_INPUT.html`，不是另建一个替代入口。

六个原路径现在都使用 probe-extension raw 中的同一组 30 条关键探针：

- BVM1–BVM4 的 SL 首/末 JJ：P/V/I；
- BVMout：P/V/I；
- `V(QBIN)`、`V(QBOUT)`、`I(LIN|XBQ1)`。

这一步没有调用 JoSIM，只用已经完成的 probe-only raw 做 HTML 重渲染。原六个
PHASE-B raw 未改动，更新前后的 probe-extension raw SHA-256 也一致。旧的
`plots/sl_endpoints/` 文件不删除，主入口以 `plots/runs/<state>/` 为准。

命令：

```text
python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/update_bvmout_qb_input_plots.py
```

结果：exit `0`，`plots_updated=6`，`raw_unchanged=true`，每张图的 phase 轴
继续使用 `rad/(2*pi)` turns。
