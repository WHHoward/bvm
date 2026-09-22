* CONTROL_ONLY fixture; mask=0000; BVM1..BVM4 sources are identical external control paths.
* IDLE [0,50); WRITE0 [50,61); settle [61,70); CONTROL [70,81); zero [81,120).
* No WRITE1 and no FINAL READ. All times are exact registered PWL points.
I_WL1 0 WL1 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_BL1 0 BL1 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 120p 0)
I_SE1 0 SE1 pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_WL2 0 WL2 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_BL2 0 BL2 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 120p 0)
I_SE2 0 SE2 pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_WL3 0 WL3 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_BL3 0 BL3 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 120p 0)
I_SE3 0 SE3 pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_WL4 0 WL4 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
I_BL4 0 BL4 pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 120p 0)
I_SE4 0 SE4 pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 120p 0)
