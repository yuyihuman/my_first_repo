import os
import argparse
import subprocess

from data_prepare import get_stock_list
from xtquant import xtdata

# 定义命令行参数
parser = argparse.ArgumentParser(description="Run experiments with varying parameters.")
parser.add_argument("-sd", "--start_date", type=str, required=True, help="Start date in YYYYMMDD format")
parser.add_argument("-ed", "--end_date", type=str, required=True, help="End date in YYYYMMDD format")

args = parser.parse_args()
start_time = args.start_date
stop_time = args.end_date
code_list = get_stock_list(lower_bound=150,upper_bound=180)
code_list_str = ",".join(map(str, code_list))

# 自定义 frange 函数，用于生成浮点数范围
def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step

# 循环参数范围
val_acc_criteria_range = [round(x, 2) for x in list(frange(0.93, 0.95, 0.01))]
seq_length_range = range(240, 481, 120)
judge_length_range = range(240, 721, 240)

start_time=args.start_date
end_time=args.end_date
period="1m"
total_stocks = len(code_list)
xtdata.enable_hello = False
## 为了方便用户进行数据管理，xtquant的大部分历史数据都是以压缩形式存储在本地的
## 比如行情数据，需要通过download_history_data下载，财务数据需要通过
## 所以在取历史数据之前，我们需要调用数据下载接口，将数据下载到本地
for index, code in enumerate(code_list):
    # 打印进度
    print(f"Downloading {code} ({index + 1}/{total_stocks})...")
    # 下载数据
    xtdata.download_history_data(code, period=period, incrementally=True, start_time=start_time)
    # 打印已完成的进度
    print(f"{code} download completed.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")

# 循环遍历参数
for val_acc_criteria in val_acc_criteria_range:
    for seq_length in seq_length_range:
        for judge_length in judge_length_range:
            print(f"Running experiment with seq_length={seq_length}, judge_length={judge_length}, "
                  f"val_acc_criteria={val_acc_criteria}, epochs=3001")
            
            # 执行 model_train.py 脚本
            subprocess.run([
                "python", "model_train.py",
                "--seq_length", str(seq_length),
                "--judge_length", str(judge_length),
                "--val_acc_criteria", str(val_acc_criteria),
                "-e", "3001",
                "-sd", start_time,
                "-ed", stop_time,
                "-cl", code_list_str
            ])
            
            # 执行 backtrader_test.py 脚本
            model_name = f"final_model_{val_acc_criteria}_{seq_length}_{judge_length}.pth"
            subprocess.run([
                "python", "backtrader_test.py",
                "-m", model_name,
                "-sd", start_time,
                "-ed", stop_time
            ])

subprocess.run([
    "python", "print_log.py"
])