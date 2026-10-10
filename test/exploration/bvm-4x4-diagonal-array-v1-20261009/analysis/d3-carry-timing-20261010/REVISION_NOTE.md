# D3 Carry timing preflight revision 2

Attempt 001 passed topology/syntax/render checks but its raw-size projection used only a net probe-count delta. It is preserved at the task root and superseded before any physical solve. Attempt 002 projects each added and removed signal separately, uses the maximum observed A036 numeric field width plus four spare characters, counts delimiters, and adds a 4 KiB header allowance.

- Attempt 001 PREFLIGHT SHA-256: `bdbb75907bd6a8d55942cf8b0f01a96a70e02f689055ef6a6b4b6b2b2dc08a1a`
- Attempt 001 STATIC_QA SHA-256: `1dcd30bb125665fc1df742df66dea676fb25a8857292d25862a402dc8f787620`
- Attempt 001 WORK_UNIT SHA-256: `e11ede826449aed3cd997b64f870f6dafa0ae38f9a0f1170848d5c89efd1297c`
- Physical solves completed in attempt 001: 0
- Historical raw/deck/config files were not modified.
