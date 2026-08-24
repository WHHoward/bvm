# QB→JTL load back-action 可视化

本目录只读取五个 accepted fixture 的既有 raw：Q0+10 Ω（QB-Q0）、Q0 OPEN/JTL-only/10 Ω||JTL（load-boundary matrix）和 M3 series-10 Ω→JTL（interface mechanism）。没有复制 raw。

- `fixture-*.html`：各 fixture 独立观察；
- `backaction_compare.html`：对齐 `200–260 ps`，覆盖注册的 `208–210 ps` pre、`210–217.1 ps` crossing、`217.1–259 ps` post 区间。

重点曲线为 `P(BJL2|XBQ)`、`I(L2|XBQ)`、`I(L0|XBQ)`、`V(OUT)`；具备时保留四颗 JTL phase。正式机制分类为 **`MIXED_DYNAMIC_LOADING`**，图形不替代 node-4 KCL/report。
