#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机构持仓数据分析器

使用 AKShare 的 stock_report_fund_hold 接口获取机构持仓数据，
进行数据整合、分析和报告生成。

集成了数据验证、性能监控、错误处理和缓存管理等功能。
"""

import os
import sys
import time
import logging
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 导入自定义模块
try:
    from data_validator import DataValidator, validate_and_clean_data
    from performance_monitor import PerformanceMonitor, monitor_performance
    from error_handler import ErrorHandler, RetryHandler, handle_errors, retry_on_failure
    from cache_manager import CacheManager, cache_result
except ImportError as e:
    print(f"警告: 无法导入增强模块 {e}，将使用基础功能")
    # 定义空的装饰器以保持兼容性
    def monitor_performance(func):
        return func
    def handle_errors(func):
        return func
    def retry_on_failure(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def cache_result(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# 导入配置
try:
    from config import get_config
    CONFIG = get_config()
except ImportError:
    # 如果没有配置文件，使用默认配置
    CONFIG = {
        'base_data_dir': 'institutional_holdings_data',
        'institution_types': ["信托持仓"],
        'max_retries': 3,
        'request_delay': 1,
        'retry_delay_base': 2,
        'top_holdings_count': 20,
        'log_level': 'INFO',
        'log_format': '%(asctime)s - %(levelname)s - %(message)s',
        'log_to_console': True,
        'file_encoding': 'utf-8-sig',
        'skip_existing_files': True
    }


class InstitutionalHoldingsAnalyzer:
    """
    机构持股数据分析器
    """
    
    def __init__(self, base_dir: str = None, config: Dict = None):
        """
        初始化分析器
        
        Args:
            base_dir: 数据存储基础目录，为None时使用配置文件中的设置
            config: 自定义配置字典，为None时使用全局配置
        """
        # 使用配置
        self.config = config or CONFIG
        
        # 设置目录
        self.base_dir = base_dir or self.config.get('base_data_dir', 'institutional_holdings_data')
        self.raw_data_dir = os.path.join(self.base_dir, "raw_data")
        self.processed_data_dir = os.path.join(self.base_dir, "processed_data")
        self.logs_dir = os.path.join(self.base_dir, "logs")
        self.analysis_dir = os.path.join(self.base_dir, "analysis")
        
        # 从配置获取机构类型列表
        self.institution_types = self.config.get('institution_types', [
            "信托持仓"
        ])
        
        # 其他配置参数
        self.max_retries = self.config.get('max_retries', 3)
        self.request_delay = self.config.get('request_delay', 1)
        self.retry_delay_base = self.config.get('retry_delay_base', 2)
        self.top_holdings_count = self.config.get('top_holdings_count', 20)
        self.skip_existing_files = self.config.get('skip_existing_files', True)
        
        # 创建目录结构
        self._create_directories()
        
        # 设置日志
        self._setup_logging()
        
        # 初始化增强功能模块
        try:
            self.data_validator = DataValidator()
            self.performance_monitor = PerformanceMonitor()
            self.error_handler = ErrorHandler()
            self.retry_handler = RetryHandler()
            self.cache_manager = CacheManager(
                cache_dir=os.path.join(self.base_dir, 'cache'),
                memory_cache_size=self.config.get('cache_memory_limit', 1000),
                default_ttl=self.config.get('cache_file_ttl', 3600)
            )
            self.logger.info("增强功能模块初始化成功")
        except Exception as e:
            self.logger.warning(f"增强功能模块初始化失败: {e}，将使用基础功能")
            self.data_validator = None
            self.performance_monitor = None
            self.error_handler = None
            self.retry_handler = None
            self.cache_manager = None
        
        self.logger.info("机构持股数据分析器初始化完成")
        self.logger.info(f"配置参数: 机构类型{len(self.institution_types)}种, 最大重试{self.max_retries}次, 请求延时{self.request_delay}秒")
    
    def _create_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.base_dir, self.raw_data_dir, self.processed_data_dir,
            self.logs_dir, self.analysis_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _setup_logging(self):
        """设置日志配置"""
        log_filename = f"holdings_analyzer_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(self.logs_dir, log_filename)
        
        # 从配置获取日志参数
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        log_format = self.config.get('log_format', '%(asctime)s - %(levelname)s - %(message)s')
        log_to_console = self.config.get('log_to_console', True)
        file_encoding = self.config.get('file_encoding', 'utf-8')
        
        # 配置处理器
        handlers = [logging.FileHandler(log_filepath, encoding=file_encoding)]
        if log_to_console:
            handlers.append(logging.StreamHandler())
        
        # 配置日志格式
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers,
            force=True  # 强制重新配置
        )
        
        self.logger = logging.getLogger(__name__)
    
    def generate_quarter_dates(self, start_year: int = 2025, end_year: Optional[int] = None) -> List[str]:
        """
        生成季度末日期列表
        
        Args:
            start_year: 开始年份
            end_year: 结束年份，默认为当前年份
            
        Returns:
            季度末日期列表，格式为YYYYMMDD
        """
        if end_year is None:
            end_year = datetime.now().year
        
        quarter_dates = []
        
        for year in range(start_year, end_year + 1):
            # 每年四个季度末
            quarters = [
                f"{year}0331",  # Q1
                f"{year}0630",  # Q2
                f"{year}0930",  # Q3
                f"{year}1231"   # Q4
            ]
            quarter_dates.extend(quarters)
        
        # 过滤掉未来的日期
        current_date = datetime.now().strftime('%Y%m%d')
        quarter_dates = [date for date in quarter_dates if date <= current_date]
        
        self.logger.info(f"生成了 {len(quarter_dates)} 个季度末日期")
        return quarter_dates
    
    @monitor_performance
    @handle_errors
    @retry_on_failure(max_retries=3)
    def fetch_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票基本信息，包括总股本和流通股本
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票信息字典，包含总股本、流通股等信息
        """
        # 检查缓存
        cache_key = f"stock_info_{stock_code}"
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                self.logger.info(f"从缓存获取股票 {stock_code} 信息")
                return cached_data
        
        try:
            # 添加延时避免请求过于频繁
            time.sleep(self.request_delay)
            
            # 使用akshare获取个股信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            
            if stock_info is not None and not stock_info.empty:
                # 转换为字典格式
                info_dict = dict(zip(stock_info['item'], stock_info['value']))
                
                # 安全的数值转换函数
                def safe_float_convert(value, default=0.0):
                    """安全地将值转换为浮点数"""
                    if value is None or value == '' or value == '-' or value == '--':
                        return default
                    try:
                        # 处理可能的字符串格式（如包含逗号的数字）
                        if isinstance(value, str):
                            # 移除逗号和其他非数字字符（保留小数点和负号）
                            cleaned_value = ''.join(c for c in value if c.isdigit() or c in '.-')
                            if not cleaned_value or cleaned_value in ['-', '.', '-.']:
                                return default
                            return float(cleaned_value)
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                # 提取关键信息
                result = {
                    'stock_code': stock_code,
                    'stock_name': str(info_dict.get('股票简称', '')),
                    'total_shares': safe_float_convert(info_dict.get('总股本')),
                    'circulating_shares': safe_float_convert(info_dict.get('流通股')),
                    'total_market_value': safe_float_convert(info_dict.get('总市值')),
                    'circulating_market_value': safe_float_convert(info_dict.get('流通市值')),
                    'industry': str(info_dict.get('行业', '')),
                    'listing_date': str(info_dict.get('上市时间', '')),
                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 缓存数据
                if self.cache_manager:
                    self.cache_manager.set(cache_key, result, ttl=72000)  # 20小时缓存
                
                self.logger.info(f"成功获取股票 {stock_code} 基本信息")
                return result
            else:
                self.logger.warning(f"获取股票 {stock_code} 信息为空")
                return None
                
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, f"fetch_stock_info_{stock_code}")
            
            self.logger.error(f"获取股票 {stock_code} 信息失败: {str(e)}")
            return None
    
    @monitor_performance
    @handle_errors
    @retry_on_failure(max_retries=3)
    def fetch_holdings_data(self, symbol: str, date: str, max_retries: int = None) -> Optional[pd.DataFrame]:
        """
        获取指定机构类型和日期的持股数据
        
        Args:
            symbol: 机构类型
            date: 日期（YYYYMMDD格式）
            max_retries: 最大重试次数，为None时使用配置中的值
            
        Returns:
            持股数据DataFrame，失败返回None
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        # 检查缓存
        cache_key = f"holdings_{symbol}_{date}"
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                self.logger.info(f"从缓存获取 {symbol} - {date} 数据")
                return cached_data
            
        for attempt in range(max_retries):
            try:
                # 添加延时避免请求过于频繁
                time.sleep(self.request_delay)
                
                data = ak.stock_report_fund_hold(symbol=symbol, date=date)
                
                if data is not None and not data.empty:
                    # 先进行列名映射和添加必需列
                    if '股票代码' in data.columns:
                        data['stock_code'] = data['股票代码']
                    if '股票简称' in data.columns:
                        data['stock_name'] = data['股票简称']
                    
                    # 添加元数据（必需列）
                    data['institution_type'] = symbol
                    data['report_date'] = date
                    data['fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 数据验证和清洗（在添加必需列之后）
                    if self.data_validator:
                        data = self.data_validator.validate_holdings_data(data)
                        # validate_holdings_data已经包含了clean_data的调用，不需要重复调用
                    
                    # 缓存数据
                    if self.cache_manager:
                        self.cache_manager.set(cache_key, data, ttl=72000)  # 20小时缓存
                    
                    self.logger.info(f"成功获取 {symbol} {date} 数据，共 {len(data)} 条记录")
                    return data
                else:
                    self.logger.warning(f"获取 {symbol} {date} 数据为空")
                    return pd.DataFrame()
                    
            except Exception as e:
                if self.error_handler:
                    self.error_handler.handle_error(e, f"fetch_holdings_data_{symbol}_{date}")
                
                self.logger.error(f"获取 {symbol} {date} 数据失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay_base ** attempt)  # 指数退避
                else:
                    self.logger.error(f"获取 {symbol} {date} 数据最终失败")
                    return None
        
        return None
    
    def save_raw_data(self, data: pd.DataFrame, symbol: str, date: str):
        """
        保存原始数据到文件
        
        Args:
            data: 数据DataFrame
            symbol: 机构类型
            date: 日期
        """
        if data is None or data.empty:
            return
        
        # 创建文件名
        safe_symbol = symbol.replace("持仓", "").replace("持股", "")
        filename = f"{safe_symbol}_{date}.csv"
        filepath = os.path.join(self.raw_data_dir, filename)
        
        # 保存数据
        file_encoding = self.config.get('file_encoding', 'utf-8-sig')
        data.to_csv(filepath, index=False, encoding=file_encoding)
        self.logger.info(f"原始数据已保存: {filepath}")
    
    def collect_all_holdings_data(self, start_year: int = 2025, end_year: Optional[int] = None):
        """
        收集所有机构类型和季度的持股数据
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
        """
        self.logger.info("开始收集机构持股数据")
        
        quarter_dates = self.generate_quarter_dates(start_year, end_year)
        total_tasks = len(self.institution_types) * len(quarter_dates)
        completed_tasks = 0
        
        self.logger.info(f"总共需要获取 {total_tasks} 个数据集")
        
        # 统计信息
        success_count = 0
        failure_count = 0
        empty_count = 0
        
        for symbol in self.institution_types:
            for date in quarter_dates:
                completed_tasks += 1
                self.logger.info(f"进度: {completed_tasks}/{total_tasks} - 获取 {symbol} {date} 数据")
                
                # 检查文件是否已存在
                safe_symbol = symbol.replace("持仓", "").replace("持股", "")
                filename = f"{safe_symbol}_{date}.csv"
                filepath = os.path.join(self.raw_data_dir, filename)
                
                if self.skip_existing_files and os.path.exists(filepath):
                    self.logger.info(f"文件已存在，跳过: {filename}")
                    continue
                
                # 获取数据
                data = self.fetch_holdings_data(symbol, date)
                
                if data is not None:
                    if not data.empty:
                        self.save_raw_data(data, symbol, date)
                        success_count += 1
                    else:
                        empty_count += 1
                        self.logger.info(f"数据为空: {symbol} {date}")
                else:
                    failure_count += 1
        
        self.logger.info(f"数据收集完成 - 成功: {success_count}, 失败: {failure_count}, 空数据: {empty_count}")
    
    def load_and_merge_data(self, calculate_holding_ratio: bool = True) -> pd.DataFrame:
        """
        加载并合并所有原始数据，可选择是否计算持股比例
        
        Args:
            calculate_holding_ratio: 是否计算持股比例
            
        Returns:
            合并后的DataFrame
        """
        self.logger.info("开始加载和合并原始数据")
        
        all_data = []
        csv_files = [f for f in os.listdir(self.raw_data_dir) if f.endswith('.csv')]
        
        self.logger.info(f"找到 {len(csv_files)} 个原始数据文件")
        
        for filename in csv_files:
            filepath = os.path.join(self.raw_data_dir, filename)
            try:
                data = pd.read_csv(filepath, encoding='utf-8-sig')
                if not data.empty:
                    # 确保股票代码格式统一为6位数字字符串
                    if '股票代码' in data.columns:
                        data['股票代码'] = data['股票代码'].astype(str).str.zfill(6)
                    all_data.append(data)
                    self.logger.debug(f"加载文件: {filename}, 记录数: {len(data)}")
            except Exception as e:
                self.logger.error(f"加载文件失败 {filename}: {str(e)}")
        
        if all_data:
            merged_data = pd.concat(all_data, ignore_index=True)
            self.logger.info(f"数据合并完成，总记录数: {len(merged_data)}")
            
            # 确保股票代码格式统一为6位数字字符串
            if '股票代码' in merged_data.columns:
                self.logger.info("开始格式化股票代码为6位数字格式")
                original_codes = merged_data['股票代码'].nunique()
                merged_data['股票代码'] = merged_data['股票代码'].astype(str).str.zfill(6)
                formatted_codes = merged_data['股票代码'].nunique()
                self.logger.info(f"股票代码格式化完成: {original_codes} -> {formatted_codes} 只股票")
            
            # 如果需要计算持股比例，获取股本信息
            if calculate_holding_ratio and '股票代码' in merged_data.columns:
                merged_data = self._add_stock_info_and_ratios(merged_data)
            
            # 保存合并后的数据
            merged_filepath = os.path.join(self.processed_data_dir, "merged_holdings_data.csv")
            merged_data.to_csv(merged_filepath, index=False, encoding='utf-8-sig')
            self.logger.info(f"合并数据已保存: {merged_filepath}")
            
            return merged_data
        else:
            self.logger.warning("没有找到有效的数据文件")
            return pd.DataFrame()
    
    def _add_stock_info_and_ratios(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        为数据添加股本信息和持股比例
        
        Args:
            data: 原始持股数据
            
        Returns:
            添加了股本信息和持股比例的数据
        """
        self.logger.info("开始获取股本信息并计算持股比例")
        
        # 获取所有唯一的股票代码
        unique_stocks = data['股票代码'].unique()
        stock_info_dict = {}
        
        # 批量获取股本信息（利用缓存避免重复获取）
        self.logger.info(f"需要获取 {len(unique_stocks)} 只股票的基本信息")
        
        # 分批处理，避免内存问题
        batch_size = CONFIG.get('batch_size', 100)  # 从配置获取批处理大小
        total_batches = (len(unique_stocks) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(unique_stocks))
            batch_stocks = unique_stocks[start_idx:end_idx]
            
            self.logger.info(f"处理第 {batch_idx + 1}/{total_batches} 批股票 ({len(batch_stocks)} 只)")
            
            for i, stock_code in enumerate(batch_stocks, 1):
                # 确保stock_code是字符串类型，避免numpy.int64错误
                stock_code_str = str(stock_code).zfill(6)  # 转换为6位字符串格式
                
                # 显示进度
                global_idx = start_idx + i
                if global_idx % 50 == 0 or global_idx == len(unique_stocks):
                    self.logger.info(f"正在获取股票信息进度: {global_idx}/{len(unique_stocks)}")
                
                try:
                    stock_info = self.fetch_stock_info(stock_code_str)
                    if stock_info:
                        stock_info_dict[stock_code] = stock_info
                    else:
                        # 如果获取失败，使用默认值
                        stock_info_dict[stock_code] = {
                            'total_shares': 0,
                            'circulating_shares': 0,
                            'stock_name': '',
                            'industry': ''
                        }
                except Exception as e:
                    self.logger.error(f"获取股票 {stock_code_str} 信息时发生错误: {str(e)}")
                    stock_info_dict[stock_code] = {
                        'total_shares': 0,
                        'circulating_shares': 0,
                        'stock_name': '',
                        'industry': ''
                    }
            
            # 批处理完成后进行垃圾回收
            import gc
            gc.collect()
        
        self.logger.info(f"股票基本信息获取完成，成功获取 {sum(1 for v in stock_info_dict.values() if v.get('total_shares', 0) > 0)} 只股票信息")
        
        # 添加股本信息列
        data['总股本'] = data['股票代码'].map(lambda x: stock_info_dict.get(x, {}).get('total_shares', 0))
        data['流通股本'] = data['股票代码'].map(lambda x: stock_info_dict.get(x, {}).get('circulating_shares', 0))
        data['股票名称'] = data['股票代码'].map(lambda x: stock_info_dict.get(x, {}).get('stock_name', ''))
        data['所属行业'] = data['股票代码'].map(lambda x: stock_info_dict.get(x, {}).get('industry', ''))
        
        # 计算持股比例
        # 确保持股数量列存在且为数值类型
        if '持股总数' in data.columns:
            data['持股总数'] = pd.to_numeric(data['持股总数'], errors='coerce').fillna(0)
            
            # 安全计算持股比例，避免DataFrame索引错误
            try:
                # 计算占总股本比例（%）
                total_share_ratios = []
                for _, row in data.iterrows():
                    try:
                        if row['总股本'] > 0:
                            ratio = (row['持股总数'] / row['总股本'] * 100)
                        else:
                            ratio = 0.0
                        total_share_ratios.append(ratio)
                    except (ZeroDivisionError, TypeError, ValueError):
                        total_share_ratios.append(0.0)
                
                data['占总股本比例'] = total_share_ratios
                
                # 计算占流通股本比例（%）
                circulating_share_ratios = []
                for _, row in data.iterrows():
                    try:
                        if row['流通股本'] > 0:
                            ratio = (row['持股总数'] / row['流通股本'] * 100)
                        else:
                            ratio = 0.0
                        circulating_share_ratios.append(ratio)
                    except (ZeroDivisionError, TypeError, ValueError):
                        circulating_share_ratios.append(0.0)
                
                data['占流通股比例'] = circulating_share_ratios
                
                self.logger.info(f"成功计算 {len(unique_stocks)} 只股票的持股比例")
            except Exception as e:
                self.logger.error(f"计算持股比例时发生错误: {str(e)}")
                data['占总股本比例'] = 0.0
                data['占流通股比例'] = 0.0
        else:
            self.logger.warning("数据中未找到持股数量列(持股总数)，无法计算持股比例")
            data['占总股本比例'] = 0
            data['占流通股比例'] = 0
        
        return data
    
    @monitor_performance
    @handle_errors
    def analyze_stock_holdings_trend(self, merged_data: pd.DataFrame, stock_code: str = None) -> Dict:
        """
        分析个股的机构持仓变化趋势
        
        Args:
            merged_data: 合并后的数据
            stock_code: 指定股票代码，为None时分析所有股票
            
        Returns:
            分析结果字典
        """
        self.logger.info(f"开始分析个股机构持仓趋势 - 股票代码: {stock_code or '全部'}")
        
        if merged_data.empty:
            self.logger.warning("数据为空，无法进行分析")
            return {}
        
        try:
            # 数据预处理 - 列名映射
            analysis_data = merged_data.copy()
            
            # 将中文列名映射为英文列名以便数据验证
            column_mapping = {
                '股票代码': 'stock_code',
                '股票简称': 'stock_name',
                '股票名称': 'stock_name_full'
            }
            
            # 应用列名映射
            for chinese_col, english_col in column_mapping.items():
                if chinese_col in analysis_data.columns and english_col not in analysis_data.columns:
                    analysis_data[english_col] = analysis_data[chinese_col]
            
            # 数据验证
            if self.data_validator:
                validation_result = self.data_validator.validate_holdings_data(analysis_data)
                if validation_result is None or validation_result.empty:
                    self.logger.warning(f"数据验证失败: {stock_code or '全部'}")
                    return {}
                analysis_data = validation_result
            
            # 确保数值列为数值类型
            numeric_columns = ['hold_num', 'share_hold_num', 'value_position', 
                              'hold_value_change', 'hold_rate_change']
            
            for col in numeric_columns:
                if col in analysis_data.columns:
                    analysis_data[col] = pd.to_numeric(analysis_data[col], errors='coerce')
            
            # 转换日期格式
            analysis_data['report_date'] = pd.to_datetime(analysis_data['report_date'], format='%Y%m%d')
            
            # 如果指定了股票代码，筛选数据
            if stock_code:
                analysis_data = analysis_data[analysis_data['stock_code'] == stock_code]
                if analysis_data.empty:
                    self.logger.warning(f"未找到股票代码 {stock_code} 的数据")
                    return {}
            
            # 分析结果
            analysis_results = {
                'summary': self._generate_summary_statistics(analysis_data),
                'trend_analysis': self._analyze_trends(analysis_data),
                'institution_comparison': self._compare_institutions(analysis_data),
                'top_holdings': self._get_top_holdings(analysis_data),
                'data_quality': {
                    'total_records': len(analysis_data),
                    'missing_values': analysis_data.isnull().sum().to_dict(),
                    'data_completeness': float((1 - analysis_data.isnull().sum().sum() / (len(analysis_data) * len(analysis_data.columns))) * 100) if len(analysis_data) > 0 else 0
                },
                'risk_indicators': self._calculate_risk_indicators(analysis_data)
            }
            
            # 保存分析结果
            self._save_analysis_results(analysis_results, stock_code)
            
            return analysis_results
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, f"analyze_stock_holdings_trend_{stock_code or 'all'}")
            
            self.logger.error(f"分析股票 {stock_code or '全部'} 趋势时出错: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def _generate_summary_statistics(self, data: pd.DataFrame) -> Dict:
        """
        生成汇总统计信息
        """
        summary = {
            'total_records': len(data),
            'unique_stocks': data['stock_code'].nunique() if 'stock_code' in data.columns else 0,
            'date_range': {
                'start': data['report_date'].min().strftime('%Y-%m-%d') if 'report_date' in data.columns else None,
                'end': data['report_date'].max().strftime('%Y-%m-%d') if 'report_date' in data.columns else None
            },
            'institution_types': data['institution_type'].unique().tolist() if 'institution_type' in data.columns else [],
            'total_market_value': data['value_position'].sum() if 'value_position' in data.columns else 0
        }
        
        self.logger.info(f"汇总统计 - 记录数: {summary['total_records']}, 股票数: {summary['unique_stocks']}")
        return summary
    
    def _analyze_trends(self, data: pd.DataFrame) -> Dict:
        """
        分析持仓趋势
        """
        if 'report_date' not in data.columns or 'value_position' not in data.columns:
            return {}
        
        # 按季度汇总
        quarterly_summary = data.groupby(['report_date', 'institution_type']).agg({
            'value_position': 'sum',
            'share_hold_num': 'sum',
            'stock_code': 'nunique'
        }).reset_index()
        
        # 计算环比增长率
        quarterly_summary = quarterly_summary.sort_values(['institution_type', 'report_date'])
        quarterly_summary['value_growth_rate'] = quarterly_summary.groupby('institution_type')['value_position'].pct_change()
        
        trend_analysis = {
            'quarterly_summary': quarterly_summary.to_dict('records'),
            'overall_trend': 'increasing' if quarterly_summary['value_position'].iloc[-1] > quarterly_summary['value_position'].iloc[0] else 'decreasing'
        }
        
        return trend_analysis
    
    def _compare_institutions(self, data: pd.DataFrame) -> Dict:
        """
        比较不同机构类型的持仓情况
        """
        if 'institution_type' not in data.columns or 'value_position' not in data.columns:
            return {}
        
        institution_comparison = data.groupby('institution_type').agg({
            'value_position': ['sum', 'mean', 'count'],
            'share_hold_num': ['sum', 'mean'],
            'stock_code': 'nunique'
        }).round(2)
        
        # 扁平化列名
        institution_comparison.columns = ['_'.join(col).strip() for col in institution_comparison.columns]
        
        return institution_comparison.to_dict('index')
    
    def _get_top_holdings(self, data: pd.DataFrame, top_n: int = None) -> Dict:
        """
        获取持仓市值最大的股票
        """
        if top_n is None:
            top_n = self.top_holdings_count
            
        if 'stock_code' not in data.columns or 'value_position' not in data.columns:
            return {}
        
        # 按股票代码汇总最新持仓
        latest_date = data['report_date'].max()
        latest_data = data[data['report_date'] == latest_date]
        
        top_holdings = latest_data.groupby(['stock_code', 'stock_name']).agg({
            'value_position': 'sum',
            'share_hold_num': 'sum',
            'institution_type': lambda x: ', '.join(x.unique())
        }).sort_values('value_position', ascending=False).head(top_n)
        
        return {
            'date': latest_date.strftime('%Y-%m-%d'),
            'top_holdings': top_holdings.to_dict('index')
        }
    
    def _calculate_risk_indicators(self, data: pd.DataFrame) -> Dict:
        """
        计算风险指标
        
        Args:
            data: 分析数据
            
        Returns:
            风险指标字典
        """
        risk_indicators = {}
        
        try:
            if 'value_position' in data.columns:
                # 集中度风险
                total_value = data['value_position'].sum()
                if total_value > 0:
                    max_holding = data['value_position'].max()
                    risk_indicators['concentration_risk'] = float(max_holding / total_value)
                
                # 持仓波动性
                risk_indicators['holding_volatility'] = float(data['value_position'].std())
            
            # 机构多样性
            risk_indicators['institution_diversity'] = data['institution_type'].nunique()
            
            # 股票多样性
            if 'stock_code' in data.columns:
                risk_indicators['stock_diversity'] = data['stock_code'].nunique()
            
            # 时间跨度风险
            if 'report_date' in data.columns:
                date_range = (data['report_date'].max() - data['report_date'].min()).days
                risk_indicators['time_span_days'] = int(date_range)
            
        except Exception as e:
            self.logger.warning(f"计算风险指标时出错: {str(e)}")
        
        return risk_indicators
    
    def _save_analysis_results(self, results: Dict, stock_code: str = None):
        """
        保存分析结果
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if stock_code:
            filename = f"analysis_{stock_code}_{timestamp}.json"
        else:
            filename = f"analysis_all_stocks_{timestamp}.json"
        
        filepath = os.path.join(self.analysis_dir, filename)
        
        # 处理不能JSON序列化的对象
        def json_serializer(obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return str(obj)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=json_serializer)
        
        self.logger.info(f"分析结果已保存: {filepath}")
    
    def generate_report(self, analysis_results: Dict, stock_code: str = None) -> str:
        """
        生成分析报告
        
        Args:
            analysis_results: 分析结果
            stock_code: 股票代码
            
        Returns:
            报告内容
        """
        report_lines = []
        report_lines.append("# 机构持股分析报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if stock_code:
            report_lines.append(f"\n分析对象: {stock_code}")
        else:
            report_lines.append("\n分析对象: 全市场")
        
        # 汇总信息
        if 'summary' in analysis_results:
            summary = analysis_results['summary']
            report_lines.append("\n## 数据概览")
            report_lines.append(f"- 总记录数: {summary.get('total_records', 0):,}")
            report_lines.append(f"- 涉及股票数: {summary.get('unique_stocks', 0):,}")
            report_lines.append(f"- 数据时间范围: {summary.get('date_range', {}).get('start', 'N/A')} 至 {summary.get('date_range', {}).get('end', 'N/A')}")
            report_lines.append(f"- 机构类型: {', '.join(summary.get('institution_types', []))}")
            report_lines.append(f"- 总持仓市值: {summary.get('total_market_value', 0):,.2f} 元")
        
        # 机构对比
        if 'institution_comparison' in analysis_results:
            report_lines.append("\n## 机构类型对比")
            for institution, stats in analysis_results['institution_comparison'].items():
                report_lines.append(f"\n### {institution}")
                report_lines.append(f"- 总持仓市值: {stats.get('value_position_sum', 0):,.2f} 元")
                report_lines.append(f"- 平均持仓市值: {stats.get('value_position_mean', 0):,.2f} 元")
                report_lines.append(f"- 持仓记录数: {stats.get('value_position_count', 0):,}")
                report_lines.append(f"- 持仓股票数: {stats.get('stock_code_nunique', 0):,}")
        
        # 重仓股
        if 'top_holdings' in analysis_results:
            top_holdings = analysis_results['top_holdings']
            report_lines.append("\n## 重仓股TOP20")
            report_lines.append(f"\n数据日期: {top_holdings.get('date', 'N/A')}")
            
            for i, (stock_info, data) in enumerate(top_holdings.get('top_holdings', {}).items(), 1):
                stock_code, stock_name = stock_info if isinstance(stock_info, tuple) else (stock_info, "")
                report_lines.append(f"\n{i}. {stock_code} {stock_name}")
                report_lines.append(f"   - 持仓市值: {data.get('value_position', 0):,.2f} 元")
                report_lines.append(f"   - 持股数量: {data.get('share_hold_num', 0):,.0f} 股")
                report_lines.append(f"   - 机构类型: {data.get('institution_type', 'N/A')}")
        
        report_content = "\n".join(report_lines)
        
        # 保存报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if stock_code:
            filename = f"report_{stock_code}_{timestamp}.md"
        else:
            filename = f"report_all_stocks_{timestamp}.md"
        
        filepath = os.path.join(self.analysis_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"分析报告已保存: {filepath}")
        return report_content
    
    def run_full_analysis(self, start_year: int = 2020, end_year: Optional[int] = None, 
                         target_stock: str = None):
        """
        运行完整的分析流程
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            target_stock: 目标股票代码，为None时分析全市场
        """
        self.logger.info("开始运行完整的机构持股分析流程")
        
        try:
            # 1. 收集数据
            self.logger.info("步骤1: 收集机构持股数据")
            self.collect_all_holdings_data(start_year, end_year)
            
            # 2. 合并数据
            self.logger.info("步骤2: 合并和处理数据")
            merged_data = self.load_and_merge_data(calculate_holding_ratio=True)
            
            if merged_data.empty:
                self.logger.error("没有可用的数据进行分析")
                return
            
            if 'total_share_ratio' in merged_data.columns:
                self.logger.info("已成功计算持股比例")
            
            # 3. 分析数据
            self.logger.info("步骤3: 分析机构持股趋势")
            analysis_results = self.analyze_stock_holdings_trend(merged_data, target_stock)
            
            # 4. 生成报告
            self.logger.info("步骤4: 生成分析报告")
            report = self.generate_report(analysis_results, target_stock)
            
            self.logger.info("完整分析流程执行完成")
            print("\n" + "="*50)
            print("分析完成！")
            print(f"数据目录: {self.base_dir}")
            print(f"日志文件: {self.logs_dir}")
            print(f"分析结果: {self.analysis_dir}")
            print("="*50)
            
        except Exception as e:
            self.logger.error(f"分析流程执行失败: {str(e)}")
            raise


@monitor_performance
@handle_errors
def main():
    """
    主函数
    """
    print("机构持股数据分析器 (增强版)")
    print("=" * 50)
    
    # 创建分析器实例
    analyzer = InstitutionalHoldingsAnalyzer()
    
    # 从配置获取参数
    start_year = CONFIG.get('start_year', 2020)
    end_year = CONFIG.get('end_year', None)  # 默认到当前年份
    target_stock = CONFIG.get('target_stock_code', None)  # 分析全市场，也可以指定如 "000001"
    
    print(f"分析参数:")
    print(f"- 开始年份: {start_year}")
    print(f"- 结束年份: {end_year or '当前年份'}")
    print(f"- 目标股票: {target_stock or '全市场'}")
    print(f"- 数据目录: {analyzer.base_dir}")
    print(f"- 机构类型: {len(analyzer.institution_types)}种")
    print("\n开始分析...")
    
    # 启动性能监控
    if analyzer.performance_monitor:
        analyzer.performance_monitor.start_system_monitoring()
    
    try:
        # 运行分析
        analyzer.run_full_analysis(
            start_year=start_year,
            end_year=end_year,
            target_stock=target_stock
        )
        
    finally:
        # 停止性能监控并生成报告
        if analyzer.performance_monitor:
            analyzer.performance_monitor.stop_system_monitoring()
            performance_summary = analyzer.performance_monitor.get_performance_summary()
            print(f"\n=== 性能报告 ===")
            
            # 检查是否有性能数据
            if 'message' in performance_summary:
                print(performance_summary['message'])
            else:
                # 计算总执行时间
                total_runtime = 0
                if 'function_statistics' in performance_summary:
                    for stats in performance_summary['function_statistics'].values():
                        total_runtime += stats.get('total_duration', 0)
                
                # 获取峰值内存
                peak_memory = performance_summary.get('system_statistics', {}).get('peak_memory_mb', 0)
                
                print(f"总执行时间: {total_runtime:.2f} 秒")
                print(f"内存使用峰值: {peak_memory:.2f} MB")
            
            # 保存性能报告
            performance_file = os.path.join(analyzer.logs_dir, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(performance_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(performance_summary, f, ensure_ascii=False, indent=2)
        
        # 生成错误报告
        if analyzer.error_handler:
            error_stats = analyzer.error_handler.get_error_statistics()
            if 'message' not in error_stats and error_stats.get('total_errors', 0) > 0:
                print(f"\n=== 错误报告 ===")
                print(f"总错误数: {error_stats.get('total_errors', 0)}")
                print(f"已解决错误: {error_stats.get('resolved_errors', 0)}")
                print(f"解决率: {error_stats.get('resolution_rate', 0):.1f}%")
                
                # 显示严重程度分布
                severity_counts = error_stats.get('error_by_severity', {})
                critical_errors = severity_counts.get('critical', 0)
                if critical_errors > 0:
                    print(f"严重错误数: {critical_errors}")
                
                # 保存错误报告
                error_file = os.path.join(analyzer.logs_dir, f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump(error_stats, f, ensure_ascii=False, indent=2)
        
        # 清理缓存
        if analyzer.cache_manager:
            cache_stats = analyzer.cache_manager.get_cache_stats()
            print(f"\n=== 缓存统计 ===")
            print(f"缓存命中率: {cache_stats.get('hit_rate_percent', 0):.2f}%")
            print(f"总请求数: {cache_stats.get('total_requests', 0)}")
            print(f"内存命中: {cache_stats.get('memory_hits', 0)}")
            print(f"文件命中: {cache_stats.get('file_hits', 0)}")
            print(f"缓存未命中: {cache_stats.get('misses', 0)}")
            print(f"内存缓存条目: {cache_stats.get('memory_cache', {}).get('total_entries', 0)}")
            print(f"文件缓存条目: {cache_stats.get('file_cache', {}).get('total_entries', 0)}")


if __name__ == "__main__":
    main()