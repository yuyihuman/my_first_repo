#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据结构检查脚本
专门用于检查 all_stocks_data 文件夹的文件结构和CSV文件字段内容
"""

import os
import pandas as pd
import logging
from datetime import datetime
import json

# 配置日志
script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
    
log_filename = os.path.join(logs_dir, "stock_data_structure.log")

# 如果日志文件存在，先删除它以确保每次运行都重新创建
if os.path.exists(log_filename):
    os.remove(log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8', mode='w'),  # 使用 'w' 模式确保重写
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

def analyze_detailed_csv_fields(file_path, file_name):
    """
    详细分析CSV文件的字段结构和内容
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"    CSV文件结构: {df.shape[0]} 行 x {df.shape[1]} 列")
        
        # 字段类型说明
        field_descriptions = {
            'datetime': '时间戳 - 数据记录的时间点',
            'open': '开盘价 - 该时间段的开盘价格',
            'high': '最高价 - 该时间段的最高价格',
            'low': '最低价 - 该时间段的最低价格',
            'close': '收盘价 - 该时间段的收盘价格',
            'volume': '成交量 - 该时间段的成交股数',
            'amount': '成交额 - 该时间段的成交金额',
            'amplitude': '振幅 - 该时间段的价格振幅百分比',
            'change': '涨跌额 - 相对于前一时间段的价格变化',
            'pct_chg': '涨跌幅 - 相对于前一时间段的价格变化百分比',
            'turnover': '换手率 - 成交量占流通股本的比例'
        }
        
        logger.info(f"    字段详细分析:")
        logger.info(f"    {'字段名':<15} {'数据类型':<12} {'非空值':<8} {'字段说明'}")
        logger.info(f"    {'-'*80}")
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null_count = df[col].count()
            description = field_descriptions.get(col.lower(), '未知字段')
            logger.info(f"    {col:<15} {dtype:<12} {non_null_count:<8} {description}")
        
        # 数据范围分析
        if not df.empty:
            logger.info(f"\n    数据时间范围:")
            if 'datetime' in df.columns:
                first_time = df['datetime'].iloc[0]
                last_time = df['datetime'].iloc[-1]
                logger.info(f"      开始时间: {first_time}")
                logger.info(f"      结束时间: {last_time}")
                logger.info(f"      数据跨度: {df.shape[0]} 个时间点")
            
            # 价格数据统计
            price_columns = ['open', 'high', 'low', 'close']
            existing_price_cols = [col for col in price_columns if col in df.columns]
            
            if existing_price_cols:
                logger.info(f"\n    价格数据统计:")
                for col in existing_price_cols:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        min_val = df[col].min()
                        max_val = df[col].max()
                        mean_val = df[col].mean()
                        logger.info(f"      {col}: 最小值={min_val:.2f}, 最大值={max_val:.2f}, 平均值={mean_val:.2f}")
            
            # 成交量统计
            if 'volume' in df.columns and pd.api.types.is_numeric_dtype(df['volume']):
                vol_min = df['volume'].min()
                vol_max = df['volume'].max()
                vol_mean = df['volume'].mean()
                logger.info(f"\n    成交量统计:")
                logger.info(f"      最小成交量: {vol_min:,.0f}")
                logger.info(f"      最大成交量: {vol_max:,.0f}")
                logger.info(f"      平均成交量: {vol_mean:,.0f}")
        
        # 显示前3行示例数据
        logger.info(f"\n    前3行示例数据:")
        for i, row in df.head(3).iterrows():
            logger.info(f"      第{i+1}行: {dict(row)}")
            
    except Exception as e:
        logger.error(f"    读取CSV文件失败: {e}")

