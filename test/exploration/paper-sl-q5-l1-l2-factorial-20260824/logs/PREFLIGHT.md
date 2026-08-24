# PAPER-SL-Q5 preflight

时间：2026-08-24T08:01:00+08:00（fixture build）

## Scope

- Parent HEAD：`67a7c9e3335343a09e90ec7ddfe5a4d7c38ea52c`
- Q5 直接从 accepted Q2 `inputs/40u` 构建；不从 Q3/Q4 派生。
- 唯一 circuit changes：`L1 3.91p→4.50p` 与 `L2 3.91p→4.50p`。
- IBIAS=40 µA；configured timestep=0.0125 ps；stop=170 ps。
- main=`[94,130)` ps；post=`[140,170)` ps。

## Fixture closure

`analysis/build_fixture.py` 验证了 Q2→Q5 只有两行电感变化；四个 replay decks
和 `jjmit.cir` 逐字复制。`inputs/deck-hashes.json` 保存 source/generated hashes。

## Stop gate

先运行 `logical1 + READ=0 control`。若出现 artifact/solver failure、startup/free-running
或完整 phase/area-consistent output transition，立即停止；control bounded 后按
预注册顺序运行其余三个 case，四个 case 后无条件停止。
