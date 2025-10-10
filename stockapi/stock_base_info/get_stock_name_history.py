import akshare as ak
import pandas as pd
import json
import time
import random
import logging
import os
from datetime import datetime

def setup_logging():
    """设置日志配置"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建logs文件夹
    logs_dir = os.path.join(script_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"stock_name_history_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return log_filename

def load_stock_codes(csv_file):
    """从CSV文件中加载股票代码"""
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
        stock_codes = df['代码'].astype(str).str.zfill(6).tolist()  # 确保是6位数字
        logging.info(f"成功加载 {len(stock_codes)} 个股票代码")
        return stock_codes
    except Exception as e:
        logging.error(f"加载股票代码失败: {e}")
        return []

def get_stock_name_history(stock_code):
    """获取单个股票的曾用名"""
    max_retries = 2  # 最多重试2次
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # 调用akshare接口获取曾用名
            name_history = ak.stock_info_change_name(symbol=stock_code)
            
            if name_history is not None and not name_history.empty:
                # 提取name列的值作为曾用名列表
                history_list = name_history['name'].tolist()
                logging.info(f"股票 {stock_code} 获取到 {len(history_list)} 条曾用名记录: {history_list}")
                return history_list
            else:
                logging.info(f"股票 {stock_code} 没有曾用名记录")
                return []
                
        except ValueError as e:
            if "No tables found" in str(e):
                if retry_count < max_retries:
                    retry_count += 1
                    wait_minutes = 10
                    logging.warning(f"股票 {stock_code} 遇到'No tables found'错误，第{retry_count}次重试，等待{wait_minutes}分钟...")
                    time.sleep(wait_minutes * 60)  # 等待10分钟
                    continue
                else:
                    logging.info(f"股票 {stock_code} 重试{max_retries}次后仍然'No tables found'，跳过")
                    return []
            else:
                logging.warning(f"股票 {stock_code} 获取曾用名时发生ValueError: {e}")
                return None
        except Exception as e:
            logging.error(f"股票 {stock_code} 获取曾用名失败: {e}")
            return None
    
    return None

def save_progress(data, output_file):
    """保存进度到JSON文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"进度已保存到 {output_file}")
    except Exception as e:
        logging.error(f"保存进度失败: {e}")

def load_existing_data(output_file):
    """加载已存在的数据"""
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logging.info(f"加载已存在的数据，包含 {len(data)} 个股票记录")
            return data
        except Exception as e:
            logging.warning(f"加载已存在数据失败: {e}")
            return {}
    return {}

def main():
    """主函数"""
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"日志文件: {log_filename}")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 输入和输出文件路径
    csv_file = os.path.join(script_dir, "stock_data.csv")
    output_file = os.path.join(script_dir, "stock_name_history.json")
    
    # 检查CSV文件是否存在
    if not os.path.exists(csv_file):
        logging.error(f"错误：找不到文件 {csv_file}")
        return
    
    # 加载股票代码
    stock_codes = load_stock_codes(csv_file)
    if not stock_codes:
        logging.error("没有加载到任何股票代码")
        return
    
    # 加载已存在的数据（支持断点续传）
    stock_name_data = load_existing_data(output_file)
    
    # 统计信息
    total_stocks = len(stock_codes)
    processed_count = len(stock_name_data)
    success_count = 0
    error_count = 0
    
    logging.info(f"开始处理股票曾用名，总计 {total_stocks} 个股票")
    logging.info(f"已处理 {processed_count} 个股票，剩余 {total_stocks - processed_count} 个")
    
    start_time = time.time()
    
    for i, stock_code in enumerate(stock_codes, 1):
        # 跳过已处理的股票
        if stock_code in stock_name_data:
            continue
        
        logging.info(f"处理进度: {i}/{total_stocks} ({i/total_stocks*100:.1f}%) - 股票代码: {stock_code}")
        
        # 获取曾用名
        name_history = get_stock_name_history(stock_code)
        
        if name_history is not None:
            stock_name_data[stock_code] = name_history
            if name_history:  # 如果有曾用名记录
                success_count += 1
        else:
            error_count += 1
        
        # 每处理10个股票保存一次进度
        if i % 10 == 0:
            save_progress(stock_name_data, output_file)
        
        # 等待10秒，避免频繁调用API
        wait_time = 10.0
        logging.debug(f"等待 {wait_time:.1f} 秒...")
        time.sleep(wait_time)
        
        # 每处理100个股票输出一次统计信息
        if i % 100 == 0:
            elapsed_time = time.time() - start_time
            avg_time_per_stock = elapsed_time / i
            remaining_stocks = total_stocks - i
            estimated_remaining_time = remaining_stocks * avg_time_per_stock
            
            logging.info(f"统计信息 - 已处理: {i}, 成功: {success_count}, 错误: {error_count}")
            logging.info(f"已用时: {elapsed_time/60:.1f}分钟, 预计剩余时间: {estimated_remaining_time/60:.1f}分钟")
    
    # 最终保存
    save_progress(stock_name_data, output_file)
    
    # 输出最终统计
    total_time = time.time() - start_time
    logging.info("="*60)
    logging.info("处理完成！")
    logging.info(f"总股票数: {total_stocks}")
    logging.info(f"成功获取曾用名的股票数: {success_count}")
    logging.info(f"错误数: {error_count}")
    logging.info(f"总用时: {total_time/60:.1f}分钟")
    logging.info(f"结果已保存到: {output_file}")
    logging.info("="*60)

if __name__ == "__main__":
    main()