def analyze_sample_stock_data(all_stocks_path, sample_stocks=["000001", "000002", "000004"]):
    """
    分析多个样本股票的数据结构
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"分析样本股票数据结构")
    logger.info(f"{'='*60}")
    
    for sample_stock in sample_stocks:
        stock_dir = os.path.join(all_stocks_path, f"stock_{sample_stock}_data")
        
        if not os.path.exists(stock_dir):
            logger.warning(f"样本股票目录不存在: {stock_dir}")
            continue
            
        logger.info(f"\n--- 股票 {sample_stock} 数据分析 ---")
        
        # 检查目录中的文件
        files = os.listdir(stock_dir)
        csv_files = [f for f in files if f.endswith('.csv')]
        other_files = [f for f in files if not f.endswith('.csv')]
        
        logger.info(f"文件总数: {len(files)}")
        logger.info(f"CSV数据文件: {len(csv_files)} 个")
        logger.info(f"其他文件: {len(other_files)} 个")
        
        # 分析每个CSV文件
        for file in sorted(csv_files):
            file_path = os.path.join(stock_dir, file)
            file_size = os.path.getsize(file_path)
            
            # 确定文件类型
            if '1minute' in file:
                file_type = "1分钟K线数据"
            elif '5minute' in file:
                file_type = "5分钟K线数据"
            elif '30minute' in file:
                file_type = "30分钟K线数据"
            elif 'daily' in file:
                file_type = "日K线数据"
            else:
                file_type = "未知类型数据"
            
            logger.info(f"\n  文件: {file}")
            logger.info(f"    类型: {file_type}")
            logger.info(f"    大小: {file_size:,} 字节")
            
            analyze_detailed_csv_fields(file_path, file)
        
        # 分析其他文件
        if other_files:
            logger.info(f"\n  其他文件:")
            for file in other_files:
                file_path = os.path.join(stock_dir, file)
                file_size = os.path.getsize(file_path)
                logger.info(f"    {file} (大小: {file_size:,} 字节)")
                
                # 如果是文本文件，显示内容
                if file.endswith('.txt'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            logger.info(f"      内容预览: {content[:200]}...")
                    except Exception as e:
                        logger.error(f"      读取文件失败: {e}")
        
        logger.info(f"--- 股票 {sample_stock} 分析完成 ---")

def analyze_all_stocks_summary(all_stocks_path):
    """
    分析all_stocks_data目录的整体统计信息
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"all_stocks_data 目录整体统计")
    logger.info(f"{'='*60}")
    
    if not os.path.exists(all_stocks_path):
        logger.error(f"目录不存在: {all_stocks_path}")
        return
    
    # 统计股票数量
    stock_dirs = [d for d in os.listdir(all_stocks_path) 
                  if os.path.isdir(os.path.join(all_stocks_path, d)) and d.startswith('stock_')]
    
    logger.info(f"总股票数量: {len(stock_dirs)}")
    
    # 统计文件类型
    file_type_stats = {
        '1minute_history.csv': 0,
        '5minute_history.csv': 0,
        '30minute_history.csv': 0,
        'daily_history.csv': 0,
        'data_summary.txt': 0,
        'other': 0
    }
    
    total_size = 0
    
    for stock_dir in stock_dirs[:10]:  # 只检查前10个作为统计样本
        stock_path = os.path.join(all_stocks_path, stock_dir)
        if os.path.exists(stock_path):
            files = os.listdir(stock_path)
            for file in files:
                file_path = os.path.join(stock_path, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    
                    # 统计文件类型
                    if file.endswith('1minute_history.csv'):
                        file_type_stats['1minute_history.csv'] += 1
                    elif file.endswith('5minute_history.csv'):
                        file_type_stats['5minute_history.csv'] += 1
                    elif file.endswith('30minute_history.csv'):
                        file_type_stats['30minute_history.csv'] += 1
                    elif file.endswith('daily_history.csv'):
                        file_type_stats['daily_history.csv'] += 1
                    elif file == 'data_summary.txt':
                        file_type_stats['data_summary.txt'] += 1
                    else:
                        file_type_stats['other'] += 1
    
    logger.info(f"\n文件类型统计 (基于前10个股票样本):")
    for file_type, count in file_type_stats.items():
        if count > 0:
            logger.info(f"  {file_type}: {count} 个")
    
    logger.info(f"\n数据规模估算:")
    logger.info(f"  样本总大小: {total_size:,} 字节 ({total_size/1024/1024:.2f} MB)")
    if len(stock_dirs) > 10:
        estimated_total = total_size * len(stock_dirs) / 10
        logger.info(f"  预估总大小: {estimated_total:,} 字节 ({estimated_total/1024/1024:.2f} MB)")

def main():
    """
    主函数 - 专门检查all_stocks_data目录结构和字段内容
    """
    logger.info("开始股票数据结构检查")
    logger.info(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定义路径
    base_path = r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info"
    all_stocks_path = os.path.join(base_path, "all_stocks_data")
    
    # 检查 all_stocks_data 目录结构
    check_directory_structure(all_stocks_path)
    
    # 分析目录整体统计
    analyze_all_stocks_summary(all_stocks_path)
    
    # 分析样本股票数据的详细字段结构
    analyze_sample_stock_data(all_stocks_path)
    
    logger.info(f"\n{'='*60}")
    logger.info("all_stocks_data 数据结构检查完成")
    logger.info(f"详细日志已保存到: {log_filename}")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()