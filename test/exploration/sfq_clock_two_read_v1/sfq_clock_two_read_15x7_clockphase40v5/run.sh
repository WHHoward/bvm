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

  python3 josim-plot.py "$FILE_PATH" -t stacked -x bvm_res.html \
  -s \
  "V(SJTL_OUT_D0_L1)" "V(SJTL_OUT_D1_L2)" "V(SJTL_OUT_D2_L3)" "V(SJTL_OUT_D3_L4)" \
  "V(SJTL_OUT_D4_L3)" "V(SJTL_OUT_D5_L2)" "V(SJTL_OUT_D6_L1)"

  python3 josim-plot.py "$FILE_PATH" -t stacked -x t1_in.html \
  -s \
  "V(T1_I_D0)" "V(T1_I_D1)" "V(T1_I_D2)" "V(T1_I_D3)" \
  "V(T1_I_D4)" "V(T1_I_D5)" "V(T1_I_D6)" "V(DFF_IN)"

  python3 josim-plot.py "$FILE_PATH" -t stacked -x carry.html \
  -s \
  "V(C_D0)" "V(C_D1)" "V(C_D2)" "V(C_D3)" \
  "V(C_D4)" "V(C_D5)" "V(DFF_IN)" 

  python3 josim-plot.py "$FILE_PATH" -t stacked -x t1_merge.html \
  -s \
  "V(CARRY_CB_IN_D1)" "V(CARRY_CB_IN_D2)" "V(CARRY_CB_IN_D3)" \
  "V(CARRY_CB_IN_D4)" "V(CARRY_CB_IN_D5)" "V(CARRY_CB_IN_D6)" 
else
  echo "find errors..."
  exit

fi

echo ""
echo "**** ok ****"