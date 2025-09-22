#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务数据结构读取脚本
简单读取 financial_data 文件夹的结构和文件内容示例
"""

import os
import pandas as pd
import logging
from datetime import datetime

# 配置日志
script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

log_filename = os.path.join(logs_dir, "financial_structure_simple.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def read_financial_data_structure(financial_data_path):
    """读取财务数据文件夹结构"""
    logger.info(f"\n{'='*60}")
    logger.info(f"读取财务数据结构: {financial_data_path}")
    logger.info(f"{'='*60}")
    
    if not os.path.exists(financial_data_path):
        logger.error(f"目录不存在: {financial_data_path}")
        return
    
    # 获取所有股票目录
    stock_dirs = [d for d in os.listdir(financial_data_path) 
                 if os.path.isdir(os.path.join(financial_data_path, d))]
    
    logger.info(f"总股票数量: {len(stock_dirs)}")
    logger.info(f"前10个股票目录: {sorted(stock_dirs)[:10]}")
    
    # 统计文件类型
    file_types = {}
    
    # 分析前几个股票的文件结构
    sample_stocks = sorted(stock_dirs)[:5]  # 只看前5个作为示例
    
    for stock_code in sample_stocks:
        stock_dir = os.path.join(financial_data_path, stock_code)
        files = os.listdir(stock_dir)
        
        logger.info(f"\n股票 {stock_code} 的文件:")
        for file in files:
            file_path = os.path.join(stock_dir, file)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"  {file} ({file_size:,} 字节)")
                
                # 统计文件类型
                file_types[file] = file_types.get(file, 0) + 1
    
    # 显示文件类型统计
    logger.info(f"\n文件类型统计 (基于前{len(sample_stocks)}个股票):")
    for file_type, count in sorted(file_types.items()):
        logger.info(f"  {file_type}: {count} 个")
    
    # 分析一个示例文件的内容结构
    show_sample_file_content(financial_data_path, sample_stocks[0] if sample_stocks else None)

def show_sample_file_content(financial_data_path, sample_stock):
    """展示示例文件的内容结构"""
    if not sample_stock:
        logger.warning("没有找到样本股票")
        return
    
    logger.info(f"\n{'='*60}")
    logger.info(f"示例文件内容结构 (股票: {sample_stock})")
    logger.info(f"{'='*60}")
    
    stock_dir = os.path.join(financial_data_path, sample_stock)
    files = [f for f in os.listdir(stock_dir) if f.endswith('.csv')]
    
    # 财务文件类型说明
    file_descriptions = {
        'Balance.csv': '资产负债表',
        'Income.csv': '利润表', 
        'CashFlow.csv': '现金流量表',
        'Indicator.csv': '财务指标'
    }
    
    for file in files:
        file_path = os.path.join(stock_dir, file)
        file_desc = file_descriptions.get(file, '未知类型')
        
        logger.info(f"\n{file} ({file_desc}):")
        
        try:
            df = pd.read_csv(file_path)
            logger.info(f"  数据形状: {df.shape[0]} 行 x {df.shape[1]} 列")
            logger.info(f"  列数量: {len(df.columns)}")
            
            # 显示所有列名
            all_columns = list(df.columns)
            logger.info(f"  所有列名 ({len(all_columns)} 个):")
            
            # 每行显示5个列名，便于阅读
            for i in range(0, len(all_columns), 5):
                columns_batch = all_columns[i:i+5]
                logger.info(f"    {i+1:2d}-{min(i+5, len(all_columns)):2d}: {columns_batch}")
            
            # 显示前3行数据的概要
            if not df.empty:
                logger.info(f"  数据示例 (前3行):")
                for i, (idx, row) in enumerate(df.head(3).iterrows()):
                    # 只显示前5个字段的值
                    sample_data = {col: row[col] for col in df.columns[:5]}
                    logger.info(f"    行{i+1}: {sample_data} ...")
            
        except Exception as e:
            logger.error(f"  读取文件失败: {e}")

def main():
    """主函数"""
    logger.info("开始财务数据结构读取")
    logger.info(f"读取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 财务数据路径
    financial_data_path = r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info\financial_data"
    
    # 读取结构
    read_financial_data_structure(financial_data_path)
    
    logger.info(f"\n{'='*60}")
    logger.info("财务数据结构读取完成")
    logger.info(f"日志文件: {log_filename}")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()