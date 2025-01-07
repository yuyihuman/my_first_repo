import os
import logging
import random
import pandas as pd
from datetime import datetime
from multiprocessing import Pool

from data_prepare import get_stock_list
from model_train import read_single_stock_outstanding_share, convert_stock_code

# 配置日志
log_folder = "log"
os.makedirs(log_folder, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_folder, "processing.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def process_code(code):
    """
    处理单个股票代码，提取 'turnover' 列的值
    """
    try:
        df = read_single_stock_outstanding_share(code=convert_stock_code(code))
        if 'turnover' in df.columns:
            return df['turnover'].dropna().tolist()
        else:
            logging.warning(f"'turnover' column not found for code {code}.")
    except FileNotFoundError:
        logging.warning(f"Data file for code {code} not found.")
    except Exception as e:
        logging.error(f"Unexpected error for code {code}: {e}")
    return []

def main():
    # 获取股票代码列表
    code_list = get_stock_list(lower_bound=100, upper_bound=200)

    if not code_list:
        logging.info("No stock codes retrieved from the source.")
        print("No stock codes retrieved from the source.")
        return

    # 分块任务
    chunk_size = 20  # 每个任务块包含的代码数量
    code_chunks = [code_list[i:i + chunk_size] for i in range(0, len(code_list), chunk_size)]

    # 使用多进程处理代码块，每次循环单独创建和释放进程池
    turnover_values = []
    for code_chunk in code_chunks:
        with Pool(processes=chunk_size) as pool:
            results = pool.map(process_code, code_chunk)
            for result in results:
                turnover_values.extend(result)

    # 计算并输出 turnover 最大值和最小值
    if turnover_values:
        max_turnover = max(turnover_values)
        min_turnover = min(turnover_values)
        print(f"Maximum turnover: {max_turnover}")
        print(f"Minimum turnover: {min_turnover}")
        logging.info(f"Maximum turnover: {max_turnover}, Minimum turnover: {min_turnover}")
    else:
        print("No turnover values found.")
        logging.info("No turnover values found.")

if __name__ == "__main__":
    main()
