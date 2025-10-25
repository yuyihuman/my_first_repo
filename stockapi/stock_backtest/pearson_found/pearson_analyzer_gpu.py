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
                 num_processes=None):
        """
        初始化GPU批量评测Pearson相关性分析器
        
        Args:
            stock_code: 目标股票代码
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
        """
        self.stock_code = stock_code
        
        # 设置固定的绝对路径
        script_dir = r'C:\Users\17701\github\my_first_repo\stockapi\stock_backtest\pearson_found'
        self.log_dir = os.path.join(script_dir, 'logs')
        self.csv_results_file = os.path.join(script_dir, csv_filename)
        
        self.window_size = window_size
        self.threshold = threshold
        self.evaluation_days = evaluation_days  # 新增：评测日期数量
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
            if stock_code in self.comparison_stocks:
                self.comparison_stocks.remove(stock_code)
        
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
        
        self.logger.info(f"初始化GPU批量评测Pearson分析器，目标股票: {stock_code}")
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
        stock_log_dir = os.path.join(self.log_dir, self.stock_code)
        os.makedirs(stock_log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thread_id = threading.get_ident()
        log_filename = f"batch_pearson_analysis_{self.stock_code}_{timestamp}_thread_{thread_id}.log"
        log_path = os.path.join(stock_log_dir, log_filename)
        
        self.logger = logging.getLogger(f'GPUBatchPearsonAnalyzer_{self.stock_code}')
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
        if not os.path.exists(self.csv_results_file):
            # 使用与单日脚本相同的表头格式
            header = ['代码', 'window_size', '阈值', '评测日期', '对比股票数量', '相关数量', 
                     '下1日高开', '下1日上涨', '下3日上涨', '下5日上涨', '下10日上涨']
            df = pd.DataFrame(columns=header)
            df['代码'] = df['代码'].astype(str)
            df.to_csv(self.csv_results_file, index=False, encoding='utf-8-sig')
            
            if self.debug:
                self.logger.info(f"🆕 Debug: 批量评测CSV文件创建完成: {self.csv_results_file}")
    
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
        """加载目标股票数据"""
        self.start_timer('target_stock_loading')
        self.logger.info("📊 数据加载中...")
        self.data_loader = StockDataLoader()
        
        data = self.data_loader.load_stock_data(self.stock_code)
        
        if data is None or data.empty:
            self.logger.error(f"无法加载股票 {self.stock_code} 的数据")
            self.end_timer('target_stock_loading')
            return None
        
        self.data = self._filter_data(data, self.stock_code)
        self.logger.info(f"✅ 目标股票 {self.stock_code} 数据加载完成 ({len(self.data)} 条记录)")
        self.end_timer('target_stock_loading')
        
        # 加载对比股票数据
        self._load_comparison_stocks_data()
        
        return self.data
    
    def _filter_data(self, data, stock_code):
        """过滤股票数据，确保数据质量和日期范围"""
        if data is None or data.empty:
            return data
            
        original_count = len(data)
        
        # 首先按日期过滤
        data = data[data.index >= self.earliest_date]
        date_filtered_count = len(data)
        date_removed_count = original_count - date_filtered_count
        
        # 然后按数据质量过滤
        data = data[
            (data['open'] > 0) & 
            (data['high'] > 0) & 
            (data['low'] > 0) & 
            (data['close'] > 0) & 
            (data['volume'] > 0)
        ]
        final_count = len(data)
        quality_removed_count = date_filtered_count - final_count
        
        if date_removed_count > 0:
            self.logger.debug(f"股票 {stock_code} 日期过滤完成，移除早于 {self.earliest_date.strftime('%Y-%m-%d')} 的 {date_removed_count} 条数据")
        
        if quality_removed_count > 0:
            self.logger.debug(f"股票 {stock_code} 数据质量过滤完成，移除 {quality_removed_count} 条异常数据")
        
        if not data.empty:
            self.logger.debug(f"股票 {stock_code} 成功加载 {len(data)} 条记录，日期范围: {data.index[0]} 到 {data.index[-1]}")
        
        return data
    
    def _load_comparison_stocks_data(self):
        """加载对比股票数据"""
        if self.comparison_mode == 'self_only':
            self.logger.info("📈 使用自身历史数据对比模式")
            return
        
        self.start_timer('comparison_stocks_loading')
        self.logger.info(f"📈 加载对比股票数据中... ({len(self.comparison_stocks)} 只)")
        successful_loads = 0
        
        for stock_code in self.comparison_stocks:
            try:
                if self.debug:
                    self.logger.info(f"正在加载对比股票: {stock_code}")
                
                data = self.data_loader.load_stock_data(stock_code)
                if data is not None and not data.empty:
                    filtered_data = self._filter_data(data, stock_code)
                    if not filtered_data.empty:
                        self.loaded_stocks_data[stock_code] = filtered_data
                        successful_loads += 1
                    else:
                        if self.debug:
                            self.logger.warning(f"股票 {stock_code} 过滤后数据为空")
                else:
                    if self.debug:
                        self.logger.warning(f"无法加载股票 {stock_code} 的数据")
                        
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"加载股票 {stock_code} 时出错: {str(e)}")
                continue
        
        self.logger.info(f"✅ 对比股票数据加载完成 ({successful_loads}/{len(self.comparison_stocks)} 只)")
        self.end_timer('comparison_stocks_loading')
    
    def prepare_evaluation_dates(self, end_date):
        """
        准备批量评测日期列表
        
        Args:
            end_date: 结束日期
            
        Returns:
            list: 评测日期列表
        """
        self.start_timer('evaluation_dates_preparation')
        
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
        准备批量评测数据矩阵
        
        Args:
            evaluation_dates: 评测日期列表
            
        Returns:
            torch.Tensor: 形状为 [evaluation_days, window_size, 5] 的评测数据张量
        """
        self.start_timer('batch_data_preparation')
        
        fields = ['open', 'high', 'low', 'close', 'volume']
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
            return None, []
        
        # 转换为张量 [evaluation_days, window_size, 5]
        batch_data = np.stack(batch_data_list, axis=0)
        batch_tensor = torch.tensor(batch_data, dtype=torch.float32, device=self.device)
        
        self.logger.info(f"批量评测数据准备完成，形状: {batch_tensor.shape}")
        self.logger.info(f"有效评测日期数量: {len(valid_dates)}")
        
        self.end_timer('batch_data_preparation')
        return batch_tensor, valid_dates
    
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
        
        evaluation_days, window_size, num_fields = batch_recent_data.shape
        num_historical_periods = len(historical_periods_data)
        
        self.logger.info(f"开始批量GPU相关性计算")
        self.logger.info(f"评测日期数: {evaluation_days}, 历史期间数: {num_historical_periods}")
        
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
        self.logger.info(f"目标输出形状: [{evaluation_days}, {historical_tensor.shape[0]}, 5]")
        
        batch_correlations = []
        
        # 分批处理以避免内存溢出
        batch_size = min(self.batch_size, evaluation_days)
        total_batches = (evaluation_days + batch_size - 1) // batch_size
        
        self.logger.info(f"分批计算配置: batch_size={batch_size}, total_batches={total_batches}")
        
        for batch_idx, i in enumerate(range(0, evaluation_days, batch_size)):
            end_idx = min(i + batch_size, evaluation_days)
            current_batch = batch_recent_data[i:end_idx]  # [batch_size, window_size, 5]
            
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
        # 合并所有批次的结果
        all_correlations = torch.cat(batch_correlations, dim=0)  # [evaluation_days, num_historical_periods, 5]
        self.logger.info(f"批次结果合并完成: 最终形状={all_correlations.shape}")
        self.end_timer('gpu_step4_batch_merging')
        self.logger.info(f"  🔗 [子步骤4/5] 合并批次结果 - 完成")
        
        # 监控相关系数计算完成后的GPU显存
        self.monitor_gpu_memory("相关系数计算完成")
        
        self.logger.info(f"批量GPU相关性计算完成，结果形状: {all_correlations.shape}")
        
        # 子步骤5/5: 处理批量相关性结果
        self.start_timer('gpu_step5_result_processing')
        self.logger.info(f"  📋 [子步骤5/5] 处理批量相关性结果 - 开始")
        self.logger.info(f"调用函数: _process_batch_correlation_results")
        results = self._process_batch_correlation_results(
            all_correlations, period_info_list, evaluation_days,
            batch_recent_data, historical_data_list, evaluation_dates
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
    
    def _process_batch_correlation_results(self, correlations_tensor, period_info_list, evaluation_days,
                                          batch_recent_data=None, historical_data_list=None, evaluation_dates=None):
        """
        处理批量相关性计算结果（整合了阶段5的详细结果处理和保存功能）
        
        Args:
            correlations_tensor: [evaluation_days, num_historical_periods, 5]
            period_info_list: 历史期间信息列表
            evaluation_days: 评测日期数量
            evaluation_dates: 评测日期列表
            
        Returns:
            dict: 处理后的完整最终结果，包含详细结果、统计信息和性能数据
        """
        # 使用统一的计时器，覆盖原来的4-5和5-1步骤
        self.start_timer('integrated_result_processing')
        
        correlations_np = correlations_tensor.cpu().numpy()
        fields = ['open', 'high', 'low', 'close', 'volume']
        
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
        
        # Debug模式下打印前10条评测数据的详细信息
        if self.debug:
            self._print_detailed_evaluation_data(
                correlations_np, avg_correlations_filtered, period_info_list, 
                high_corr_mask, fields, batch_recent_data, historical_data_list, evaluation_dates
            )
        
        # 构建详细结果（整合阶段5的功能）
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
                                'source': 'gpu_batch'
                            })
                    
                    # 计算该评测日期的预测统计
                    stats = self.calculate_future_performance_stats(self.data, high_corr_periods)
                    
                    detailed_results.append({
                        'evaluation_date': eval_date,
                        'high_correlation_periods': high_corr_periods,
                        'daily_high_count': len(high_corr_periods),
                        'prediction_stats': stats
                    })
        
        # 构建批量结果
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
            'stock_code': self.stock_code,
            'backtest_date': self.backtest_date,
            'evaluation_days': len(evaluation_dates) if evaluation_dates else evaluation_days,
            'window_size': self.window_size,
            'threshold': self.threshold,
            'evaluation_dates': evaluation_dates if evaluation_dates else [],
            'batch_results': batch_results,
            'performance_stats': self._get_performance_stats()
        }
        
        # 保存结果到CSV（原阶段5的功能）
        if hasattr(self, 'save_results') and self.save_results:
            self.save_batch_results_to_csv(final_result)
        
        self.logger.info(f"批量结果处理完成（已整合详细结果处理和保存功能）")
        self.logger.info(f"总高相关性期间: {batch_results['summary']['total_high_correlations']}")
        self.logger.info(f"平均每日高相关数: {batch_results['summary']['avg_high_correlations_per_day']:.2f}")
        
        self.end_timer('integrated_result_processing')
        return final_result
    
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
        self.logger.info(f"目标股票: {self.stock_code}")
        self.logger.info(f"回测结束日期: {self.backtest_date}")
        self.logger.info(f"评测日期数量: {self.evaluation_days}")
        self.logger.info(f"窗口大小: {self.window_size}")
        self.logger.info(f"相关系数阈值: {self.threshold}")
        self.logger.info(f"对比模式: {self.comparison_mode}")
        self.logger.info(f"GPU设备: {self.device}")
        self.logger.info("=" * 80)
        
        # 初始GPU显存监控
        self.monitor_gpu_memory("分析开始")
        
        # 🔄 第1阶段：数据加载 - 开始
        self.logger.info("🔄 [阶段1/6] 数据加载 - 开始")
        if not hasattr(self, 'data') or self.data is None:
            self.data = self.load_data()
            if self.data is None:
                self.logger.error("数据加载失败")
                return None
        self.logger.info("🔄 [阶段1/5] 数据加载 - 完成")
        
        # 📋 第2阶段：数据准备 - 开始
        self.logger.info("📋 [阶段2/5] 数据准备 - 开始")
        evaluation_dates = self.prepare_evaluation_dates(self.backtest_date)
        
        if not evaluation_dates:
            self.logger.error("没有有效的评测日期")
            return None
        
        # 准备批量评测数据
        batch_recent_data, valid_dates = self.prepare_batch_evaluation_data(evaluation_dates)
        
        if batch_recent_data is None:
            self.logger.error("批量评测数据准备失败")
            return None
        
        # 监控数据准备后的GPU显存
        self.monitor_gpu_memory("数据准备完成")
        self.logger.info("📋 [阶段2/5] 数据准备 - 完成")
        
        # 📚 第3阶段：历史数据收集 - 开始
        self.logger.info("📚 [阶段3/5] 历史数据收集 - 开始")
        earliest_eval_date = min(valid_dates)
        historical_periods_data = self._collect_historical_periods_data(earliest_eval_date)
        
        if not historical_periods_data:
            self.logger.error("没有有效的历史期间数据")
            return None
        self.logger.info("📚 [阶段3/5] 历史数据收集 - 完成")
        
        # 🚀 第4阶段：GPU计算与结果处理 - 开始（整合了原阶段4-5和5）
        self.logger.info("🚀 [阶段4/5] GPU计算与结果处理 - 开始")
        self.monitor_gpu_memory("GPU计算开始")
        batch_correlations = self.calculate_batch_gpu_correlation(batch_recent_data, historical_periods_data, valid_dates)
        self.monitor_gpu_memory("GPU计算完成")
        self.logger.info("🚀 [阶段4/5] GPU计算与结果处理 - 完成")
        
        if not batch_correlations:
            self.logger.error("批量相关性计算失败")
            return None
        
        # 📊 第5阶段：最终处理 - 已整合到阶段4-5中
        self.logger.info("📊 [阶段5/5] 最终处理 - 已整合完成")
        
        # 直接使用阶段4-5的整合结果（已包含保存和最终结果构建）
        final_result = batch_correlations
        
        self.end_timer('total_batch_analysis')
        
        # 输出性能总结
        self._log_performance_summary()
        
        # 最终GPU显存监控
        self.monitor_gpu_memory("分析完成")
        self.logger.info("📊 [阶段5/5] 最终处理 - 完成")
        
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
        
        for result in final_result['batch_results']['detailed_results']:
            for period in result['high_correlation_periods']:
                if period['avg_correlation'] > max_correlation:
                    max_correlation = period['avg_correlation']
                    max_correlation_item = period
                    max_eval_date = result['evaluation_date']
        
        if max_correlation_item:
            self.logger.info("=" * 40)
            self.logger.info("相关系数最大的条目:")
            self.logger.info(f"评测日期: {max_eval_date.strftime('%Y-%m-%d')}")
            self.logger.info(f"历史期间: {max_correlation_item['start_date'].strftime('%Y-%m-%d')} 到 {max_correlation_item['end_date'].strftime('%Y-%m-%d')}")
            self.logger.info(f"相关系数: {max_correlation_item['avg_correlation']:.6f}")
            self.logger.info(f"来源股票: {max_correlation_item['stock_code']}")
            self.logger.info(f"数据来源: {max_correlation_item['source']}")
            self.logger.info("=" * 40)
        
        self.logger.info("=" * 80)
        
        return final_result
    
    def _collect_historical_periods_data(self, earliest_eval_date):
        """收集历史期间数据"""
        self.start_timer('historical_data_collection')
        
        historical_periods_data = []
        
        # 在all模式下，自身历史数据已经包含在对比股票数据中，无需单独收集
        if self.comparison_mode != 'all':
            # 收集自身历史数据
            self_historical_data = self._collect_self_historical_data(earliest_eval_date)
            historical_periods_data.extend(self_historical_data)
        
        # 收集对比股票数据
        if self.comparison_mode != 'self_only':
            # 根据股票数量决定是否使用多进程
            if len(self.loaded_stocks_data) >= 10 and self.num_processes > 1:
                comparison_historical_data = self._collect_comparison_historical_data_multiprocess(earliest_eval_date)
            else:
                comparison_historical_data = self._collect_comparison_historical_data(earliest_eval_date)
            historical_periods_data.extend(comparison_historical_data)
        
        self.logger.info(f"收集到 {len(historical_periods_data)} 个历史期间数据")
        self.end_timer('historical_data_collection')
        return historical_periods_data
    
    def _collect_self_historical_data(self, earliest_eval_date):
        """收集自身历史数据（已优化：直接筛选和预处理）"""
        historical_data = []
        valid_periods = 0
        invalid_periods = 0
        
        # 使用所有可用数据，不进行日期截断
        available_data = self.data
        
        if len(available_data) < self.window_size:
            self.logger.info(f"自身数据长度 {len(available_data)} 小于窗口大小 {self.window_size}，跳过")
            return historical_data
        
        # 定义需要的字段
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        # 生成历史期间并直接进行筛选和预处理
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
        
        self.logger.info(f"自身历史数据收集完成: 有效期间={valid_periods}, 无效期间={invalid_periods}")
        return historical_data
    
    def _collect_comparison_historical_data(self, earliest_eval_date):
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
    
    def _collect_comparison_historical_data_multiprocess(self, earliest_eval_date):
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
    
    def estimate_memory_requirement(self, evaluation_days, num_stocks, window_size, num_fields):
        """估算显存需求（GB）"""
        # 计算张量大小
        # 目标数据: [evaluation_days, window_size, num_fields]
        target_size = evaluation_days * window_size * num_fields * 4  # float32 = 4 bytes
        
        # 对比数据: [num_stocks, evaluation_days, window_size, num_fields]
        comparison_size = num_stocks * evaluation_days * window_size * num_fields * 4
        
        # 相关系数结果: [num_stocks, evaluation_days, num_fields]
        correlation_size = num_stocks * evaluation_days * num_fields * 4
        
        # 中间计算缓存（估算为2倍）
        intermediate_size = (target_size + comparison_size) * 2
        
        # 总显存需求
        total_bytes = target_size + comparison_size + correlation_size + intermediate_size
        total_gb = total_bytes / 1024**3
        
        self.logger.info(f"📊 显存需求估算:")
        self.logger.info(f"   评测日期数: {evaluation_days}")
        self.logger.info(f"   股票数量: {num_stocks}")
        self.logger.info(f"   窗口大小: {window_size}")
        self.logger.info(f"   预计显存需求: {total_gb:.2f}GB")
        
        return total_gb
    
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
    
    def _log_performance_summary(self):
        """输出分层性能总结"""
        self.logger.info("=" * 80)
        self.logger.info("📊 分层性能统计总结 (按执行顺序)")
        self.logger.info("=" * 80)
        
        # 获取性能统计
        stats = self._get_performance_stats()
        
        # 定义步骤映射和显示顺序
        step_mapping = {
            # 第1阶段：数据加载
            'target_stock_loading': ('1-1', '目标股票数据加载'),
            'comparison_stocks_loading': ('1-2', '对比股票数据加载'),
            
            # 第2阶段：数据准备
            'evaluation_dates_preparation': ('2-1', '评测日期准备'),
            'batch_data_preparation': ('2-2', '批量数据准备'),
            
            # 第3阶段：历史数据收集
            'historical_data_collection': ('3-1', '历史数据收集'),
            
            # 第4阶段：GPU计算（详细拆分为5个子步骤）
            'gpu_step1_data_preparation': ('4-1', '历史数据准备和筛选'),
            'gpu_step2_tensor_creation': ('4-2', '创建GPU历史数据张量'),
            'gpu_step3_correlation_calculation': ('4-3', '批量相关系数计算'),
            'gpu_step4_batch_merging': ('4-4', '合并批次结果'),
            'gpu_step5_result_processing': ('4-5', '处理批量相关性结果'),
            
            # 第5阶段：结果处理
            'batch_result_processing': ('5-1', '相关性结果处理'),
            
            # 第6阶段：最终处理
            'batch_results_processing': ('6-1', '批量结果整合'),
            
            # 总体统计
            'total_batch_analysis': ('总计', '完整批量分析')
        }
        
        # 按步骤顺序显示
        current_stage = 0
        stage_names = {
            1: "🔄 第1阶段：数据加载",
            2: "📋 第2阶段：数据准备", 
            3: "📚 第3阶段：历史数据收集",
            4: "🚀 第4阶段：GPU计算",
            5: "⚙️  第5阶段：结果处理",
            6: "📊 第6阶段：最终处理"
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
        """保存批量结果到CSV文件 - 逐日详细记录"""
        try:
            batch_results = result['batch_results']
            evaluation_dates = result['evaluation_dates']
            
            # 读取现有CSV文件
            if os.path.exists(self.csv_results_file):
                df = pd.read_csv(self.csv_results_file, encoding='utf-8-sig', dtype={'代码': str})
            else:
                df = pd.DataFrame()
            
            # 为每个评测日期创建一行记录
            new_rows = []
            for i, daily_result in enumerate(batch_results['detailed_results']):
                evaluation_date = evaluation_dates[i]
                prediction_stats = daily_result.get('prediction_stats', {})
                
                # 计算对比股票数量
                # 在self_only模式下，只对比自身历史数据，不需要额外加1
                # 在其他模式下，需要加上目标股票自身
                if self.comparison_mode == 'self_only':
                    comparison_stock_count = len(self.comparison_stocks)
                else:
                    comparison_stock_count = len(self.comparison_stocks) + 1
                
                # 准备单日结果数据
                row_data = {
                    '代码': str(result['stock_code']),
                    'window_size': result['window_size'],
                    '阈值': result['threshold'],
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
            
            # 添加所有新行
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                df = pd.concat([df, new_df], ignore_index=True)
                
                # 确保代码列为字符串类型
                df['代码'] = df['代码'].astype(str)
                
                # 按评测日期降序排列（最新日期在前）
                df['评测日期_排序'] = pd.to_datetime(df['评测日期'])
                df = df.sort_values('评测日期_排序', ascending=False)
                df = df.drop('评测日期_排序', axis=1)  # 删除临时排序列
                df = df.reset_index(drop=True)  # 重置索引
                
                # 保存CSV文件
                df.to_csv(self.csv_results_file, index=False, encoding='utf-8-sig')
                
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
                                         num_processes=None):
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
        num_processes=num_processes
    )
    
    result = analyzer.analyze_batch()
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GPU批量评测Pearson相关性分析')
    parser.add_argument('stock_code', help='股票代码')
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

    args = parser.parse_args()
    
    print(f"开始GPU批量评测分析，股票代码: {args.stock_code}")
    print(f"评测日期数量: {args.evaluation_days}")
    print(f"窗口大小: {args.window_size}")
    print(f"相关系数阈值: {args.threshold}")
    
    result = analyze_pearson_correlation_gpu_batch(
        stock_code=args.stock_code,
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
        num_processes=args.num_processes
    )
    
    if result:
        print(f"分析完成，评测了 {result['evaluation_days']} 个日期")
        print(f"总高相关性期间: {result['batch_results']['summary']['total_high_correlations']}")
        print(f"平均每日高相关数量: {result['batch_results']['summary']['avg_high_correlations_per_day']:.2f}")
    else:
        print("分析失败")