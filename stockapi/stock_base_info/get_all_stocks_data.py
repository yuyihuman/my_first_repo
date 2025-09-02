from xtquant import xtdata
import pandas as pd
import os
from datetime import datetime
import time
import logging

def get_stock_data(stock_code, stock_name, base_folder="all_stocks_data"):
    """
    下载单个股票的1分钟和日线数据到本地缓存
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        base_folder: 数据缓存的基础文件夹（仅用于日志记录）
    """
    logging.info(f"开始下载股票 {stock_code} ({stock_name}) 的1分钟和日线数据到本地缓存...")
    
    success_count = 0
    total_attempts = 2  # 1分钟数据 + 日线数据
    
    # 构造股票代码格式（需要添加交易所后缀）
    if stock_code.startswith('6'):
        full_code = f"{stock_code}.SH"  # 上海交易所（包括主板和科创板）
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        full_code = f"{stock_code}.SZ"  # 深圳交易所
    else:
        logging.warning(f"  跳过不支持的股票代码: {stock_code}")
        return False
    
    try:
        # 下载日线数据到本地
        logging.info(f"  下载日线数据到本地（从1990年开始）...")
        download_result = xtdata.download_history_data(full_code, period='1d', start_time='19900101')
        logging.info(f"  日线数据下载结果: {download_result}")
        logging.info(f"    日线数据已下载到本地缓存")
        success_count += 1
        
        # 尝试下载1分钟数据（从1990年开始，如果支持的话）
        logging.info(f"  下载1分钟数据到本地（从1990年开始）...")
        try:
            download_result_1m = xtdata.download_history_data(full_code, period='1m', start_time='19900101')
            logging.info(f"  1分钟数据下载结果: {download_result_1m}")
            logging.info(f"    1分钟数据已下载到本地缓存")
            success_count += 1
        except Exception as e:
            logging.info(f"    1分钟数据下载失败，跳过: {e}")
        
    except Exception as e:
        logging.error(f"    数据获取失败: {e}")
    

    
    logging.info(f"  股票 {stock_code} 数据下载完成，成功率: {success_count}/{total_attempts}")
    return success_count > 0

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
    
    if deleted_count > 0:
        print(f"已清理 {deleted_count} 个旧日志文件")

def setup_logging():
    """
    设置日志配置
    """
    # 创建logs文件夹
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 清理旧日志文件
    clean_old_logs(logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"stock_data_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

def main():
    """
    主函数：批量下载所有股票的历史数据到本地缓存
    """
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"日志文件: {log_filename}")
    
    # 读取股票列表CSV文件
    csv_file = "stock_data.csv"
    
    if not os.path.exists(csv_file):
        logging.error(f"错误：找不到文件 {csv_file}")
        return
    
    logging.info(f"读取股票列表文件: {csv_file}")
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        logging.info(f"共找到 {len(df)} 只股票")
        
        # 过滤掉8开头的股票（北交所）
        df = df[~df['代码'].astype(str).str.startswith('8')]
        logging.info(f"过滤8开头股票后剩余 {len(df)} 只股票")
        
        # 创建总的数据文件夹
        base_folder = "all_stocks_data"
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            logging.info(f"创建总文件夹: {base_folder}")
        
        # 统计信息
        total_stocks = len(df)
        processed_stocks = 0
        successful_stocks = 0
        
        # 批量处理所有股票
        for index, row in df.iterrows():
            stock_code = str(row['代码']).zfill(6)  # 确保股票代码是6位数字
            stock_name = row['名称']
            
            processed_stocks += 1
            logging.info(f"{'='*60}")
            logging.info(f"处理进度: {processed_stocks}/{total_stocks} ({processed_stocks/total_stocks*100:.1f}%)")
            logging.info(f"当前股票: {stock_code} - {stock_name}")
            
            try:
                result = get_stock_data(stock_code, stock_name)
                if result:
                    successful_stocks += 1
                else:
                    failed_stocks += 1
                
                # 添加延时，避免请求过于频繁
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"处理股票 {stock_code} 时发生错误: {e}")
                failed_stocks += 1
        
        # 统计完成
        
        # 生成总体报告
        logging.info(f"{'='*60}")
        logging.info("批量数据获取完成！")
        logging.info(f"总共处理股票: {total_stocks}")
        logging.info(f"成功获取数据的股票: {successful_stocks}")
        logging.info(f"总体成功率: {successful_stocks/total_stocks*100:.1f}%")
        logging.info(f"失败股票数量: {failed_stocks}")
        
        logging.info(f"\n批量下载完成!")
        logging.info(f"总共下载 {total_stocks} 只股票数据到本地缓存，成功 {successful_stocks} 只，失败 {failed_stocks} 只")
        
    except Exception as e:
        logging.error(f"读取CSV文件时发生错误: {e}")
        return

if __name__ == "__main__":
    main()