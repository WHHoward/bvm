# PAPER-SL-L0 报告：12×320 µA JSL load characterization

## Verdict

**`PAPER_JSL_LOAD_VALID`（限于本轮 external-series-load realization）**

12 个 JSL 在四个 matched case 中都没有形成完整的 phase transition，也没有
出现 free-running。canonical `+READ` 的 logical1/logical0 source distinction
仍然明显，READ=0 controls 仍 inactive；BVM 的 settled storage phase 没有出现
明显的 state-sign 破坏。

但这不是 waveform-equivalent 的 canonical no-receiver 结果：JSL load 明显
改变了 `SL` 的 lobe 形状、持续时间和 read1 后振铃。这个 bounded loading
effect 已作为本轮结果保留，不能在下一轮 replay 中被忽略。

本 verdict 不等价于“所有 JSL 实现都有效”，也不等价于 SFQ delivery。

## 1. 实际拓扑与 provenance

本轮使用：

```text
XBVM1 ... SL1 BVM
SL1 -> B_LD1 -> B_LD2 -> ... -> B_LD12 -> GND
```

`B_LD1...B_LD12` 全部为 `jjmit area=3.2`。canonical BVM 内部的
`L_PSL`、`R_SL=12 Ω`、`L_SL=0.4 pH` 未改变，因此 `I(L_SL|XBVM1)` 仍是
BVM-side source current；`V(SL1)` 是 stack 的 BVM-side terminal，
`V(NJSL11)` 是最后一个 JSL 前的 far-side terminal，`B_LD12` 的另一端为
ground。

论文第 2.5 节还描述了“用 JSL 替换内部 `L_SL`”的另一种设计解释。本轮
没有执行该内部 replacement，因为当前问题是 frozen canonical BVM 的 SL
load characterization；历史仓库的 8-JJ fixture 也采用了从 BVM `SL` port
向外串接并接地的 stack。因而本结果必须标注为 external-load realization，
不能直接充当 internal-`L_SL` replacement 的证据。

使用的输入/模型：

