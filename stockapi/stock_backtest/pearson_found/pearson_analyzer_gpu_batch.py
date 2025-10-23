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
7. 真正的TopN模式（N个股票同时期数据矩阵比较）

使用方法：
python pearson_analyzer_gpu_batch.py --stock_code 000001 --evaluation_days 100

作者：Stock Backtest System
创建时间：2024年
GPU批量优化版本：2024年
TopN模式增强版本：2024年
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

# 忽略一些不重要的警告
warnings.filterwarnings('ignore', category=UserWarning)


class GPUBatchPearsonAnalyzer:
    def __init__(self, stock_code, log_dir='logs', window_size=15, threshold=0.9, 
                 evaluation_days=100, debug=False, comparison_stocks=None, 
                 comparison_mode='top10', backtest_date=None, 
                 csv_filename='evaluation_results.csv', use_gpu=True, 
                 batch_size=1000, gpu_memory_limit=0.8, topn_mode=True, 
                 max_comparison_stocks=10):
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
            topn_mode: 是否启用TopN模式（N个股票同时期数据矩阵比较）
            max_comparison_stocks: TopN模式下最大对比股票数量
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
        self.use_gpu = use_gpu
        self.batch_size = batch_size
        self.gpu_memory_limit = gpu_memory_limit
        self.topn_mode = topn_mode  # 新增：TopN模式开关
        self.max_comparison_stocks = max_comparison_stocks  # 新增：最大对比股票数量
        self.data_loader = None
        self.logger = None
        
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
        
        # TopN模式下限制对比股票数量
        if self.topn_mode and len(self.comparison_stocks) > self.max_comparison_stocks:
            self.comparison_stocks = self.comparison_stocks[:self.max_comparison_stocks]
        
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
    
    def start_timer(self, timer_name):
        """开始计时"""
        self.current_timers[timer_name] = time.time()
        if self.debug:
            self.logger.info(f"⏱️ 开始计时: {timer_name}")
    
    def end_timer(self, timer_name):
        """结束计时并记录耗时"""
        if timer_name in self.current_timers:
            elapsed_time = time.time() - self.current_timers[timer_name]
            self.performance_timers[timer_name].append(elapsed_time)
            del self.current_timers[timer_name]
            if self.debug:
                self.logger.info(f"⏱️ 结束计时: {timer_name} - 耗时: {elapsed_time:.3f}秒")
            return elapsed_time
        return 0
    
    def load_data(self):
        """加载目标股票数据"""
        self.start_timer('target_stock_loading')
        self.logger.info("初始化数据加载器")
        self.data_loader = StockDataLoader()
        
        self.logger.info(f"开始加载目标股票 {self.stock_code} 的数据")
        data = self.data_loader.load_stock_data(self.stock_code)
        
        if data is None or data.empty:
            self.logger.error(f"无法加载股票 {self.stock_code} 的数据")
            self.end_timer('target_stock_loading')
            return None
        
        self.data = self._filter_data(data, self.stock_code)
        self.end_timer('target_stock_loading')
        
        # 加载对比股票数据
        self._load_comparison_stocks_data()
        
        return self.data
    
    def _filter_data(self, data, stock_code):
        """过滤股票数据，确保数据质量"""
        if data is None or data.empty:
            return data
            
        original_count = len(data)
        data = data[
            (data['open'] > 0) & 
            (data['high'] > 0) & 
            (data['low'] > 0) & 
            (data['close'] > 0) & 
            (data['volume'] > 0)
        ]
        filtered_count = len(data)
        removed_count = original_count - filtered_count
        
        if removed_count > 0:
            self.logger.info(f"股票 {stock_code} 数据过滤完成，移除 {removed_count} 条异常数据")
        
        if not data.empty:
            self.logger.info(f"股票 {stock_code} 成功加载 {len(data)} 条记录，日期范围: {data.index[0]} 到 {data.index[-1]}")
        
        return data
    
    def _load_comparison_stocks_data(self):
        """加载对比股票数据"""
        if self.comparison_mode == 'self_only':
            self.logger.info("使用自身历史数据对比模式，跳过其他股票数据加载")
            return
        
        self.start_timer('comparison_stocks_loading')
        self.logger.info(f"开始加载 {len(self.comparison_stocks)} 只对比股票的数据")
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
        
        self.logger.info(f"成功加载 {successful_loads} 只对比股票的数据")
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
            # 获取该评测日期的窗口数据
            recent_data = self.data[self.data.index < eval_date].tail(self.window_size)
            
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
    
    def calculate_batch_gpu_correlation(self, batch_recent_data, historical_periods_data):
        """
        批量GPU相关性计算
        
        Args:
            batch_recent_data: 批量评测数据 [evaluation_days, window_size, 5]
            historical_periods_data: 历史期间数据列表
            
        Returns:
            dict: 批量相关性结果
        """
        self.start_timer('batch_gpu_correlation')
        
        if batch_recent_data is None or len(historical_periods_data) == 0:
            self.end_timer('batch_gpu_correlation')
            return {}
        
        evaluation_days, window_size, num_fields = batch_recent_data.shape
        num_historical_periods = len(historical_periods_data)
        
        self.logger.info(f"开始批量GPU相关性计算")
        self.logger.info(f"评测日期数: {evaluation_days}, 历史期间数: {num_historical_periods}")
        
        # 准备历史数据张量 [num_historical_periods, window_size, 5]
        historical_data_list = []
        period_info_list = []
        
        for data, start_date, end_date, stock_code in historical_periods_data:
            if len(data) == window_size:
                fields = ['open', 'high', 'low', 'close', 'volume']
                historical_values = data[fields].values
                historical_data_list.append(historical_values)
                period_info_list.append({
                    'start_date': start_date,
                    'end_date': end_date,
                    'stock_code': stock_code
                })
        
        if not historical_data_list:
            self.logger.warning("没有有效的历史期间数据")
            self.end_timer('batch_gpu_correlation')
            return {}
        
        historical_tensor = torch.tensor(
            np.stack(historical_data_list, axis=0), 
            dtype=torch.float32, 
            device=self.device
        )  # [num_historical_periods, window_size, 5]
        
        # 批量计算相关系数
        # 扩展维度进行批量计算
        # batch_recent_data: [evaluation_days, window_size, 5]
        # historical_tensor: [num_historical_periods, window_size, 5]
        # 目标: [evaluation_days, num_historical_periods, 5]
        
        batch_correlations = []
        
        # 分批处理以避免内存溢出
        batch_size = min(self.batch_size, evaluation_days)
        
        for i in range(0, evaluation_days, batch_size):
            end_idx = min(i + batch_size, evaluation_days)
            current_batch = batch_recent_data[i:end_idx]  # [batch_size, window_size, 5]
            
            # 计算当前批次的相关系数
            batch_corr = self._compute_correlation_matrix(current_batch, historical_tensor)
            batch_correlations.append(batch_corr)
        
        # 合并所有批次的结果
        all_correlations = torch.cat(batch_correlations, dim=0)  # [evaluation_days, num_historical_periods, 5]
        
        self.logger.info(f"批量GPU相关性计算完成，结果形状: {all_correlations.shape}")
        
        # 处理结果
        results = self._process_batch_correlation_results(
            all_correlations, period_info_list, evaluation_days
        )
        
        self.end_timer('batch_gpu_correlation')
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
        
        # 扩展维度进行广播计算
        recent_expanded = recent_batch.unsqueeze(1)  # [batch_size, 1, window_size, 5]
        historical_expanded = historical_tensor.unsqueeze(0)  # [1, num_historical_periods, window_size, 5]
        
        # 计算均值
        recent_mean = recent_expanded.mean(dim=2, keepdim=True)  # [batch_size, 1, 1, 5]
        historical_mean = historical_expanded.mean(dim=2, keepdim=True)  # [1, num_historical_periods, 1, 5]
        
        # 中心化
        recent_centered = recent_expanded - recent_mean
        historical_centered = historical_expanded - historical_mean
        
        # 计算协方差
        covariance = (recent_centered * historical_centered).sum(dim=2)  # [batch_size, num_historical_periods, 5]
        
        # 计算标准差
        recent_std = torch.sqrt((recent_centered ** 2).sum(dim=2))  # [batch_size, 1, 5]
        historical_std = torch.sqrt((historical_centered ** 2).sum(dim=2))  # [1, num_historical_periods, 5]
        
        # 计算相关系数
        correlation = covariance / (recent_std * historical_std + 1e-8)
        
        return correlation
    
    def _process_batch_correlation_results(self, correlations_tensor, period_info_list, evaluation_days):
        """
        处理批量相关性计算结果
        
        Args:
            correlations_tensor: [evaluation_days, num_historical_periods, 5]
            period_info_list: 历史期间信息列表
            evaluation_days: 评测日期数量
            
        Returns:
            dict: 处理后的结果
        """
        self.start_timer('batch_result_processing')
        
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
        
        # 统计结果
        results = {
            'evaluation_days': evaluation_days,
            'num_historical_periods': len(period_info_list),
            'high_correlation_counts': high_corr_mask.sum(axis=1).tolist(),  # 每个评测日期的高相关数量
            'avg_correlations': avg_correlations_filtered.tolist(),  # 使用过滤后的相关系数
            'detailed_correlations': correlations_np.tolist(),
            'period_info': period_info_list,
            'summary': {
                'total_high_correlations': high_corr_mask.sum(),
                'avg_high_correlations_per_day': high_corr_mask.sum(axis=1).mean(),
                'max_high_correlations_per_day': high_corr_mask.sum(axis=1).max(),
                'overall_avg_correlation': avg_correlations_filtered[high_corr_mask].mean() if high_corr_mask.any() else 0,
                'filtered_self_correlations': int(filtered_count)  # 添加过滤统计
            }
        }
        
        self.logger.info(f"批量结果处理完成")
        self.logger.info(f"总高相关性期间: {results['summary']['total_high_correlations']}")
        self.logger.info(f"平均每日高相关数: {results['summary']['avg_high_correlations_per_day']:.2f}")
        
        self.end_timer('batch_result_processing')
        return results
    
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
    
    def process_batch_results(self, batch_correlations, evaluation_dates, historical_periods_data):
        """
        处理批量相关性结果
        
        Args:
            batch_correlations: 批量相关性结果字典
            evaluation_dates: 评测日期列表
            historical_periods_data: 历史期间数据列表
            
        Returns:
            dict: 处理后的批量结果
        """
        self.start_timer('batch_results_processing')
        
        # 从batch_correlations中提取数据
        avg_correlations = batch_correlations.get('avg_correlations', [])  # [evaluation_days, num_historical_periods]
        summary = batch_correlations.get('summary', {})
        period_info = batch_correlations.get('period_info', [])
        
        # 构建详细结果
        detailed_results = []
        
        for eval_idx, eval_date in enumerate(evaluation_dates):
            if eval_idx < len(avg_correlations):
                eval_avg_correlations = avg_correlations[eval_idx]  # 该评测日期的平均相关性列表
                
                # 找到高相关性期间
                high_corr_periods = []
                for hist_idx, avg_correlation in enumerate(eval_avg_correlations):
                    if avg_correlation >= self.threshold and hist_idx < len(period_info):
                        period_data = period_info[hist_idx]
                        
                        high_corr_periods.append({
                            'start_date': period_data['start_date'],
                            'end_date': period_data['end_date'],
                            'avg_correlation': float(avg_correlation),
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
        
        # 构建最终结果
        batch_results = {
            'detailed_results': detailed_results,
            'num_historical_periods': len(historical_periods_data),
            'summary': summary
        }
        
        self.logger.info("批量结果处理完成")
        self.logger.info(f"总高相关性期间: {summary.get('total_high_correlations', 0)}")
        self.logger.info(f"平均每日高相关数量: {summary.get('avg_high_correlations_per_day', 0):.2f}")
        
        self.end_timer('batch_results_processing')
        return batch_results
    
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
        
        # 加载数据
        if not hasattr(self, 'data') or self.data is None:
            self.data = self.load_data()
            if self.data is None:
                self.logger.error("数据加载失败")
                return None
        
        # 准备评测日期
        evaluation_dates = self.prepare_evaluation_dates(self.backtest_date)
        
        if not evaluation_dates:
            self.logger.error("没有有效的评测日期")
            return None
        
        # 准备批量评测数据
        batch_recent_data, valid_dates = self.prepare_batch_evaluation_data(evaluation_dates)
        
        if batch_recent_data is None:
            self.logger.error("批量评测数据准备失败")
            return None
        
        # 收集历史期间数据
        earliest_eval_date = min(valid_dates)
        historical_periods_data = self._collect_historical_periods_data(earliest_eval_date)
        
        if not historical_periods_data:
            self.logger.error("没有有效的历史期间数据")
            return None
        
        # 执行批量GPU相关性计算
        batch_correlations = self.calculate_batch_gpu_correlation(batch_recent_data, historical_periods_data)
        
        if not batch_correlations:
            self.logger.error("批量相关性计算失败")
            return None
        
        # 处理批量结果
        batch_results = self.process_batch_results(batch_correlations, valid_dates, historical_periods_data)
        
        # 保存结果标志（添加缺失的属性）
        self.save_results = True
        
        # 保存结果
        if self.save_results:
            # 构建完整结果用于保存
            save_result = {
                'stock_code': self.stock_code,
                'backtest_date': self.backtest_date,
                'evaluation_days': len(valid_dates),
                'window_size': self.window_size,
                'threshold': self.threshold,
                'evaluation_dates': valid_dates,
                'batch_results': batch_results
            }
            self.save_batch_results_to_csv(save_result)
        
        # 构建最终结果
        final_result = {
            'stock_code': self.stock_code,
            'backtest_date': self.backtest_date,
            'evaluation_days': len(valid_dates),
            'window_size': self.window_size,
            'threshold': self.threshold,
            'evaluation_dates': valid_dates,
            'batch_results': batch_results,
            'performance_stats': self._get_performance_stats()
        }
        
        self.end_timer('total_batch_analysis')
        
        # 输出性能总结
        self._log_performance_summary()
        
        # 输出分析总结
        self.logger.info("=" * 80)
        self.logger.info("批量分析结果总结:")
        self.logger.info(f"评测日期数量: {len(valid_dates)}")
        self.logger.info(f"总高相关性期间: {batch_results['summary']['total_high_correlations']}")
        self.logger.info(f"平均每日高相关数量: {batch_results['summary']['avg_high_correlations_per_day']:.2f}")
        self.logger.info(f"最大每日高相关数量: {batch_results['summary']['max_high_correlations_per_day']}")
        if batch_results['summary']['overall_avg_correlation'] > 0:
            self.logger.info(f"整体平均相关系数: {batch_results['summary']['overall_avg_correlation']:.4f}")
        self.logger.info("=" * 80)
        
        return final_result
    
    def _collect_historical_periods_data(self, earliest_eval_date):
        """收集历史期间数据"""
        self.start_timer('historical_data_collection')
        
        historical_periods_data = []
        
        # 收集自身历史数据
        self_historical_data = self._collect_self_historical_data(earliest_eval_date)
        historical_periods_data.extend(self_historical_data)
        
        # 收集对比股票数据
        if self.comparison_mode != 'self_only':
            comparison_historical_data = self._collect_comparison_historical_data(earliest_eval_date)
            historical_periods_data.extend(comparison_historical_data)
        
        self.logger.info(f"收集到 {len(historical_periods_data)} 个历史期间数据")
        self.end_timer('historical_data_collection')
        return historical_periods_data
    
    def _collect_self_historical_data(self, earliest_eval_date):
        """收集自身历史数据"""
        historical_data = []
        
        # 使用所有可用数据，不进行日期截断
        available_data = self.data
        
        if len(available_data) < self.window_size:
            return historical_data
        
        # 生成历史期间
        for i in range(len(available_data) - self.window_size + 1):
            period_data = available_data.iloc[i:i + self.window_size]
            start_date = period_data.index[0]
            end_date = period_data.index[-1]
            
            historical_data.append((period_data, start_date, end_date, self.stock_code))
        
        self.logger.info(f"收集到 {len(historical_data)} 个自身历史期间（包含所有可用数据）")
        return historical_data
    
    def _collect_comparison_historical_data(self, earliest_eval_date):
        """收集对比股票历史数据"""
        historical_data = []
        
        for stock_code, stock_data in self.loaded_stocks_data.items():
            # 使用所有可用数据，不进行日期截断
            available_data = stock_data
            
            if len(available_data) < self.window_size:
                continue
            
            # 生成该股票的历史期间
            for i in range(len(available_data) - self.window_size + 1):
                period_data = available_data.iloc[i:i + self.window_size]
                start_date = period_data.index[0]
                end_date = period_data.index[-1]
                
                historical_data.append((period_data, start_date, end_date, stock_code))
        
        self.logger.info(f"收集到 {len(historical_data)} 个对比股票历史期间（包含所有可用数据）")
        return historical_data
    
    def _implement_topn_mode(self, comparison_stocks_data):
        """实现TopN模式"""
        max_stocks = self.max_comparison_stocks
        
        self.logger.info(f"启动TopN模式，最大对比股票数: {max_stocks}")
        
        # 如果股票数量已经在限制内，直接返回
        if len(comparison_stocks_data) <= max_stocks:
            self.logger.info(f"✅ 当前股票数量 {len(comparison_stocks_data)} 在TopN限制内")
            return comparison_stocks_data
        
        # 根据数据质量和可用性选择TopN股票
        stock_scores = []
        
        for stock_code, stock_data in comparison_stocks_data.items():
            # 计算股票数据质量分数
            data_length = len(stock_data)
            data_completeness = 1.0 - (stock_data.isnull().sum().sum() / (len(stock_data) * len(stock_data.columns)))
            
            # 计算数据的时间跨度
            date_range = (stock_data.index[-1] - stock_data.index[0]).days
            
            # 综合评分
            score = data_length * 0.4 + data_completeness * 0.3 + (date_range / 365) * 0.3
            
            stock_scores.append((stock_code, score, data_length))
        
        # 按分数排序，选择TopN
        stock_scores.sort(key=lambda x: x[1], reverse=True)
        selected_stocks = stock_scores[:max_stocks]
        
        self.logger.info(f"📊 TopN股票选择结果:")
        for i, (stock_code, score, data_length) in enumerate(selected_stocks, 1):
            self.logger.info(f"   Top{i}: {stock_code} (评分: {score:.2f}, 数据量: {data_length})")
        
        # 构建TopN股票数据字典
        topn_data = {}
        for stock_code, score, data_length in selected_stocks:
            topn_data[stock_code] = comparison_stocks_data[stock_code]
        
        self.logger.info(f"✅ TopN模式完成，从 {len(comparison_stocks_data)} 只股票中选择了 {len(topn_data)} 只")
        
        return topn_data
    
    def prepare_topn_matrix_comparison(self, evaluation_dates, topn_stocks_data):
        """准备TopN模式的矩阵比较数据"""
        self.logger.info(f"🔄 准备TopN矩阵比较数据")
        
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        # 为每个评测日期准备目标股票数据
        target_matrices = []
        valid_eval_dates = []
        
        for eval_date in evaluation_dates:
            target_recent_data = self.data[self.data.index < eval_date].tail(self.window_size)
            
            if len(target_recent_data) == self.window_size:
                target_matrix = target_recent_data[fields].values  # [window_size, 5]
                target_matrices.append(target_matrix)
                valid_eval_dates.append(eval_date)
        
        if not target_matrices:
            self.logger.error("没有有效的目标股票评测数据")
            return None, None, []
        
        # 转换为张量 [evaluation_days, window_size, 5]
        target_tensor = torch.tensor(np.stack(target_matrices, axis=0), dtype=torch.float32, device=self.device)
        
        # 为每个TopN股票准备同时期数据矩阵
        topn_matrices = []
        topn_stock_codes = []
        
        for stock_code, stock_data in topn_stocks_data.items():
            stock_matrices = []
            
            for eval_date in valid_eval_dates:
                # 获取该股票在同一评测日期的同时期数据
                stock_recent_data = stock_data[stock_data.index < eval_date].tail(self.window_size)
                
                if len(stock_recent_data) == self.window_size:
                    stock_matrix = stock_recent_data[fields].values  # [window_size, 5]
                    stock_matrices.append(stock_matrix)
                else:
                    # 如果数据不足，用零矩阵填充
                    stock_matrices.append(np.zeros((self.window_size, len(fields))))
            
            if stock_matrices:
                # [evaluation_days, window_size, 5]
                stock_tensor = torch.tensor(np.stack(stock_matrices, axis=0), dtype=torch.float32, device=self.device)
                topn_matrices.append(stock_tensor)
                topn_stock_codes.append(stock_code)
        
        if not topn_matrices:
            self.logger.error("没有有效的TopN股票数据")
            return None, None, []
        
        # 合并所有TopN股票数据 [num_stocks, evaluation_days, window_size, 5]
        topn_tensor = torch.stack(topn_matrices, dim=0)
        
        self.logger.info(f"✅ TopN矩阵数据准备完成")
        self.logger.info(f"   目标股票数据形状: {target_tensor.shape}")
        self.logger.info(f"   TopN股票数据形状: {topn_tensor.shape}")
        self.logger.info(f"   TopN股票数量: {len(topn_stock_codes)}")
        
        return target_tensor, topn_tensor, topn_stock_codes
    
    def calculate_topn_correlations(self, target_tensor, topn_tensor, topn_stock_codes):
        """计算TopN模式的相关系数"""
        self.start_timer('topn_correlation_calculation')
        
        num_stocks, evaluation_days, window_size, num_fields = topn_tensor.shape
        
        self.logger.info(f"🔄 开始TopN相关性计算")
        self.logger.info(f"   股票数量: {num_stocks}")
        self.logger.info(f"   评测日期数: {evaluation_days}")
        
        # 监控显存
        self.monitor_gpu_memory("TopN计算开始")
        
        all_correlations = []
        
        # 对每只TopN股票计算与目标股票的相关性
        for stock_idx, stock_code in enumerate(topn_stock_codes):
            stock_data = topn_tensor[stock_idx]  # [evaluation_days, window_size, 5]
            
            # 计算相关系数 [evaluation_days, 5]
            stock_correlations = self._compute_topn_correlation(target_tensor, stock_data)
            all_correlations.append(stock_correlations)
            
            if self.debug:
                self.logger.info(f"   完成股票 {stock_code} 的相关性计算")
        
        # 合并结果 [num_stocks, evaluation_days, 5]
        correlations_tensor = torch.stack(all_correlations, dim=0)
        
        # 监控显存
        self.monitor_gpu_memory("TopN计算完成")
        
        self.logger.info(f"✅ TopN相关性计算完成，结果形状: {correlations_tensor.shape}")
        
        self.end_timer('topn_correlation_calculation')
        
        return correlations_tensor
    
    def _compute_topn_correlation(self, target_data, comparison_data):
        """计算TopN模式下单只股票的相关系数"""
        # target_data: [evaluation_days, window_size, 5]
        # comparison_data: [evaluation_days, window_size, 5]
        
        # 计算均值
        target_mean = target_data.mean(dim=1, keepdim=True)  # [evaluation_days, 1, 5]
        comparison_mean = comparison_data.mean(dim=1, keepdim=True)  # [evaluation_days, 1, 5]
        
        # 中心化
        target_centered = target_data - target_mean
        comparison_centered = comparison_data - comparison_mean
        
        # 计算协方差
        covariance = (target_centered * comparison_centered).sum(dim=1)  # [evaluation_days, 5]
        
        # 计算标准差
        target_std = torch.sqrt((target_centered ** 2).sum(dim=1))  # [evaluation_days, 5]
        comparison_std = torch.sqrt((comparison_centered ** 2).sum(dim=1))  # [evaluation_days, 5]
        
        # 计算相关系数
        correlation = covariance / (target_std * comparison_std + 1e-8)
        
        return correlation
    
    def process_topn_results(self, correlations_tensor, topn_stock_codes, evaluation_dates):
        """处理TopN模式的结果"""
        self.start_timer('topn_result_processing')
        
        num_stocks, evaluation_days, num_fields = correlations_tensor.shape
        correlations_np = correlations_tensor.cpu().numpy()
        
        # 计算平均相关系数 [num_stocks, evaluation_days]
        avg_correlations = correlations_np.mean(axis=2)
        
        # 构建结果
        topn_results = {
            'num_stocks': num_stocks,
            'evaluation_days': evaluation_days,
            'stock_codes': topn_stock_codes,
            'avg_correlations': avg_correlations.tolist(),
            'detailed_correlations': correlations_np.tolist(),
            'high_correlation_summary': {}
        }
        
        # 统计高相关性
        total_high_correlations = 0
        daily_high_counts = []
        
        for eval_idx in range(evaluation_days):
            daily_high_count = 0
            for stock_idx in range(num_stocks):
                if avg_correlations[stock_idx, eval_idx] > self.threshold:
                    daily_high_count += 1
                    total_high_correlations += 1
            daily_high_counts.append(daily_high_count)
        
        topn_results['high_correlation_summary'] = {
            'total_high_correlations': total_high_correlations,
            'daily_high_counts': daily_high_counts,
            'avg_high_per_day': np.mean(daily_high_counts),
            'max_high_per_day': max(daily_high_counts) if daily_high_counts else 0
        }
        
        self.logger.info(f"✅ TopN结果处理完成")
        self.logger.info(f"   总高相关性: {total_high_correlations}")
        self.logger.info(f"   平均每日高相关数: {np.mean(daily_high_counts):.2f}")
        
        self.end_timer('topn_result_processing')
        
        return topn_results
    
    def analyze_topn_mode(self, evaluation_dates):
        """执行TopN模式分析"""
        if not self.topn_mode:
            self.logger.info("TopN模式未启用，跳过TopN分析")
            return None
        
        self.start_timer('topn_mode_analysis')
        
        self.logger.info("🔝 开始TopN模式分析")
        
        # 实现TopN股票选择
        topn_stocks_data = self._implement_topn_mode(self.loaded_stocks_data)
        
        if not topn_stocks_data:
            self.logger.warning("没有可用的TopN股票数据")
            self.end_timer('topn_mode_analysis')
            return None
        
        # 准备TopN矩阵比较数据
        target_tensor, topn_tensor, topn_stock_codes = self.prepare_topn_matrix_comparison(
            evaluation_dates, topn_stocks_data
        )
        
        if target_tensor is None or topn_tensor is None:
            self.logger.error("TopN矩阵数据准备失败")
            self.end_timer('topn_mode_analysis')
            return None
        
        # 检查显存需求
        evaluation_days = target_tensor.shape[0]
        num_stocks = topn_tensor.shape[0]
        
        # 估算TopN模式的显存需求
        topn_memory_required = self.estimate_memory_requirement(
            evaluation_days, num_stocks, self.window_size, 5
        )
        
        # 根据显存情况选择处理方式
        if self.check_gpu_memory_limit(topn_memory_required):
            # 显存充足，直接计算
            correlations_tensor = self.calculate_topn_correlations(
                target_tensor, topn_tensor, topn_stock_codes
            )
        else:
            # 显存不足，使用自适应处理
            self.logger.info("🔄 TopN模式显存不足，启用自适应处理")
            correlations_tensor = self._adaptive_topn_processing(
                target_tensor, topn_tensor, topn_stock_codes
            )
        
        if correlations_tensor is None:
            self.logger.error("TopN相关性计算失败")
            self.end_timer('topn_mode_analysis')
            return None
        
        # 处理TopN结果
        topn_results = self.process_topn_results(
            correlations_tensor, topn_stock_codes, evaluation_dates
        )
        
        self.end_timer('topn_mode_analysis')
        
        self.logger.info("✅ TopN模式分析完成")
        return topn_results
    
    def _adaptive_topn_processing(self, target_tensor, topn_tensor, topn_stock_codes):
        """TopN模式的自适应处理"""
        num_stocks, evaluation_days, window_size, num_fields = topn_tensor.shape
        
        # 计算每次可以处理的股票数量
        if self.device.type == 'cuda':
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            available_memory = total_memory * self.gpu_memory_limit * 0.8
        else:
            available_memory = 4.0
        
        # 估算单只股票的显存需求
        single_stock_memory = self.estimate_memory_requirement(
            evaluation_days, 1, window_size, num_fields
        )
        
        # 计算批次大小
        stocks_per_batch = max(1, int(available_memory / single_stock_memory))
        stocks_per_batch = min(stocks_per_batch, num_stocks)
        
        self.logger.info(f"📦 TopN自适应处理参数:")
        self.logger.info(f"   总股票数: {num_stocks}")
        self.logger.info(f"   每批股票数: {stocks_per_batch}")
        self.logger.info(f"   预计批次数: {(num_stocks + stocks_per_batch - 1) // stocks_per_batch}")
        
        all_correlations = []
        
        for i in range(0, num_stocks, stocks_per_batch):
            end_idx = min(i + stocks_per_batch, num_stocks)
            batch_stocks = topn_tensor[i:end_idx]  # [batch_size, evaluation_days, window_size, 5]
            batch_codes = topn_stock_codes[i:end_idx]
            
            self.logger.info(f"🔄 处理TopN第 {i//stocks_per_batch + 1} 批 (股票 {i+1}-{end_idx})")
            
            # 清理GPU缓存
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
                gc.collect()
            
            # 监控显存
            self.monitor_gpu_memory(f"TopN批次{i//stocks_per_batch + 1}开始")
            
            # 处理当前批次
            batch_correlations = []
            for stock_idx, stock_code in enumerate(batch_codes):
                stock_data = batch_stocks[stock_idx]  # [evaluation_days, window_size, 5]
                stock_correlations = self._compute_topn_correlation(target_tensor, stock_data)
                batch_correlations.append(stock_correlations)
            
            # 合并当前批次结果
            batch_tensor = torch.stack(batch_correlations, dim=0)
            all_correlations.append(batch_tensor)
            
            # 监控显存
            self.monitor_gpu_memory(f"TopN批次{i//stocks_per_batch + 1}完成")
        
        # 合并所有批次结果
        if all_correlations:
            final_correlations = torch.cat(all_correlations, dim=0)
            self.logger.info("✅ TopN自适应处理完成")
            return final_correlations
        else:
            return None
    
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
        for timer_name, times in self.performance_timers.items():
            if times:
                stats[timer_name] = {
                    'total_time': sum(times),
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times),
                    'count': len(times)
                }
        
        # 添加GPU显存统计
        if self.device.type == 'cuda':
            stats['gpu_memory'] = self.gpu_memory_stats.copy()
        
        return stats
    
    def _log_performance_summary(self):
        """输出性能总结"""
        self.logger.info("=" * 60)
        self.logger.info("性能统计总结:")
        
        for timer_name, times in self.performance_timers.items():
            if times:
                total_time = sum(times)
                avg_time = total_time / len(times)
                self.logger.info(f"  {timer_name}: 总耗时={total_time:.3f}秒, 平均={avg_time:.3f}秒, 次数={len(times)}")
        
        # GPU显存统计
        if self.device.type == 'cuda':
            self.logger.info("GPU显存统计:")
            self.logger.info(f"  峰值已分配: {self.gpu_memory_stats['peak_allocated']:.2f}GB")
            self.logger.info(f"  峰值已保留: {self.gpu_memory_stats['peak_reserved']:.2f}GB")
            self.logger.info(f"  当前已分配: {self.gpu_memory_stats['current_allocated']:.2f}GB")
            self.logger.info(f"  当前已保留: {self.gpu_memory_stats['current_reserved']:.2f}GB")
        
        self.logger.info("=" * 60)
    
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
                    '下1日高开': f"{prediction_stats.get('next_day_gap_up_rate', 0):.2%}" if prediction_stats else 'N/A',
                    '下1日上涨': f"{prediction_stats.get('next_1_day_up_rate', 0):.2%}" if prediction_stats else 'N/A',
                    '下3日上涨': f"{prediction_stats.get('next_3_day_up_rate', 0):.2%}" if prediction_stats else 'N/A',
                    '下5日上涨': f"{prediction_stats.get('next_5_day_up_rate', 0):.2%}" if prediction_stats else 'N/A',
                    '下10日上涨': f"{prediction_stats.get('next_10_day_up_rate', 0):.2%}" if prediction_stats else 'N/A'
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


def analyze_pearson_correlation_gpu_batch(stock_code, backtest_date=None, evaluation_days=100, 
                                         window_size=15, threshold=0.9, comparison_mode='default', 
                                         comparison_stocks=None, debug=False, csv_filename=None, 
                                         use_gpu=True, batch_size=1000):
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
        batch_size=batch_size
    )
    
    result = analyzer.analyze_batch()
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GPU批量评测Pearson相关性分析')
    parser.add_argument('--stock_code', type=str, required=True, help='股票代码')
    parser.add_argument('--backtest_date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--evaluation_days', type=int, default=100, help='评测日期数量')
    parser.add_argument('--window_size', type=int, default=15, help='分析窗口大小')
    parser.add_argument('--threshold', type=float, default=0.9, help='相关系数阈值')
    parser.add_argument('--comparison_mode', type=str, default='top10', 
                       choices=['top10', 'industry', 'self_only'],
                       help='对比模式: top10(市值前10), industry(行业股票), self_only(仅自身历史)')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')
    parser.add_argument('--csv_filename', type=str, default='evaluation_results.csv', help='CSV结果文件名')
    parser.add_argument('--use_gpu', action='store_true', default=True, help='使用GPU加速')
    parser.add_argument('--batch_size', type=int, default=1000, 
                       help='GPU批处理大小 - 控制单次GPU计算的数据量，影响内存使用和计算效率。'
                            '推荐值：RTX 3060(8GB)=500-1000, RTX 3080(10GB)=1000-2000, RTX 4090(24GB)=2000-5000')
    
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
        debug=args.debug,
        csv_filename=args.csv_filename,
        use_gpu=args.use_gpu,
        batch_size=args.batch_size
    )
    
    if result:
        print(f"分析完成，评测了 {result['evaluation_days']} 个日期")
        print(f"总高相关性期间: {result['batch_results']['summary']['total_high_correlations']}")
        print(f"平均每日高相关数量: {result['batch_results']['summary']['avg_high_correlations_per_day']:.2f}")
    else:
        print("分析失败")