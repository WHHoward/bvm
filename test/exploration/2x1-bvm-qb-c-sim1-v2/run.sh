#!/bin/bash

FILE_PATH="data_tran.csv"

echo "Run JoSIM sim..."
# josim-cli -o $FILE_PATH BQ_test.cir
# josim-cli -o $FILE_PATH single_bvm_qb.cir
josim-cli -o $FILE_PATH deck.cir
# josim-cli -o $FILE_PATH test_bvm_mixed.cir
# josim-cli -o $FILE_PATH test_bvm_mixed_0.cir
# josim-cli -o $FILE_PATH test_bvm_mixed_1.cir
# josim-cli test_bvm_mixed.cir

if [ $? -eq 0 ]; then
  echo "complete and deal data..."
  python3 josim-plot-v2.py "$FILE_PATH" -t stacked -x 111.html
else
  echo "find errors..."
  exit

fi

echo ""
echo "**** ok ****"