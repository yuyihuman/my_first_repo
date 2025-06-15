import os
import shutil
import subprocess
import time
import sys
import logging
import os
import pandas as pd
import datetime

def setup_logger():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "run_stock_analysis.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

def clear_directory(directory):
    """清空指定目录中的所有文件（保留目录结构）"""
    if os.path.exists(directory):
        logging.info(f"正在清空 {directory} 目录...")
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    logging.info(f"已删除文件: {file_path}")
            except Exception as e:
                logging.error(f"删除文件 {file_path} 时出错: {e}")
    else:
        os.makedirs(directory)
        logging.info(f"创建目录: {directory}")

def check_data_freshness():
    """检查数据是否需要更新"""
    data_dir = "data"
    
    # 确保data目录存在
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logging.info(f"创建目录: {data_dir}")
        return True  # 目录不存在，需要获取数据
    
    # 检查港股通成分股列表文件是否存在
    stocks_file = os.path.join(data_dir, "hk_ggt_stocks.csv")
    if not os.path.exists(stocks_file):
        logging.info("港股通成分股列表文件不存在，需要获取")
        return True
    
    # 检查文件修改时间，如果超过1天则需要更新
    file_mtime = os.path.getmtime(stocks_file)
    current_time = time.time()
    time_diff = current_time - file_mtime
    
    if time_diff > 24 * 3600:  # 超过24小时
        logging.info(f"港股通成分股列表文件已过期（{time_diff/3600:.1f}小时），需要更新")
        return True
    
    logging.info(f"港股通成分股列表文件较新（{time_diff/3600:.1f}小时），无需更新")
    return False

def get_latest_data_date():
    """获取现有数据中的最新日期"""
    data_dir = "data"
    latest_date = None
    
    # 遍历所有CSV文件，找到最新的数据日期
    for filename in os.listdir(data_dir):
        if filename.endswith("_eastmoney_table.csv") and filename != "hk_ggt_stocks.csv":
            file_path = os.path.join(data_dir, filename)
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                if not df.empty and '日期' in df.columns:
                    # 获取第一行的日期（最新日期）
                    file_latest_date = pd.to_datetime(df['日期'].iloc[0]).date()
                    if latest_date is None or file_latest_date > latest_date:
                        latest_date = file_latest_date
            except Exception as e:
                logging.warning(f"读取文件 {filename} 时出错: {e}")
                continue
    
    return latest_date

def should_update_stock_data():
    """判断是否需要更新股票数据"""
    latest_date = get_latest_data_date()
    
    if latest_date is None:
        logging.info("未找到现有数据，需要获取数据")
        return True
    
    # 获取昨天的日期（因为今天的数据可能还没有）
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    
    if latest_date < yesterday:
        logging.info(f"现有数据最新日期为 {latest_date}，需要更新到 {yesterday}")
        return True
    else:
        logging.info(f"现有数据已是最新（{latest_date}），无需更新")
        return False

def run_command(command, description):
    """运行命令并打印输出"""
    logging.info("="*50)
    logging.info(f"开始{description}...")
    logging.info(f"执行命令: {' '.join(command)}")
    logging.info("="*50)
    
    start_time = time.time()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # 实时输出命令执行结果
    for line in process.stdout:
        logging.info(line.rstrip())
    
    process.wait()
    end_time = time.time()
    
    logging.info("="*50)
    logging.info(f"{description}完成，耗时: {end_time - start_time:.2f}秒")
    logging.info(f"返回代码: {process.returncode}")
    logging.info("="*50)
    
    return process.returncode

def main():
    """主函数，按顺序执行所有步骤"""
    logging.info("开始执行港股通数据分析流程（增量更新模式）")
    
    # 1. 检查是否需要更新港股通成分股列表
    need_update_stocks = check_data_freshness()
    if need_update_stocks:
        logging.info("需要更新港股通成分股列表")
        get_stocks_cmd = ["python", "get_hk_ggt_stocks.py"]
        if run_command(get_stocks_cmd, "获取港股通成分股列表") != 0:
            logging.error("获取港股通成分股列表失败，终止流程")
            return
    else:
        logging.info("港股通成分股列表无需更新，跳过")
    
    # 2. 检查是否需要更新股票数据
    need_update_data = should_update_stock_data()
    if need_update_data:
        logging.info("需要更新股票数据")
        extract_data_cmd = ["python", "batch_extract_eastmoney.py", "--incremental"]
        if run_command(extract_data_cmd, "批量提取东方财富网数据（增量更新）") != 0:
            logging.error("批量提取东方财富网数据失败，终止流程")
            return
    else:
        logging.info("股票数据已是最新，跳过数据提取")
    
    # 3. 检查是否需要重新生成图表
    # 只有在数据更新后才重新生成图表
    if need_update_data:
        # 清空图表目录，重新生成
        clear_directory("charts")
        generate_charts_cmd = ["python", "generate_charts.py"]
        if run_command(generate_charts_cmd, "生成图表") != 0:
            logging.error("生成图表失败，终止流程")
            return
        logging.info("图表已重新生成")
    else:
        logging.info("数据未更新，图表无需重新生成")
    
    if need_update_stocks or need_update_data:
        logging.info("数据分析流程执行完毕！")
        logging.info("- 数据文件保存在 data 目录")
        logging.info("- 图表文件保存在 charts 目录")
        logging.info("- 日志文件保存在 logs 目录")
    else:
        logging.info("所有数据均为最新，无需执行任何更新操作")

if __name__ == "__main__":
    setup_logger()
    main()