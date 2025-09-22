# -*- coding: utf-8 -*-
"""
Revenue增长分析脚本
分析从2010年到现在营业收入增长超过10倍的股票

作者: AI Assistant
创建时间: 2025-09-18
"""

import pandas as pd
import os
import logging
import time
from datetime import datetime
import json
import numpy as np
import multiprocessing as mp
from multiprocessing import Pool, Manager
from functools import partial

# 全局变量，用于存储每个进程的日志记录器
process_loggers = {}

# 创建一个进程特定的日志记录函数
def safe_log(msg, level="info"):
    """进程特定的日志记录函数，主进程使用标准日志，子进程使用独立日志文件"""
    # 获取当前进程ID
    process_id = mp.current_process().name
    
    # 如果是主进程，使用标准的logging模块
    if process_id == "MainProcess":
        if level == "info":
            logging.info(msg)
        elif level == "warning":
            logging.warning(msg)
        elif level == "error":
            logging.error(msg)
        elif level == "debug":
            logging.debug(msg)
        elif level == "critical":
            logging.critical(msg)
    else:
        # 子进程使用独立的日志记录器
        if process_id not in process_loggers:
            process_loggers[process_id] = setup_process_logging(process_id)
        
        # 使用进程特定的日志记录器记录日志
        logger = process_loggers[process_id]
        if level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "debug":
            logger.debug(msg)
        elif level == "critical":
            logger.critical(msg)

def clean_old_logs(logs_dir="revenue_log", keep_days=0):
    """清理旧的日志文件
    
    Args:
        logs_dir: 日志文件夹路径
        keep_days: 保留最近几天的日志，默认0天（清理所有旧日志）
    """
    if not os.path.exists(logs_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 60 * 60)  # 转换为秒
    
    deleted_count = 0
    
    # 清理主日志文件夹中的旧日志
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
    
    # 清理进程日志文件夹中的旧日志
    process_logs_dir = os.path.join(logs_dir, "process_logs")
    if os.path.exists(process_logs_dir):
        for filename in os.listdir(process_logs_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(process_logs_dir, filename)
                file_time = os.path.getmtime(file_path)
                
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"删除进程日志文件 {filename} 失败: {e}")
    
    if deleted_count > 0:
        print(f"已清理 {deleted_count} 个旧日志文件")

def setup_process_logging(process_id):
    """
    为特定进程设置日志配置
    
    Args:
        process_id: 进程ID或名称
    
    Returns:
        logger: 配置好的日志记录器
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建进程日志文件夹（在脚本所在目录下的revenue_log文件夹中）
    logs_dir = os.path.join(script_dir, "revenue_log")
    process_logs_dir = os.path.join(logs_dir, "process_logs")
    if not os.path.exists(process_logs_dir):
        os.makedirs(process_logs_dir)
    
    # 生成带时间戳和进程ID的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(process_logs_dir, f"revenue_analysis_{process_id}_{timestamp}.log")
    
    # 创建日志记录器
    logger = logging.getLogger(f"revenue_process_{process_id}")
    logger.setLevel(logging.INFO)
    
    # 防止重复添加处理器
    if not logger.handlers:
        # 添加文件处理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 设置日志配置
def setup_logging():
    """设置主进程日志配置"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建revenue_log文件夹
    logs_dir = os.path.join(script_dir, "revenue_log")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 清理旧日志文件
    clean_old_logs(logs_dir)
    
    # 创建进程日志文件夹
    process_logs_dir = os.path.join(logs_dir, "process_logs")
    if not os.path.exists(process_logs_dir):
        os.makedirs(process_logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"revenue_growth_analysis_main_{timestamp}.log")
    
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

def check_stock_data_completeness(stock_code, start_year=2020, min_years=4):
    """
    检查股票数据的完整性
    
    Args:
        stock_code: 股票代码（6位数字）
        start_year: 起始年份
        min_years: 最少需要的年份数量
    
    Returns:
        dict: 数据完整性检查结果
    """
    try:
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 构建股票数据文件路径
        stock_folder = f"{stock_code}.SZ"  # 先尝试深圳
        income_file_path = os.path.join(script_dir, "financial_data", stock_folder, "Income.csv")
        
        if not os.path.exists(income_file_path):
            # 如果深圳不存在，尝试上海
            stock_folder = f"{stock_code}.SH"
            income_file_path = os.path.join(script_dir, "financial_data", stock_folder, "Income.csv")
        
        if not os.path.exists(income_file_path):
            return {
                'is_complete': False,
                'error': f'股票{stock_code}的Income.csv文件不存在',
                'missing_years': [],
                'available_years': [],
                'data_quality': 'no_file'
            }
        
        # 读取CSV文件
        df = pd.read_csv(income_file_path)
        
        if df.empty:
            return {
                'is_complete': False,
                'error': f'股票{stock_code}的Income.csv文件为空',
                'missing_years': [],
                'available_years': [],
                'data_quality': 'empty_file'
            }
        
        # 检查必要的列是否存在
        required_columns = {
            'revenue': ['revenue_inc', 'revenue', 'operating_revenue', '营业收入', '营业总收入'],
            'net_profit': ['net_profit_incl_min_int_inc', 'net_profit', 'net_profit_excl_min_int_inc', '净利润', '归属于母公司所有者的净利润'],
            'date': ['m_timetag', 'date', 'report_date', '报告期']
        }
        
        missing_columns = []
        found_columns = {}
        
        for col_type, possible_names in required_columns.items():
            found = False
            for col_name in possible_names:
                if col_name in df.columns:
                    found_columns[col_type] = col_name
                    found = True
                    break
            if not found:
                missing_columns.append(col_type)
        
        if missing_columns:
            return {
                'is_complete': False,
                'error': f'股票{stock_code}缺少必要的列: {missing_columns}',
                'missing_years': [],
                'available_years': [],
                'data_quality': 'missing_columns'
            }
        
        # 检查年度数据的完整性
        date_col = found_columns['date']
        revenue_col = found_columns['revenue']
        net_profit_col = found_columns['net_profit']
        
        # 处理日期格式
        df[date_col] = df[date_col].astype(str)
        
        # 筛选年度数据
        if date_col == 'm_timetag':
            # m_timetag格式为YYYYMMDD，年度数据以1231结尾
            annual_df = df[df[date_col].str.endswith('1231')].copy()
        else:
            # 其他格式以-12-31结尾
            annual_df = df[df[date_col].str.endswith('-12-31')].copy()
        
        if annual_df.empty:
            return {
                'is_complete': False,
                'error': f'股票{stock_code}没有年度财务数据',
                'missing_years': [],
                'available_years': [],
                'data_quality': 'no_annual_data'
            }
        
        # 提取有效的年份数据
        available_years = []
        current_year = datetime.now().year
        
        for _, row in annual_df.iterrows():
            year = int(row[date_col][:4])
            
            # 只检查指定年份范围内的数据
            if year < start_year or year >= current_year:
                continue
            
            # 检查营业收入和净利润数据是否有效
            revenue = row.get(revenue_col, None)
            net_profit = row.get(net_profit_col, None)
            
            revenue_valid = revenue is not None and pd.notna(revenue) and revenue != '' and float(revenue) > 0
            net_profit_valid = net_profit is not None and pd.notna(net_profit) and net_profit != ''
            
            if revenue_valid and net_profit_valid:
                available_years.append(year)
        
        # 检查年份连续性和数量
        available_years = sorted(available_years)
        expected_years = list(range(start_year, current_year))
        missing_years = [year for year in expected_years if year not in available_years]
        
        # 判断数据是否完整
        has_enough_years = len(available_years) >= min_years
        has_recent_data = available_years and max(available_years) >= current_year - 2  # 最近2年内有数据
        is_continuous = len(available_years) > 1 and (max(available_years) - min(available_years) + 1) == len(available_years)
        
        data_quality = 'good'
        if not has_enough_years:
            data_quality = 'insufficient_years'
        elif not has_recent_data:
            data_quality = 'outdated'
        elif not is_continuous:
            data_quality = 'discontinuous'
        
        # 根据min_years调整缺失年份的容忍度
        # 如果要求5年数据，则不允许缺失任何年份；如果要求4年数据，允许缺失1年
        max_missing_years = 0 if min_years >= 5 else 1
        is_complete = has_enough_years and has_recent_data and len(missing_years) <= max_missing_years
        
        return {
            'is_complete': is_complete,
            'available_years': available_years,
            'missing_years': missing_years,
            'data_quality': data_quality,
            'has_enough_years': has_enough_years,
            'has_recent_data': has_recent_data,
            'is_continuous': is_continuous,
            'years_count': len(available_years)
        }
        
    except Exception as e:
        return {
            'is_complete': False,
            'error': f'检查股票{stock_code}数据完整性时发生错误: {str(e)}',
            'missing_years': [],
            'available_years': [],
            'data_quality': 'check_error'
        }

