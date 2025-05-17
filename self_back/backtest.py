import pandas as pd
import os

def backtest_return(code, buy_time, sell_time, data_dir='stock_data'):
    """
    股票涨跌回测接口
    参数:
        code: 股票代码，如'600519.SH'
        buy_time: 买入时间，格式如'20240517093000'
        sell_time: 卖出时间，格式如'20240517150000'
        data_dir: 数据文件夹，默认为'stock_data'
    返回:
        收益率（百分比），买入价，卖出价
    """
    file_path = os.path.join(data_dir, f"{code}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到股票数据文件: {file_path}")
    df = pd.read_csv(file_path, dtype={'time':str})
    buy_row = df[df['time'] == buy_time]
    sell_row = df[df['time'] == sell_time]
    if buy_row.empty or sell_row.empty:
        raise ValueError("买入时间或卖出时间在数据中未找到")
    buy_price = float(buy_row.iloc[0]['close'])
    sell_price = float(sell_row.iloc[0]['close'])
    ret = (sell_price - buy_price) / buy_price * 100
    return ret, buy_price, sell_price

# 示例用法
if __name__ == "__main__":
    code = "600519.SH"
    buy_time = "20240517093000"
    sell_time = "20240517150000"
    try:
        ret, buy, sell = backtest_return(code, buy_time, sell_time)
        print(f"{code} 从{buy_time}买入({buy:.2f})，到{sell_time}卖出({sell:.2f})，收益率：{ret:.2f}%")
    except Exception as e:
        print("回测出错：", e)