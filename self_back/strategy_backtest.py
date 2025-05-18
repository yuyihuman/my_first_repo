import os
import sys
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from utils import logger, setup_logger, get_current_log_file  # 添加 get_current_log_file

def run_strategy_backtest(
    code,
    start_time,
    end_time,
    buy_strategy,
    sell_strategy,
    data_loader,
    data_dir='stock_data',
    custom_logger=None
):
    """
    使用指定买入/卖出策略对股票进行区间回测，并生成带操作标志的新csv
    :param code: 股票代码
    :param start_time: 回测起始时间（字符串）
    :param end_time: 回测结束时间（字符串）
    :param buy_strategy: 买入策略函数
    :param sell_strategy: 卖出策略函数
    :param data_loader: 数据加载函数
    :param data_dir: 数据目录
    :param custom_logger: 自定义日志记录器，如果为None则创建新的
    :return: 回测结果DataFrame
    """
    # 创建特定的日志文件名 - 移除时间戳使其更简洁
    buy_name = buy_strategy.__name__
    sell_name = sell_strategy.__name__
    
    # 如果没有提供自定义日志记录器，则创建一个
    if custom_logger is None:
        log_file_name = f"{code}_{buy_name}_{sell_name}.log"
        custom_logger = setup_logger(name=None, log_file=log_file_name, reset=True)
        
        # 使用全局logger变量指向新创建的logger，确保其他模块也使用这个日志文件
        import utils
        utils.logger = custom_logger
    
    custom_logger.info(f"开始回测: {code}, 策略: 买入={buy_strategy.__name__}, 卖出={sell_strategy.__name__}")
    custom_logger.info(f"回测时间段: {start_time} 到 {end_time}")
    
    file_path = os.path.join(data_dir, f"{code}.csv")
    
    # 检查数据文件是否存在，如果不存在则下载
    if not os.path.exists(file_path):
        custom_logger.info(f"未找到股票数据文件: {file_path}，正在下载数据...")
        download_stock_data(code, start_time[:8], custom_logger)  # 传递custom_logger
    
    # 检查数据是否覆盖回测时间段
    df = pd.read_csv(file_path, dtype={'time': str})
    min_time = df['time'].min() if not df.empty else None
    max_time = df['time'].max() if not df.empty else None
    
    # 如果数据不足，重新下载
    if df.empty or min_time > start_time or max_time < end_time:
        custom_logger.info(f"数据不足以覆盖回测时间段 ({start_time} 到 {end_time})，正在下载更多数据...")
        # 确定下载起始日期（使用回测开始日期或比现有数据更早的日期）
        download_start = start_time[:8]
        if min_time and min_time > start_time:
            # 如果现有数据的最早时间晚于回测开始时间，使用更早的日期
            start_date = datetime.strptime(start_time[:8], "%Y%m%d")
            # 往前推30天以确保有足够数据
            download_start = (start_date.replace(day=1)).strftime("%Y%m%d")
        download_stock_data(code, download_start, custom_logger)  # 传递custom_logger
        
        # 重新加载数据
        df = pd.read_csv(file_path, dtype={'time': str})
    
    # 筛选回测时间段内的数据
    df = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()
    
    custom_logger.debug(f"筛选后数据点数量: {len(df)}")
    custom_logger.debug(f"数据时间范围: {df['time'].min()} 到 {df['time'].max()}")
    
    # 检查筛选后的数据是否足够
    if len(df) < 20:  # 假设策略至少需要20个数据点
        custom_logger.warning(f"警告: 回测时间段内的数据点数量不足 ({len(df)} < 20)，可能影响策略效果")
    
    df['buy_flag'] = 0
    df['sell_flag'] = 0
    df['hold_flag'] = 0

    # 初始化指数为100
    index_value = 100.0
    custom_logger.info(f"回测开始，初始指数值: {index_value}")
    
    # 记录交易次数
    trade_count = 0
    win_count = 0
    lose_count = 0
    
    holding = False
    buy_time = None  # 记录买入时间
    
    for i, row in df.iterrows():
        cur_time = row['time']
        cur_price = row['close']
        custom_logger.debug(f"处理时间点: {cur_time}, 价格: {cur_price}")
        if not holding:
            # 非持有状态，只能买入
            buy_signal = buy_strategy(code, cur_time, data_loader)
            custom_logger.debug(f"买入信号: {buy_signal}, 时间: {cur_time}")
            if buy_signal == 1:
                df.at[i, 'buy_flag'] = 1
                df.at[i, 'hold_flag'] = 1
                holding = True
                buy_time = cur_time  # 记录买入时间
                custom_logger.info(f"在 {cur_time} 买入 {code}")
        else:
            # 持有状态，只能卖出
            sell_signal = sell_strategy(code, cur_time, data_loader)
            custom_logger.debug(f"卖出信号: {sell_signal}, 时间: {cur_time}")
            if sell_signal == -1:
                df.at[i, 'sell_flag'] = 1
                holding = False
                
                # 计算收益率并更新指数
                if buy_time:
                    try:
                        ret, buy_price, sell_price = backtest_return(code, buy_time, cur_time, data_dir)
                        # 根据收益率更新指数值
                        index_value = index_value * (1 + ret / 100)
                        
                        # 记录交易结果
                        trade_count += 1
                        if ret > 0:
                            win_count += 1
                        else:
                            lose_count += 1
                            
                        custom_logger.info(f"在 {cur_time} 卖出 {code}，买入价: {buy_price:.2f}，卖出价: {sell_price:.2f}，收益率: {ret:.2f}%，当前指数: {index_value:.2f}")
                    except Exception as e:
                        custom_logger.error(f"计算收益率出错: {e}", exc_info=True)
                
                buy_time = None  # 重置买入时间
            else:
                df.at[i, 'hold_flag'] = 1
    
    # 检查回测结束时是否仍然持有股票，如果是，则在最后一个时间点卖出
    if holding and len(df) > 0:
        last_index = df.index[-1]
        last_time = df.iloc[-1]['time']
        # 移除强制卖出的代码
        # df.at[last_index, 'sell_flag'] = 1
        # df.at[last_index, 'hold_flag'] = 0
        
        # 计算最后一次卖出的收益率并更新指数
        if buy_time:
            try:
                # 不再计算强制卖出的收益率
                # ret, buy_price, sell_price = backtest_return(code, buy_time, last_time, data_dir)
                # 根据收益率更新指数值
                # index_value = index_value * (1 + ret / 100)
                custom_logger.info(f"回测结束时仍持有股票 {code}，买入时间: {buy_time}，保持持有状态")
            except Exception as e:
                custom_logger.error(f"处理最终持仓状态出错: {e}", exc_info=True)

    # 打印交易统计信息
    if trade_count > 0:
        win_rate = win_count / trade_count * 100
        custom_logger.info(f"交易统计: 总交易次数={trade_count}, 盈利次数={win_count}, 亏损次数={lose_count}, 胜率={win_rate:.2f}%")
    
    # 打印最终指数值
    custom_logger.info(f"回测结束，最终指数值: {index_value:.2f}")

    # 生成新文件名
    new_file = os.path.join(
        data_dir,
        f"{code}_backtest_{buy_name}_{sell_name}.csv"
    )
    df.to_csv(new_file, index=False, float_format='%.2f')
    custom_logger.info(f"回测结果已保存到: {new_file}")
    return df, index_value  # 返回回测结果和最终指数值