def check_stock_data_completeness_wrapper(args):
    """多进程包装函数"""
    stock_code, start_year, min_years = args
    return stock_code, check_stock_data_completeness(stock_code, start_year, min_years)

def get_stock_list(filter_incomplete_data=True, start_year=2020, min_years=4, use_multiprocessing=True, num_processes=None):
    """
    从本地financial_data文件夹获取股票列表，可选择过滤数据不全的股票
    
    Args:
        filter_incomplete_data: 是否过滤数据不全的股票
        start_year: 数据完整性检查的起始年份
        min_years: 最少需要的年份数量
        use_multiprocessing: 是否使用多进程加速数据完整性检查
        num_processes: 进程数量，默认为CPU核心数
    
    Returns:
        DataFrame: 股票列表，包含数据完整性信息
    """
    safe_log("正在从本地获取股票列表...")
    
    try:
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        financial_data_path = os.path.join(script_dir, "financial_data")
        
        if not os.path.exists(financial_data_path):
            safe_log(f"财务数据目录不存在: {financial_data_path}", "error")
            return None
        
        # 获取所有股票目录
        stock_dirs = [d for d in os.listdir(financial_data_path) 
                     if os.path.isdir(os.path.join(financial_data_path, d))]
        
        safe_log(f"发现 {len(stock_dirs)} 个股票数据目录")
        
        # 创建股票列表，包含数据完整性检查
        stock_data = []
        complete_count = 0
        incomplete_count = 0
        total_stocks = len(stock_dirs)
        
        # 提取股票代码
        stock_codes = [stock_code.split('.')[0] for stock_code in stock_dirs]
        
        safe_log(f"开始数据完整性检查，总共需要检查 {total_stocks} 个股票...")
        start_time = time.time()
        
        if filter_incomplete_data:
            if use_multiprocessing and total_stocks > 100:  # 只有股票数量较多时才使用多进程
                # 使用多进程并行检查
                if num_processes is None:
                    num_processes = min(mp.cpu_count(), 8)  # 限制最大进程数为8
                
                safe_log(f"使用多进程并行检查数据完整性，进程数: {num_processes}")
                
                # 准备参数列表
                args_list = [(code, start_year, min_years) for code in stock_codes]
                
                # 使用多进程池
                with mp.Pool(processes=num_processes) as pool:
                    results = pool.map(check_stock_data_completeness_wrapper, args_list)
                
                # 处理结果
                for stock_code, completeness_result in results:
                    if completeness_result['is_complete']:
                        complete_count += 1
                        stock_data.append({
                            'code': stock_code,
                            'name': f'股票{stock_code}',
                            'data_quality': completeness_result['data_quality'],
                            'available_years': len(completeness_result['available_years']),
                            'missing_years': len(completeness_result['missing_years']),
                            'is_continuous': completeness_result.get('is_continuous', False)
                        })
                    else:
                        incomplete_count += 1
            else:
                # 使用单进程串行检查（带进度提示）
                safe_log("使用单进程串行检查数据完整性")
                
                for i, stock_code in enumerate(stock_codes):
                    # 每处理100个股票输出一次进度
                    if i % 100 == 0 and i > 0:
                        elapsed_time = time.time() - start_time
                        progress_pct = (i / total_stocks) * 100
                        estimated_total_time = elapsed_time / i * total_stocks
                        remaining_time = estimated_total_time - elapsed_time
                        safe_log(f"数据完整性检查进度: {i}/{total_stocks} ({progress_pct:.1f}%) - "
                                f"已用时: {elapsed_time:.1f}秒, 预计剩余: {remaining_time:.1f}秒")
                    
                    try:
                        completeness_result = check_stock_data_completeness(stock_code, start_year, min_years)
                        
                        if completeness_result['is_complete']:
                            complete_count += 1
                            stock_data.append({
                                'code': stock_code,
                                'name': f'股票{stock_code}',
                                'data_quality': completeness_result['data_quality'],
                                'available_years': len(completeness_result['available_years']),
                                'missing_years': len(completeness_result['missing_years']),
                                'is_continuous': completeness_result.get('is_continuous', False)
                            })
                        else:
                            incomplete_count += 1
                    except Exception as e:
                        incomplete_count += 1
                        if i % 500 == 0:  # 每500个股票汇总一次错误
                            safe_log(f"检查股票 {stock_code} 时发生错误: {str(e)}", "warning")
        else:
            # 不过滤，直接添加所有股票
            for stock_code in stock_codes:
                stock_data.append({
                    'code': stock_code,
                    'name': f'股票{stock_code}',
                    'data_quality': 'unknown',
                    'available_years': 0,
                    'missing_years': 0,
                    'is_continuous': False
                })
        
        # 输出最终进度
        total_time = time.time() - start_time
        safe_log(f"数据完整性检查完成! 总用时: {total_time:.1f}秒")
        
        stock_list = pd.DataFrame(stock_data)
        
        if filter_incomplete_data:
            safe_log(f"数据完整性过滤结果: 完整数据 {complete_count} 只, 不完整数据 {incomplete_count} 只")
            safe_log(f"过滤后获得 {len(stock_list)} 只数据完整的股票")
        else:
            safe_log(f"成功从本地获取 {len(stock_list)} 只股票（未过滤）")
        
        return stock_list
        
    except Exception as e:
        safe_log(f"获取本地股票列表失败: {e}", "error")
        return None

