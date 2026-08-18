# Internal adversarial and numerical review

**Review time:** 2026-08-19T04:21:52+08:00
**Scope:** R0 Exploration only; this is not a Copilot/Sol audit.

## Strongest bounded claim under review

At the declared model, SL load, bias, input timing, requested timestep, and
170 ps run length, the one-JJ receiver shows trigger-level discrimination:
read1 has a clear local switching/phase-transition excursion, read0 remains
edge-dominated, and both READ=0 controls remain bias-only.

## Adversarial probes

| Hidden-error hypothesis | Independent probe | Result |
|---|---|---|
| Stale or wrong BVM/model branch | SHA-256 of fixture snapshots versus canonical files; inspect include closure | PASS: BVM and jjmit fixture hashes equal current canonical hashes |
| No-op or constant-output receiver | Compare direct trigger P/V and branch-current traces across read1, read0, and controls | PASS: read1/read0/control amplitudes differ by large factors |
| Weak oracle counts phase samples as SFQ | Recompute raw trigger phase range, endpoint delta, and same-JJ voltage area independently | PASS: no event count is used; net turns are explicitly labelled net quantities |
| Wrong current direction or hidden branch | Check KCL I(B_TRIG) = I(R_IN)+I(I_TRIG_BIAS), and compare I(R_IN) with I(L_SL) | PASS: activity-window KCL residual <= 1e-11 A; R_IN and L_SL agree to printed precision |
| READ=0 control accidentally contains READ | Inspect control netlists and independent trigger maxima | PASS: control read sources are zero; trigger phase range <= 0.001210 rad and voltage peak <= 0.431 uV |
| Loading destroys the BVM state/read discrimination | Recompute SL, N6, JS1/JS2 activity and JM1/JM2 PRE-to-POST deltas | PASS for this bounded fixture; read1/read0 separation remains |
| Report upgrades a local event into SFQ/JTL success | Search report claim boundary and unknown list | PASS: report excludes SFQ count, exactly-one, JTL, self-quench, Candidate, and Gate claims |

## Independent numerical cross-check

The cross-check was recomputed directly from each raw CSV, not from
analysis/r0-analysis.json:

| Case | phase range | endpoint delta / 2pi | V-area / Phi0 | area minus phase | actual dt |
|---|---:|---:|---:|---:|---:|
| read1 | 3.672452 rad | 0.0123121309 turns | 0.0123144603 turns | 2.33e-6 turns | 0.0125–0.025 ps |
| read0 | 1.1431775 rad | 0.0240018387 turns | 0.0240058333 turns | 3.99e-6 turns | 0.0125–0.025 ps |
| logical1 READ=0 | 0.0004929 rad | -3.5189e-5 turns | -3.5192e-5 turns | -3.09e-9 turns | 0.0125–0.025 ps |
| logical0 READ=0 | 0.0012099 rad | 7.3625e-5 turns | 7.3648e-5 turns | 2.30e-8 turns | 0.0125–0.025 ps |

The phase/area comparison uses B_TRIG only, the same N_TRIG-to-ground
direction, the same 94–130 ps window, and the actual CSV time column.
The small displayed residuals are consistent with printed phase precision and
window endpoint arithmetic; no acceptance tolerance is invented from them.

## Numerical review checklist

| Check | Disposition | Evidence |
|---|---|---|
| Units | PASS | raw time is seconds; report converts to ps; P is rad; turns divide by 2*pi; V-area divides by Phi0 |
| Sign/direction | PASS | B_TRIG direction is N_TRIG -> 0; signed read-edge currents remain visible |
| Integration | PASS | trapezoidal integration over actual CSV time |
| Window definition | PASS | PRE 80–90 ps, activity 94–130 ps, storage POST 140–150 ps, post 140–170 ps |
| Artifact QA | PASS | four valid CSVs, 13,599 rows each, finite and strictly increasing |
| Threshold semantics | PASS | 50 uA is the designed trigger Ic; no over-threshold sample count is called an event |
| Convergence | UNKNOWN | only requested 0.0125 ps run; no 0.025/0.00625 ps classification study |
| Sensitivity | UNKNOWN | no parameter, temperature, load, or longer-stop sweep |

## Residual uncertainty

The strongest remaining ambiguity is physical vocabulary: the read1 trigger
has a large finite local voltage/phase excursion but its net phase and
same-window voltage area are only about 0.0123 turns because the trace contains
opposite lobes. The review therefore supports the declared trigger-level R0
claim, not a quantized SFQ claim.

**Internal review disposition:** PASS with bounded scope; retain the
Exploration label and do not upgrade to Candidate or any system Gate.
