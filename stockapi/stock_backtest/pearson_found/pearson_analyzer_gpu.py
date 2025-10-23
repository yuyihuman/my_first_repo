"""
股票数据Pearson相关系数分析脚本 - GPU加速版本

该脚本使用PyTorch GPU加速来批量计算Pearson相关系数，大幅提升性能。
通过矩阵运算替代逐一比较，特别适合处理大量数据的相关性分析。

功能：
1. 支持命令行参数传入股票代码
2. 加载股票历史数据
3. 使用GPU批量计算开盘价、收盘价、最高价、最低价、成交量的Pearson相关系数
4. 找出相关系数大于阈值的数据
5. 将结果记录到日志文件

使用方法：
python pearson_analyzer_gpu.py --stock_code 000001

作者：Stock Backtest System
创建时间：2024年
GPU优化版本：2024年
"""

import argparse
import logging
import os
from datetime import datetime
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

# 忽略一些不重要的警告
warnings.filterwarnings('ignore', category=UserWarning)


class GPUPearsonAnalyzer:
    def __init__(self, stock_code, log_dir='logs', window_size=15, threshold=0.9, debug=False, 
                 comparison_stocks=None, comparison_mode='default', backtest_date=None, 
                 csv_filename='evaluation_results.csv', use_gpu=True, batch_size=1000):
        """
        初始化GPU加速的Pearson相关性分析器
        
        Args:
            stock_code: 目标股票代码
            log_dir: 日志目录
            window_size: 分析窗口大小（交易日数量）
            threshold: 相关系数阈值
            debug: 是否开启debug模式（影响性能）
            comparison_stocks: 自定义对比股票列表
            comparison_mode: 对比模式 ('default', 'top10', 'banks', 'tech', 'new_energy', 'healthcare', 'consumer', 'self_only')
            backtest_date: 回测起始日期 (格式: YYYY-MM-DD)，从该日期往前数获取数据段进行分析
            csv_filename: CSV结果文件名 (默认: evaluation_results.csv)
            use_gpu: 是否使用GPU加速 (默认: True)
            batch_size: GPU批处理大小 (默认: 1000)
        """
        self.stock_code = stock_code
        
        # 设置固定的绝对路径
        script_dir = r'C:\Users\17701\github\my_first_repo\stockapi\stock_backtest\pearson_found'
        self.log_dir = os.path.join(script_dir, 'logs')
        self.csv_results_file = os.path.join(script_dir, csv_filename)
        
        self.window_size = window_size
        self.threshold = threshold
        self.debug = debug
        self.comparison_mode = comparison_mode
        self.backtest_date = backtest_date
        self.use_gpu = use_gpu
        self.batch_size = batch_size
        self.data_loader = None
        self.logger = None
        
        # GPU设备设置
        self.device = self._setup_device()
        
        # 设置对比股票列表
        if comparison_stocks:
            self.comparison_stocks = comparison_stocks
        elif comparison_mode == 'self_only':
            self.comparison_stocks = [stock_code]  # 只对比自己的历史数据
        else:
            self.comparison_stocks = get_comparison_stocks(comparison_mode)
            # 确保目标股票不在对比列表中（避免重复）
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
        
        self.logger.info(f"初始化GPU加速Pearson分析器，目标股票: {stock_code}")
        self.logger.info(f"窗口大小: {window_size}, 阈值: {threshold}, Debug模式: {debug}")
        self.logger.info(f"GPU设备: {self.device}, 批处理大小: {batch_size}")
        self.logger.info(f"对比模式: {comparison_mode}, 对比股票数量: {len(self.comparison_stocks)}")
        if self.debug:
            self.logger.info(f"对比股票列表: {self.comparison_stocks[:10]}{'...' if len(self.comparison_stocks) > 10 else ''}")
    
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
        # 按股票代码创建子文件夹
        stock_log_dir = os.path.join(self.log_dir, self.stock_code)
        os.makedirs(stock_log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thread_id = threading.get_ident()
        log_filename = f"pearson_analysis_gpu_{self.stock_code}_{timestamp}_thread_{thread_id}.log"
        log_path = os.path.join(stock_log_dir, log_filename)
        
        # 创建logger
        self.logger = logging.getLogger(f'GPUPearsonAnalyzer_{self.stock_code}')
        self.logger.setLevel(logging.INFO)
        
        # 清除已有的handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 创建文件handler
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加handler到logger
        self.logger.addHandler(file_handler)
        
        self.logger.info(f"日志文件创建: {log_path}")
    
    def _setup_csv_file(self):
        """设置CSV文件，如果不存在则创建"""
        if not os.path.exists(self.csv_results_file):
            if self.debug:
                self.logger.info(f"🆕 Debug: CSV结果文件不存在，创建新文件: {self.csv_results_file}")
            
            # 创建CSV文件的表头
            header = ['代码', 'window_size', '阈值', '评测日期', '对比股票数量', '相关数量', '下1日高开', '下1日上涨', '下3日上涨', '下5日上涨', '下10日上涨']
            df = pd.DataFrame(columns=header)
            # 确保代码列为字符串类型
            df['代码'] = df['代码'].astype(str)
            df.to_csv(self.csv_results_file, index=False, encoding='utf-8-sig')
            
            if self.debug:
                file_size = os.path.getsize(self.csv_results_file)
                self.logger.info(f"🆕 Debug: CSV文件创建完成，表头: {header}")
                self.logger.info(f"🆕 Debug: 初始文件大小: {file_size} bytes")
        else:
            if self.debug:
                file_size = os.path.getsize(self.csv_results_file)
                self.logger.info(f"✅ Debug: CSV结果文件已存在: {self.csv_results_file}")
                self.logger.info(f"✅ Debug: 现有文件大小: {file_size} bytes")
    
    def save_evaluation_result(self, evaluation_date, stats, correlation_count=0):
        """
        保存单次评测结果到CSV文件
        
        Args:
            evaluation_date: 评测日期（评测序列的最后一天）
            stats: 统计结果字典
            correlation_count: 相关数量（高相关性期间的数量）
        """
        try:
            # 计算对比股票数量
            # 在self_only模式下，只对比自身历史数据，不需要额外加1
            # 在其他模式下，需要加上目标股票自身
            if self.comparison_mode == 'self_only':
                comparison_stock_count = len(self.comparison_stocks)
            else:
                comparison_stock_count = len(self.comparison_stocks) + 1
            
            # 准备要保存的数据
            result_data = {
                '代码': str(self.stock_code),  # 确保股票代码为字符串
                'window_size': self.window_size,
                '阈值': self.threshold,
                '评测日期': evaluation_date.strftime('%Y-%m-%d'),
                '对比股票数量': comparison_stock_count,
                '相关数量': correlation_count,
                '下1日高开': f"{stats['ratios']['next_day_gap_up']:.2%}" if stats and 'ratios' in stats else 'N/A',
                '下1日上涨': f"{stats['ratios']['next_1_day_up']:.2%}" if stats and 'ratios' in stats else 'N/A',
                '下3日上涨': f"{stats['ratios']['next_3_day_up']:.2%}" if stats and 'ratios' in stats else 'N/A',
                '下5日上涨': f"{stats['ratios']['next_5_day_up']:.2%}" if stats and 'ratios' in stats else 'N/A',
                '下10日上涨': f"{stats['ratios']['next_10_day_up']:.2%}" if stats and 'ratios' in stats else 'N/A'
            }
            
            # 读取现有的CSV文件，指定代码列为字符串类型
            if os.path.exists(self.csv_results_file):
                if self.debug:
                    self.logger.info(f"📖 Debug: 开始读取现有CSV文件: {self.csv_results_file}")
                    file_size = os.path.getsize(self.csv_results_file)
                    self.logger.info(f"📖 Debug: CSV文件大小: {file_size} bytes")
                
                df = pd.read_csv(self.csv_results_file, encoding='utf-8-sig', dtype={'代码': str})
                
                if self.debug:
                    self.logger.info(f"📖 Debug: CSV文件读取完成，共 {len(df)} 行数据")
                    if not df.empty:
                        self.logger.info(f"📖 Debug: CSV文件列名: {list(df.columns)}")
                        self.logger.info(f"📖 Debug: 最后一条记录的股票代码: {df.iloc[-1]['代码'] if '代码' in df.columns else 'N/A'}")
            else:
                if self.debug:
                    self.logger.info(f"📖 Debug: CSV文件不存在，创建新的DataFrame: {self.csv_results_file}")
                # 如果文件不存在，创建新的DataFrame
                df = pd.DataFrame()
            
            # 添加新的结果行
            new_row = pd.DataFrame([result_data])
            df = pd.concat([df, new_row], ignore_index=True)
            
            # 确保代码列为字符串类型
            df['代码'] = df['代码'].astype(str)
            
            if self.debug:
                self.logger.info(f"💾 Debug: 准备保存CSV文件，当前DataFrame共 {len(df)} 行数据")
                self.logger.info(f"💾 Debug: 新增数据: {result_data}")
            
            # 保存到CSV文件
            df.to_csv(self.csv_results_file, index=False, encoding='utf-8-sig')
            
            if self.debug:
                # 验证保存后的文件
                saved_file_size = os.path.getsize(self.csv_results_file)
                self.logger.info(f"💾 Debug: CSV文件保存完成，文件大小: {saved_file_size} bytes")
            
            self.logger.info(f"评测结果已保存到CSV文件: {self.csv_results_file}")
            self.logger.info(f"保存的结果: {result_data}")
            
        except Exception as e:
            self.logger.error(f"保存评测结果到CSV文件时出错: {str(e)}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
    
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
    
    def get_timer_stats(self, timer_name):
        """获取计时器统计信息"""
        times = self.performance_timers[timer_name]
        if not times:
            return None
        return {
            'count': len(times),
            'total': sum(times),
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    
    def log_performance_summary(self):
        """输出性能统计表"""
        self.logger.info("=" * 80)
        self.logger.info("🚀 GPU加速性能统计报告")
        self.logger.info("=" * 80)
        
        # 计算总耗时
        total_analysis_time = sum(self.performance_timers.get('total_analysis', [0]))
        
        # 创建统计表
        stats_table = []
        stats_table.append(f"{'阶段':<25} {'次数':<8} {'总耗时(秒)':<12} {'平均耗时(秒)':<15} {'最小耗时(秒)':<15} {'最大耗时(秒)':<15}")
        stats_table.append("-" * 90)
        
        # 定义关键阶段的显示顺序和中文名称
        stage_names = {
            'total_analysis': '总分析时间',
            'data_loading': '数据加载',
            'target_stock_loading': '目标股票数据加载',
            'comparison_stocks_loading': '对比股票数据加载',
            'gpu_data_preparation': 'GPU数据准备',
            'gpu_correlation_calculation': 'GPU相关性计算',
            'self_analysis': '自身历史数据分析',
            'comparison_analysis': '跨股票对比分析',
            'plotting': 'K线图绘制',
            'stats_calculation': '统计计算'
        }
        
        for timer_name, display_name in stage_names.items():
            stats = self.get_timer_stats(timer_name)
            if stats:
                stats_table.append(
                    f"{display_name:<25} {stats['count']:<8} {stats['total']:<12.3f} "
                    f"{stats['average']:<15.3f} {stats['min']:<15.3f} {stats['max']:<15.3f}"
                )
        
        # 输出统计表
        for line in stats_table:
            self.logger.info(line)
        
        # 输出性能分析
        self.logger.info("-" * 90)
        if total_analysis_time > 0:
            data_loading_time = sum(self.performance_timers.get('data_loading', [0]))
            gpu_prep_time = sum(self.performance_timers.get('gpu_data_preparation', [0]))
            gpu_calc_time = sum(self.performance_timers.get('gpu_correlation_calculation', [0]))
            analysis_time = sum(self.performance_timers.get('self_analysis', [0])) + sum(self.performance_timers.get('comparison_analysis', [0]))
            plotting_time = sum(self.performance_timers.get('plotting', [0]))
            
            self.logger.info(f"📊 GPU加速性能分析:")
            self.logger.info(f"   数据加载占比: {(data_loading_time/total_analysis_time)*100:.1f}%")
            self.logger.info(f"   GPU数据准备占比: {(gpu_prep_time/total_analysis_time)*100:.1f}%")
            self.logger.info(f"   GPU计算占比: {(gpu_calc_time/total_analysis_time)*100:.1f}%")
            self.logger.info(f"   分析处理占比: {(analysis_time/total_analysis_time)*100:.1f}%")
            self.logger.info(f"   图表绘制占比: {(plotting_time/total_analysis_time)*100:.1f}%")
        
        self.logger.info("=" * 80)

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
        
        # 数据过滤：确保价格为正数，成交量大于0
        self.data = self._filter_data(data, self.stock_code)
        self.end_timer('target_stock_loading')
        
        # 加载对比股票数据
        self._load_comparison_stocks_data()
        
        return self.data
    
    def _filter_data(self, data, stock_code):
        """
        过滤股票数据，确保数据质量
        
        Args:
            data: 原始股票数据
            stock_code: 股票代码
            
        Returns:
            过滤后的数据
        """
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
                    # 过滤数据
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
        if successful_loads == 0:
            self.logger.warning("未能加载任何对比股票数据，将使用自身历史数据对比")
        self.end_timer('comparison_stocks_loading')
    
    def prepare_gpu_data(self, recent_data, historical_periods_data):
        """
        准备GPU计算所需的数据格式
        
        Args:
            recent_data: 最近期间的数据 (DataFrame)
            historical_periods_data: 历史期间数据列表 [(data, start_date, end_date, stock_code), ...]
            
        Returns:
            tuple: (recent_tensor, historical_tensor, period_info_list)
        """
        self.start_timer('gpu_data_preparation')
        
        fields = ['open', 'high', 'low', 'close', 'volume']
        
        try:
            # 准备最近数据
            recent_values = recent_data[fields].values.astype(np.float32)
            recent_tensor = torch.from_numpy(recent_values).to(self.device)
            
            # 准备历史数据
            historical_data_list = []
            period_info_list = []
            
            for hist_data, start_date, end_date, stock_code in historical_periods_data:
                hist_values = hist_data[fields].values.astype(np.float32)
                if hist_values.shape[0] == self.window_size:  # 确保数据长度一致
                    historical_data_list.append(hist_values)
                    period_info_list.append({
                        'start_date': start_date,
                        'end_date': end_date,
                        'stock_code': stock_code
                    })
            
            if not historical_data_list:
                self.end_timer('gpu_data_preparation')
                return None, None, []
            
            # 转换为张量 [num_periods, window_size, num_features]
            historical_array = np.stack(historical_data_list, axis=0)
            historical_tensor = torch.from_numpy(historical_array).to(self.device)
            
            self.logger.info(f"GPU数据准备完成: 最近数据 {recent_tensor.shape}, 历史数据 {historical_tensor.shape}")
            
            self.end_timer('gpu_data_preparation')
            return recent_tensor, historical_tensor, period_info_list
            
        except Exception as e:
            self.logger.error(f"GPU数据准备失败: {str(e)}")
            self.end_timer('gpu_data_preparation')
            return None, None, []
    
    def calculate_pearson_correlation_gpu_batch(self, recent_tensor, historical_tensor):
        """
        使用GPU批量计算Pearson相关系数
        
        Args:
            recent_tensor: 最近数据张量 [window_size, num_features]
            historical_tensor: 历史数据张量 [num_periods, window_size, num_features]
            
        Returns:
            torch.Tensor: 相关系数矩阵 [num_periods, num_features]
        """
        self.start_timer('gpu_correlation_calculation')
        
        try:
            # 扩展recent_tensor以匹配historical_tensor的维度
            # recent_tensor: [window_size, num_features] -> [1, window_size, num_features]
            recent_expanded = recent_tensor.unsqueeze(0)
            
            # 计算均值
            recent_mean = torch.mean(recent_expanded, dim=1, keepdim=True)  # [1, 1, num_features]
            historical_mean = torch.mean(historical_tensor, dim=1, keepdim=True)  # [num_periods, 1, num_features]
            
            # 中心化数据
            recent_centered = recent_expanded - recent_mean  # [1, window_size, num_features]
            historical_centered = historical_tensor - historical_mean  # [num_periods, window_size, num_features]
            
            # 计算协方差
            # 使用广播机制计算所有期间的协方差
            covariance = torch.sum(recent_centered * historical_centered, dim=1)  # [num_periods, num_features]
            
            # 计算标准差
            recent_std = torch.sqrt(torch.sum(recent_centered ** 2, dim=1))  # [1, num_features]
            historical_std = torch.sqrt(torch.sum(historical_centered ** 2, dim=1))  # [num_periods, num_features]
            
            # 计算相关系数
            denominator = recent_std * historical_std
            
            # 避免除零错误
            correlation = torch.where(
                denominator > 1e-8,
                covariance / denominator,
                torch.zeros_like(covariance)
            )
            
            # 处理NaN和Inf值
            correlation = torch.where(
                torch.isfinite(correlation),
                correlation,
                torch.zeros_like(correlation)
            )
            
            self.end_timer('gpu_correlation_calculation')
            return correlation
            
        except Exception as e:
            self.logger.error(f"GPU相关系数计算失败: {str(e)}")
            self.end_timer('gpu_correlation_calculation')
            return None
    
    def process_gpu_correlation_results(self, correlation_tensor, period_info_list, threshold):
        """
        处理GPU计算的相关系数结果
        
        Args:
            correlation_tensor: 相关系数张量 [num_periods, num_features]
            period_info_list: 期间信息列表
            threshold: 相关系数阈值
            
        Returns:
            list: 高相关性期间列表
        """
        fields = ['open', 'high', 'low', 'close', 'volume']
        high_correlation_periods = []
        
        # 转换为numpy数组以便处理
        correlation_array = correlation_tensor.cpu().numpy()
        
        # 计算每个期间的平均相关系数
        avg_correlations = np.mean(correlation_array, axis=1)
        
        # 找出超过阈值的期间
        high_corr_indices = np.where(avg_correlations >= threshold)[0]
        
        for idx in high_corr_indices:
            period_info = period_info_list[idx]
            avg_correlation = avg_correlations[idx]
            
            # 构建各字段的相关系数字典
            correlations = {}
            for i, field in enumerate(fields):
                correlations[field] = {
                    'correlation': float(correlation_array[idx, i]),
                    'p_value': np.nan  # GPU版本暂不计算p值以提高性能
                }
            
            high_correlation_periods.append({
                'start_date': period_info['start_date'],
                'end_date': period_info['end_date'],
                'avg_correlation': float(avg_correlation),
                'correlations': correlations,
                'stock_code': period_info['stock_code'],
                'source': 'self' if period_info['stock_code'] == self.stock_code else 'comparison'
            })
        
        return high_correlation_periods
    
    def calculate_pearson_correlation_gpu(self, recent_data, historical_periods_data):
        """
        GPU加速的Pearson相关系数计算主函数
        
        Args:
            recent_data: 最近期间的数据
            historical_periods_data: 历史期间数据列表
            
        Returns:
            list: 高相关性期间列表
        """
        if not historical_periods_data:
            return []
        
        # 分批处理以避免GPU内存不足
        all_high_correlation_periods = []
        total_periods = len(historical_periods_data)
        
        for batch_start in range(0, total_periods, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_periods)
            batch_data = historical_periods_data[batch_start:batch_end]
            
            if self.debug:
                self.logger.info(f"处理批次 {batch_start//self.batch_size + 1}/{(total_periods-1)//self.batch_size + 1}: "
                               f"期间 {batch_start+1}-{batch_end}/{total_periods}")
            
            # 准备GPU数据
            recent_tensor, historical_tensor, period_info_list = self.prepare_gpu_data(recent_data, batch_data)
            
            if recent_tensor is None or historical_tensor is None:
                continue
            
            # GPU批量计算相关系数
            correlation_tensor = self.calculate_pearson_correlation_gpu_batch(recent_tensor, historical_tensor)
            
            if correlation_tensor is None:
                continue
            
            # 处理结果
            batch_high_correlations = self.process_gpu_correlation_results(
                correlation_tensor, period_info_list, self.threshold
            )
            
            all_high_correlation_periods.extend(batch_high_correlations)
            
            # 清理GPU内存
            del recent_tensor, historical_tensor, correlation_tensor
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
        
        return all_high_correlation_periods
    
    def calculate_pearson_correlation(self, recent_data, historical_data):
        """
        兼容性函数：单个历史期间的相关系数计算
        为了保持与原版本的接口兼容性
        """
        # 构建历史期间数据列表
        historical_periods_data = [(
            historical_data,
            historical_data.index[0],
            historical_data.index[-1],
            self.stock_code
        )]
        
        # 使用GPU批量计算
        high_correlation_periods = self.calculate_pearson_correlation_gpu(recent_data, historical_periods_data)
        
        if high_correlation_periods:
            period = high_correlation_periods[0]
            return period['avg_correlation'], period['correlations']
        else:
            # 如果没有超过阈值，仍然返回计算结果
            recent_tensor, historical_tensor, period_info_list = self.prepare_gpu_data(recent_data, historical_periods_data)
            if recent_tensor is not None and historical_tensor is not None:
                correlation_tensor = self.calculate_pearson_correlation_gpu_batch(recent_tensor, historical_tensor)
                if correlation_tensor is not None:
                    correlation_array = correlation_tensor.cpu().numpy()
                    avg_correlation = float(np.mean(correlation_array[0]))
                    
                    fields = ['open', 'high', 'low', 'close', 'volume']
                    correlations = {}
                    for i, field in enumerate(fields):
                        correlations[field] = {
                            'correlation': float(correlation_array[0, i]),
                            'p_value': np.nan
                        }
                    
                    return avg_correlation, correlations
        
        # 回退到CPU计算
        return self.calculate_pearson_correlation_fallback(recent_data, historical_data)
    
    def calculate_pearson_correlation_fallback(self, recent_data, historical_data):
        """
        CPU回退计算方法
        """
        fields = ['open', 'high', 'low', 'close', 'volume']
        correlations = {}
        
        for field in fields:
            try:
                corr_coef, p_value = pearsonr(recent_data[field], historical_data[field])
                correlations[field] = {'correlation': corr_coef, 'p_value': p_value}
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"计算 {field} 相关系数时出错: {e}")
                correlations[field] = {'correlation': np.nan, 'p_value': np.nan}
        
        # 计算平均相关系数（忽略NaN值）
        valid_correlations = [corr['correlation'] for corr in correlations.values() 
                            if not np.isnan(corr['correlation'])]
        avg_correlation = np.mean(valid_correlations) if valid_correlations else 0
        
        return avg_correlation, correlations
    
    def analyze_self_historical_data(self, recent_data, backtest_date):
        """
        分析目标股票自身的历史数据
        
        Args:
            recent_data: 最近期间的数据
            backtest_date: 回测日期
            
        Returns:
            list: 高相关性期间列表
        """
        self.start_timer('self_historical_analysis')
        self.logger.info(f"开始分析股票 {self.stock_code} 自身历史数据")
        
        # 获取回测日期之前的历史数据
        historical_data = self.data[self.data.index < backtest_date]
        
        if len(historical_data) < self.window_size:
            self.logger.warning(f"历史数据不足，需要至少 {self.window_size} 条记录")
            self.end_timer('self_historical_analysis')
            return []
        
        # 准备历史期间数据
        historical_periods_data = []
        
        # 生成所有可能的历史窗口
        for i in range(len(historical_data) - self.window_size + 1):
            start_idx = i
            end_idx = i + self.window_size
            
            hist_period_data = historical_data.iloc[start_idx:end_idx]
            start_date = hist_period_data.index[0]
            end_date = hist_period_data.index[-1]
            
            historical_periods_data.append((
                hist_period_data,
                start_date,
                end_date,
                self.stock_code
            ))
        
        self.logger.info(f"准备分析 {len(historical_periods_data)} 个历史期间")
        
        # 使用GPU批量计算
        high_correlation_periods = self.calculate_pearson_correlation_gpu(recent_data, historical_periods_data)
        
        # 按相关系数排序
        high_correlation_periods.sort(key=lambda x: x['avg_correlation'], reverse=True)
        
        self.logger.info(f"自身历史数据分析完成，发现 {len(high_correlation_periods)} 个高相关性期间")
        
        if high_correlation_periods:
            avg_correlation = np.mean([p['avg_correlation'] for p in high_correlation_periods])
            self.logger.info(f"自身历史数据平均相关系数: {avg_correlation:.4f}")
        
        self.end_timer('self_historical_analysis')
        return high_correlation_periods
    
    def analyze_comparison_stocks(self, recent_data, backtest_date):
        """
        分析对比股票数据
        
        Args:
            recent_data: 最近期间的数据
            backtest_date: 回测日期
            
        Returns:
            list: 高相关性期间列表
        """
        if self.comparison_mode == 'self_only':
            self.logger.info("跳过对比股票分析（仅使用自身历史数据模式）")
            return []
        
        if not self.loaded_stocks_data:
            self.logger.warning("没有可用的对比股票数据")
            return []
        
        self.start_timer('comparison_stocks_analysis')
        self.logger.info(f"开始分析 {len(self.loaded_stocks_data)} 只对比股票")
        
        all_high_correlation_periods = []
        stock_analysis_count = 0
        
        for stock_code, stock_data in self.loaded_stocks_data.items():
            if self.debug:
                self.logger.info(f"正在分析对比股票: {stock_code}")
            
            # 获取回测日期之前的历史数据
            historical_data = stock_data[stock_data.index < backtest_date]
            
            if len(historical_data) < self.window_size:
                if self.debug:
                    self.logger.warning(f"股票 {stock_code} 历史数据不足")
                continue
            
            # 准备历史期间数据
            historical_periods_data = []
            
            # 生成所有可能的历史窗口
            for i in range(len(historical_data) - self.window_size + 1):
                start_idx = i
                end_idx = i + self.window_size
                
                hist_period_data = historical_data.iloc[start_idx:end_idx]
                start_date = hist_period_data.index[0]
                end_date = hist_period_data.index[-1]
                
                historical_periods_data.append((
                    hist_period_data,
                    start_date,
                    end_date,
                    stock_code
                ))
            
            if self.debug:
                self.logger.info(f"股票 {stock_code} 准备分析 {len(historical_periods_data)} 个历史期间")
            
            # 使用GPU批量计算
            stock_high_correlations = self.calculate_pearson_correlation_gpu(recent_data, historical_periods_data)
            
            if stock_high_correlations:
                all_high_correlation_periods.extend(stock_high_correlations)
                if self.debug:
                    avg_corr = np.mean([p['avg_correlation'] for p in stock_high_correlations])
                    self.logger.info(f"股票 {stock_code} 发现 {len(stock_high_correlations)} 个高相关性期间，"
                                   f"平均相关系数: {avg_corr:.4f}")
            
            stock_analysis_count += 1
        
        # 按相关系数排序
        all_high_correlation_periods.sort(key=lambda x: x['avg_correlation'], reverse=True)
        
        self.logger.info(f"对比股票分析完成，共分析 {stock_analysis_count} 只股票，"
                        f"发现 {len(all_high_correlation_periods)} 个高相关性期间")
        
        if all_high_correlation_periods:
            avg_correlation = np.mean([p['avg_correlation'] for p in all_high_correlation_periods])
            self.logger.info(f"对比股票平均相关系数: {avg_correlation:.4f}")
        
        self.end_timer('comparison_stocks_analysis')
        return all_high_correlation_periods
    
    def analyze(self, backtest_date=None, window_size=None, threshold=None, comparison_mode=None, 
                comparison_stocks=None, debug=None):
        """
        主分析函数 - 保持与原版本相同的接口
        
        Args:
            backtest_date: 回测日期
            window_size: 窗口大小
            threshold: 相关系数阈值
            comparison_mode: 对比模式
            comparison_stocks: 对比股票列表
            debug: 调试模式
            
        Returns:
            dict: 分析结果
        """
        self.start_timer('total_analysis')
        
        # 更新参数
        if backtest_date is not None:
            self.backtest_date = pd.to_datetime(backtest_date)
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
        self.logger.info(f"开始GPU加速Pearson相关性分析")
        self.logger.info(f"目标股票: {self.stock_code}")
        self.logger.info(f"回测日期: {self.backtest_date}")
        self.logger.info(f"窗口大小: {self.window_size}")
        self.logger.info(f"相关系数阈值: {self.threshold}")
        self.logger.info(f"对比模式: {self.comparison_mode}")
        self.logger.info(f"GPU设备: {self.device}")
        self.logger.info(f"批处理大小: {self.batch_size}")
        self.logger.info("=" * 80)
        
        # 加载数据
        if self.data is None:
            if self.load_data() is None:
                self.logger.error("数据加载失败")
                return None
        
        # 准备最近期间数据
        recent_data = self.data[self.data.index < self.backtest_date].tail(self.window_size)
        
        if len(recent_data) < self.window_size:
            self.logger.error(f"最近期间数据不足，需要 {self.window_size} 条记录，实际只有 {len(recent_data)} 条")
            return None
        
        self.logger.info(f"最近期间数据: {recent_data.index[0]} 到 {recent_data.index[-1]}")
        
        # 分析自身历史数据
        self_high_correlations = self.analyze_self_historical_data(recent_data, self.backtest_date)
        
        # 分析对比股票数据
        comparison_high_correlations = self.analyze_comparison_stocks(recent_data, self.backtest_date)
        
        # 合并结果
        all_high_correlations = self_high_correlations + comparison_high_correlations
        all_high_correlations.sort(key=lambda x: x['avg_correlation'], reverse=True)
        
        # 生成分析结果
        result = {
            'stock_code': self.stock_code,
            'backtest_date': self.backtest_date,
            'window_size': self.window_size,
            'threshold': self.threshold,
            'recent_period': {
                'start_date': recent_data.index[0],
                'end_date': recent_data.index[-1]
            },
            'self_high_correlations': self_high_correlations,
            'comparison_high_correlations': comparison_high_correlations,
            'all_high_correlations': all_high_correlations,
            'summary': {
                'total_high_correlations': len(all_high_correlations),
                'self_high_correlations_count': len(self_high_correlations),
                'comparison_high_correlations_count': len(comparison_high_correlations),
                'avg_correlation': np.mean([p['avg_correlation'] for p in all_high_correlations]) if all_high_correlations else 0
            }
        }
        
        self.end_timer('total_analysis')
        
        # 输出性能总结
        self.print_performance_summary()
        
        # 输出分析总结
        self.logger.info("=" * 80)
        self.logger.info("分析结果总结:")
        self.logger.info(f"总计发现 {result['summary']['total_high_correlations']} 个高相关性期间")
        self.logger.info(f"  - 自身历史数据: {result['summary']['self_high_correlations_count']} 个")
        self.logger.info(f"  - 对比股票数据: {result['summary']['comparison_high_correlations_count']} 个")
        if result['summary']['avg_correlation'] > 0:
            self.logger.info(f"平均相关系数: {result['summary']['avg_correlation']:.4f}")
        self.logger.info("=" * 80)
        
        return result
    
    def save_results_to_csv(self, result, output_file=None):
        """
        保存分析结果到CSV文件
        
        Args:
            result: 分析结果
            output_file: 输出文件路径
        """
        if result is None or not result['all_high_correlations']:
            self.logger.info("没有高相关性期间数据需要保存")
            return
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"pearson_analysis_gpu_{self.stock_code}_{timestamp}.csv"
        
        try:
            # 准备CSV数据
            csv_data = []
            for period in result['all_high_correlations']:
                row = {
                    'stock_code': period['stock_code'],
                    'source': period['source'],
                    'start_date': period['start_date'],
                    'end_date': period['end_date'],
                    'avg_correlation': period['avg_correlation']
                }
                
                # 添加各字段的相关系数
                for field, corr_data in period['correlations'].items():
                    row[f'{field}_correlation'] = corr_data['correlation']
                    row[f'{field}_p_value'] = corr_data['p_value']
                
                csv_data.append(row)
            
            # 保存到CSV
            df = pd.DataFrame(csv_data)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"分析结果已保存到: {output_file}")
            self.logger.info(f"共保存 {len(csv_data)} 条高相关性期间记录")
            
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {str(e)}")

# 兼容性函数：保持与原版本相同的调用接口
def analyze_pearson_correlation_gpu(stock_code, backtest_date, window_size=30, threshold=0.7,
                                   comparison_mode='mixed', comparison_stocks=None, debug=False,
                                   output_csv=True, batch_size=1000):
    """
    GPU加速的Pearson相关性分析函数 - 保持与原版本相同的接口
    
    Args:
        stock_code: 目标股票代码
        backtest_date: 回测日期
        window_size: 窗口大小
        threshold: 相关系数阈值
        comparison_mode: 对比模式
        comparison_stocks: 对比股票列表
        debug: 调试模式
        output_csv: 是否输出CSV文件
        batch_size: GPU批处理大小
        
    Returns:
        dict: 分析结果
    """
    analyzer = GPUPearsonAnalyzer(
        stock_code=stock_code,
        window_size=window_size,
        threshold=threshold,
        comparison_mode=comparison_mode,
        comparison_stocks=comparison_stocks,
        debug=debug,
        batch_size=batch_size
    )
    
    result = analyzer.analyze(backtest_date=backtest_date)
    
    if result and output_csv:
        analyzer.save_results_to_csv(result)
    
    return result

if __name__ == "__main__":
    # 示例用法
    stock_code = "000001.SZ"
    backtest_date = "2024-01-01"
    
    result = analyze_pearson_correlation_gpu(
        stock_code=stock_code,
        backtest_date=backtest_date,
        window_size=30,
        threshold=0.7,
        comparison_mode='mixed',
        debug=True,
        batch_size=500
    )
    
    if result:
        print(f"分析完成，发现 {result['summary']['total_high_correlations']} 个高相关性期间")