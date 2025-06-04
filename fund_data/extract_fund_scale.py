import sys
import os

# 添加上级目录到路径，以便导入 extract_eastmoney_table 模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from stockapi.extract_eastmoney_table import setup_logger

import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

def extract_fund_code(url):
    """从URL中提取基金代码"""
    match = re.search(r'/gmbd_(\d+)\.html', url)
    if match:
        return match.group(1)
    return "unknown"

# 定义函数处理期末净资产列
def clean_asset_value(value):
    """清理期末净资产值，将带逗号的文本格式转换为数字"""
    if pd.isna(value) or value == '---':
        return value
    
    # 如果是字符串类型且包含逗号，移除引号和逗号
    if isinstance(value, str):
        # 移除引号
        value = value.strip('"')
        # 移除逗号
        value = value.replace(',', '')
        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            return value
    return value

def extract_fund_scale_table(url, output_file=None, wait_time=10, log_file=None, output_dir="output"):
    """
    从东方财富网页面提取基金规模变动表格数据
    
    参数:
        url: 目标网页URL
        output_file: 输出文件名
        wait_time: 等待页面加载的时间(秒)
        log_file: 日志文件路径
        output_dir: 输出文件夹路径
    """
    # 设置日志
    logger = setup_logger(log_file)
    
    # 从URL中提取基金代码
    fund_code = extract_fund_code(url)
    logger.info(f"提取到基金代码: {fund_code}")
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    # 如果没有指定输出文件名，则使用基金代码命名
    if output_file is None:
        output_file = f"{fund_code}_fund_scale.csv"
    
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
            # 先尝试定位包含基金规模变动表格的div
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # 找到所有表格
            tables = driver.find_elements(By.TAG_NAME, "table")
            logger.info(f"找到 {len(tables)} 个表格元素")
            
            target_table = None
            
            for table in tables:
                # 检查表格前面是否有"份额/净资产规模变动详情"标题
                try:
                    prev_element = table.find_element(By.XPATH, "./preceding::div[contains(text(), '份额/净资产规模变动详情')]")
                    if prev_element:
                        target_table = table
                        break
                except:
                    continue
            
            if target_table is None:
                # 如果没有找到特定标题，尝试找到包含特定列名的表格
                for table in tables:
                    if "期间申购" in table.text:
                        target_table = table
                        break
            
            if target_table is None:
                logger.error("未能找到基金规模变动表格")
                return None
            
            # 提取表格数据
            rows = []
            row_elements = target_table.find_elements(By.TAG_NAME, "tr")
            logger.debug(f"找到 {len(row_elements)} 行数据")
            
            # 提取表头
            headers = []
            header_cells = row_elements[0].find_elements(By.TAG_NAME, "th")
            for th in header_cells:
                headers.append(th.text.strip())
            
            logger.info(f"表头: {headers}")
            
            # 提取数据行
            for i, row_element in enumerate(row_elements[1:], 1):
                cell_elements = row_element.find_elements(By.TAG_NAME, "td")
                if cell_elements:
                    row_data = []
                    for cell in cell_elements:
                        cell_text = cell.text.strip()
                        row_data.append(cell_text)
                    rows.append(row_data)
                    logger.debug(f"行 {i}: {row_data}")
            
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
            
            # 处理期末净资产列，将文本格式转换为数字格式
            if '期末净资产（亿元）' in df.columns:
                logger.info("正在处理期末净资产列，将文本格式转换为数字格式...")
                df['期末净资产（亿元）'] = df['期末净资产（亿元）'].apply(clean_asset_value)
                logger.info("期末净资产列处理完成")
            
            # 保存到CSV
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"表格数据已保存到 {output_path}")
            
            return df
        
        except Exception as e:
            logger.error(f"查找表格元素时发生错误: {str(e)}", exc_info=True)
            return None
    
    except Exception as e:
        logger.error(f"发生错误: {str(e)}", exc_info=True)
        return None
    
    finally:
        if driver:
            driver.quit()
            logger.debug("浏览器已关闭")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="从东方财富网提取基金规模变动表格数据")
    parser.add_argument("code", help="基金代码，例如：510300")
    parser.add_argument("--output", help="输出CSV文件名（默认使用基金代码命名）")
    parser.add_argument("--wait", type=int, default=10, help="等待页面加载的时间(秒)")
    parser.add_argument("--log", help="日志文件路径（默认自动生成）")
    parser.add_argument("--dir", default="output", help="输出文件夹路径（默认为'output'）")
    
    args = parser.parse_args()
    
    # 构建URL
    url = f"https://fundf10.eastmoney.com/gmbd_{args.code}.html"
    
    # 提取数据
    df = extract_fund_scale_table(url, args.output, args.wait, args.log, args.dir)
    
    if df is not None:
        print(f"成功提取基金 {args.code} 的规模变动数据，共 {len(df)} 条记录")
        print(df.head())
    else:
        print(f"提取基金 {args.code} 的规模变动数据失败")