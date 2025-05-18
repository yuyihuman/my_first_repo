import pandas as pd
import os
from utils import logger  # 导入共用日志模块

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
    logger.debug(f"计算回测收益: {code}, 买入时间: {buy_time}, 卖出时间: {sell_time}")
    file_path = os.path.join(data_dir, f"{code}.csv")
    if not os.path.exists(file_path):
        logger.error(f"未找到股票数据文件: {file_path}")
        raise FileNotFoundError(f"未找到股票数据文件: {file_path}")
    
    logger.debug(f"加载数据文件: {file_path}")
    df = pd.read_csv(file_path, dtype={'time':str})
    logger.debug(f"数据文件加载完成, 数据点数量: {len(df)}")
    
    buy_row = df[df['time'] == buy_time]
    sell_row = df[df['time'] == sell_time]
    
    if buy_row.empty:
        logger.error(f"买入时间在数据中未找到: {buy_time}")
        raise ValueError(f"买入时间在数据中未找到: {buy_time}")
    if sell_row.empty:
        logger.error(f"卖出时间在数据中未找到: {sell_time}")
        raise ValueError(f"卖出时间在数据中未找到: {sell_time}")
    
    buy_price = float(buy_row.iloc[0]['close'])
    sell_price = float(sell_row.iloc[0]['close'])
    ret = (sell_price - buy_price) / buy_price * 100
    
    logger.debug(f"回测计算完成: 买入价: {buy_price:.2f}, 卖出价: {sell_price:.2f}, 收益率: {ret:.2f}%")
    return ret, buy_price, sell_price

# 示例用法
if __name__ == "__main__":
    code = "600519.SH"
    buy_time = "20240517093000"
    sell_time = "20240517150000"
    logger.info(f"开始回测: {code}, 买入时间: {buy_time}, 卖出时间: {sell_time}")
    try:
        ret, buy, sell = backtest_return(code, buy_time, sell_time)
        logger.info(f"回测结果: {code} 从{buy_time}买入({buy:.2f})，到{sell_time}卖出({sell:.2f})，收益率：{ret:.2f}%")
        print(f"{code} 从{buy_time}买入({buy:.2f})，到{sell_time}卖出({sell:.2f})，收益率：{ret:.2f}%")
    except Exception as e:
        logger.error(f"回测出错: {e}", exc_info=True)
        print("回测出错：", e)