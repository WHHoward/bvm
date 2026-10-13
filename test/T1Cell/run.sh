#!/bin/bash

FILE_PATH="data_tran.csv"

echo "Run JoSIM sim..."
# josim-cli -o $FILE_PATH MutiFlux_cell_jtl.cir
# josim-cli -o $FILE_PATH cycle_cell1.cir
# josim-cli -o $FILE_PATH tff3_ring_v2.cir
# josim-cli -o $FILE_PATH single_bvm_qb.cir
# josim-cli -o $FILE_PATH cycle_cell_zzx_0623-2.cir
josim-cli -o $FILE_PATH tb_t1_cell.cir

if [ $? -eq 0 ]; then
  echo "complete and deal data..."
  python3 josim-plot.py "$FILE_PATH" -t stacked -x res.html
else
  echo "find errors..."
  exit

fi

echo ""
echo "**** ok ****"