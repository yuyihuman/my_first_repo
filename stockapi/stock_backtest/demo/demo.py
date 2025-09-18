# coding:utf-8
"""选股策略：基于最低价收盘价与均线关系的股票筛选

数据来源：
- 股票历史数据来源于：c:/Users/17701/github/my_first_repo/stockapi/stock_base_info/all_stocks_data/
- 数据结构检查日志：c:/Users/17701/github/my_first_repo/stockapi/stock_base_info/logs/data_structure_check.log
- 如需查找新数据或验证数据完整性，请查看上述日志文件

"""

import pandas as pd
import os
from datetime import datetime
import multiprocessing as mp
from multiprocessing import Queue, Process, JoinableQueue
from functools import partial
import logging
import shutil
import gc
import argparse

# 策略条件定义（唯一权威来源）
STRATEGY_CONDITIONS = """策略条件：
1、股票价格必须大于1（最低价和收盘价都必须大于1）
2、当天开盘价高于上一日最高价至少2%，且当日收盘价高于上一日最高价，当天涨幅小于9.5%
3、当日20，30日均线值大于上一日20，30日均线值
4、前面三个交易日中至少一天5、10、20、30日均线中最大值和最小值之间的差距小于1%
5、当日成交量小于之前一个交易日10日成交量均值的2.5倍"""

def load_stock_data(csv_file_path):
    """
    加载股票数据
    
    Args:
        csv_file_path: CSV文件路径
    
    Returns:
        DataFrame: 股票数据
    """
    try:
        # 首先读取基本列
        basic_cols = ['datetime', 'open', 'close', 'high', 'low', 'volume']
        ma_cols = ['close_5d_avg', 'close_10d_avg', 'close_20d_avg', 'close_30d_avg', 'close_60d_avg']
        volume_cols = ['volume_5d_avg', 'volume_10d_avg']
        
        # 检查文件中存在哪些列
        try:
            # 读取第一行来检查列名
            sample_df = pd.read_csv(csv_file_path, nrows=1)
            available_cols = sample_df.columns.tolist()
            
            # 确定要读取的列
            cols_to_read = basic_cols.copy()
            available_ma_cols = [col for col in ma_cols if col in available_cols]
            available_volume_cols = [col for col in volume_cols if col in available_cols]
            cols_to_read.extend(available_ma_cols)
            cols_to_read.extend(available_volume_cols)
            
            # 读取CSV文件
            df = pd.read_csv(csv_file_path, usecols=cols_to_read)
            
        except Exception:
            # 如果列检查失败，回退到只读取基本列
            df = pd.read_csv(csv_file_path, usecols=basic_cols)
            available_ma_cols = []
        
        # 转换日期列
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 按日期排序
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # 检查是否有必需的预计算均线数据，缺失时直接跳过股票
        required_ma_cols = ['close_5d_avg', 'close_10d_avg', 'close_20d_avg', 'close_30d_avg']
        missing_ma_cols = [col for col in required_ma_cols if col not in available_ma_cols]
        
        if missing_ma_cols:
            logging.warning(f"缺失预计算均线数据: {missing_ma_cols}，跳过该股票")
            return None
        
        # 处理收盘价均线数据：只使用预计算的数据
        df['ma5'] = df['close_5d_avg']
        df['ma10'] = df['close_10d_avg']
        df['ma20'] = df['close_20d_avg']
        df['ma30'] = df['close_30d_avg']
        
        # 处理60日均线（可选）
        if 'close_60d_avg' in available_ma_cols:
            df['ma60'] = df['close_60d_avg']
        else:
            df['ma60'] = None
        
        # 检查是否有必需的预计算成交量数据，缺失时直接跳过股票
        required_volume_cols = ['volume_5d_avg', 'volume_10d_avg']
        missing_volume_cols = [col for col in required_volume_cols if col not in available_volume_cols]
        
        if missing_volume_cols:
            logging.warning(f"缺失预计算成交量数据: {missing_volume_cols}，跳过该股票")
            return None
        
        # 处理成交量数据：只使用预计算的数据
        df['vol5'] = df['volume_5d_avg']
        df['vol10'] = df['volume_10d_avg']
        
        # 删除不再需要的原始均线列和成交量列以节省内存
        for col in available_ma_cols + available_volume_cols:
            if col in df.columns:
                df.drop(col, axis=1, inplace=True)
        
        return df
    except Exception as e:
        logging.error(f"加载数据失败: {e}")
        return None

def check_strategy_conditions(df, current_idx):
    """
    检查当前日期是否符合策略条件
    
    Args:
        df: 股票数据DataFrame
        current_idx: 当前日期的索引
    
    Returns:
        bool: 是否符合条件
    """
    # 需要至少前三个交易日的数据
    if current_idx < 3:
        return False
    
    # 获取当日数据和前一日数据
    current_data = df.iloc[current_idx]
    prev_data = df.iloc[current_idx - 1]
    
    # 获取当日开盘价、收盘价、成交量
    open_price = current_data['open']
    close_price = current_data['close']
    low_price = current_data['low']
    volume = current_data['volume'] if 'volume' in current_data and not pd.isna(current_data['volume']) else None
    
    # 获取前一日最高价和收盘价
    prev_high = prev_data['high']
    prev_close = prev_data['close']
    
    # 策略条件1：股票价格必须大于1（最低价和收盘价都必须大于1）
    if close_price <= 1 or low_price <= 1:
        return False
    
    # 策略条件2：当天开盘价高于上一日最高价至少2%，且当日收盘价高于上一日最高价，当天涨幅小于9.5%
    open_above_prev_high_2_percent = open_price > prev_high * 1.02
    close_above_prev_high = close_price > prev_high
    
    # 计算当天涨幅（相对于前一日收盘价）
    daily_return = (close_price - prev_close) / prev_close
    daily_return_under_9_5_percent = daily_return < 0.095
    
    condition2_met = open_above_prev_high_2_percent and close_above_prev_high and daily_return_under_9_5_percent
    
    # 策略条件3：当日20，30日均线值大于上一日20，30日均线值
    condition3_met = False
    current_ma20 = current_data['ma20'] if 'ma20' in current_data and not pd.isna(current_data['ma20']) else None
    current_ma30 = current_data['ma30'] if 'ma30' in current_data and not pd.isna(current_data['ma30']) else None
    prev_ma20 = prev_data['ma20'] if 'ma20' in prev_data and not pd.isna(prev_data['ma20']) else None
    prev_ma30 = prev_data['ma30'] if 'ma30' in prev_data and not pd.isna(prev_data['ma30']) else None
    
    if (current_ma20 is not None and prev_ma20 is not None and 
        current_ma30 is not None and prev_ma30 is not None):
        condition3_met = current_ma20 > prev_ma20 and current_ma30 > prev_ma30
    
    # 策略条件4：前面三个交易日中至少一天5、10、20、30日均线中最大值和最小值之间的差距小于1%
    condition4_met = False
    for i in range(1, 4):  # 检查前1、2、3个交易日
        if current_idx - i >= 0:
            day_data = df.iloc[current_idx - i]
            
            # 获取均线数据
            ma_values = []
            for ma_col in ['ma5', 'ma10', 'ma20', 'ma30']:
                if ma_col in day_data and not pd.isna(day_data[ma_col]):
                    ma_values.append(day_data[ma_col])
            
            # 如果有足够的均线数据，检查差距
            if len(ma_values) >= 2:
                max_ma = max(ma_values)
                min_ma = min(ma_values)
                if min_ma > 0:
                    ma_diff_percent = (max_ma - min_ma) / min_ma
                    if ma_diff_percent < 0.01:  # 小于1%
                        condition4_met = True
                        break
    
    # 策略条件5：当日成交量小于之前一个交易日10日成交量均值的2.5倍
    condition5_met = False
    if volume is not None:
        prev_vol10 = prev_data['vol10'] if 'vol10' in prev_data and not pd.isna(prev_data['vol10']) else None
        
        if prev_vol10 is not None and prev_vol10 > 0:
            condition5_met = volume < prev_vol10 * 2.5
    
    return condition2_met and condition3_met and condition4_met and condition5_met

