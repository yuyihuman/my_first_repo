from xtquant import xtdata
import pandas as pd
import os
from datetime import datetime
import time
import logging
import multiprocessing
from multiprocessing import Pool, Lock
import math

# 全局变量，用于存储每个进程的日志记录器
process_loggers = {}

# 创建一个进程特定的日志记录函数
def safe_log(msg, level="info"):
    """进程特定的日志记录函数，每个进程使用自己的日志记录器"""
    # 获取当前进程ID
    process_id = multiprocessing.current_process().name
    
    # 如果当前进程还没有日志记录器，则创建一个
    if process_id not in process_loggers:
        process_loggers[process_id] = setup_process_logging(process_id)
    
    # 使用进程特定的日志记录器记录日志
    logger = process_loggers[process_id]
    if level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    elif level == "debug":
        logger.debug(msg)
    elif level == "critical":
        logger.critical(msg)

def save_stock_data_to_csv(stock_code, stock_name, base_folder="all_stocks_data"):
    """
    将单个股票的数据保存为CSV文件
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        base_folder: 数据保存的基础文件夹
    
    Returns:
        tuple: (success_count, total_attempts, detailed_results)
        detailed_results: dict with detailed status for each data type
    """
    safe_log(f"🔄 开始处理股票: {stock_code} ({stock_name})")
    
    # 创建股票专用数据文件夹
    stock_folder = os.path.join(base_folder, f"stock_{stock_code}_data")
    if not os.path.exists(stock_folder):
        os.makedirs(stock_folder)
    
    success_count = 0
    total_attempts = 4  # 1分钟数据 + 5分钟数据 + 30分钟数据 + 日线数据
    
    # 详细结果记录
    detailed_results = {
        'stock_code': stock_code,
        'stock_name': stock_name,
        'daily_data': {'status': 'pending', 'records': 0, 'error': None},
        '1min_data': {'status': 'pending', 'records': 0, 'error': None},
        '5min_data': {'status': 'pending', 'records': 0, 'error': None},
        '30min_data': {'status': 'pending', 'records': 0, 'error': None}
    }
    
    # 构造股票代码格式（需要添加交易所后缀）
    if stock_code.startswith('6'):
        full_code = f"{stock_code}.SH"  # 上海交易所（包括主板和科创板）
        exchange = "上海交易所"
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        full_code = f"{stock_code}.SZ"  # 深圳交易所
        exchange = "深圳交易所"
    else:
        error_msg = f"不支持的股票代码格式: {stock_code}"
        safe_log(f"❌ {error_msg}", "warning")
        for key in ['daily_data', '1min_data', '5min_data', '30min_data']:
            detailed_results[key]['status'] = 'failed'
            detailed_results[key]['error'] = error_msg
        return 0, 0, detailed_results
    
    safe_log(f"📊 股票信息: {stock_code} ({stock_name}) - {exchange} - 完整代码: {full_code}")
    
    # 1. 获取日线数据
    safe_log(f"📈 [1/4] 开始获取日线数据...")
    try:
        daily_data = xtdata.get_market_data([], [full_code], period='1d', start_time='19900101', dividend_type='none')
        
        if daily_data and isinstance(daily_data, dict):
            try:
                # 获取时间序列（日期）
                time_df = daily_data.get('time')
                if time_df is not None and not time_df.empty:
                    # 获取股票在DataFrame中的数据
                    if full_code in time_df.index:
                        dates = time_df.loc[full_code].values
                        
                        # 构建新的DataFrame，行为日期，列为各个指标
                        df_data = {'date': dates}
                        
                        # 提取各个字段的数据
                        for field_name, field_df in daily_data.items():
                            if field_name != 'time' and field_df is not None and not field_df.empty:
                                if full_code in field_df.index:
                                    df_data[field_name] = field_df.loc[full_code].values
                        
                        # 创建最终的DataFrame
                        daily_df = pd.DataFrame(df_data)
                        
                        # 按时间排序（确保数据按时间顺序排列）
                        daily_df = daily_df.sort_values('date').reset_index(drop=True)
                        
                        # 添加可读的日期时间列（紧跟在date列后面）
                        if 'date' in daily_df.columns:
                            datetime_col = pd.to_datetime(daily_df['date'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:%M:%S')
                            # 重新排列列顺序，将datetime放在date后面
                            cols = list(daily_df.columns)
                            date_idx = cols.index('date')
                            cols.insert(date_idx + 1, 'datetime')
                            daily_df['datetime'] = datetime_col
                            daily_df = daily_df[cols]
                        
                        # 计算移动平均值（如果有收盘价数据）
                        if 'close' in daily_df.columns:
                            data_count = len(daily_df)
                            # 只有在数据量足够时才计算相应的移动平均值
                            if data_count >= 5:
                                daily_df['close_5d_avg'] = daily_df['close'].rolling(window=5, min_periods=5).mean()
                            if data_count >= 10:
                                daily_df['close_10d_avg'] = daily_df['close'].rolling(window=10, min_periods=10).mean()
                            if data_count >= 20:
                                daily_df['close_20d_avg'] = daily_df['close'].rolling(window=20, min_periods=20).mean()
                            if data_count >= 30:
                                daily_df['close_30d_avg'] = daily_df['close'].rolling(window=30, min_periods=30).mean()
                            if data_count >= 60:
                                daily_df['close_60d_avg'] = daily_df['close'].rolling(window=60, min_periods=60).mean()
                        
                        # 计算成交量移动平均值（如果有成交量数据）
                        if 'volume' in daily_df.columns:
                            data_count = len(daily_df)
                            # 只有在数据量足够时才计算相应的成交量移动平均值
                            if data_count >= 5:
                                daily_df['volume_5d_avg'] = daily_df['volume'].rolling(window=5, min_periods=5).mean()
                            if data_count >= 10:
                                daily_df['volume_10d_avg'] = daily_df['volume'].rolling(window=10, min_periods=10).mean()
                            if data_count >= 20:
                                daily_df['volume_20d_avg'] = daily_df['volume'].rolling(window=20, min_periods=20).mean()
                            if data_count >= 30:
                                daily_df['volume_30d_avg'] = daily_df['volume'].rolling(window=30, min_periods=30).mean()
                            if data_count >= 60:
                                daily_df['volume_60d_avg'] = daily_df['volume'].rolling(window=60, min_periods=60).mean()
                        
                        # 计算开盘价移动平均值（如果有开盘价数据）
                        if 'open' in daily_df.columns:
                            data_count = len(daily_df)
                            # 只有在数据量足够时才计算相应的移动平均值
                            if data_count >= 5:
                                daily_df['open_5d_avg'] = daily_df['open'].rolling(window=5, min_periods=5).mean()
                            if data_count >= 10:
                                daily_df['open_10d_avg'] = daily_df['open'].rolling(window=10, min_periods=10).mean()
                            if data_count >= 20:
                                daily_df['open_20d_avg'] = daily_df['open'].rolling(window=20, min_periods=20).mean()
                            if data_count >= 30:
                                daily_df['open_30d_avg'] = daily_df['open'].rolling(window=30, min_periods=30).mean()
                            if data_count >= 60:
                                daily_df['open_60d_avg'] = daily_df['open'].rolling(window=60, min_periods=60).mean()
                        
                        daily_filename = os.path.join(stock_folder, f"{stock_code}_daily_history.csv")
                        daily_df.to_csv(daily_filename, encoding='utf-8-sig', index=False)
                        
                        record_count = len(daily_df)
                        detailed_results['daily_data']['status'] = 'success'
                        detailed_results['daily_data']['records'] = record_count
                        safe_log(f"✅ 日线数据获取成功: {record_count} 条记录")
                        success_count += 1
                    else:
                        error_msg = f"股票代码 {full_code} 不在返回数据中"
                        detailed_results['daily_data']['status'] = 'failed'
                        detailed_results['daily_data']['error'] = error_msg
                        safe_log(f"❌ 日线数据获取失败: {error_msg}", "error")
                else:
                    error_msg = "时间数据为空"
                    detailed_results['daily_data']['status'] = 'failed'
                    detailed_results['daily_data']['error'] = error_msg
                    safe_log(f"❌ 日线数据获取失败: {error_msg}", "error")
            except Exception as e:
                error_msg = f"日线数据处理失败: {str(e)}"
                detailed_results['daily_data']['status'] = 'failed'
                detailed_results['daily_data']['error'] = error_msg
                safe_log(f"❌ {error_msg}", "error")
        else:
            error_msg = "日线数据获取失败: 无数据返回"
            detailed_results['daily_data']['status'] = 'failed'
            detailed_results['daily_data']['error'] = error_msg
            safe_log(f"❌ {error_msg}", "error")
    except Exception as e:
        error_msg = f"日线数据获取异常: {str(e)}"
        detailed_results['daily_data']['status'] = 'failed'
        detailed_results['daily_data']['error'] = error_msg
        safe_log(f"❌ {error_msg}", "error")
    
    # 2. 获取1分钟数据
    safe_log(f"📊 [2/4] 开始获取1分钟数据...")
    try:
        minute_data = xtdata.get_market_data([], [full_code], period='1m', start_time='19900101', dividend_type='none')
        
        if minute_data and isinstance(minute_data, dict):
            try:
                # 获取时间序列
                time_df = minute_data.get('time')
                if time_df is not None and not time_df.empty:
                    # 获取股票在DataFrame中的数据
                    if full_code in time_df.index:
                        times = time_df.loc[full_code].values
                        
                        # 构建新的DataFrame，行为时间，列为各个指标
                        df_data = {'time': times}
                        
                        # 提取各个字段的数据
                        for field_name, field_df in minute_data.items():
                            if field_name != 'time' and field_df is not None and not field_df.empty:
                                if full_code in field_df.index:
                                    df_data[field_name] = field_df.loc[full_code].values
                        
                        # 创建最终的DataFrame
                        minute_df = pd.DataFrame(df_data)
                        
                        # 添加可读的日期时间列（紧跟在time列后面）
                        if 'time' in minute_df.columns:
                            datetime_col = pd.to_datetime(minute_df['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:%M:%S')
                            # 重新排列列顺序，将datetime放在time后面
                            cols = list(minute_df.columns)
                            time_idx = cols.index('time')
                            cols.insert(time_idx + 1, 'datetime')
                            minute_df['datetime'] = datetime_col
                            minute_df = minute_df[cols]
                        
                        minute_filename = os.path.join(stock_folder, f"{stock_code}_1minute_history.csv")
                        minute_df.to_csv(minute_filename, encoding='utf-8-sig', index=False)
                        
                        record_count = len(minute_df)
                        detailed_results['1min_data']['status'] = 'success'
                        detailed_results['1min_data']['records'] = record_count
                        safe_log(f"✅ 1分钟数据获取成功: {record_count} 条记录")
                        success_count += 1
                    else:
                        error_msg = f"股票代码 {full_code} 不在1分钟数据中"
                        detailed_results['1min_data']['status'] = 'failed'
                        detailed_results['1min_data']['error'] = error_msg
                        safe_log(f"⚠️ 1分钟数据跳过: {error_msg}")
                else:
                    error_msg = "1分钟数据时间序列为空"
                    detailed_results['1min_data']['status'] = 'failed'
                    detailed_results['1min_data']['error'] = error_msg
                    safe_log(f"⚠️ 1分钟数据跳过: {error_msg}")
            except Exception as e:
                error_msg = f"1分钟数据处理失败: {str(e)}"
                detailed_results['1min_data']['status'] = 'failed'
                detailed_results['1min_data']['error'] = error_msg
                safe_log(f"⚠️ 1分钟数据跳过: {error_msg}")
        else:
            error_msg = "1分钟数据不可用"
            detailed_results['1min_data']['status'] = 'failed'
            detailed_results['1min_data']['error'] = error_msg
            safe_log(f"⚠️ 1分钟数据跳过: {error_msg}")
    except Exception as e:
        error_msg = f"1分钟数据获取异常: {str(e)}"
        detailed_results['1min_data']['status'] = 'failed'
        detailed_results['1min_data']['error'] = error_msg
        safe_log(f"⚠️ 1分钟数据跳过: {error_msg}")
    
    # 3. 获取5分钟数据
    safe_log(f"📊 [3/4] 开始获取5分钟数据...")
    try:
        minute_5_data = xtdata.get_market_data([], [full_code], period='5m', start_time='19900101', dividend_type='none')
        
        if minute_5_data and isinstance(minute_5_data, dict):
            try:
                # 获取时间序列
                time_df = minute_5_data.get('time')
                if time_df is not None and not time_df.empty:
                    # 获取股票在DataFrame中的数据
                    if full_code in time_df.index:
                        times = time_df.loc[full_code].values
                        
                        # 构建新的DataFrame，行为时间，列为各个指标
                        df_data = {'time': times}
                        
                        # 提取各个字段的数据
                        for field_name, field_df in minute_5_data.items():
                            if field_name != 'time' and field_df is not None and not field_df.empty:
                                if full_code in field_df.index:
                                    df_data[field_name] = field_df.loc[full_code].values
                        
                        # 创建最终的DataFrame
                        minute_5_df = pd.DataFrame(df_data)
                        
                        # 添加可读的日期时间列（紧跟在time列后面）
                        if 'time' in minute_5_df.columns:
                            datetime_col = pd.to_datetime(minute_5_df['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:%M:%S')
                            # 重新排列列顺序，将datetime放在time后面
                            cols = list(minute_5_df.columns)
                            time_idx = cols.index('time')
                            cols.insert(time_idx + 1, 'datetime')
                            minute_5_df['datetime'] = datetime_col
                            minute_5_df = minute_5_df[cols]
                        
                        minute_5_filename = os.path.join(stock_folder, f"{stock_code}_5minute_history.csv")
                        minute_5_df.to_csv(minute_5_filename, encoding='utf-8-sig', index=False)
                        
                        record_count = len(minute_5_df)
                        detailed_results['5min_data']['status'] = 'success'
                        detailed_results['5min_data']['records'] = record_count
                        safe_log(f"✅ 5分钟数据获取成功: {record_count} 条记录")
                        success_count += 1
                    else:
                        error_msg = f"股票代码 {full_code} 不在5分钟数据中"
                        detailed_results['5min_data']['status'] = 'failed'
                        detailed_results['5min_data']['error'] = error_msg
                        safe_log(f"⚠️ 5分钟数据跳过: {error_msg}")
                else:
                    error_msg = "5分钟数据时间序列为空"
                    detailed_results['5min_data']['status'] = 'failed'
                    detailed_results['5min_data']['error'] = error_msg
                    safe_log(f"⚠️ 5分钟数据跳过: {error_msg}")
            except Exception as e:
                error_msg = f"5分钟数据处理失败: {str(e)}"
                detailed_results['5min_data']['status'] = 'failed'
                detailed_results['5min_data']['error'] = error_msg
                safe_log(f"⚠️ 5分钟数据跳过: {error_msg}")
        else:
            error_msg = "5分钟数据不可用"
            detailed_results['5min_data']['status'] = 'failed'
            detailed_results['5min_data']['error'] = error_msg
            safe_log(f"⚠️ 5分钟数据跳过: {error_msg}")
    except Exception as e:
        error_msg = f"5分钟数据获取异常: {str(e)}"
        detailed_results['5min_data']['status'] = 'failed'
        detailed_results['5min_data']['error'] = error_msg
        safe_log(f"⚠️ 5分钟数据跳过: {error_msg}")
    
    # 4. 获取30分钟数据
    safe_log(f"📊 [4/4] 开始获取30分钟数据...")
    try:
        minute_30_data = xtdata.get_market_data([], [full_code], period='30m', start_time='19900101', dividend_type='none')
        
        if minute_30_data and isinstance(minute_30_data, dict):
            try:
                # 获取时间序列
                time_df = minute_30_data.get('time')
                if time_df is not None and not time_df.empty:
                    # 获取股票在DataFrame中的数据
                    if full_code in time_df.index:
                        times = time_df.loc[full_code].values
                        
                        # 构建新的DataFrame，行为时间，列为各个指标
                        df_data = {'time': times}
                        
                        # 提取各个字段的数据
                        for field_name, field_df in minute_30_data.items():
                            if field_name != 'time' and field_df is not None and not field_df.empty:
                                if full_code in field_df.index:
                                    df_data[field_name] = field_df.loc[full_code].values
                        
                        # 创建最终的DataFrame
                        minute_30_df = pd.DataFrame(df_data)
                        
                        # 添加可读的日期时间列（紧跟在time列后面）
                        if 'time' in minute_30_df.columns:
                            datetime_col = pd.to_datetime(minute_30_df['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:%M:%S')
                            # 重新排列列顺序，将datetime放在time后面
                            cols = list(minute_30_df.columns)
                            time_idx = cols.index('time')
                            cols.insert(time_idx + 1, 'datetime')
                            minute_30_df['datetime'] = datetime_col
                            minute_30_df = minute_30_df[cols]
                        
                        minute_30_filename = os.path.join(stock_folder, f"{stock_code}_30minute_history.csv")
                        minute_30_df.to_csv(minute_30_filename, encoding='utf-8-sig', index=False)
                        
                        record_count = len(minute_30_df)
                        detailed_results['30min_data']['status'] = 'success'
                        detailed_results['30min_data']['records'] = record_count
                        safe_log(f"✅ 30分钟数据获取成功: {record_count} 条记录")
                        success_count += 1
                    else:
                        error_msg = f"股票代码 {full_code} 不在30分钟数据中"
                        detailed_results['30min_data']['status'] = 'failed'
                        detailed_results['30min_data']['error'] = error_msg
                        safe_log(f"⚠️ 30分钟数据跳过: {error_msg}")
                else:
                    error_msg = "30分钟数据时间序列为空"
                    detailed_results['30min_data']['status'] = 'failed'
                    detailed_results['30min_data']['error'] = error_msg
                    safe_log(f"⚠️ 30分钟数据跳过: {error_msg}")
            except Exception as e:
                error_msg = f"30分钟数据处理失败: {str(e)}"
                detailed_results['30min_data']['status'] = 'failed'
                detailed_results['30min_data']['error'] = error_msg
                safe_log(f"⚠️ 30分钟数据跳过: {error_msg}")
        else:
            error_msg = "30分钟数据不可用"
            detailed_results['30min_data']['status'] = 'failed'
            detailed_results['30min_data']['error'] = error_msg
            safe_log(f"⚠️ 30分钟数据跳过: {error_msg}")
    except Exception as e:
        error_msg = f"30分钟数据获取异常: {str(e)}"
        detailed_results['30min_data']['status'] = 'failed'
        detailed_results['30min_data']['error'] = error_msg
        safe_log(f"⚠️ 30分钟数据跳过: {error_msg}")

    # 生成单个股票的数据报告
    data_files_info = f"""获取的数据文件:
1. {stock_code}_1minute_history.csv - 1分钟历史数据 (xtquant)
2. {stock_code}_5minute_history.csv - 5分钟历史数据 (xtquant)
3. {stock_code}_30minute_history.csv - 30分钟历史数据 (xtquant)
4. {stock_code}_daily_history.csv - 日线历史数据 (xtquant)"""
    encoding_info = "- 文件编码：UTF-8-BOM，支持中文显示"
    
    summary_content = f"""股票代码: {stock_code}
股票名称: {stock_name}
完整代码: {full_code}
数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
成功获取数据类型: {success_count}/{total_attempts}

{data_files_info}

数据来源说明:
- 历史价格数据：xtquant (迅投量化)
{encoding_info}
- 数据周期：1分钟K线 + 5分钟K线 + 30分钟K线 + 日线K线
"""
    
    report_filename = os.path.join(stock_folder, "data_summary.txt")
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    # 记录最终结果
    if success_count == total_attempts:
        safe_log(f"🎉 股票 {stock_code} 数据保存完成: 全部成功 ({success_count}/{total_attempts})")
    elif success_count > 0:
        safe_log(f"⚠️ 股票 {stock_code} 数据保存完成: 部分成功 ({success_count}/{total_attempts})")
    else:
        safe_log(f"❌ 股票 {stock_code} 数据保存失败: 全部失败 ({success_count}/{total_attempts})", "error")
    
    return success_count, total_attempts, detailed_results

def clean_old_logs(logs_dir="logs", keep_days=7):
    """清理旧的日志文件
    
    Args:
        logs_dir: 日志文件夹路径
        keep_days: 保留最近几天的日志，默认7天
    """
    if not os.path.exists(logs_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 60 * 60)  # 转换为秒
    
    deleted_count = 0
    
    # 清理主日志文件夹中的旧日志
    for filename in os.listdir(logs_dir):
        if filename.endswith('.log'):
            file_path = os.path.join(logs_dir, filename)
            file_time = os.path.getmtime(file_path)
            
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"删除日志文件 {filename} 失败: {e}")
    
    # 清理进程日志文件夹中的旧日志
    process_logs_dir = os.path.join(logs_dir, "process_logs")
    if os.path.exists(process_logs_dir):
        for filename in os.listdir(process_logs_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(process_logs_dir, filename)
                file_time = os.path.getmtime(file_path)
                
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"删除进程日志文件 {filename} 失败: {e}")
    
    if deleted_count > 0:
        print(f"已清理 {deleted_count} 个旧日志文件")

def setup_process_logging(process_id):
    """
    为特定进程设置日志配置
    
    Args:
        process_id: 进程ID或名称
    
    Returns:
        logger: 配置好的日志记录器
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建进程日志文件夹（在脚本所在目录下的logs文件夹中）
    logs_dir = os.path.join(script_dir, "logs")
    process_logs_dir = os.path.join(logs_dir, "process_logs")
    if not os.path.exists(process_logs_dir):
        os.makedirs(process_logs_dir)
    
    # 生成带时间戳和进程ID的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(process_logs_dir, f"save_stocks_csv_{process_id}_{timestamp}.log")
    
    # 创建日志记录器
    logger = logging.getLogger(f"process_{process_id}")
    logger.setLevel(logging.INFO)
    
    # 清除已有的处理器，防止重复
    logger.handlers.clear()
    
    # 添加文件处理器
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 添加控制台处理器（可选，用于调试）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 只在控制台显示警告和错误
    console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 防止日志传播到根日志记录器
    logger.propagate = False
    
    return logger

def setup_logging():
    """
    设置主进程日志配置
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建logs文件夹（在脚本所在目录下）
    logs_dir = os.path.join(script_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 清理旧日志文件
    clean_old_logs(logs_dir)
    
    # 创建进程日志文件夹
    process_logs_dir = os.path.join(logs_dir, "process_logs")
    if not os.path.exists(process_logs_dir):
        os.makedirs(process_logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"save_stocks_csv_main_{timestamp}.log")
    
    # 配置主进程日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    # 获取主日志记录器
    main_logger = logging.getLogger('main')
    main_logger.info(f"🚀 主进程日志系统初始化完成")
    main_logger.info(f"📝 主进程日志文件: {log_filename}")
    main_logger.info(f"📁 进程日志目录: {process_logs_dir}")
    
    return log_filename

def process_stock_batch(stock_batch, base_folder):
    """
    处理一批股票数据
    
    Args:
        stock_batch: 包含股票代码和名称的DataFrame批次
        base_folder: 数据保存的基础文件夹
    
    Returns:
        tuple: (successful_stocks, failed_stocks, total_success_count, total_attempts, detailed_results_list, failed_stocks_list)
    """
    process_id = multiprocessing.current_process().name
    batch_start_index = stock_batch.index[0] if not stock_batch.empty else 0
    batch_end_index = stock_batch.index[-1] if not stock_batch.empty else 0
    
    # 为当前进程设置独立的日志记录器
    process_logger = setup_process_logging(process_id)
    
    # 将进程日志记录器存储到全局字典中，供safe_log使用
    global process_loggers
    process_loggers[process_id] = process_logger
    
    # 记录进程开始处理的信息
    safe_log(f"{'='*80}")
    safe_log(f"🚀 进程 {process_id} 开始处理批次，包含 {len(stock_batch)} 只股票，索引范围: {batch_start_index}-{batch_end_index}")
    safe_log(f"📝 进程 {process_id} 日志记录器已初始化")
    safe_log(f"{'='*80}")
    
    successful_stocks = 0
    failed_stocks = 0
    total_success_count = 0
    total_attempts = 0
    total_in_batch = len(stock_batch)
    processed_in_batch = 0
    
    # 详细结果列表和失败股票列表
    detailed_results_list = []
    failed_stocks_list = []
    
    for index, row in stock_batch.iterrows():
        stock_code = str(row['code']).zfill(6)  # 确保股票代码是6位数字
        stock_name = row['name']
        
        processed_in_batch += 1
        safe_log(f"{'='*60}")
        safe_log(f"📊 进程 {process_id} 处理进度: {processed_in_batch}/{total_in_batch} ({processed_in_batch/total_in_batch*100:.1f}%)")
        safe_log(f"🔍 进程 {process_id} 处理股票: {stock_code} - {stock_name}")
        
        try:
            success_count, attempt_count, detailed_results = save_stock_data_to_csv(stock_code, stock_name, base_folder)
            total_success_count += success_count
            total_attempts += attempt_count
            
            # 保存详细结果
            detailed_results_list.append(detailed_results)
            
            if success_count > 0:
                successful_stocks += 1
                safe_log(f"✅ 进程 {process_id} - 股票 {stock_code} 处理成功 ({success_count}/{attempt_count})")
            else:
                failed_stocks += 1
                failed_stocks_list.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'reason': '所有数据类型获取失败',
                    'details': detailed_results
                })
                safe_log(f"❌ 进程 {process_id} - 股票 {stock_code} 处理失败 (0/{attempt_count})", "error")
            
            # 添加延时，避免请求过于频繁
            time.sleep(1)
            
        except Exception as e:
            error_msg = f"处理股票 {stock_code} 时发生异常: {str(e)}"
            safe_log(f"💥 进程 {process_id} - {error_msg}", "error")
            failed_stocks += 1
            failed_stocks_list.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'reason': f'处理异常: {str(e)}',
                'details': None
            })
    
    # 记录进程完成处理的信息
    safe_log(f"{'='*80}")
    safe_log(f"🏁 进程 {process_id} 完成批次处理")
    safe_log(f"📈 成功处理: {successful_stocks} 只股票")
    safe_log(f"📉 失败处理: {failed_stocks} 只股票") 
    safe_log(f"📊 总计处理: {total_in_batch} 只股票")
    safe_log(f"🎯 批次成功率: {successful_stocks/total_in_batch*100:.1f}%")
    safe_log(f"📝 进程 {process_id} 日志记录完成")
    safe_log(f"{'='*80}")
    
    # 清理进程日志记录器
    if process_id in process_loggers:
        # 关闭所有处理器
        for handler in process_loggers[process_id].handlers:
            handler.close()
        # 从字典中移除
        del process_loggers[process_id]
    
    return (successful_stocks, failed_stocks, total_success_count, total_attempts, detailed_results_list, failed_stocks_list)

def main():
    """
    主函数：批量将所有股票数据保存为CSV文件，使用多进程加速
    """
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"📝 日志文件: {log_filename}")  # 主进程日志初始化，不需要使用safe_log
    logging.info(f"🚀 开始批量股票数据下载任务")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取股票列表CSV文件（在脚本所在目录下）
    csv_file = os.path.join(script_dir, "stock_data.csv")
    
    if not os.path.exists(csv_file):
        logging.error(f"❌ 错误：找不到文件 {csv_file}")  # 主进程日志，不需要使用safe_log
        return
    
    logging.info(f"📂 读取股票列表文件: {csv_file}")  # 主进程日志，不需要使用safe_log
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        logging.info(f"📊 共找到 {len(df)} 只股票")  # 主进程日志，不需要使用safe_log
        
        # 过滤掉8开头和9开头的股票（北交所等）
        original_count = len(df)
        # 确保股票代码是6位数字，然后检查第一位数字
        df['code_6digit'] = df['code'].astype(str).str.zfill(6)
        df = df[~df['code_6digit'].str[0].isin(['8', '9'])]
        df = df.drop('code_6digit', axis=1)  # 删除临时列
        filtered_count = len(df)
        logging.info(f"🔍 过滤8开头和9开头股票后剩余 {filtered_count} 只股票 (过滤掉 {original_count - filtered_count} 只)")  # 主进程日志，不需要使用safe_log
        
        # 创建总的数据文件夹（在脚本所在目录下）
        base_folder = os.path.join(script_dir, "all_stocks_data")
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            logging.info(f"📁 创建总文件夹: {base_folder}")  # 主进程日志，不需要使用safe_log
        
        # 统计信息
        total_stocks = len(df)
        
        # 设置进程数
        num_processes = 20
        logging.info(f"⚙️ 使用 {num_processes} 个进程并行处理股票数据")
        
        # 将股票列表分成多个批次
        batch_size = math.ceil(total_stocks / num_processes)
        batches = [df.iloc[i:i+batch_size] for i in range(0, total_stocks, batch_size)]
        logging.info(f"📦 将 {total_stocks} 只股票分成 {len(batches)} 个批次，每批次约 {batch_size} 只股票")
        
        # 确保进程日志文件夹存在
        logs_dir = os.path.join(script_dir, "logs")
        process_logs_dir = os.path.join(logs_dir, "process_logs")
        if not os.path.exists(process_logs_dir):
            os.makedirs(process_logs_dir)
            logging.info(f"📁 创建进程日志文件夹: {process_logs_dir}")
        
        # 记录开始时间
        start_time = datetime.now()
        logging.info(f"⏰ 任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 使用进程池并行处理，为每个进程设置日志记录器
        with Pool(processes=num_processes) as pool:
            # 为每个批次提供基础文件夹参数
            results = pool.starmap(process_stock_batch, [(batch, base_folder) for batch in batches])
        
        # 记录结束时间
        end_time = datetime.now()
        duration = end_time - start_time
        logging.info(f"⏰ 任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"⏱️ 总耗时: {duration}")
        
        # 汇总结果
        successful_stocks = sum(result[0] for result in results)
        failed_stocks = sum(result[1] for result in results)
        total_success_count = sum(result[2] for result in results)
        total_attempts = sum(result[3] for result in results)
        
        # 汇总详细结果和失败列表
        all_detailed_results = []
        all_failed_stocks = []
        for result in results:
            all_detailed_results.extend(result[4])  # detailed_results_list
            all_failed_stocks.extend(result[5])     # failed_stocks_list
        
        # 统计各种数据类型的成功率
        daily_success = sum(1 for r in all_detailed_results if r['daily_data']['status'] == 'success')
        min1_success = sum(1 for r in all_detailed_results if r['1min_data']['status'] == 'success')
        min5_success = sum(1 for r in all_detailed_results if r['5min_data']['status'] == 'success')
        min30_success = sum(1 for r in all_detailed_results if r['30min_data']['status'] == 'success')
        
        # 生成总体报告
        logging.info(f"{'='*80}")
        logging.info("🎉 批量数据保存完成！")
        logging.info(f"📊 总共处理股票: {total_stocks}")
        logging.info(f"✅ 成功保存数据的股票: {successful_stocks}")
        logging.info(f"❌ 失败的股票: {failed_stocks}")
        logging.info(f"🎯 总体成功率: {successful_stocks/total_stocks*100:.1f}%")
        logging.info(f"📈 数据保存成功率: {total_success_count/total_attempts*100:.1f}%")
        logging.info(f"")
        logging.info(f"📋 各数据类型成功率:")
        logging.info(f"  📈 日线数据: {daily_success}/{total_stocks} ({daily_success/total_stocks*100:.1f}%)")
        logging.info(f"  📊 1分钟数据: {min1_success}/{total_stocks} ({min1_success/total_stocks*100:.1f}%)")
        logging.info(f"  📊 5分钟数据: {min5_success}/{total_stocks} ({min5_success/total_stocks*100:.1f}%)")
        logging.info(f"  📊 30分钟数据: {min30_success}/{total_stocks} ({min30_success/total_stocks*100:.1f}%)")
        logging.info(f"⏱️ 总耗时: {duration}")
        
        # 如果有失败的股票，记录失败详情
        if all_failed_stocks:
            logging.warning(f"⚠️ 以下 {len(all_failed_stocks)} 只股票处理失败:")
            for failed_stock in all_failed_stocks[:10]:  # 只显示前10个失败的股票
                logging.warning(f"  ❌ {failed_stock['stock_code']} ({failed_stock['stock_name']}) - {failed_stock['reason']}")
            if len(all_failed_stocks) > 10:
                logging.warning(f"  ... 还有 {len(all_failed_stocks) - 10} 只股票失败 (详见详细报告)")
        
        # 保存详细的失败报告
        if all_failed_stocks:
            failed_report_filename = os.path.join(base_folder, "failed_stocks_report.txt")
            with open(failed_report_filename, 'w', encoding='utf-8') as f:
                f.write(f"失败股票详细报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总失败数量: {len(all_failed_stocks)}\n\n")
                
                for i, failed_stock in enumerate(all_failed_stocks, 1):
                    f.write(f"{i}. 股票代码: {failed_stock['stock_code']}\n")
                    f.write(f"   股票名称: {failed_stock['stock_name']}\n")
                    f.write(f"   失败原因: {failed_stock['reason']}\n")
                    
                    if failed_stock['details']:
                        f.write(f"   详细信息:\n")
                        for data_type, info in failed_stock['details'].items():
                            if data_type not in ['stock_code', 'stock_name'] and info['status'] == 'failed':
                                f.write(f"     - {data_type}: {info['error']}\n")
                    f.write(f"\n")
            
            logging.info(f"📄 失败股票详细报告已保存到: {failed_report_filename}")
        
        # 保存总体报告
        storage_info = f"数据存储位置: {base_folder}/\n每个股票的数据存储在独立的子文件夹中"
        file_info = "- 所有文件使用UTF-8-BOM编码"
        process_info = "- 需要先下载数据到本地，然后读取保存为CSV文件"
        
        overall_report = f"""批量股票多周期数据保存报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
总耗时: {duration}

统计信息:
- 总共处理股票: {total_stocks}
- 成功保存数据的股票: {successful_stocks}
- 失败数量: {failed_stocks}
- 股票处理成功率: {successful_stocks/total_stocks*100:.1f}%
- 数据保存成功率: {total_success_count/total_attempts*100:.1f}%

各数据类型成功率:
- 日线数据: {daily_success}/{total_stocks} ({daily_success/total_stocks*100:.1f}%)
- 1分钟数据: {min1_success}/{total_stocks} ({min1_success/total_stocks*100:.1f}%)
- 5分钟数据: {min5_success}/{total_stocks} ({min5_success/total_stocks*100:.1f}%)
- 30分钟数据: {min30_success}/{total_stocks} ({min30_success/total_stocks*100:.1f}%)

{storage_info}

数据来源:
- xtquant库 (迅投量化)

数据类型:
- 1分钟K线数据
- 5分钟K线数据
- 30分钟K线数据
- 日线K线数据

注意事项:
{file_info}
- 部分股票可能因为数据源限制无法获取完整数据
- 建议定期更新数据
{process_info}

失败股票数量: {len(all_failed_stocks)}
{f"详细失败信息请查看: failed_stocks_report.txt" if all_failed_stocks else ""}
"""
        
        report_filename = os.path.join(base_folder, "batch_csv_save_report.txt")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(overall_report)
        
        logging.info(f"")
        logging.info(f"🎉 批量保存完成!")
        logging.info(f"📊 总共处理 {total_stocks} 只股票，成功 {successful_stocks} 只，失败 {failed_stocks} 只")
        logging.info(f"📄 详细报告已保存到: {report_filename}")
        logging.info(f"{'='*80}")
        
    except Exception as e:
        logging.error(f"💥 读取CSV文件时发生错误: {e}")
        return

if __name__ == "__main__":
    main()