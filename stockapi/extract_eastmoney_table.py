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
from datetime import datetime as dt

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
    
    # 配置日志格式（只输出到文件，时间格式更清晰）
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    return logging.getLogger()

def extract_stock_code(url):
    """从URL中提取股票代码"""
    match = re.search(r'/StockHdDetail/(\d+)/', url)
    if match:
        return match.group(1)
    return "unknown"

def get_latest_date_from_file(file_path):
    """从现有CSV文件中获取最新的日期"""
    if not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        if df.empty or '日期' not in df.columns:
            return None
        
        # 将日期列转换为datetime格式并找到最新日期
        df['日期'] = pd.to_datetime(df['日期'])
        latest_date = df['日期'].max()
        return latest_date.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return None

def parse_date_from_row(date_str):
    """解析行数据中的日期字符串"""
    try:
        return dt.strptime(date_str, '%Y-%m-%d')
    except:
        try:
            return dt.strptime(date_str, '%Y/%m/%d')
        except:
            return None

def extract_eastmoney_table(url, output_file=None, wait_time=10, log_file=None, output_dir="data", incremental=False):
    """
    从东方财富网页面直接提取表格数据
    
    参数:
        url: 目标网页URL
        output_file: 输出文件名
        wait_time: 等待页面加载的时间(秒)
        log_file: 日志文件路径
        output_dir: 输出文件夹路径
        incremental: 是否启用增量更新模式
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
    
    # 增量更新模式：获取现有文件的最新日期
    latest_date_str = None
    latest_date = None
    if incremental:
        latest_date_str = get_latest_date_from_file(output_path)
        if latest_date_str:
            latest_date = dt.strptime(latest_date_str, '%Y-%m-%d')
            logger.info(f"增量更新模式：现有数据最新日期为 {latest_date_str}")
        else:
            logger.info("增量更新模式：未找到现有数据，将获取所有数据")
    
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
            # 优先使用最常成功的选择器
            logger.debug("尝试使用选择器: table")
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            table_selector = "table"
            logger.info("找到表格元素: table")
        except Exception as e:
            logger.warning(f"未找到table: {str(e)}")
            # 备用选择器
            logger.debug("尝试使用选择器: table.tab1")
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.tab1"))
            )
            table_selector = "table.tab1"
            logger.info("找到表格元素: table.tab1")
        
        # 记录找到的表格数量
        tables = driver.find_elements(By.CSS_SELECTOR, table_selector)
        logger.info(f"找到 {len(tables)} 个表格元素")
        
        # 提取表格数据
        rows = []
        new_rows = []  # 用于存储增量更新的新数据
        found_old_data = False  # 标记是否已经遇到旧数据
        
        # 遍历表格行
        table_rows = driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr")
        logger.info(f"找到 {len(table_rows)} 行数据")
        
        # 跳过表头行，直接提取数据行
        for i, row_element in enumerate(table_rows[1:], 1):
            cell_elements = row_element.find_elements(By.TAG_NAME, "td")
            if cell_elements:
                row_data = []
                for cell in cell_elements:
                    cell_text = cell.text.strip()
                    row_data.append(cell_text)
                
                # 在增量更新模式下，检查日期是否比现有数据更新
                if incremental and latest_date and len(row_data) > 0:
                    row_date = parse_date_from_row(row_data[0])  # 假设第一列是日期
                    if row_date and row_date <= latest_date:
                        logger.debug(f"遇到旧数据行 {i}: {row_data[0]} (不晚于 {latest_date_str})")
                        found_old_data = True
                        # 由于数据是按日期倒序排列，遇到第一个旧数据就可以停止
                        break
                    else:
                        logger.debug(f"新数据行 {i}: {row_data[0]}")
                        new_rows.append(row_data)
                        rows.append(row_data)  # 只在增量模式下添加新数据
                else:
                    # 非增量模式，添加所有数据
                    rows.append(row_data)
                
                logger.debug(f"行 {i}: {row_data}")
        
        # 使用自定义表头
        headers = ['日期', '收盘价', '涨跌幅', '持股数量', '持股市值', '持股占比', '当日增持', '5日增持', '10日增持']
        logger.info(f"使用自定义表头: {headers}")
        
        # 在增量更新模式下，处理数据保存逻辑
        if incremental and latest_date:
            if not new_rows:
                if found_old_data:
                    logger.info("增量更新模式：没有找到新数据，已提前停止遍历")
                else:
                    logger.info("增量更新模式：没有找到新数据")
                return None
            
            logger.info(f"增量更新模式：找到 {len(new_rows)} 行新数据")
            
            # 确保新数据与表头匹配
            if new_rows and len(headers) != len(new_rows[0]):
                logger.warning(f"表头数量({len(headers)})与数据列数({len(new_rows[0])})不匹配")
                if len(headers) > len(new_rows[0]):
                    headers = headers[:len(new_rows[0])]
                else:
                    for row in new_rows:
                        row = row[:len(headers)]
            
            # 创建新数据的DataFrame
            new_df = pd.DataFrame(new_rows, columns=headers)
            
            # 读取现有数据并合并
            if os.path.exists(output_path):
                existing_df = pd.read_csv(output_path, encoding='utf-8-sig')
                # 将新数据添加到现有数据的顶部（因为数据是按日期倒序排列的）
                combined_df = pd.concat([new_df, existing_df], ignore_index=True)
            else:
                combined_df = new_df
            
            # 保存合并后的数据
            combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"增量更新完成：新增 {len(new_rows)} 行数据到 {output_path}")
            
            return new_df
        else:
            # 非增量更新模式：原有逻辑
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
    parser.add_argument("--incremental", action="store_true", help="启用增量更新模式，只获取比现有数据更新的记录")
    
    args = parser.parse_args()
    
    extract_eastmoney_table(args.url, args.output, args.wait, args.log, args.dir, args.incremental)