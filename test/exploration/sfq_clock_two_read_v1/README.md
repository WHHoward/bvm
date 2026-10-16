# BVM 4×4 V9 main experiment entry

This directory is the current manual entry point. The old 4×4 platform remains
historical and unchanged. Everything under final_runs/ is retained as immutable
history; new work goes only under runs/.

## Edit one case

Edit USER_CASE.env. The runner requires PROTOCOL=V9_SHARED_ROW_SE_BL and will
hard-stop rather than fall back to the older WL+SE read wiring.

- A and B: unsigned 4-bit inputs, 0–15. R1 maps to A's least-significant bit;
  C1 maps to B's most-significant bit.
- ROUNDS: repeat the same A/B input for 1–64 reads.
- READ_INTERVAL_PS: period between read PWL starts.
- CLOCK_PERIOD_PS: period between clock PWL starts; independently configurable.
- SE_CLOCK_DELAY_PS: first clock PWL start minus FIRST_READ_PS.
- WRITE_START_PS and FIRST_READ_PS: one all-cell WRITE1 start and first read.
- DT_PS and STOP_PS: JoSIM transient step and stop time.
- WL_WRITE_AMPLITUDE, BL_WRITE_AMPLITUDE, BL_READ_AMPLITUDE, and
  SE_READ_AMPLITUDE: source levels. The default SE value 375u is an active user
  candidate, not a validated optimum.
- PROBE_PROFILE=OUTPUTS stores only the eight output voltages. CUSTOM adds only
  the probes named in CUSTOM_PROBES_FILE.

The 80/68 example generates READ starts 110/190/270 ps and CLK PWL starts
178/258/338 ps. The clock values are source start times, not measured internal
clock arrivals. The V9 stimulus performs one WRITE1 of all 16 cells, then reads
with selected column BL and selected row SE together. It does not generate
WRITE0, READ0, or a second write.

## Preview and run

    ./try.sh --dry-run
    ./try.sh

The dry-run renders and validates the deck, PWL, topology, source closure and
probe list in memory. It does not invoke JoSIM, create a run directory, or
reserve an ID. A normal invocation is exactly one physical solve. Each run
gets a non-reused V9R001+ ID under runs/; this namespace is separate from the
retired platform's A001–A112 sequence. Existing raw, log, or run directories
are never overwritten. Solver or post-processing failures remain in their
allocated run directory. The runner does not compute SFQ counts, multiplication
correctness, mechanism, or clock margin.

## View results and add probes

After a successful raw QA and plot, open:

    runs/<RUN_ID>/res.html

It uses scripts/josim-plot2.py with the classic stacked/dark style and includes
all stored rows—no downsampling or resampling. Plotly is embedded in res.html,
so the page is standalone and works offline. Default raw probes are exactly:

    V(S_D0_OUT) ... V(S_D6_OUT), V(DFF_O)

For extra signals, set PROBE_PROFILE=CUSTOM and provide a file path relative to
this directory, for example:

    PROBE_PROFILE=CUSTOM
    CUSTOM_PROBES_FILE=tests/fixtures/custom_probes_sample.txt

Use one JoSIM probe expression per line (blank lines and #/* comments ignored),
such as V(CLK_D0) or P(B_JM1|XBVM_R1C1). The runner checks syntax and resolves
each requested node/element against the rendered deck and frozen subcircuits
before any solve. This is a static grammar/reference check, not a JoSIM parser
execution: the available JoSIM sanity-check switch still runs a transient, so
actual parser acceptance is not claimed without a user-authorized solve.
CUSTOM contains the eight outputs plus only those explicit extra probes; there
is no implicit FULL DEBUG profile. Probes never change electrical topology.

## Evidence, raw access, and Drive archive

Each run keeps deck.cir, stimulus.inc, USER_CASE.snapshot.env, raw.csv,
res.html when plotting is possible, run.log, PREFLIGHT.md, probe_manifest.json,
manifest.json, and sources_frozen/. The raw is directly readable at
runs/<RUN_ID>/raw.csv and is not ignored by Git; it is not deleted after
archiving. The local runs/.gitignore also re-includes per-run JSON manifests
despite the repository-wide JSON ignore rule. Share that path and the run
manifest for later ChatGPT review; commits remain an explicit user/Codex action.

One self-contained ZIP per run is written directly to the configured Google
DriveFS folder, not to a permanent local ZIP or D: mirror:

    G:\.shortcut-targets-by-id\1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh\BVM_Backages

The WSL mount form expected by this platform is
/mnt/g/.shortcut-targets-by-id/1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh/BVM_Backages.
There is no alternate-path fallback. An actual run performs an exclusive
write/read/unlink preflight before reserving an ID or invoking JoSIM; if that
exact folder is unavailable, the physical solve does not start. The ZIP is
first written under a unique temporary name in the target folder, checked for
CRC and every member SHA, then renamed to its unique final name. The final
DriveFS path bytes are SHA-checked. The run manifest reports the Drive folder
ID, path, file name and ZIP SHA; the shell does not invent a Drive file ID or
claim cloud-sync verification from a local filesystem read. If a Drive API
metadata check is not available, the manifest explicitly leaves remote sync
unconfirmed.

No raw-only or metadata-only companion ZIP is created. The single archive
contains the run config, deck, PWL, frozen source closure, log, raw and
standalone visualization. No physical run or archive is created by dry-run.

## Static tests

    python3 -m unittest discover -s tests -v

Tests use rendered configurations and synthetic CSV only; they never invoke
JoSIM. They include the V9 topology equivalence check and exercise the archive
writer in a temporary directory, not in Drive.
