# Execution record

- parent accepted HEAD: `8bb86f61c3243655467d61f00680977349b41cf3`
- repository: `/home/howard/JoSIM`
- binary: `build/josim-cli`
- version: `JoSIM v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- command per run: `build/josim-cli -o raw/<fixture>/<dt>/run.csv inputs/<fixture>/<dt>/main.cir`
- requested timesteps: `0.025 ps`, `0.0125 ps`, `0.00625 ps`
- stop times: R11 `170 ps`; pulse-5 replay `300 ps`
- jobs: 9; each exit code `0`; each has direct four-JJ `P/V/I` probes
- analysis: `analysis/analyze_numerical_freeze.py`
- no JTL topology, model, bias, source waveform, polarity, or load parameter was changed

The W−/W0/W+ window variants are analysis-only views of the same raw files;
they do not create additional JoSIM runs.
