"""
股票数据Pearson相关系数分析脚本 - GPU批量评测版本

该脚本支持批量处理多个评测日期，通过三维矩阵运算大幅提升GPU利用率。
相比单日评测版本，可以同时处理多个评测日期，实现更高的并行计算效率。

功能：
1. 支持批量评测日期参数（evaluation_days）
2. 三维GPU矩阵运算：[评测日期数, 窗口大小, 字段数]
3. 批量计算所有评测日期的Pearson相关系数
4. 智能内存管理，避免GPU内存溢出
5. 批量结果统计和CSV导出
6. GPU显存监控和自适应分组处理

使用方法：
python pearson_analyzer_gpu.py 000001 --evaluation_days 100

作者：Stock Backtest System
创建时间：2024年
GPU批量优化版本：2024年
"""

import argparse
import logging
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from scipy.stats import pearsonr
from data_loader import StockDataLoader
import matplotlib.pyplot as plt
import mplfinance as mpf
from stock_config import get_comparison_stocks
import time
import threading
from collections import defaultdict
import warnings
import gc
import multiprocessing as mp
from functools import partial

# 忽略一些不重要的警告
warnings.filterwarnings('ignore', category=UserWarning)


def _process_stock_historical_data_worker(args):
    """
    多进程工作函数：处理单只股票的历史数据
    
    Args:
        args: (stock_code, stock_data, window_size, fields, debug)
    
    Returns:
        tuple: (stock_code, historical_data_list, stats)
    """
    stock_code, stock_data, window_size, fields, debug = args
    
    historical_data = []
    stock_valid_periods = 0
    stock_invalid_periods = 0
    
    try:
        # 使用所有可用数据
        available_data = stock_data
        
        if len(available_data) < window_size:
            return stock_code, [], {'valid_periods': 0, 'invalid_periods': 0, 'skipped': True}
        
        # 生成该股票的历史期间并直接进行筛选和预处理
        for i in range(len(available_data) - window_size + 1):
            period_data = available_data.iloc[i:i + window_size]
            
            # 检查数据长度是否正确
            if len(period_data) == window_size:
                start_date = period_data.index[0]
                end_date = period_data.index[-1]
                
                # 直接提取并预处理数据
                historical_values = period_data[fields].values
                
                # 存储预处理后的数据
                historical_data.append((historical_values, start_date, end_date, stock_code))
                stock_valid_periods += 1
            else:
                stock_invalid_periods += 1
        
        return stock_code, historical_data, {
            'valid_periods': stock_valid_periods, 
            'invalid_periods': stock_invalid_periods, 
            'skipped': False
        }
        
    except Exception as e:
        if debug:
            print(f"处理股票 {stock_code} 时出错: {str(e)}")
        return stock_code, [], {'valid_periods': 0, 'invalid_periods': 0, 'error': str(e)}


