from xtquant import xtdata
import pandas as pd
import os
from datetime import datetime
import time
import logging
import multiprocessing
from multiprocessing import Pool, Lock
import math
import shutil

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

def get_stock_data(stock_code, stock_name, base_folder="all_stocks_data"):
    """
    下载单个股票的1分钟、5分钟、30分钟和日线数据到本地缓存
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        base_folder: 数据缓存的基础文件夹（仅用于日志记录）
    """
    safe_log(f"开始下载股票 {stock_code} ({stock_name}) 的1分钟、5分钟、30分钟和日线数据到本地缓存...")
    
    success_count = 0
    total_attempts = 4  # 1分钟数据 + 5分钟数据 + 30分钟数据 + 日线数据
    
    # 构造股票代码格式（需要添加交易所后缀）
    if stock_code.startswith('6'):
        full_code = f"{stock_code}.SH"  # 上海交易所（包括主板和科创板）
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        full_code = f"{stock_code}.SZ"  # 深圳交易所
    else:
        safe_log(f"  跳过不支持的股票代码: {stock_code}", "warning")
        return False
    
    try:
        # 下载日线数据到本地（带重试机制）
        safe_log(f"  下载日线数据到本地（从1990年开始）...")
        daily_success = False
        try:
            download_result = xtdata.download_history_data(full_code, period='1d', start_time='19900101')
            safe_log(f"  日线数据下载结果: {download_result}")
            safe_log(f"    日线数据已下载到本地缓存")
            daily_success = True
            success_count += 1
        except Exception as e:
            safe_log(f"    日线数据首次下载失败: {e}，准备重试...", "warning")
            try:
                # 重试一次
                time.sleep(2)  # 等待2秒后重试
                download_result = xtdata.download_history_data(full_code, period='1d', start_time='19900101')
                safe_log(f"  日线数据重试下载结果: {download_result}")
                safe_log(f"    日线数据重试成功，已下载到本地缓存")
                daily_success = True
                success_count += 1
            except Exception as retry_e:
                safe_log(f"    日线数据重试下载仍然失败: {retry_e}", "error")
        
        # 尝试下载1分钟数据（从1990年开始，如果支持的话）
        safe_log(f"  下载1分钟数据到本地（从1990年开始）...")
        try:
            download_result_1m = xtdata.download_history_data(full_code, period='1m', start_time='19900101')
            safe_log(f"  1分钟数据下载结果: {download_result_1m}")
            safe_log(f"    1分钟数据已下载到本地缓存")
            success_count += 1
        except Exception as e:
            safe_log(f"    1分钟数据首次下载失败: {e}，准备重试...", "warning")
            try:
                # 重试一次
                time.sleep(2)  # 等待2秒后重试
                download_result_1m = xtdata.download_history_data(full_code, period='1m', start_time='19900101')
                safe_log(f"  1分钟数据重试下载结果: {download_result_1m}")
                safe_log(f"    1分钟数据重试成功，已下载到本地缓存")
                success_count += 1
            except Exception as retry_e:
                safe_log(f"    1分钟数据重试下载仍然失败，跳过: {retry_e}")
        
        # 尝试下载5分钟数据（从1990年开始，如果支持的话）
        safe_log(f"  下载5分钟数据到本地（从1990年开始）...")
        try:
            download_result_5m = xtdata.download_history_data(full_code, period='5m', start_time='19900101')
            safe_log(f"  5分钟数据下载结果: {download_result_5m}")
            safe_log(f"    5分钟数据已下载到本地缓存")
            success_count += 1
        except Exception as e:
            safe_log(f"    5分钟数据首次下载失败: {e}，准备重试...", "warning")
            try:
                # 重试一次
                time.sleep(2)  # 等待2秒后重试
                download_result_5m = xtdata.download_history_data(full_code, period='5m', start_time='19900101')
                safe_log(f"  5分钟数据重试下载结果: {download_result_5m}")
                safe_log(f"    5分钟数据重试成功，已下载到本地缓存")
                success_count += 1
            except Exception as retry_e:
                safe_log(f"    5分钟数据重试下载仍然失败，跳过: {retry_e}")
        
        # 尝试下载30分钟数据（从1990年开始，如果支持的话）
        safe_log(f"  下载30分钟数据到本地（从1990年开始）...")
        try:
            download_result_30m = xtdata.download_history_data(full_code, period='30m', start_time='19900101')
            safe_log(f"  30分钟数据下载结果: {download_result_30m}")
            safe_log(f"    30分钟数据已下载到本地缓存")
            success_count += 1
        except Exception as e:
            safe_log(f"    30分钟数据首次下载失败: {e}，准备重试...", "warning")
            try:
                # 重试一次
                time.sleep(2)  # 等待2秒后重试
                download_result_30m = xtdata.download_history_data(full_code, period='30m', start_time='19900101')
                safe_log(f"  30分钟数据重试下载结果: {download_result_30m}")
                safe_log(f"    30分钟数据重试成功，已下载到本地缓存")
                success_count += 1
            except Exception as retry_e:
                safe_log(f"    30分钟数据重试下载仍然失败，跳过: {retry_e}")
        

        
    except Exception as e:
        safe_log(f"    数据获取过程中发生未预期错误: {e}", "error")
    

    
    safe_log(f"  股票 {stock_code} 数据下载完成，成功率: {success_count}/{total_attempts}")
    return success_count > 0

