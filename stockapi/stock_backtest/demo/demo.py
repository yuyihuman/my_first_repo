# coding:utf-8
"""选股策略：基于均线趋势的股票筛选

数据来源：
- 股票历史数据来源于：c:/Users/17701/github/my_first_repo/stockapi/stock_base_info/all_stocks_data/
- 数据结构检查日志：c:/Users/17701/github/my_first_repo/stockapi/stock_base_info/logs/data_structure_check.log
- 如需查找新数据或验证数据完整性，请查看上述日志文件

策略条件：
1. 5日线、10日线、20日线、30日线、60日线在周一到周三都必须逐渐上升
2. 当天5日线、10日线、20日线、30日线、60日线中最大值和最小值的差距不能超过6%
3. 当天5日线上穿10日线
"""

import pandas as pd
import os
from datetime import datetime
import multiprocessing as mp
from functools import partial
import logging
import shutil
import gc

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
        basic_cols = ['datetime', 'open', 'close', 'volume']
        ma_cols = ['close_5d_avg', 'close_10d_avg', 'close_20d_avg', 'close_30d_avg', 'close_60d_avg']
        
        # 检查文件中存在哪些列
        try:
            # 读取第一行来检查列名
            sample_df = pd.read_csv(csv_file_path, nrows=1)
            available_cols = sample_df.columns.tolist()
            
            # 确定要读取的列
            cols_to_read = basic_cols.copy()
            available_ma_cols = [col for col in ma_cols if col in available_cols]
            cols_to_read.extend(available_ma_cols)
            
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
        
        # 处理均线数据：优先使用预计算的，缺失的则计算
        if 'close_5d_avg' in available_ma_cols:
            df['ma5'] = df['close_5d_avg']
        else:
            df['ma5'] = df['close'].rolling(window=5).mean()
            
        if 'close_10d_avg' in available_ma_cols:
            df['ma10'] = df['close_10d_avg']
        else:
            df['ma10'] = df['close'].rolling(window=10).mean()
            
        if 'close_20d_avg' in available_ma_cols:
            df['ma20'] = df['close_20d_avg']
        else:
            df['ma20'] = df['close'].rolling(window=20).mean()
            
        if 'close_30d_avg' in available_ma_cols:
            df['ma30'] = df['close_30d_avg']
        else:
            df['ma30'] = df['close'].rolling(window=30).mean()
            
        if 'close_60d_avg' in available_ma_cols:
            df['ma60'] = df['close_60d_avg']
        else:
            df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 删除不再需要的原始均线列以节省内存
        for col in available_ma_cols:
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
    # 需要至少3天的数据来检查周一到周三的条件
    if current_idx < 3:
        return False
    
    # 获取当前日期和前3个交易日的数据
    current_day = df.iloc[current_idx]
    
    # 检查数据完整性
    if pd.isna(current_day['open']) or pd.isna(current_day['close']):
        return False
    
    # 获取前3个交易日的数据用于检查均线趋势
    week_days = []
    for i in range(3):
        day_data = df.iloc[current_idx - 2 + i]  # 前天、昨天、今天
        week_days.append(day_data)
    
    # 检查周一到周三的移动平均线数据完整性
    for day in week_days:
        if pd.isna(day['ma5']) or pd.isna(day['ma10']) or pd.isna(day['ma20']) or pd.isna(day['ma30']) or pd.isna(day['ma60']) or pd.isna(day['close']):
            return False
    
    # 条件1: 5日线、10日线、20日线、30日线、60日线在前3个交易日都必须逐渐上升
    ma5_rising = all(week_days[i]['ma5'] > week_days[i-1]['ma5'] for i in range(1, 3))
    ma10_rising = all(week_days[i]['ma10'] > week_days[i-1]['ma10'] for i in range(1, 3))
    ma20_rising = all(week_days[i]['ma20'] > week_days[i-1]['ma20'] for i in range(1, 3))
    ma30_rising = all(week_days[i]['ma30'] > week_days[i-1]['ma30'] for i in range(1, 3))
    ma60_rising = all(week_days[i]['ma60'] > week_days[i-1]['ma60'] for i in range(1, 3))
    
    ma_trend_ok = ma5_rising and ma10_rising and ma20_rising and ma30_rising and ma60_rising
    
    # 条件2: 当天5日线、10日线、20日线、30日线、60日线中最大值和最小值的差距不能超过6%
    current_ma5 = current_day['ma5']
    current_ma10 = current_day['ma10']
    current_ma20 = current_day['ma20']
    current_ma30 = current_day['ma30']
    current_ma60 = current_day['ma60']
    
    if pd.isna(current_ma5) or pd.isna(current_ma10) or pd.isna(current_ma20) or pd.isna(current_ma30) or pd.isna(current_ma60):
        return False
    
    ma_values = [current_ma5, current_ma10, current_ma20, current_ma30, current_ma60]
    ma_max = max(ma_values)
    ma_min = min(ma_values)
    
    # 避免除零错误
    if ma_min <= 0:
        return False
    
    ma_spread_pct = (ma_max - ma_min) / ma_min * 100
    ma_spread_ok = ma_spread_pct <= 6.0
    
    # 条件3: 当天5日线上穿10日线（前一天5日线小于10日线，当天5日线大于10日线）
    if current_idx < 1:
        return False
    
    prev_day = df.iloc[current_idx - 1]
    prev_ma5 = prev_day['ma5']
    prev_ma10 = prev_day['ma10']
    
    if pd.isna(prev_ma5) or pd.isna(prev_ma10):
        return False
    
    ma5_cross_ma10 = (prev_ma5 < prev_ma10) and (current_ma5 > current_ma10)
    
    # 所有条件都满足
    return ma_trend_ok and ma_spread_ok and ma5_cross_ma10