class GPUBatchPearsonAnalyzer:
    def __init__(self, stock_code, log_dir='logs', window_size=15, threshold=0.85, 
                 evaluation_days=1, debug=False, comparison_stocks=None, 
                 comparison_mode='top10', backtest_date=None, 
                 csv_filename='evaluation_results.csv', use_gpu=True, 
                 batch_size=1000, gpu_memory_limit=0.8, earliest_date='2020-01-01',
                 num_processes=None, evaluation_batch_size=20):
        """
        初始化GPU批量评测Pearson相关性分析器
        
        Args:
            stock_code: 目标股票代码，支持单个股票或逗号分隔的多个股票
            log_dir: 日志目录
            window_size: 分析窗口大小（交易日数量）
            threshold: 相关系数阈值
            evaluation_days: 评测日期数量（从backtest_date往前数的交易日数）
            debug: 是否开启debug模式
            comparison_stocks: 自定义对比股票列表
            comparison_mode: 对比模式
            backtest_date: 回测起始日期 (格式: YYYY-MM-DD)
            csv_filename: CSV结果文件名
            use_gpu: 是否使用GPU加速
            batch_size: GPU批处理大小
            gpu_memory_limit: GPU内存使用限制（0.0-1.0）
            earliest_date: 数据获取的最早日期限制 (格式: YYYY-MM-DD，默认: 2020-01-01)
            num_processes: 多进程数量，None表示自动检测（默认为CPU核心数-1）
            evaluation_batch_size: 每批次处理的计算单元数量，用于控制GPU内存使用
                              单股票模式: 直接表示评测日期数量
                              多股票模式: 表示总计算单元数 (股票数 × 评测日期数)
                              例如: 100股票×15评测日期=1500计算单元，batch_size=20时分75批处理 (默认: 20)
        """
        # 支持多个股票代码
        if isinstance(stock_code, str):
            if ',' in stock_code:
                self.stock_codes = [code.strip() for code in stock_code.split(',')]
            else:
                self.stock_codes = [stock_code]
        elif isinstance(stock_code, list):
            self.stock_codes = stock_code
        else:
            self.stock_codes = [str(stock_code)]
        
        self.stock_code = self.stock_codes[0]  # 保持向后兼容性，主要股票代码
        self.is_multi_stock = len(self.stock_codes) > 1
        
        # 设置固定的绝对路径
        script_dir = r'C:\Users\17701\github\my_first_repo\stockapi\stock_backtest\pearson_found'
        self.log_dir = os.path.join(script_dir, 'logs')
        self.csv_results_file = os.path.join(script_dir, csv_filename)
        
        self.window_size = window_size
        self.threshold = threshold
        self.evaluation_days = evaluation_days  # 新增：评测日期数量
        self.evaluation_batch_size = evaluation_batch_size  # 每批次处理的评测日期数量
        self.debug = debug
        self.comparison_mode = comparison_mode
        self.backtest_date = pd.to_datetime(backtest_date) if backtest_date else None
        self.earliest_date = pd.to_datetime(earliest_date)
        self.use_gpu = use_gpu
        self.batch_size = batch_size
        self.gpu_memory_limit = gpu_memory_limit
        self.data_loader = None
        self.logger = None
        
        # 多进程设置
        self.num_processes = num_processes if num_processes is not None else max(1, mp.cpu_count() - 1)
        
        # 设置CSV保存功能（默认启用）
        self.save_results = True
        
        # GPU设备设置
        self.device = self._setup_device()
        
        # GPU显存监控
        self.gpu_memory_stats = {
            'peak_allocated': 0,
            'peak_reserved': 0,
            'current_allocated': 0,
            'current_reserved': 0
        }
        
        # 设置对比股票列表
        if comparison_stocks:
            self.comparison_stocks = comparison_stocks
        elif comparison_mode == 'self_only':
            self.comparison_stocks = [stock_code]
        else:
            self.comparison_stocks = get_comparison_stocks(comparison_mode)
            # 确保目标股票不在对比列表中（避免重复）
            # if stock_code in self.comparison_stocks:
            #     self.comparison_stocks.remove(stock_code)
        
        # 存储已加载的股票数据
        self.loaded_stocks_data = {}
        
        # 性能计时器
        self.performance_timers = defaultdict(list)
        self.current_timers = {}
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 设置日志
        self._setup_logging()
        
        # 设置CSV文件
        self._setup_csv_file()
        
        if self.is_multi_stock:
            self.logger.info(f"初始化GPU批量评测Pearson分析器，目标股票: {self.stock_codes} (多股票模式)")
        else:
            self.logger.info(f"初始化GPU批量评测Pearson分析器，目标股票: {self.stock_code}")
        self.logger.info(f"窗口大小: {window_size}, 阈值: {threshold}, 评测日期数: {evaluation_days}")
        self.logger.info(f"GPU设备: {self.device}, 批处理大小: {batch_size}")
        self.logger.info(f"GPU内存限制: {gpu_memory_limit*100:.0f}%")
        self.logger.info(f"对比模式: {comparison_mode}, 对比股票数量: {len(self.comparison_stocks)}")
    
    def _setup_device(self):
        """设置计算设备（GPU或CPU）"""
        if self.use_gpu and torch.cuda.is_available():
            device = torch.device('cuda')
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if self.debug:
                print(f"使用GPU加速: {gpu_name} ({gpu_memory:.1f}GB)")
            return device
        else:
            if self.use_gpu:
                print("警告：CUDA不可用，回退到CPU计算")
            else:
                print("使用CPU计算")
            return torch.device('cpu')
    
    def _setup_logging(self):
        """设置日志配置"""
        # 直接使用logs根目录，不创建子文件夹
        os.makedirs(self.log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thread_id = threading.get_ident()
        
        # 根据是否为多股票模式决定日志文件名
        if self.is_multi_stock:
            log_filename = f"batch_pearson_analysis_list_{timestamp}_thread_{thread_id}.log"
            logger_name = 'GPUBatchPearsonAnalyzer_list'
        else:
            log_filename = f"batch_pearson_analysis_{self.stock_code}_{timestamp}_thread_{thread_id}.log"
            logger_name = f'GPUBatchPearsonAnalyzer_{self.stock_code}'
        
        log_path = os.path.join(self.log_dir, log_filename)
        
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8-sig')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.info(f"批量评测日志文件创建: {log_path}")
    
    def _setup_csv_file(self):
        """设置CSV文件，如果不存在则创建"""
        self.logger.info(f"📋 开始设置CSV文件: {self.csv_results_file}")
        
        if not os.path.exists(self.csv_results_file):
            self.logger.info("📋 CSV文件不存在，开始创建新文件...")
            
            # 使用与单日脚本相同的表头格式
            header = ['代码', 'window_size', '阈值', '评测日期', '对比股票数量', '相关数量', 
                     '下1日高开', '下1日上涨', '下3日上涨', '下5日上涨', '下10日上涨']
            
            self.logger.info(f"📋 CSV表头字段: {header}")
            self.logger.info(f"📋 CSV表头字段数量: {len(header)}")
            
            df = pd.DataFrame(columns=header)
            df['代码'] = df['代码'].astype(str)
            
            try:
                df.to_csv(self.csv_results_file, index=False, encoding='utf-8-sig')
                
                # 验证文件创建成功
                if os.path.exists(self.csv_results_file):
                    file_size = os.path.getsize(self.csv_results_file)
                    self.logger.info(f"✅ CSV文件创建成功: {self.csv_results_file}")
                    self.logger.info(f"✅ 初始文件大小: {file_size} bytes")
                    self.logger.info(f"✅ 编码格式: utf-8-sig")
                else:
                    self.logger.error("❌ CSV文件创建失败：文件不存在")
                    
            except Exception as e:
                self.logger.error(f"❌ CSV文件创建时出错: {str(e)}")
                raise
        else:
            # 文件已存在，检查文件状态
            try:
                file_size = os.path.getsize(self.csv_results_file)
                existing_df = pd.read_csv(self.csv_results_file, encoding='utf-8-sig', dtype={'代码': str})
                row_count = len(existing_df)
                
                self.logger.info(f"📋 CSV文件已存在: {self.csv_results_file}")
                self.logger.info(f"📋 现有文件大小: {file_size} bytes")
                self.logger.info(f"📋 现有记录数量: {row_count} 行")
                
                if row_count > 0:
                    self.logger.info(f"📋 现有数据列名: {list(existing_df.columns)}")
                    # 显示最近的几条记录作为参考
                    if row_count <= 3:
                        self.logger.info(f"📋 现有数据预览: \n{existing_df.to_string()}")
                    else:
                        self.logger.info(f"📋 最新3条记录预览: \n{existing_df.head(3).to_string()}")
                        
            except Exception as e:
                self.logger.warning(f"⚠️ 读取现有CSV文件时出错: {str(e)}")
                
        self.logger.info("📋 CSV文件设置完成")
    
    def start_timer(self, timer_name, parent_timer=None):
        """
        开始计时
        
        Args:
            timer_name: 计时器名称
            parent_timer: 父计时器名称（用于分层显示）
        """
        self.current_timers[timer_name] = {
            'start_time': time.time(),
            'parent': parent_timer
        }
        if self.debug:
            self.logger.info(f"⏱️ 开始计时: {timer_name}")
    
    def end_timer(self, timer_name):
        """结束计时并记录耗时"""
        if timer_name in self.current_timers:
            timer_info = self.current_timers[timer_name]
            elapsed_time = time.time() - timer_info['start_time']
            
            # 存储计时信息，包括父计时器信息
            if timer_name not in self.performance_timers:
                self.performance_timers[timer_name] = []
            
            self.performance_timers[timer_name].append({
                'elapsed_time': elapsed_time,
                'parent': timer_info['parent'],
                'timestamp': time.time()
            })
            
            del self.current_timers[timer_name]
            if self.debug:
                self.logger.info(f"⏱️ 结束计时: {timer_name} - 耗时: {elapsed_time:.3f}秒")
            return elapsed_time
        return 0
    
    def load_data(self):
        """一次性加载所有目标股票和对比股票数据，实现真正的批量处理"""
        self.start_timer('all_data_loading')
        
        if self.is_multi_stock:
            self.logger.info(f"📊 批量数据加载中: {len(self.stock_codes)} 个目标股票 + {len(self.comparison_stocks)} 个对比股票")
        else:
            self.logger.info(f"📊 数据加载中: 1 个目标股票 + {len(self.comparison_stocks)} 个对比股票")
        
        self.data_loader = StockDataLoader()
        
        # 存储所有目标股票的数据
        self.multi_stock_data = {}
        # 存储所有对比股票的数据（避免重复加载）
        self.loaded_stocks_data = {}
        
        # 1. 首先加载所有对比股票数据
        self.logger.info(f"📈 [1/2] 加载对比股票数据...")
        successful_comparison_loads = 0
        for stock_code in self.comparison_stocks:
            try:
                data = self.data_loader.load_stock_data(stock_code)
                if data is not None and not data.empty:
                    filtered_data = self._filter_data(data, stock_code, is_target_stock=False)
                    if not filtered_data.empty:
                        self.loaded_stocks_data[stock_code] = filtered_data
                        successful_comparison_loads += 1
                    else:
                        if self.debug:
                            self.logger.warning(f"对比股票 {stock_code} 过滤后数据为空")
                else:
                    if self.debug:
                        self.logger.warning(f"无法加载对比股票 {stock_code} 的数据")
                        
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"加载对比股票 {stock_code} 时出错: {str(e)}")
                continue
        
        # 2. 然后加载目标股票数据（检查是否已在对比股票中）
        self.logger.info(f"📈 [2/2] 加载目标股票数据...")
        successful_target_loads = 0
        for stock_code in self.stock_codes:
            try:
                # 检查目标股票是否已经在对比股票数据中
                if stock_code in self.loaded_stocks_data:
                    # 如果已经在对比股票中，直接使用，但需要重新过滤为目标股票格式
                    original_data = self.data_loader.load_stock_data(stock_code)
                    if original_data is not None and not original_data.empty:
                        filtered_data = self._filter_data(original_data, stock_code, is_target_stock=True)
                        self.multi_stock_data[stock_code] = filtered_data
                        successful_target_loads += 1
                        self.logger.info(f"✅ 目标股票 {stock_code} 数据已存在于对比股票中，重新过滤完成 ({len(filtered_data)} 条记录)")
                    else:
                        self.logger.error(f"无法重新加载目标股票 {stock_code} 的数据")
                        continue
                else:
                    # 如果不在对比股票中，单独加载
                    data = self.data_loader.load_stock_data(stock_code)
                    
                    if data is None or data.empty:
                        self.logger.error(f"无法加载目标股票 {stock_code} 的数据")
                        continue
                    
                    filtered_data = self._filter_data(data, stock_code, is_target_stock=True)
                    self.multi_stock_data[stock_code] = filtered_data
                    successful_target_loads += 1
                    self.logger.info(f"✅ 目标股票 {stock_code} 数据单独加载完成 ({len(filtered_data)} 条记录)")
            except Exception as e:
                self.logger.error(f"加载目标股票 {stock_code} 时出错: {str(e)}")
                continue
        
        if not self.multi_stock_data:
            self.logger.error("没有成功加载任何目标股票数据")
            self.end_timer('all_data_loading')
            return None
        
        # 为了保持向后兼容性，将第一个股票的数据设为主数据
        self.data = self.multi_stock_data[self.stock_codes[0]]
        
        self.logger.info(f"✅ 数据加载完成: {successful_target_loads}/{len(self.stock_codes)} 个目标股票, {successful_comparison_loads}/{len(self.comparison_stocks)} 个对比股票")
        self.end_timer('all_data_loading')
        return self.data
    
    def _filter_data(self, data, stock_code, is_target_stock=False):
        """过滤股票数据，确保数据质量和日期范围
        
        Args:
            data: 股票数据DataFrame
            stock_code: 股票代码
            is_target_stock: 是否为目标股票，目标股票不受earliest_date限制
        """
        if data is None or data.empty:
            return data
            
        original_count = len(data)
        date_filtered_count = original_count
        date_removed_count = 0
        
        # 只对对比股票应用日期过滤，目标股票使用完整历史数据
        if not is_target_stock:
            data = data[data.index >= self.earliest_date]
            date_filtered_count = len(data)
            date_removed_count = original_count - date_filtered_count
        
        # 数据质量过滤（对所有股票都应用）
        data = data[
            (data['open'] > 1) & 
            (data['high'] > 1) & 
            (data['low'] > 1) & 
            (data['close'] > 1) & 
            (data['volume'] > 1)
        ]
        final_count = len(data)
        quality_removed_count = date_filtered_count - final_count
        
        if date_removed_count > 0:
            self.logger.debug(f"对比股票 {stock_code} 日期过滤完成，移除早于 {self.earliest_date.strftime('%Y-%m-%d')} 的 {date_removed_count} 条数据")
        elif is_target_stock:
            self.logger.debug(f"目标股票 {stock_code} 使用完整历史数据，无日期过滤")
        
        if quality_removed_count > 0:
            self.logger.debug(f"股票 {stock_code} 数据质量过滤完成，移除 {quality_removed_count} 条异常数据")
        
        if not data.empty:
            self.logger.debug(f"股票 {stock_code} 成功加载 {len(data)} 条记录，日期范围: {data.index[0]} 到 {data.index[-1]}")
        
        return data
    

    
    def prepare_evaluation_dates(self, end_date):
        """
        准备批量评测日期列表
        
        Args:
            end_date: 结束日期，如果为None则使用数据的最新日期
            
        Returns:
            list: 评测日期列表
        """
        self.start_timer('evaluation_dates_preparation')
        
        # 如果end_date为None，使用数据的最新日期
        if end_date is None:
            end_date = self.data.index.max()
            self.logger.info(f"未指定结束日期，使用数据最新日期: {end_date}")
        
        # 获取所有可用的交易日期（包含end_date当天，如果数据可用）
        available_dates = self.data[self.data.index <= end_date].index
        
        if len(available_dates) < self.evaluation_days + self.window_size:
            self.logger.warning(f"可用数据不足，需要 {self.evaluation_days + self.window_size} 个交易日，"
                              f"实际只有 {len(available_dates)} 个")
            # 调整评测日期数量
            self.evaluation_days = max(1, len(available_dates) - self.window_size)
            self.logger.info(f"调整评测日期数量为: {self.evaluation_days}")
        
        # 选择最近的evaluation_days个交易日作为评测日期
        evaluation_dates = available_dates[-self.evaluation_days:].tolist()
        
        self.logger.info(f"准备了 {len(evaluation_dates)} 个评测日期")
        self.logger.info(f"评测日期范围: {evaluation_dates[0]} 到 {evaluation_dates[-1]}")
        
        self.end_timer('evaluation_dates_preparation')
        return evaluation_dates
    
    def prepare_batch_evaluation_data(self, evaluation_dates):
        """
        准备批量评测数据矩阵，支持多股票
        
        Args:
            evaluation_dates: 评测日期列表
            
        Returns:
            torch.Tensor: 形状为 [num_stocks, evaluation_days, window_size, 5] 的评测数据张量（多股票）
                         或 [evaluation_days, window_size, 5] 的评测数据张量（单股票）
            list: 有效评测日期列表
            list: 股票代码列表（多股票模式）
        """
        self.start_timer('batch_data_preparation')
        
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        if self.is_multi_stock:
            # 多股票模式：为每个股票构建数据
            multi_stock_batch_data = []
            valid_stock_codes = []
            common_valid_dates = None
            
            for stock_code in self.stock_codes:
                if stock_code not in self.multi_stock_data:
                    self.logger.warning(f"股票 {stock_code} 数据未加载，跳过")
                    continue
                
                stock_data = self.multi_stock_data[stock_code]
                batch_data_list = []
                valid_dates = []
                
                for eval_date in evaluation_dates:
                    # 获取该评测日期的窗口数据（包含评测日期当天）
                    recent_data = stock_data[stock_data.index <= eval_date].tail(self.window_size)
                    
                    if len(recent_data) == self.window_size:
                        # 提取字段数据
                        data_values = recent_data[fields].values  # [window_size, 5]
                        batch_data_list.append(data_values)
                        valid_dates.append(eval_date)
                    else:
                        if self.debug:
                            self.logger.warning(f"股票 {stock_code} 评测日期 {eval_date} 的数据不足，跳过")
                
                if batch_data_list:
                    # 转换为数组 [evaluation_days, window_size, 5]
                    stock_batch_data = np.stack(batch_data_list, axis=0)
                    multi_stock_batch_data.append(stock_batch_data)
                    valid_stock_codes.append(stock_code)
                    
                    # 确保所有股票使用相同的有效日期
                    if common_valid_dates is None:
                        common_valid_dates = valid_dates
                    else:
                        # 取交集，确保所有股票都有数据的日期
                        common_valid_dates = [date for date in common_valid_dates if date in valid_dates]
            
            if not multi_stock_batch_data:
                self.logger.error("没有有效的多股票评测数据")
                self.end_timer('batch_data_preparation')
                return None, [], []
            
            # 重新筛选数据，确保所有股票使用相同的日期
            final_multi_stock_data = []
            for i, stock_code in enumerate(valid_stock_codes):
                stock_data = multi_stock_batch_data[i]
                # 这里简化处理，假设日期顺序一致
                final_multi_stock_data.append(stock_data[:len(common_valid_dates)])
            
            # 转换为张量 [num_stocks, evaluation_days, window_size, 5]
            batch_data = np.stack(final_multi_stock_data, axis=0)
            batch_tensor = torch.tensor(batch_data, dtype=torch.float32, device=self.device)
            
            self.logger.info(f"多股票批量评测数据准备完成，形状: {batch_tensor.shape}")
            self.logger.info(f"有效股票数量: {len(valid_stock_codes)}")
            self.logger.info(f"有效评测日期数量: {len(common_valid_dates)}")
            
            self.end_timer('batch_data_preparation')
            return batch_tensor, common_valid_dates, valid_stock_codes
        
        else:
            # 单股票模式：保持原有逻辑
            batch_data_list = []
            valid_dates = []
            
            for eval_date in evaluation_dates:
                # 获取该评测日期的窗口数据（包含评测日期当天）
                recent_data = self.data[self.data.index <= eval_date].tail(self.window_size)
                
                if len(recent_data) == self.window_size:
                    # 提取字段数据
                    data_values = recent_data[fields].values  # [window_size, 5]
                    batch_data_list.append(data_values)
                    valid_dates.append(eval_date)
                else:
                    if self.debug:
                        self.logger.warning(f"评测日期 {eval_date} 的数据不足，跳过")
            
            if not batch_data_list:
                self.logger.error("没有有效的评测数据")
                self.end_timer('batch_data_preparation')
                return None, [], []
            
            # 转换为张量 [evaluation_days, window_size, 5]
            batch_data = np.stack(batch_data_list, axis=0)
            batch_tensor = torch.tensor(batch_data, dtype=torch.float32, device=self.device)
            
            self.logger.info(f"批量评测数据准备完成，形状: {batch_tensor.shape}")
            self.logger.info(f"有效评测日期数量: {len(valid_dates)}")
            
            self.end_timer('batch_data_preparation')
            return batch_tensor, valid_dates, [self.stock_code]
    
    def calculate_batch_gpu_correlation(self, batch_recent_data, historical_periods_data, evaluation_dates=None):
        """
        批量GPU相关性计算
        
        Args:
            batch_recent_data: 批量评测数据 [evaluation_days, window_size, 5]
            historical_periods_data: 历史期间数据列表
            evaluation_dates: 评测日期列表
            
        Returns:
            dict: 批量相关性结果
        """
        
        if batch_recent_data is None or len(historical_periods_data) == 0:
            return {}
        
        # 支持多股票和单股票模式
        if self.is_multi_stock:
            num_stocks, evaluation_days, window_size, num_fields = batch_recent_data.shape
            self.logger.info(f"开始多股票批量GPU相关性计算")
            self.logger.info(f"股票数: {num_stocks}, 评测日期数: {evaluation_days}, 历史期间数: {len(historical_periods_data)}")
        else:
            evaluation_days, window_size, num_fields = batch_recent_data.shape
            num_stocks = 1
            self.logger.info(f"开始单股票批量GPU相关性计算")
            self.logger.info(f"评测日期数: {evaluation_days}, 历史期间数: {len(historical_periods_data)}")
        
        num_historical_periods = len(historical_periods_data)
        
        # 子步骤1/5: 历史数据准备（已优化：数据在阶段3已预处理）
        self.start_timer('gpu_step1_data_preparation')
        self.logger.info(f"  🔍 [子步骤1/5] 历史数据准备（已优化） - 开始")
        
        # 数据已在阶段3预处理，直接提取
        historical_data_list = []
        period_info_list = []
        
        for historical_values, start_date, end_date, stock_code in historical_periods_data:
            historical_data_list.append(historical_values)
            period_info_list.append({
                'start_date': start_date,
                'end_date': end_date,
                'stock_code': stock_code
            })
        
        valid_periods = len(historical_data_list)
        self.logger.info(f"历史数据准备完成: 有效期间={valid_periods}（数据已在阶段3预处理）")
        self.end_timer('gpu_step1_data_preparation')
        self.logger.info(f"  🔍 [子步骤1/5] 历史数据准备（已优化） - 完成")
        
        if not historical_data_list:
            self.logger.warning("没有有效的历史期间数据")
            return {}
        
        # 子步骤2/5: 创建GPU历史数据张量
        self.start_timer('gpu_step2_tensor_creation')
        self.logger.info(f"  📊 [子步骤2/5] 创建GPU历史数据张量 - 开始")
        self.logger.info(f"张量形状将为: [{len(historical_data_list)}, {window_size}, 5]")
        
        historical_tensor = torch.tensor(
            np.stack(historical_data_list, axis=0), 
            dtype=torch.float32, 
            device=self.device
        )  # [num_historical_periods, window_size, 5]
        
        self.logger.info(f"GPU历史数据张量创建完成: {historical_tensor.shape}, 设备: {historical_tensor.device}")
        self.end_timer('gpu_step2_tensor_creation')
        self.logger.info(f"  📊 [子步骤2/5] 创建GPU历史数据张量 - 完成")
        
        # 监控数据张量创建后的GPU显存
        self.monitor_gpu_memory("张量创建完成")
        
        # 子步骤3/5: 批量相关系数计算
        self.start_timer('gpu_step3_correlation_calculation')
        self.logger.info(f"  ⚡ [子步骤3/5] 批量相关系数计算 - 开始")
        self.logger.info(f"输入张量形状: batch_recent_data={batch_recent_data.shape}, historical_tensor={historical_tensor.shape}")
        
        if self.is_multi_stock:
            self.logger.info(f"目标输出形状: [{num_stocks}, {evaluation_days}, {historical_tensor.shape[0]}, 5]")
        else:
            self.logger.info(f"目标输出形状: [{evaluation_days}, {historical_tensor.shape[0]}, 5]")
        
        batch_correlations = []
        
        # 分批处理以避免内存溢出
        batch_size = min(self.batch_size, evaluation_days)
        total_batches = (evaluation_days + batch_size - 1) // batch_size
        
        self.logger.info(f"分批计算配置: batch_size={batch_size}, total_batches={total_batches}")
        
        for batch_idx, i in enumerate(range(0, evaluation_days, batch_size)):
            end_idx = min(i + batch_size, evaluation_days)
            
            if self.is_multi_stock:
                # 多股票模式: [num_stocks, batch_size, window_size, 5]
                current_batch = batch_recent_data[:, i:end_idx]
                self.logger.info(f"处理批次 {batch_idx + 1}/{total_batches}: 评测日期 {i+1}-{end_idx} (形状: {current_batch.shape})")
                
                # 为每个股票计算相关系数
                stock_batch_correlations = []
                for stock_idx in range(num_stocks):
                    stock_batch = current_batch[stock_idx]  # [batch_size, window_size, 5]
                    stock_corr = self._compute_correlation_matrix(stock_batch, historical_tensor)
                    stock_batch_correlations.append(stock_corr)
                
                # 合并所有股票的结果: [num_stocks, batch_size, num_historical_periods, 5]
                multi_stock_batch_corr = torch.stack(stock_batch_correlations, dim=0)
                batch_correlations.append(multi_stock_batch_corr)
            else:
                # 单股票模式: [batch_size, window_size, 5]
                current_batch = batch_recent_data[i:end_idx]
                self.logger.info(f"处理批次 {batch_idx + 1}/{total_batches}: 评测日期 {i+1}-{end_idx} (形状: {current_batch.shape})")
                
                # 计算当前批次的相关系数
                batch_corr = self._compute_correlation_matrix(current_batch, historical_tensor)
                batch_correlations.append(batch_corr)
            
            # 监控每个批次后的GPU显存
            if batch_idx % max(1, total_batches // 5) == 0:  # 每20%进度监控一次
                self.monitor_gpu_memory(f"批次{batch_idx + 1}完成")
        
        self.end_timer('gpu_step3_correlation_calculation')
        self.logger.info(f"  ⚡ [子步骤3/5] 批量相关系数计算 - 完成")
        
        # 子步骤4/5: 合并批次结果
        self.start_timer('gpu_step4_batch_merging')
        self.logger.info(f"  🔗 [子步骤4/5] 合并批次结果 - 开始")
        
        if self.is_multi_stock:
            # 多股票模式: 合并所有批次的结果
            # batch_correlations中每个元素形状: [num_stocks, batch_size, num_historical_periods, 5]
            # 需要在第二个维度（evaluation_days维度）上合并
            all_correlations = torch.cat(batch_correlations, dim=1)  # [num_stocks, evaluation_days, num_historical_periods, 5]
            self.logger.info(f"多股票批次结果合并完成: 最终形状={all_correlations.shape}")
        else:
            # 单股票模式: 合并所有批次的结果
            all_correlations = torch.cat(batch_correlations, dim=0)  # [evaluation_days, num_historical_periods, 5]
            self.logger.info(f"单股票批次结果合并完成: 最终形状={all_correlations.shape}")
        
        self.end_timer('gpu_step4_batch_merging')
        self.logger.info(f"  🔗 [子步骤4/5] 合并批次结果 - 完成")
        
        # 监控相关系数计算完成后的GPU显存
        self.monitor_gpu_memory("相关系数计算完成")
        
        self.logger.info(f"批量GPU相关性计算完成，结果形状: {all_correlations.shape}")
        
        # 子步骤5/5: 处理批量相关性结果
        self.start_timer('gpu_step5_result_processing')
        self.logger.info(f"  📋 [子步骤5/5] 处理批量相关性结果 - 开始")
        self.logger.info(f"调用函数: _process_batch_correlation_results")
        
        # 传递股票代码信息
        if self.is_multi_stock:
            # 从analyze_batch方法传递的stock_codes参数获取
            # 这里需要从调用栈中获取stock_codes，暂时使用self.stock_codes
            target_stock_codes = self.stock_codes
        else:
            target_stock_codes = [self.stock_code]
        
        results = self._process_batch_correlation_results(
            all_correlations, period_info_list, evaluation_days,
            batch_recent_data, historical_data_list, evaluation_dates,
            target_stock_codes
        )
        self.end_timer('gpu_step5_result_processing')
        self.logger.info(f"  📋 [子步骤5/5] 处理批量相关性结果 - 完成")
        
        self.logger.info(f"批量GPU相关性计算全部完成，返回结果包含 {len(results) if results else 0} 个字段")
        return results
    
    def _compute_correlation_matrix(self, recent_batch, historical_tensor):
        """
        计算相关系数矩阵
        
        Args:
            recent_batch: [batch_size, window_size, 5]
            historical_tensor: [num_historical_periods, window_size, 5]
            
        Returns:
            torch.Tensor: [batch_size, num_historical_periods, 5]
        """
        batch_size, window_size, num_fields = recent_batch.shape
        num_historical_periods = historical_tensor.shape[0]
        
        if self.debug:
            self.logger.debug(f"    [GPU计算] 开始相关系数矩阵计算 - _compute_correlation_matrix")
            self.logger.debug(f"    输入形状: recent_batch={recent_batch.shape}, historical_tensor={historical_tensor.shape}")
        
        # 扩展维度进行广播计算
        if self.debug:
            self.logger.debug(f"    [GPU计算] 步骤1: 扩展维度进行广播")
        recent_expanded = recent_batch.unsqueeze(1)  # [batch_size, 1, window_size, 5]
        historical_expanded = historical_tensor.unsqueeze(0)  # [1, num_historical_periods, window_size, 5]
        
        # 计算均值
        if self.debug:
            self.logger.debug(f"    [GPU计算] 步骤2: 计算均值")
        recent_mean = recent_expanded.mean(dim=2, keepdim=True)  # [batch_size, 1, 1, 5]
        historical_mean = historical_expanded.mean(dim=2, keepdim=True)  # [1, num_historical_periods, 1, 5]
        
        # 中心化
        if self.debug:
            self.logger.debug(f"    [GPU计算] 步骤3: 数据中心化")
        recent_centered = recent_expanded - recent_mean
        historical_centered = historical_expanded - historical_mean
        
        # 计算协方差
        if self.debug:
            self.logger.debug(f"    [GPU计算] 步骤4: 计算协方差")
        covariance = (recent_centered * historical_centered).sum(dim=2)  # [batch_size, num_historical_periods, 5]
        
        # 计算标准差
        if self.debug:
            self.logger.debug(f"    [GPU计算] 步骤5: 计算标准差")
        recent_std = torch.sqrt((recent_centered ** 2).sum(dim=2))  # [batch_size, 1, 5]
        historical_std = torch.sqrt((historical_centered ** 2).sum(dim=2))  # [1, num_historical_periods, 5]
        
        # 计算相关系数
        if self.debug:
            self.logger.debug(f"    [GPU计算] 步骤6: 计算最终相关系数")
        correlation = covariance / (recent_std * historical_std + 1e-8)
        
        if self.debug:
            self.logger.debug(f"    [GPU计算] 相关系数计算完成，输出形状: {correlation.shape}")
        
        return correlation

    def _compute_correlation_matrix_multi_stock(self, recent_batch, historical_tensor):
        """
        计算多股票相关系数矩阵
        
        Args:
            recent_batch: [num_stocks, batch_size, window_size, 5]
            historical_tensor: [num_historical_periods, window_size, 5]
            
        Returns:
            torch.Tensor: [num_stocks, batch_size, num_historical_periods, 5]
        """
        num_stocks, batch_size, window_size, num_fields = recent_batch.shape
        num_historical_periods = historical_tensor.shape[0]
        
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 开始相关系数矩阵计算 - _compute_correlation_matrix_multi_stock")
            self.logger.debug(f"    输入形状: recent_batch={recent_batch.shape}, historical_tensor={historical_tensor.shape}")
        
        # 扩展维度进行广播计算
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 步骤1: 扩展维度进行广播")
        recent_expanded = recent_batch.unsqueeze(2)  # [num_stocks, batch_size, 1, window_size, 5]
        historical_expanded = historical_tensor.unsqueeze(0).unsqueeze(0)  # [1, 1, num_historical_periods, window_size, 5]
        
        # 计算均值
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 步骤2: 计算均值")
        recent_mean = recent_expanded.mean(dim=3, keepdim=True)  # [num_stocks, batch_size, 1, 1, 5]
        historical_mean = historical_expanded.mean(dim=3, keepdim=True)  # [1, 1, num_historical_periods, 1, 5]
        
        # 中心化
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 步骤3: 数据中心化")
        recent_centered = recent_expanded - recent_mean
        historical_centered = historical_expanded - historical_mean
        
        # 计算协方差
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 步骤4: 计算协方差")
        covariance = (recent_centered * historical_centered).sum(dim=3)  # [num_stocks, batch_size, num_historical_periods, 5]
        
        # 计算标准差
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 步骤5: 计算标准差")
        recent_std = torch.sqrt((recent_centered ** 2).sum(dim=3))  # [num_stocks, batch_size, 1, 5]
        historical_std = torch.sqrt((historical_centered ** 2).sum(dim=3))  # [1, 1, num_historical_periods, 5]
        
        # 计算相关系数
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 步骤6: 计算最终相关系数")
        correlation = covariance / (recent_std * historical_std + 1e-8)
        
        if self.debug:
            self.logger.debug(f"    [GPU多股票计算] 相关系数计算完成，输出形状: {correlation.shape}")
        
        return correlation
    
    def _process_single_stock_results(self, stock_correlations, avg_correlations_filtered, high_corr_mask,
                                     period_info_list, evaluation_dates, stock_code, fields):
        """
        处理单个股票的相关性结果
        
        Args:
            stock_correlations: 单个股票的相关性数据 [evaluation_days, num_historical_periods, 5]
            avg_correlations_filtered: 过滤后的平均相关系数 [evaluation_days, num_historical_periods]
            high_corr_mask: 高相关性掩码
            period_info_list: 历史期间信息列表
            evaluation_dates: 评测日期列表
            stock_code: 股票代码
            fields: 字段列表
            
        Returns:
            list: 详细结果列表
        """
        detailed_results = []
        
        if evaluation_dates:
            for eval_idx, eval_date in enumerate(evaluation_dates):
                if eval_idx < avg_correlations_filtered.shape[0]:
                    eval_correlations = avg_correlations_filtered[eval_idx]  # 该评测日期的相关性列表
                    
                    # 找到高相关性期间
                    high_corr_periods = []
                    for hist_idx, correlation in enumerate(eval_correlations):
                        if correlation >= self.threshold and hist_idx < len(period_info_list):
                            period_data = period_info_list[hist_idx]
                            
                            high_corr_periods.append({
                                'start_date': period_data['start_date'],
                                'end_date': period_data['end_date'],
                                'avg_correlation': float(correlation),
                                'stock_code': period_data['stock_code'],
                                'target_stock_code': stock_code,  # 添加目标股票代码
                                'source': 'gpu_batch'
                            })
                    
                    # 计算该评测日期的预测统计（如果有数据的话）
                    stats = {}
                    if hasattr(self, 'data') and stock_code == self.stock_code:
                        # 只有当前股票才计算预测统计
                        stats = self.calculate_future_performance_stats(self.data, high_corr_periods)
                    elif hasattr(self, 'multi_stock_data') and stock_code in self.multi_stock_data:
                        # 多股票模式下计算对应股票的预测统计
                        stats = self.calculate_future_performance_stats(self.multi_stock_data[stock_code], high_corr_periods)
                    
                    detailed_results.append({
                        'evaluation_date': eval_date,
                        'target_stock_code': stock_code,  # 添加目标股票代码
                        'high_correlation_periods': high_corr_periods,
                        'daily_high_count': len(high_corr_periods),
                        'prediction_stats': stats
                    })
        
        return detailed_results

    def _process_batch_correlation_results(self, correlations_tensor, period_info_list, evaluation_days,
                                          batch_recent_data=None, historical_data_list=None, evaluation_dates=None,
                                          target_stock_codes=None):
        """
        处理批量相关性计算结果（整合了阶段5的详细结果处理和保存功能），支持多股票
        
        Args:
            correlations_tensor: [evaluation_days, num_historical_periods, 5] (单股票)
                                或 [num_stocks, evaluation_days, num_historical_periods, 5] (多股票)
            period_info_list: 历史期间信息列表
            evaluation_days: 评测日期数量
            evaluation_dates: 评测日期列表
            target_stock_codes: 目标股票代码列表
            
        Returns:
            dict: 处理后的完整最终结果，包含详细结果、统计信息和性能数据
        """
        # 使用统一的计时器，覆盖原来的4-5和5-1步骤
        self.start_timer('integrated_result_processing')
        
        correlations_np = correlations_tensor.cpu().numpy()
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        # 确保target_stock_codes有值
        if target_stock_codes is None:
            target_stock_codes = [self.stock_code] if not self.is_multi_stock else self.stock_codes
        
        # 支持多股票和单股票模式
        if self.is_multi_stock:
            # 多股票模式: correlations_np形状为 [num_stocks, evaluation_days, num_historical_periods, 5]
            num_stocks = correlations_np.shape[0]
            self.logger.info(f"处理多股票相关性结果: {num_stocks}只股票, {evaluation_days}个评测日期")
            
            # 为每个股票分别处理
            all_stock_results = {}
            all_detailed_results = []
            
            for stock_idx, stock_code in enumerate(target_stock_codes):
                self.logger.info(f"处理股票 {stock_code} ({stock_idx + 1}/{num_stocks})")
                
                # 提取当前股票的相关性数据 [evaluation_days, num_historical_periods, 5]
                stock_correlations = correlations_np[stock_idx]
                
                # 计算平均相关系数 [evaluation_days, num_historical_periods]
                avg_correlations = stock_correlations.mean(axis=2)
                
                # 过滤掉相关性为1.0的结果（自相关）
                self_correlation_threshold = 0.9999
                self_correlation_mask = avg_correlations >= self_correlation_threshold
                
                # 统计被过滤的自相关数量
                filtered_count = self_correlation_mask.sum()
                if filtered_count > 0:
                    self.logger.info(f"股票 {stock_code}: 过滤掉 {filtered_count} 个自相关结果（相关性 >= {self_correlation_threshold}）")
                
                # 将自相关的位置设置为0，使其不会被选为高相关性期间
                avg_correlations_filtered = avg_correlations.copy()
                avg_correlations_filtered[self_correlation_mask] = 0.0
                
                # 找出高相关性期间（使用过滤后的相关系数）
                high_corr_mask = avg_correlations_filtered > self.threshold
                
                # 处理当前股票的详细结果
                stock_detailed_results = self._process_single_stock_results(
                    stock_correlations, avg_correlations_filtered, high_corr_mask,
                    period_info_list, evaluation_dates, stock_code, fields
                )
                
                all_detailed_results.extend(stock_detailed_results)
                all_stock_results[stock_code] = {
                    'high_corr_count': high_corr_mask.sum(),
                    'avg_correlation': avg_correlations_filtered[avg_correlations_filtered > 0].mean() if (avg_correlations_filtered > 0).any() else 0.0,
                    'max_correlation': avg_correlations_filtered.max()
                }
            
            # 汇总多股票结果
            total_high_corr = sum(result['high_corr_count'] for result in all_stock_results.values())
            overall_avg_corr = np.mean([result['avg_correlation'] for result in all_stock_results.values() if result['avg_correlation'] > 0])
            overall_max_corr = max([result['max_correlation'] for result in all_stock_results.values()])
            
        else:
            # 单股票模式: 保持原有逻辑
            # 计算平均相关系数 [evaluation_days, num_historical_periods]
            avg_correlations = correlations_np.mean(axis=2)
            
            # 过滤掉相关性为1.0的结果（自相关）
            # 设置容差，避免浮点数精度问题
            self_correlation_threshold = 0.9999
            self_correlation_mask = avg_correlations >= self_correlation_threshold
            
            # 统计被过滤的自相关数量
            filtered_count = self_correlation_mask.sum()
            if filtered_count > 0:
                self.logger.info(f"过滤掉 {filtered_count} 个自相关结果（相关性 >= {self_correlation_threshold}）")
            
            # 将自相关的位置设置为0，使其不会被选为高相关性期间
            avg_correlations_filtered = avg_correlations.copy()
            avg_correlations_filtered[self_correlation_mask] = 0.0
            
            # 找出高相关性期间（使用过滤后的相关系数）
            high_corr_mask = avg_correlations_filtered > self.threshold
            
            # 处理单股票的详细结果
            all_detailed_results = self._process_single_stock_results(
                correlations_np, avg_correlations_filtered, high_corr_mask,
                period_info_list, evaluation_dates, target_stock_codes[0], fields
            )
            
            total_high_corr = high_corr_mask.sum()
            overall_avg_corr = avg_correlations_filtered[avg_correlations_filtered > 0].mean() if (avg_correlations_filtered > 0).any() else 0.0
            overall_max_corr = avg_correlations_filtered.max()
        
        # Debug模式下打印前10条评测数据的详细信息
        if self.debug and not self.is_multi_stock:
            # 单股票模式下才打印详细信息，多股票模式下信息太多
            self._print_detailed_evaluation_data(
                correlations_np, avg_correlations_filtered, period_info_list, 
                high_corr_mask, fields, batch_recent_data, historical_data_list, evaluation_dates
            )
        
        # 构建批量结果（支持多股票模式）
        if self.is_multi_stock:
            # 多股票模式：汇总所有股票的结果
            batch_results = {
                'evaluation_days': evaluation_days,
                'num_historical_periods': len(period_info_list),
                'stock_codes': target_stock_codes,
                'detailed_results': detailed_results,  # 包含所有股票的详细结果
                'summary': {
                    'total_stocks': len(target_stock_codes),
                    'total_high_correlations': sum(result.get('total_high_correlations', 0) for result in detailed_results),
                    'avg_high_correlations_per_stock': sum(result.get('total_high_correlations', 0) for result in detailed_results) / len(target_stock_codes) if target_stock_codes else 0,
                    'filtered_self_correlations': int(filtered_count)
                }
            }
        else:
            # 单股票模式：保持原有格式
            batch_results = {
                'evaluation_days': evaluation_days,
                'num_historical_periods': len(period_info_list),
                'high_correlation_counts': high_corr_mask.sum(axis=1).tolist(),  # 每个评测日期的高相关数量
                'avg_correlations': avg_correlations_filtered.tolist(),  # 使用过滤后的相关系数
                'detailed_correlations': correlations_np.tolist(),
                'period_info': period_info_list,
                'detailed_results': detailed_results,  # 新增：详细结果（整合阶段5功能）
                'summary': {
                    'total_high_correlations': high_corr_mask.sum(),
                    'avg_high_correlations_per_day': high_corr_mask.sum(axis=1).mean(),
                    'max_high_correlations_per_day': high_corr_mask.sum(axis=1).max(),
                    'overall_avg_correlation': avg_correlations_filtered[high_corr_mask].mean() if high_corr_mask.any() else 0,
                    'filtered_self_correlations': int(filtered_count)  # 添加过滤统计
                }
            }
        
        # 整合原阶段5的功能：构建最终结果并保存
        final_result = {
            'stock_code': self.stock_code if not self.is_multi_stock else ','.join(target_stock_codes),
            'backtest_date': self.backtest_date,
            'evaluation_days': len(evaluation_dates) if evaluation_dates else evaluation_days,
            'window_size': self.window_size,
            'threshold': self.threshold,
            'evaluation_dates': evaluation_dates if evaluation_dates else [],
            'batch_results': batch_results,
            'performance_stats': self._get_performance_stats(),
            'is_multi_stock': self.is_multi_stock
        }
        
        # 保存结果到CSV（原阶段5的功能）
        if getattr(self, 'save_results', True):  # 默认为True，确保CSV保存功能正常工作
            self.logger.info("开始保存批量结果到CSV文件...")
            self.save_batch_results_to_csv(final_result)
        else:
            self.logger.warning("CSV保存功能已禁用，跳过保存步骤")
        
        self.logger.info(f"批量结果处理完成（已整合详细结果处理和保存功能）")
        self.logger.info(f"总高相关性期间: {batch_results['summary']['total_high_correlations']}")
        self.logger.info(f"平均每日高相关数: {batch_results['summary']['avg_high_correlations_per_day']:.2f}")
        
        self.end_timer('integrated_result_processing')
        return final_result

    def calculate_batch_gpu_correlation_optimized(self, batch_recent_data, historical_periods_data, evaluation_dates=None):
        """
        优化版批量GPU相关性计算 - 支持多目标股票同时处理
        
        Args:
            batch_recent_data: 批量评测数据 
                - 单股票模式: [evaluation_days, window_size, 5]
                - 多股票模式: [num_stocks, evaluation_days, window_size, 5]
            historical_periods_data: 历史期间数据列表
            evaluation_dates: 评测日期列表
            
        Returns:
            dict: 批量相关性结果
        """
        
        if batch_recent_data is None or len(historical_periods_data) == 0:
            return {}

        # 使用传参判断模式，不依赖矩阵形状
        is_multi_stock = self.is_multi_stock
        if is_multi_stock:
            # 多股票模式: [num_stocks, evaluation_days, window_size, 5]
            num_stocks, evaluation_days, window_size, num_fields = batch_recent_data.shape
            self.logger.info(f"多股票模式: {num_stocks} 个股票")
        else:
            # 单股票模式: 可能是 [evaluation_days, window_size, 5] 或已转换的 [1, evaluation_days, window_size, 5]
            if len(batch_recent_data.shape) == 3:
                evaluation_days, window_size, num_fields = batch_recent_data.shape
                # 为了统一处理，将单股票数据扩展一个维度
                batch_recent_data = batch_recent_data.unsqueeze(0)  # [1, evaluation_days, window_size, 5]
                self.logger.info(f"单股票模式，已转换为统一格式")
            else:
                # 已经是4维格式 [1, evaluation_days, window_size, 5]
                num_stocks, evaluation_days, window_size, num_fields = batch_recent_data.shape
                self.logger.info(f"单股票模式（已为统一格式）")
            num_stocks = 1
        
        num_historical_periods = len(historical_periods_data)
        
        self.logger.info(f"开始优化版批量GPU相关性计算")
        self.logger.info(f"股票数: {num_stocks}, 评测日期数: {evaluation_days}, 历史期间数: {num_historical_periods}")
        
        # 子步骤1/3: 历史数据准备（已优化：数据在阶段3已预处理）
        self.start_timer('gpu_step1_data_preparation')
        self.logger.info(f"  🔍 [子步骤1/3] 历史数据准备（已优化） - 开始")
        
        # 数据已在阶段3预处理，直接提取
        historical_data_list = []
        period_info_list = []
        
        for historical_values, start_date, end_date, stock_code in historical_periods_data:
            historical_data_list.append(historical_values)
            period_info_list.append({
                'start_date': start_date,
                'end_date': end_date,
                'stock_code': stock_code
            })
        
        valid_periods = len(historical_data_list)
        self.logger.info(f"历史数据准备完成: 有效期间={valid_periods}（数据已在阶段3预处理）")
        self.end_timer('gpu_step1_data_preparation')
        self.logger.info(f"  🔍 [子步骤1/3] 历史数据准备（已优化） - 完成")
        
        if not historical_data_list:
            self.logger.warning("没有有效的历史期间数据")
            return {}
        
        # 子步骤2/3: 创建GPU历史数据张量
        self.start_timer('gpu_step2_tensor_creation')
        self.logger.info(f"  📊 [子步骤2/3] 创建GPU历史数据张量 - 开始")
        self.logger.info(f"张量形状将为: [{len(historical_data_list)}, {window_size}, 5]")
        
        historical_tensor = torch.tensor(
            np.stack(historical_data_list, axis=0), 
            dtype=torch.float32, 
            device=self.device
        )  # [num_historical_periods, window_size, 5]
        
        self.logger.info(f"GPU历史数据张量创建完成: {historical_tensor.shape}, 设备: {historical_tensor.device}")
        self.end_timer('gpu_step2_tensor_creation')
        self.logger.info(f"  📊 [子步骤2/3] 创建GPU历史数据张量 - 完成")
        
        # 监控数据张量创建后的GPU显存
        self.monitor_gpu_memory("张量创建完成")
        
        # 子步骤3/3: 合并的GPU相关系数计算和结果处理
        self.start_timer('gpu_step3_integrated_correlation_processing')
        self.logger.info(f"  ⚡ [子步骤3/3] 合并的GPU相关系数计算和结果处理 - 开始")
        self.logger.info(f"输入张量形状: batch_recent_data={batch_recent_data.shape}, historical_tensor={historical_tensor.shape}")
        
        # 使用优化的GPU端一体化处理
        results = self._compute_and_process_correlations_gpu(
            batch_recent_data, historical_tensor, period_info_list, 
            evaluation_days, evaluation_dates, num_stocks, is_multi_stock
        )
        
        self.end_timer('gpu_step3_integrated_correlation_processing')
        self.logger.info(f"  ⚡ [子步骤3/3] 合并的GPU相关系数计算和结果处理 - 完成")
        
        self.logger.info(f"优化版批量GPU相关性计算全部完成，返回结果包含 {len(results) if results else 0} 个字段")
        return results

    def _calculate_batch_gpu_correlation_no_timer(self, batch_recent_data, historical_periods_data, evaluation_dates=None):
        """
        批量GPU相关性计算（不带计时器版本）- 用于多股票分批处理
        
        Args:
            batch_recent_data: 批量评测数据
            historical_periods_data: 历史期间数据列表
            evaluation_dates: 评测日期列表
            
        Returns:
            dict: 批量相关性结果
        """
        
        if batch_recent_data is None or len(historical_periods_data) == 0:
            return {}
        
        # 使用传参判断模式，不依赖矩阵形状
        is_multi_stock = self.is_multi_stock
        if is_multi_stock:
            # 多股票模式: [num_stocks, evaluation_days, window_size, 5]
            num_stocks, evaluation_days, window_size, num_fields = batch_recent_data.shape
        else:
            # 单股票模式: 可能是 [evaluation_days, window_size, 5] 或已转换的 [1, evaluation_days, window_size, 5]
            if len(batch_recent_data.shape) == 3:
                evaluation_days, window_size, num_fields = batch_recent_data.shape
                # 为了统一处理，将单股票数据扩展一个维度
                batch_recent_data = batch_recent_data.unsqueeze(0)  # [1, evaluation_days, window_size, 5]
            else:
                # 已经是4维格式 [1, evaluation_days, window_size, 5]
                num_stocks, evaluation_days, window_size, num_fields = batch_recent_data.shape
            num_stocks = 1
        
        num_historical_periods = len(historical_periods_data)
        
        # 历史数据准备（不计时）
        historical_data_list = []
        period_info_list = []
        
        for historical_values, start_date, end_date, stock_code in historical_periods_data:
            historical_data_list.append(historical_values)
            period_info_list.append({
                'start_date': start_date,
                'end_date': end_date,
                'stock_code': stock_code
            })
        
        if not historical_data_list:
            return {}
        
        # 创建GPU历史数据张量（不计时）
        historical_tensor = torch.tensor(
            np.stack(historical_data_list, axis=0), 
            dtype=torch.float32, 
            device=self.device
        )  # [num_historical_periods, window_size, 5]
        
        # GPU相关系数计算和结果处理（不计时）
        results = self._compute_and_process_correlations_gpu(
            batch_recent_data, historical_tensor, period_info_list, 
            evaluation_days, evaluation_dates, num_stocks, is_multi_stock
        )
        
        return results

    def _compute_and_process_correlations_gpu(self, batch_recent_data, historical_tensor, 
                                            period_info_list, evaluation_days, evaluation_dates, 
                                            num_stocks, is_multi_stock):
        """
        GPU端一体化相关系数计算和结果处理 - 支持多股票
        
        Args:
            batch_recent_data: [num_stocks, evaluation_days, window_size, 5]
            historical_tensor: [num_historical_periods, window_size, 5]
            period_info_list: 历史期间信息列表
            evaluation_days: 评测日期数量
            evaluation_dates: 评测日期列表
            num_stocks: 股票数量
            is_multi_stock: 是否为多股票模式
            
        Returns:
            dict: 处理后的完整最终结果
        """
        # 分批处理以避免内存溢出
        batch_size = min(self.batch_size, evaluation_days)
        total_batches = (evaluation_days + batch_size - 1) // batch_size
        
        self.logger.info(f"GPU一体化处理配置: batch_size={batch_size}, total_batches={total_batches}")
        self.logger.info(f"多股票处理: {num_stocks} 个股票同时处理")
        
        # GPU端存储所有结果 - 支持多股票
        all_avg_correlations = []  # 每个元素: [num_stocks, batch_size, num_historical_periods]
        all_high_corr_masks = []   # 每个元素: [num_stocks, batch_size, num_historical_periods]
        all_high_corr_counts = []  # 每个元素: [num_stocks, batch_size]
        
        # 创建阈值张量（在GPU上）
        threshold_tensor = torch.tensor(self.threshold, device=self.device, dtype=torch.float32)
        self_correlation_threshold = torch.tensor(0.9999, device=self.device, dtype=torch.float32)
        
        for batch_idx, i in enumerate(range(0, evaluation_days, batch_size)):
            end_idx = min(i + batch_size, evaluation_days)
            current_batch = batch_recent_data[:, i:end_idx]  # [num_stocks, batch_size, window_size, 5]
            
            self.logger.info(f"GPU处理批次 {batch_idx + 1}/{total_batches}: 评测日期 {i+1}-{end_idx} (形状: {current_batch.shape})")
            
            # 计算当前批次的相关系数 - 支持多股票
            batch_correlations = self._compute_correlation_matrix_multi_stock(current_batch, historical_tensor)
            # batch_correlations: [num_stocks, batch_size, num_historical_periods, 5]
            
            # GPU端计算平均相关系数
            batch_avg_correlations = batch_correlations.mean(dim=3)  # [num_stocks, batch_size, num_historical_periods]
            
            # GPU端过滤自相关（相关性 >= 0.9999）
            self_corr_mask = batch_avg_correlations >= self_correlation_threshold
            batch_avg_correlations_filtered = batch_avg_correlations.clone()
            batch_avg_correlations_filtered[self_corr_mask] = 0.0
            
            # GPU端计算高相关性掩码
            batch_high_corr_mask = batch_avg_correlations_filtered > threshold_tensor
            
            # GPU端计算每个评测日期的高相关数量
            batch_high_corr_counts = batch_high_corr_mask.sum(dim=2)  # [num_stocks, batch_size]
            
            # 🔍 Debug模式：为第一个评测日期打印详细信息
            if self.debug and batch_idx == 0 and evaluation_dates and len(evaluation_dates) > 0:
                self._log_first_evaluation_debug_info(
                    batch_avg_correlations_filtered, batch_high_corr_mask, 
                    period_info_list, evaluation_dates, current_batch, historical_tensor, i, is_multi_stock
                )
            
            # 存储批次结果（仍在GPU上）
            all_avg_correlations.append(batch_avg_correlations_filtered)
            all_high_corr_masks.append(batch_high_corr_mask)
            all_high_corr_counts.append(batch_high_corr_counts)
            
            # 监控每个批次后的GPU显存
            if batch_idx % max(1, total_batches // 5) == 0:  # 每20%进度监控一次
                self.monitor_gpu_memory(f"GPU批次{batch_idx + 1}完成")
        
        # 合并所有批次的结果（仍在GPU上）- 支持多股票
        all_avg_correlations_tensor = torch.cat(all_avg_correlations, dim=1)  # [num_stocks, evaluation_days, num_historical_periods]
        all_high_corr_masks_tensor = torch.cat(all_high_corr_masks, dim=1)    # [num_stocks, evaluation_days, num_historical_periods]
        all_high_corr_counts_tensor = torch.cat(all_high_corr_counts, dim=1)  # [num_stocks, evaluation_days]
        
        # GPU端计算全局统计 - 支持多股票
        if is_multi_stock:
            # 多股票模式：计算所有股票的总体统计
            total_high_correlations = all_high_corr_masks_tensor.sum()
            
            # 检查张量是否为空，避免空张量调用统计方法
            if all_high_corr_counts_tensor.numel() > 0:
                avg_high_correlations_per_day = all_high_corr_counts_tensor.float().mean()
                max_high_correlations_per_day = all_high_corr_counts_tensor.max()
            else:
                avg_high_correlations_per_day = torch.tensor(0.0, device=self.device)
                max_high_correlations_per_day = torch.tensor(0, device=self.device)
            
            # 计算每个股票的统计信息
            stock_summary = {}
            for stock_idx in range(num_stocks):
                stock_code = self.stock_codes[stock_idx] if hasattr(self, 'stock_codes') and stock_idx < len(self.stock_codes) else f"stock_{stock_idx}"
                stock_high_corr_count = all_high_corr_masks_tensor[stock_idx].sum()
                stock_high_corr_values = all_avg_correlations_tensor[stock_idx][all_high_corr_masks_tensor[stock_idx]]
                stock_avg_correlation = stock_high_corr_values.mean() if stock_high_corr_values.numel() > 0 else torch.tensor(0.0, device=self.device)
                
                stock_summary[stock_code] = {
                    'high_correlations': int(stock_high_corr_count.item()),
                    'avg_correlation': float(stock_avg_correlation.item())
                }
        else:
            # 单股票模式：保持原有逻辑
            all_avg_correlations_tensor = all_avg_correlations_tensor.squeeze(0)  # [evaluation_days, num_historical_periods]
            all_high_corr_masks_tensor = all_high_corr_masks_tensor.squeeze(0)    # [evaluation_days, num_historical_periods]
            all_high_corr_counts_tensor = all_high_corr_counts_tensor.squeeze(0)  # [evaluation_days]
            
            total_high_correlations = all_high_corr_masks_tensor.sum()
            
            # 检查张量是否为空，避免空张量调用统计方法
            if all_high_corr_counts_tensor.numel() > 0:
                avg_high_correlations_per_day = all_high_corr_counts_tensor.float().mean()
                max_high_correlations_per_day = all_high_corr_counts_tensor.max()
            else:
                avg_high_correlations_per_day = torch.tensor(0.0, device=self.device)
                max_high_correlations_per_day = torch.tensor(0, device=self.device)
            stock_summary = None
        
        # 计算整体平均相关系数（只对高相关性的）
        high_corr_values = all_avg_correlations_tensor[all_high_corr_masks_tensor]
        overall_avg_correlation = high_corr_values.mean() if high_corr_values.numel() > 0 else torch.tensor(0.0, device=self.device)
        
        self.logger.info(f"GPU端统计完成 - 总高相关数: {total_high_correlations.item()}, "
                        f"平均每日高相关数: {avg_high_correlations_per_day.item():.2f}")
        
        # 只在需要详细结果时才传输到CPU - 支持多股票
        if evaluation_dates and len(evaluation_dates) > 0:
            # 传输必要的数据到CPU进行详细结果构建
            avg_correlations_cpu = all_avg_correlations_tensor.cpu().numpy()
            high_corr_masks_cpu = all_high_corr_masks_tensor.cpu().numpy()
            
            if is_multi_stock:
                # 多股票模式：为每个股票构建详细结果
                detailed_results = {}
                for stock_idx in range(num_stocks):
                    stock_code = self.stock_codes[stock_idx] if hasattr(self, 'stock_codes') and stock_idx < len(self.stock_codes) else f"stock_{stock_idx}"
                    stock_avg_correlations = avg_correlations_cpu[stock_idx]
                    stock_high_corr_masks = high_corr_masks_cpu[stock_idx]
                    
                    detailed_results[stock_code] = self._build_detailed_results_cpu(
                        stock_avg_correlations, stock_high_corr_masks, period_info_list, evaluation_dates
                    )
            else:
                # 单股票模式：保持原有逻辑
                detailed_results = self._build_detailed_results_cpu(
                    avg_correlations_cpu, high_corr_masks_cpu, period_info_list, evaluation_dates
                )
        else:
            detailed_results = {} if is_multi_stock else []
        
        # 构建最终结果（大部分数据已在GPU上计算完成）- 支持多股票
        batch_results = {
            'evaluation_days': evaluation_days,
            'num_historical_periods': len(period_info_list),
            'high_correlation_counts': all_high_corr_counts_tensor.cpu().tolist(),
            'avg_correlations': all_avg_correlations_tensor.cpu().tolist(),
            'period_info': period_info_list,
            'detailed_results': detailed_results,
            'summary': {
                'total_high_correlations': int(total_high_correlations.item()),
                'avg_high_correlations_per_day': float(avg_high_correlations_per_day.item()),
                'max_high_correlations_per_day': int(max_high_correlations_per_day.item()),
                'overall_avg_correlation': float(overall_avg_correlation.item()),
                'stock_summary': stock_summary  # 添加每个股票的统计信息
            }
        }
        
        # 构建最终结果 - 支持多股票
        if is_multi_stock:
            # 多股票模式：返回所有股票的结果
            final_result = {
                'stock_codes': self.stock_codes if hasattr(self, 'stock_codes') else [f"stock_{i}" for i in range(num_stocks)],
                'backtest_date': self.backtest_date,
                'evaluation_days': len(evaluation_dates) if evaluation_dates else evaluation_days,
                'window_size': self.window_size,
                'threshold': self.threshold,
                'evaluation_dates': evaluation_dates if evaluation_dates else [],
                'batch_results': batch_results,
                'performance_stats': self._get_performance_stats(),
                'is_multi_stock': True
            }
        else:
            # 单股票模式：保持原有结构
            final_result = {
                'stock_code': self.stock_code,
                'backtest_date': self.backtest_date,
                'evaluation_days': len(evaluation_dates) if evaluation_dates else evaluation_days,
                'window_size': self.window_size,
                'threshold': self.threshold,
                'evaluation_dates': evaluation_dates if evaluation_dates else [],
                'batch_results': batch_results,
                'performance_stats': self._get_performance_stats(),
                'is_multi_stock': False
            }
        
        # 保存结果到CSV
        if getattr(self, 'save_results', True):
            self.logger.info("开始保存优化版批量结果到CSV文件...")
            self.save_batch_results_to_csv(final_result)
        
        return final_result

    def _build_detailed_results_cpu(self, avg_correlations_cpu, high_corr_masks_cpu, 
                                   period_info_list, evaluation_dates):
        """
        在CPU上构建详细结果（仅在需要时调用）
        
        Args:
            avg_correlations_cpu: CPU上的平均相关系数 [evaluation_days, num_historical_periods]
            high_corr_masks_cpu: CPU上的高相关性掩码 [evaluation_days, num_historical_periods]
            period_info_list: 历史期间信息列表
            evaluation_dates: 评测日期列表
            
        Returns:
            list: 详细结果列表
        """
        detailed_results = []
        
        for eval_idx, eval_date in enumerate(evaluation_dates):
            if eval_idx < avg_correlations_cpu.shape[0]:
                eval_correlations = avg_correlations_cpu[eval_idx]
                eval_high_corr_mask = high_corr_masks_cpu[eval_idx]
                
                # 找到高相关性期间
                high_corr_periods = []
                high_corr_indices = np.where(eval_high_corr_mask)[0]
                
                for hist_idx in high_corr_indices:
                    if hist_idx < len(period_info_list):
                        period_data = period_info_list[hist_idx]
                        correlation = eval_correlations[hist_idx]
                        
                        high_corr_periods.append({
                            'start_date': period_data['start_date'],
                            'end_date': period_data['end_date'],
                            'avg_correlation': float(correlation),
                            'stock_code': period_data['stock_code'],
                            'source': 'gpu_optimized'
                        })
                
                # 计算该评测日期的预测统计
                stats = self.calculate_future_performance_stats(self.data, high_corr_periods)
                
                detailed_results.append({
                    'evaluation_date': eval_date,
                    'high_correlation_periods': high_corr_periods,
                    'daily_high_count': len(high_corr_periods),
                    'prediction_stats': stats
                })
        
        return detailed_results
    
    def _print_detailed_evaluation_data(self, correlations_np, avg_correlations_filtered, 
                                       period_info_list, high_corr_mask, fields,
                                       batch_recent_data=None, historical_data_list=None, evaluation_dates=None):
        """
        打印前10条评测数据的详细信息，包括对比数组
        
        Args:
            correlations_np: 详细相关系数数组 [evaluation_days, num_historical_periods, 5]
            avg_correlations_filtered: 过滤后的平均相关系数 [evaluation_days, num_historical_periods]
            period_info_list: 历史期间信息列表
            high_corr_mask: 高相关性掩码
            fields: 字段名称列表
            batch_recent_data: 批量评测数据 [evaluation_days, window_size, 5]
            historical_data_list: 历史期间数据列表
            evaluation_dates: 评测日期列表
        """
        self.logger.info("=" * 80)
        self.logger.info("DEBUG模式 - 前10条评测数据详细信息:")
        self.logger.info("=" * 80)
        
        evaluation_days, num_historical_periods, num_fields = correlations_np.shape
        max_display_count = min(10, evaluation_days * num_historical_periods)
        
        # 收集前10条评测数据（按评测日期顺序）
        all_evaluation_data = []
        count = 0
        
        # 按评测日期顺序遍历，每个评测日期取第一个历史期间的数据
        for eval_idx in range(evaluation_days):
            if count >= 10:  # 只取前10条
                break
            for hist_idx in range(num_historical_periods):
                if count >= 10:  # 只取前10条
                    break
                    
                avg_corr = avg_correlations_filtered[eval_idx, hist_idx]
                detailed_corr = correlations_np[eval_idx, hist_idx]
                is_high_corr = high_corr_mask[eval_idx, hist_idx]
                
                period_info = period_info_list[hist_idx]
                
                all_evaluation_data.append({
                    'eval_idx': eval_idx,
                    'hist_idx': hist_idx,
                    'avg_correlation': avg_corr,
                    'detailed_correlations': detailed_corr,
                    'is_high_correlation': is_high_corr,
                    'period_info': period_info
                })
                count += 1
        
        # 打印前10条数据（按评测日期顺序）
        for i, data in enumerate(all_evaluation_data):
            self.logger.info(f"\n第 {i+1} 条评测数据:")
            self.logger.info(f"  评测日期索引: {data['eval_idx']}")
            
            # 添加评测数据时间段信息
            if evaluation_dates and data['eval_idx'] < len(evaluation_dates):
                eval_date = evaluation_dates[data['eval_idx']]
                # 计算评测数据的时间段（从评测日期往前推window_size天）
                eval_start_date = eval_date - pd.Timedelta(days=self.window_size - 1)
                self.logger.info(f"  评测数据时间段: {eval_start_date.strftime('%Y-%m-%d')} 到 {eval_date.strftime('%Y-%m-%d')}")
            
            self.logger.info(f"  历史期间索引: {data['hist_idx']}")
            self.logger.info(f"  历史期间: {data['period_info']['start_date'].strftime('%Y-%m-%d')} 到 {data['period_info']['end_date'].strftime('%Y-%m-%d')}")
            self.logger.info(f"  来源股票: {data['period_info']['stock_code']}")
            self.logger.info(f"  平均相关系数: {data['avg_correlation']:.6f}")
            self.logger.info(f"  是否高相关: {'是' if data['is_high_correlation'] else '否'}")
            
            # 打印各字段的详细相关系数
            self.logger.info("  各字段相关系数:")
            for j, field in enumerate(fields):
                self.logger.info(f"    {field}: {data['detailed_correlations'][j]:.6f}")
            
            # 打印对比数组（如果有原始数据）
            if batch_recent_data is not None and historical_data_list is not None:
                eval_idx = data['eval_idx']
                hist_idx = data['hist_idx']
                
                # 获取评测数据（转换为numpy数组）
                recent_data = batch_recent_data[eval_idx]  # [window_size, 5]
                if isinstance(recent_data, torch.Tensor):
                    recent_data = recent_data.cpu().numpy()
                
                # 获取历史数据
                if hist_idx < len(historical_data_list):
                    historical_data = historical_data_list[hist_idx]  # [window_size, 5]
                    if isinstance(historical_data, torch.Tensor):
                        historical_data = historical_data.cpu().numpy()
                    
                    self.logger.info("  对比数组详情:")
                    self.logger.info(f"    数据窗口大小: {recent_data.shape[0]} 天")
                    
                    # 打印前5天和后5天的数据对比
                    for field_idx, field in enumerate(fields):
                        self.logger.info(f"    {field} 字段对比:")
                        self.logger.info(f"      评测数据前5天: {recent_data[:5, field_idx].tolist()}")
                        self.logger.info(f"      历史数据前5天: {historical_data[:5, field_idx].tolist()}")
                        self.logger.info(f"      评测数据后5天: {recent_data[-5:, field_idx].tolist()}")
                        self.logger.info(f"      历史数据后5天: {historical_data[-5:, field_idx].tolist()}")
                        
                        # 计算统计信息
                        recent_mean = np.mean(recent_data[:, field_idx])
                        historical_mean = np.mean(historical_data[:, field_idx])
                        recent_std = np.std(recent_data[:, field_idx])
                        historical_std = np.std(historical_data[:, field_idx])
                        
                        self.logger.info(f"      评测数据统计 - 均值: {recent_mean:.4f}, 标准差: {recent_std:.4f}")
                        self.logger.info(f"      历史数据统计 - 均值: {historical_mean:.4f}, 标准差: {historical_std:.4f}")
            
            self.logger.info("-" * 60)
        
        self.logger.info("=" * 80)
    
    def _log_first_evaluation_debug_info(self, batch_avg_correlations_filtered, batch_high_corr_mask, 
                                        period_info_list, evaluation_dates, current_batch, historical_tensor, batch_start_idx, is_multi_stock):
        """
        为第一个评测日期打印详细的debug信息
        
        Args:
            batch_avg_correlations_filtered: 过滤后的平均相关系数 [num_stocks, batch_size, num_historical_periods] 或 [batch_size, num_historical_periods]
            batch_high_corr_mask: 高相关性掩码 [num_stocks, batch_size, num_historical_periods] 或 [batch_size, num_historical_periods]
            period_info_list: 历史期间信息列表
            evaluation_dates: 评测日期列表
            current_batch: 当前批次的评测数据 [num_stocks, batch_size, window_size, 5] 或 [batch_size, window_size, 5]
            historical_tensor: 历史数据张量 [num_historical_periods, window_size, 5]
            batch_start_idx: 当前批次的起始索引
            is_multi_stock: 是否为多股票模式
        """
        # 获取第一个评测日期的信息
        first_eval_date = evaluation_dates[batch_start_idx]
        
        if is_multi_stock:
            # 多股票模式：取第一个股票的第一个评测日期
            first_eval_correlations = batch_avg_correlations_filtered[0, 0]  # [num_historical_periods]
            first_eval_high_corr_mask = batch_high_corr_mask[0, 0]  # [num_historical_periods]
            first_eval_data = current_batch[0, 0]  # [window_size, 5]
        else:
            # 单股票模式
            first_eval_correlations = batch_avg_correlations_filtered[0]  # [num_historical_periods]
            first_eval_high_corr_mask = batch_high_corr_mask[0]  # [num_historical_periods]
            first_eval_data = current_batch[0]  # [window_size, 5]
        
        # 转换为CPU numpy数组以便处理
        first_eval_correlations_np = first_eval_correlations.cpu().numpy()
        first_eval_high_corr_mask_np = first_eval_high_corr_mask.cpu().numpy()
        first_eval_data_np = first_eval_data.cpu().numpy()
        
        # 找到所有超过阈值的对比日期
        high_corr_indices = np.where(first_eval_high_corr_mask_np)[0]
        
        self.logger.info("🔍" + "=" * 80)
        self.logger.info(f"🔍 DEBUG模式 - 第一个评测日期详细信息")
        self.logger.info("🔍" + "=" * 80)
        self.logger.info(f"🔍 评测日期: {first_eval_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"🔍 评测数据窗口: {first_eval_date - pd.Timedelta(days=self.window_size-1)} 到 {first_eval_date}")
        self.logger.info(f"🔍 超过阈值的对比期间数量: {len(high_corr_indices)}")
        
        if len(high_corr_indices) > 0:
            self.logger.info("🔍 超过阈值的对比日期和相关系数:")
            
            # 按相关系数降序排列
            sorted_indices = high_corr_indices[np.argsort(-first_eval_correlations_np[high_corr_indices])]
            
            for rank, hist_idx in enumerate(sorted_indices[:10], 1):  # 只显示前10个
                period_info = period_info_list[hist_idx]
                correlation = first_eval_correlations_np[hist_idx]
                
                self.logger.info(f"🔍   #{rank} 历史期间 {hist_idx}: {period_info['start_date']} 到 {period_info['end_date']}")
                self.logger.info(f"🔍       来源股票: {period_info['stock_code']}")
                self.logger.info(f"🔍       平均相关系数: {correlation:.6f}")
                
                # 获取对应的历史数据
                historical_data_np = historical_tensor[hist_idx].cpu().numpy()  # [window_size, 5]
                
                # 打印源数据列的详细对比
                fields = ['open', 'high', 'low', 'close', 'volume']
                self.logger.info(f"🔍       源数据列对比 (前3天和后3天):")
                
                for field_idx, field in enumerate(fields):
                    eval_field_data = first_eval_data_np[:, field_idx]
                    hist_field_data = historical_data_np[:, field_idx]
                    
                    # 计算相关系数
                    field_correlation = np.corrcoef(eval_field_data, hist_field_data)[0, 1]
                    
                    self.logger.info(f"🔍         {field} (相关系数: {field_correlation:.6f}):")
                    self.logger.info(f"🔍           评测数据前3天: {eval_field_data[:3].tolist()}")
                    self.logger.info(f"🔍           历史数据前3天: {hist_field_data[:3].tolist()}")
                    self.logger.info(f"🔍           评测数据后3天: {eval_field_data[-3:].tolist()}")
                    self.logger.info(f"🔍           历史数据后3天: {hist_field_data[-3:].tolist()}")
                
                self.logger.info("🔍" + "-" * 60)
            
            if len(high_corr_indices) > 10:
                self.logger.info(f"🔍   ... 还有 {len(high_corr_indices) - 10} 个超过阈值的期间")
        else:
            self.logger.info("🔍 没有找到超过阈值的对比期间")
        
        # 打印评测数据的统计信息
        self.logger.info("🔍 评测数据统计信息:")
        fields = ['open', 'high', 'low', 'close', 'volume']
        for field_idx, field in enumerate(fields):
            field_data = first_eval_data_np[:, field_idx]
            self.logger.info(f"🔍   {field}: 均值={np.mean(field_data):.4f}, 标准差={np.std(field_data):.4f}, 最小值={np.min(field_data):.4f}, 最大值={np.max(field_data):.4f}")
        
        self.logger.info("🔍" + "=" * 80)
    
    def calculate_future_performance_stats(self, data, high_correlation_periods):
        """
        计算高相关性期间的未来交易日表现统计
        
        Args:
            data: 完整的股票数据
            high_correlation_periods: 高相关性期间列表
            
        Returns:
            dict: 统计结果
        """
        if not high_correlation_periods:
            return None
        
        stats = {
            'total_periods': len(high_correlation_periods),
            'next_day_gap_up': 0,  # 下1个交易日高开
            'next_1_day_up': 0,    # 下1个交易日上涨
            'next_3_day_up': 0,    # 下3个交易日上涨
            'next_5_day_up': 0,    # 下5个交易日上涨
            'next_10_day_up': 0,   # 下10个交易日上涨
            'valid_periods': {
                'next_day': 0,
                'next_3_day': 0,
                'next_5_day': 0,
                'next_10_day': 0
            }
        }
        
        for i, period in enumerate(high_correlation_periods, 1):
            end_date = period['end_date']
            start_date = period['start_date']
            avg_correlation = period['avg_correlation']
            source_stock_code = period['stock_code']
            
            # 根据来源股票代码获取正确的数据源
            if source_stock_code == self.stock_code:
                # 来自目标股票自身的历史数据
                source_data = data
            else:
                # 来自对比股票的历史数据
                source_data = self.loaded_stocks_data.get(source_stock_code)
                if source_data is None:
                    if self.debug:
                        self.logger.warning(f"无法找到股票 {source_stock_code} 的数据，跳过期间 #{i}")
                    continue
            
            # 找到该期间结束后的数据位置
            try:
                end_idx = source_data.index.get_loc(end_date)
            except KeyError:
                if self.debug:
                    self.logger.warning(f"在股票 {source_stock_code} 数据中找不到日期 {end_date}，跳过期间 #{i}")
                continue
            
            # 获取期间最后一天的收盘价
            period_close = source_data.iloc[end_idx]['close']
            
            # 检查下1个交易日
            if end_idx + 1 < len(source_data):
                next_day_data = source_data.iloc[end_idx + 1]
                next_day_open = next_day_data['open']
                next_day_close = next_day_data['close']
                
                stats['valid_periods']['next_day'] += 1
                
                # 高开判断
                if next_day_open > period_close:
                    stats['next_day_gap_up'] += 1
                
                # 下1个交易日上涨判断
                if next_day_close > period_close:
                    stats['next_1_day_up'] += 1
            
            # 检查下3个交易日
            if end_idx + 3 < len(source_data):
                day_3_close = source_data.iloc[end_idx + 3]['close']
                stats['valid_periods']['next_3_day'] += 1
                
                if day_3_close > period_close:
                    stats['next_3_day_up'] += 1
            
            # 检查下5个交易日
            if end_idx + 5 < len(source_data):
                day_5_close = source_data.iloc[end_idx + 5]['close']
                stats['valid_periods']['next_5_day'] += 1
                
                if day_5_close > period_close:
                    stats['next_5_day_up'] += 1
            
            # 检查下10个交易日
            if end_idx + 10 < len(source_data):
                day_10_close = source_data.iloc[end_idx + 10]['close']
                stats['valid_periods']['next_10_day'] += 1
                
                if day_10_close > period_close:
                    stats['next_10_day_up'] += 1
        
        # 计算比例
        stats['ratios'] = {}
        if stats['valid_periods']['next_day'] > 0:
            stats['ratios']['next_day_gap_up'] = stats['next_day_gap_up'] / stats['valid_periods']['next_day']
            stats['ratios']['next_1_day_up'] = stats['next_1_day_up'] / stats['valid_periods']['next_day']
        
        if stats['valid_periods']['next_3_day'] > 0:
            stats['ratios']['next_3_day_up'] = stats['next_3_day_up'] / stats['valid_periods']['next_3_day']
        
        if stats['valid_periods']['next_5_day'] > 0:
            stats['ratios']['next_5_day_up'] = stats['next_5_day_up'] / stats['valid_periods']['next_5_day']
        
        if stats['valid_periods']['next_10_day'] > 0:
            stats['ratios']['next_10_day_up'] = stats['next_10_day_up'] / stats['valid_periods']['next_10_day']
        
        return stats
    

    
    def analyze_batch(self, backtest_date=None, evaluation_days=None, window_size=None, 
                     threshold=None, comparison_mode=None, comparison_stocks=None, debug=None):
        """
        批量分析主函数
        
        Args:
            backtest_date: 回测结束日期
            evaluation_days: 评测日期数量
            window_size: 窗口大小
            threshold: 相关系数阈值
            comparison_mode: 对比模式
            comparison_stocks: 对比股票列表
            debug: 调试模式
            
        Returns:
            dict: 批量分析结果
        """
        self.start_timer('total_batch_analysis')
        
        # 更新参数
        if backtest_date is not None:
            self.backtest_date = pd.to_datetime(backtest_date)
        if evaluation_days is not None:
            self.evaluation_days = evaluation_days
        if window_size is not None:
            self.window_size = window_size
        if threshold is not None:
            self.threshold = threshold
        if comparison_mode is not None:
            self.comparison_mode = comparison_mode
        if comparison_stocks is not None:
            self.comparison_stocks = comparison_stocks
        if debug is not None:
            self.debug = debug
        
        self.logger.info("=" * 80)
        self.logger.info(f"开始GPU批量评测Pearson相关性分析")
        if self.is_multi_stock:
            self.logger.info(f"目标股票: {self.stock_codes} (多股票模式，共{len(self.stock_codes)}只)")
        else:
            self.logger.info(f"目标股票: {self.stock_code}")
        self.logger.info(f"回测结束日期: {self.backtest_date}")
        self.logger.info(f"评测日期数量: {self.evaluation_days}")
        self.logger.info(f"每批次处理数量: {self.evaluation_batch_size}")
        self.logger.info(f"窗口大小: {self.window_size}")
        self.logger.info(f"相关系数阈值: {self.threshold}")
        self.logger.info(f"对比模式: {self.comparison_mode}")
        self.logger.info(f"GPU设备: {self.device}")
        
        # 多股票模式总计算量信息（仅用于日志显示）
        if self.is_multi_stock:
            total_computation_units = len(self.stock_codes) * self.evaluation_days
            self.logger.info(f"📊 多股票模式总计算量: {len(self.stock_codes)} 股票 × {self.evaluation_days} 评测日期 = {total_computation_units} 计算单元")
        
        self.logger.info("=" * 80)
        
        # 初始GPU显存监控
        self.monitor_gpu_memory("分析开始")
        
        # 📚 第1阶段：数据加载 - 开始
        self.logger.info("📚 [阶段1/4] 数据加载 - 开始")
        # 先加载所有数据（目标股票和对比股票）
        self.data = self.load_data()
        if self.data is None:
            self.logger.error("数据加载失败")
            return None
        self.logger.info("📚 [阶段1/4] 数据加载 - 完成")
        
        # 🔄 第2阶段：历史数据处理 - 开始
        self.logger.info("🔄 [阶段2/4] 历史数据处理 - 开始")
        # 收集历史期间数据
        historical_periods_data = self._collect_historical_periods_data()
        
        if not historical_periods_data:
            self.logger.error("没有有效的历史期间数据")
            return None
        self.logger.info("🔄 [阶段2/4] 历史数据处理 - 完成")
        
        evaluation_dates = self.prepare_evaluation_dates(self.backtest_date)
        
        if not evaluation_dates:
            self.logger.error("没有有效的评测日期")
            return None
        
        # 准备批量评测数据
        batch_recent_data, valid_dates, stock_codes = self.prepare_batch_evaluation_data(evaluation_dates)
        
        if batch_recent_data is None:
            self.logger.error("批量评测数据准备失败")
            return None
        
        # 监控数据准备后的GPU显存
        self.monitor_gpu_memory("数据准备完成")
        
        # 💾 基于实际历史期间数据量进行GPU内存预估
        self.logger.info("💾 基于实际数据量进行GPU内存预估...")
        estimation_result = self.estimate_memory_requirement(
            evaluation_days=self.evaluation_days,
            num_historical_periods=len(historical_periods_data),
            window_size=self.window_size
        )
        estimated_memory = estimation_result['total_estimated_gb']
        self.logger.info(f"📊 实际历史期间数据量: {len(historical_periods_data):,}")
        self.logger.info(f"💾 预估GPU内存使用量: {estimated_memory:.2f} GB (基于实际{len(historical_periods_data):,}个历史期间)")
        self.logger.info("=" * 60)
        
        # 🔄 检查是否需要分批处理
        if self.is_multi_stock:
            # 多股票模式：按计算单元（股票数 × 评测日期数）分批
            total_computation_units = len(self.stock_codes) * len(valid_dates)
            total_batches = (total_computation_units + self.evaluation_batch_size - 1) // self.evaluation_batch_size
            
            self.logger.info(f"📊 总计算单元: {total_computation_units} ({len(self.stock_codes)} 只股票 × {len(valid_dates)} 个评测日期)")
            self.logger.info(f"📦 每批处理最大计算单元数: {self.evaluation_batch_size}")
            
            if total_batches > 1:
                self.logger.info(f"🔄 多股票分批处理策略: 将 {total_computation_units} 个计算单元分成 {total_batches} 批处理")
                computation_units_per_batch = min(self.evaluation_batch_size, total_computation_units)
                memory_save_percent = ((total_computation_units - computation_units_per_batch) / total_computation_units) * 100
                self.logger.info(f"💾 预计GPU内存节省: {memory_save_percent:.1f}%")
                return self._process_evaluation_batches(valid_dates, batch_recent_data, historical_periods_data)
            else:
                self.logger.info(f"🔄 多股票单批处理模式: {total_computation_units} 个计算单元一次性处理")
        else:
            # 单股票模式：保持原有逻辑
            total_batches = (len(valid_dates) + self.evaluation_batch_size - 1) // self.evaluation_batch_size
            if total_batches > 1:
                self.logger.info(f"🔄 单股票分批处理策略: 将 {len(valid_dates)} 个评测日期分成 {total_batches} 批处理")
                self.logger.info(f"📦 每批处理: 最多 {self.evaluation_batch_size} 个评测日期")
                memory_save_percent = ((len(valid_dates) - self.evaluation_batch_size) / len(valid_dates)) * 100
                self.logger.info(f"💾 预计GPU内存节省: {memory_save_percent:.1f}%")
                return self._process_evaluation_batches(valid_dates, batch_recent_data, historical_periods_data)
            else:
                self.logger.info("🔄 单批处理模式: 所有评测日期一次性处理")
        
        # 🚀 第3阶段：GPU计算与结果处理 - 开始
        self.logger.info("🚀 [阶段3/4] GPU计算与结果处理 - 开始")
        self.monitor_gpu_memory("GPU计算开始")
        batch_correlations = self.calculate_batch_gpu_correlation_optimized(batch_recent_data, historical_periods_data, valid_dates)
        self.monitor_gpu_memory("GPU计算完成")
        self.logger.info("🚀 [阶段3/4] GPU计算与结果处理 - 完成")
        
        if not batch_correlations:
            self.logger.error("批量相关性计算失败")
            return None
        
        # 📊 第4阶段：最终处理 - 开始
        self.logger.info("📊 [阶段4/4] 最终处理 - 开始")
        
        # 直接使用阶段4-5的整合结果（已包含保存和最终结果构建）
        final_result = batch_correlations
        
        self.end_timer('total_batch_analysis')
        
        # 输出性能总结
        self._log_performance_summary()
        
        # 最终GPU显存监控
        self.monitor_gpu_memory("分析完成")
        self.logger.info("📊 [阶段4/4] 最终处理 - 完成")
        
        # 输出分析总结
        self.logger.info("=" * 80)
        self.logger.info("批量分析结果总结:")
        self.logger.info(f"评测日期数量: {len(valid_dates)}")
        self.logger.info(f"总高相关性期间: {final_result['batch_results']['summary']['total_high_correlations']}")
        self.logger.info(f"平均每日高相关数量: {final_result['batch_results']['summary']['avg_high_correlations_per_day']:.2f}")
        self.logger.info(f"最大每日高相关数量: {final_result['batch_results']['summary']['max_high_correlations_per_day']}")
        if final_result['batch_results']['summary']['overall_avg_correlation'] > 0:
            self.logger.info(f"整体平均相关系数: {final_result['batch_results']['summary']['overall_avg_correlation']:.4f}")
        
        # 查找并打印相关系数最大的条目
        max_correlation = 0
        max_correlation_item = None
        max_eval_date = None
        max_stock_code = None
        
        detailed_results = final_result['batch_results']['detailed_results']
        
        if final_result.get('is_multi_stock', False):
            # 多股票模式：遍历每个股票的结果
            for stock_code, stock_results in detailed_results.items():
                for result in stock_results:
                    for period in result['high_correlation_periods']:
                        if period['avg_correlation'] > max_correlation:
                            max_correlation = period['avg_correlation']
                            max_correlation_item = period
                            max_eval_date = result['evaluation_date']
                            max_stock_code = stock_code
        else:
            # 单股票模式：原有逻辑
            for result in detailed_results:
                for period in result['high_correlation_periods']:
                    if period['avg_correlation'] > max_correlation:
                        max_correlation = period['avg_correlation']
                        max_correlation_item = period
                        max_eval_date = result['evaluation_date']
        
        if max_correlation_item:
            self.logger.info("=" * 40)
            self.logger.info("相关系数最大的条目:")
            if max_stock_code:
                self.logger.info(f"目标股票: {max_stock_code}")
            self.logger.info(f"评测日期: {max_eval_date.strftime('%Y-%m-%d')}")
            self.logger.info(f"历史期间: {max_correlation_item['start_date'].strftime('%Y-%m-%d')} 到 {max_correlation_item['end_date'].strftime('%Y-%m-%d')}")
            self.logger.info(f"相关系数: {max_correlation_item['avg_correlation']:.6f}")
            self.logger.info(f"来源股票: {max_correlation_item['stock_code']}")
            self.logger.info(f"数据来源: {max_correlation_item['source']}")
            self.logger.info("=" * 40)
        
        self.logger.info("=" * 80)
        
        return final_result
    
    def _collect_historical_periods_data(self):
        """收集历史期间数据（合并了对比股票数据加载逻辑）"""
        self.start_timer('historical_data_collection')
        
        historical_periods_data = []
        
        # 检查self_only模式的特殊情况
        if self.comparison_mode == 'self_only':
            self.logger.info("📈 使用自身历史数据对比模式")
            # 在self_only模式下，收集目标股票自身的历史数据
            self_historical_data = self._collect_self_historical_data()
            historical_periods_data.extend(self_historical_data)
            self.logger.info(f"收集到 {len(historical_periods_data)} 个历史期间数据")
            self.end_timer('historical_data_collection')
            return historical_periods_data
        
        # 对比股票数据已经在load_data中加载，无需重复加载
        
        # 收集对比股票历史数据
        # 根据股票数量决定是否使用多进程
        if len(self.loaded_stocks_data) >= 10 and self.num_processes > 1:
            comparison_historical_data = self._collect_comparison_historical_data_multiprocess()
        else:
            comparison_historical_data = self._collect_comparison_historical_data()
        historical_periods_data.extend(comparison_historical_data)
        
        self.logger.info(f"收集到 {len(historical_periods_data)} 个历史期间数据")
        self.end_timer('historical_data_collection')
        return historical_periods_data
    


    
    def _collect_comparison_historical_data(self):
        """收集对比股票历史数据（已优化：直接筛选和预处理）"""
        historical_data = []
        total_valid_periods = 0
        total_invalid_periods = 0
        processed_stocks = 0
        
        # 定义需要的字段
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        for stock_code, stock_data in self.loaded_stocks_data.items():
            # 使用所有可用数据，不进行日期截断
            available_data = stock_data
            
            if len(available_data) < self.window_size:
                if self.debug:
                    self.logger.info(f"股票 {stock_code} 数据长度 {len(available_data)} 小于窗口大小 {self.window_size}，跳过")
                continue
            
            stock_valid_periods = 0
            stock_invalid_periods = 0
            
            # 生成该股票的历史期间并直接进行筛选和预处理
            for i in range(len(available_data) - self.window_size + 1):
                period_data = available_data.iloc[i:i + self.window_size]
                
                # 检查数据长度是否正确
                if len(period_data) == self.window_size:
                    start_date = period_data.index[0]
                    end_date = period_data.index[-1]
                    
                    # 直接提取并预处理数据
                    historical_values = period_data[fields].values
                    
                    # 存储预处理后的数据
                    historical_data.append((historical_values, start_date, end_date, stock_code))
                    stock_valid_periods += 1
                    total_valid_periods += 1
                else:
                    stock_invalid_periods += 1
                    total_invalid_periods += 1
            
            processed_stocks += 1
            
            # 每处理100只股票打印一次进度
            if processed_stocks % 100 == 0:
                self.logger.info(f"对比股票数据收集进度: {processed_stocks}/{len(self.loaded_stocks_data)} 只股票")
        
        self.logger.info(f"对比股票历史数据收集完成: 处理股票={processed_stocks}, 有效期间={total_valid_periods}, 无效期间={total_invalid_periods}")
        return historical_data
    
    def _collect_comparison_historical_data_multiprocess(self):
        """收集对比股票历史数据（多进程版本）"""
        if not self.loaded_stocks_data:
            return []
        
        # 定义需要的字段
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        # 准备多进程任务参数
        tasks = []
        for stock_code, stock_data in self.loaded_stocks_data.items():
            tasks.append((stock_code, stock_data, self.window_size, fields, self.debug))
        
        self.logger.info(f"🚀 启动多进程数据预处理: {len(tasks)} 只股票，{self.num_processes} 个进程")
        
        historical_data = []
        total_valid_periods = 0
        total_invalid_periods = 0
        processed_stocks = 0
        
        try:
            # 使用进程池处理任务
            with mp.Pool(processes=self.num_processes) as pool:
                # 分批处理以显示进度
                batch_size = max(1, len(tasks) // 10)  # 分成10批显示进度
                
                for i in range(0, len(tasks), batch_size):
                    batch_tasks = tasks[i:i + batch_size]
                    batch_results = pool.map(_process_stock_historical_data_worker, batch_tasks)
                    
                    # 处理批次结果
                    for stock_code, stock_historical_data, stats in batch_results:
                        if 'error' in stats:
                            if self.debug:
                                self.logger.warning(f"股票 {stock_code} 处理出错: {stats['error']}")
                            continue
                        
                        if stats.get('skipped', False):
                            if self.debug:
                                self.logger.debug(f"股票 {stock_code} 数据不足，跳过")
                            continue
                        
                        # 添加到总结果中
                        historical_data.extend(stock_historical_data)
                        total_valid_periods += stats['valid_periods']
                        total_invalid_periods += stats['invalid_periods']
                        processed_stocks += 1
                    
                    # 显示进度
                    progress = min(i + batch_size, len(tasks))
                    self.logger.info(f"📊 多进程处理进度: {progress}/{len(tasks)} 只股票 ({progress/len(tasks)*100:.1f}%)")
        
        except Exception as e:
            self.logger.error(f"多进程处理出错，回退到单进程模式: {str(e)}")
            return self._collect_comparison_historical_data(earliest_eval_date)
        
        self.logger.info(f"✅ 多进程对比股票历史数据收集完成: 处理股票={processed_stocks}, 有效期间={total_valid_periods}, 无效期间={total_invalid_periods}")
        return historical_data
    
    def _collect_self_historical_data(self):
        """收集目标股票自身的历史数据（用于self_only模式）"""
        historical_data = []
        
        if self.data is None or self.data.empty:
            self.logger.warning(f"目标股票 {self.stock_code} 数据为空，无法收集历史数据")
            return historical_data
        
        # 定义需要的字段
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        # 使用目标股票的所有可用数据
        available_data = self.data
        
        if len(available_data) < self.window_size:
            self.logger.warning(f"目标股票 {self.stock_code} 数据长度 {len(available_data)} 小于窗口大小 {self.window_size}")
            return historical_data
        
        valid_periods = 0
        invalid_periods = 0
        
        # 生成目标股票的历史期间数据
        for i in range(len(available_data) - self.window_size + 1):
            period_data = available_data.iloc[i:i + self.window_size]
            
            # 检查数据长度是否正确
            if len(period_data) == self.window_size:
                start_date = period_data.index[0]
                end_date = period_data.index[-1]
                
                # 直接提取并预处理数据
                historical_values = period_data[fields].values
                
                # 存储预处理后的数据
                historical_data.append((historical_values, start_date, end_date, self.stock_code))
                valid_periods += 1
            else:
                invalid_periods += 1
        
        self.logger.info(f"目标股票 {self.stock_code} 历史数据收集完成: 有效期间={valid_periods}, 无效期间={invalid_periods}")
        return historical_data
    

    

    

    

    

    
    def monitor_gpu_memory(self, stage_name):
        """监控GPU显存使用情况"""
        if self.device.type == 'cuda':
            # 获取当前显存使用情况
            current_allocated = torch.cuda.memory_allocated() / 1024**3  # GB
            current_reserved = torch.cuda.memory_reserved() / 1024**3    # GB
            
            # 更新峰值记录
            self.gpu_memory_stats['peak_allocated'] = max(
                self.gpu_memory_stats['peak_allocated'], current_allocated
            )
            self.gpu_memory_stats['peak_reserved'] = max(
                self.gpu_memory_stats['peak_reserved'], current_reserved
            )
            
            # 更新当前值
            self.gpu_memory_stats['current_allocated'] = current_allocated
            self.gpu_memory_stats['current_reserved'] = current_reserved
            
            # 记录日志
            self.logger.info(f"🔍 GPU显存监控 [{stage_name}]:")
            self.logger.info(f"   当前已分配: {current_allocated:.2f}GB")
            self.logger.info(f"   当前已保留: {current_reserved:.2f}GB")
            self.logger.info(f"   峰值已分配: {self.gpu_memory_stats['peak_allocated']:.2f}GB")
            self.logger.info(f"   峰值已保留: {self.gpu_memory_stats['peak_reserved']:.2f}GB")
            
            # 检查显存使用率
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            usage_rate = current_allocated / total_memory
            
            if usage_rate > 0.8:
                self.logger.warning(f"⚠️ GPU显存使用率较高: {usage_rate*100:.1f}%")
            elif usage_rate > 0.9:
                self.logger.error(f"❌ GPU显存使用率过高: {usage_rate*100:.1f}%，可能导致内存溢出")
        else:
            self.logger.info(f"🔍 CPU模式，跳过GPU显存监控 [{stage_name}]")
    
    def estimate_memory_requirement(self, evaluation_days, num_historical_periods, window_size, num_fields=5):
        """
        精确估算GPU显存需求（GB）
        基于实际内存使用模式和PyTorch内存池机制
        支持多股票模式的内存估算
        
        Args:
            evaluation_days: 评测日期数量
            num_historical_periods: 历史期间数量
            window_size: 窗口大小
            num_fields: 字段数量（默认5：开高低收量）
            
        Returns:
            dict: 包含详细内存估算的字典
        """
        bytes_per_float32 = 4
        
        # 获取股票数量（多股票模式下需要考虑）
        num_stocks = len(self.stock_codes) if self.is_multi_stock else 1
        
        # 1. 基础数据张量
        # 多股票模式: [num_stocks, evaluation_days, window_size, num_fields]
        # 单股票模式: [evaluation_days, window_size, num_fields]
        batch_recent_data_bytes = num_stocks * evaluation_days * window_size * num_fields * bytes_per_float32
        
        # 历史数据张量: [num_historical_periods, window_size, num_fields]
        historical_tensor_bytes = num_historical_periods * window_size * num_fields * bytes_per_float32
        
        # 2. 相关系数计算中间张量（这是内存峰值的主要来源）
        # 在_compute_correlation_matrix中的广播计算
        
        # 多股票模式下的张量形状：
        # recent_expanded: [num_stocks, batch_size, 1, window_size, num_fields]
        # historical_expanded: [1, num_historical_periods, window_size, num_fields]
        # 广播后的实际内存占用: [num_stocks, batch_size, num_historical_periods, window_size, num_fields]
        
        # 使用实际的GPU分组批处理大小，而不是self.batch_size
        if self.is_multi_stock:
            # 多股票模式：批处理大小基于计算单元数量
            total_computation_units = num_stocks * evaluation_days
            batch_size = min(self.evaluation_batch_size, total_computation_units)
        else:
            # 单股票模式：批处理大小基于评测日期数量
            batch_size = min(self.evaluation_batch_size, evaluation_days)
        
        # 广播张量（最大内存消耗点）- 考虑多股票模式
        broadcast_tensor_bytes = num_stocks * batch_size * num_historical_periods * window_size * num_fields * bytes_per_float32
        
        # 中心化张量（2个）
        centered_tensors_bytes = 2 * broadcast_tensor_bytes
        
        # 协方差、标准差、相关系数张量 - 考虑多股票模式
        covariance_bytes = num_stocks * batch_size * num_historical_periods * num_fields * bytes_per_float32
        std_tensors_bytes = 2 * num_stocks * batch_size * num_historical_periods * num_fields * bytes_per_float32
        correlation_bytes = num_stocks * batch_size * num_historical_periods * num_fields * bytes_per_float32
        
        # 3. GPU端结果存储张量
        # 多股票模式: [num_stocks, evaluation_days, num_historical_periods]
        # 单股票模式: [evaluation_days, num_historical_periods]
        avg_correlations_bytes = num_stocks * evaluation_days * num_historical_periods * bytes_per_float32
        
        # 高相关掩码: [num_stocks, evaluation_days, num_historical_periods] (bool = 1 byte)
        high_corr_mask_bytes = num_stocks * evaluation_days * num_historical_periods * 1
        
        # 4. 关键修正：GPU计算过程中的真实内存峰值
        # 在_compute_correlation_matrix中，广播操作会创建巨大的中间张量：
        # - recent_expanded.unsqueeze(1): [batch_size, 1, window_size, 5]
        # - historical_expanded.unsqueeze(0): [1, num_historical_periods, window_size, 5]  
        # - 广播计算时，PyTorch会创建完整的 [batch_size, num_historical_periods, window_size, 5] 张量
        
        # 真实的广播内存消耗（这是被严重低估的部分）- 考虑多股票模式
        full_broadcast_tensor_bytes = num_stocks * batch_size * num_historical_periods * window_size * num_fields * bytes_per_float32
        
        # GPU计算峰值时同时存在的张量：
        # 1. 原始数据
        # 2. recent_expanded (广播后的完整大小)
        # 3. historical_expanded (广播后的完整大小)
        # 4. recent_centered (完整大小)
        # 5. historical_centered (完整大小)
        # 6. 各种中间计算结果
        
        # 实际内存峰值主要来源：
        # 1. 历史数据张量（持续存在）
        # 2. 广播计算时的临时张量（峰值时刻）
        # 3. 少量中间结果张量
        peak_allocated_bytes = (
            historical_tensor_bytes +           # 原始历史数据（持续存在）
            full_broadcast_tensor_bytes +       # 主要的广播张量峰值
            covariance_bytes +                  # 协方差张量
            std_tensors_bytes +                 # 标准差张量
            correlation_bytes                   # 相关系数张量
        )
        
        # 5. PyTorch内存池预留（基于实际观察修正）
        # 实际观察：预估分配29.2GB，实际峰值27GB，约0.9倍
        # 说明我们的基础计算略有过度估算，PyTorch实际使用更高效
        pytorch_memory_pool_multiplier = 0.9  # 基于实际观察的精确调整
        
        peak_allocated_gb = peak_allocated_bytes / (1024**3)
        estimated_reserved_gb = peak_allocated_gb * pytorch_memory_pool_multiplier
        
        # 6. 构建详细估算结果
        estimation_details = {
            'evaluation_days': evaluation_days,
            'num_historical_periods': num_historical_periods,
            'window_size': window_size,
            'batch_size': batch_size,
            
            # 基础张量大小（GB）
            'batch_recent_data_gb': batch_recent_data_bytes / (1024**3),
            'historical_tensor_gb': historical_tensor_bytes / (1024**3),
            'broadcast_tensor_gb': broadcast_tensor_bytes / (1024**3),
            'intermediate_tensors_gb': (centered_tensors_bytes + covariance_bytes + std_tensors_bytes + correlation_bytes) / (1024**3),
            
            # 内存峰值估算
            'peak_allocated_gb': peak_allocated_gb,
            'estimated_reserved_gb': estimated_reserved_gb,
            'total_estimated_gb': estimated_reserved_gb,  # 主要关注保留内存
            
            # 内存池信息
            'pytorch_pool_multiplier': pytorch_memory_pool_multiplier,
            
            # 关键计算参数
            'critical_tensor_size': f"[{batch_size}, {num_historical_periods}, {window_size}, {num_fields}]",
            'critical_tensor_gb': broadcast_tensor_bytes / (1024**3)
        }
        
        # 记录详细的内存估算日志
        self.logger.info(f"🧮 GPU内存需求精确估算:")
        self.logger.info(f"   📊 输入参数:")
        if self.is_multi_stock:
            self.logger.info(f"      股票数量: {num_stocks}")
            self.logger.info(f"      评测日期数: {evaluation_days} (每股票)")
            self.logger.info(f"      总计算单元: {num_stocks * evaluation_days}")
        else:
            self.logger.info(f"      评测日期数: {evaluation_days}")
        self.logger.info(f"      历史期间数: {num_historical_periods:,}")
        self.logger.info(f"      窗口大小: {window_size}")
        self.logger.info(f"      批处理大小: {batch_size}")
        self.logger.info(f"   📦 关键张量大小:")
        self.logger.info(f"      批量评测数据: {estimation_details['batch_recent_data_gb']:.3f}GB")
        self.logger.info(f"      历史数据张量: {estimation_details['historical_tensor_gb']:.3f}GB")
        self.logger.info(f"      关键广播张量: {estimation_details['critical_tensor_gb']:.3f}GB {estimation_details['critical_tensor_size']}")
        self.logger.info(f"      中间计算张量: {estimation_details['intermediate_tensors_gb']:.3f}GB")
        self.logger.info(f"   💾 内存峰值预估:")
        self.logger.info(f"      预估分配峰值: {peak_allocated_gb:.2f}GB")
        self.logger.info(f"      预估保留峰值: {estimated_reserved_gb:.2f}GB (PyTorch内存池 x{pytorch_memory_pool_multiplier:.1f})")
        self.logger.info(f"   🎯 总内存需求预估: {estimated_reserved_gb:.2f}GB")
        
        return estimation_details
    
    def check_gpu_memory_limit(self, required_memory_gb):
        """检查GPU显存是否足够"""
        if self.device.type != 'cuda':
            return True  # CPU模式不受显存限制
        
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        available_memory = total_memory * self.gpu_memory_limit
        
        self.logger.info(f"🔍 GPU显存检查:")
        self.logger.info(f"   总显存: {total_memory:.2f}GB")
        self.logger.info(f"   可用显存: {available_memory:.2f}GB (限制: {self.gpu_memory_limit*100:.0f}%)")
        self.logger.info(f"   需求显存: {required_memory_gb:.2f}GB")
        
        if required_memory_gb <= available_memory:
            self.logger.info(f"✅ 显存充足，可以直接处理")
            return True
        else:
            self.logger.warning(f"⚠️ 显存不足，需要分批处理")
            return False
    
    def _get_performance_stats(self):
        """获取性能统计信息"""
        stats = {}
        for timer_name, timer_records in self.performance_timers.items():
            if timer_records:
                # 处理新的数据结构
                if isinstance(timer_records[0], dict):
                    elapsed_times = [record['elapsed_time'] for record in timer_records]
                    stats[timer_name] = {
                        'total_time': sum(elapsed_times),
                        'avg_time': sum(elapsed_times) / len(elapsed_times),
                        'max_time': max(elapsed_times),
                        'min_time': min(elapsed_times),
                        'count': len(elapsed_times),
                        'parent': timer_records[0]['parent'],
                        'timestamp': timer_records[0]['timestamp']
                    }
                else:
                    # 兼容旧的数据结构
                    stats[timer_name] = {
                        'total_time': sum(timer_records),
                        'avg_time': sum(timer_records) / len(timer_records),
                        'max_time': max(timer_records),
                        'min_time': min(timer_records),
                        'count': len(timer_records),
                        'parent': None,
                        'timestamp': time.time()
                    }
        
        # 添加GPU显存统计
        if self.device.type == 'cuda':
            stats['gpu_memory'] = self.gpu_memory_stats.copy()
        
        return stats
    
    def _process_evaluation_batches(self, valid_dates, batch_recent_data, historical_periods_data):
        """
        分批处理评测日期，避免GPU内存溢出
        
        Args:
            valid_dates: 有效的评测日期列表
            batch_recent_data: 批量最近数据
            historical_periods_data: 历史期间数据
            
        Returns:
            dict: 合并后的分析结果
        """
        self.logger.info("🔄 开始分批处理评测日期...")
        
        # 初始化合并结果
        merged_results = {
            'evaluation_days': len(valid_dates),
            'batch_results': {
                'detailed_results': [],
                'summary': {
                    'total_high_correlations': 0,
                    'avg_high_correlations_per_day': 0.0,
                    'max_high_correlations_per_day': 0,
                    'overall_avg_correlation': 0.0
                }
            }
        }
        
        # 计算批次数量（考虑多股票模式）
        if self.is_multi_stock:
            # 多股票模式：按计算单元（股票数 × 评测日期数）分批
            total_computation_units = len(self.stock_codes) * len(valid_dates)
            
            # 直接按照计算单元数量分批，确保每批不超过evaluation_batch_size个计算单元
            total_batches = (total_computation_units + self.evaluation_batch_size - 1) // self.evaluation_batch_size
        else:
            # 单股票模式：保持原有逻辑
            total_batches = (len(valid_dates) + self.evaluation_batch_size - 1) // self.evaluation_batch_size
        
        # 分批处理
        if self.is_multi_stock:
            # 多股票模式：按计算单元分批处理
            # 创建所有计算单元的列表：[(stock_idx, stock_code, date_idx, date)]
            all_computation_units = []
            for stock_idx, stock_code in enumerate(self.stock_codes):
                for date_idx, date in enumerate(valid_dates):
                    all_computation_units.append((stock_idx, stock_code, date_idx, date))
            
            # 按批次处理计算单元
            for batch_idx in range(total_batches):
                start_unit = batch_idx * self.evaluation_batch_size
                end_unit = min(start_unit + self.evaluation_batch_size, total_computation_units)
                current_batch_units = end_unit - start_unit
                
                self.logger.info(f"🔄 处理第 {batch_idx + 1}/{total_batches} 批: {current_batch_units} 个计算单元")
                
                # 获取当前批次的计算单元
                batch_units = all_computation_units[start_unit:end_unit]
                
                # 按股票分组当前批次的计算单元
                stock_date_groups = {}
                for stock_idx, stock_code, date_idx, date in batch_units:
                    if stock_code not in stock_date_groups:
                        stock_date_groups[stock_code] = {'stock_idx': stock_idx, 'dates': []}
                    stock_date_groups[stock_code]['dates'].append((date_idx, date))
                
                # 准备批次数据：收集所有股票的相关日期数据
                batch_stock_indices = []
                batch_date_indices = []
                batch_dates_list = []
                
                for stock_code, group_info in stock_date_groups.items():
                    stock_idx = group_info['stock_idx']
                    batch_dates_info = group_info['dates']
                    
                    for date_idx, date in batch_dates_info:
                        batch_stock_indices.append(stock_idx)
                        batch_date_indices.append(date_idx)
                        batch_dates_list.append(date)
                
                # 提取批次数据：[batch_size, window_size, 5]
                # batch_recent_data: [num_stocks, evaluation_days, window_size, 5]
                batch_data_list = []
                for stock_idx, date_idx in zip(batch_stock_indices, batch_date_indices):
                    batch_data_list.append(batch_recent_data[stock_idx, date_idx, :, :])
                
                # 堆叠成批次张量
                batch_tensor = torch.stack(batch_data_list, dim=0)  # [batch_size, window_size, 5]
                
                # 监控GPU内存
                self.monitor_gpu_memory(f"批次 {batch_idx + 1} GPU计算开始")
                
                # 🚀 一次性GPU计算整个批次
                self.logger.info(f"🚀 批次 {batch_idx + 1} GPU计算 - 开始")
                self.logger.info(f"📦 处理 {len(set(batch_stock_indices))} 只股票，{current_batch_units} 个计算单元")
                
                # 输出详细的计算单元信息
                self.logger.info("📋 计算单元详细信息:")
                for i, (stock_idx, date_idx, date) in enumerate(zip(batch_stock_indices, batch_date_indices, batch_dates_list)):
                    stock_code = self.stock_codes[stock_idx] if self.is_multi_stock else self.stock_code
                    self.logger.info(f"   单元 {i+1}: 股票代码={stock_code}, 评测日期={date}")
                
                # 开始批次级别的GPU计时
                self.start_timer('gpu_step1_data_preparation')
                self.start_timer('gpu_step2_tensor_creation') 
                self.start_timer('gpu_step3_integrated_correlation_processing')
                
                # 调用不带计时器的GPU计算函数
                batch_correlations = self._calculate_batch_gpu_correlation_no_timer(
                    batch_tensor.unsqueeze(0), historical_periods_data, batch_dates_list
                )
                
                # 结束批次级别的GPU计时
                self.end_timer('gpu_step3_integrated_correlation_processing')
                self.end_timer('gpu_step2_tensor_creation')
                self.end_timer('gpu_step1_data_preparation')
                
                self.monitor_gpu_memory(f"批次 {batch_idx + 1} GPU计算完成")
                self.logger.info(f"🚀 批次 {batch_idx + 1} GPU计算 - 完成")
                
                # 合并批次结果
                if batch_correlations:
                    merged_results['batch_results']['detailed_results'].extend(
                        batch_correlations['batch_results']['detailed_results']
                    )
                    
                    # 累加统计数据
                    batch_summary = batch_correlations['batch_results']['summary']
                    merged_results['batch_results']['summary']['total_high_correlations'] += batch_summary['total_high_correlations']
                    merged_results['batch_results']['summary']['max_high_correlations_per_day'] = max(
                        merged_results['batch_results']['summary']['max_high_correlations_per_day'],
                        batch_summary['max_high_correlations_per_day']
                    )
                
                # 清理GPU缓存
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()
                    gc.collect()
                
                self.logger.info(f"✅ 批次 {batch_idx + 1} 处理完成，已处理 {current_batch_units} 个计算单元")
            
            self.logger.info(f"🔄 分批处理完成！")
        else:
            # 单股票模式的原有逻辑
            for batch_idx in range(total_batches):
                # 单股票模式：按日期分批
                start_idx = batch_idx * self.evaluation_batch_size
                end_idx = min(start_idx + self.evaluation_batch_size, len(valid_dates))
                
                batch_dates = valid_dates[start_idx:end_idx]
                batch_size = len(batch_dates)
                
                self.logger.info(f"🔄 处理第 {batch_idx + 1}/{total_batches} 批: {batch_size} 个评测日期")
                self.logger.info(f"📅 日期范围: {batch_dates[0]} 到 {batch_dates[-1]}")
                
                # 提取当前批次的数据 (batch_recent_data 是 PyTorch 张量)
                # 使用传参判断模式，不依赖矩阵形状
                if self.is_multi_stock:
                    # 多股票模式: [num_stocks, evaluation_days, window_size, 5]
                    batch_recent_subset = batch_recent_data[:, start_idx:end_idx]
                else:
                    # 单股票模式: 可能是 [1, evaluation_days, window_size, 5] 或 [evaluation_days, window_size, 5]
                    if len(batch_recent_data.shape) == 4:
                        # 已转换为统一格式 [1, evaluation_days, window_size, 5]
                        batch_recent_subset = batch_recent_data[:, start_idx:end_idx]
                    else:
                        # 原始单股票格式 [evaluation_days, window_size, 5]
                        batch_recent_subset = batch_recent_data[start_idx:end_idx]
                
                # 监控GPU内存
                self.monitor_gpu_memory(f"批次 {batch_idx + 1} 开始")
                
                # 🚀 GPU计算当前批次
                self.logger.info(f"🚀 [批次 {batch_idx + 1}] GPU计算与结果处理 - 开始")
                
                # 输出详细的计算单元信息（单股票模式）
                self.logger.info("📋 计算单元详细信息:")
                for i, date in enumerate(batch_dates):
                    self.logger.info(f"   单元 {i+1}: 股票代码={self.stock_code}, 评测日期={date}")
                
                batch_correlations = self.calculate_batch_gpu_correlation_optimized(
                    batch_recent_subset, historical_periods_data, batch_dates
                )
                self.monitor_gpu_memory(f"批次 {batch_idx + 1} 完成")
                self.logger.info(f"🚀 [批次 {batch_idx + 1}] GPU计算与结果处理 - 完成")
                
                if not batch_correlations:
                    self.logger.error(f"批次 {batch_idx + 1} 计算失败")
                    continue
                
                # 合并结果
                merged_results['batch_results']['detailed_results'].extend(
                    batch_correlations['batch_results']['detailed_results']
                )
                
                # 累加统计数据
                batch_summary = batch_correlations['batch_results']['summary']
                merged_results['batch_results']['summary']['total_high_correlations'] += batch_summary['total_high_correlations']
                merged_results['batch_results']['summary']['max_high_correlations_per_day'] = max(
                    merged_results['batch_results']['summary']['max_high_correlations_per_day'],
                    batch_summary['max_high_correlations_per_day']
                )
                
                # 清理GPU缓存
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()
                    gc.collect()
                
                self.logger.info(f"✅ 批次 {batch_idx + 1} 处理完成，累计高相关性期间: {merged_results['batch_results']['summary']['total_high_correlations']}")
        
        # 计算最终平均值
        total_days = len(valid_dates)
        if total_days > 0:
            merged_results['batch_results']['summary']['avg_high_correlations_per_day'] = (
                merged_results['batch_results']['summary']['total_high_correlations'] / total_days
            )
        
        # 计算整体平均相关系数
        if merged_results['batch_results']['detailed_results']:
            all_correlations = []
            for result in merged_results['batch_results']['detailed_results']:
                if 'high_correlations' in result:
                    for corr_data in result['high_correlations']:
                        if 'correlation' in corr_data:
                            all_correlations.append(corr_data['correlation'])
            
            if all_correlations:
                merged_results['batch_results']['summary']['overall_avg_correlation'] = np.mean(all_correlations)
        
        self.logger.info("🔄 分批处理完成！")
        if self.is_multi_stock:
            total_computation_units = len(self.stock_codes) * total_days
            self.logger.info(f"📊 总计处理: {total_computation_units} 个计算单元 ({len(self.stock_codes)} 只股票 × {total_days} 个评测日期)，分 {total_batches} 批")
        else:
            self.logger.info(f"📊 总计处理: {total_days} 个评测日期，分 {total_batches} 批")
        self.logger.info(f"📈 总高相关性期间: {merged_results['batch_results']['summary']['total_high_correlations']}")
        
        # 输出性能统计（分批处理模式）
        self._log_performance_summary()
        
        return merged_results
    
    def _merge_batch_correlations(self, batch_correlations_list):
        """
        合并多个股票的批次相关性结果
        
        Args:
            batch_correlations_list: 多个股票的批次结果列表
            
        Returns:
            dict: 合并后的批次结果
        """
        if not batch_correlations_list:
            return None
        
        # 初始化合并结果
        merged_result = {
            'evaluation_days': 0,
            'batch_results': {
                'detailed_results': [],
                'summary': {
                    'total_high_correlations': 0,
                    'avg_high_correlations_per_day': 0.0,
                    'max_high_correlations_per_day': 0,
                    'overall_avg_correlation': 0.0
                }
            }
        }
        
        # 合并所有详细结果
        for batch_result in batch_correlations_list:
            if batch_result and 'batch_results' in batch_result:
                # 合并详细结果
                merged_result['batch_results']['detailed_results'].extend(
                    batch_result['batch_results']['detailed_results']
                )
                
                # 累加统计数据
                batch_summary = batch_result['batch_results']['summary']
                merged_result['batch_results']['summary']['total_high_correlations'] += batch_summary['total_high_correlations']
                merged_result['batch_results']['summary']['max_high_correlations_per_day'] = max(
                    merged_result['batch_results']['summary']['max_high_correlations_per_day'],
                    batch_summary['max_high_correlations_per_day']
                )
                
                # 累加评测日期数
                merged_result['evaluation_days'] += batch_result.get('evaluation_days', 0)
        
        # 计算平均值
        if merged_result['evaluation_days'] > 0:
            merged_result['batch_results']['summary']['avg_high_correlations_per_day'] = (
                merged_result['batch_results']['summary']['total_high_correlations'] / merged_result['evaluation_days']
            )
        
        # 计算整体平均相关系数
        if merged_result['batch_results']['detailed_results']:
            all_correlations = []
            for result in merged_result['batch_results']['detailed_results']:
                if 'high_correlations' in result:
                    for corr_data in result['high_correlations']:
                        if 'correlation' in corr_data:
                            all_correlations.append(corr_data['correlation'])
            
            if all_correlations:
                merged_result['batch_results']['summary']['overall_avg_correlation'] = np.mean(all_correlations)
        
        return merged_result
    
    def _log_performance_summary(self):
        """输出分层性能总结"""
        self.logger.info("=" * 80)
        self.logger.info("📊 分层性能统计总结 (按执行顺序)")
        self.logger.info("=" * 80)
        
        # 获取性能统计
        stats = self._get_performance_stats()
        
        # 定义步骤映射和显示顺序 - 新的4阶段划分
        step_mapping = {
            # 第1阶段：多进程历史数据处理（含对比股票数据加载）
            'historical_data_collection': ('1-1', '历史数据收集（含对比股票数据加载）'),
            
            # 第2阶段：初始化与数据准备
            'target_stock_loading': ('2-1', '目标股票数据加载'),
            'evaluation_dates_preparation': ('2-2', '评测日期准备'),
            'batch_data_preparation': ('2-3', '批量数据准备'),
            
            # 第3阶段：GPU计算与结果处理（合并原4-6阶段）
            'gpu_step1_data_preparation': ('3-1', '历史数据准备和筛选'),
            'gpu_step2_tensor_creation': ('3-2', '创建GPU历史数据张量'),
            'gpu_step3_correlation_calculation': ('3-3', '批量相关系数计算'),
            'gpu_step3_integrated_correlation_processing': ('3-4', '集成相关性处理'),
            'gpu_step4_batch_merging': ('3-5', '合并批次结果'),
            'gpu_step5_result_processing': ('3-6', '处理批量相关性结果'),
            'integrated_result_processing': ('3-7', '集成结果处理'),
            
            # 总体统计
            'total_batch_analysis': ('总计', '完整批量分析')
        }
        
        # 按步骤顺序显示 - 新的4阶段划分
        current_stage = 0
        stage_names = {
            1: "📚 第1阶段：多进程历史数据处理",
            2: "🔄 第2阶段：初始化与数据准备",
            3: "🚀 第3阶段：GPU计算与结果处理"
        }
        
        for timer_name, (step_id, step_name) in step_mapping.items():
            if timer_name in stats:
                stat = stats[timer_name]
                
                # 检查是否需要显示新的阶段标题
                if step_id != '总计':
                    stage_num = int(step_id.split('-')[0])
                    if stage_num != current_stage:
                        if current_stage > 0:
                            self.logger.info("")  # 空行分隔
                        self.logger.info(stage_names[stage_num])
                        current_stage = stage_num
                
                # 显示步骤统计
                if step_id == '总计':
                    self.logger.info("")
                    self.logger.info("=" * 40)
                    self.logger.info(f"📈 {step_id} - {step_name}:")
                else:
                    self.logger.info(f"  {step_id} {step_name}:")
                
                self.logger.info(f"      总耗时: {stat['total_time']:.3f}秒")
                self.logger.info(f"      平均耗时: {stat['avg_time']:.3f}秒") 
                self.logger.info(f"      执行次数: {stat['count']}")
                
                # 计算百分比（相对于总时间）
                if 'total_batch_analysis' in stats:
                    total_time = stats['total_batch_analysis']['total_time']
                    percentage = (stat['total_time'] / total_time) * 100
                    self.logger.info(f"      占比: {percentage:.1f}%")
        
        # 显示其他未映射的计时器
        unmapped_timers = set(stats.keys()) - set(step_mapping.keys()) - {'gpu_memory'}
        if unmapped_timers:
            self.logger.info("")
            self.logger.info("🔧 其他计时器:")
            for timer_name in sorted(unmapped_timers):
                stat = stats[timer_name]
                self.logger.info(f"  {timer_name}: 总耗时={stat['total_time']:.3f}秒, "
                               f"平均={stat['avg_time']:.3f}秒, 次数={stat['count']}")
        
        # GPU显存统计
        if self.device.type == 'cuda':
            self.logger.info("")
            self.logger.info("💾 GPU显存统计:")
            self.logger.info(f"  峰值已分配: {self.gpu_memory_stats['peak_allocated']:.2f}GB")
            self.logger.info(f"  峰值已保留: {self.gpu_memory_stats['peak_reserved']:.2f}GB")
            self.logger.info(f"  当前已分配: {self.gpu_memory_stats['current_allocated']:.2f}GB")
            self.logger.info(f"  当前已保留: {self.gpu_memory_stats['current_reserved']:.2f}GB")
        
        self.logger.info("=" * 80)
    
    def save_batch_results_to_csv(self, result):
        """保存批量结果到CSV文件 - 基于评测单元列表确保数据完全对应"""
        self.logger.info("💾 开始保存批量结果到CSV文件...")
        
        # 记录输入参数的详细信息
        self.logger.info(f"💾 输入参数类型: {type(result)}")
        self.logger.info(f"💾 输入参数键: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        
        # 详细打印关键传入参数
        self.logger.info("💾 ========== 关键传入参数详情 ==========")
        
        # 1. evaluation_dates - 评测日期列表
        evaluation_dates = result.get('evaluation_dates', [])
        self.logger.info(f"💾 evaluation_dates (评测日期列表):")
        self.logger.info(f"💾   - 类型: {type(evaluation_dates)}")
        self.logger.info(f"💾   - 长度: {len(evaluation_dates) if evaluation_dates else 0}")
        if evaluation_dates:
            self.logger.info(f"💾   - 内容: {evaluation_dates}")
        else:
            self.logger.info(f"💾   - 内容: 空列表")
        
        # 2. batch_results - 批量分析结果
        batch_results = result.get('batch_results', {})
        self.logger.info(f"💾 batch_results (批量分析结果):")
        self.logger.info(f"💾   - 类型: {type(batch_results)}")
        if isinstance(batch_results, dict):
            self.logger.info(f"💾   - 键列表: {list(batch_results.keys())}")
            
            # 打印每个主要键的详细信息
            for key in batch_results.keys():
                value = batch_results[key]
                self.logger.info(f"💾   - {key}: {type(value)}")
                
                if key == 'summary' and isinstance(value, dict):
                    self.logger.info(f"💾     summary内容: {value}")
                elif key == 'evaluation_days':
                    self.logger.info(f"💾     evaluation_days值: {value}")
                elif key == 'num_historical_periods':
                    self.logger.info(f"💾     num_historical_periods值: {value}")
                elif key == 'high_correlation_counts' and hasattr(value, '__len__'):
                    self.logger.info(f"💾     high_correlation_counts长度: {len(value)}")
                    if hasattr(value, 'shape'):
                        self.logger.info(f"💾     high_correlation_counts形状: {value.shape}")
                elif key == 'avg_correlations' and hasattr(value, '__len__'):
                    self.logger.info(f"💾     avg_correlations长度: {len(value)}")
                    if hasattr(value, 'shape'):
                        self.logger.info(f"💾     avg_correlations形状: {value.shape}")
                elif key == 'period_info' and isinstance(value, list):
                    self.logger.info(f"💾     period_info列表长度: {len(value)}")
                    if len(value) > 0:
                        self.logger.info(f"💾     period_info第一个元素: {value[0]}")
            
            # 打印detailed_results的详细信息
            detailed_results = batch_results.get('detailed_results', {})
            self.logger.info(f"💾   - detailed_results类型: {type(detailed_results)}")
            if isinstance(detailed_results, dict):
                self.logger.info(f"💾   - detailed_results包含股票: {list(detailed_results.keys())}")
                for stock_code, stock_data in detailed_results.items():
                    self.logger.info(f"💾   - 股票{stock_code}数据类型: {type(stock_data)}, 长度: {len(stock_data) if hasattr(stock_data, '__len__') else 'N/A'}")
                    
                    # 打印每个股票的详细数据结构
                    if isinstance(stock_data, list) and len(stock_data) > 0:
                        self.logger.info(f"💾     股票{stock_code}第一个元素类型: {type(stock_data[0])}")
                        if isinstance(stock_data[0], dict):
                            self.logger.info(f"💾     股票{stock_code}第一个元素键: {list(stock_data[0].keys())}")
                            # 打印第一个元素的详细内容
                            first_item = stock_data[0]
                            for item_key, item_value in first_item.items():
                                if isinstance(item_value, (int, float, str, bool)):
                                    self.logger.info(f"💾       {item_key}: {item_value}")
                                else:
                                    self.logger.info(f"💾       {item_key}: {type(item_value)} (长度: {len(item_value) if hasattr(item_value, '__len__') else 'N/A'})")
            elif isinstance(detailed_results, list):
                self.logger.info(f"💾   - detailed_results列表长度: {len(detailed_results)}")
        else:
            self.logger.info(f"💾   - 内容: {batch_results}")
        
        # 3. is_multi_stock - 是否为多股票模式的标志
        is_multi_stock = result.get('is_multi_stock', False)
        self.logger.info(f"💾 is_multi_stock (多股票模式标志):")
        self.logger.info(f"💾   - 类型: {type(is_multi_stock)}")
        self.logger.info(f"💾   - 值: {is_multi_stock}")
        
        # 4. 其他重要参数
        self.logger.info(f"💾 其他重要参数:")
        other_params = ['stock_codes', 'backtest_date', 'evaluation_days', 'window_size', 'threshold', 'performance_stats']
        for param in other_params:
            if param in result:
                value = result[param]
                self.logger.info(f"💾   - {param}: {type(value)} = {value}")
                
                # 对performance_stats进行详细展示
                if param == 'performance_stats' and isinstance(value, dict):
                    for perf_key, perf_value in value.items():
                        self.logger.info(f"💾     {perf_key}: {perf_value}")
        
        self.logger.info("💾 ========================================")
        
        try:
            
            # 记录关键参数信息
            self.logger.info(f"💾 评测模式: {'多股票模式' if is_multi_stock else '单股票模式'}")
            
            # 记录目标CSV文件信息
            self.logger.info(f"💾 目标CSV文件: {self.csv_results_file}")
            self.logger.info(f"💾 CSV文件是否存在: {os.path.exists(self.csv_results_file)}")
            
            # 读取现有CSV文件
            self.logger.info("💾 开始读取现有CSV文件...")
            if os.path.exists(self.csv_results_file):
                try:
                    df = pd.read_csv(self.csv_results_file, encoding='utf-8-sig', dtype={'代码': str})
                    self.logger.info(f"💾 成功读取现有CSV文件，现有记录数: {len(df)}")
                    if len(df) > 0:
                        self.logger.info(f"💾 现有CSV列名: {list(df.columns)}")
                        # 显示现有数据的基本统计
                        unique_stocks = df['代码'].nunique() if '代码' in df.columns else 0
                        unique_dates = df['评测日期'].nunique() if '评测日期' in df.columns else 0
                        self.logger.info(f"💾 现有数据统计: {unique_stocks} 个股票, {unique_dates} 个评测日期")
                except Exception as e:
                    self.logger.error(f"💾 读取现有CSV文件时出错: {str(e)}")
                    df = pd.DataFrame()
                    self.logger.info("💾 创建空DataFrame作为备用")
            else:
                df = pd.DataFrame()
                self.logger.info("💾 CSV文件不存在，创建空DataFrame")
            
            # 构建评测单元列表 - 使用和批次处理时相同的逻辑
            evaluation_units = []
            self.logger.info("💾 开始构建评测单元列表...")
            
            # 获取评测日期列表
            evaluation_dates = result.get('evaluation_dates', [])
            self.logger.info(f"💾 评测日期数量: {len(evaluation_dates)}")
            
            if is_multi_stock:
                # 多股票模式：使用和批次处理时相同的逻辑
                detailed_results = batch_results['detailed_results']
                self.logger.info(f"💾 多股票模式 - 详细结果包含股票: {list(detailed_results.keys()) if isinstance(detailed_results, dict) else 'N/A'}")
                
                if isinstance(detailed_results, dict):
                    # 按照股票代码和评测日期的组合来构建计算单元
                    for stock_code, stock_daily_results in detailed_results.items():
                        self.logger.info(f"💾 处理股票 {stock_code}，日结果数量: {len(stock_daily_results) if isinstance(stock_daily_results, list) else 'N/A'}")
                        
                        if isinstance(stock_daily_results, list):
                            for daily_result in stock_daily_results:
                                evaluation_date = daily_result.get('evaluation_date')
                                
                                if evaluation_date:
                                    evaluation_unit = {
                                        'stock_code': str(stock_code),  # 直接使用外层的stock_code
                                        'evaluation_date': evaluation_date,
                                        'daily_result': daily_result,
                                        'window_size': result['window_size'],
                                        'threshold': result['threshold']
                                    }
                                    evaluation_units.append(evaluation_unit)
                                else:
                                    self.logger.warning(f"💾 股票 {stock_code} 的某个日结果缺少evaluation_date字段")
                        else:
                            self.logger.warning(f"💾 股票 {stock_code} 的日结果不是列表格式: {type(stock_daily_results)}")
                else:
                    self.logger.error(f"💾 多股票模式下detailed_results不是字典格式: {type(detailed_results)}")
            else:
                # 单股票模式：从detailed_results列表中提取评测单元
                detailed_results_list = batch_results['detailed_results']
                stock_code = result.get('stock_code', self.stock_code)
                self.logger.info(f"💾 单股票模式 - 目标股票: {stock_code}，日结果数量: {len(detailed_results_list) if isinstance(detailed_results_list, list) else 'N/A'}")
                
                if isinstance(detailed_results_list, list):
                    for daily_result in detailed_results_list:
                        evaluation_date = daily_result.get('evaluation_date')
                        
                        if evaluation_date:
                            evaluation_unit = {
                                'stock_code': str(stock_code),  # 使用统一的stock_code
                                'evaluation_date': evaluation_date,
                                'daily_result': daily_result,
                                'window_size': result['window_size'],
                                'threshold': result['threshold']
                            }
                            evaluation_units.append(evaluation_unit)
                        else:
                            self.logger.warning(f"💾 某个日结果缺少evaluation_date字段")
                else:
                    self.logger.error(f"💾 单股票模式下detailed_results不是列表格式: {type(detailed_results_list)}")
            
            # 记录当前批次的计算单元列表
            self.logger.info(f"💾 当前批次计算单元列表 (共 {len(evaluation_units)} 个):")
            if evaluation_units:
                for i, unit in enumerate(evaluation_units):
                    self.logger.info(f"   单元 {i+1}: {unit['stock_code']} - {unit['evaluation_date'].strftime('%Y-%m-%d')}")
            
            # 基于评测单元列表生成CSV数据行
            new_rows = []
            self.logger.info("💾 开始基于评测单元生成CSV数据行...")
            
            for unit_idx, unit in enumerate(evaluation_units):
                stock_code = unit['stock_code']
                evaluation_date = unit['evaluation_date']
                daily_result = unit['daily_result']
                
                # 提取预测统计信息
                prediction_stats = daily_result.get('prediction_stats', {})
                
                # 计算对比股票数量
                comparison_stock_count = len(self.comparison_stocks)
                
                # 准备单行数据
                row_data = {
                    '代码': stock_code,
                    'window_size': unit['window_size'],
                    '阈值': unit['threshold'],
                    '评测日期': evaluation_date.strftime('%Y-%m-%d'),
                    '对比股票数量': comparison_stock_count,
                    '相关数量': daily_result.get('daily_high_count', 0),
                    '下1日高开': f"{prediction_stats.get('ratios', {}).get('next_day_gap_up', 0):.2%}" if prediction_stats else 'N/A',
                    '下1日上涨': f"{prediction_stats.get('ratios', {}).get('next_1_day_up', 0):.2%}" if prediction_stats else 'N/A',
                    '下3日上涨': f"{prediction_stats.get('ratios', {}).get('next_3_day_up', 0):.2%}" if prediction_stats else 'N/A',
                    '下5日上涨': f"{prediction_stats.get('ratios', {}).get('next_5_day_up', 0):.2%}" if prediction_stats else 'N/A',
                    '下10日上涨': f"{prediction_stats.get('ratios', {}).get('next_10_day_up', 0):.2%}" if prediction_stats else 'N/A'
                }
                new_rows.append(row_data)
                
                # 记录每行数据的详细内容（仅在debug模式下或前几行）
                if self.debug or unit_idx < 3:
                    self.logger.info(f"💾 新增数据行 {unit_idx+1}: {row_data}")
            
            # 记录数据准备完成的统计信息
            self.logger.info(f"💾 CSV数据准备完成，共生成 {len(new_rows)} 行新数据")
            
            # 添加所有新行
            if new_rows:
                self.logger.info("💾 开始合并新数据到现有CSV数据...")
                self.logger.info(f"💾 合并前现有数据行数: {len(df)}")
                self.logger.info(f"💾 待合并新数据行数: {len(new_rows)}")
                
                new_df = pd.DataFrame(new_rows)
                self.logger.info(f"💾 新DataFrame创建成功，列名: {list(new_df.columns)}")
                
                # 合并数据
                original_row_count = len(df)
                df = pd.concat([df, new_df], ignore_index=True)
                self.logger.info(f"💾 数据合并完成，合并后总行数: {len(df)} (增加了 {len(df) - original_row_count} 行)")
                
                # 确保代码列为字符串类型
                df['代码'] = df['代码'].astype(str)
                self.logger.info("💾 代码列类型转换为字符串完成")
                
                # 按评测日期降序排列（最新日期在前）
                self.logger.info("💾 开始按评测日期排序...")
                df['评测日期_排序'] = pd.to_datetime(df['评测日期'])
                df = df.sort_values('评测日期_排序', ascending=False)
                df = df.drop('评测日期_排序', axis=1)  # 删除临时排序列
                df = df.reset_index(drop=True)  # 重置索引
                self.logger.info("💾 数据排序完成（按评测日期降序）")
                
                # 保存CSV文件
                self.logger.info("💾 开始保存CSV文件...")
                df.to_csv(self.csv_results_file, index=False, encoding='utf-8-sig')
                
                # 保存后验证
                self.logger.info("✅ CSV文件保存完成，开始验证...")
                try:
                    # 验证文件是否存在
                    if os.path.exists(self.csv_results_file):
                        # 获取文件大小
                        file_size = os.path.getsize(self.csv_results_file)
                        file_size_mb = file_size / (1024 * 1024)
                        self.logger.info(f"✅ CSV文件验证 - 文件大小: {file_size} 字节 ({file_size_mb:.2f} MB)")
                        
                        # 重新读取文件验证行数
                        verification_df = pd.read_csv(self.csv_results_file, encoding='utf-8-sig', dtype={'代码': str})
                        actual_rows = len(verification_df)
                        self.logger.info(f"✅ CSV文件验证 - 实际行数: {actual_rows}")
                        self.logger.info(f"✅ CSV文件验证 - 列数: {len(verification_df.columns)}")
                        
                        # 验证数据统计
                        if actual_rows > 0:
                            unique_stocks = verification_df['代码'].nunique() if '代码' in verification_df.columns else 0
                            unique_dates = verification_df['评测日期'].nunique() if '评测日期' in verification_df.columns else 0
                            self.logger.info(f"✅ CSV文件验证 - 包含 {unique_stocks} 个股票, {unique_dates} 个评测日期")
                            
                            # 显示最新的几条记录（前3行）
                            if self.debug and actual_rows > 0:
                                self.logger.info("✅ CSV文件验证 - 最新3条记录:")
                                for i, row in verification_df.head(3).iterrows():
                                    self.logger.info(f"✅   行{i+1}: {dict(row)}")
                        
                        self.logger.info(f"✅ 批量结果已成功保存到CSV文件: {self.csv_results_file}")
                        self.logger.info(f"✅ 本次新增 {len(new_rows)} 条逐日评测记录，文件总计 {actual_rows} 条记录")
                    else:
                        self.logger.error("❌ CSV文件保存后验证失败：文件不存在")
                except Exception as verify_error:
                    self.logger.error(f"❌ CSV文件保存后验证时出错: {str(verify_error)}")
                    self.logger.info(f"✅ 批量结果已保存到CSV文件: {self.csv_results_file}")
                    self.logger.info(f"✅ 共保存 {len(new_rows)} 条逐日评测记录")
            else:
                self.logger.warning("⚠️ 没有有效的评测结果需要保存")
            
        except Exception as e:
            self.logger.error(f"❌ 保存CSV文件时出错: {str(e)}")
            import traceback
            self.logger.error(f"❌ 详细错误信息: {traceback.format_exc()}")


def analyze_pearson_correlation_gpu_batch(stock_code, backtest_date=None, evaluation_days=1, 
                                         window_size=15, threshold=0.85, comparison_mode='default', 
                                         comparison_stocks=None, debug=False, csv_filename=None, 
                                         use_gpu=True, batch_size=1000, earliest_date='2020-01-01',
                                         num_processes=None, evaluation_batch_size=20):
    """
    GPU批量评测Pearson相关性分析的便捷函数
    
    Args:
        stock_code: 股票代码
        backtest_date: 回测结束日期
        evaluation_days: 评测日期数量
        window_size: 窗口大小
        threshold: 相关系数阈值
        comparison_mode: 对比模式
        comparison_stocks: 对比股票列表
        debug: 调试模式
        csv_filename: CSV文件名
        use_gpu: 是否使用GPU
        batch_size: 批处理大小
        earliest_date: 数据获取的最早日期限制 (格式: YYYY-MM-DD，默认: 2020-01-01)
        evaluation_batch_size: 每批次处理的评测日期数量
        
    Returns:
        dict: 分析结果
    """
    if backtest_date is None:
        backtest_date = datetime.now().strftime('%Y-%m-%d')
    
    if csv_filename is None:
        csv_filename = 'batch_evaluation_results.csv'
    
    analyzer = GPUBatchPearsonAnalyzer(
        stock_code=stock_code,
        window_size=window_size,
        threshold=threshold,
        evaluation_days=evaluation_days,
        debug=debug,
        comparison_stocks=comparison_stocks,
        comparison_mode=comparison_mode,
        backtest_date=backtest_date,
        csv_filename=csv_filename,
        use_gpu=use_gpu,
        batch_size=batch_size,
        earliest_date=earliest_date,
        num_processes=num_processes,
        evaluation_batch_size=evaluation_batch_size
    )
    
    result = analyzer.analyze_batch()
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GPU批量评测Pearson相关性分析')
    parser.add_argument('--stock_code', required=True, help='股票代码或模式名称。支持: 1)单个股票代码(000001) 2)多个逗号分隔(000001,000002) 3)预定义模式(top10/industry/all)')
    parser.add_argument('--backtest_date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--evaluation_days', type=int, default=1, help='评测日期数量 (默认: 1)')
    parser.add_argument('--window_size', type=int, default=15, help='分析窗口大小 (默认: 15)')
    parser.add_argument('--threshold', type=float, default=0.85, help='相关系数阈值 (默认: 0.85)')
    parser.add_argument('--comparison_mode', type=str, default='top10', 
                       choices=['top10', 'industry', 'custom', 'self_only', 'all'],
                       help='对比模式: top10(市值前10), industry(行业股票), custom(自定义), self_only(仅自身历史), all(全部A股) (默认: top10)')
    parser.add_argument('--comparison_stocks', nargs='*', 
                       help='自定义对比股票列表，用空格分隔 (仅在comparison_mode=custom时有效)')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')
    parser.add_argument('--csv_filename', type=str, default='evaluation_results.csv', help='CSV结果文件名 (默认: evaluation_results.csv)')
    parser.add_argument('--no_gpu', action='store_true', help='禁用GPU加速 (默认启用GPU)')
    parser.add_argument('--batch_size', type=int, default=1000, 
                       help='GPU批处理大小 - 控制单次GPU计算的数据量，影响内存使用和计算效率。'
                            '推荐值：RTX 3060(8GB)=500-1000, RTX 3080(10GB)=1000-2000, RTX 4090(24GB)=2000-5000 (默认: 1000)')
    parser.add_argument('--earliest_date', type=str, default='2022-01-01', 
                       help='数据获取的最早日期限制 (YYYY-MM-DD)，早于此日期的数据将被过滤掉 (默认: 2022-01-01)')
    parser.add_argument('--num_processes', type=int, default=None,
                       help='多进程数量，None表示自动检测（默认为CPU核心数-1）')
    parser.add_argument('--evaluation_batch_size', type=int, default=20,
                        help='每批次处理的计算单元数量，用于控制GPU内存使用。'
                             '单股票模式: 直接表示评测日期数量 (如evaluation_days=100, batch_size=20, 分5批处理)。'
                             '多股票模式: 表示总计算单元数 (如100股票×15评测日期=1500单元, batch_size=20, 分75批处理) (默认: 20)')

    args = parser.parse_args()
    
    # 解析股票代码，支持逗号分隔的多个股票或模式名称
    input_value = args.stock_code.strip()
    
    # 检查是否为预定义的模式名称
    predefined_modes = ['top10', 'industry', 'all']
    if input_value in predefined_modes:
        # 使用模式获取股票列表
        from stock_config import get_comparison_stocks, get_all_stocks_list
        if input_value == 'all':
            stock_codes = get_all_stocks_list()
        else:
            stock_codes = get_comparison_stocks(input_value)
        print(f"使用预定义模式 '{input_value}'，获取到 {len(stock_codes)} 个股票")
    else:
        # 传统的股票代码解析，支持逗号分隔的多个股票
        stock_codes = [code.strip() for code in input_value.split(',')]
    
    print(f"开始GPU批量评测分析，股票代码: {stock_codes}")
    print(f"评测日期数量: {args.evaluation_days}")
    print(f"窗口大小: {args.window_size}")
    print(f"相关系数阈值: {args.threshold}")
    
    # 使用真正的多股票批量处理
    print(f"\n开始批量处理所有股票: {stock_codes}")
    result = analyze_pearson_correlation_gpu_batch(
        stock_code=','.join(stock_codes),  # 传递逗号分隔的股票代码
        backtest_date=args.backtest_date,
        evaluation_days=args.evaluation_days,
        window_size=args.window_size,
        threshold=args.threshold,
        comparison_mode=args.comparison_mode,
        comparison_stocks=args.comparison_stocks,
        debug=args.debug,
        csv_filename=args.csv_filename,
        use_gpu=not args.no_gpu,
        batch_size=args.batch_size,
        earliest_date=args.earliest_date,
        num_processes=args.num_processes,
        evaluation_batch_size=args.evaluation_batch_size
    )
    
    # 输出总体结果
    if result:
        print(f"\n所有股票分析完成，成功处理 {len(stock_codes)} 个股票")
        print(f"评测了 {result['evaluation_days']} 个日期")
        print(f"总高相关性期间: {result['batch_results']['summary']['total_high_correlations']}")
        print(f"平均每日高相关数量: {result['batch_results']['summary']['avg_high_correlations_per_day']:.2f}")
        print(f"整体平均相关系数: {result['batch_results']['summary']['overall_avg_correlation']:.4f}")
        
        # 如果是多股票，显示每个股票的统计信息
        if len(stock_codes) > 1 and 'stock_summary' in result['batch_results']:
            print("\n各股票统计信息:")
            for stock_code, stats in result['batch_results']['stock_summary'].items():
                print(f"  {stock_code}: 高相关期间={stats['high_correlations']}, 平均相关性={stats['avg_correlation']:.4f}")
    else:
        print("所有股票分析失败")