def is_valid_stock_code(stock_code):
    """检查股票代码是否符合要求（只保留0、3、60开头的股票）
    
    Args:
        stock_code: 股票代码字符串
    
    Returns:
        bool: 如果股票代码符合要求返回True，否则返回False
    """
    stock_code_str = str(stock_code).zfill(6)
    
    # 只保留0、3、60开头的股票
    if stock_code_str.startswith('0') or stock_code_str.startswith('3') or stock_code_str.startswith('60'):
        return True
    
    return False



def clean_all_stocks_data_folder(folder_path):
    """清空all_stocks_data文件夹中的所有内容
    
    Args:
        folder_path: 要清空的文件夹路径
    """
    if not os.path.exists(folder_path):
        print(f"文件夹 {folder_path} 不存在，无需清空")
        return
    
    deleted_count = 0
    deleted_folders = 0
    
    try:
        # 遍历文件夹中的所有内容
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            
            try:
                if os.path.isfile(item_path):
                    # 删除文件
                    os.remove(item_path)
                    deleted_count += 1
                elif os.path.isdir(item_path):
                    # 删除文件夹及其所有内容
                    shutil.rmtree(item_path)
                    deleted_folders += 1
            except Exception as e:
                print(f"删除 {item_path} 失败: {e}")
        
        print(f"已清空 all_stocks_data 文件夹，删除了 {deleted_count} 个文件和 {deleted_folders} 个文件夹")
        
    except Exception as e:
        print(f"清空文件夹时发生错误: {e}")

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
    log_filename = os.path.join(process_logs_dir, f"stock_data_{process_id}_{timestamp}.log")
    
    # 创建日志记录器
    logger = logging.getLogger(f"process_{process_id}")
    logger.setLevel(logging.INFO)
    
    # 防止重复添加处理器
    if not logger.handlers:
        # 添加文件处理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
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
    log_filename = os.path.join(logs_dir, f"stock_data_main_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

def process_stock_batch(stock_batch):
    """
    处理一批股票数据
    
    Args:
        stock_batch: 包含股票代码和名称的DataFrame批次
    
    Returns:
        成功和失败的股票数量元组 (successful_stocks, failed_stocks)
    """
    process_id = multiprocessing.current_process().name
    batch_start_index = stock_batch.index[0] if not stock_batch.empty else 0
    batch_end_index = stock_batch.index[-1] if not stock_batch.empty else 0
    
    # 记录进程开始处理的信息
    safe_log(f"{'='*80}")
    safe_log(f"进程 {process_id} 开始处理批次，包含 {len(stock_batch)} 只股票，索引范围: {batch_start_index}-{batch_end_index}")
    safe_log(f"{'='*80}")
    
    successful_stocks = 0
    failed_stocks = 0
    total_in_batch = len(stock_batch)
    processed_in_batch = 0
    
    for index, row in stock_batch.iterrows():
        stock_code = str(row['code']).zfill(6)  # 确保股票代码是6位数字
        stock_name = row['name']
        
        processed_in_batch += 1
        safe_log(f"{'='*60}")
        safe_log(f"进程 {process_id} 处理进度: {processed_in_batch}/{total_in_batch} ({processed_in_batch/total_in_batch*100:.1f}%)")
        safe_log(f"进程 {process_id} 处理股票: {stock_code} - {stock_name}")
        
        try:
            result = get_stock_data(stock_code, stock_name)
            if result:
                successful_stocks += 1
            else:
                failed_stocks += 1
            
            # 添加延时，避免请求过于频繁
            time.sleep(1)
            
        except Exception as e:
            safe_log(f"处理股票 {stock_code} 时发生错误: {e}", "error")
            failed_stocks += 1
    
    # 记录进程完成处理的信息
    safe_log(f"{'='*80}")
    safe_log(f"进程 {process_id} 完成批次处理，成功: {successful_stocks}，失败: {failed_stocks}，总计: {total_in_batch}")
    safe_log(f"{'='*80}")
    
    return (successful_stocks, failed_stocks)

def main():
    """
    主函数：批量下载所有股票的历史数据到本地缓存，使用多进程加速
    """
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"日志文件: {log_filename}")  # 主进程日志初始化，不需要使用safe_log
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取股票列表CSV文件（在脚本所在目录下）
    csv_file = os.path.join(script_dir, "stock_data.csv")
    
    if not os.path.exists(csv_file):
        logging.error(f"错误：找不到文件 {csv_file}")  # 主进程日志，不需要使用safe_log
        return
    
    logging.info(f"读取股票列表文件: {csv_file}")  # 主进程日志，不需要使用safe_log
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        logging.info(f"共找到 {len(df)} 只股票")  # 主进程日志，不需要使用safe_log
        
        # 过滤掉8开头和9开头的股票（北交所等）
        # 确保股票代码是6位数字，然后检查第一位数字
        df['code_6digit'] = df['code'].astype(str).str.zfill(6)
        df = df[~df['code_6digit'].str[0].isin(['8', '9'])]
        df = df.drop('code_6digit', axis=1)  # 删除临时列
        logging.info(f"过滤8开头和9开头股票后剩余 {len(df)} 只股票")  # 主进程日志，不需要使用safe_log
        

        
        # 创建总的数据文件夹（在脚本所在目录下）
        base_folder = os.path.join(script_dir, "all_stocks_data")
        
        # 清空all_stocks_data文件夹
        logging.info("开始清空 all_stocks_data 文件夹...")
        clean_all_stocks_data_folder(base_folder)
        
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            logging.info(f"创建总文件夹: {base_folder}")  # 主进程日志，不需要使用safe_log
        
        # 统计信息
        total_stocks = len(df)
        
        # 设置进程数
        num_processes = 20
        logging.info(f"使用 {num_processes} 个进程并行处理股票数据")
        
        # 将股票列表分成多个批次
        batch_size = math.ceil(total_stocks / num_processes)
        batches = [df.iloc[i:i+batch_size] for i in range(0, total_stocks, batch_size)]
        logging.info(f"将 {total_stocks} 只股票分成 {len(batches)} 个批次，每批次约 {batch_size} 只股票")
        
        # 确保进程日志文件夹存在
        logs_dir = os.path.join(script_dir, "logs")
        process_logs_dir = os.path.join(logs_dir, "process_logs")
        if not os.path.exists(process_logs_dir):
            os.makedirs(process_logs_dir)
            logging.info(f"创建进程日志文件夹: {process_logs_dir}")
        
        # 使用进程池并行处理，为每个进程设置日志记录器
        with Pool(processes=num_processes) as pool:
            results = pool.map(process_stock_batch, batches)
        
        # 汇总结果
        successful_stocks = sum(result[0] for result in results)
        failed_stocks = sum(result[1] for result in results)
        
        # 生成总体报告
        logging.info(f"{'='*60}")  # 主进程日志，不需要使用safe_log
        logging.info("批量数据获取完成！")  # 主进程日志，不需要使用safe_log
        logging.info(f"总共处理股票: {total_stocks}")  # 主进程日志，不需要使用safe_log
        logging.info(f"成功获取数据的股票: {successful_stocks}")  # 主进程日志，不需要使用safe_log
        logging.info(f"总体成功率: {successful_stocks/total_stocks*100:.1f}%")  # 主进程日志，不需要使用safe_log
        logging.info(f"失败股票数量: {failed_stocks}")  # 主进程日志，不需要使用safe_log
        
        logging.info(f"\n批量下载完成!")  # 主进程日志，不需要使用safe_log
        logging.info(f"总共下载 {total_stocks} 只股票的1分钟、5分钟、30分钟和日线数据到本地缓存，成功 {successful_stocks} 只，失败 {failed_stocks} 只")  # 主进程日志，不需要使用safe_log
        
    except Exception as e:
        logging.error(f"读取CSV文件时发生错误: {e}")
        return

if __name__ == "__main__":
    # 设置多进程启动方法
    multiprocessing.set_start_method('spawn', force=True)
    main()