def process_single_stock(stock_folder_name, data_folder, process_index=1, log_to_file=None):
    """
    处理单个股票的数据，检查是否符合策略条件
    
    Args:
        stock_folder_name: 股票文件夹名称
        data_folder: 数据根目录路径
        process_index: 进程序号（1-20）
    
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
    if df is None or len(df) < 65:  # 至少需要65天数据（60天均线+5天条件检查）
        return []
    
    log_to_file(f"处理股票 {stock_code}，共 {len(df)} 条记录")
    
    # 存储符合条件的日期
    selected_dates = []
    
    try:
        # 预先计算所有需要的数据，避免在循环中重复计算
        df_values = df[['datetime', 'open', 'close', 'ma5', 'ma10', 'ma20', 'ma30', 'ma60']].values
        
        # 遍历每一个日期（从第60天开始到倒数第11天，确保有足够历史数据和未来10个交易日数据）
        for i in range(60, len(df) - 10):
            current_row = df_values[i]
            
            if check_strategy_conditions(df, i):
                next_row = df_values[i + 1]
                
                # 计算涨跌比例
                current_close = current_row[2]  # close
                next_open = next_row[1]  # next open
                next_close = next_row[2]  # next close
                
                next_open_change = (next_open - current_close) / current_close * 100
                next_close_change = (next_close - current_close) / current_close * 100
                
                # 计算5日后和10日后的收盘价变化
                day5_close = df_values[i + 5][2] if i + 5 < len(df) else None
                day10_close = df_values[i + 10][2] if i + 10 < len(df) else None
                
                day5_change = (day5_close - current_close) / current_close * 100 if day5_close is not None else None
                day10_change = (day10_close - current_close) / current_close * 100 if day10_close is not None else None
                
                selected_dates.append({
                    'stock_code': stock_code,
                    'date': current_row[0].strftime('%Y-%m-%d'),  # datetime
                    'open': current_row[1],  # open
                    'close': current_close,
                    'ma5': round(current_row[3], 2),  # ma5
                    'ma10': round(current_row[4], 2),  # ma10
                    'ma20': round(current_row[5], 2),  # ma20
                    'ma30': round(current_row[6], 2),  # ma30
                    'ma60': round(current_row[7], 2),  # ma60
                    'next_open': next_open,
                    'next_close': next_close,
                    'next_open_change_pct': round(next_open_change, 2),
                    'next_close_change_pct': round(next_close_change, 2),
                    'day5_close': round(day5_close, 2) if day5_close is not None else None,
                    'day5_change_pct': round(day5_change, 2) if day5_change is not None else None,
                    'day10_close': round(day10_close, 2) if day10_close is not None else None,
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
    
    # 将过滤后的股票文件夹分成多个批次
    batch_size = len(filtered_stock_folders) // num_processes + 1
    stock_batches = [filtered_stock_folders[i:i + batch_size] for i in range(0, len(filtered_stock_folders), batch_size)]
    
    logging.info(f"将股票分成 {len(stock_batches)} 个批次进行处理")
    
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
        # 删除了当日涨幅统计，因为不再是策略条件
        
        # 计算关键比例统计
        total_count = len(result_df)
        next_open_up_count = len(result_df[result_df['next_open_change_pct'] > 0])
        next_close_up_count = len(result_df[result_df['next_close_change_pct'] > 0])
        day5_up_count = len(result_df[result_df['day5_change_pct'] > 0])
        day10_up_count = len(result_df[result_df['day10_change_pct'] > 0])
        
        logging.info("关键比例统计:")
        logging.info(f"次日高开比例: {next_open_up_count}/{total_count} ({next_open_up_count/total_count*100:.2f}%)")
        logging.info(f"次日收盘上涨比例: {next_close_up_count}/{total_count} ({next_close_up_count/total_count*100:.2f}%)")
        logging.info(f"5日收盘上涨比例: {day5_up_count}/{total_count} ({day5_up_count/total_count*100:.2f}%)")
        logging.info(f"10日收盘上涨比例: {day10_up_count}/{total_count} ({day10_up_count/total_count*100:.2f}%)")
        
        # 计算平均涨跌幅
        logging.info("平均涨跌幅统计:")
        logging.info(f"次日开盘平均涨跌幅: {result_df['next_open_change_pct'].mean():.2f}%")
        logging.info(f"次日收盘平均涨跌幅: {result_df['next_close_change_pct'].mean():.2f}%")
        logging.info(f"5日收盘平均涨跌幅: {result_df['day5_change_pct'].mean():.2f}%")
        logging.info(f"10日收盘平均涨跌幅: {result_df['day10_change_pct'].mean():.2f}%")
        
        # 筛选次日开盘价高于当日收盘价的最后10条数据
        next_open_up_df = result_df[result_df['next_open_change_pct'] > 0].tail(10)
        logging.info("次日开盘价高于当日收盘价的最后10条数据:")
        if not next_open_up_df.empty:
            for _, row in next_open_up_df.iterrows():
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
        
        # 筛选次日开盘价低于当日收盘价的最后10条数据
        next_open_down_df = result_df[result_df['next_open_change_pct'] < 0].tail(10)
        logging.info("次日开盘价低于当日收盘价的最后10条数据:")
        if not next_open_down_df.empty:
            for _, row in next_open_down_df.iterrows():
                day5_str = f"{row['day5_change_pct']:.2f}%" if pd.notna(row['day5_change_pct']) else "N/A"
                day10_str = f"{row['day10_change_pct']:.2f}%" if pd.notna(row['day10_change_pct']) else "N/A"
                logging.info(f"{row['stock_code']} {row['date']} 次日开盘:{row['next_open_change_pct']:.2f}% 次日收盘:{row['next_close_change_pct']:.2f}% 5日:{day5_str} 10日:{day10_str}")
        else:
            logging.info("无符合条件的数据")
    else:
        logging.warning("没有找到符合条件的交易日")
        # 创建空的CSV文件
        empty_df = pd.DataFrame(columns=['stock_code', 'date', 'open', 'close', 'ma5', 'ma10', 'ma20', 'ma30', 'ma60', 'next_open', 'next_close', 'next_open_change_pct', 'next_close_change_pct', 'day5_close', 'day5_change_pct', 'day10_close', 'day10_change_pct'])
        empty_df.to_csv(output_file_path, index=False, encoding='utf-8')
        logging.info(f"空结果文件已保存到: {output_file_path}")

def main():
    """
    主函数
    """
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
    
    # 清空进程日志目录
    logs_dir = os.path.join(script_dir, "process_logs")
    if os.path.exists(logs_dir):
        try:
            shutil.rmtree(logs_dir)
            logging.info("已清空进程日志目录")
        except Exception as e:
            logging.error(f"清空进程日志目录失败: {e}")
    
    # 输入文件夹路径（包含所有股票数据）
    input_folder = r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info\all_stocks_data"
    
    # 输出文件路径（保存在当前脚本所在目录）
    output_file = os.path.join(script_dir, "demo.csv")
    
    logging.info(f"输入文件夹: {input_folder}")
    logging.info(f"输出文件: {output_file}")
    
    # 检查输入文件夹是否存在
    if not os.path.exists(input_folder):
        logging.error(f"输入文件夹不存在 - {input_folder}")
        return
    
    # 使用20个进程批量运行策略
    run_stock_selection_strategy_batch(input_folder, output_file, num_processes=20)


if __name__ == "__main__":
    # 多进程保护，确保在Windows系统上正常运行
    mp.freeze_support()
    main()