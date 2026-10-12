# 15x7 / 20 GHz exploratory two-read trial

Base: exact archived `sfq_clock_two_read_15x7_dt001.zip` in Google Drive, under `test/exploration/sfq_clock_two_read_v1/`.
Place this folder alongside the original directory to keep `.include ../../../../circuits/...` valid.

- WRITE0 50–61 ps, READ0 70–81 ps, WRITE1 90–101 ps: unchanged.
- Read1 110–121 ps, Read2 160–171 ps (50 ps between read starts).
- Eight PWL trigger chains: 150–154 ps and 200–204 ps (50 ps trigger interval).
- End time 550 ps and `.tran 0.01p 550p`: unchanged.
- T1/CB/SFQ device models, connectivity, bias values: unchanged.
- All original probes preserved; twelve previously commented/absent `V(T1_I_Dk)`/`V(C_Dk)` probes enabled for k≠3; overview HTML still shows only eight output signals through existing `run.sh -s`.
- Input 15x7, expected decimal product: 105.

Execute `bash run.sh` from inside this folder in the Git checkout after checking JoSIM is installed.
`run.sh` overwrites the `data_tran.csv` and `res.html` in this new folder; originals remain archived separately.

Do not take nominal 20 GHz clock spacing as validated whole-system 20 GHz throughput; verify independent output pulses, pipeline collision, BVM state, carry, DFF and timing.