- `build/josim-cli` v2.7.2837d13，SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`；
- canonical `bvm_cell.cir` SHA-256
  `ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4`；
- repository `jjmit.cir` SHA-256
  `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`；
- local included model copy SHA-256
  `7afca1762aa314dc2589d86b69cc9e3bfe471f28b83bb5fc3eda45fef50b3022`；
- `.tran 0.0125p 170p`，每个 CSV 13,599 个有效数据行。

实际模型中的 `AREA=3.2` 参数为：

| 参数 | 实值 |
|---|---:|
| `Ic` | 320 µA |
| `C` | 224 fF |
| `RN` | 5 Ω |
| `R0` | 50 Ω |

零偏 Josephson inductance 为约 `1.028 pH/JJ`，12 个约 `12.34 pH`；运行时
的非零电流修正由 raw nonlinear trajectory 决定。

## 2. JSL phase/current/voltage evidence

以下 phase 单位是 raw `P()` radians 解包后除以 `2π` 的 turns；同段 area
使用同一 JSL、同一 monotonic segment 和 CSV 实际时间积分。

| case | 12 个 JSL 最大 read activity range | 最大 monotonic segment | 同段 voltage area | post 最大 range | complete JSL |
|---|---:|---:|---:|---:|---:|
| logical1 + READ | 0.0693363 turn | −0.0543798 turn | −0.0543884 Φ0 | 0.00512784 turn | 0 |
| logical0 + READ | 0.00539254 turn | +0.00370884 turn | +0.00370977 Φ0 | 0.000234727 turn | 0 |
| logical1 + READ=0 | 2.64770×10⁻⁵ turn | −2.64770×10⁻⁵ turn | −2.64829×10⁻⁵ Φ0 | 2.30577×10⁻⁶ turn | 0 |
| logical0 + READ=0 | 2.64770×10⁻⁵ turn | +2.64770×10⁻⁵ turn | +2.64829×10⁻⁵ Φ0 | 2.30577×10⁻⁶ turn | 0 |

12 个 branch 的 current 在 read window 内完全一致到数值精度：最大瞬时
`I(B_LD1)-I(B_LD12)` 差异为 `0`（controls 的最大数值残差约
`1×10⁻¹³ µA`）。所以表中的 phase/area 结果不是某一颗 JSL 独有的
局部异常。

JSL current 与 voltage 的 read-window 范围如下；电流超过/低于 `Ic` 只作
operating-scale 检查，不作 switching 判据：

| case | `I(JSL)` min…max | `|I|/Ic` max | `V(JSL)` min…max |
|---|---:|---:|---:|
| logical1 + READ | −20.037…79.067 µA | 0.2471 | −127.33…84.71 µV |
| logical0 + READ | −4.199…3.636 µA | 0.01312 | −8.546…10.045 µV |
| logical1 + READ=0 | −0.009725…0.008644 µA | 3.04×10⁻⁵ | −0.0671…0.0609 µV |
| logical0 + READ=0 | −0.008644…0.009725 µA | 3.04×10⁻⁵ | −0.0609…0.0671 µV |

最大 read1 activity segment 的 phase/area residual 只有约
`−8.66×10⁻⁶ turn`；logical0 为约 `+9.29×10⁻⁷ turn`。这支持的是
bounded sub-turn trajectory，不是 local SFQ event。

## 3. SL waveform 与 canonical no-receiver 对照

这里的 loaded signal 在 `SL1`（BVM-side terminal）观察；canonical 对照为
同一四 case 的 no-receiver `R_LD=12 Ω` raw。lobe area 单位为
`µA·ps`（电流）或 `µV·ps`（电压），持续时间是本轮预注册的
`|waveform| ≥ 10% peak` diagnostic duration，不是物理 universal threshold。

### 3.1 `I(L_SL|XBVM1)`

| case | loaded min…max (µA) | canonical min…max (µA) | loaded signed / positive / negative area | canonical signed / positive / negative area | loaded / canonical duration |
|---|---:|---:|---:|---:|---:|
| logical1 + READ | −20.04…79.07 | −45.15…75.34 | 516.36 / 580.59 / −64.23 | 258.40 / 357.75 / −99.35 | 17.59 / 14.21 ps |
| logical0 + READ | −4.20…3.64 | −26.41…22.73 | −0.113 / 17.40 / −17.52 | 0.004 / 56.60 / −56.60 | 24.76 / 12.24 ps |

### 3.2 `V(SL1)` and post ringing

| case | loaded read min…max | canonical read min…max | loaded read p2p | canonical read p2p | loaded post p2p / canonical post p2p |
|---|---:|---:|---:|---:|---:|
| logical1 + READ | −1.528…+1.017 mV | −0.542…+0.904 mV | 2.544 mV | 1.446 mV | 0.284 mV / 2.06 µV |
| logical0 + READ | −0.1026…+0.1205 mV | −0.3169…+0.2728 mV | 0.223 mV | 0.590 mV | 13.4 µV / 0.537 µV |

`V(NJSL11)`（最后一个 JSL 前的 far-side node）在 read window 的范围为：

- logical1 + READ：`−127.33…+84.71 µV`；
- logical0 + READ：`−8.55…+10.05 µV`；
- 两个 controls：约 `±0.067 µV`。

因此 JSL load 的主要可见作用不是让 JSL 本身接近 switching，而是把
read1 的 SL transient 拉出更明显的负 lobe 和 post ringing，同时压低
read0 的 read-window amplitude；这个动态改变必须在后续 ideal replay 中
原样保留。

## 4. BVM source/storage guards

### Observed

- read1/read0 `I(L_SL)` 与 `V(SL1)` 仍有清晰分离：read1 的 current
  p2p 为约 `99.10 µA`，read0 为约 `7.835 µA`；`V(SL1)` p2p 分别约
  `2.544 mV` 和 `0.223 mV`；
- 两个 READ=0 controls 的 JSL read activity 仅 `2.65×10⁻⁵ turn`，
  source current 约 `0.01 µA` 量级，没有 read-like output；
- `V(N6)` read1 p2p `2.837 mV`，与 canonical `2.903 mV` 同量级；
- `JM1/JM2/JS1/JS2` 的 post median 与 canonical baseline 保持接近。

post median 的 loaded-minus-canonical phase（turn）为：

| case | JM1 | JM2 | JS1 | JS2 |
|---|---:|---:|---:|---:|
| logical1 + READ | −4.85×10⁻⁵ | −7.04×10⁻⁴ | +0.00316 | +0.00275 |
| logical0 + READ | −1.50×10⁻⁶ | +4.16×10⁻⁵ | +4.30×10⁻⁵ | +6.60×10⁻⁵ |
| logical1 + READ=0 | 0 | −1.50×10⁻⁷ | +1.20×10⁻⁶ | +1.20×10⁻⁶ |
| logical0 + READ=0 | 0 | +1.50×10⁻⁷ | −1.20×10⁻⁶ | −1.20×10⁻⁶ |

### Guard boundary

read1 的 JS1/JS2 post p2p 分别约 `0.4035/0.4046 turn`，高于 canonical
post p2p；这是 bounded ringing/load disturbance，而不是被忽略的“完全无
back-action”结果。其 settled median 仍接近 baseline，且没有跨一整圈的
JSL transition。本轮因此只支持“逻辑/存储 sign 未明显崩溃且 source
discrimination 保留”，不升级为更强的 nondestructive-read claim。

## 5. Observed / Derived / Inference / Unknown

### Observed

- 四个 raw run 均完成，时间轴严格递增，13,599 行；
- 12 个 JSL branch current 一致；
- 最大 JSL phase activity 为 `0.0693363 turn`，同段 voltage area 与
  phase 一致但远小于一圈；
- read1/read0/control 的 JSL/source amplitudes 分离；
- read1 后存在明显但 bounded 的 SL/N6/JS post ringing；
- storage phase 的 post median 未出现明显 sign/state drift。

### Derived

- 在此 external stack fixture 中，12×`AREA=3.2` JSL 的 read1 最大电流约
  `0.247 Ic`，不足以支持 junction switching；
- JSL stack current 是闭合串联路径的同一电流，不是每颗结独立分流；
- JSL junction inductance 将读出 path 的动态时间尺度从单独 `L_SL` 的
  `0.4 pH` 提升到约 `12.7 pH` 量级（电流修正下的数量级估计）。

### Inference

- 本点支持 `PAPER_JSL_LOAD_VALID`：paper-motivated 12-JSL external load
  可以在 canonical read1/read0 matrix 中保持 non-switching 与 state
  selectivity；
- JSL load 不是“透明负载”。后续 QB waveform replay 必须使用 loaded
  `SL/N6` waveform，不能继续使用 no-receiver waveform；
- 由于 post ringing 增强，若后续接 physical QB，source isolation/back-action
  仍需重新判定，不能由本轮 storage median 直接推出 safe interface。

### Unknown

- 论文第 2.5 节的 internal `L_SL` replacement topology 在当前 canonical
  BVM 上的独立 waveform 是否与本 external-load realization 相同；
- loaded waveform 输入 frozen scaled QB 是否改善 BJL1/BJL2 dynamic window；
- JSL 栈在 physical BVM→QB 连接中与 QB input network 的联合 load-line；
- 更长 array 中多个 row-JSL stack 的总 inductance/termination effect。

## 6. Next boundary

按用户预注册的停止规则，本轮不接 QB、不改 QB、不做 scale/bias sweep。下一
轮只能先把本轮 loaded BVM output waveform 作为 ideal replay 输入 frozen
scaled QB，与 QB-Q2A 的 canonical replay 做一对一比较；只有该 replay
显示 BJL1/BJL2 明显改善，才考虑 physical `BVM → 12×JSL → QB`。

