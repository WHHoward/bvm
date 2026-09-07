# Tooling incident SETUP-01

- Time: `2026-09-07T13:11:46+08:00` setup attempt
- Failure: the first `generate_decks.py` invocation compared the downstream block from `XBQ1` through `.tran`, unintentionally including the fixture-specific control sources.
- Effect: setup exited before writing the source manifest; no solver was started and no raw file was produced.
- Correction: the next generator revision compares only the frozen receiver block `XBQ1` through `R_TERM`.
- Physics status: no registered netlist, topology, parameter, timing, solver, or probe content was changed.