def download_stock_data(code, start_time, custom_logger=None):
    """
    调用stock_data_collector.py下载股票数据
    :param code: 股票代码
    :param start_time: 起始时间（格式：YYYYMMDD）
    :param custom_logger: 自定义日志记录器，如果为None则使用全局logger
    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stock_data_collector.py')
    
    # 使用传入的custom_logger或全局logger
    log = custom_logger if custom_logger else logger
    
    log.info(f"正在下载 {code} 从 {start_time} 开始的数据...")
    
    try:
        # 获取当前日志文件
        current_log_file = get_current_log_file()
        log_file_param = []
        
        # 只有当日志文件存在时才添加日志文件参数
        if current_log_file:
            log_file_param = ['--log_file', os.path.basename(current_log_file)]
        
        # 使用subprocess调用数据收集脚本
        subprocess.run([
            sys.executable,  # 当前Python解释器路径
            script_path,
            '--code', code,
            '--start_time', start_time
        ] + log_file_param, check=True)
        
        log.info(f"{code} 数据下载完成")
    except subprocess.CalledProcessError as e:
        log.error(f"数据下载失败: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    from strategy import BuyStrategy, SellStrategy, load_stock_data
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='股票策略回测工具')
    parser.add_argument('--code', type=str, default="600519.SH", help='股票代码，例如：600519.SH')
    parser.add_argument('--start_time', type=str, default="20240517093000", help='回测开始时间，格式：YYYYMMDDHHmmss')
    parser.add_argument('--end_time', type=str, default="20240517150000", help='回测结束时间，格式：YYYYMMDDHHmmss')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    code = args.code
    start_time = args.start_time
    end_time = args.end_time
    
    # 创建特定的日志文件名
    log_file_name = f"{code}_simple_ma_buy_simple_ma_sell.log"
    
    # 重新配置日志记录器，使用特定的日志文件
    custom_logger = setup_logger(name=None, log_file=log_file_name, reset=True)
    
    # 使用全局logger变量指向新创建的logger
    import utils
    utils.logger = custom_logger
    
    custom_logger.info(f"开始回测 {code}，时间段: {start_time} 到 {end_time}")
    
    # 传递已配置的logger给run_strategy_backtest函数，避免重复配置
    run_strategy_backtest(
        code,
        start_time,
        end_time,
        BuyStrategy.simple_ma_buy,
        SellStrategy.simple_ma_sell,
        load_stock_data,
        data_dir='stock_data',
        custom_logger=custom_logger  # 传递已配置的logger
    )