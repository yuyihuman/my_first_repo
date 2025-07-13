import pandas as pd
import numpy as np

def read_stock_data(filename):
    # 读取CSV文件
    df = pd.read_csv(filename)
    
    # 提取开盘价、收盘价和涨跌幅数据
    open_prices = df['开盘'].values
    close_prices = df['收盘'].values
    change_percentages = df['涨跌幅'].values
    exchange_percentages = df['换手率'].values
    
    # 将数据转换为NumPy数组
    open_prices = np.array(open_prices)
    close_prices = np.array(close_prices)
    change_percentages = np.array(change_percentages)
    exchange_percentages = np.array(exchange_percentages)
    
    # 计算 rnn_input 向量
    rnn_input = np.column_stack((change_percentages, exchange_percentages))
    
    # 计算 rnn_target 向量
    rnn_target = np.zeros_like(open_prices)
    # rnn_target[1:] = np.round((open_prices[1:] - close_prices[:-1]) / close_prices[:-1]*100,2)
    rnn_target[1:] = ((open_prices[1:] - close_prices[:-1]) > 0).astype(int)
    
    return open_prices, close_prices, change_percentages, exchange_percentages, rnn_input, rnn_target


# 使用示例
if __name__ == "__main__":
    open_prices, close_prices, change_percentages, exchange_percentages, rnn_input, rnn_target = read_stock_data('000001.csv')
    print("开盘价向量:", open_prices, "长度:", len(open_prices))
    print("收盘价向量:", close_prices, "长度:", len(close_prices))
    print("涨跌幅向量:", change_percentages, "长度:", len(change_percentages))
    print("换手率向量:", exchange_percentages, "长度:", len(exchange_percentages))
    print("RNN输入向量:", rnn_input, "长度:", len(rnn_input))
    print("RNN目标向量:", rnn_target, "长度:", len(rnn_target))
