import pandas as pd
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from akshare_test import akshare_module
import numpy as np

def get_stock_list(lower_bound, upper_bound):
    df = akshare_module.AKSHARE().get_zong_gu_ben()
    filtered_df = akshare_module.AKSHARE().filter_by_market_cap(df, lower_bound, upper_bound)
    # 筛选代码以 0、3、6 开头的股票
    filtered_df = filtered_df[filtered_df['代码'].str.startswith(('0', '3', '6'))]
    # print(filtered_df[['代码', '名称']])
    code_list = filtered_df['代码'].tolist()
    # print(code_list)
    return code_list

def split_list_by_ratio_np(data_list, ratio):
    """
    使用 NumPy 随机分割列表

    Args:
        data_list: 要分隔的列表
        ratio: 分割比例

    Returns:
        两个子列表
    """
    np.random.shuffle(data_list)  # 先随机打乱列表
    split_index = int(len(data_list) * ratio)
    return np.array(data_list[:split_index]), np.array(data_list[split_index:])

def prepare_rnn_data(code_list):
    pass

if __name__ == "__main__":
    stock_list = get_stock_list(lower_bound=100, upper_bound=200)
    stock_list_train, stock_list_val = split_list_by_ratio_np(stock_list, 0.8)
    print(stock_list_train)
    print(stock_list_val)