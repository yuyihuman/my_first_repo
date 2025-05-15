import os
import shutil
import subprocess
import time
import sys
import logging

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
    logging.info("开始执行港股通数据分析流程")
    
    # 1. 清空数据和图表目录
    clear_directory("data")
    clear_directory("charts")
    
    # 2. 获取港股通成分股列表
    get_stocks_cmd = ["python", "get_hk_ggt_stocks.py"]
    if run_command(get_stocks_cmd, "获取港股通成分股列表") != 0:
        logging.error("获取港股通成分股列表失败，终止流程")
        return
    
    # 3. 批量提取东方财富网数据
    extract_data_cmd = ["python", "batch_extract_eastmoney.py"]
    if run_command(extract_data_cmd, "批量提取东方财富网数据") != 0:
        logging.error("批量提取东方财富网数据失败，终止流程")
        return
    
    # 4. 生成图表
    generate_charts_cmd = ["python", "generate_charts.py"]
    if run_command(generate_charts_cmd, "生成图表") != 0:
        logging.error("生成图表失败，终止流程")
        return
    
    logging.info("全部流程执行完毕！")
    logging.info("- 数据文件保存在 data 目录")
    logging.info("- 图表文件保存在 charts 目录")
    logging.info("- 日志文件保存在 logs 目录")

if __name__ == "__main__":
    setup_logger()
    main()