def get_stock_net_profit_data(stock_code, start_year=2010, max_retries=3):
    """
    从本地CSV文件读取股票的净利润数据
    
    Args:
        stock_code: 股票代码
        start_year: 起始年份
        max_retries: 最大重试次数
    
    Returns:
        dict: 包含净利润数据的字典
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建文件路径
    stock_folder = f"{stock_code}.SZ" if stock_code.startswith(('000', '002', '003', '300', '301')) else f"{stock_code}.SH"
    income_file_path = os.path.join(script_dir, "financial_data", stock_folder, "Income.csv")
    
    # 如果SZ文件不存在，尝试SH
    if not os.path.exists(income_file_path):
        stock_folder = f"{stock_code}.SH" if stock_code.startswith(('000', '002', '003', '300', '301')) else f"{stock_code}.SZ"
        income_file_path = os.path.join(script_dir, "financial_data", stock_folder, "Income.csv")
    
    if not os.path.exists(income_file_path):
        return {'error': f'股票{stock_code}的Income.csv文件不存在'}
    
    try:
        df = pd.read_csv(income_file_path)
        
        if df.empty:
            return {'error': f'股票{stock_code}的Income.csv文件为空'}
        
        # 检查是否有净利润列
        net_profit_columns = ['net_profit_incl_min_int_inc', 'net_profit', 'net_profit_excl_min_int_inc', '净利润', '归属于母公司所有者的净利润']
        net_profit_col = None
        for col in df.columns:
            if col in net_profit_columns:
                net_profit_col = col
                break
        
        if net_profit_col is None:
            return {'error': f'股票{stock_code}的Income.csv文件中未找到净利润列'}
        
        # 检查是否有日期列
        date_columns = ['m_timetag', 'date', 'report_date', '报告期']
        date_col = None
        for col in df.columns:
            if col in date_columns:
                date_col = col
                break
        
        if date_col is None:
            return {'error': f'股票{stock_code}的Income.csv文件中未找到日期列'}
        
        # 提取净利润数据，增加严格的数据验证
        net_profit_data = {}
        invalid_data_count = 0
        
        for _, row in df.iterrows():
            try:
                # 提取年份
                date_str = str(row[date_col])
                if len(date_str) >= 4:
                    year = int(date_str[:4])
                else:
                    invalid_data_count += 1
                    continue
                
                # 只处理指定年份范围的数据
                if year < start_year:
                    continue
                
                net_profit = row.get(net_profit_col, None)
                
                # 严格的数据验证
                if net_profit is None or pd.isna(net_profit) or net_profit == '':
                    invalid_data_count += 1
                    continue
                
                try:
                    net_profit_value = float(net_profit)
                    
                    # 检查数据是否异常（过大或过小）
                    if abs(net_profit_value) > 100000000000:  # 绝对值大于1000亿，可能是数据错误
                        safe_log(f"股票{stock_code}在{year}年的净利润异常: {net_profit_value}", "warning")
                        invalid_data_count += 1
                        continue
                    
                    # 只保留每年最新的数据（年报数据）
                    if year not in net_profit_data or len(date_str) == 8:  # 年报通常是8位日期
                        net_profit_data[year] = net_profit_value
                        
                except (ValueError, TypeError) as e:
                    safe_log(f"股票{stock_code}在{year}年的净利润数据格式错误: {net_profit}", "warning")
                    invalid_data_count += 1
                    continue
                    
            except (ValueError, TypeError):
                invalid_data_count += 1
                continue
        
        # 检查数据质量
        if not net_profit_data:
            return {'error': f'股票{stock_code}没有有效的净利润数据'}
        
        if invalid_data_count > len(net_profit_data):
            safe_log(f"股票{stock_code}净利润有大量无效数据: 有效{len(net_profit_data)}条, 无效{invalid_data_count}条", "warning")
        
        return {
            'success': True, 
            'data': net_profit_data,
            'invalid_count': invalid_data_count,
            'valid_count': len(net_profit_data)
        }
        
    except Exception as e:
        safe_log(f"读取股票 {stock_code} 本地净利润数据失败: {e}", "error")
        return {'error': f'读取股票{stock_code}净利润数据失败: {str(e)}'}

def get_stock_revenue_data(stock_code, start_year=2010, max_retries=3):
    """
    从本地CSV文件读取股票的营业收入数据
    
    Args:
        stock_code: 股票代码（6位数字）
        start_year: 开始年份
        max_retries: 最大重试次数（保留参数兼容性）
    
    Returns:
        dict: 包含营业收入数据的字典
    """
    try:
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 构建股票数据文件路径
        stock_folder = f"{stock_code}.SZ"  # 先尝试深圳
        income_file_path = os.path.join(script_dir, "financial_data", stock_folder, "Income.csv")
        
        if not os.path.exists(income_file_path):
            # 如果深圳不存在，尝试上海
            stock_folder = f"{stock_code}.SH"
            income_file_path = os.path.join(script_dir, "financial_data", stock_folder, "Income.csv")
        
        if not os.path.exists(income_file_path):
            return {'error': f'股票{stock_code}的Income.csv文件不存在'}
        
        # 读取CSV文件
        df = pd.read_csv(income_file_path)
        
        if df.empty:
            return {'error': f'股票{stock_code}的Income.csv文件为空'}
        
        # 检查是否有营业收入列
        revenue_columns = ['revenue_inc', 'revenue', 'operating_revenue', '营业收入', '营业总收入']
        revenue_col = None
        for col in revenue_columns:
            if col in df.columns:
                revenue_col = col
                break
        
        if revenue_col is None:
            return {'error': f'股票{stock_code}的Income.csv文件中未找到营业收入列'}
        
        # 检查日期列
        date_columns = ['m_timetag', 'date', 'report_date', '报告期']
        date_col = None
        for col in date_columns:
            if col in df.columns:
                date_col = col
                break
        
        if date_col is None:
            return {'error': f'股票{stock_code}的Income.csv文件中未找到日期列'}
        
        # 处理日期格式
        df[date_col] = df[date_col].astype(str)
        
        # 筛选指定年份之后的数据
        df_filtered = df[df[date_col].str[:4].astype(int) >= start_year].copy()
        
        # 只保留年度数据
        if date_col == 'm_timetag':
            # m_timetag格式为YYYYMMDD，年度数据以1231结尾
            annual_df = df_filtered[df_filtered[date_col].str.endswith('1231')].copy()
        else:
            # 其他格式以-12-31结尾
            annual_df = df_filtered[df_filtered[date_col].str.endswith('-12-31')].copy()
        
        if annual_df.empty:
            return {'error': f'股票{stock_code}没有年度财务数据'}
        
        # 提取营业收入数据，增加严格的数据验证
        revenue_data = {}
        invalid_data_count = 0
        
        for _, row in annual_df.iterrows():
            year = int(row[date_col][:4])
            revenue = row.get(revenue_col, None)
            
            # 严格的数据验证
            if revenue is None or pd.isna(revenue) or revenue == '' or revenue == 0:
                invalid_data_count += 1
                continue
            
            try:
                revenue_value = float(revenue)
                
                # 更严格的数据验证
                if revenue_value <= 0:
                    invalid_data_count += 1
                    continue
                
                # 检查数据是否异常（过大或过小）
                if revenue_value < 1000000:  # 小于100万，可能是数据错误
                    safe_log(f"股票{stock_code}在{year}年的营业收入过小: {revenue_value}", "warning")
                    invalid_data_count += 1
                    continue
                
                if revenue_value > 1000000000000:  # 大于1万亿，可能是数据错误
                    safe_log(f"股票{stock_code}在{year}年的营业收入过大: {revenue_value}", "warning")
                    invalid_data_count += 1
                    continue
                
                revenue_data[year] = revenue_value
                
            except (ValueError, TypeError) as e:
                safe_log(f"股票{stock_code}在{year}年的营业收入数据格式错误: {revenue}", "warning")
                invalid_data_count += 1
                continue
        
        # 检查数据质量
        if not revenue_data:
            return {'error': f'股票{stock_code}没有有效的营业收入数据'}
        
        if invalid_data_count > len(revenue_data):
            safe_log(f"股票{stock_code}有大量无效数据: 有效{len(revenue_data)}条, 无效{invalid_data_count}条", "warning")
        
        return {
            'success': True, 
            'data': revenue_data,
            'invalid_count': invalid_data_count,
            'valid_count': len(revenue_data)
        }
        
    except Exception as e:
        safe_log(f"读取股票 {stock_code} 本地营业收入数据失败: {e}", "error")
        return {'error': str(e)}

def calculate_net_profit_growth(stock_code, start_year=2010, max_retries=3):
    """
    计算股票的净利润增长倍数
    
    Args:
        stock_code: 股票代码
        start_year: 起始年份
        max_retries: 最大重试次数
    
    Returns:
        dict: 包含净利润增长信息的字典
    """
    try:
        # 获取净利润数据
        net_profit_result = get_stock_net_profit_data(stock_code, start_year, max_retries)
        
        if 'error' in net_profit_result:
            return {'error': net_profit_result['error']}
        
        net_profit_data = net_profit_result['data']
        
        if not net_profit_data:
            return {'error': f'股票{stock_code}没有有效的净利润数据'}
        
        # 获取起始年份和最新年份的净利润
        years = sorted(net_profit_data.keys())
        start_year_actual = years[0]
        latest_year = years[-1]
        
        start_net_profit = net_profit_data[start_year_actual]
        latest_net_profit = net_profit_data[latest_year]
        
        # 检查起始净利润是否为正数
        if start_net_profit <= 0:
            return {'error': f'股票{stock_code}起始年份({start_year_actual})净利润为负数或零，无法计算增长倍数'}
        
        # 计算增长倍数
        growth_multiple = latest_net_profit / start_net_profit
        
        return {
            'success': True,
            'stock_code': stock_code,
            'start_year': start_year_actual,
            'latest_year': latest_year,
            'start_net_profit': start_net_profit,
            'latest_net_profit': latest_net_profit,
            'growth_multiple': growth_multiple,
            'net_profit_data': net_profit_data
        }
        
    except Exception as e:
        safe_log(f"计算股票 {stock_code} 净利润增长失败: {e}", "error")
        return {'error': f'计算股票{stock_code}净利润增长失败: {str(e)}'}

def calculate_net_profit_cagr(stock_code, start_year=2020, max_retries=3):
    """
    检查股票的净利润是否每年增幅都超过20%
    
    Args:
        stock_code: 股票代码
        start_year: 起始年份
        max_retries: 最大重试次数
    
    Returns:
        dict: 包含净利润每年增长分析信息的字典
    """
    try:
        # 获取净利润数据
        net_profit_result = get_stock_net_profit_data(stock_code, start_year, max_retries)
        
        if 'error' in net_profit_result:
            return {'error': net_profit_result['error']}
        
        net_profit_data = net_profit_result['data']
        
        if not net_profit_data:
            return {'error': f'股票{stock_code}没有有效的净利润数据'}
        
        # 获取所有年份并排序
        years = sorted(net_profit_data.keys())
        
        if len(years) < 2:
            return {'error': f'股票{stock_code}数据年份不足，无法计算年增长率'}
        
        start_year_actual = years[0]
        latest_year = years[-1]
        
        # 检查每年的增长率
        yearly_growth_rates = []
        all_years_above_30 = True
        failed_year = None
        
        for i in range(1, len(years)):
            prev_year = years[i-1]
            curr_year = years[i]
            prev_profit = net_profit_data[prev_year]
            curr_profit = net_profit_data[curr_year]
            
            # 检查前一年净利润是否为正数
            if prev_profit <= 0:
                return {'error': f'股票{stock_code}在{prev_year}年净利润为负数或零，无法计算增长率'}
            
            # 计算年增长率: ((当年/前一年) - 1) * 100
            growth_rate = ((curr_profit / prev_profit) - 1) * 100
            yearly_growth_rates.append({
                'from_year': prev_year,
                'to_year': curr_year,
                'growth_rate': growth_rate,
                'prev_profit': prev_profit,
                'curr_profit': curr_profit
            })
            
            # 检查是否低于20%
            if growth_rate < 20:
                all_years_above_30 = False
                if failed_year is None:
                    failed_year = f"{prev_year}-{curr_year}"
        
        # 计算整体CAGR作为参考
        start_net_profit = net_profit_data[start_year_actual]
        latest_net_profit = net_profit_data[latest_year]
        years_span = latest_year - start_year_actual
        
        overall_cagr = 0
        if start_net_profit > 0 and latest_net_profit > 0 and years_span > 0:
            overall_cagr = (pow(latest_net_profit / start_net_profit, 1.0 / years_span) - 1) * 100
        
        return {
            'success': True,
            'stock_code': stock_code,
            'start_year': start_year_actual,
            'latest_year': latest_year,
            'start_net_profit': start_net_profit,
            'latest_net_profit': latest_net_profit,
            'years_span': years_span,
            'all_years_above_30': all_years_above_30,
            'failed_year': failed_year,
            'yearly_growth_rates': yearly_growth_rates,
            'overall_cagr': overall_cagr,
            'net_profit_data': net_profit_data
        }
        
    except Exception as e:
        safe_log(f"计算股票 {stock_code} 净利润每年增长失败: {e}", "error")
        return {'error': f'计算股票{stock_code}净利润每年增长失败: {str(e)}'}

def calculate_revenue_growth(revenue_data, start_year=2010):
    """
    计算营业收入增长倍数
    
    Args:
        revenue_data: 营业收入数据字典 {year: revenue}
        start_year: 起始年份
    
    Returns:
        dict: 包含增长分析结果
    """
    if not revenue_data:
        return {'error': '没有有效的营业收入数据'}
    
    # 获取可用年份并排序
    years = sorted(revenue_data.keys())
    
    # 找到起始年份的数据
    start_revenue = None
    start_year_actual = None
    
    # 寻找起始年份或之后最早的数据
    for year in years:
        if year >= start_year:
            start_revenue = revenue_data[year]
            start_year_actual = year
            break
    
    if start_revenue is None or start_revenue <= 0:
        return {'error': f'没有找到{start_year}年或之后的有效起始营业收入数据'}
    
    # 获取最新年份的数据
    latest_year = max(years)
    latest_revenue = revenue_data[latest_year]
    
    if latest_revenue <= 0:
        return {'error': '最新年份的营业收入数据无效'}
    
    # 计算增长倍数
    growth_multiple = latest_revenue / start_revenue
    
    return {
        'success': True,
        'start_year': start_year_actual,
        'start_revenue': start_revenue,
        'latest_year': latest_year,
        'latest_revenue': latest_revenue,
        'growth_multiple': growth_multiple,
        'years_span': latest_year - start_year_actual,
        'all_data': revenue_data
    }

def process_single_stock(stock_info, start_year=2010, min_growth_multiple=10):
    """
    处理单个股票的营业收入增长分析
    
    Args:
        stock_info: 包含股票代码和名称的元组 (stock_code, stock_name)
        start_year: 起始年份
        min_growth_multiple: 最小增长倍数
    
    Returns:
        dict: 处理结果，包含股票信息或错误信息
    """
    stock_code, stock_name = stock_info
    
    # 确保子进程创建自己的日志记录器
    process_id = mp.current_process().name
    safe_log(f"进程 {process_id} 开始处理股票: {stock_code} - {stock_name}")
    
    try:
        # 获取营业收入数据
        safe_log(f"进程 {process_id} 正在获取股票 {stock_code} 的营业收入数据...")
        revenue_result = get_stock_revenue_data(stock_code, start_year)
        
        if 'error' in revenue_result:
            safe_log(f"进程 {process_id} 获取股票 {stock_code} 营业收入数据失败: {revenue_result['error']}", "warning")
            return {
                'status': 'error',
                'code': stock_code,
                'name': stock_name,
                'error': revenue_result['error']
            }
        
        # 计算增长倍数
        safe_log(f"进程 {process_id} 正在计算股票 {stock_code} 的增长倍数...")
        growth_result = calculate_revenue_growth(revenue_result['data'], start_year)
        
        if 'error' in growth_result:
            safe_log(f"进程 {process_id} 计算股票 {stock_code} 增长倍数失败: {growth_result['error']}", "warning")
            return {
                'status': 'error',
                'code': stock_code,
                'name': stock_name,
                'error': growth_result['error']
            }
        
        growth_multiple = growth_result['growth_multiple']
        
        # 检查是否符合条件
        if growth_multiple >= min_growth_multiple:
            safe_log(f"进程 {process_id} 股票 {stock_code} 符合条件! 增长倍数: {growth_multiple:.2f}")
            return {
                'status': 'qualified',
                'code': stock_code,
                'name': stock_name,
                'start_year': growth_result['start_year'],
                'start_revenue': growth_result['start_revenue'],
                'latest_year': growth_result['latest_year'],
                'latest_revenue': growth_result['latest_revenue'],
                'growth_multiple': growth_multiple,
                'years_span': growth_result['years_span'],
                'revenue_data': growth_result['all_data']
            }
        else:
            safe_log(f"进程 {process_id} 股票 {stock_code} 不符合条件，增长倍数: {growth_multiple:.2f}")
            return {
                'status': 'not_qualified',
                'code': stock_code,
                'name': stock_name,
                'growth_multiple': growth_multiple
            }
            
    except Exception as e:
        safe_log(f"进程 {process_id} 处理股票 {stock_code} 时发生异常: {str(e)}", "error")
        return {
            'status': 'error',
            'code': stock_code,
            'name': stock_name,
            'error': str(e)
        }

def process_single_stock_with_profit(stock_info, start_year=2010, min_revenue_growth=10, min_profit_growth=10, min_revenue_threshold=100*100000000):
    """
    处理单个股票的营业收入和净利润增长分析
    
    Args:
        stock_info: 包含股票代码和名称的元组 (stock_code, stock_name)
        start_year: 起始年份
        min_revenue_growth: 最小营收增长倍数
        min_profit_growth: 最小净利润增长倍数
        min_revenue_threshold: 最小营收规模阈值（元）
    
    Returns:
        dict: 处理结果，包含股票信息或错误信息
    """
    stock_code, stock_name = stock_info
    
    # 确保子进程创建自己的日志记录器
    process_id = mp.current_process().name
    safe_log(f"进程 {process_id} 开始处理股票: {stock_code} - {stock_name}")
    
    try:
        # 获取营业收入数据
        safe_log(f"进程 {process_id} 正在获取股票 {stock_code} 的营业收入数据...")
        revenue_result = get_stock_revenue_data(stock_code, start_year)
        
        if 'error' in revenue_result:
            safe_log(f"进程 {process_id} 获取股票 {stock_code} 营业收入数据失败: {revenue_result['error']}", "warning")
            return {
                'status': 'error',
                'code': stock_code,
                'name': stock_name,
                'error': revenue_result['error']
            }
        
        # 计算营收增长倍数
        safe_log(f"进程 {process_id} 正在计算股票 {stock_code} 的营收增长倍数...")
        revenue_growth_result = calculate_revenue_growth(revenue_result['data'], start_year)
        
        if 'error' in revenue_growth_result:
            safe_log(f"进程 {process_id} 计算股票 {stock_code} 营收增长倍数失败: {revenue_growth_result['error']}", "warning")
            return {
                'status': 'error',
                'code': stock_code,
                'name': stock_name,
                'error': revenue_growth_result['error']
            }
        
        # 检查营收规模是否达到阈值
        latest_revenue = revenue_growth_result['latest_revenue']
        if latest_revenue < min_revenue_threshold:
            safe_log(f"进程 {process_id} 股票 {stock_code} 当前营收规模不足，营收: {latest_revenue:,.0f}元")
            return {
                'status': 'revenue_too_small',
                'code': stock_code,
                'name': stock_name,
                'latest_revenue': latest_revenue
            }
        
        revenue_growth_multiple = revenue_growth_result['growth_multiple']
        
        # 检查营收增长是否符合条件
        if revenue_growth_multiple < min_revenue_growth:
            safe_log(f"进程 {process_id} 股票 {stock_code} 营收增长不符合条件，增长倍数: {revenue_growth_multiple:.2f}")
            return {
                'status': 'revenue_growth_insufficient',
                'code': stock_code,
                'name': stock_name,
                'revenue_growth_multiple': revenue_growth_multiple
            }
        
        # 获取净利润数据
        safe_log(f"进程 {process_id} 正在获取股票 {stock_code} 的净利润数据...")
        profit_result = calculate_net_profit_growth(stock_code, start_year)
        
        if 'error' in profit_result:
            safe_log(f"进程 {process_id} 获取股票 {stock_code} 净利润数据失败: {profit_result['error']}", "warning")
            return {
                'status': 'error',
                'code': stock_code,
                'name': stock_name,
                'error': profit_result['error']
            }
        
        profit_growth_multiple = profit_result['growth_multiple']
        
        # 检查净利润增长是否符合条件
        if profit_growth_multiple >= min_profit_growth:
            safe_log(f"进程 {process_id} 股票 {stock_code} 符合所有条件! 营收增长: {revenue_growth_multiple:.2f}倍, 净利润增长: {profit_growth_multiple:.2f}倍")
            return {
                'status': 'qualified',
                'code': stock_code,
                'name': stock_name,
                'start_year': revenue_growth_result['start_year'],
                'start_revenue': revenue_growth_result['start_revenue'],
                'latest_year': revenue_growth_result['latest_year'],
                'latest_revenue': revenue_growth_result['latest_revenue'],
                'revenue_growth_multiple': revenue_growth_multiple,
                'start_net_profit': profit_result['start_net_profit'],
                'latest_net_profit': profit_result['latest_net_profit'],
                'profit_growth_multiple': profit_result['growth_multiple'],
                'years_span': revenue_growth_result['years_span'],
                'revenue_data': revenue_growth_result['all_data'],
                'profit_data': profit_result['net_profit_data']
            }
        else:
            safe_log(f"进程 {process_id} 股票 {stock_code} 净利润增长不符合条件，增长倍数: {profit_growth_multiple:.2f}")
            return {
                'status': 'profit_growth_insufficient',
                'code': stock_code,
                'name': stock_name,
                'revenue_growth_multiple': revenue_growth_multiple,
                'profit_growth_multiple': profit_growth_multiple
            }
            
    except Exception as e:
        safe_log(f"进程 {process_id} 处理股票 {stock_code} 时发生异常: {str(e)}", "error")
        return {
            'status': 'error',
            'code': stock_code,
            'name': stock_name,
            'error': str(e)
        }

def analyze_revenue_and_profit_growth(stock_list, start_year, min_revenue_growth, min_profit_growth, min_revenue_threshold, num_processes=20):
    """
    分析股票的营业收入和净利润增长（多进程版本）
    
    Args:
        stock_list: 股票列表DataFrame
        start_year: 起始年份
        min_revenue_growth: 最小营收增长倍数
        min_profit_growth: 最小净利润增长倍数
        min_revenue_threshold: 最小营收规模阈值
        num_processes: 进程数
    
    Returns:
        list: 符合条件的股票列表
    """
    safe_log(f"开始分析 {len(stock_list)} 只股票的营收和净利润增长（多进程版本）")
    safe_log(f"分析条件: 起始年份={start_year}, 营收增长倍数>={min_revenue_growth}, 净利润增长倍数>={min_profit_growth}, 营收规模>={min_revenue_threshold/100000000:.0f}亿")
    safe_log(f"使用进程数: {num_processes}")
    
    # 准备股票信息列表，修复列名
    stock_info_list = [(row['code'], row['name']) for _, row in stock_list.iterrows()]
    
    # 创建参数列表 - 修复参数格式
    args_list = [(stock_info, start_year, min_revenue_growth, min_profit_growth, min_revenue_threshold) 
                 for stock_info in stock_info_list]
    
    # 使用多进程处理
    with mp.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_single_stock_with_profit, args_list)
    
    # 统计结果
    qualified_stocks = []
    error_count = 0
    unqualified_count = 0
    
    for result in results:
        if result['status'] == 'qualified':
            qualified_stocks.append(result)
        elif result['status'] == 'error':
            error_count += 1
        else:
            unqualified_count += 1
    
    safe_log(f"分析完成: 符合条件 {len(qualified_stocks)} 只, 不符合条件 {unqualified_count} 只, 错误 {error_count} 只")
    
    return qualified_stocks

def save_results(qualified_stocks, start_year, min_growth_multiple):
    """保存分析结果"""
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 生成结果文件名（固定文件名，不包含时间戳）
    results_filename = os.path.join(script_dir, "revenue_growth_results.json")
    
    # 准备保存的数据
    results_data = {
        'analysis_info': {
            'start_year': start_year,
            'min_growth_multiple': min_growth_multiple,
            'analysis_date': datetime.now().isoformat(),
            'total_qualified_stocks': len(qualified_stocks)
        },
        'qualified_stocks': qualified_stocks
    }
    
    # 保存为JSON文件
    try:
        with open(results_filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        safe_log(f"分析结果已保存到: {results_filename}")
    except Exception as e:
        safe_log(f"保存结果文件失败: {e}", "error")

def get_display_width(text):
    """
    计算字符串的显示宽度
    中文字符宽度为2，英文字符宽度为1
    
    Args:
        text: 要计算宽度的字符串
    
    Returns:
        int: 字符串的显示宽度
    """
    width = 0
    for char in str(text):
        # 判断是否为中文字符（包括中文标点符号）
        if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f' or '\uff00' <= char <= '\uffef':
            width += 2
        else:
            width += 1
    return width

def format_aligned_text(text, target_width, align='left'):
    """
    格式化文本，使其在指定宽度内对齐
    
    Args:
        text: 要格式化的文本
        target_width: 目标显示宽度
        align: 对齐方式 ('left', 'right', 'center')
    
    Returns:
        str: 格式化后的文本
    """
    text_str = str(text)
    current_width = get_display_width(text_str)
    
    if current_width >= target_width:
        return text_str
    
    padding = target_width - current_width
    
    if align == 'left':
        return text_str + ' ' * padding
    elif align == 'right':
        return ' ' * padding + text_str
    elif align == 'center':
        left_padding = padding // 2
        right_padding = padding - left_padding
        return ' ' * left_padding + text_str + ' ' * right_padding
    else:
        return text_str + ' ' * padding

def print_summary(qualified_stocks, start_year, min_growth_multiple):
    """打印分析结果摘要"""
    
    safe_log("="*120)
    safe_log("营业收入增长分析结果摘要")
    safe_log("="*120)
    safe_log(f"分析条件: {start_year}年至今，增长倍数 >= {min_growth_multiple}倍")
    safe_log(f"符合条件的股票数量: {len(qualified_stocks)}只")
    
    # 过滤掉当前营收规模小于100亿的股票
    min_revenue_threshold = 100 * 100000000  # 100亿元，单位元
    large_revenue_stocks = [stock for stock in qualified_stocks 
                           if stock['latest_revenue'] >= min_revenue_threshold]
    
    safe_log(f"当前营收规模 >= 100亿的股票数量: {len(large_revenue_stocks)}只")
    safe_log("")
    
    if large_revenue_stocks:
        # 按增长倍数排序
        sorted_stocks = sorted(large_revenue_stocks, key=lambda x: x['growth_multiple'], reverse=True)
        
        safe_log("营收规模 >= 100亿的股票排名:")
        safe_log("-" * 120)
        
        # 定义列宽
        col_widths = {
            'rank': 6,      # 排名
            'code': 10,     # 股票代码  
            'name': 24,     # 股票名称
            'multiple': 12, # 增长倍数
            'span': 14,     # 时间跨度
            'start': 18,    # 起始收入
            'latest': 18    # 最新收入
        }
        
        # 打印表头
        header = (format_aligned_text("排名", col_widths['rank']) +
                 format_aligned_text("股票代码", col_widths['code']) +
                 format_aligned_text("股票名称", col_widths['name']) +
                 format_aligned_text("增长倍数", col_widths['multiple']) +
                 format_aligned_text("时间跨度", col_widths['span']) +
                 format_aligned_text("起始收入(元)", col_widths['start']) +
                 format_aligned_text("最新收入(元)", col_widths['latest']))
        safe_log(header)
        safe_log("-" * 120)
        
        # 打印数据行
        for i, stock in enumerate(sorted_stocks, 1):
            row = (format_aligned_text(str(i), col_widths['rank']) +
                   format_aligned_text(stock['code'], col_widths['code']) +
                   format_aligned_text(stock['name'], col_widths['name']) +
                   format_aligned_text(f"{stock['growth_multiple']:.2f}", col_widths['multiple']) +
                   format_aligned_text(f"{stock['start_year']}-{stock['latest_year']}", col_widths['span']) +
                   format_aligned_text(f"{stock['start_revenue']:,.0f}", col_widths['start']) +
                   format_aligned_text(f"{stock['latest_revenue']:,.0f}", col_widths['latest']))
            safe_log(row)
        
        safe_log("-" * 120)
        
        # 统计信息
        growth_multiples = [stock['growth_multiple'] for stock in large_revenue_stocks]
        safe_log(f"营收规模 >= 100亿股票的增长倍数统计:")
        safe_log(f"  最大增长倍数: {max(growth_multiples):.2f}倍")
        safe_log(f"  平均增长倍数: {np.mean(growth_multiples):.2f}倍")
        safe_log(f"  中位数增长倍数: {np.median(growth_multiples):.2f}倍")
        
        # 按增长倍数区间统计
        ranges = [(10, 20), (20, 50), (50, 100), (100, float('inf'))]
        for min_val, max_val in ranges:
            count = len([s for s in large_revenue_stocks if min_val <= s['growth_multiple'] < max_val])
            range_str = f"{min_val}-{max_val if max_val != float('inf') else '∞'}倍"
            safe_log(f"  {range_str}: {count}只")
    
    # 如果还需要显示所有符合条件的股票统计
    if qualified_stocks:
        safe_log("")
        safe_log("所有符合条件股票的统计信息:")
        growth_multiples_all = [stock['growth_multiple'] for stock in qualified_stocks]
        safe_log(f"  最大增长倍数: {max(growth_multiples_all):.2f}倍")
        safe_log(f"  平均增长倍数: {np.mean(growth_multiples_all):.2f}倍")
        safe_log(f"  中位数增长倍数: {np.median(growth_multiples_all):.2f}倍")
        
        # 按增长倍数区间统计
        ranges = [(10, 20), (20, 50), (50, 100), (100, float('inf'))]
        for min_val, max_val in ranges:
            count = len([s for s in qualified_stocks if min_val <= s['growth_multiple'] < max_val])
            range_str = f"{min_val}-{max_val if max_val != float('inf') else '∞'}倍"
            safe_log(f"  {range_str}: {count}只")
    
    safe_log("="*120)

def print_revenue_and_profit_summary(qualified_stocks, start_year, min_revenue_growth, min_profit_growth, min_revenue_threshold):
    """
    打印营收和净利润增长分析结果摘要
    
    Args:
        qualified_stocks: 符合条件的股票列表
        start_year: 起始年份
        min_revenue_growth: 最小营收增长倍数
        min_profit_growth: 最小净利润增长倍数
        min_revenue_threshold: 最小营收规模阈值
    """
    safe_log("="*140)
    safe_log("营业收入和净利润增长分析结果摘要")
    safe_log("="*140)
    safe_log(f"分析条件:")
    safe_log(f"  起始年份: {start_year}年")
    safe_log(f"  营收增长倍数 >= {min_revenue_growth}倍")
    safe_log(f"  净利润增长倍数 >= {min_profit_growth}倍")
    safe_log(f"  当前营收规模 >= {min_revenue_threshold/100000000:.0f}亿元")
    safe_log(f"符合所有条件的股票数量: {len(qualified_stocks)}只")
    safe_log("")
    
    if qualified_stocks:
        # 按净利润增长倍数排序
        sorted_stocks = sorted(qualified_stocks, key=lambda x: x['profit_growth_multiple'], reverse=True)
        
        safe_log("符合条件的股票排名（按净利润增长倍数排序）:")
        safe_log("-" * 140)
        
        # 定义列宽
        col_widths = {
            'rank': 6,          # 排名
            'code': 10,         # 股票代码  
            'name': 20,         # 股票名称
            'revenue_multiple': 12,  # 营收增长倍数
            'profit_multiple': 12,   # 净利润增长倍数
            'span': 12,         # 时间跨度
            'start_revenue': 16, # 起始营收
            'latest_revenue': 16, # 最新营收
            'start_profit': 16,  # 起始净利润
            'latest_profit': 16  # 最新净利润
        }
        
        # 打印表头
        header = (format_aligned_text("排名", col_widths['rank']) +
                 format_aligned_text("股票代码", col_widths['code']) +
                 format_aligned_text("股票名称", col_widths['name']) +
                 format_aligned_text("营收增长倍数", col_widths['revenue_multiple']) +
                 format_aligned_text("净利润增长倍数", col_widths['profit_multiple']) +
                 format_aligned_text("时间跨度", col_widths['span']) +
                 format_aligned_text("起始营收(元)", col_widths['start_revenue']) +
                 format_aligned_text("最新营收(元)", col_widths['latest_revenue']) +
                 format_aligned_text("起始净利润(元)", col_widths['start_profit']) +
                 format_aligned_text("最新净利润(元)", col_widths['latest_profit']))
        safe_log(header)
        safe_log("-" * 140)
        
        # 打印数据行
        for i, stock in enumerate(sorted_stocks, 1):
            row = (format_aligned_text(str(i), col_widths['rank']) +
                   format_aligned_text(stock['code'], col_widths['code']) +
                   format_aligned_text(stock['name'], col_widths['name']) +
                   format_aligned_text(f"{stock['revenue_growth_multiple']:.2f}", col_widths['revenue_multiple']) +
                   format_aligned_text(f"{stock['profit_growth_multiple']:.2f}", col_widths['profit_multiple']) +
                   format_aligned_text(f"{stock['start_year']}-{stock['latest_year']}", col_widths['span']) +
                   format_aligned_text(f"{stock['start_revenue']:,.0f}", col_widths['start_revenue']) +
                   format_aligned_text(f"{stock['latest_revenue']:,.0f}", col_widths['latest_revenue']) +
                   format_aligned_text(f"{stock['start_net_profit']:,.0f}", col_widths['start_profit']) +
                   format_aligned_text(f"{stock['latest_net_profit']:,.0f}", col_widths['latest_profit']))
            safe_log(row)
        
        safe_log("-" * 140)
        
        # 统计信息
        revenue_multiples = [stock['revenue_growth_multiple'] for stock in qualified_stocks]
        profit_multiples = [stock['profit_growth_multiple'] for stock in qualified_stocks]
        
        safe_log(f"营收增长倍数统计:")
        safe_log(f"  最大增长倍数: {max(revenue_multiples):.2f}倍")
        safe_log(f"  平均增长倍数: {np.mean(revenue_multiples):.2f}倍")
        safe_log(f"  中位数增长倍数: {np.median(revenue_multiples):.2f}倍")
        
        safe_log(f"净利润增长倍数统计:")
        safe_log(f"  最大增长倍数: {max(profit_multiples):.2f}倍")
        safe_log(f"  平均增长倍数: {np.mean(profit_multiples):.2f}倍")
        safe_log(f"  中位数增长倍数: {np.median(profit_multiples):.2f}倍")
        
        # 按净利润增长倍数区间统计
        safe_log(f"净利润增长倍数区间分布:")
        ranges = [(10, 20), (20, 50), (50, 100), (100, float('inf'))]
        for min_val, max_val in ranges:
            count = len([s for s in qualified_stocks if min_val <= s['profit_growth_multiple'] < max_val])
            range_str = f"{min_val}-{max_val if max_val != float('inf') else '∞'}倍"
            safe_log(f"  {range_str}: {count}只")
    
    safe_log("="*140)

def main_revenue_and_profit():
    """主函数 - 分析营收和净利润增长"""
    # 设置日志
    log_filename = setup_logging()
    
    safe_log("开始营业收入和净利润增长分析（多进程版本）")
    safe_log(f"日志文件: {log_filename}")
    
    # 分析参数
    start_year = 2010
    min_revenue_growth = 10  # 营收增长倍数
    min_profit_growth = 10   # 净利润增长倍数
    min_revenue_threshold = 100 * 100000000  # 100亿元
    num_processes = 20  # 使用20个进程
    
    # 获取系统CPU核心数
    cpu_count = mp.cpu_count()
    safe_log(f"系统CPU核心数: {cpu_count}")
    
    # 确保进程数不超过CPU核心数的2倍
    if num_processes > cpu_count * 2:
        num_processes = cpu_count * 2
        safe_log(f"进程数调整为 {num_processes}（不超过CPU核心数的2倍）", "warning")
    
    try:
        # 获取股票列表（带数据完整性过滤）
        safe_log("正在获取股票列表并进行数据完整性检查...")
        stock_list = get_stock_list(filter_incomplete_data=True, start_year=start_year)
        
        if stock_list is None or stock_list.empty:
            safe_log("无法获取股票列表，程序退出", "error")
            return
        
        # 输出数据完整性统计
        safe_log("=" * 60)
        safe_log("数据完整性检查结果")
        safe_log("=" * 60)
        safe_log(f"获得数据完整的股票: {len(stock_list)} 只")
        safe_log("=" * 60)
        safe_log(f"将分析 {len(stock_list)} 只数据完整的股票")
        
        # 分析营业收入和净利润增长（多进程版本）
        qualified_stocks = analyze_revenue_and_profit_growth(
            stock_list, 
            start_year, 
            min_revenue_growth, 
            min_profit_growth, 
            min_revenue_threshold, 
            num_processes
        )
        
        # 打印摘要
        print_revenue_and_profit_summary(
            qualified_stocks, 
            start_year, 
            min_revenue_growth, 
            min_profit_growth, 
            min_revenue_threshold
        )
        
        safe_log("营业收入和净利润增长分析完成!")
        
    except Exception as e:
        safe_log(f"程序执行出错: {e}", "error")
        raise

def main():
    """主函数"""
    # 设置日志
    log_filename = setup_logging()
    
    safe_log("开始营业收入增长分析（多进程版本）")
    safe_log(f"日志文件: {log_filename}")
    
    # 分析参数
    start_year = 2010
    min_growth_multiple = 10
    num_processes = 20  # 使用20个进程
    
    # 获取系统CPU核心数
    cpu_count = mp.cpu_count()
    safe_log(f"系统CPU核心数: {cpu_count}")
    
    # 确保进程数不超过CPU核心数的2倍
    if num_processes > cpu_count * 2:
        num_processes = cpu_count * 2
        safe_log(f"进程数调整为 {num_processes}（不超过CPU核心数的2倍）", "warning")
    
    try:
        # 获取股票列表（带数据完整性过滤）
        safe_log("正在获取股票列表并进行数据完整性检查...")
        stock_list = get_stock_list(filter_incomplete_data=True, start_year=start_year)
        
        if stock_list is None or stock_list.empty:
            safe_log("无法获取股票列表，程序退出", "error")
            return
        
        # 分析营业收入增长（多进程版本）
        qualified_stocks = analyze_revenue_growth(stock_list, start_year, min_growth_multiple, num_processes)
        
        # 保存结果
        save_results(qualified_stocks, start_year, min_growth_multiple)
        
        # 打印摘要
        print_summary(qualified_stocks, start_year, min_growth_multiple)
        
        safe_log("营业收入增长分析完成!")
        
    except Exception as e:
        safe_log(f"程序执行出错: {e}", "error")
        raise

def process_single_stock_net_profit_cagr(stock_info, start_year=2020, min_cagr=20):
    """
    处理单个股票的净利润CAGR分析（近5年每年增幅超过20%）
    
    Args:
        stock_info: 包含股票代码和名称的元组 (stock_code, stock_name)
        start_year: 起始年份（默认2020年，近5年）
        min_cagr: 最小年复合增长率（默认20%）
    
    Returns:
        dict: 处理结果，包含股票信息或错误信息
    """
    stock_code, stock_name = stock_info
    
    # 确保子进程创建自己的日志记录器
    process_id = mp.current_process().name
    safe_log(f"进程 {process_id} 开始处理股票: {stock_code} - {stock_name}")
    
    try:
        # 获取净利润CAGR数据
        safe_log(f"进程 {process_id} 正在计算股票 {stock_code} 的净利润CAGR...")
        cagr_result = calculate_net_profit_cagr(stock_code, start_year)
        
        if 'error' in cagr_result:
            safe_log(f"进程 {process_id} 计算股票 {stock_code} 净利润CAGR失败: {cagr_result['error']}", "warning")
            return {
                'status': 'error',
                'code': stock_code,
                'name': stock_name,
                'error': cagr_result['error']
            }
        
        # 检查是否每年增长率都超过阈值
        if cagr_result['all_years_above_30']:
            safe_log(f"进程 {process_id} 股票 {stock_code} 符合条件! 每年增长率都超过{min_cagr}%, 整体CAGR: {cagr_result['overall_cagr']:.2f}%")
            return {
                'status': 'qualified',
                'code': stock_code,
                'name': stock_name,
                'start_year': cagr_result['start_year'],
                'start_net_profit': cagr_result['start_net_profit'],
                'latest_year': cagr_result['latest_year'],
                'latest_net_profit': cagr_result['latest_net_profit'],
                'years_span': cagr_result['years_span'],
                'overall_cagr': cagr_result['overall_cagr'],
                'yearly_growth_rates': cagr_result['yearly_growth_rates'],
                'net_profit_data': cagr_result['net_profit_data']
            }
        else:
            safe_log(f"进程 {process_id} 股票 {stock_code} 不符合条件，有年份增长率低于{min_cagr}%")
            return {
                'status': 'not_qualified',
                'code': stock_code,
                'name': stock_name,
                'overall_cagr': cagr_result['overall_cagr'],
                'yearly_growth_rates': cagr_result['yearly_growth_rates']
            }
            
    except Exception as e:
        safe_log(f"进程 {process_id} 处理股票 {stock_code} 时发生错误: {e}", "error")
        return {
            'status': 'error',
            'code': stock_code,
            'name': stock_name,
            'error': str(e)
        }

def analyze_net_profit_cagr(stock_list, start_year=2020, min_cagr=20, num_processes=None):
    """
    分析股票净利润年复合增长率（多进程版本）
    
    Args:
        stock_list: 股票列表DataFrame
        start_year: 起始年份（默认2020年，近5年）
        min_cagr: 最小年复合增长率（默认20%）
        num_processes: 进程数量
    
    Returns:
        dict: 分析结果
    """
    safe_log(f"开始分析 {len(stock_list)} 只股票的净利润年复合增长率（多进程版本）")
    safe_log(f"分析条件: 起始年份={start_year}, 净利润年复合增长率>={min_cagr}%")
    
    if num_processes is None:
        num_processes = min(20, mp.cpu_count())
    
    safe_log(f"使用进程数: {num_processes}")
    
    # 准备参数列表
    args_list = [((row['code'], row['name']), start_year, min_cagr) for _, row in stock_list.iterrows()]
    
    # 使用多进程处理
    with Pool(processes=num_processes) as pool:
        results = pool.starmap(process_single_stock_net_profit_cagr, args_list)
    
    # 统计结果
    qualified_stocks = []
    error_count = 0
    unqualified_count = 0
    
    for result in results:
        if result['status'] == 'qualified':
            qualified_stocks.append(result)
        elif result['status'] == 'error':
            error_count += 1
        else:
            unqualified_count += 1
    
    safe_log(f"分析完成: 符合条件 {len(qualified_stocks)} 只, 不符合条件 {unqualified_count} 只, 错误 {error_count} 只")
    
    return {
        'qualified_stocks': qualified_stocks,
        'total_analyzed': len(results),
        'qualified_count': len(qualified_stocks),
        'unqualified_count': unqualified_count,
        'error_count': error_count
    }

def save_net_profit_cagr_results(qualified_stocks, start_year, min_cagr):
    """保存净利润CAGR分析结果"""
    if not qualified_stocks:
        safe_log("没有符合条件的股票，跳过保存")
        return None
    
    # 创建DataFrame
    results_data = []
    for stock in qualified_stocks:
        # 格式化每年增长率
        yearly_rates_str = ', '.join([f"{item['from_year']}-{item['to_year']}: {item['growth_rate']:.1f}%" for item in stock['yearly_growth_rates']])
        
        results_data.append({
            '股票代码': stock['code'],
            '股票名称': stock['name'],
            '起始年份': stock['start_year'],
            '最新年份': stock['latest_year'],
            '年份跨度': stock['years_span'],
            '起始净利润(万元)': round(stock['start_net_profit'] / 10000, 2),
            '最新净利润(万元)': round(stock['latest_net_profit'] / 10000, 2),
            '整体年复合增长率(%)': round(stock['overall_cagr'], 2),
            '每年增长率': yearly_rates_str
        })
    
    df = pd.DataFrame(results_data)
    
    # 按整体年复合增长率降序排列
    df = df.sort_values('整体年复合增长率(%)', ascending=False)
    
    # 生成文件名
    filename = f"net_profit_cagr_analysis_{start_year}_{min_cagr}pct.csv"
    
    # 保存到CSV文件
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    safe_log(f"分析结果已保存到文件: {filename}")
    
    return filename

def print_net_profit_cagr_summary(qualified_stocks):
    """打印净利润CAGR分析摘要"""
    if not qualified_stocks:
        safe_log("没有符合条件的股票")
        return
    
    # 提取CAGR数据
    cagr_values = [stock['overall_cagr'] for stock in qualified_stocks]
    
    # 计算统计数据
    max_cagr = max(cagr_values)
    min_cagr = min(cagr_values)
    avg_cagr = sum(cagr_values) / len(cagr_values)
    median_cagr = sorted(cagr_values)[len(cagr_values) // 2]
    
    safe_log("=" * 60)
    safe_log("净利润年复合增长率分析摘要（每年增长率都超过20%）")
    safe_log("=" * 60)
    safe_log(f"符合条件的股票总数: {len(qualified_stocks)}")
    safe_log(f"最高整体年复合增长率: {max_cagr:.2f}%")
    safe_log(f"最低整体年复合增长率: {min_cagr:.2f}%")
    safe_log(f"平均整体年复合增长率: {avg_cagr:.2f}%")
    safe_log(f"中位数整体年复合增长率: {median_cagr:.2f}%")
    
    # 按CAGR区间统计
    ranges = [
        (20, 50, "20%-50%"),
        (50, 100, "50%-100%"),
        (100, 200, "100%-200%"),
        (200, float('inf'), "200%以上")
    ]
    
    safe_log("\n整体年复合增长率区间分布:")
    for min_val, max_val, label in ranges:
        count = sum(1 for cagr in cagr_values if min_val <= cagr < max_val)
        safe_log(f"{label}: {count}只")
    
    # 显示前10名
    sorted_stocks = sorted(qualified_stocks, key=lambda x: x['overall_cagr'], reverse=True)
    safe_log(f"\n前10名股票:")
    for i, stock in enumerate(sorted_stocks[:10], 1):
        yearly_rates = ', '.join([f"{item['growth_rate']:.1f}%" for item in stock['yearly_growth_rates']])
        safe_log(f"{i:2d}. {stock['code']} {stock['name']} - 整体CAGR: {stock['overall_cagr']:.2f}% (每年: {yearly_rates})")
    
    # 输出所有选中股票代码列表
    safe_log("=" * 60)
    safe_log("所有符合条件的股票代码列表")
    safe_log("=" * 60)
    
    # 按CAGR从高到低排序
    all_stock_codes = [stock['code'] for stock in sorted_stocks]
    
    # 以列表形式输出所有股票代码
    safe_log(f"股票代码列表（共{len(all_stock_codes)}只）:")
    safe_log(str(all_stock_codes))
    
    # 同时以更易读的格式输出（每行10个代码）
    safe_log("\n股票代码列表（格式化显示）:")
    for i in range(0, len(all_stock_codes), 10):
        batch = all_stock_codes[i:i+10]
        safe_log(f"  {','.join(batch)}")
    
    safe_log("=" * 60)

def main_net_profit_cagr_analysis():
    """主函数：近5年净利润年复合增长率超过20%的股票分析"""
    try:
        # 设置日志
        log_filename = setup_logging()
        
        # 清理旧日志文件
        clean_old_logs()
        
        safe_log("开始近5年净利润年复合增长率分析...")
        safe_log(f"日志文件: {log_filename}")
        safe_log(f"系统CPU核心数: {mp.cpu_count()}")
        
        # 获取股票列表（带数据完整性过滤）
        safe_log("正在获取股票列表并进行数据完整性检查...")
        stock_list = get_stock_list(filter_incomplete_data=True, start_year=2020, min_years=5, 
                                   use_multiprocessing=True, num_processes=8)
        
        if stock_list is None or stock_list.empty:
            safe_log("获取股票列表失败或没有符合条件的股票", "error")
            return
        
        # 输出数据完整性统计
        safe_log("=" * 60)
        safe_log("数据完整性检查结果")
        safe_log("=" * 60)
        safe_log(f"获得数据完整的股票: {len(stock_list)} 只")
        safe_log("=" * 60)
        safe_log(f"将分析 {len(stock_list)} 只数据完整的股票")
        
        # 分析参数
        start_year = 2020  # 近5年
        min_cagr = 20      # 年复合增长率超过20%
        num_processes = min(20, mp.cpu_count())
        
        # 执行分析
        analysis_result = analyze_net_profit_cagr(
            stock_list, 
            start_year=start_year, 
            min_cagr=min_cagr, 
            num_processes=num_processes
        )
        
        qualified_stocks = analysis_result['qualified_stocks']
        
        # 保存结果
        filename = save_net_profit_cagr_results(qualified_stocks, start_year, min_cagr)
        
        # 打印摘要
        print_net_profit_cagr_summary(qualified_stocks)
        
        safe_log("近5年净利润年复合增长率分析完成")
        
    except Exception as e:
        safe_log(f"分析过程中发生错误: {e}", "error")
        raise

if __name__ == "__main__":
    # 多进程保护，确保在Windows上正常工作
    mp.freeze_support()
    # 调用新的近5年净利润年复合增长率分析函数
    main_net_profit_cagr_analysis()