def check_strategy_conditions_verbose(df, current_idx, stock_code, verbose=False):
    """
    检查当前日期是否符合策略条件（详细版本，用于单股票测试）
    
    Args:
        df: 股票数据DataFrame
        current_idx: 当前日期的索引
        stock_code: 股票代码
        verbose: 是否打印详细信息
    
    Returns:
        bool: 是否符合条件
    """
    # 需要至少前三个交易日的数据
    if current_idx < 3:
        if verbose:
            logging.info(f"股票 {stock_code} 索引 {current_idx}: 数据不足，需要至少前3个交易日数据")
        return False
    
    current_date = df.iloc[current_idx]['datetime'].strftime('%Y-%m-%d')
    current_data = df.iloc[current_idx]
    prev_data = df.iloc[current_idx - 1]
    prev_date = prev_data['datetime'].strftime('%Y-%m-%d')
    
    # 获取当日开盘价、收盘价、成交量
    open_price = current_data['open']
    close_price = current_data['close']
    low_price = current_data['low']
    volume = current_data['volume'] if 'volume' in current_data and not pd.isna(current_data['volume']) else None
    
    # 获取前一日最高价和收盘价
    prev_high = prev_data['high']
    prev_close = prev_data['close']

    if verbose:
        logging.info(f"\n=== 股票 {stock_code} 日期 {current_date} 策略条件检查 ===")
        logging.info(f"当日价格信息:")
        logging.info(f"  开盘价: {open_price:.4f}")
        logging.info(f"  收盘价: {close_price:.4f}")
        logging.info(f"  最低价: {low_price:.4f}")
        logging.info(f"  成交量: {volume if volume is not None else 'N/A'}")
        logging.info(f"前一日价格信息({prev_date}):")
        logging.info(f"  最高价: {prev_high:.4f}")
        logging.info(f"  收盘价: {prev_close:.4f}")
    
    # 策略条件1：股票价格必须大于1（最低价和收盘价都必须大于1）
    if close_price <= 1 or low_price <= 1:
        if verbose:
            logging.info(f"股票 {stock_code} 日期 {current_date}: 股票价格小于等于1，跳过 (收盘价:{close_price}, 最低价:{low_price})")
        return False
    
    # 策略条件2：当天开盘价高于上一日最高价至少2%，且当日收盘价高于上一日最高价，当天涨幅小于9.5%
    open_above_prev_high_2_percent = open_price > prev_high * 1.02
    close_above_prev_high = close_price > prev_high
    
    # 计算当天涨幅（相对于前一日收盘价）
    daily_return = (close_price - prev_close) / prev_close
    daily_return_under_9_5_percent = daily_return < 0.095
    
    condition2_met = open_above_prev_high_2_percent and close_above_prev_high and daily_return_under_9_5_percent
    
    if verbose:
        logging.info(f"\n策略条件2检查:")
        logging.info(f"  当日开盘价 > 前一日最高价*1.02: {open_price:.4f} > {prev_high*1.02:.4f} = {open_above_prev_high_2_percent}")
        logging.info(f"  当日收盘价 > 前一日最高价: {close_price:.4f} > {prev_high:.4f} = {close_above_prev_high}")
        logging.info(f"  当天涨幅: ({close_price:.4f} - {prev_close:.4f}) / {prev_close:.4f} = {daily_return:.4f} ({daily_return*100:.2f}%)")
        logging.info(f"  当天涨幅 < 9.5%: {daily_return*100:.2f}% < 9.5% = {daily_return_under_9_5_percent}")
        logging.info(f"  条件2满足: {condition2_met}")
    
    # 策略条件3：当日20，30日均线值大于上一日20，30日均线值
    condition3_met = False
    current_ma20 = current_data['ma20'] if 'ma20' in current_data and not pd.isna(current_data['ma20']) else None
    current_ma30 = current_data['ma30'] if 'ma30' in current_data and not pd.isna(current_data['ma30']) else None
    prev_ma20 = prev_data['ma20'] if 'ma20' in prev_data and not pd.isna(prev_data['ma20']) else None
    prev_ma30 = prev_data['ma30'] if 'ma30' in prev_data and not pd.isna(prev_data['ma30']) else None
    
    if (current_ma20 is not None and prev_ma20 is not None and 
        current_ma30 is not None and prev_ma30 is not None):
        condition3_met = current_ma20 > prev_ma20 and current_ma30 > prev_ma30
    
    if verbose:
        logging.info(f"\n策略条件3检查(均线上升):")
        logging.info(f"  当日20日均线: {current_ma20}")
        logging.info(f"  前一日20日均线: {prev_ma20}")
        logging.info(f"  当日30日均线: {current_ma30}")
        logging.info(f"  前一日30日均线: {prev_ma30}")
        if (current_ma20 is not None and prev_ma20 is not None and 
            current_ma30 is not None and prev_ma30 is not None):
            logging.info(f"  20日均线上升: {current_ma20:.4f} > {prev_ma20:.4f} = {current_ma20 > prev_ma20}")
            logging.info(f"  30日均线上升: {current_ma30:.4f} > {prev_ma30:.4f} = {current_ma30 > prev_ma30}")
        logging.info(f"  条件3满足: {condition3_met}")
    
    # 策略条件4：前面三个交易日中至少一天5、10、20、30日均线中最大值和最小值之间的差距小于1%
    condition4_met = False
    if verbose:
        logging.info(f"\n策略条件4检查(均线差距):")
    
    for i in range(1, 4):  # 检查前1、2、3个交易日
        if current_idx - i >= 0:
            day_data = df.iloc[current_idx - i]
            day_date = day_data['datetime'].strftime('%Y-%m-%d')
            
            # 获取均线数据
            ma_values = []
            ma_info = {}
            for ma_col in ['ma5', 'ma10', 'ma20', 'ma30']:
                if ma_col in day_data and not pd.isna(day_data[ma_col]):
                    ma_values.append(day_data[ma_col])
                    ma_info[ma_col] = day_data[ma_col]
            
            if verbose:
                logging.info(f"  检查日期 {day_date}: {ma_info}")
            
            # 如果有足够的均线数据，检查差距
            if len(ma_values) >= 2:
                max_ma = max(ma_values)
                min_ma = min(ma_values)
                if min_ma > 0:
                    ma_diff_percent = (max_ma - min_ma) / min_ma
                    if verbose:
                        logging.info(f"    均线差距: ({max_ma:.4f} - {min_ma:.4f}) / {min_ma:.4f} = {ma_diff_percent:.4f} ({ma_diff_percent*100:.2f}%)")
                    
                    if ma_diff_percent < 0.01:  # 小于1%
                        condition4_met = True
                        if verbose:
                            logging.info(f"    ✓ 日期 {day_date} 均线差距小于1%，条件4满足")
                        break
                    elif verbose:
                        logging.info(f"    ✗ 日期 {day_date} 均线差距大于等于1%")
            elif verbose:
                logging.info(f"    ✗ 日期 {day_date} 均线数据不足")
    
    if verbose:
        logging.info(f"  条件4满足: {condition4_met}")
    
    # 策略条件5：当日成交量小于之前一个交易日10日成交量均值的2.5倍
    condition5_met = False
    if volume is not None:
        prev_vol10 = prev_data['vol10'] if 'vol10' in prev_data and not pd.isna(prev_data['vol10']) else None
        
        if prev_vol10 is not None and prev_vol10 > 0:
            condition5_met = volume < prev_vol10 * 2.5
            
            if verbose:
                logging.info(f"\n策略条件5检查(成交量):")
                logging.info(f"  当日成交量: {volume}")
                logging.info(f"  前一日10日成交量均值: {prev_vol10}")
                logging.info(f"  需要小于: {prev_vol10 * 2.5}")
                logging.info(f"  条件5满足: {condition5_met}")
        else:
            if verbose:
                logging.info(f"\n策略条件5检查(成交量): 前一日10日成交量均值数据缺失")
                logging.info(f"  前一日10日成交量均值: {prev_vol10}")
    else:
        if verbose:
            logging.info(f"\n策略条件5检查(成交量): 当日成交量数据缺失")
    
    # 最终结果
    result = condition2_met and condition3_met and condition4_met and condition5_met
    
    if verbose:
        logging.info(f"\n最终结果: {result}")
        logging.info(f"  条件2(开盘价和收盘价高于前一日最高价且涨幅<9.5%): {condition2_met}")
        logging.info(f"  条件3(当日20、30日均线值大于上一日均线值): {condition3_met}")
        logging.info(f"  条件4(前三日中至少一天均线差距<1%): {condition4_met}")
        logging.info(f"  条件5(成交量<前一日10日成交量均值2.5倍): {condition5_met}")
        if result:
            logging.info(f"*** 股票 {stock_code} 在 {current_date} 符合选股条件! ***")
        logging.info("=" * 60)
    
    return result

