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
    log_filename = os.path.join(process_logs_dir, f"financial_data_{process_id}_{timestamp}.log")
    
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
    log_filename = os.path.join(logs_dir, f"financial_data_main_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

def callback_func(data):
    """财务数据下载回调函数"""
    # 获取当前进程ID
    process_id = multiprocessing.current_process().name
    
    # 使用进程特定的日志记录器记录回调信息
    if process_id in process_loggers:
        safe_log(f"财务数据下载回调: {data}")
    else:
        # 如果是主进程调用，使用主进程日志记录器
        logging.info(f"财务数据下载回调: {data}")

def process_stock_batch(stock_batch):
    """
    处理一批股票数据
    
    Args:
        stock_batch: 包含股票代码和名称的DataFrame批次
    
    Returns:
        成功下载的股票数量
    """
    process_id = multiprocessing.current_process().name
    batch_start_index = stock_batch.index[0] if not stock_batch.empty else 0
    batch_end_index = stock_batch.index[-1] if not stock_batch.empty else 0
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建财务数据输出文件夹（在脚本所在目录下）
    base_output_dir = os.path.join(script_dir, "financial_data")
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)
    
    # 记录进程开始处理的信息
    safe_log(f"{'='*80}")
    safe_log(f"进程 {process_id} 开始处理批次，包含 {len(stock_batch)} 只股票，索引范围: {batch_start_index}-{batch_end_index}")
    safe_log(f"{'='*80}")
    
    # 构造股票代码列表（添加交易所后缀）
    stock_codes = []
    for _, row in stock_batch.iterrows():
        stock_code = str(row['代码']).zfill(6)
        if stock_code.startswith('6'):
            full_code = f"{stock_code}.SH"  # 上海交易所
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            full_code = f"{stock_code}.SZ"  # 深圳交易所
        else:
            continue  # 跳过不支持的代码
        stock_codes.append(full_code)
    
    if not stock_codes:
        safe_log(f"进程 {process_id} 没有有效的股票代码", "warning")
        return 0
    
    safe_log(f"进程 {process_id} 处理 {len(stock_codes)} 只股票: {stock_codes}")
    success_count = 0
    
    try:
        # 下载财务数据
        safe_log(f"进程 {process_id} 正在下载财务数据...")
        safe_log(f"进程 {process_id} 下载参数: 股票数量={len(stock_codes)}, 开始时间=19900101")
        
        # 记录下载开始时间
        download_start_time = datetime.now()
        safe_log(f"进程 {process_id} 下载开始时间: {download_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 下载财务数据
        xtdata.download_financial_data2(stock_codes, table_list=[], start_time='19900101', end_time='', callback=callback_func)
        
        # 记录下载结束时间
        download_end_time = datetime.now()
        download_duration = (download_end_time - download_start_time).total_seconds()
        safe_log(f"进程 {process_id} 下载结束时间: {download_end_time.strftime('%Y-%m-%d %H:%M:%S')}, 耗时: {download_duration:.2f}秒")
        
        # 获取财务数据
        safe_log(f"进程 {process_id} 正在获取财务数据...")
        get_data_start_time = datetime.now()
        data = xtdata.get_financial_data(stock_codes, table_list=[], start_time='', end_time='', report_type='report_time')
        get_data_end_time = datetime.now()
        get_data_duration = (get_data_end_time - get_data_start_time).total_seconds()
        safe_log(f"进程 {process_id} 获取财务数据完成，耗时: {get_data_duration:.2f}秒")
        
        if data is not None and isinstance(data, dict):
            safe_log(f"进程 {process_id} 成功获取到 {len(data)} 个股票的财务数据")
            
            # 为每个股票代码分别保存数据
            safe_log(f"进程 {process_id} 开始保存 {len(data)} 只股票的财务数据...")
            save_start_time = datetime.now()
            
            for i, (stock_code, stock_data) in enumerate(data.items(), 1):
                try:
                    # 记录处理进度
                    if i % 10 == 0 or i == 1 or i == len(data):
                        safe_log(f"进程 {process_id} 正在保存第 {i}/{len(data)} 只股票 ({stock_code}) 的财务数据...")
                    
                    # 为每个股票创建单独的文件夹
                    stock_dir = os.path.join(base_output_dir, stock_code)
                    if not os.path.exists(stock_dir):
                        os.makedirs(stock_dir)
                        
                    if isinstance(stock_data, dict):
                        # 如果股票数据也是字典（包含多个报表类型）
                        table_count = 0
                        table_rows_total = 0
                        
                        for table_name, table_data in stock_data.items():
                            if hasattr(table_data, 'to_csv') and not table_data.empty:
                                csv_filename = os.path.join(stock_dir, f"{table_name}.csv")
                                table_data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
                                
                                # 获取文件大小
                                file_size = os.path.getsize(csv_filename)
                                file_size_kb = file_size / 1024
                                
                                safe_log(f"进程 {process_id} 已保存 {stock_code} 的 {table_name} 数据，形状: {table_data.shape}，文件大小: {file_size_kb:.2f}KB")
                                table_count += 1
                                table_rows_total += len(table_data)
                        
                        if table_count > 0:
                            success_count += 1
                            safe_log(f"进程 {process_id} 股票 {stock_code} 成功保存 {table_count} 个财务报表，总行数: {table_rows_total}")
                        else:
                            safe_log(f"进程 {process_id} 股票 {stock_code} 没有有效的财务数据", "warning")
                            
                    elif hasattr(stock_data, 'to_csv') and not stock_data.empty:
                        # 如果股票数据直接是DataFrame
                        csv_filename = os.path.join(stock_dir, "financial_data.csv")
                        stock_data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
                        
                        # 获取文件大小
                        file_size = os.path.getsize(csv_filename)
                        file_size_kb = file_size / 1024
                        
                        safe_log(f"进程 {process_id} 已保存 {stock_code} 的财务数据，形状: {stock_data.shape}，文件大小: {file_size_kb:.2f}KB")
                        success_count += 1
                    else:
                        safe_log(f"进程 {process_id} 股票 {stock_code} 的数据格式不支持或为空", "warning")
                        
                except Exception as e:
                    safe_log(f"进程 {process_id} 保存股票 {stock_code} 财务数据时发生错误: {e}", "error")
            
            # 记录保存完成时间和耗时
            save_end_time = datetime.now()
            save_duration = (save_end_time - save_start_time).total_seconds()
            safe_log(f"进程 {process_id} 完成保存 {len(data)} 只股票的财务数据，成功: {success_count}，耗时: {save_duration:.2f}秒")
                    
        else:
            safe_log(f"进程 {process_id} 没有获取到有效的财务数据", "warning")
            
    except Exception as e:
        safe_log(f"进程 {process_id} 下载财务数据时发生错误: {e}", "error")
    
    # 记录进程完成处理的信息
    safe_log(f"{'='*80}")
    safe_log(f"进程 {process_id} 完成批次处理，成功: {success_count}/{len(stock_codes)} 只股票")
    safe_log(f"{'='*80}")
    
    return success_count

def main():
    """
    主函数：批量下载所有0、3、6开头股票的财务数据，使用多进程加速
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
        
        # 过滤出0、3、6开头的股票
        df['代码_str'] = df['代码'].astype(str).str.zfill(6)
        filtered_df = df[df['代码_str'].str.startswith(('0', '3', '6'))]
        logging.info(f"过滤出0、3、6开头的股票共 {len(filtered_df)} 只")  # 主进程日志，不需要使用safe_log
        
        if len(filtered_df) == 0:
            logging.warning("没有找到符合条件的股票")  # 主进程日志，不需要使用safe_log
            return
        
        # 创建财务数据输出文件夹（在脚本所在目录下）
        base_output_dir = os.path.join(script_dir, "financial_data")
        if not os.path.exists(base_output_dir):
            os.makedirs(base_output_dir)
            logging.info(f"创建输出文件夹: {base_output_dir}")  # 主进程日志，不需要使用safe_log
        
        # 统计信息
        total_stocks = len(filtered_df)
        
        # 设置进程数
        num_processes = 20
        logging.info(f"使用 {num_processes} 个进程并行处理股票数据")
        
        # 将股票列表分成多个批次
        batch_size = math.ceil(total_stocks / num_processes)
        batches = [filtered_df.iloc[i:i+batch_size] for i in range(0, total_stocks, batch_size)]
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
        successful_stocks = sum(results)
        processed_stocks = total_stocks
        
        # 生成总体报告
        logging.info(f"{'='*60}")  # 主进程日志，不需要使用safe_log
        logging.info("批量财务数据下载完成！")  # 主进程日志，不需要使用safe_log
        logging.info(f"总共处理股票: {processed_stocks}")  # 主进程日志，不需要使用safe_log
        logging.info(f"成功下载财务数据的股票: {successful_stocks}")  # 主进程日志，不需要使用safe_log
        logging.info(f"总体成功率: {successful_stocks/processed_stocks*100:.1f}%")  # 主进程日志，不需要使用safe_log
        
        # 保存总体报告
        report_content = f"""批量股票财务数据下载报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计信息:
- 总共处理股票: {processed_stocks}
- 成功下载财务数据的股票: {successful_stocks}
- 总体成功率: {successful_stocks/processed_stocks*100:.1f}%
- 使用进程数: {num_processes}

数据存储位置: {base_output_dir}/
每个股票的财务数据存储在独立的子文件夹中

数据来源:
- xtquant库 (迅投量化)

数据类型:
- 财务报表数据（资产负债表、利润表、现金流量表等）

注意事项:
- 所有文件使用UTF-8-BOM编码
- 部分股票可能因为数据源限制无法获取完整数据
- 建议定期更新数据
"""
        
        report_filename = os.path.join(base_output_dir, "financial_data_download_report.txt")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logging.info(f"\n批量下载完成!")  # 主进程日志，不需要使用safe_log
        logging.info(f"总共处理 {processed_stocks} 只股票，成功 {successful_stocks} 只")  # 主进程日志，不需要使用safe_log
        logging.info(f"详细报告已保存到: {report_filename}")  # 主进程日志，不需要使用safe_log
        
    except Exception as e:
        logging.error(f"读取CSV文件时发生错误: {e}")  # 主进程日志，不需要使用safe_log
        return

if __name__ == "__main__":
    main()