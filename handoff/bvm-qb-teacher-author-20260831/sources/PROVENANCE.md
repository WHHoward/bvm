# 分享包 provenance

本包从仓库 HEAD `c8cdf07794d40f3376a1c542603c836b76535f99` 复制。实验实际使用的 JoSIM 记录为：

- solver：`build/josim-cli`，版本 `v2.7.2837d13`
- solver SHA-256：`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- canonical BVM：`circuits/bvm/bvm_cell.cir`
- canonical QB：`circuits/qb/bq_cell.cir`
- JJ model：`circuits/models/jjmit.cir`
- metric specification：`docs/research/METRIC_SPEC_V2.md`，版本 `2.0.0`

复制到 `sources/` 的 canonical 文件 SHA-256：

```text
ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4  bvm/bvm_cell.cir
7e019511c0615e1208b1887e49b0a33e61d18e5423134984f052318f494856ce  qb/bq_cell.cir
19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336  models/jjmit.cir
d27ef0445aa311ac4f1bdf50cbd8d111e89f81695e6d544de93a95b95842ef28  docs/BVM_QB_PAPER_INTERFACE_AUDIT.md
f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470  docs/METRIC_SPEC_V2.md
```

`SHA256SUMS.txt` 是本分享包建立后对包内全部文件计算的校验清单（不包含校验文件自身）；校验时在本分享包根目录执行 `sha256sum -c SHA256SUMS.txt`。