def process_single_stock(stock_folder_name, data_folder, process_index=1, log_to_file=None, verbose=False):
    """
    处理单个股票的数据，检查是否符合策略条件
    
    Args:
        stock_folder_name: 股票文件夹名称
        data_folder: 数据根目录路径
        process_index: 进程序号（1-20）
        log_to_file: 日志记录函数
        verbose: 是否打印详细的策略判断信息（用于单股票测试）
    
    Returns:
        list: 符合条件的日期列表，包含次日收盘价和涨跌比例
    """
    # 从文件夹名称提取股票代码
    stock_code = stock_folder_name.replace('stock_', '').replace('_data', '')
    
    # 如果没有提供log_to_file函数，创建一个默认的
    if log_to_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(script_dir, "process_logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        process_log_file = os.path.join(logs_dir, f"process_{process_index}.log")
        
        def log_to_file(message):
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                with open(process_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{timestamp} - INFO - {message}\n")
                    f.flush()
            except Exception as e:
                logging.error(f"进程日志写入失败: {e}")
    
    # 记录开始处理股票
    log_to_file(f"开始处理股票 {stock_code}，进程序号: {process_index}")
    
    # 构建CSV文件路径
    stock_folder_path = os.path.join(data_folder, stock_folder_name)
    csv_file_path = os.path.join(stock_folder_path, f"{stock_code}_daily_history.csv")
    
    # 检查股票文件夹是否存在
    if not os.path.exists(stock_folder_path):
        log_to_file(f"股票 {stock_code} 的数据文件夹不存在: {stock_folder_path}")
        return []
    
    log_to_file(f"找到股票 {stock_code} 的数据文件夹: {stock_folder_path}")
    
    # 加载股票数据
    df = load_stock_data(csv_file_path)
    if df is None:
        log_to_file(f"股票 {stock_code} 数据加载失败或缺失必需的预计算数据，跳过处理")
        return []
    
    if len(df) < 41:  # 至少需要41天数据（30天均线+1天前一日数据+10天未来数据）
        log_to_file(f"股票 {stock_code} 数据量不足（{len(df)}条），需要至少41条数据，跳过处理")
        return []
    
    log_to_file(f"处理股票 {stock_code}，共 {len(df)} 条记录")
    
    # 存储符合条件的日期
    selected_dates = []
    
    try:
        # 预先计算所有需要的数据，避免在循环中重复计算
        df_values = df[['datetime', 'open', 'close', 'low', 'ma5', 'ma10', 'ma20', 'ma30']].values
        
        # 遍历每一个日期（从第30天开始到倒数第11天，确保有足够历史数据和未来10个交易日数据）
        for i in range(30, len(df) - 10):
            current_row = df_values[i]
            
            # 根据verbose参数选择使用哪个条件检查函数
            if verbose:
                condition_met = check_strategy_conditions_verbose(df, i, stock_code, verbose=True)
            else:
                condition_met = check_strategy_conditions(df, i)
            
            if condition_met:
                next_row = df_values[i + 1]
                
                # 计算涨跌比例
                current_close = current_row[2]  # close
                next_open = next_row[1]  # next open
                next_close = next_row[2]  # next close
                
                next_open_change = (next_open - current_close) / current_close * 100
                next_close_change = (next_close - current_close) / current_close * 100
                
                # 计算3日后、5日后和10日后的收盘价变化
                day3_close = df_values[i + 3][2] if i + 3 < len(df) else None
                day5_close = df_values[i + 5][2] if i + 5 < len(df) else None
                day10_close = df_values[i + 10][2] if i + 10 < len(df) else None
                
                day3_change = (day3_close - current_close) / current_close * 100 if day3_close is not None else None
                day5_change = (day5_close - current_close) / current_close * 100 if day5_close is not None else None
                day10_change = (day10_close - current_close) / current_close * 100 if day10_close is not None else None
                
                selected_dates.append({
                    'stock_code': stock_code,
                    'date': current_row[0].strftime('%Y-%m-%d'),  # datetime
                    'open': current_row[1],  # open
                    'close': current_close,
                    'low': current_row[3],  # low
                    'ma5': round(current_row[4], 2),  # ma5
                    'ma10': round(current_row[5], 2),  # ma10
                    'ma20': round(current_row[6], 2),  # ma20
                    'ma30': round(current_row[7], 2),  # ma30
                    'next_open': next_open,
                    'next_close': next_close,
                    'next_open_change_pct': round(next_open_change, 2),
                    'next_close_change_pct': round(next_close_change, 2),
                    'day3_close': day3_close,
                    'day3_change_pct': round(day3_change, 2) if day3_change is not None else None,
                    'day5_close': day5_close,
                    'day5_change_pct': round(day5_change, 2) if day5_change is not None else None,
                    'day10_close': day10_close,
                    'day10_change_pct': round(day10_change, 2) if day10_change is not None else None
                })
        
        logging.info(f"股票 {stock_code} 找到 {len(selected_dates)} 个符合条件的日期")
        return selected_dates
    
    except Exception as e:
        logging.error(f"处理股票 {stock_code} 时发生错误: {e}")
        return []
    
    finally:
        # 显式释放DataFrame内存
        if 'df' in locals():
            del df
        if 'df_values' in locals():
            del df_values
        # 强制垃圾回收
        gc.collect()

def process_stock_batch(stock_info_list, data_folder_path, process_index=1):
    """
    处理一批股票的选股策略（用于多进程）
    
    Args:
        stock_info_list: 股票信息列表
        data_folder_path: 股票数据文件夹路径
        process_index: 进程序号（1-20）
    
    Returns:
        list: 所有符合条件的日期列表
    """
    # 确保每个进程都创建日志文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "process_logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    process_log_file = os.path.join(logs_dir, f"process_{process_index}.log")
    
    # 直接写入日志文件
    def log_to_file(message):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            with open(process_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - INFO - {message}\n")
                f.flush()
        except Exception as e:
            logging.error(f"进程日志写入失败: {e}")
    
    # 记录批次开始
    log_to_file(f"进程 {process_index} 开始处理，批次包含 {len(stock_info_list)} 个股票文件夹")
    
    batch_results = []
    processed_count = 0
    
    for stock_folder in stock_info_list:
        # 提取股票代码
        stock_code = stock_folder.replace('stock_', '').replace('_data', '')
        
        # 检查股票文件夹是否存在
        stock_folder_path = os.path.join(data_folder_path, stock_folder)
        if os.path.exists(stock_folder_path):
            stock_results = process_single_stock(stock_folder, data_folder_path, process_index, log_to_file)
            batch_results.extend(stock_results)
        else:
            log_to_file(f"股票 {stock_code} 的文件夹不存在: {stock_folder_path}")
        
        processed_count += 1
        # 每处理50个股票就进行一次垃圾回收，减少内存累积
        if processed_count % 50 == 0:
            gc.collect()
            log_to_file(f"进程 {process_index} 已处理 {processed_count}/{len(stock_info_list)} 个股票，当前结果数: {len(batch_results)}")
    
    # 记录批次结束
    log_to_file(f"进程 {process_index} 处理完成，共处理 {len(batch_results)} 个符合条件的日期")
    return batch_results

def process_stock_dynamic(task_queue, result_queue, data_folder_path, process_index):
    """
    动态处理股票的选股策略（用于多进程动态任务分配）
    
    Args:
        task_queue: 任务队列，包含股票文件夹名称
        result_queue: 结果队列，用于收集处理结果
        data_folder_path: 股票数据文件夹路径
        process_index: 进程序号
    """
    # 确保每个进程都创建日志文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "process_logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    process_log_file = os.path.join(logs_dir, f"process_{process_index}.log")
    
    def log_to_file(message, level="info"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        with open(process_log_file, "a", encoding="utf-8") as f:
            f.write(log_message)
    
    start_time = datetime.now()
    log_to_file(f"进程 {process_index} 启动，开始动态处理任务，启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"进程 {process_index} 已启动，开始处理任务，启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    processed_count = 0
    total_results = []
    
    while True:
        try:
            # 从队列中获取任务，设置超时避免无限等待
            get_task_msg = f"进程 {process_index} 尝试获取任务..."
            log_to_file(get_task_msg)
            
            stock_folder = task_queue.get(timeout=2)
            
            task_received_msg = f"进程 {process_index} 获取到任务: {stock_folder}"
            log_to_file(task_received_msg)
            
            try:
                # 处理单个股票
                stock_results = process_single_stock(stock_folder, data_folder_path, process_index, log_to_file)
                total_results.extend(stock_results)
                
                processed_count += 1
                
                # 每处理10个股票就进行一次垃圾回收和进度报告
                if processed_count % 10 == 0:
                    gc.collect()
                    progress_msg = f"进程 {process_index} 已处理 {processed_count} 个股票，当前结果数: {len(total_results)}"
                    log_to_file(progress_msg)
                    logging.info(progress_msg)
                
            except Exception as process_error:
                error_msg = f"进程 {process_index} 处理股票 {stock_folder} 时发生错误: {process_error}"
                log_to_file(error_msg)
                logging.warning(error_msg)
            
            # 无论处理成功还是失败，都要标记任务完成
            task_done_msg = f"进程 {process_index} 标记任务 {stock_folder} 完成"
            log_to_file(task_done_msg)
            task_queue.task_done()
            
        except Exception as e:
            error_msg = f"进程 {process_index} 获取任务时发生错误: {e}"
            log_to_file(error_msg)
            
            if "timeout" in str(e).lower() or "Empty" in str(e) or "queue.Empty" in str(type(e)):
                # 队列为空或超时，准备退出并提交结果
                timeout_msg = f"进程 {process_index} 获取任务超时，可能所有任务已完成，准备退出"
                log_to_file(timeout_msg)
                logging.info(timeout_msg)
                break
            else:
                logging.error(error_msg)
                continue
    
    end_time = datetime.now()
    duration = end_time - start_time
    completion_msg = f"进程 {process_index} 完成，共处理 {processed_count} 个股票，找到 {len(total_results)} 个符合条件的日期，结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}，运行时长: {duration}"
    log_to_file(completion_msg)
    logging.info(completion_msg)
    
    # 将结果放入结果队列（使用非阻塞方式避免卡住）
    put_start_msg = f"进程 {process_index} 开始将结果放入队列，结果数量: {len(total_results)}"
    log_to_file(put_start_msg)
    logging.info(put_start_msg)
    
    try:
        result_queue.put(total_results, timeout=5)
        exit_msg = f"进程 {process_index} 已将结果放入队列，准备退出"
        log_to_file(exit_msg)
        logging.info(exit_msg)
    except Exception as e:
        error_msg = f"进程 {process_index} 放入结果队列失败: {e}，但仍将退出"
        log_to_file(error_msg)
        logging.warning(error_msg)
    
    # 确保进程正常退出
    final_msg = f"进程 {process_index} 函数执行完毕，即将退出"
    log_to_file(final_msg)
    logging.info(final_msg)

def run_stock_selection_strategy_dynamic(data_folder_path, output_file_path, num_processes=20, limit=None):
    """
    动态批量运行选股策略，使用多进程和任务队列实现动态负载均衡
    
    Args:
        data_folder_path: 股票数据文件夹路径
        output_file_path: 输出结果CSV文件路径
        num_processes: 进程数量，默认20
        limit: 限制处理的股票数量，None表示处理所有股票
    """
    logging.info(f"开始动态批量运行选股策略，使用 {num_processes} 个进程...")
    
    # 获取所有股票文件夹
    all_stock_folders = []
    for item in os.listdir(data_folder_path):
        item_path = os.path.join(data_folder_path, item)
        if os.path.isdir(item_path) and item.startswith('stock_') and item.endswith('_data'):
            all_stock_folders.append(item)
    
    logging.info(f"找到 {len(all_stock_folders)} 个股票文件夹")
    
    # 先过滤出符合条件的股票（以0、3、60开头）
    filtered_stock_folders = []
    for stock_folder in all_stock_folders:
        stock_code = stock_folder.replace('stock_', '').replace('_data', '')
        if stock_code.startswith('0') or stock_code.startswith('3') or stock_code.startswith('60'):
            filtered_stock_folders.append(stock_folder)
    
    logging.info(f"过滤后符合条件的股票: {len(filtered_stock_folders)} 个")
    
    # 如果设置了limit参数，限制处理的股票数量
    if limit is not None and limit > 0:
        if limit < len(filtered_stock_folders):
            filtered_stock_folders = filtered_stock_folders[:limit]
            logging.info(f"根据limit参数限制，实际处理股票数量: {len(filtered_stock_folders)} 个")
        else:
            logging.info(f"limit参数({limit})大于等于可用股票数量({len(filtered_stock_folders)})，处理所有股票")
    
    if not filtered_stock_folders:
        logging.warning("没有找到符合条件的股票文件夹")
        return
    
    # 创建任务队列和结果队列
    task_queue = JoinableQueue()
    result_queue = Queue(maxsize=num_processes * 2)  # 设置结果队列大小，避免无限制增长
    
    # 将所有股票任务放入队列
    for stock_folder in filtered_stock_folders:
        task_queue.put(stock_folder)
    
    logging.info(f"已将 {len(filtered_stock_folders)} 个股票任务放入队列")
    
    # 创建并启动进程
    processes = []
    for i in range(num_processes):
        p = Process(target=process_stock_dynamic, 
                   args=(task_queue, result_queue, data_folder_path, i+1))
        p.start()
        processes.append(p)
        logging.info(f"进程 {i+1} (PID: {p.pid}) 已启动")
    
    logging.info(f"已启动 {num_processes} 个进程进行动态处理")
    
    # 等待所有任务完成
    logging.info("等待所有任务完成...")
    task_queue.join()
    logging.info("所有任务已完成，开始收集结果并终止进程")
    
    # 等待进程完成结果提交
    logging.info("等待进程完成结果提交...")
    all_selected_dates = []
    result_count = 0
    
    # 给进程足够时间完成最后的结果提交
    import time
    time.sleep(3)
    
    # 收集所有可用的结果
    logging.info("开始收集进程结果...")
    while not result_queue.empty():
        try:
            batch_result = result_queue.get_nowait()
            all_selected_dates.extend(batch_result)
            result_count += 1
            logging.info(f"收集到结果批次 {result_count}，当前总结果数: {len(all_selected_dates)}")
        except:
            break
    
    # 再等待一下，确保所有进程都有机会提交结果
    if result_count == 0:
        logging.info("第一次未收集到结果，再等待2秒...")
        time.sleep(2)
        while not result_queue.empty():
            try:
                batch_result = result_queue.get_nowait()
                all_selected_dates.extend(batch_result)
                result_count += 1
                logging.info(f"延迟收集到结果批次 {result_count}，当前总结果数: {len(all_selected_dates)}")
            except:
                break
    
    # 现在强制终止所有进程
    logging.info("开始强制终止所有进程...")
    for i, p in enumerate(processes):
        if p.is_alive():
            logging.info(f"强制终止进程 {i+1} (PID: {p.pid})")
            p.terminate()
            p.join(timeout=3)  # 给一点时间让进程清理
            if p.is_alive():
                logging.warning(f"进程 {i+1} (PID: {p.pid}) 仍未结束，使用kill")
                p.kill()
        else:
            logging.info(f"进程 {i+1} (PID: {p.pid}) 已自然结束")
    
    logging.info("所有进程已完成")
    logging.info(f"结果收集完成！共收集了 {result_count} 个进程的结果")
    logging.info(f"动态处理完成！总共找到 {len(all_selected_dates)} 个符合条件的日期")
    
    # 保存结果到CSV文件
    if all_selected_dates:
        result_df = pd.DataFrame(all_selected_dates)
        
        # 按日期排序
        result_df = result_df.sort_values('date').reset_index(drop=True)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        result_df.to_csv(output_file_path, index=False, encoding='utf-8')
        logging.info(f"结果已保存到: {output_file_path}")
        
        # 统计信息
        logging.info("统计信息:")
        logging.info(f"总共符合条件的交易日数: {len(all_selected_dates)}")
        logging.info(f"涉及股票数: {result_df['stock_code'].nunique()}")
        
        # 计算关键比例统计
        total_count = len(result_df)
        next_open_up_count = len(result_df[result_df['next_open_change_pct'] > 0])
        next_close_up_count = len(result_df[result_df['next_close_change_pct'] > 0])
        day3_up_count = len(result_df[(result_df['day3_change_pct'] > 0) & pd.notna(result_df['day3_change_pct'])])
        day5_up_count = len(result_df[result_df['day5_change_pct'] > 0])
        day10_up_count = len(result_df[result_df['day10_change_pct'] > 0])
        
        # 筛选次日高开高走的股票（次日开盘上涨且收盘也上涨）
        next_high_open_high_close = result_df[(result_df['next_open_change_pct'] > 0) & (result_df['next_close_change_pct'] > 0)]
        high_open_high_close_count = len(next_high_open_high_close)
        
        # 筛选次日低开收盘上涨的股票（次日开盘下跌但收盘上涨）
        next_low_open_close_up = result_df[(result_df['next_open_change_pct'] < 0) & (result_df['next_close_change_pct'] > 0)]
        low_open_close_up_count = len(next_low_open_close_up)
        
        # 筛选次日低开低走的股票（次日开盘下跌且收盘也下跌）
        next_low_open_low_close = result_df[(result_df['next_open_change_pct'] < 0) & (result_df['next_close_change_pct'] < 0)]
        low_open_low_close_count = len(next_low_open_low_close)
        
        # 筛选次日低开低走的股票（次日开盘下跌且收盘也下跌）
        next_low_open_low_close = result_df[(result_df['next_open_change_pct'] < 0) & (result_df['next_close_change_pct'] < 0)]
        low_open_low_close_count = len(next_low_open_low_close)
        
        # 在次日高开高走的股票中，计算3日、5日、10日收盘上涨的比例
        if high_open_high_close_count > 0:
            high_open_high_close_day3_up = len(next_high_open_high_close[(next_high_open_high_close['day3_change_pct'] > 0) & pd.notna(next_high_open_high_close['day3_change_pct'])])
            high_open_high_close_day5_up = len(next_high_open_high_close[next_high_open_high_close['day5_change_pct'] > 0])
            high_open_high_close_day10_up = len(next_high_open_high_close[next_high_open_high_close['day10_change_pct'] > 0])
        else:
            high_open_high_close_day3_up = 0
            high_open_high_close_day5_up = 0
            high_open_high_close_day10_up = 0
        
        # 在次日低开低走的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_low_close_count > 0:
            low_open_low_close_day3_up = len(next_low_open_low_close[(next_low_open_low_close['day3_change_pct'] > 0) & pd.notna(next_low_open_low_close['day3_change_pct'])])
            low_open_low_close_day5_up = len(next_low_open_low_close[next_low_open_low_close['day5_change_pct'] > 0])
            low_open_low_close_day10_up = len(next_low_open_low_close[next_low_open_low_close['day10_change_pct'] > 0])
        else:
            low_open_low_close_day3_up = 0
            low_open_low_close_day5_up = 0
            low_open_low_close_day10_up = 0
        
        logging.info("关键比例统计:")
        logging.info("次日表现:")
        logging.info(f"  次日高开比例: {next_open_up_count}/{total_count} ({next_open_up_count/total_count*100:.2f}%)")
        logging.info(f"  次日收盘上涨比例: {next_close_up_count}/{total_count} ({next_close_up_count/total_count*100:.2f}%)")
        logging.info(f"  次日高开高走比例: {high_open_high_close_count}/{total_count} ({high_open_high_close_count/total_count*100:.2f}%)")
        logging.info(f"  次日低开收盘上涨比例: {low_open_close_up_count}/{total_count} ({low_open_close_up_count/total_count*100:.2f}%)")
        logging.info(f"  次日低开低走比例: {low_open_low_close_count}/{total_count} ({low_open_low_close_count/total_count*100:.2f}%)")
        logging.info("中长期表现:")
        logging.info(f"  3日收盘上涨比例: {day3_up_count}/{total_count} ({day3_up_count/total_count*100:.2f}%)")
        logging.info(f"  5日收盘上涨比例: {day5_up_count}/{total_count} ({day5_up_count/total_count*100:.2f}%)")
        logging.info(f"  10日收盘上涨比例: {day10_up_count}/{total_count} ({day10_up_count/total_count*100:.2f}%)")
        
        # 在次日高开高走的股票中的统计
        logging.info("\n次日高开高走股票中的后续表现:")
        if high_open_high_close_count > 0:
            logging.info(f"3日收盘上涨比例: {high_open_high_close_day3_up}/{high_open_high_close_count} ({high_open_high_close_day3_up/high_open_high_close_count*100:.2f}%)")
            logging.info(f"5日收盘上涨比例: {high_open_high_close_day5_up}/{high_open_high_close_count} ({high_open_high_close_day5_up/high_open_high_close_count*100:.2f}%)")
            logging.info(f"10日收盘上涨比例: {high_open_high_close_day10_up}/{high_open_high_close_count} ({high_open_high_close_day10_up/high_open_high_close_count*100:.2f}%)")
        else:
            logging.info("无次日高开高走的股票")
        
        # 在次日低开收盘上涨的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_close_up_count > 0:
            low_open_close_up_day3_up = len(next_low_open_close_up[(next_low_open_close_up['day3_change_pct'] > 0) & pd.notna(next_low_open_close_up['day3_change_pct'])])
            low_open_close_up_day5_up = len(next_low_open_close_up[next_low_open_close_up['day5_change_pct'] > 0])
            low_open_close_up_day10_up = len(next_low_open_close_up[next_low_open_close_up['day10_change_pct'] > 0])
        else:
            low_open_close_up_day3_up = 0
            low_open_close_up_day5_up = 0
            low_open_close_up_day10_up = 0
        
        # 在次日低开低走的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_low_close_count > 0:
            low_open_low_close_day3_up = len(next_low_open_low_close[(next_low_open_low_close['day3_change_pct'] > 0) & pd.notna(next_low_open_low_close['day3_change_pct'])])
            low_open_low_close_day5_up = len(next_low_open_low_close[next_low_open_low_close['day5_change_pct'] > 0])
            low_open_low_close_day10_up = len(next_low_open_low_close[next_low_open_low_close['day10_change_pct'] > 0])
        else:
            low_open_low_close_day3_up = 0
            low_open_low_close_day5_up = 0
            low_open_low_close_day10_up = 0
        
        # 在次日低开低走的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_low_close_count > 0:
            low_open_low_close_day3_up = len(next_low_open_low_close[(next_low_open_low_close['day3_change_pct'] > 0) & pd.notna(next_low_open_low_close['day3_change_pct'])])
            low_open_low_close_day5_up = len(next_low_open_low_close[next_low_open_low_close['day5_change_pct'] > 0])
            low_open_low_close_day10_up = len(next_low_open_low_close[next_low_open_low_close['day10_change_pct'] > 0])
        else:
            low_open_low_close_day3_up = 0
            low_open_low_close_day5_up = 0
            low_open_low_close_day10_up = 0
        
        # 在次日低开收盘上涨的股票中的统计
        logging.info("\n次日低开收盘上涨股票中的后续表现:")
        if low_open_close_up_count > 0:
            logging.info(f"3日收盘上涨比例: {low_open_close_up_day3_up}/{low_open_close_up_count} ({low_open_close_up_day3_up/low_open_close_up_count*100:.2f}%)")
            logging.info(f"5日收盘上涨比例: {low_open_close_up_day5_up}/{low_open_close_up_count} ({low_open_close_up_day5_up/low_open_close_up_count*100:.2f}%)")
            logging.info(f"10日收盘上涨比例: {low_open_close_up_day10_up}/{low_open_close_up_count} ({low_open_close_up_day10_up/low_open_close_up_count*100:.2f}%)")
        else:
            logging.info("无次日低开收盘上涨的股票")
        
        # 在次日低开低走的股票中的统计
        logging.info("\n次日低开低走股票中的后续表现:")
        if low_open_low_close_count > 0:
            logging.info(f"3日收盘上涨比例: {low_open_low_close_day3_up}/{low_open_low_close_count} ({low_open_low_close_day3_up/low_open_low_close_count*100:.2f}%)")
            logging.info(f"5日收盘上涨比例: {low_open_low_close_day5_up}/{low_open_low_close_count} ({low_open_low_close_day5_up/low_open_low_close_count*100:.2f}%)")
            logging.info(f"10日收盘上涨比例: {low_open_low_close_day10_up}/{low_open_low_close_count} ({low_open_low_close_day10_up/low_open_low_close_count*100:.2f}%)")
        else:
            logging.info("无次日低开低走的股票")
        
        # 计算平均涨跌幅
        logging.info("平均涨跌幅统计:")
        logging.info(f"次日开盘平均涨跌幅: {result_df['next_open_change_pct'].mean():.2f}%")
        logging.info(f"次日收盘平均涨跌幅: {result_df['next_close_change_pct'].mean():.2f}%")
        logging.info(f"3日收盘平均涨跌幅: {result_df['day3_change_pct'].mean():.2f}%")
        logging.info(f"5日收盘平均涨跌幅: {result_df['day5_change_pct'].mean():.2f}%")
        logging.info(f"10日收盘平均涨跌幅: {result_df['day10_change_pct'].mean():.2f}%")
        
        # 筛选3日上涨的最后10条数据
        day3_up_df = result_df[(result_df['day3_change_pct'] > 0) & pd.notna(result_df['day3_change_pct'])].tail(10)
        logging.info("3日上涨的最后10条数据:")
        if not day3_up_df.empty:
            for _, row in day3_up_df.iterrows():
                day3_str = f"{row['day3_change_pct']:.2f}%" if pd.notna(row['day3_change_pct']) else "N/A"
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 3日:{day3_str} 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 筛选5日上涨的最后10条数据
        day5_up_df = result_df[(result_df['day5_change_pct'] > 0) & pd.notna(result_df['day5_change_pct'])].tail(10)
        logging.info("5日上涨的最后10条数据:")
        if not day5_up_df.empty:
            for _, row in day5_up_df.iterrows():
                day3_str = f"{row['day3_change_pct']:.2f}%" if pd.notna(row['day3_change_pct']) else "N/A"
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 3日:{day3_str} 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 筛选3日下跌的最后10条数据
        day3_down_df = result_df[(result_df['day3_change_pct'] < 0) & pd.notna(result_df['day3_change_pct'])].tail(10)
        logging.info("3日下跌的最后10条数据:")
        if not day3_down_df.empty:
            for _, row in day3_down_df.iterrows():
                day3_str = f"{row['day3_change_pct']:.2f}%" if pd.notna(row['day3_change_pct']) else "N/A"
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 3日:{day3_str} 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 筛选5日下跌的最后10条数据
        day5_down_df = result_df[(result_df['day5_change_pct'] < 0) & pd.notna(result_df['day5_change_pct'])].tail(10)
        logging.info("5日下跌的最后10条数据:")
        if not day5_down_df.empty:
            for _, row in day5_down_df.iterrows():
                day3_str = f"{row['day3_change_pct']:.2f}%" if pd.notna(row['day3_change_pct']) else "N/A"
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 3日:{day3_str} 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 将回测结果写入final_result文件
        write_backtest_result_to_file(total_count, next_open_up_count, next_close_up_count, 
                                    high_open_high_close_count, day5_up_count, day10_up_count,
                                    high_open_high_close_day5_up, high_open_high_close_day10_up,
                                    low_open_close_up_count, low_open_close_up_day3_up,
                                    low_open_close_up_day5_up, low_open_close_up_day10_up,
                                    low_open_low_close_count, low_open_low_close_day3_up,
                                    low_open_low_close_day5_up, low_open_low_close_day10_up,
                                    result_df)
    else:
        logging.warning("没有找到符合条件的交易日")
        # 创建空的CSV文件
        empty_df = pd.DataFrame(columns=['stock_code', 'date', 'open', 'close', 'low', 'ma5', 'ma10', 'ma20', 'ma30',
                                       'next_open', 'next_close', 'next_open_change_pct', 'next_close_change_pct',
                                       'day5_close', 'day5_change_pct', 'day10_close', 'day10_change_pct'])
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        empty_df.to_csv(output_file_path, index=False, encoding='utf-8')
        logging.info(f"空结果文件已保存到: {output_file_path}")
        
        # 即使没有符合条件的数据，也要写入回测结果
        write_backtest_result_to_file(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, empty_df)

def run_stock_selection_strategy_batch(data_folder_path, output_file_path, num_processes=20):
    """
    批量运行选股策略，使用多进程遍历所有股票
    
    Args:
        data_folder_path: 股票数据文件夹路径
        output_file_path: 输出结果CSV文件路径
        num_processes: 进程数量，默认20
    """
    logging.info(f"开始批量运行选股策略，使用 {num_processes} 个进程...")
    
    # 获取所有股票文件夹
    all_stock_folders = []
    for item in os.listdir(data_folder_path):
        item_path = os.path.join(data_folder_path, item)
        if os.path.isdir(item_path) and item.startswith('stock_') and item.endswith('_data'):
            all_stock_folders.append(item)
    
    logging.info(f"找到 {len(all_stock_folders)} 个股票文件夹")
    
    # 先过滤出符合条件的股票（以0、3、60开头）
    filtered_stock_folders = []
    for stock_folder in all_stock_folders:
        stock_code = stock_folder.replace('stock_', '').replace('_data', '')
        if stock_code.startswith('0') or stock_code.startswith('3') or stock_code.startswith('60'):
            filtered_stock_folders.append(stock_folder)
    
    logging.info(f"过滤后符合条件的股票: {len(filtered_stock_folders)} 个")
    
    if not filtered_stock_folders:
        logging.warning("没有找到符合条件的股票文件夹")
        return
    
    # 将过滤后的股票文件夹分成固定数量的批次（20组）
    stock_batches = [[] for _ in range(num_processes)]
    
    # 将股票均匀分配到各个批次中
    for i, stock_folder in enumerate(filtered_stock_folders):
        batch_index = i % num_processes
        stock_batches[batch_index].append(stock_folder)
    
    # 记录每个批次的股票数量
    batch_info = []
    for i, batch in enumerate(stock_batches):
        batch_info.append(f"批次{i+1}: {len(batch)}个股票")
    
    logging.info(f"将 {len(filtered_stock_folders)} 只股票分成 {num_processes} 个批次进行处理")
    logging.info(f"批次分配详情: {', '.join(batch_info)}")
    
    # 使用多进程处理
    with mp.Pool(processes=num_processes) as pool:
        # 创建部分函数，固定data_folder_path参数，并为每个批次分配进程序号
        process_args = [(batch, data_folder_path, i+1) for i, batch in enumerate(stock_batches)]
        
        # 并行处理所有批次
        logging.info("开始多进程处理...")
        batch_results = pool.starmap(process_stock_batch, process_args)
    
    # 合并所有结果
    all_selected_dates = []
    for batch_result in batch_results:
        all_selected_dates.extend(batch_result)
    
    logging.info(f"处理完成！总共找到 {len(all_selected_dates)} 个符合条件的日期")
    
    # 保存结果到CSV文件
    if all_selected_dates:
        result_df = pd.DataFrame(all_selected_dates)
        
        # 按日期排序
        result_df = result_df.sort_values('date').reset_index(drop=True)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        result_df.to_csv(output_file_path, index=False, encoding='utf-8')
        logging.info(f"结果已保存到: {output_file_path}")
        
        # 统计信息
        logging.info("统计信息:")
        logging.info(f"总共符合条件的交易日数: {len(all_selected_dates)}")
        logging.info(f"涉及股票数: {result_df['stock_code'].nunique()}")
        
        # 计算关键比例统计
        total_count = len(result_df)
        next_open_up_count = len(result_df[result_df['next_open_change_pct'] > 0])
        next_close_up_count = len(result_df[result_df['next_close_change_pct'] > 0])
        day5_up_count = len(result_df[result_df['day5_change_pct'] > 0])
        day10_up_count = len(result_df[result_df['day10_change_pct'] > 0])
        
        # 筛选次日高开高走的股票（次日开盘上涨且收盘也上涨）
        next_high_open_high_close = result_df[(result_df['next_open_change_pct'] > 0) & (result_df['next_close_change_pct'] > 0)]
        high_open_high_close_count = len(next_high_open_high_close)
        
        # 筛选次日低开收盘上涨的股票（次日开盘下跌但收盘上涨）
        next_low_open_close_up = result_df[(result_df['next_open_change_pct'] < 0) & (result_df['next_close_change_pct'] > 0)]
        low_open_close_up_count = len(next_low_open_close_up)
        
        # 筛选次日低开低走的股票（次日开盘下跌且收盘也下跌）
        next_low_open_low_close = result_df[(result_df['next_open_change_pct'] < 0) & (result_df['next_close_change_pct'] < 0)]
        low_open_low_close_count = len(next_low_open_low_close)
        
        # 在次日高开高走的股票中，计算5日、10日收盘上涨的比例
        if high_open_high_close_count > 0:
            high_open_high_close_day5_up = len(next_high_open_high_close[next_high_open_high_close['day5_change_pct'] > 0])
            high_open_high_close_day10_up = len(next_high_open_high_close[next_high_open_high_close['day10_change_pct'] > 0])
        else:
            high_open_high_close_day5_up = 0
            high_open_high_close_day10_up = 0
        
        logging.info("关键比例统计:")
        logging.info("次日表现:")
        logging.info(f"  次日高开比例: {next_open_up_count}/{total_count} ({next_open_up_count/total_count*100:.2f}%)")
        logging.info(f"  次日收盘上涨比例: {next_close_up_count}/{total_count} ({next_close_up_count/total_count*100:.2f}%)")
        logging.info(f"  次日高开高走比例: {high_open_high_close_count}/{total_count} ({high_open_high_close_count/total_count*100:.2f}%)")
        logging.info(f"  次日低开收盘上涨比例: {low_open_close_up_count}/{total_count} ({low_open_close_up_count/total_count*100:.2f}%)")
        logging.info(f"  次日低开低走比例: {low_open_low_close_count}/{total_count} ({low_open_low_close_count/total_count*100:.2f}%)")
        logging.info("中长期表现:")
        logging.info(f"  5日收盘上涨比例: {day5_up_count}/{total_count} ({day5_up_count/total_count*100:.2f}%)")
        logging.info(f"  10日收盘上涨比例: {day10_up_count}/{total_count} ({day10_up_count/total_count*100:.2f}%)")
        
        # 在次日高开高走的股票中的统计
        logging.info("\n次日高开高走股票中的后续表现:")
        if high_open_high_close_count > 0:
            logging.info(f"5日收盘上涨比例: {high_open_high_close_day5_up}/{high_open_high_close_count} ({high_open_high_close_day5_up/high_open_high_close_count*100:.2f}%)")
            logging.info(f"10日收盘上涨比例: {high_open_high_close_day10_up}/{high_open_high_close_count} ({high_open_high_close_day10_up/high_open_high_close_count*100:.2f}%)")
        else:
            logging.info("无次日高开高走的股票")
        
        # 在次日低开收盘上涨的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_close_up_count > 0:
            low_open_close_up_day3_up = len(next_low_open_close_up[(next_low_open_close_up['day3_change_pct'] > 0) & pd.notna(next_low_open_close_up['day3_change_pct'])])
            low_open_close_up_day5_up = len(next_low_open_close_up[next_low_open_close_up['day5_change_pct'] > 0])
            low_open_close_up_day10_up = len(next_low_open_close_up[next_low_open_close_up['day10_change_pct'] > 0])
        else:
            low_open_close_up_day3_up = 0
            low_open_close_up_day5_up = 0
            low_open_close_up_day10_up = 0
        
        # 在次日低开低走的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_low_close_count > 0:
            low_open_low_close_day3_up = len(next_low_open_low_close[(next_low_open_low_close['day3_change_pct'] > 0) & pd.notna(next_low_open_low_close['day3_change_pct'])])
            low_open_low_close_day5_up = len(next_low_open_low_close[next_low_open_low_close['day5_change_pct'] > 0])
            low_open_low_close_day10_up = len(next_low_open_low_close[next_low_open_low_close['day10_change_pct'] > 0])
        else:
            low_open_low_close_day3_up = 0
            low_open_low_close_day5_up = 0
            low_open_low_close_day10_up = 0
        
        # 在次日低开收盘上涨的股票中的统计
        logging.info("\n次日低开收盘上涨股票中的后续表现:")
        if low_open_close_up_count > 0:
            logging.info(f"3日收盘上涨比例: {low_open_close_up_day3_up}/{low_open_close_up_count} ({low_open_close_up_day3_up/low_open_close_up_count*100:.2f}%)")
            logging.info(f"5日收盘上涨比例: {low_open_close_up_day5_up}/{low_open_close_up_count} ({low_open_close_up_day5_up/low_open_close_up_count*100:.2f}%)")
            logging.info(f"10日收盘上涨比例: {low_open_close_up_day10_up}/{low_open_close_up_count} ({low_open_close_up_day10_up/low_open_close_up_count*100:.2f}%)")
        else:
            logging.info("无次日低开收盘上涨的股票")
        
        # 在次日低开低走的股票中的统计
        logging.info("\n次日低开低走股票中的后续表现:")
        if low_open_low_close_count > 0:
            logging.info(f"3日收盘上涨比例: {low_open_low_close_day3_up}/{low_open_low_close_count} ({low_open_low_close_day3_up/low_open_low_close_count*100:.2f}%)")
            logging.info(f"5日收盘上涨比例: {low_open_low_close_day5_up}/{low_open_low_close_count} ({low_open_low_close_day5_up/low_open_low_close_count*100:.2f}%)")
            logging.info(f"10日收盘上涨比例: {low_open_low_close_day10_up}/{low_open_low_close_count} ({low_open_low_close_day10_up/low_open_low_close_count*100:.2f}%)")
        else:
            logging.info("无次日低开低走的股票")
        
        # 计算平均涨跌幅
        logging.info("平均涨跌幅统计:")
        logging.info(f"次日开盘平均涨跌幅: {result_df['next_open_change_pct'].mean():.2f}%")
        logging.info(f"次日收盘平均涨跌幅: {result_df['next_close_change_pct'].mean():.2f}%")
        logging.info(f"5日收盘平均涨跌幅: {result_df['day5_change_pct'].mean():.2f}%")
        logging.info(f"10日收盘平均涨跌幅: {result_df['day10_change_pct'].mean():.2f}%")
        
        # 筛选5日上涨的最后10条数据
        day5_up_df = result_df[(result_df['day5_change_pct'] > 0) & pd.notna(result_df['day5_change_pct'])].tail(10)
        logging.info("5日上涨的最后10条数据:")
        if not day5_up_df.empty:
            for _, row in day5_up_df.iterrows():
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 筛选5日下跌的最后10条数据
        day5_down_df = result_df[(result_df['day5_change_pct'] < 0) & pd.notna(result_df['day5_change_pct'])].tail(10)
        logging.info("5日下跌的最后10条数据:")
        if not day5_down_df.empty:
            for _, row in day5_down_df.iterrows():
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 将回测结果写入final_result文件
        write_backtest_result_to_file(total_count, next_open_up_count, next_close_up_count, 
                                    high_open_high_close_count, day5_up_count, day10_up_count,
                                    high_open_high_close_day5_up, high_open_high_close_day10_up,
                                    low_open_close_up_count, low_open_close_up_day3_up,
                                    low_open_close_up_day5_up, low_open_close_up_day10_up,
                                    low_open_low_close_count, low_open_low_close_day3_up,
                                    low_open_low_close_day5_up, low_open_low_close_day10_up,
                                    result_df)
    else:
        logging.warning("没有找到符合条件的交易日")
        # 创建空的CSV文件
        empty_df = pd.DataFrame(columns=['stock_code', 'date', 'open', 'close', 'low', 'ma5', 'ma10', 'ma20', 'ma30', 'next_open', 'next_close', 'next_open_change_pct', 'next_close_change_pct', 'day3_close', 'day3_change_pct', 'day5_close', 'day5_change_pct', 'day10_close', 'day10_change_pct'])
        empty_df.to_csv(output_file_path, index=False, encoding='utf-8')
        logging.info(f"空结果文件已保存到: {output_file_path}")
        
        # 即使没有符合条件的数据，也要写入回测结果
        write_backtest_result_to_file(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, empty_df)

def write_backtest_result_to_file(total_count, next_open_up_count, next_close_up_count, 
                                 high_open_high_close_count, day5_up_count, day10_up_count,
                                 high_open_high_close_day5_up, high_open_high_close_day10_up,
                                 low_open_close_up_count, low_open_close_up_day3_up, 
                                 low_open_close_up_day5_up, low_open_close_up_day10_up,
                                 low_open_low_close_count, low_open_low_close_day3_up,
                                 low_open_low_close_day5_up, low_open_low_close_day10_up,
                                 result_df):
    """
    将回测结果以增量方式写入final_result文件
    
    Args:
        total_count: 总交易日数
        next_open_up_count: 次日高开数量
        next_close_up_count: 次日收盘上涨数量
        high_open_high_close_count: 次日高开高走数量
        day5_up_count: 5日收盘上涨数量
        day10_up_count: 10日收盘上涨数量
        high_open_high_close_day5_up: 次日高开高走中5日上涨数量
        high_open_high_close_day10_up: 次日高开高走中10日上涨数量
        low_open_close_up_count: 次日低开收盘上涨数量
        low_open_close_up_day3_up: 次日低开收盘上涨中3日上涨数量
        low_open_close_up_day5_up: 次日低开收盘上涨中5日上涨数量
        low_open_close_up_day10_up: 次日低开收盘上涨中10日上涨数量
        low_open_low_close_count: 次日低开低走数量
        low_open_low_close_day3_up: 次日低开低走中3日上涨数量
        low_open_low_close_day5_up: 次日低开低走中5日上涨数量
        low_open_low_close_day10_up: 次日低开低走中10日上涨数量
        result_df: 结果DataFrame
    """
    try:
        # 获取当前时间戳
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 使用统一的策略条件定义
        strategy_conditions = STRATEGY_CONDITIONS
        
        # 计算百分比，避免除零错误
        next_open_up_pct = (next_open_up_count/total_count*100) if total_count > 0 else 0.00
        next_close_up_pct = (next_close_up_count/total_count*100) if total_count > 0 else 0.00
        high_open_high_close_pct = (high_open_high_close_count/total_count*100) if total_count > 0 else 0.00
        low_open_close_up_pct = (low_open_close_up_count/total_count*100) if total_count > 0 else 0.00
        day3_up_count = len(result_df[result_df['day3_change_pct'] > 0]) if len(result_df) > 0 else 0
        day3_up_pct = (day3_up_count/total_count*100) if total_count > 0 else 0.00
        day5_up_pct = (day5_up_count/total_count*100) if total_count > 0 else 0.00
        day10_up_pct = (day10_up_count/total_count*100) if total_count > 0 else 0.00
        
        high_open_high_close_day3_up_count = len(result_df[(result_df['next_open_change_pct'] > 0) & (result_df['next_close_change_pct'] > 0) & (result_df['day3_change_pct'] > 0)]) if len(result_df) > 0 else 0
        high_open_high_close_day3_up_pct = (high_open_high_close_day3_up_count/high_open_high_close_count*100) if high_open_high_close_count > 0 else 0.00
        high_open_high_close_day5_up_pct = (high_open_high_close_day5_up/high_open_high_close_count*100) if high_open_high_close_count > 0 else 0.00
        high_open_high_close_day10_up_pct = (high_open_high_close_day10_up/high_open_high_close_count*100) if high_open_high_close_count > 0 else 0.00
        
        # 计算次日低开收盘上涨的百分比
        low_open_close_up_day3_up_pct = (low_open_close_up_day3_up/low_open_close_up_count*100) if low_open_close_up_count > 0 else 0.00
        low_open_close_up_day5_up_pct = (low_open_close_up_day5_up/low_open_close_up_count*100) if low_open_close_up_count > 0 else 0.00
        low_open_close_up_day10_up_pct = (low_open_close_up_day10_up/low_open_close_up_count*100) if low_open_close_up_count > 0 else 0.00
        
        # 计算次日低开低走的百分比
        low_open_low_close_pct = (low_open_low_close_count/total_count*100) if total_count > 0 else 0.00
        low_open_low_close_day3_up_pct = (low_open_low_close_day3_up/low_open_low_close_count*100) if low_open_low_close_count > 0 else 0.00
        low_open_low_close_day5_up_pct = (low_open_low_close_day5_up/low_open_low_close_count*100) if low_open_low_close_count > 0 else 0.00
        low_open_low_close_day10_up_pct = (low_open_low_close_day10_up/low_open_low_close_count*100) if low_open_low_close_count > 0 else 0.00
        
        # 构建统计信息
        statistics_info = f"""
统计信息:
总共符合条件的交易日数: {total_count}
涉及股票数: {result_df['stock_code'].nunique() if len(result_df) > 0 else 0}
关键比例统计:
次日表现:
  次日高开比例: {next_open_up_count}/{total_count} ({next_open_up_pct:.2f}%)
  次日收盘上涨比例: {next_close_up_count}/{total_count} ({next_close_up_pct:.2f}%)
  次日高开高走比例: {high_open_high_close_count}/{total_count} ({high_open_high_close_pct:.2f}%)
  次日低开收盘上涨比例: {low_open_close_up_count}/{total_count} ({low_open_close_up_pct:.2f}%)
  次日低开低走比例: {low_open_low_close_count}/{total_count} ({low_open_low_close_pct:.2f}%)
中长期表现:
  3日收盘上涨比例: {day3_up_count}/{total_count} ({day3_up_pct:.2f}%)
  5日收盘上涨比例: {day5_up_count}/{total_count} ({day5_up_pct:.2f}%)
  10日收盘上涨比例: {day10_up_count}/{total_count} ({day10_up_pct:.2f}%)

次日高开高走股票中的后续表现:
3日收盘上涨比例: {high_open_high_close_day3_up_count}/{high_open_high_close_count} ({high_open_high_close_day3_up_pct:.2f}%)
5日收盘上涨比例: {high_open_high_close_day5_up}/{high_open_high_close_count} ({high_open_high_close_day5_up_pct:.2f}%)
10日收盘上涨比例: {high_open_high_close_day10_up}/{high_open_high_close_count} ({high_open_high_close_day10_up_pct:.2f}%)

次日低开收盘上涨股票中的后续表现:
3日收盘上涨比例: {low_open_close_up_day3_up}/{low_open_close_up_count} ({low_open_close_up_day3_up_pct:.2f}%)
5日收盘上涨比例: {low_open_close_up_day5_up}/{low_open_close_up_count} ({low_open_close_up_day5_up_pct:.2f}%)
10日收盘上涨比例: {low_open_close_up_day10_up}/{low_open_close_up_count} ({low_open_close_up_day10_up_pct:.2f}%)

次日低开低走股票中的后续表现:
3日收盘上涨比例: {low_open_low_close_day3_up}/{low_open_low_close_count} ({low_open_low_close_day3_up_pct:.2f}%)
5日收盘上涨比例: {low_open_low_close_day5_up}/{low_open_low_close_count} ({low_open_low_close_day5_up_pct:.2f}%)
10日收盘上涨比例: {low_open_low_close_day10_up}/{low_open_low_close_count} ({low_open_low_close_day10_up_pct:.2f}%)"""
        
        # 构建完整的回测记录
        backtest_record = f"""
{'='*80}
回测时间: {current_time}
{strategy_conditions}
{statistics_info}
{'='*80}

"""
        
        # 确定final_result文件路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        final_result_path = os.path.join(os.path.dirname(script_dir), "final_result")
        
        # 以追加模式写入文件，确保使用UTF-8编码（不使用BOM）
        with open(final_result_path, 'a', encoding='utf-8') as f:
            f.write(backtest_record)
        
        logging.info(f"回测结果已追加写入: {final_result_path}")
        
    except Exception as e:
        logging.error(f"写入final_result文件失败: {e}")

def test_single_stock(stock_code, data_folder_path, verbose=True):
    """
    测试单个股票的策略逻辑
    
    Args:
        stock_code: 股票代码，如 '301379'
        data_folder_path: 股票数据文件夹路径
        verbose: 是否打印详细的策略判断信息
    """
    logging.info(f"开始测试单个股票: {stock_code}")
    
    # 构建股票文件夹名称
    stock_folder_name = f"stock_{stock_code}_data"
    
    # 测试单个股票，启用详细模式
    results = process_single_stock(stock_folder_name, data_folder_path, process_index=1, verbose=verbose)
    
    if results:
        logging.info(f"股票 {stock_code} 找到 {len(results)} 个符合条件的交易日:")
        
        # 显示前10个结果的详细信息
        for i, result in enumerate(results[:10]):
            logging.info(f"  {i+1}. {result['date']} - 开盘:{result['open']:.2f} 收盘:{result['close']:.2f} 最低:{result['low']:.2f} MA30:{result['ma30']:.2f}")
            logging.info(f"     次日开盘变化:{result['next_open_change_pct']:.2f}% 次日收盘变化:{result['next_close_change_pct']:.2f}%")
            if result['day3_change_pct'] is not None:
                logging.info(f"     3日变化:{result['day3_change_pct']:.2f}% 5日变化:{result['day5_change_pct']:.2f}% 10日变化:{result['day10_change_pct']:.2f}%")
        
        if len(results) > 10:
            logging.info(f"  ... 还有 {len(results) - 10} 个结果")
        
        # 保存单股票测试结果
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, f"test_{stock_code}.csv")
        
        result_df = pd.DataFrame(results)
        result_df.to_csv(output_file, index=False, encoding='utf-8')
        logging.info(f"测试结果已保存到: {output_file}")
        
        # 统计信息
        next_open_up = len([r for r in results if r['next_open_change_pct'] > 0])
        next_close_up = len([r for r in results if r['next_close_change_pct'] > 0])
        day3_up = len([r for r in results if r['day3_change_pct'] is not None and r['day3_change_pct'] > 0])
        day5_up = len([r for r in results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0])
        day10_up = len([r for r in results if r['day10_change_pct'] is not None and r['day10_change_pct'] > 0])
        
        # 筛选次日高开高走的股票
        high_open_high_close_results = [r for r in results if r['next_open_change_pct'] > 0 and r['next_close_change_pct'] > 0]
        high_open_high_close_count = len(high_open_high_close_results)
        
        # 在次日高开高走的股票中，计算3日、5日、10日收盘上涨的比例
        if high_open_high_close_count > 0:
            high_open_high_close_day3_up = len([r for r in high_open_high_close_results if r['day3_change_pct'] is not None and r['day3_change_pct'] > 0])
            high_open_high_close_day5_up = len([r for r in high_open_high_close_results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0])
            high_open_high_close_day10_up = len([r for r in high_open_high_close_results if r['day10_change_pct'] is not None and r['day10_change_pct'] > 0])
        else:
            high_open_high_close_day3_up = 0
            high_open_high_close_day5_up = 0
            high_open_high_close_day10_up = 0
        
        # 筛选次日低开收盘上涨的股票
        low_open_close_up_results = [r for r in results if r['next_open_change_pct'] < 0 and r['next_close_change_pct'] > 0]
        low_open_close_up_count = len(low_open_close_up_results)
        
        # 筛选次日低开低走的股票
        low_open_low_close_results = [r for r in results if r['next_open_change_pct'] < 0 and r['next_close_change_pct'] < 0]
        low_open_low_close_count = len(low_open_low_close_results)
        
        logging.info(f"统计信息:")
        logging.info("次日表现:")
        logging.info(f"  次日高开比例: {next_open_up}/{len(results)} ({next_open_up/len(results)*100:.2f}%)")
        logging.info(f"  次日收盘上涨比例: {next_close_up}/{len(results)} ({next_close_up/len(results)*100:.2f}%)")
        logging.info(f"  次日高开高走比例: {high_open_high_close_count}/{len(results)} ({high_open_high_close_count/len(results)*100:.2f}%)")
        logging.info(f"  次日低开收盘上涨比例: {low_open_close_up_count}/{len(results)} ({low_open_close_up_count/len(results)*100:.2f}%)")
        logging.info(f"  次日低开低走比例: {low_open_low_close_count}/{len(results)} ({low_open_low_close_count/len(results)*100:.2f}%)")
        logging.info("中长期表现:")
        logging.info(f"  3日上涨比例: {day3_up}/{len(results)} ({day3_up/len(results)*100:.2f}%)")
        logging.info(f"  5日上涨比例: {day5_up}/{len(results)} ({day5_up/len(results)*100:.2f}%)")
        logging.info(f"  10日上涨比例: {day10_up}/{len(results)} ({day10_up/len(results)*100:.2f}%)")
        
        # 在次日高开高走的股票中的统计
        logging.info(f"\n次日高开高走股票中的后续表现:")
        if high_open_high_close_count > 0:
            logging.info(f"  3日收盘上涨比例: {high_open_high_close_day3_up}/{high_open_high_close_count} ({high_open_high_close_day3_up/high_open_high_close_count*100:.2f}%)")
            logging.info(f"  5日收盘上涨比例: {high_open_high_close_day5_up}/{high_open_high_close_count} ({high_open_high_close_day5_up/high_open_high_close_count*100:.2f}%)")
            logging.info(f"  10日收盘上涨比例: {high_open_high_close_day10_up}/{high_open_high_close_count} ({high_open_high_close_day10_up/high_open_high_close_count*100:.2f}%)")
        else:
            logging.info(f"  无次日高开高走的股票")
        
        # 在次日低开收盘上涨的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_close_up_count > 0:
            low_open_close_up_day3_up = len([r for r in low_open_close_up_results if r['day3_change_pct'] is not None and r['day3_change_pct'] > 0])
            low_open_close_up_day5_up = len([r for r in low_open_close_up_results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0])
            low_open_close_up_day10_up = len([r for r in low_open_close_up_results if r['day10_change_pct'] is not None and r['day10_change_pct'] > 0])
        else:
            low_open_close_up_day3_up = 0
            low_open_close_up_day5_up = 0
            low_open_close_up_day10_up = 0
        
        # 在次日低开收盘上涨的股票中的统计
        logging.info(f"\n次日低开收盘上涨股票中的后续表现:")
        if low_open_close_up_count > 0:
            logging.info(f"  3日收盘上涨比例: {low_open_close_up_day3_up}/{low_open_close_up_count} ({low_open_close_up_day3_up/low_open_close_up_count*100:.2f}%)")
            logging.info(f"  5日收盘上涨比例: {low_open_close_up_day5_up}/{low_open_close_up_count} ({low_open_close_up_day5_up/low_open_close_up_count*100:.2f}%)")
            logging.info(f"  10日收盘上涨比例: {low_open_close_up_day10_up}/{low_open_close_up_count} ({low_open_close_up_day10_up/low_open_close_up_count*100:.2f}%)")
        else:
            logging.info(f"  无次日低开收盘上涨的股票")
        
        # 在次日低开低走的股票中，计算3日、5日、10日收盘上涨的比例
        if low_open_low_close_count > 0:
            low_open_low_close_day3_up = len([r for r in low_open_low_close_results if r['day3_change_pct'] is not None and r['day3_change_pct'] > 0])
            low_open_low_close_day5_up = len([r for r in low_open_low_close_results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0])
            low_open_low_close_day10_up = len([r for r in low_open_low_close_results if r['day10_change_pct'] is not None and r['day10_change_pct'] > 0])
        else:
            low_open_low_close_day3_up = 0
            low_open_low_close_day5_up = 0
            low_open_low_close_day10_up = 0
        
        # 在次日低开低走的股票中的统计
        logging.info(f"\n次日低开低走股票中的后续表现:")
        if low_open_low_close_count > 0:
            logging.info(f"  3日收盘上涨比例: {low_open_low_close_day3_up}/{low_open_low_close_count} ({low_open_low_close_day3_up/low_open_low_close_count*100:.2f}%)")
            logging.info(f"  5日收盘上涨比例: {low_open_low_close_day5_up}/{low_open_low_close_count} ({low_open_low_close_day5_up/low_open_low_close_count*100:.2f}%)")
            logging.info(f"  10日收盘上涨比例: {low_open_low_close_day10_up}/{low_open_low_close_count} ({low_open_low_close_day10_up/low_open_low_close_count*100:.2f}%)")
        else:
            logging.info(f"  无次日低开低走的股票")
        
        # 计算平均涨跌幅
        avg_next_open = sum(r['next_open_change_pct'] for r in results) / len(results)
        avg_next_close = sum(r['next_close_change_pct'] for r in results) / len(results)
        avg_day3 = sum(r['day3_change_pct'] for r in results if r['day3_change_pct'] is not None) / len([r for r in results if r['day3_change_pct'] is not None]) if any(r['day3_change_pct'] is not None for r in results) else 0
        logging.info(f"  次日开盘平均涨跌幅: {avg_next_open:.2f}%")
        logging.info(f"  次日收盘平均涨跌幅: {avg_next_close:.2f}%")
        logging.info(f"  3日平均涨跌幅: {avg_day3:.2f}%")
        
        # 显示3日上涨的全部记录
        day3_up_results = [r for r in results if r['day3_change_pct'] is not None and r['day3_change_pct'] > 0]
        if day3_up_results:
            logging.info(f"\n3日上涨的全部记录 (共{len(day3_up_results)}个):")
            for i, result in enumerate(day3_up_results):
                day3_str = f"{result['day3_change_pct']:.2f}%" if result['day3_change_pct'] is not None else "N/A"
                day5_str = f"{result['day5_change_pct']:.2f}%" if result['day5_change_pct'] is not None else "N/A"
                day10_str = f"{result['day10_change_pct']:.2f}%" if result['day10_change_pct'] is not None else "N/A"
                logging.info(f"  {i+1}. {result['date']} - 开盘:{result['open']:.2f} 收盘:{result['close']:.2f} 最低:{result['low']:.2f} MA30:{result['ma30']:.2f}")
                logging.info(f"     昨日开盘变化:{result['next_open_change_pct']:.2f}% 昨日收盘变化:{result['next_close_change_pct']:.2f}%")
                logging.info(f"     3日变化:{day3_str} 5日变化:{day5_str} 10日变化:{day10_str}")
        else:
            logging.info(f"\n无3日上涨的记录")
        
        # 显示3日下跌的全部记录
        day3_down_results = [r for r in results if r['day3_change_pct'] is not None and r['day3_change_pct'] < 0]
        if day3_down_results:
            logging.info(f"\n3日下跌的全部记录 (共{len(day3_down_results)}个):")
            for i, result in enumerate(day3_down_results):
                day3_str = f"{result['day3_change_pct']:.2f}%" if result['day3_change_pct'] is not None else "N/A"
                day5_str = f"{result['day5_change_pct']:.2f}%" if result['day5_change_pct'] is not None else "N/A"
                day10_str = f"{result['day10_change_pct']:.2f}%" if result['day10_change_pct'] is not None else "N/A"
                logging.info(f"  {i+1}. {result['date']} - 开盘:{result['open']:.2f} 收盘:{result['close']:.2f} 最低:{result['low']:.2f} MA30:{result['ma30']:.2f}")
                logging.info(f"     昨日开盘变化:{result['next_open_change_pct']:.2f}% 昨日收盘变化:{result['next_close_change_pct']:.2f}%")
                logging.info(f"     3日变化:{day3_str} 5日变化:{day5_str} 10日变化:{day10_str}")
        else:
            logging.info(f"\n无3日下跌的记录")
        
        # 显示5日上涨的全部记录
        day5_up_results = [r for r in results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0]
        if day5_up_results:
            logging.info(f"\n5日上涨的全部记录 (共{len(day5_up_results)}个):")
            for i, result in enumerate(day5_up_results):
                day3_str = f"{result['day3_change_pct']:.2f}%" if result['day3_change_pct'] is not None else "N/A"
                day5_str = f"{result['day5_change_pct']:.2f}%" if result['day5_change_pct'] is not None else "N/A"
                day10_str = f"{result['day10_change_pct']:.2f}%" if result['day10_change_pct'] is not None else "N/A"
                logging.info(f"  {i+1}. {result['date']} - 开盘:{result['open']:.2f} 收盘:{result['close']:.2f} 最低:{result['low']:.2f} MA30:{result['ma30']:.2f}")
                logging.info(f"     昨日开盘变化:{result['next_open_change_pct']:.2f}% 昨日收盘变化:{result['next_close_change_pct']:.2f}%")
                logging.info(f"     3日变化:{day3_str} 5日变化:{day5_str} 10日变化:{day10_str}")
        else:
            logging.info(f"\n无5日上涨的记录")
        
        # 显示5日下跌的全部记录
        day5_down_results = [r for r in results if r['day5_change_pct'] is not None and r['day5_change_pct'] < 0]
        if day5_down_results:
            logging.info(f"\n5日下跌的全部记录 (共{len(day5_down_results)}个):")
            for i, result in enumerate(day5_down_results):
                day3_str = f"{result['day3_change_pct']:.2f}%" if result['day3_change_pct'] is not None else "N/A"
                day5_str = f"{result['day5_change_pct']:.2f}%" if result['day5_change_pct'] is not None else "N/A"
                day10_str = f"{result['day10_change_pct']:.2f}%" if result['day10_change_pct'] is not None else "N/A"
                logging.info(f"  {i+1}. {result['date']} - 开盘:{result['open']:.2f} 收盘:{result['close']:.2f} 最低:{result['low']:.2f} MA30:{result['ma30']:.2f}")
                logging.info(f"     昨日开盘变化:{result['next_open_change_pct']:.2f}% 昨日收盘变化:{result['next_close_change_pct']:.2f}%")
                logging.info(f"     3日变化:{day3_str} 5日变化:{day5_str} 10日变化:{day10_str}")
        else:
            logging.info(f"\n无5日下跌的记录")
        
        # 将单股票测试结果写入final_result文件
        result_df = pd.DataFrame(results)
        total_count = len(results)
        next_open_up_count = len([r for r in results if r['next_open_change_pct'] > 0])
        next_close_up_count = len([r for r in results if r['next_close_change_pct'] > 0])
        high_open_high_close_count = len([r for r in results if r['next_open_change_pct'] > 0 and r['next_close_change_pct'] > 0])
        day5_up_count = len([r for r in results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0])
        day10_up_count = len([r for r in results if r['day10_change_pct'] is not None and r['day10_change_pct'] > 0])
        high_open_high_close_results = [r for r in results if r['next_open_change_pct'] > 0 and r['next_close_change_pct'] > 0]
        high_open_high_close_day5_up = len([r for r in high_open_high_close_results if r['day5_change_pct'] is not None and r['day5_change_pct'] > 0])
        high_open_high_close_day10_up = len([r for r in high_open_high_close_results if r['day10_change_pct'] is not None and r['day10_change_pct'] > 0])
        
        write_backtest_result_to_file(total_count, next_open_up_count, next_close_up_count, 
                                     high_open_high_close_count, day5_up_count, day10_up_count,
                                     high_open_high_close_day5_up, high_open_high_close_day10_up,
                                     low_open_close_up_count, low_open_close_up_day3_up,
                                     low_open_close_up_day5_up, low_open_close_up_day10_up,
                                     result_df)
        logging.info(f"单股票测试结果已写入final_result文件")
        
    else:
        logging.info(f"股票 {stock_code} 没有找到符合条件的交易日")
        # 即使没有结果也写入final_result文件记录
        empty_df = pd.DataFrame()
        write_backtest_result_to_file(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, empty_df)
        logging.info(f"单股票测试结果（无符合条件记录）已写入final_result文件")

def simulate_investment_strategy(result_df, initial_capital=100000):
    """
    投资模拟功能：以2000年1月1日为基准，总计100000元
    策略：选定日期以当日收盘价买入，次日低开直接卖出，次日高开则第三日收盘价卖出
    
    Args:
        result_df: 包含股票回测结果的DataFrame
        initial_capital: 初始资金，默认100000元
    
    Returns:
        dict: 包含总收益率和各年收益率的统计结果
    """
    if result_df.empty:
        logging.warning("没有回测数据，无法进行投资模拟")
        return {}
    
    # 按日期排序
    result_df = result_df.sort_values('date').reset_index(drop=True)
    
    # 过滤数据：从2000年1月1日开始
    result_df['date'] = pd.to_datetime(result_df['date'])
    start_date = pd.to_datetime('2000-01-01')
    
    logging.info(f"过滤前数据量: {len(result_df)} 条")
    if not result_df.empty:
        logging.info(f"过滤前日期范围: {result_df['date'].min()} 到 {result_df['date'].max()}")
    
    filtered_df = result_df[result_df['date'] >= start_date].copy()
    
    logging.info(f"过滤后数据量: {len(filtered_df)} 条")
    if not filtered_df.empty:
        logging.info(f"过滤后日期范围: {filtered_df['date'].min()} 到 {filtered_df['date'].max()}")
    
    if filtered_df.empty:
        logging.warning("没有2000年1月1日及之后的数据，无法进行投资模拟")
        return {}
    
    # 投资记录
    investment_records = []
    current_capital = initial_capital
    yearly_returns = {}
    
    logging.info(f"=== 投资模拟开始 ===")
    logging.info(f"初始资金: {initial_capital:,.2f}元")
    logging.info(f"基准日期: 2000年1月1日")
    
    # 按日期分组处理，同一天的股票平均分配资金
    grouped = filtered_df.groupby('date')
    
    for date_str, group in grouped:
        try:
            date = pd.to_datetime(date_str)
            stocks_count = len(group)
            
            # 如果当天有多只股票，平均分配资金
            capital_per_stock = current_capital / stocks_count
            day_total_profit = 0
            day_trades = 0
            
            for idx, row in group.iterrows():
                # 获取股票数据
                stock_code = row['stock_code']
                close_price = row['close']
                next_open_price = row['next_open']
                next_close_price = row['next_close']
                day3_close_price = row.get('day3_close', None)
                
                # 检查必要数据
                if pd.isna(close_price) or pd.isna(next_open_price) or pd.isna(next_close_price):
                    continue
                
                # 过滤异常数据：次日开盘价和收盘价相同且开盘涨幅大于4%
                next_open_gain = ((next_open_price - close_price) / close_price) * 100
                if next_open_price == next_close_price and next_open_gain > 4.0:
                    logging.warning(f"剔除异常数据 - 股票: {stock_code}, 日期: {date.strftime('%Y-%m-%d')}, "
                                  f"次日开盘价和收盘价相同且开盘涨幅{next_open_gain:.2f}%超过4%")
                    continue
                
                # 计算买入股数（按分配的资金买入）
                buy_price = close_price
                shares = int(capital_per_stock / buy_price)
                if shares <= 0:
                    continue
                
                # 实际买入金额
                buy_amount = shares * buy_price
                
                # 统一使用次日开盘价卖出
                sell_price = next_open_price
                sell_date = date + pd.Timedelta(days=1)
                sell_reason = "次日开盘价卖出"
                
                # 计算收益
                sell_amount = shares * sell_price
                profit = sell_amount - buy_amount
                profit_rate = (profit / buy_amount) * 100
                
                # 记录交易详情
                investment_records.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'stock_code': stock_code,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'shares': shares,
                    'buy_amount': buy_amount,
                    'sell_amount': sell_amount,
                    'profit': profit,
                    'profit_rate': profit_rate,
                    'sell_date': sell_date.strftime('%Y-%m-%d'),
                    'sell_reason': sell_reason,
                    'capital_before': current_capital,
                    'capital_after': 0  # 稍后更新
                })
                
                # 打印每笔交易的详细记录
                logging.info(f"交易记录 - 日期: {date.strftime('%Y-%m-%d')}, "
                           f"股票: {stock_code}, "
                           f"买入价: {buy_price:.2f}, "
                           f"卖出价: {sell_price:.2f}, "
                           f"股数: {shares}, "
                           f"买入金额: {buy_amount:.2f}, "
                           f"卖出金额: {sell_amount:.2f}, "
                           f"收益: {profit:.2f} ({profit_rate:.2f}%), "
                           f"卖出日期: {sell_date.strftime('%Y-%m-%d')}, "
                           f"原因: {sell_reason}")
                
                # 累计当天收益
                day_total_profit += profit
                day_trades += 1
                

            
            # 更新总资金（当天所有交易完成后）
            current_capital += day_total_profit
            
            # 更新当天所有交易记录的资金状态
            for record in investment_records[-day_trades:]:
                record['capital_after'] = current_capital
            
            # 统计年度收益
            year = date.year
            if year not in yearly_returns:
                yearly_returns[year] = {'profit': 0, 'trades': 0}
            yearly_returns[year]['profit'] += day_total_profit
            yearly_returns[year]['trades'] += day_trades
            
        except Exception as e:
            logging.warning(f"处理日期 {date_str} 时出错: {e}")
            continue
    
    # 计算总收益率
    total_return = ((current_capital - initial_capital) / initial_capital) * 100
    
    # 计算各年收益率
    yearly_return_rates = {}
    running_capital = initial_capital
    
    for year in sorted(yearly_returns.keys()):
        year_profit = yearly_returns[year]['profit']
        year_return_rate = (year_profit / running_capital) * 100
        running_capital += year_profit
        yearly_return_rates[year] = {
            'profit': year_profit,
            'return_rate': year_return_rate,
            'trades': yearly_returns[year]['trades'],
            'capital_end': running_capital
        }
    
    # 输出统计结果
    logging.info(f"=== 投资模拟结果 ===")
    logging.info(f"总交易次数: {len(investment_records)}")
    logging.info(f"初始资金: {initial_capital:,.2f}元")
    logging.info(f"最终资金: {current_capital:,.2f}元")
    logging.info(f"总收益: {current_capital - initial_capital:,.2f}元")
    logging.info(f"总收益率: {total_return:.2f}%")
    
    logging.info(f"=== 各年收益统计 ===")
    for year in sorted(yearly_return_rates.keys()):
        year_data = yearly_return_rates[year]
        logging.info(f"{year}年: 收益 {year_data['profit']:,.2f}元, "
                    f"收益率 {year_data['return_rate']:.2f}%, "
                    f"交易次数 {year_data['trades']}, "
                    f"年末资金 {year_data['capital_end']:,.2f}元")
    
    # 计算一些额外统计指标
    if investment_records:
        profits = [r['profit'] for r in investment_records]
        profit_rates = [r['profit_rate'] for r in investment_records]
        
        win_trades = [p for p in profits if p > 0]
        lose_trades = [p for p in profits if p <= 0]
        
        win_rate = len(win_trades) / len(profits) * 100 if profits else 0
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_profit_rate = sum(profit_rates) / len(profit_rates) if profit_rates else 0
        
        logging.info(f"=== 交易统计 ===")
        logging.info(f"胜率: {win_rate:.2f}% ({len(win_trades)}/{len(profits)})")
        logging.info(f"平均每笔收益: {avg_profit:.2f}元")
        logging.info(f"平均每笔收益率: {avg_profit_rate:.2f}%")
        
        if win_trades:
            avg_win = sum(win_trades) / len(win_trades)
            logging.info(f"平均盈利: {avg_win:.2f}元")
        
        if lose_trades:
            avg_lose = sum(lose_trades) / len(lose_trades)
            logging.info(f"平均亏损: {avg_lose:.2f}元")
    
    return {
        'total_return': total_return,
        'yearly_returns': yearly_return_rates,
        'investment_records': investment_records,
        'final_capital': current_capital,
        'total_trades': len(investment_records)
    }


def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票选股策略回测工具')
    parser.add_argument('--single-stock', type=str, help='指定单个股票代码进行测试，如: 301379')
    parser.add_argument('--data-folder', type=str, 
                       default=r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info\all_stocks_data",
                       help='股票数据文件夹路径')
    parser.add_argument('--processes', type=int, default=20, help='多进程数量（仅全量测试模式）')
    parser.add_argument('--limit', type=int, help='限制批量测试的股票数量，如: 100（仅全量测试模式）')
    parser.add_argument('--investment-simulation', action='store_true', help='启用投资模拟功能')
    args = parser.parse_args()
    
    # 配置日志
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "strategy_backtest.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.info("开始运行选股策略回测")
    
    # 检查输入文件夹是否存在
    if not os.path.exists(args.data_folder):
        logging.error(f"输入文件夹不存在 - {args.data_folder}")
        return
    
    if args.single_stock:
        # 单股票测试模式
        logging.info(f"=== 单股票测试模式: {args.single_stock} ===")
        logging.info(f"数据文件夹: {args.data_folder}")
        test_single_stock(args.single_stock, args.data_folder, verbose=True)
    else:
        # 全量测试模式
        logging.info("=== 全量测试模式 ===")
        
        # 清空进程日志目录
        logs_dir = os.path.join(script_dir, "process_logs")
        if os.path.exists(logs_dir):
            try:
                shutil.rmtree(logs_dir)
                logging.info("已清空进程日志目录")
            except Exception as e:
                logging.error(f"清空进程日志目录失败: {e}")
        
        output_file = os.path.join(script_dir, "stock_backtest_data.csv")
        logging.info(f"输入文件夹: {args.data_folder}")
        logging.info(f"输出文件: {output_file}")
        logging.info(f"进程数量: {args.processes}")
        if args.limit:
            logging.info(f"限制测试数量: {args.limit}")
        run_stock_selection_strategy_dynamic(args.data_folder, output_file, num_processes=args.processes, limit=args.limit)
        
        # 如果启用投资模拟功能
        if args.investment_simulation:
            try:
                # 读取回测结果
                if os.path.exists(output_file):
                    result_df = pd.read_csv(output_file)
                    simulate_investment_strategy(result_df)
                else:
                    logging.error("回测结果文件不存在，无法进行投资模拟")
            except Exception as e:
                logging.error(f"投资模拟过程中出错: {e}")


if __name__ == "__main__":
    # 多进程保护，确保在Windows系统上正常运行
    mp.freeze_support()
    main()