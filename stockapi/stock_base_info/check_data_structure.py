#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据结构检查脚本
用于检查 all_stocks_data 和 financial_data 两个文件夹的文件结构和内容
"""

import os
import pandas as pd
import logging
from datetime import datetime
import json

# 配置日志
log_filename = "logs/data_structure_check.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_directory_structure(directory_path, max_depth=3):
    """
    检查目录结构
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"检查目录结构: {directory_path}")
    logger.info(f"{'='*60}")
    
    if not os.path.exists(directory_path):
        logger.error(f"目录不存在: {directory_path}")
        return
    
    # 统计信息
    total_dirs = 0
    total_files = 0
    file_extensions = {}
    
    for root, dirs, files in os.walk(directory_path):
        # 计算当前深度
        depth = root.replace(directory_path, '').count(os.sep)
        if depth >= max_depth:
            dirs[:] = []  # 不再深入子目录
            continue
            
        indent = '  ' * depth
        logger.info(f"{indent}{os.path.basename(root)}/")
        total_dirs += 1
        
        # 显示文件
        subindent = '  ' * (depth + 1)
        for file in files[:10]:  # 只显示前10个文件
            logger.info(f"{subindent}{file}")
            total_files += 1
            
            # 统计文件扩展名
            ext = os.path.splitext(file)[1].lower()
            file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        if len(files) > 10:
            logger.info(f"{subindent}... 还有 {len(files) - 10} 个文件")
            total_files += len(files) - 10
    
    logger.info(f"\n目录统计:")
    logger.info(f"  总目录数: {total_dirs}")
    logger.info(f"  总文件数: {total_files}")
    logger.info(f"  文件类型分布: {dict(sorted(file_extensions.items()))}")

def analyze_sample_stock_data(all_stocks_path, sample_stock="000001"):
    """
    分析样本股票的数据结构
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"分析样本股票数据: {sample_stock}")
    logger.info(f"{'='*60}")
    
    stock_dir = os.path.join(all_stocks_path, f"stock_{sample_stock}_data")
    
    if not os.path.exists(stock_dir):
        logger.error(f"样本股票目录不存在: {stock_dir}")
        return
    
    # 检查目录中的文件
    files = os.listdir(stock_dir)
    logger.info(f"股票 {sample_stock} 的文件列表:")
    for file in files:
        file_path = os.path.join(stock_dir, file)
        if os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"  {file} (大小: {file_size:,} 字节)")
            
            # 如果是CSV文件，分析其结构
            if file.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)
                    logger.info(f"    CSV结构: {df.shape[0]} 行 x {df.shape[1]} 列")
                    logger.info(f"    列名: {list(df.columns)}")
                    
                    # 显示前几行数据
                    logger.info(f"    前3行数据:")
                    for i, row in df.head(3).iterrows():
                        logger.info(f"      行{i}: {dict(row)}")
                        
                    # 数据类型
                    logger.info(f"    数据类型: {dict(df.dtypes)}")
                    
                    # 基本统计
                    if not df.empty:
                        logger.info(f"    数据范围: {df.index[0]} 到 {df.index[-1]}")
                        
                except Exception as e:
                    logger.error(f"    读取CSV文件失败: {e}")

def analyze_sample_financial_data(financial_path, sample_stock="000002.SZ"):
    """
    分析样本股票的财务数据结构
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"分析样本财务数据: {sample_stock}")
    logger.info(f"{'='*60}")
    
    stock_dir = os.path.join(financial_path, sample_stock)
    
    if not os.path.exists(stock_dir):
        logger.error(f"样本财务数据目录不存在: {stock_dir}")
        return
    
    # 检查目录中的文件
    files = os.listdir(stock_dir)
    logger.info(f"股票 {sample_stock} 的财务文件列表:")
    
    for file in files:
        file_path = os.path.join(stock_dir, file)
        if os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"  {file} (大小: {file_size:,} 字节)")
            
            # 如果是CSV文件，分析其结构
            if file.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)
                    logger.info(f"    CSV结构: {df.shape[0]} 行 x {df.shape[1]} 列")
                    logger.info(f"    列名: {list(df.columns)}")
                    
                    # 显示前几行数据
                    if not df.empty:
                        logger.info(f"    前3行数据:")
                        for i, row in df.head(3).iterrows():
                            logger.info(f"      行{i}: {dict(row)}")
                    
                    # 数据类型
                    logger.info(f"    数据类型: {dict(df.dtypes)}")
                    
                except Exception as e:
                    logger.error(f"    读取CSV文件失败: {e}")

def main():
    """
    主函数
    """
    logger.info("开始股票数据结构检查")
    logger.info(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定义路径
    base_path = r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info"
    all_stocks_path = os.path.join(base_path, "all_stocks_data")
    financial_path = os.path.join(base_path, "financial_data")
    
    # 检查 all_stocks_data 目录结构
    check_directory_structure(all_stocks_path)
    
    # 检查 financial_data 目录结构
    check_directory_structure(financial_path)
    
    # 分析样本股票数据
    analyze_sample_stock_data(all_stocks_path, "000001")
    
    # 分析样本财务数据
    analyze_sample_financial_data(financial_path, "000002.SZ")
    
    logger.info(f"\n{'='*60}")
    logger.info("数据结构检查完成")
    logger.info(f"详细日志已保存到: {log_filename}")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()