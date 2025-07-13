import os
import sys
import subprocess
import shutil
import logging
import argparse
import random
import pandas as pd
import glob
from datetime import datetime, timedelta
from data_prepare import get_stock_list
from model_train import read_single_stock_outstanding_share, convert_stock_code, clear_folder
from xtquant import xtdata

            
# 设置最大线程数
os.environ["NUMEXPR_MAX_THREADS"] = "20"

# 获取当前时间
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

# 设置日志文件路径
log_filename = f"log_start2.txt"
log_file_path = os.path.join("log", log_filename)

# 确保log目录存在
os.makedirs("log", exist_ok=True)
os.makedirs("data", exist_ok=True)

# 保留文件夹，只删除里面的文件和子文件夹
clear_folder("log")
clear_folder("data")
[os.remove(f) for f in glob.glob("*.pth")]

# 配置logging，将输出重定向到日志文件
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s', filename=log_file_path, filemode='a')

# 将stdout和stderr重定向到日志文件
sys.stdout = open(log_file_path, 'a', encoding='utf-8')
sys.stderr = sys.stdout

# 定义命令行参数
parser = argparse.ArgumentParser(description="Run experiments with varying parameters.")
parser.add_argument("-sd", "--start_date", type=str, default="20160101", help="Start date in YYYYMMDD format")
parser.add_argument("-ed", "--end_date", type=str, default="20231230", help="End date in YYYYMMDD format")
parser.add_argument("-d", "--download", type=str, default="True", help="True or False")

args = parser.parse_args()
start_time = args.start_date
stop_time = args.end_date
# 将 end_data 转换为 datetime 对象
end_date = datetime.strptime(str(stop_time), "%Y%m%d")
# 计算前一年的日期
one_year_ago = end_date - timedelta(days=180)
# 将结果转换回指定格式
previous_year_date = one_year_ago.strftime("%Y%m%d")

# 获取股票代码列表
code_list = get_stock_list(lower_bound=120, upper_bound=200)
code_list = [code for code in code_list if code.startswith("0")]
code_list = [
    code for code in code_list
    if pd.to_datetime(read_single_stock_outstanding_share(code=convert_stock_code(code)).loc[0, 'date']) <= pd.to_datetime('2010-01-01')
]
code_list = random.sample(code_list, 40)
code_list_str = ",".join(map(str, code_list))
logging.info(f'code_list_str is {code_list_str}')

code_list_backtrader = get_stock_list(lower_bound=100, upper_bound=120)
code_list_backtrader = [code for code in code_list_backtrader if code.startswith("0")]
code_list_backtrader = [
    code for code in code_list_backtrader
    if pd.to_datetime(read_single_stock_outstanding_share(code=convert_stock_code(code)).loc[0, 'date']) <= pd.to_datetime('2010-01-01')
]
code_list_backtrader = random.sample(code_list_backtrader, 10)
code_list_backtrader_str = ",".join(map(str, code_list_backtrader))

combined_code_list = list(set(code_list + code_list_backtrader))
combined_code_list_str = ",".join(map(str, combined_code_list))

# 自定义frange函数，用于生成浮点数范围
def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step

# 循环参数范围
val_acc_criteria_range = [round(x, 2) for x in list(frange(0.85, 0.90+0.01, 0.05))]
seq_length_range = range(24, 200+1, 144)
judge_length_range = range(48, 100+1, 48)
logging.info("==============================================")
# 下载数据
if args.download == "True":
    total_stocks = len(combined_code_list)
    xtdata.enable_hello = False
    for index, code in enumerate(combined_code_list):
        logging.info(f"Downloading {code} ({index + 1}/{total_stocks})...")
        xtdata.download_history_data(code, period="5m", incrementally=True, start_time=start_time)
        logging.info(f"{code} download completed.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")

# 遍历参数范围
for val_acc_criteria in val_acc_criteria_range:
    for seq_length in seq_length_range:
        for judge_length in judge_length_range:
            # 构建model_train.py的命令
            train_command = [
                "python", "model_train.py",
                "train",
                "--seq_length", str(seq_length),
                "--judge_length", str(judge_length),
                "--val_acc_criteria", str(val_acc_criteria),
                "-e", "5001",
                "-sd", start_time,
                "-ed", stop_time,
                "-cl", code_list_str,
                "-clb", code_list_backtrader_str
            ]
            # 记录日志并执行model_train.py
            logging.info(f"Executing: {' '.join(train_command)}")
            subprocess.run(train_command)

            # 构建backtrader_test.py的命令
            model_name = f"final_model_{val_acc_criteria}_{seq_length}_{judge_length}.pth"
            
            test_command_1 = [
                "python", "backtrader_test.py",
                "-m", model_name,
                "-sd", previous_year_date,
                "-ed", stop_time,
                "-clb", combined_code_list_str
            ]
            logging.info(f"Executing: {' '.join(test_command_1)}")
            subprocess.run(test_command_1)
            
            # test_command_2 = [
            #     "python", "backtrader_test.py",
            #     "-m", model_name,
            #     "-sd", start_time,
            #     "-ed", stop_time,
            #     "-clb", combined_code_list_str,
            #     "-mode", "truth"
            # ]
            # logging.info(f"Executing: {' '.join(test_command_2)}")
            # subprocess.run(test_command_2)

# 执行print_log.py并将日志输出记录到log文件
logging.info("Executing print_log.py...")
subprocess.run(
    ["python", "print_log.py"],
    stdout=sys.stdout, stderr=sys.stderr
)

# 备份log和data文件夹
backup_folder = f"backup_{current_time}"
os.makedirs(backup_folder, exist_ok=True)

# 备份log文件夹
log_backup_path = os.path.join(backup_folder, "log")
shutil.copytree("log", log_backup_path)

# 备份data文件夹
data_backup_path = os.path.join(backup_folder, "data")
shutil.copytree("data", data_backup_path)

# 创建model文件夹并移动所有.pth文件
model_folder = os.path.join(backup_folder, "model")
os.makedirs(model_folder, exist_ok=True)

# 将所有.pth文件移动到model文件夹
for file in os.listdir("."):  # 当前目录
    if file.endswith(".pth"):
        file_path = os.path.join(".", file)  # 当前目录下的文件
        shutil.move(file_path, os.path.join(model_folder, file))

# 保留文件夹，只删除里面的文件和子文件夹
clear_folder("log")
clear_folder("data")

logging.info(f"Backup and cleanup completed. All data has been saved to {backup_folder}.")
