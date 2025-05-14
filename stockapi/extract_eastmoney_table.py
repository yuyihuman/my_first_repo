import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import re
import logging
import datetime

# 配置日志
def setup_logger(log_file=None):
    """设置日志记录器"""
    if log_file is None:
        # 创建logs目录（如果不存在）
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 使用时间戳创建日志文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"eastmoney_scraper_{timestamp}.log")
    
    # 配置日志格式
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return logging.getLogger()

def extract_stock_code(url):
    """从URL中提取股票代码"""
    match = re.search(r'/StockHdDetail/(\d+)/', url)
    if match:
        return match.group(1)
    return "unknown"

def extract_eastmoney_table(url, output_file=None, wait_time=10, log_file=None, output_dir="data"):
    """
    从东方财富网页面直接提取表格数据
    
    参数:
        url: 目标网页URL
        output_file: 输出文件名
        wait_time: 等待页面加载的时间(秒)
        log_file: 日志文件路径
        output_dir: 输出文件夹路径
    """
    # 设置日志
    logger = setup_logger(log_file)
    
    # 从URL中提取股票代码
    stock_code = extract_stock_code(url)
    logger.info(f"提取到股票代码: {stock_code}")
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    # 如果没有指定输出文件名，则使用股票代码命名
    if output_file is None:
        output_file = f"{stock_code}_eastmoney_table.csv"
    
    # 将输出文件路径与目录结合
    output_path = os.path.join(output_dir, output_file)
    logger.info(f"输出文件路径: {output_path}")
    
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")  # 减少日志输出
    
    logger.info(f"正在访问页面: {url}")
    driver = None
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.debug("Chrome浏览器已启动")
        
        driver.get(url)
        logger.info(f"等待页面加载 {wait_time} 秒...")
        time.sleep(wait_time)  # 等待页面加载和JavaScript执行
        
        # 记录页面源代码，便于调试
        logger.debug("页面源代码前1000字符:")
        logger.debug(driver.page_source[:1000] + "...")
        
        # 尝试查找表格元素
        logger.info("尝试查找表格元素...")
        try:
            # 先尝试使用原始选择器
            logger.debug("尝试使用选择器: table.tab1")
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.tab1"))
            )
            table_selector = "table.tab1"
            logger.info("找到表格元素: table.tab1")
        except Exception as e:
            logger.warning(f"未找到table.tab1: {str(e)}")
            # 尝试其他可能的选择器
            logger.debug("尝试使用选择器: table")
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            table_selector = "table"
            logger.info("找到表格元素: table")
        
        # 记录找到的表格数量
        tables = driver.find_elements(By.CSS_SELECTOR, table_selector)
        logger.info(f"找到 {len(tables)} 个表格元素")
        
        # 提取表格数据
        rows = []
        row_elements = driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr")
        logger.debug(f"找到 {len(row_elements)} 行数据")
        
        # 跳过表头行，直接提取数据行
        for i, row_element in enumerate(row_elements[1:], 1):
            cell_elements = row_element.find_elements(By.TAG_NAME, "td")
            if cell_elements:
                row_data = []
                for cell in cell_elements:
                    cell_text = cell.text.strip()
                    row_data.append(cell_text)
                rows.append(row_data)
                logger.debug(f"行 {i}: {row_data}")
        
        # 使用自定义表头
        headers = ['日期', '收盘价', '涨跌幅', '持股数量', '持股市值', '持股占比', '当日增持', '5日增持', '10日增持']
        logger.info(f"使用自定义表头: {headers}")
        
        # 创建DataFrame
        if not rows:
            logger.error("未能提取到有效的表格数据")
            return None
            
        logger.info(f"提取到 {len(rows)} 行数据")
        
        # 确保行数据与表头匹配
        if rows and len(headers) != len(rows[0]):
            logger.warning(f"表头数量({len(headers)})与数据列数({len(rows[0])})不匹配")
            # 尝试调整
            if len(headers) > len(rows[0]):
                headers = headers[:len(rows[0])]
            else:
                for row in rows:
                    row = row[:len(headers)]
        
        df = pd.DataFrame(rows, columns=headers)
        
        # 保存到CSV
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"表格数据已保存到 {output_path}")
        
        return df
    
    except Exception as e:
        logger.error(f"发生错误: {str(e)}", exc_info=True)
        return None
    
    finally:
        if driver:
            driver.quit()
            logger.debug("浏览器已关闭")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="从东方财富网提取表格数据")
    parser.add_argument("url", help="要分析的网页URL")
    parser.add_argument("--output", help="输出CSV文件名（默认使用股票代码命名）")
    parser.add_argument("--wait", type=int, default=10, help="等待页面加载的时间(秒)")
    parser.add_argument("--log", help="日志文件路径（默认自动生成）")
    parser.add_argument("--dir", default="data", help="输出文件夹路径（默认为'data'）")
    
    args = parser.parse_args()
    
    extract_eastmoney_table(args.url, args.output, args.wait, args.log, args.dir)