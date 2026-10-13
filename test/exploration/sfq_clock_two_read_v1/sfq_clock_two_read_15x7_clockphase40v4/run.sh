#!/bin/bash

#FILE_PATH="data_tran.csv"
#FILE_PATH="data_tran_0.05.csv"
#FILE_PATH="data_tran_0_0.05_v1.csv"
FILE_PATH="data_tran.csv"

echo "Run JoSIM sim..."
# josim-cli -o $FILE_PATH BQ_test.cir
# josim-cli -o $FILE_PATH single_bvm_qb.cir
# josim-cli -o $FILE_PATH test_bvm.cir
# josim-cli -o $FILE_PATH test_bvm_mixed.cir
#josim-cli -o $FILE_PATH test_bvm_mixed_0.cir
#josim-cli -o $FILE_PATH test_bvm_mixed_0_0.05.cir
#josim-cli -o $FILE_PATH test_bvm_mixed_0_0.05_v1.cir
josim-cli -o $FILE_PATH deck.cir
# josim-cli test_bvm_mixed.cir

if [ $? -eq 0 ]; then
  echo "complete and deal data..."
  python3 josim-plot.py "$FILE_PATH" -t stacked -x res.html \
  -s \
  "V(S_D0_OUT)" "V(S_D1_OUT)" "V(S_D2_OUT)" "V(S_D3_OUT)" \
  "V(S_D4_OUT)" "V(S_D5_OUT)" "V(S_D6_OUT)" "V(DFF_O)"
  python3 josim-plot.py "$FILE_PATH" -t stacked -x qb.html \
  -s \
  "P(BJ1|XBQ_R1C4)" "P(BJ2|XBQ_R1C4)" "P(BJ3|XBQ_R1C4)"
else
  echo "find errors..."
  exit

fi

echo ""
echo "**** ok ****"