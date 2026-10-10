# D3 Carry timing preflight revision 3

Attempts 001 and 002 are preserved and superseded before any physical solve. Attempt 001's raw-size projection used a net probe-count delta. Attempt 002 corrected the estimate but required two commits to force-stage ignored machine-readable JSON, which violated the direct-parent execution lock. Attempt 003 uses the corrected per-signal width estimate and all lock files will be committed atomically in one preflight commit.

- Attempt 001 PREFLIGHT SHA-256: `bdbb75907bd6a8d55942cf8b0f01a96a70e02f689055ef6a6b4b6b2b2dc08a1a`
- Attempt 001 STATIC_QA SHA-256: `1dcd30bb125665fc1df742df66dea676fb25a8857292d25862a402dc8f787620`
- Attempt 002 PREFLIGHT SHA-256: `f01c30067112b09bf28fea8f441de6c85579261cfc342dc7ca5022476dec04f3`
- Attempt 002 STATIC_QA SHA-256: `375a7a383931b690766878750a544af9af1bfaa9e4c6174705a6907608dff4b7`
- Physical solves completed in attempts 001/002: 0
- Historical raw/deck/config files were not modified.
