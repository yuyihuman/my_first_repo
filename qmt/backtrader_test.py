import time
import pandas as pd
import backtrader as bt
import argparse
import numpy as np
import torch
import sys
import io
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# 禁用显示功能
plt.show = lambda: None
import concurrent.futures
import logging
from datetime import datetime
from xtquant import xtdata
from model_train import *

if __name__ == '__main__':
    # 获取当前时间
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 设置日志文件路径
    log_filename = f"log_backtrader.txt"
    log_file_path = os.path.join("log", log_filename)
    # 确保log目录存在
    os.makedirs("log", exist_ok=True)
    # 配置logging，将输出重定向到日志文件
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s', filename=log_file_path, filemode='a')
    # 将stdout和stderr重定向到日志文件
    sys.stdout = open(log_file_path, 'a', encoding='utf-8')
    sys.stderr = sys.stdout

    parser = argparse.ArgumentParser(description="")
    parser.add_argument('-m', '--model', type=str, default="final_model_0.95_120_720.pth", help="指定模型名称")
    parser.add_argument('-sd', '--start_date', type=str, default="20140101", help="开始时间")
    parser.add_argument('-ed', '--end_date', type=str, default="20180101", help="结束时间")
    parser.add_argument('-mode', '--mode', type=str, default="predict", help="predict/truth")
    parser.add_argument('-p', '--plot', type=str, default="False", help="True/False")
    parser.add_argument('-clb', '--code_list_backtrader', type=str, default="", help="回测代码列表")
    args = parser.parse_args()
    code_list_backtrader = args.code_list_backtrader.split(",") if args.code_list_backtrader else []
    logging.info(code_list_backtrader)

    # 检查模型文件是否存在
    if not os.path.exists(args.model) and args.mode == "predict":
        logging.info(f"Error: Model file '{args.model}' does not exist.")
        sys.exit(0)  # 非零值表示异常退出
    else:
        logging.info(f"Info: Use Model file {args.model}")

    input_length, hold_cycles, accuracy = get_model_para(model_name=args.model)
    input_size = 2
    hidden_size = 64
    model = RNNModel(input_size, hidden_size, input_length)

    chunk_size = 20
    tasks = [(code, input_length, hold_cycles, accuracy, args.start_date, args.end_date, "backtest") for code in code_list_backtrader]
    tasks_chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]  
    for tasks_chunk in tasks_chunks:
        with multiprocessing.Pool(chunk_size) as pool:
            pool.starmap(process_stock_data_backtest, tasks_chunk)