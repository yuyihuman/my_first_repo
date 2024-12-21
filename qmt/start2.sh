#!/bin/bash

# 定义时间范围
start_time=20120101
stop_time=20201230

for val_acc_criteria in $(seq 0.93 0.01 0.95)
do
    # 循环遍历 seq_length 从 360 到 360，步长为 120
    for seq_length in $(seq 240 120 480)
    do
        # 循环遍历 judge_length 从 480 到 480，步长为 240
        for judge_length in $(seq 240 240 720)
        do
            # 调用 Python 脚本并传递参数
            echo "Running experiment with seq_length=$seq_length, judge_length=$judge_length, val_acc_criteria=$val_acc_criteria, epochs=3001"
            python model_train.py --seq_length "$seq_length" --judge_length "$judge_length" \
                --val_acc_criteria "$val_acc_criteria" -e 3001 -sd "$start_time" -ed "$stop_time"
            
            python backtrader_test.py -m "final_model_${val_acc_criteria}_${seq_length}_${judge_length}.pth" \
                -sd "$start_time" -ed "$stop_time"
        done
    done
done
