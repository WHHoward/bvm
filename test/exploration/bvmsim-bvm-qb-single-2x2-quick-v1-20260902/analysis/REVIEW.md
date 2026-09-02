# Numerical and adversarial review

## Scope

这是对 `BVM_QB_SINGLE_BVMSIM_BVM_TO_QB_MATCHED_2X2_QUICK_V1` 的 exploratory review。它不改变 raw、netlist、事件规则或共享工具，不将结果升级为 Formal Gate。

- Requested base HEAD: `61627bdaf1c76395106ddbcabfcae572a5920ebd`
- Pre-registered setup commit: `e3fce35`
- Four-condition attempt: `A001`
- Historical BVM authority: `BVMSim/bvm_cell.cir` only
- Canonical BVM was not used

## Artifact and topology checks

| check | result |
|---|---|
| JoSIM execution | four conditions exit code 0 |
| raw QA | all `VALID`; no NaN/Inf; strictly increasing time |
| samples | 7999 per condition |
| saved interval | 0 to 199.975 ps |
| grid relation | all four grids exactly identical; no interpolation |
| requested nominal step | 0.025 ps; one stored 0.05 ps interval per raw is reported, not hidden |
| active BVM instances | 1 per deck |
| terminal sensing-line JJ count | 11 `B_LD4` plus `BVMout` = 12 |
| JTL conditions | six `jtl` instances; direct conditions have none |
| raw overwrite | none; `runs/A001/*/raw.csv` are separate files |

The raw headers contain the required BVM, QB, JTL P/V probes and QB current branches, including `RJ1`, `RJ2`, and `I_QB_BIAS`. The duplicate-column-sensitive shared reader was used; these new raw headers have no duplicate labels.

## Numerical review

The local candidate algorithm uses the preregistered voltage activity and quiescent-gap thresholds. Phase is continuous-unwrapped raw JoSIM radians; turns are `Δrad/(2π)`. Voltage area uses the same candidate endpoints, same JJ direct voltage, and the actual stored time grid.

Independent recheck (`analysis/independent_recheck.py`) reported:

- maximum candidate phase arithmetic difference: `2.778e-19` turns;
- maximum candidate voltage-area arithmetic difference: `4.441e-16` turns;
- maximum QB KCL residual: `1.400e-04 µA`.

The KCL equations follow the declared BQ orientation:

1. `I(Lin) - I(BJs) = 0` at QB node 1;
2. `I(BJs) - I(BJ1) - I(RJ1) - I(L1) = 0` at QB node 2;
3. `I(L1) + I(QB bias) - I(L2) = 0` at BIAS;
4. `I(L2) - I(BJ2) - I(RJ2) - I(L3) = 0` at QB node 4.

The largest residual is numerical-scale relative to the approximately 100–250 µA branches. This validates current-partition arithmetic for this analysis; it does not validate a physical mechanism.

## Event and boundary review

- No full-trace candidate was cut at a write/read boundary. Candidate endpoints remain the voltage-activity segment endpoints; windows are only onset/context associations.
- The S1-R BJ2 candidate spans approximately `0.175..95.3 ps`; the S1-J BJ2 candidate spans approximately `0.15..104.2 ps`. Both have phase/area agreement but no pre/post retrap, so each is one continuous candidate rather than multiple clean events.
- S1-R and S1-J first complete QB-chain candidate is at BJ1, before the READ window. This is a spontaneous/initial-bias timing observation, not read attribution.
- The JTL B01/B02 traces in S1-J each contain one complete long segment and zero clean separated events at all six stages. Similar onset timing around the initial bias activity cannot establish stage-to-stage discrete-event latency.

## Adversarial checks

| hidden-failure hypothesis | probe | result |
|---|---|---|
| wrong topology/no-op load change | deck topology count and explicit `xjtl1_1..xjtl1_6` inspection | direct/JTL distinction is present; terminal count remains 12 |
| stale or shared raw authority | per-condition run directories, command files, raw hashes | four independent raw paths and hashes are recorded |
| phase-only event inflation | same-JJ phase plus voltage area plus retrap | no clean separated event is reported; long segments remain one candidate |
| read-window boundary manufacture | full-trace candidate endpoints plus onset contexts | early candidates cross context windows and are not truncated |
| hidden QB branch imbalance | four KCL equations and independent recheck | residual max `1.40e-04 µA`; no missing printed branch in the equations |
| JTL transport overclaim | B01 and B02 at all six stages, clean count and onset | clean count is 0 at every stage; only continuous activity is observed |
| load backaction ignored | exact-grid BJ2 phase/voltage comparison in READ | S1 phase max/RMS difference `0.5643/0.2230` turns; S0 `0.00455/0.00189` turns |

## Review disposition

- Artifact validity: `VALID`.
- Physical classification: `CONTINUOUS_MULTI_TURN_RUNNING_STATE` for this fixture, freshly derived from A001 raw evidence and the current task-local event rule; it is not copied from the old Stage-A report.
- Quick label: `QUICK_OPPOSITE_OR_AMBIGUOUS`.
- Scientific claim strength: exploratory only; no Formal PASS language.
- Remaining uncertainty: the current 2×2 does not isolate the BVM contribution from early 250 µA QB/JTL bias activity, and no timestep convergence or alternate bias control was authorized.

## Commands and exit codes

| command | exit |
|---|---:|
| `./run.sh A001` | 0 |
| `python3 analysis/test_analyze.py` | 0 |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools/test_bvmtools.py` | 0; 23 passed |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/plot/test_josim_plot2.py` | 0; 5 passed |
| `python3 analysis/independent_recheck.py` | 0 |
| `python3 analysis/plot.py --timestamp 2026-09-02T16:58:41+08:00` | 0; 5 HTML pages |

No additional experiment is authorized by this review. The human gate remains open.
