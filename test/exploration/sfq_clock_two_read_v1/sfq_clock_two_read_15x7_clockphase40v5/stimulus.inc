
* CARRY5 full-SFQ clock; 15 x 15; two post-WRITE1 reads.
* ROW_BITS=1111 (R1 LSB); COL_BITS=1111 (C1 MSB).
* Read-active columns: C1, C2, C3, C4; selected crosspoints: 16.
* 50-61p WRITE0 all; 70-81p existing READ0 preconditioning; 90-101p WRITE1 all.
* Counted read #1 110-121p; read #2 310-321p; no intervening write.
* In counted reads all four WLs active; BL=0; only selected cell-local SE active.
I_WL_R1 0 WL_R1 PWL(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 100u 80p 100u 81p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 100u 120p 100u 121p 0 310p 0 311p 100u 320p 100u 321p 0 550p 0)
I_BL_C1 0 BL_C1 PWL(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 0 120p 0 121p 0 310p 0 311p 0 320p 0 321p 0 550p 0)
I_SE_R1C1 0 SE_R1C1 PWL(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p 100u 80p 100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0 201p 100u 210p 100u 211p 0 310p 0 311p 100u 320p 100u 321p 0 550p 0)
