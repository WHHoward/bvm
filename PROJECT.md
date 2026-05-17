# JoSIM BVM + QB 仿真项目文档

> **项目目标**: 在 JoSIM 中复现超导存储器 BVM 和量化缓冲器 QB 电路，验证论文方案
> **仿真器**: [JoSIM](https://github.com/JoeyDelp/JoSIM) v2.7 | **工艺**: MITLL SFQ5ee

---

## 目录结构

```
JoSIM/
├── circuits/                    # 电路库（可复用子电路）
│   ├── bvm/bvm_cell.cir         # BVM 存储单元子电路（论文 Fig.2b）
│   ├── qb/bq_cell.cir           # BQ 量化缓冲器子电路（Synapse 论文 Fig.4）
│   ├── t1/                      # （预留）T1 加法器
│   └── models/mitll_models.cir  # MITLL SFQ5ee 约瑟夫森结模型
│
├── test/
│   ├── final/                   # ★ 最终测试与结果
│   │   ├── REPORT.md            # 完整实验报告
│   │   ├── SUMMARY_FINAL.md     # 项目总结
│   │   ├── bvm/                 # BVM 独立功能测试
│   │   ├── qb/                  # QB 独立功能测试
│   │   ├── final_4bvm_series.cir/.csv  # 4BVM+QB 串联基线测试
│   │   ├── isolate_js18.cir/.csv       # 隔离测试：单BVM JS=18μA
│   │   ├── isolate_js25.cir/.csv       # 隔离测试：单BVM JS=25μA
│   │   ├── series_js25.cir/.csv        # 4BVM JS=25μA R=10Ω
│   │   ├── series_r7.cir/.csv          # R_shunt 扫描 7Ω
│   │   ├── series_r12.cir/.csv         # R_shunt 扫描 12Ω
│   │   ├── series_r15.cir/.csv         # R_shunt 扫描 15Ω
│   │   ├── qb_multilevel.cir/.csv      # QB 多级输入独立测试
│   │   └── *.html *.py                 # 可视化文件
│   ├── bvm/                     # BVM 早期测试与可视化
│   ├── bq/                      # BQ 早期测试与可视化
│   ├── comp/                    # 基础元件测试
│   ├── param/ syntax/           # 参数/语法测试
│   └── ex_*.cir                 # JoSIM 示例电路
│
├── circuits/bvm/bvm_cell.cir    # BVM 子电路定义
├── circuits/qb/bq_cell.cir      # QB 子电路定义
├── library_josim/               # JoSIM 标准单元库
├── scripts/                     # Python 辅助脚本
├── src/ include/                # JoSIM C++ 源码
├── build/                       # 编译产物
└── docs/                        # JoSIM 官方文档
```

---

## 核心电路

### 1. BVM（双稳态涡旋存储器）

**文件**: `circuits/bvm/bvm_cell.cir`
**参考**: Karamuftuoglu et al., *Supercond. Sci. Technol.* 38 015020 (2025)

BVM 是一个双 SQUID 环超导存储单元：
- **S-Loop（存储环）**: JM1(120μA) + JM2(140μA) 形成双稳态涡旋态，存储逻辑 0/1
- **R-Loop（读出环）**: JS1/JS2(74μA) 感应存储态并输出读出电流
- **端口**: WL(写字线), BL(位线), SE(敏感线), SL(读出线)
- **操作**: WL+BL 同时激活→写入，SE 激活→读出，WL/BL 单独激活→半选（不影响状态）

### 2. QB/BQ（量化缓冲器）

**文件**: `circuits/qb/bq_cell.cir`
**参考**: Razmkhah et al., *Supercond. Sci. Technol.* 37 065011 (2024)

QB 是一个类似数字 SQUID 的电路：
- **JS**: 串联约瑟夫森结，感应输入电流并累积相位
- **JL1/JL2**: 并联支路结，提供偏置路径
- **IBias**: 偏置电流，走 JL1→RB→JL2 支路
- **R_shunt (C1 优化)**: JS 两端并联电阻，降低 βc，抑制 LC 振荡

### 3. MITLL SFQ5ee 结模型

**文件**: `circuits/models/mitll_models.cir`

| 模型名 | IC (μA) | RN (Ω) | 用途 |
|--------|---------|--------|------|
| jj120 | 120 | 2.0 | BVM JM1 |
| jj140 | 140 | 1.8 | BVM JM2 |
| jj74 | 74 | 3.5 | BVM JS1/JS2 |
| jj320 | 320 | 0.8 | SL 负载端接 |
| jj112 | 112 | 2.2 | QB JL1 |
| jj189 | 189 | 1.3 | QB JL2 |

---

## 关键实验结果

### BVM 单元（独立验证）— 全部通过

| 功能 | 结果 |
|------|------|
| 写入 W1 | P_JM1 = +13.4 rad (2.1Φ₀) |
| 写入 W0 | P_JM1 翻转至负值 |
| 读出 R1 | I_SL = 32.3 μA |
| 读出 R0 | I_SL ≈ 12.6 μA |
| R1/R0 区分度 | 2.5-2.6× |
| 半选保护 | ΔP_JM1 < 1 rad |
| NDRO | 读后相位不变 |

### QB 单元（独立验证 + C1 优化）

| 输入电流 | 相位累积 |
|---------|---------|
| 32 μA (等效 1 BVM) | 1.0 Φ₀ |
| 64 μA (等效 2 BVM) | 2.4 Φ₀ |
| 96 μA (等效 3 BVM) | 3.6 Φ₀ |
| 128 μA (等效 4 BVM) | 5.3 Φ₀ |

注：以上为 10ps 理想电流脉冲输入，相位为准离散（非真正的 2π 整数跳变）。

### 4BVM 阵列 + QB 串联

| 配置 | Read1 I_SL | Read4 I_SL | Read4 Φ₀ | 相位重置 |
|------|-----------|-----------|----------|---------|
| JS=18μA R=10Ω | 16.9 | 56.1 | 1.55Φ₀ | 差 |
| JS=25μA R=7Ω | 19.5 | 73.3 | 0.80Φ₀ | 优 |
| JS=25μA R=15Ω | 18.2 | 59.6 | 1.00Φ₀ | 中 |

**串联拓扑**: SL → jj320 → QB → GND（所有电流经过 QB，19× 强于并联拓扑）

---

## 如何运行测试

```bash
# 编译 JoSIM（如需要）
cd build && cmake .. && make -j$(nproc)

# 运行单个测试
cd test/final
josim-cli isolate_js18.cir -o isolate_js18.csv

# 生成可视化
python3 plot_comprehensive.py

# 运行 JoSIM 内置测试套件
cd build && ctest
```

## 如何添加新结模型

在 `circuits/models/mitll_models.cir` 中添加：
```spice
.model jjXXX jj(RTYPE=1, IC=XXXU, RN=X.X, R0=X.X, CAP=X.XP, VG=2.8M, DELV=0.1M)
```
参数估算：RN ≈ 0.25mV / IC，R0 ≈ 3×RN，CAP 使 βc ≈ 1（βc = 2π·IC·RN²·C/Φ₀）

---

## 已知限制

1. **QB 无离散 SFQ 脉冲**: 10ps BVM 脉宽太短，JS 结来不及完成 2π 转换
2. **V_OUT 始终为零**: JL2 结从未触发
3. **多 BVM 单读漏电**: 非读取 BVM 的 R-loop 提供超导旁路（整列同时读无此问题）
4. **相位连续累积**: 即使 C1 优化后仍是准离散，非真正的 2π 整数跳变

## 参考论文

- BVM: Karamuftuoglu et al., *Supercond. Sci. Technol.* 38 015020 (2025)
- BQ: Razmkhah et al., *Supercond. Sci. Technol.* 37 065011 (2024)
- MVM: Karamuftuoglu et al., arXiv:2507.04648 (2025)
