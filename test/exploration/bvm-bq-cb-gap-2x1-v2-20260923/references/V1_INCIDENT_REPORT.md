# Preflight execution incident

Status: `ABORTED_PENDING_USER_DIRECTION`.

On 2026-09-23 at 17:58:43 +08:00, the preflight helper invoked JoSIM with
`--sanitycheck`, incorrectly assuming that it only parsed the circuit. The
command returned 0 but also started and completed a transient solve of a
temporary `N0_00` preview deck. It was not launched by the registered
`run_matrix.py` workflow and is not accepted as experiment evidence.

The transient output reported:

```text
Unknown device/node ACC2_OUT
Cannot store results for this device/node.
Ignoring this store request.
```

The deck and stimulus hashes observed in the preflight report were:

- Deck: `ba358f88979dde96257e2330410038d1f77a964b71aeed6b190385dec3a8ea56`
- Stimulus: `0df75c3e5a050a2a9fc75b4d622cc8f5d42535a6a3071686c4212d3d9d528f5d`
- Solver `build/josim-cli`, v2.7.2837d13, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

Temporary directory `/tmp/bvm_gap_sanity_3kkocwsj` was automatically removed
after the command, so its raw and logs could not be retained. No registered
`runs/N*` folder or accepted raw file exists. The probe was corrected: `XACC2`
connects directly to `GAP2_IN`, so the proper voltage probe is `V(GAP2_IN)`;
`I(L2|XACC2)` preserves its separate branch current.

The preflight no longer invokes JoSIM. This experiment directory is now
hard-disabled for source-lock creation and physical solves. A new versioned
experiment requires explicit user direction.
