# PAPER-SL-Q4 preflight

时间：2026-08-24T07:48:05+08:00（fixture build）

## Scope

- Parent HEAD：`bfc3c6ee600f30d27078b53ed09b23053a5191e3`
- 唯一新点：`L1=3.91 pH, L2=4.50 pH`
- 来源：accepted PAPER-SL-Q2 `inputs/40u`
- 禁止从 Q3 派生；禁止追加参数点。
- 四个 case 完成后停止。

## Fixture closure

`analysis/build_fixture.py` 对 Q2 `bq_cell.cir` 只替换一次：

```text
L2 3 4 3.91p  ->  L2 3 4 4.50p
```

`L1 2 3 3.91p` 保持；四个 source deck 和 `jjmit.cir` 均逐字复制。
生成的 byte-level 证明记录在 `inputs/deck-hashes.json`。

## Runtime provenance

- JoSIM：`build/josim-cli` v2.7.2837d13
- binary SHA-256：`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- metric spec SHA-256：`f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- timestep：0.0125 ps
- stop：170 ps
- analysis windows：main `[94,130)` ps，post `[140,170)` ps

## Stop gate

首个 `logical1 + READ=0` control 若出现 solver/artifact failure、startup/free-running
或完整 phase/area-consistent transition，不运行其余 case。control bounded 后按
预注册顺序运行其余三个 matched cases。
