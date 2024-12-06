#!/bin/bash

# 循环遍历 seq_length 从 240 到 2400，步长为 240
for seq_length in $(seq 120 120 720)
do
    # 循环遍历 judge_length 从 120 到 480，步长为 120
    for judge_length in $(seq 240 120 720)
    do
        # 调用 Python 脚本并传递参数
        echo "Running experiment with seq_length=$seq_length and judge_length=$judge_length -e 3001"
        python model_train.py --seq_length $seq_length --judge_length $judge_length -e 3001
    done
done
