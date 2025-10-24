"""
股票数据Pearson相关系数分析脚本

该脚本用于分析股票数据的Pearson相关系数，通过滑动窗口的方式
计算最近20个交易日与历史20个交易日数据的相关性。

功能：
1. 支持命令行参数传入股票代码
2. 加载股票历史数据
3. 计算开盘价、收盘价、最高价、最低价、成交量的Pearson相关系数
4. 找出相关系数大于0.90的数据
5. 将结果记录到日志文件

使用方法：
python pearson_analyzer.py --stock_code 000001

作者：Stock Backtest System
创建时间：2024年
"""

import argparse
import logging
import os
from datetime import datetime
import numpy as np
from scipy.stats import pearsonr
from data_loader import StockDataLoader
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from stock_config import get_comparison_stocks
import time
import threading
from collections import defaultdict


class PearsonAnalyzer:
    def __init__(self, stock_code, log_dir='logs', window_size=15, threshold=0.85, debug=False, 
                 comparison_stocks=None, comparison_mode='default', backtest_date=None, csv_filename='evaluation_results.csv',
                 earliest_date='2020-01-01'):
        """
        初始化Pearson相关性分析器
        
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
            earliest_date: 数据获取的最早日期限制 (格式: YYYY-MM-DD，默认: 2020-01-01)
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
        self.earliest_date = pd.to_datetime(earliest_date)
        self.data_loader = None
        self.logger = None
        
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
        
        self.logger.info(f"初始化Pearson分析器，目标股票: {stock_code}")
        self.logger.info(f"窗口大小: {window_size}, 阈值: {threshold}, Debug模式: {debug}")
        self.logger.info(f"对比模式: {comparison_mode}, 对比股票数量: {len(self.comparison_stocks)}")
        if self.debug:
            self.logger.info(f"对比股票列表: {self.comparison_stocks[:10]}{'...' if len(self.comparison_stocks) > 10 else ''}")
    
    def _setup_logging(self):
        """设置日志配置"""
        # 按股票代码创建子文件夹
        stock_log_dir = os.path.join(self.log_dir, self.stock_code)
        os.makedirs(stock_log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thread_id = threading.get_ident()
        log_filename = f"pearson_analysis_{self.stock_code}_{timestamp}_thread_{thread_id}.log"
        log_path = os.path.join(stock_log_dir, log_filename)
        
        # 创建logger
        self.logger = logging.getLogger(f'PearsonAnalyzer_{self.stock_code}')
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
        self.logger.info("🚀 性能统计报告")
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
            'self_analysis': '自身历史数据分析',
            'comparison_analysis': '跨股票对比分析',
            'correlation_calculation': '相关性计算',
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
            analysis_time = sum(self.performance_timers.get('self_analysis', [0])) + sum(self.performance_timers.get('comparison_analysis', [0]))
            plotting_time = sum(self.performance_timers.get('plotting', [0]))
            
            self.logger.info(f"📊 性能分析:")
            self.logger.info(f"   数据加载占比: {(data_loading_time/total_analysis_time)*100:.1f}%")
            self.logger.info(f"   分析计算占比: {(analysis_time/total_analysis_time)*100:.1f}%")
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
            self.logger.info(f"股票 {stock_code} 日期过滤完成，移除早于 {self.earliest_date.strftime('%Y-%m-%d')} 的 {date_removed_count} 条数据")
        
        if quality_removed_count > 0:
            self.logger.info(f"股票 {stock_code} 数据质量过滤完成，移除 {quality_removed_count} 条异常数据")
        
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
    
    def plot_kline_comparison(self, recent_data, historical_data, correlation_info):
        """
        绘制最近数据和历史高相关性数据的K线图对比
        
        Args:
            recent_data: 最近的数据
            historical_data: 历史高相关性数据
            correlation_info: 相关性信息字典
        """
        self.start_timer('plotting')
        try:
            # 创建图表目录（按股票代码组织）
            chart_dir = os.path.join(self.log_dir, self.stock_code, 'charts')
            os.makedirs(chart_dir, exist_ok=True)
            
            # 准备数据 - 确保列名符合mplfinance要求
            recent_df = recent_data[['open', 'high', 'low', 'close', 'volume']].copy()
            recent_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            historical_df = historical_data[['open', 'high', 'low', 'close', 'volume']].copy()
            historical_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            # 设置图表样式
            mc = mpf.make_marketcolors(up='red', down='green', edge='inherit',
                                     wick={'up':'red', 'down':'green'},
                                     volume='in')
            s = mpf.make_mpf_style(marketcolors=mc, gridstyle='-', y_on_right=False)
            
            # 获取日期信息用于对比图
            historical_start = correlation_info['start_date'].strftime('%Y-%m-%d')
            historical_end = correlation_info['end_date'].strftime('%Y-%m-%d')
            recent_start = recent_data.index[0].strftime('%Y-%m-%d')
            recent_end = recent_data.index[-1].strftime('%Y-%m-%d')
            
            # 获取来源股票信息
            source_stock = correlation_info.get('source_stock', self.stock_code)
            source_label = f"Stock {source_stock}" if source_stock != self.stock_code else f"Target Stock {self.stock_code}"
            
            # 绘制K线对比图（两个子图上下排列，包含成交量）
            # 创建一个包含四个子图的图形（价格+成交量各两个）
            fig = plt.figure(figsize=(14, 12))
            
            # 上方 - 历史数据（价格和成交量）
            ax1 = plt.subplot(4, 1, 1)
            ax1_vol = plt.subplot(4, 1, 2)
            mpf.plot(historical_df,
                    type='candle',
                    style=s,
                    ax=ax1,
                    volume=ax1_vol,
                    warn_too_much_data=10000)
            ax1.set_title(f'Historical High Correlation Period - {source_label}\n({historical_start} to {historical_end}) | Avg Correlation: {correlation_info["avg_correlation"]:.4f}')
            ax1.set_ylabel('Price')
            ax1_vol.set_ylabel('Volume')
            
            # 下方 - 最近数据（价格和成交量）
            ax2 = plt.subplot(4, 1, 3)
            ax2_vol = plt.subplot(4, 1, 4)
            mpf.plot(recent_df,
                    type='candle',
                    style=s,
                    ax=ax2,
                    volume=ax2_vol,
                    warn_too_much_data=10000)
            ax2.set_title(f'Recent Trading Period - Target Stock {self.stock_code}\n({recent_start} to {recent_end})')
            ax2.set_ylabel('Price')
            ax2_vol.set_ylabel('Volume')
            
            plt.tight_layout()
            comparison_file = os.path.join(chart_dir, f'kline_comparison_{self.stock_code}.png')
            plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"K线对比图已保存: {comparison_file}")
            self.end_timer('plotting')
            
        except Exception as e:
            self.logger.error(f"绘制K线图时出错: {str(e)}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.end_timer('plotting')
    
    def calculate_pearson_correlation_vectorized(self, recent_data, historical_data):
        """
        向量化计算Pearson相关系数 - 性能优化版本
        
        Args:
            recent_data: 最近的数据 (numpy array or DataFrame)
            historical_data: 历史数据 (numpy array or DataFrame)
            
        Returns:
            tuple: (平均相关系数, 各字段相关系数字典)
        """
        fields = ['open', 'high', 'low', 'close', 'volume']
        correlations = {}
        
        try:
            # 转换为numpy数组以提高性能
            if hasattr(recent_data, 'values'):
                recent_values = recent_data[fields].values
            else:
                recent_values = recent_data
                
            if hasattr(historical_data, 'values'):
                historical_values = historical_data[fields].values
            else:
                historical_values = historical_data
            
            # 向量化计算所有字段的相关系数
            correlations_matrix = np.corrcoef(recent_values.T, historical_values.T)
            
            # 提取对角线上的相关系数（recent vs historical for each field）
            n_fields = len(fields)
            field_correlations = np.diag(correlations_matrix[:n_fields, n_fields:])
            
            # 构建结果字典
            for i, field in enumerate(fields):
                corr_coef = field_correlations[i]
                if np.isnan(corr_coef) or np.isinf(corr_coef):
                    correlations[field] = {'correlation': np.nan, 'p_value': np.nan}
                else:
                    # 对于向量化版本，我们暂时不计算p_value以提高性能
                    # 如果需要p_value，可以在必要时单独计算
                    correlations[field] = {'correlation': corr_coef, 'p_value': np.nan}
            
            # 计算平均相关系数（忽略NaN值）
            valid_correlations = [corr['correlation'] for corr in correlations.values() 
                                if not np.isnan(corr['correlation'])]
            avg_correlation = np.mean(valid_correlations) if valid_correlations else 0
            
            return avg_correlation, correlations
            
        except Exception as e:
            if self.debug:
                self.logger.warning(f"向量化相关系数计算出错，回退到原始方法: {e}")
            # 回退到原始方法
            return self.calculate_pearson_correlation_original(recent_data, historical_data)
    
    def calculate_pearson_correlation_original(self, recent_data, historical_data):
        """
        原始的Pearson相关系数计算方法（作为备用）
        
        Args:
            recent_data: 最近的数据
            historical_data: 历史数据
            
        Returns:
            tuple: (平均相关系数, 各字段相关系数字典)
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
    
    def calculate_pearson_correlation(self, recent_data, historical_data):
        """
        计算Pearson相关系数 - 使用优化后的向量化方法
        """
        return self.calculate_pearson_correlation_vectorized(recent_data, historical_data)
    
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
            source_type = period['source']
            
            # 根据来源股票代码获取正确的数据源
            if source_stock_code == self.stock_code:
                # 来自目标股票自身的历史数据
                source_data = data
            else:
                # 来自对比股票的历史数据
                source_data = self.loaded_stocks_data.get(source_stock_code)
                if source_data is None:
                    self.logger.warning(f"无法找到股票 {source_stock_code} 的数据，跳过期间 #{i}")
                    continue
            
            # 找到该期间结束后的数据位置
            try:
                end_idx = source_data.index.get_loc(end_date)
            except KeyError:
                self.logger.warning(f"在股票 {source_stock_code} 数据中找不到日期 {end_date}，跳过期间 #{i}")
                continue
            
            # 获取期间最后一天的收盘价
            period_close = source_data.iloc[end_idx]['close']
            
            # Debug模式下记录每个期间的详细信息
            if self.debug:
                self.logger.info(f"高相关性期间 #{i}:")
                self.logger.info(f"  期间: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  来源股票: {source_stock_code} ({'自身历史' if source_type == 'self' else '对比股票'})")
                self.logger.info(f"  相关系数: {avg_correlation:.4f}")
                self.logger.info(f"  期间收盘价: {period_close:.2f}")
            
            # 根据高相关性期间的来源股票获取对应的数据源
            period_stock_code = period['stock_code']
            if period_stock_code == self.stock_code:
                # 来自目标股票自身的历史数据
                source_data = data
            else:
                # 来自对比股票的数据
                source_data = self.loaded_stocks_data.get(period_stock_code)
                if source_data is None:
                    self.logger.warning(f"无法获取股票 {period_stock_code} 的数据，跳过期间 #{i} 的未来表现分析")
                    continue
            
            # 找到对应的日期在数据源中的位置
            try:
                source_end_idx = source_data.index.get_loc(end_date)
            except KeyError:
                self.logger.warning(f"在股票 {period_stock_code} 数据中找不到日期 {end_date}，跳过期间 #{i} 的未来表现分析")
                continue
            
            # 检查下1个交易日
            if source_end_idx + 1 < len(source_data):
                next_day_data = source_data.iloc[source_end_idx + 1]
                next_day_date = source_data.index[source_end_idx + 1]
                next_day_open = next_day_data['open']
                next_day_close = next_day_data['close']
                
                stats['valid_periods']['next_day'] += 1
                
                # 高开判断
                gap_up = next_day_open > period_close
                if gap_up:
                    stats['next_day_gap_up'] += 1
                
                # 下1个交易日上涨判断
                day_1_up = next_day_close > period_close
                if day_1_up:
                    stats['next_1_day_up'] += 1
                
                # Debug模式下记录详细信息
                if self.debug:
                    gap_up_str = "是" if gap_up else "否"
                    day_1_up_str = "是" if day_1_up else "否"
                    self.logger.info(f"  下1日({next_day_date.strftime('%Y-%m-%d')}): 开盘{next_day_open:.2f} 收盘{next_day_close:.2f} | 高开:{gap_up_str} 上涨:{day_1_up_str}")
            
            # 检查下3个交易日
            if source_end_idx + 3 < len(source_data):
                day_3_data = source_data.iloc[source_end_idx + 3]
                day_3_date = source_data.index[source_end_idx + 3]
                day_3_close = day_3_data['close']
                stats['valid_periods']['next_3_day'] += 1
                
                day_3_up = day_3_close > period_close
                if day_3_up:
                    stats['next_3_day_up'] += 1
                
                # Debug模式下记录详细信息
                if self.debug:
                    day_3_up_str = "是" if day_3_up else "否"
                    self.logger.info(f"  下3日({day_3_date.strftime('%Y-%m-%d')}): 收盘{day_3_close:.2f} | 上涨:{day_3_up_str}")
            
            # 检查下5个交易日
            if source_end_idx + 5 < len(source_data):
                day_5_data = source_data.iloc[source_end_idx + 5]
                day_5_date = source_data.index[source_end_idx + 5]
                day_5_close = day_5_data['close']
                stats['valid_periods']['next_5_day'] += 1
                
                day_5_up = day_5_close > period_close
                if day_5_up:
                    stats['next_5_day_up'] += 1
                
                # Debug模式下记录详细信息
                if self.debug:
                    day_5_up_str = "是" if day_5_up else "否"
                    self.logger.info(f"  下5日({day_5_date.strftime('%Y-%m-%d')}): 收盘{day_5_close:.2f} | 上涨:{day_5_up_str}")
            
            # 检查下10个交易日
            if source_end_idx + 10 < len(source_data):
                day_10_data = source_data.iloc[source_end_idx + 10]
                day_10_date = source_data.index[source_end_idx + 10]
                day_10_close = day_10_data['close']
                stats['valid_periods']['next_10_day'] += 1
                
                day_10_up = day_10_close > period_close
                if day_10_up:
                    stats['next_10_day_up'] += 1
                
                # Debug模式下记录详细信息
                if self.debug:
                    day_10_up_str = "是" if day_10_up else "否"
                    self.logger.info(f"  下10日({day_10_date.strftime('%Y-%m-%d')}): 收盘{day_10_close:.2f} | 上涨:{day_10_up_str}")
            
            # Debug模式下添加分隔线
            if self.debug:
                self.logger.info("  " + "-" * 50)
        
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
    
    def log_performance_stats(self, stats):
        """
        记录统计结果到日志
        
        Args:
            stats: 统计结果字典
        """
        if not stats:
            self.logger.info("无统计数据可输出")
            return
        
        self.logger.info("=" * 60)
        self.logger.info("高相关性期间未来表现统计")
        self.logger.info("=" * 60)
        self.logger.info(f"总高相关性期间数: {stats['total_periods']}")
        
        # 简洁的单行输出格式
        if stats['valid_periods']['next_day'] > 0:
            self.logger.info(f"下1日高开: {stats['ratios']['next_day_gap_up']:.1%}({stats['next_day_gap_up']}/{stats['valid_periods']['next_day']})")
            self.logger.info(f"下1日上涨: {stats['ratios']['next_1_day_up']:.1%}({stats['next_1_day_up']}/{stats['valid_periods']['next_day']})")
        
        if stats['valid_periods']['next_3_day'] > 0:
            self.logger.info(f"下3日上涨: {stats['ratios']['next_3_day_up']:.1%}({stats['next_3_day_up']}/{stats['valid_periods']['next_3_day']})")
        
        if stats['valid_periods']['next_5_day'] > 0:
            self.logger.info(f"下5日上涨: {stats['ratios']['next_5_day_up']:.1%}({stats['next_5_day_up']}/{stats['valid_periods']['next_5_day']})")
        
        if stats['valid_periods']['next_10_day'] > 0:
            self.logger.info(f"下10日上涨: {stats['ratios']['next_10_day_up']:.1%}({stats['next_10_day_up']}/{stats['valid_periods']['next_10_day']})")
    
    def _print_detailed_evaluation_data(self, high_correlation_periods, recent_data):
        """
        Debug模式下打印前10条评测数据的详细信息
        
        Args:
            high_correlation_periods: 高相关性期间列表
            recent_data: 最近的数据
        """
        self.logger.info("=" * 80)
        self.logger.info("DEBUG模式 - 前10条评测数据详细信息:")
        self.logger.info("=" * 80)
        
        # 为了与GPU批量版本保持一致，我们需要模拟其逻辑：
        # 1. 将所有历史期间按时间顺序排序（模拟历史期间索引顺序）
        # 2. 取前10条数据（无论是否高相关）
        
        # 首先获取所有可能的历史期间数据
        data = self.load_data()
        if data is None:
            self.logger.error("无法加载数据用于详细信息打印")
            return
        
        # 生成所有可能的历史期间（模拟GPU批量版本的历史期间列表）
        all_historical_periods = []
        
        # 计算所有可能的历史期间
        for i in range(len(data) - self.window_size + 1):
            start_idx = i
            end_idx = i + self.window_size - 1
            
            if end_idx < len(data):
                start_date = data.index[start_idx]
                end_date = data.index[end_idx]
                
                # 获取该期间的数据
                period_data = data.iloc[start_idx:end_idx + 1]
                
                # 计算与最近数据的相关性
                if len(period_data) == self.window_size and len(recent_data) == self.window_size:
                    fields = ['open', 'high', 'low', 'close', 'volume']
                    correlations = {}
                    correlation_values = []
                    
                    for field in fields:
                        if field in recent_data.columns and field in period_data.columns:
                            recent_values = recent_data[field].values
                            historical_values = period_data[field].values
                            
                            # 计算相关系数
                            corr = np.corrcoef(recent_values, historical_values)[0, 1]
                            if not np.isnan(corr):
                                correlations[field] = corr
                                correlation_values.append(corr)
                    
                    # 计算平均相关系数
                    avg_correlation = np.mean(correlation_values) if correlation_values else 0.0
                    is_high_correlation = avg_correlation >= self.threshold
                    
                    all_historical_periods.append({
                        'hist_idx': i,
                        'start_date': start_date,
                        'end_date': end_date,
                        'stock_code': self.stock_code,
                        'avg_correlation': avg_correlation,
                        'correlations': correlations,
                        'is_high_correlation': is_high_correlation,
                        'period_data': period_data
                    })
        
        # 取前10条数据（按历史期间索引顺序，模拟GPU批量版本）
        periods_to_print = all_historical_periods[:10]
        
        count = 0
        for period in periods_to_print:
            count += 1
            
            self.logger.info(f"评测数据 #{count}:")
            self.logger.info(f"  历史期间: {period['start_date'].strftime('%Y-%m-%d')} 到 {period['end_date'].strftime('%Y-%m-%d')}")
            self.logger.info(f"  来源股票: {period['stock_code']}")
            self.logger.info(f"  平均相关系数: {period['avg_correlation']:.6f}")
            self.logger.info(f"  高相关性状态: {'是' if period['is_high_correlation'] else '否'}")
            
            # 打印各字段相关系数
            self.logger.info(f"  各字段相关系数:")
            for field, corr in period['correlations'].items():
                if not np.isnan(corr):
                    self.logger.info(f"    {field}: {corr:.6f}")
            
            # 打印比较数组详情
            self._print_comparison_array_details(recent_data, period['period_data'], field_name="自身历史")
            
            self.logger.info("  " + "-" * 60)
        
        self.logger.info(f"DEBUG模式 - 已打印前{count}条评测数据详细信息")
        self.logger.info("=" * 80)

    def _print_comparison_array_details(self, recent_data, historical_data, field_name):
        """
        打印比较数组的详细信息
        
        Args:
            recent_data: 最近数据
            historical_data: 历史数据
            field_name: 字段名称
        """
        self.logger.info(f"  比较数组详情 ({field_name}):")
        self.logger.info(f"    数据窗口大小: {len(recent_data)} vs {len(historical_data)}")
        
        # 打印各字段的比较详情
        for field in ['open', 'high', 'low', 'close', 'volume']:
            if field in recent_data.columns and field in historical_data.columns:
                recent_values = recent_data[field].values
                historical_values = historical_data[field].values
                
                self.logger.info(f"    {field}字段比较:")
                
                # 前5天数据比较
                recent_first_5 = recent_values[:5] if len(recent_values) >= 5 else recent_values
                historical_first_5 = historical_values[:5] if len(historical_values) >= 5 else historical_values
                
                self.logger.info(f"      评测数据前5天: {[f'{x:.2f}' for x in recent_first_5]}")
                self.logger.info(f"      历史数据前5天: {[f'{x:.2f}' for x in historical_first_5]}")
                
                # 后5天数据比较
                recent_last_5 = recent_values[-5:] if len(recent_values) >= 5 else recent_values
                historical_last_5 = historical_values[-5:] if len(historical_values) >= 5 else historical_values
                
                self.logger.info(f"      评测数据后5天: {[f'{x:.2f}' for x in recent_last_5]}")
                self.logger.info(f"      历史数据后5天: {[f'{x:.2f}' for x in historical_last_5]}")
                
                # 统计信息
                recent_mean = np.mean(recent_values)
                recent_std = np.std(recent_values)
                historical_mean = np.mean(historical_values)
                historical_std = np.std(historical_values)
                
                self.logger.info(f"      评测数据统计: 均值={recent_mean:.2f}, 标准差={recent_std:.2f}")
                self.logger.info(f"      历史数据统计: 均值={historical_mean:.2f}, 标准差={historical_std:.2f}")

    def save_stats_to_file(self, stats):
        """
        将统计结果保存到CSV文件
        
        Args:
            stats: 统计结果字典
        """
        if not stats:
            return
        
        self.start_timer('stats_saving')
        
        # 创建统计结果目录
        stats_dir = os.path.join(self.log_dir, 'stats')
        os.makedirs(stats_dir, exist_ok=True)
        
        # 准备CSV数据
        csv_data = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 添加基本信息
        csv_data.append(['股票代码', self.stock_code])
        csv_data.append(['分析时间', timestamp])
        csv_data.append(['总高相关性期间数', stats['total_periods']])
        csv_data.append(['相关系数阈值', self.threshold])
        csv_data.append([''])  # 空行
        
        # 添加统计结果
        csv_data.append(['统计项目', '有效样本数', '成功次数', '成功比例'])
        
        if stats['valid_periods']['next_day'] > 0:
            csv_data.append(['下1个交易日高开', stats['valid_periods']['next_day'], 
                           stats['next_day_gap_up'], f"{stats['ratios']['next_day_gap_up']:.2%}"])
            csv_data.append(['下1个交易日上涨', stats['valid_periods']['next_day'], 
                           stats['next_1_day_up'], f"{stats['ratios']['next_1_day_up']:.2%}"])
        
        if stats['valid_periods']['next_3_day'] > 0:
            csv_data.append(['下3个交易日上涨', stats['valid_periods']['next_3_day'], 
                           stats['next_3_day_up'], f"{stats['ratios']['next_3_day_up']:.2%}"])
        
        if stats['valid_periods']['next_5_day'] > 0:
            csv_data.append(['下5个交易日上涨', stats['valid_periods']['next_5_day'], 
                           stats['next_5_day_up'], f"{stats['ratios']['next_5_day_up']:.2%}"])
        
        if stats['valid_periods']['next_10_day'] > 0:
            csv_data.append(['下10个交易日上涨', stats['valid_periods']['next_10_day'], 
                           stats['next_10_day_up'], f"{stats['ratios']['next_10_day_up']:.2%}"])
        
        # 保存到CSV文件
        import csv
        csv_file = os.path.join(stats_dir, f'performance_stats_{self.stock_code}_{timestamp}.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
        
        self.logger.info(f"统计结果已保存到: {csv_file}")
        self.end_timer('stats_saving')

    def analyze(self):
        """执行Pearson相关性分析"""
        self.start_timer('total_analysis')
        self.start_timer('data_loading')
        
        # 加载目标股票数据
        data = self.load_data()
        if data is None:
            self.end_timer('data_loading')
            self.end_timer('total_analysis')
            return
        
        # 检查数据量是否足够
        if len(data) < self.window_size * 2:
            self.logger.error(f"数据量不足，需要至少 {self.window_size * 2} 条记录")
            self.end_timer('data_loading')
            self.end_timer('total_analysis')
            return
        
        self.end_timer('data_loading')
        
        # 获取最近的数据（支持自定义回测日期）
        if self.backtest_date:
            # 如果指定了回测日期，从该日期往前数获取数据段
            try:
                backtest_datetime = pd.to_datetime(self.backtest_date)
                
                # 检查指定日期是否在数据范围内
                if backtest_datetime < data.index.min():
                    self.logger.error(f"指定的回测日期 {self.backtest_date} 早于所有可用数据（最早数据日期: {data.index.min().strftime('%Y-%m-%d')}）")
                    print(f"错误：指定的回测日期 {self.backtest_date} 早于所有可用数据")
                    return
                
                if backtest_datetime > data.index.max():
                    self.logger.error(f"指定的回测日期 {self.backtest_date} 晚于所有可用数据（最晚数据日期: {data.index.max().strftime('%Y-%m-%d')}）")
                    print(f"错误：指定的回测日期 {self.backtest_date} 晚于所有可用数据")
                    return
                
                # 找到指定日期或之前最近的交易日
                available_dates = data.index[data.index <= backtest_datetime]
                if len(available_dates) == 0:
                    self.logger.error(f"指定的回测日期 {self.backtest_date} 没有对应的交易日数据")
                    print(f"错误：指定的回测日期 {self.backtest_date} 没有对应的交易日数据")
                    return
                
                # 检查指定日期当天是否有数据
                exact_date_data = data[data.index.date == backtest_datetime.date()]
                if exact_date_data.empty:
                    # 如果指定日期当天没有数据，直接结束程序
                    self.logger.error(f"指定的回测日期 {self.backtest_date} 当天没有交易数据，程序结束")
                    print(f"错误：指定的回测日期 {self.backtest_date} 当天没有交易数据，程序结束")
                    return
                else:
                    self.logger.info(f"找到指定回测日期 {self.backtest_date} 的交易数据")
                
                # 使用全部数据，但以指定日期为分析终点
                recent_data = data[data.index <= backtest_datetime]
                
                if len(recent_data) < self.window_size:
                    self.logger.error(f"从指定日期 {self.backtest_date} 往前数据不足 {self.window_size} 个交易日，实际获取 {len(recent_data)} 个交易日，无法进行分析")
                    print(f"错误：从指定日期 {self.backtest_date} 往前数据不足 {self.window_size} 个交易日，无法进行分析")
                    return
                
            except Exception as e:
                self.logger.error(f"解析回测日期 {self.backtest_date} 失败: {str(e)}")
                print(f"错误：解析回测日期 {self.backtest_date} 失败: {str(e)}")
                return
        else:
            # 使用全部数据进行分析
            recent_data = data
        
        recent_start_date = recent_data.index[0]
        recent_end_date = recent_data.index[-1]
        
        self.logger.info(f"开始Pearson相关性分析")
        self.logger.info(f"目标股票: {self.stock_code}")
        self.logger.info(f"分析的最近交易日期间: {recent_start_date} 到 {recent_end_date}")
        self.logger.info(f"窗口大小: {self.window_size}, 阈值: {self.threshold}")
        
        # 存储高相关性结果
        high_correlation_periods = []
        max_correlation = 0
        max_correlation_period = None
        
        # 1. 分析自身历史数据
        self.start_timer('self_analysis')
        self.start_timer('correlation_calculation')
        self.logger.info(f"开始分析自身历史数据...")
        comparison_count = 0
        
        # 为自身历史数据分析重新定义recent_data，只包含最近window_size天的数据
        if self.backtest_date:
            # 有回测日期时，取回测日期之前的最近window_size天数据
            backtest_data = data[data.index <= pd.to_datetime(self.backtest_date)]
            recent_data_for_self = backtest_data.iloc[-self.window_size:]
            # 比较回测日期之前的历史数据段，包含所有可能的窗口
            max_historical_periods = len(backtest_data) - self.window_size + 1
        else:
            # 没有回测日期时，取最近window_size天数据
            recent_data_for_self = data.iloc[-self.window_size:]
            # 比较除了最后window_size天之外的历史数据段，包含所有可能的窗口
            max_historical_periods = len(data) - self.window_size + 1
        
        for i in range(max_historical_periods):
            historical_data = data.iloc[i:i + self.window_size]
            historical_start_date = historical_data.index[0]
            historical_end_date = historical_data.index[-1]
            
            comparison_count += 1
            
            # 计算相关系数
            avg_correlation, correlations = self.calculate_pearson_correlation(recent_data_for_self, historical_data)
            
            # 更新最高相关系数（剔除相关性系数>=0.9999的结果）
            if avg_correlation > max_correlation and avg_correlation < 0.9999:
                max_correlation = avg_correlation
                max_correlation_period = (historical_start_date, historical_end_date, self.stock_code)
            
            # Debug模式下的详细日志
            if self.debug and comparison_count % 500 == 0:
                self.logger.info(f"DEBUG - 自身历史第{comparison_count}次比较:")
                self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  平均相关系数: {avg_correlation:.6f}")
            
            # 检查是否超过阈值，并剔除相关性系数>=0.9999的结果
            if avg_correlation >= self.threshold and avg_correlation < 0.9999:
                high_correlation_periods.append({
                    'start_date': historical_start_date,
                    'end_date': historical_end_date,
                    'avg_correlation': avg_correlation,
                    'correlations': correlations,
                    'stock_code': self.stock_code,
                    'source': 'self'
                })
                
                # 记录发现的高相关性数据
                self.logger.info("发现高相关性数据 (自身历史):")
                self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  平均相关系数: {avg_correlation:.4f}")
            elif avg_correlation >= 1.0:
                # 记录被过滤的相关性系数等于1的数据
                if self.debug:
                    self.logger.info(f"过滤相关性系数等于1的数据 (自身历史): {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
        
        # 结束自身历史的相关性计算计时
        correlation_elapsed_time = self.end_timer('correlation_calculation')
        self.logger.info(f"自身历史数据分析完成，比较了 {comparison_count} 个期间，相关性计算耗时: {correlation_elapsed_time:.3f}秒")
        self.end_timer('self_analysis')
        
        # 2. 分析对比股票数据
        if self.comparison_stocks:
            self.start_timer('comparison_analysis')
            self.logger.info(f"开始分析对比股票数据...")
            cross_comparison_count = 0
            
            # 为对比股票分析重新定义recent_data，只包含目标股票最近window_size天的数据
            if self.backtest_date:
                # 有回测日期时，取目标股票回测日期之前的最近window_size天数据
                backtest_data = data[data.index <= pd.to_datetime(self.backtest_date)]
                recent_data_for_comparison = backtest_data.iloc[-self.window_size:]
            else:
                # 没有回测日期时，取目标股票最近window_size天数据
                recent_data_for_comparison = data.iloc[-self.window_size:]
            
            # 计算有效的对比股票总数
            valid_comparison_stocks = [
                (code, data) for code, data in self.loaded_stocks_data.items() 
                if data is not None and len(data) >= self.window_size
            ]
            total_comparison_stocks = len(valid_comparison_stocks)
            current_stock_index = 0
            
            for comp_stock_code, comp_data in valid_comparison_stocks:
                current_stock_index += 1
                
                # 开始单个股票的相关性计算计时
                self.start_timer('correlation_calculation')
                self.logger.info(f"正在分析对比股票: {comp_stock_code} ({current_stock_index}/{total_comparison_stocks})")
                stock_comparison_count = 0
                
                # 遍历对比股票的历史数据
                # 当使用全部数据时，我们需要比较不同的历史时间段
                # 如果指定了回测日期，则比较该日期之前的历史数据段
                # 如果没有指定回测日期，则比较除了最后window_size天之外的历史数据段
                if self.backtest_date:
                    # 有回测日期时，比较回测日期之前的历史数据段，包含所有可能的窗口
                    max_comp_historical_periods = len(comp_data[comp_data.index <= pd.to_datetime(self.backtest_date)]) - self.window_size + 1
                else:
                    # 没有回测日期时，比较除了最后window_size天之外的历史数据段，包含所有可能的窗口
                    max_comp_historical_periods = len(comp_data) - self.window_size + 1
                
                for i in range(max_comp_historical_periods):
                    historical_data = comp_data.iloc[i:i + self.window_size]
                    historical_start_date = historical_data.index[0]
                    historical_end_date = historical_data.index[-1]
                    
                    stock_comparison_count += 1
                    cross_comparison_count += 1
                    
                    # 计算相关系数
                    avg_correlation, correlations = self.calculate_pearson_correlation(recent_data_for_comparison, historical_data)
                    
                    # 更新最高相关系数（剔除相关性系数等于1的结果）
                    if avg_correlation > max_correlation and avg_correlation < 1.0:
                        max_correlation = avg_correlation
                        max_correlation_period = (historical_start_date, historical_end_date, comp_stock_code)
                    
                    # Debug模式下的详细日志
                    if self.debug and cross_comparison_count % 1000 == 0:
                        self.logger.info(f"DEBUG - 跨股票第{cross_comparison_count}次比较 ({comp_stock_code}):")
                        self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                        self.logger.info(f"  平均相关系数: {avg_correlation:.6f}")
                    
                    # 检查是否超过阈值，并剔除相关性系数等于1的结果
                    if avg_correlation >= self.threshold and avg_correlation < 1.0:
                        high_correlation_periods.append({
                            'start_date': historical_start_date,
                            'end_date': historical_end_date,
                            'avg_correlation': avg_correlation,
                            'correlations': correlations,
                            'stock_code': comp_stock_code,
                            'source': 'comparison'
                        })
                        
                        # 记录发现的高相关性数据
                        self.logger.info(f"发现高相关性数据 (对比股票 {comp_stock_code}):")
                        self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                        self.logger.info(f"  平均相关系数: {avg_correlation:.4f}")
                    elif avg_correlation >= 1.0:
                        # 记录被过滤的相关性系数等于1的数据
                        if self.debug:
                            self.logger.info(f"过滤相关性系数等于1的数据 (对比股票 {comp_stock_code}): {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                
                # 结束单个股票的相关性计算计时
                elapsed_time = self.end_timer('correlation_calculation')
                self.logger.info(f"对比股票 {comp_stock_code} 分析完成，比较了 {stock_comparison_count} 个期间，耗时: {elapsed_time:.3f}秒")
            
            self.logger.info(f"跨股票数据分析完成，总共比较了 {cross_comparison_count} 个期间")
            self.end_timer('comparison_analysis')
        
        # 开始统计计算
        self.start_timer('stats_calculation')
        
        # 输出分析结果
        self.logger.info("=" * 80)
        self.logger.info("分析总结")
        self.logger.info("=" * 80)
        self.logger.info(f"目标股票代码: {self.stock_code}")
        self.logger.info(f"分析的最近交易日期间: {recent_start_date.strftime('%Y-%m-%d')} 到 {recent_end_date.strftime('%Y-%m-%d')}")
        
        # 统计不同来源的比较次数
        total_comparisons = comparison_count
        if self.comparison_stocks:
            cross_comparison_count = sum(1 for _ in self.loaded_stocks_data.values() if _ is not None)
            total_comparisons += cross_comparison_count
            self.logger.info(f"自身历史期间比较数: {comparison_count}")
            self.logger.info(f"跨股票期间比较数: {cross_comparison_count}")
            self.logger.info(f"总比较期间数: {total_comparisons}")
        else:
            self.logger.info(f"总共比较的历史期间数: {comparison_count}")
        
        self.logger.info(f"相关系数阈值: {self.threshold}")
        self.logger.info(f"发现的高相关性期间数: {len(high_correlation_periods)}")
        
        # 按来源统计高相关性期间
        if high_correlation_periods:
            self_periods = [p for p in high_correlation_periods if p['source'] == 'self']
            comparison_periods = [p for p in high_correlation_periods if p['source'] == 'comparison']
            
            self.logger.info(f"  - 来自自身历史: {len(self_periods)} 个")
            self.logger.info(f"  - 来自对比股票: {len(comparison_periods)} 个")
            
            if comparison_periods:
                # 统计对比股票的分布
                stock_distribution = {}
                for period in comparison_periods:
                    stock_code = period['stock_code']
                    stock_distribution[stock_code] = stock_distribution.get(stock_code, 0) + 1
                
                self.logger.info("对比股票高相关性期间分布:")
                for stock_code, count in sorted(stock_distribution.items(), key=lambda x: x[1], reverse=True)[:10]:
                    self.logger.info(f"  {stock_code}: {count} 个")
                if len(stock_distribution) > 10:
                    self.logger.info(f"  ... 还有 {len(stock_distribution) - 10} 个股票")
        
        if max_correlation_period:
            self.logger.info(f"最高平均相关系数: {max_correlation:.4f}")
            self.logger.info(f"对应历史期间: {max_correlation_period[0].strftime('%Y-%m-%d')} 到 {max_correlation_period[1].strftime('%Y-%m-%d')}")
            self.logger.info(f"来源股票: {max_correlation_period[2]}")
        
        if high_correlation_periods:
            avg_high_correlation = np.mean([period['avg_correlation'] for period in high_correlation_periods])
            self.logger.info(f"高相关性期间的平均相关系数: {avg_high_correlation:.4f}")
            
            # Debug模式下输出最高相关性期间的详细信息
            if self.debug and max_correlation_period:
                # 找到最高相关性期间的详细数据
                for period in high_correlation_periods:
                    if (period['start_date'] == max_correlation_period[0] and 
                        period['end_date'] == max_correlation_period[1] and
                        period['stock_code'] == max_correlation_period[2]):
                        self.logger.info("最高相关性期间详细信息:")
                        self.logger.info(f"  来源: {period['source']} ({'自身历史' if period['source'] == 'self' else '对比股票'})")
                        self.logger.info(f"  股票代码: {period['stock_code']}")
                        self.logger.info(f"  各字段相关系数:")
                        for field, corr_data in period['correlations'].items():
                            corr = corr_data['correlation']
                            if not np.isnan(corr):
                                self.logger.info(f"    {field}: {corr:.6f}")
                        break
        else:
            self.logger.info(f"未发现相关系数超过 {self.threshold} 的历史期间")
            # 即使未发现高相关性期间，也保存基本信息到CSV
            self.save_evaluation_result(recent_end_date, None, 0)
        
        # Debug模式下打印前10条评测数据的详细信息
        if self.debug and high_correlation_periods:
            self._print_detailed_evaluation_data(high_correlation_periods, recent_data_for_self if 'recent_data_for_self' in locals() else recent_data)
        
        # Debug模式下绘制K线图对比
        if self.debug and max_correlation_period and high_correlation_periods:
            self.logger.info("=" * 80)
            self.logger.info("开始绘制K线图对比")
            self.logger.info("=" * 80)
            
            # 找到最高相关性期间的数据
            max_period_start = max_correlation_period[0]
            max_period_end = max_correlation_period[1]
            max_period_stock = max_correlation_period[2]
            
            # 根据股票代码获取对应的历史数据
            if max_period_stock == self.stock_code:
                # 来自目标股票自身的历史数据
                source_data = data
                self.logger.info(f"最高相关性期间来自目标股票 {self.stock_code} 的历史数据")
            else:
                # 来自对比股票的历史数据
                source_data = self.loaded_stocks_data.get(max_period_stock)
                self.logger.info(f"最高相关性期间来自对比股票 {max_period_stock} 的历史数据")
            
            if source_data is not None:
                try:
                    # 获取历史数据
                    historical_data = source_data.loc[max_period_start:max_period_end]
                    
                    # 准备相关性信息
                    correlation_info = {
                        'start_date': max_period_start,
                        'end_date': max_period_end,
                        'avg_correlation': max_correlation,
                        'source_stock': max_period_stock
                    }
                    
                    # 准备绘图用的recent_data - 只包含最近window_size天的数据
                    if self.backtest_date:
                        # 如果指定了回测日期，获取该日期之前的最近window_size天数据
                        backtest_end_idx = data.index.get_loc(self.backtest_date)
                        plot_recent_start_idx = max(0, backtest_end_idx - self.window_size + 1)
                        plot_recent_data = data.iloc[plot_recent_start_idx:backtest_end_idx + 1]
                    else:
                        # 如果没有指定回测日期，获取最新的window_size天数据
                        plot_recent_data = data.iloc[-self.window_size:]
                    
                    # 绘制K线图对比
                    self.plot_kline_comparison(plot_recent_data, historical_data, correlation_info)
                except Exception as e:
                    self.logger.error(f"获取历史数据时出错: {str(e)}")
                    self.logger.error(f"期间: {max_period_start} 到 {max_period_end}, 股票: {max_period_stock}")
            else:
                self.logger.error(f"无法找到股票 {max_period_stock} 的数据")
        
        self.end_timer('stats_calculation')
        
        # 计算并输出统计结果
        if high_correlation_periods:
            self.logger.info("=" * 80)
            self.logger.info("开始计算未来表现统计")
            self.logger.info("=" * 80)
            
            stats = self.calculate_future_performance_stats(data, high_correlation_periods)
            if stats:
                self.log_performance_stats(stats)
                # self.save_stats_to_file(stats)  # 已移除stats文件夹生成功能
                # 保存评测结果到CSV文件
                self.save_evaluation_result(recent_end_date, stats, len(high_correlation_periods))
            else:
                self.logger.info("无法计算统计数据")
                # 即使没有统计数据，也保存基本信息到CSV
                self.save_evaluation_result(recent_end_date, None, len(high_correlation_periods))
        
        # 结束总分析计时并输出性能统计表
        self.end_timer('total_analysis')
        self.log_performance_summary()
        
        self.logger.info("分析完成")
        
        return high_correlation_periods

def main():
    parser = argparse.ArgumentParser(description='股票Pearson相关性分析工具')
    parser.add_argument('stock_code', help='股票代码')
    parser.add_argument('--log_dir', default='logs', help='日志目录 (默认: logs)')
    parser.add_argument('--window_size', type=int, default=15, help='分析窗口大小 (默认: 15)')
    parser.add_argument('--threshold', type=float, default=0.85, help='相关系数阈值 (默认: 0.85)')
    parser.add_argument('--debug', action='store_true', help='开启debug模式（会影响性能）')
    
    # 跨股票对比参数
    parser.add_argument('--comparison_mode', choices=['none', 'top10', 'industry', 'custom'],
                        default='top10', help='对比模式: none(仅自身), top10(市值前10), industry(同行业), custom(自定义) (默认: top10)')
    parser.add_argument('--comparison_stocks', nargs='*', 
                       help='自定义对比股票列表，用空格分隔 (仅在comparison_mode=custom时有效)')
    parser.add_argument('--no_comparison', action='store_true', 
                       help='禁用跨股票对比，仅分析自身历史数据')
    parser.add_argument('--backtest_date', type=str, 
                       help='指定回测起始日期 (格式: YYYY-MM-DD)，从该日期往前数获取数据段进行分析，默认使用最后一个交易日')
    parser.add_argument('--csv_filename', type=str, default='evaluation_results.csv',
                       help='指定CSV结果文件名 (默认: evaluation_results.csv)')
    parser.add_argument('--earliest_date', type=str, default='2020-01-01',
                       help='数据过滤的最早日期 (格式: YYYY-MM-DD, 默认: 2020-01-01)')
    
    args = parser.parse_args()
    
    # 清空logs文件夹
    def clear_logs_directory(log_dir):
        """清空logs目录下的内容，但保留所有CSV文件"""
        import shutil
        if os.path.exists(log_dir):
            try:
                # 删除目录下的所有内容，但保留CSV文件
                for item in os.listdir(log_dir):
                    if item.endswith('.csv'):
                        continue  # 跳过所有CSV文件
                    item_path = os.path.join(log_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                print(f"已清空 {log_dir} 目录（保留所有CSV文件）")
            except Exception as e:
                print(f"清空 {log_dir} 目录时出错: {e}")
        else:
            print(f"{log_dir} 目录不存在，将自动创建")
    
    # 设置固定的绝对路径
    script_dir = r'C:\Users\17701\github\my_first_repo\stockapi\stock_backtest\pearson_found'
    fixed_log_dir = os.path.join(script_dir, 'logs')
    
    # 清空logs目录 - 已注释，不再删除日志文件
    # clear_logs_directory(fixed_log_dir)
    
    # 处理对比模式
    if args.no_comparison:
        comparison_mode = 'none'
        comparison_stocks = None
    else:
        comparison_mode = args.comparison_mode
        comparison_stocks = args.comparison_stocks if args.comparison_mode == 'custom' else None
    
    # 创建分析器并执行分析
    analyzer = PearsonAnalyzer(
        stock_code=args.stock_code,
        log_dir=args.log_dir,  # 这个参数现在在PearsonAnalyzer内部会被忽略，使用固定路径
        window_size=args.window_size,
        threshold=args.threshold,
        debug=args.debug,
        comparison_mode=comparison_mode,
        comparison_stocks=comparison_stocks,
        backtest_date=args.backtest_date,
        csv_filename=args.csv_filename,
        earliest_date=args.earliest_date
    )
    
    results = analyzer.analyze()
    
    # 输出简要结果到控制台
    if results:
        print(f"分析完成！发现 {len(results)} 个高相关性期间，相关系数阈值: {args.threshold}")
        
        # 统计不同来源的结果
        self_periods = [p for p in results if p['source'] == 'self']
        comparison_periods = [p for p in results if p['source'] == 'comparison']
        
        print(f"  - 来自自身历史: {len(self_periods)} 个")
        print(f"  - 来自对比股票: {len(comparison_periods)} 个")
        
        if results:
            max_corr = max(results, key=lambda x: x['avg_correlation'])
            print(f"最高平均相关系数: {max_corr['avg_correlation']:.4f}")
            print(f"对应期间: {max_corr['start_date'].strftime('%Y-%m-%d')} 到 {max_corr['end_date'].strftime('%Y-%m-%d')}")
            print(f"来源股票: {max_corr['stock_code']} ({'自身历史' if max_corr['source'] == 'self' else '对比股票'})")
    else:
        print(f"分析完成！未发现相关系数超过 {args.threshold} 的历史期间")
    
    print(f"详细结果请查看日志文件: {analyzer.log_dir}")

if __name__ == "__main__":
    main()