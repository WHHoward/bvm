# Preserved failed attempt

The first generated passive decks failed mechanical preflight because the
quiet-cell `BL` and `SE` PWL templates did not reproduce the registered
zero-state-read segment before the final READ. No solver was invoked and no
raw file was created. The failed preflight record, source manifest, and the
N2 deck are retained here; the final experiment artifacts use the corrected
templates and a new generation pass.
