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


class PearsonAnalyzer:
    def __init__(self, stock_code, log_dir='logs', window_size=20, threshold=0.8, debug=False, 
                 comparison_stocks=None, comparison_mode='default'):
        """
        初始化Pearson相关性分析器
        
        Args:
            stock_code: 目标股票代码
            log_dir: 日志目录
            window_size: 分析窗口大小（交易日数量）
            threshold: 相关系数阈值
            debug: 是否开启debug模式（影响性能）
            comparison_stocks: 自定义对比股票列表
            comparison_mode: 对比模式 ('default', 'top100', 'banks', 'tech', 'new_energy', 'healthcare', 'consumer', 'self_only')
        """
        self.stock_code = stock_code
        self.log_dir = log_dir
        self.window_size = window_size
        self.threshold = threshold
        self.debug = debug
        self.comparison_mode = comparison_mode
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
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志
        self._setup_logging()
        
        self.logger.info(f"初始化Pearson分析器，目标股票: {stock_code}")
        self.logger.info(f"窗口大小: {window_size}, 阈值: {threshold}, Debug模式: {debug}")
        self.logger.info(f"对比模式: {comparison_mode}, 对比股票数量: {len(self.comparison_stocks)}")
        if self.debug:
            self.logger.info(f"对比股票列表: {self.comparison_stocks[:10]}{'...' if len(self.comparison_stocks) > 10 else ''}")
    
    def _setup_logging(self):
        """设置日志配置"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"pearson_analysis_{self.stock_code}_{timestamp}.log"
        log_path = os.path.join(self.log_dir, log_filename)
        
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
    
    def load_data(self):
        """加载目标股票数据"""
        self.logger.info("初始化数据加载器")
        self.data_loader = StockDataLoader()
        
        self.logger.info(f"开始加载目标股票 {self.stock_code} 的数据")
        data = self.data_loader.load_stock_data(self.stock_code)
        
        if data is None or data.empty:
            self.logger.error(f"无法加载股票 {self.stock_code} 的数据")
            return None
        
        # 数据过滤：确保价格为正数，成交量大于0
        self.data = self._filter_data(data, self.stock_code)
        
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
    
    def plot_kline_comparison(self, recent_data, historical_data, correlation_info):
        """
        绘制最近数据和历史高相关性数据的K线图对比
        
        Args:
            recent_data: 最近的数据
            historical_data: 历史高相关性数据
            correlation_info: 相关性信息字典
        """
        try:
            # 创建图表目录
            chart_dir = os.path.join(self.log_dir, 'charts')
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
                    volume=ax1_vol)
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
                    volume=ax2_vol)
            ax2.set_title(f'Recent Trading Period - Target Stock {self.stock_code}\n({recent_start} to {recent_end})')
            ax2.set_ylabel('Price')
            ax2_vol.set_ylabel('Volume')
            
            plt.tight_layout()
            comparison_file = os.path.join(chart_dir, f'kline_comparison_{self.stock_code}.png')
            plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"K线对比图已保存: {comparison_file}")
            
        except Exception as e:
            self.logger.error(f"绘制K线图时出错: {str(e)}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def calculate_pearson_correlation(self, recent_data, historical_data):
        """
        计算Pearson相关系数
        
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
            
            # 找到该期间结束后的数据位置
            try:
                end_idx = data.index.get_loc(end_date)
            except KeyError:
                continue
            
            # 获取期间最后一天的收盘价
            period_close = data.iloc[end_idx]['close']
            
            # Debug模式下记录每个期间的详细信息
            if self.debug:
                self.logger.info(f"高相关性期间 #{i}:")
                self.logger.info(f"  期间: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  相关系数: {avg_correlation:.4f}")
                self.logger.info(f"  期间收盘价: {period_close:.2f}")
            
            # 检查下1个交易日
            if end_idx + 1 < len(data):
                next_day_data = data.iloc[end_idx + 1]
                next_day_date = data.index[end_idx + 1]
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
            if end_idx + 3 < len(data):
                day_3_data = data.iloc[end_idx + 3]
                day_3_date = data.index[end_idx + 3]
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
            if end_idx + 5 < len(data):
                day_5_data = data.iloc[end_idx + 5]
                day_5_date = data.index[end_idx + 5]
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
            if end_idx + 10 < len(data):
                day_10_data = data.iloc[end_idx + 10]
                day_10_date = data.index[end_idx + 10]
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
    
    def save_stats_to_file(self, stats):
        """
        将统计结果保存到CSV文件
        
        Args:
            stats: 统计结果字典
        """
        if not stats:
            return
        
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

    def analyze(self):
        """执行Pearson相关性分析"""
        # 加载目标股票数据
        data = self.load_data()
        if data is None:
            return
        
        # 检查数据量是否足够
        if len(data) < self.window_size * 2:
            self.logger.error(f"数据量不足，需要至少 {self.window_size * 2} 条记录")
            return
        
        # 获取最近的数据
        recent_data = data.tail(self.window_size)
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
        self.logger.info(f"开始分析自身历史数据...")
        comparison_count = 0
        for i in range(len(data) - self.window_size):
            historical_data = data.iloc[i:i + self.window_size]
            historical_start_date = historical_data.index[0]
            historical_end_date = historical_data.index[-1]
            
            # 跳过与最近数据重叠的期间
            if historical_end_date >= recent_start_date:
                continue
            
            comparison_count += 1
            
            # 计算相关系数
            avg_correlation, correlations = self.calculate_pearson_correlation(recent_data, historical_data)
            
            # 更新最高相关系数
            if avg_correlation > max_correlation:
                max_correlation = avg_correlation
                max_correlation_period = (historical_start_date, historical_end_date, self.stock_code)
            
            # Debug模式下的详细日志
            if self.debug and comparison_count % 500 == 0:
                self.logger.info(f"DEBUG - 自身历史第{comparison_count}次比较:")
                self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  平均相关系数: {avg_correlation:.6f}")
            
            # 检查是否超过阈值
            if avg_correlation >= self.threshold:
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
        
        self.logger.info(f"自身历史数据分析完成，比较了 {comparison_count} 个期间")
        
        # 2. 分析对比股票数据
        if self.comparison_stocks:
            self.logger.info(f"开始分析对比股票数据...")
            cross_comparison_count = 0
            
            for comp_stock_code, comp_data in self.loaded_stocks_data.items():
                if comp_data is None or len(comp_data) < self.window_size:
                    continue
                
                self.logger.info(f"正在分析对比股票: {comp_stock_code}")
                stock_comparison_count = 0
                
                # 遍历对比股票的历史数据
                for i in range(len(comp_data) - self.window_size):
                    historical_data = comp_data.iloc[i:i + self.window_size]
                    historical_start_date = historical_data.index[0]
                    historical_end_date = historical_data.index[-1]
                    
                    # 跳过与最近数据重叠的期间（基于日期）
                    if historical_end_date >= recent_start_date:
                        continue
                    
                    stock_comparison_count += 1
                    cross_comparison_count += 1
                    
                    # 计算相关系数
                    avg_correlation, correlations = self.calculate_pearson_correlation(recent_data, historical_data)
                    
                    # 更新最高相关系数
                    if avg_correlation > max_correlation:
                        max_correlation = avg_correlation
                        max_correlation_period = (historical_start_date, historical_end_date, comp_stock_code)
                    
                    # Debug模式下的详细日志
                    if self.debug and cross_comparison_count % 1000 == 0:
                        self.logger.info(f"DEBUG - 跨股票第{cross_comparison_count}次比较 ({comp_stock_code}):")
                        self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                        self.logger.info(f"  平均相关系数: {avg_correlation:.6f}")
                    
                    # 检查是否超过阈值
                    if avg_correlation >= self.threshold:
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
                
                self.logger.info(f"对比股票 {comp_stock_code} 分析完成，比较了 {stock_comparison_count} 个期间")
            
            self.logger.info(f"跨股票数据分析完成，总共比较了 {cross_comparison_count} 个期间")
        
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
                    
                    # 绘制K线图对比
                    self.plot_kline_comparison(recent_data, historical_data, correlation_info)
                except Exception as e:
                    self.logger.error(f"获取历史数据时出错: {str(e)}")
                    self.logger.error(f"期间: {max_period_start} 到 {max_period_end}, 股票: {max_period_stock}")
            else:
                self.logger.error(f"无法找到股票 {max_period_stock} 的数据")
        
        # 计算并输出统计结果
        if high_correlation_periods:
            self.logger.info("=" * 80)
            self.logger.info("开始计算未来表现统计")
            self.logger.info("=" * 80)
            
            stats = self.calculate_future_performance_stats(data, high_correlation_periods)
            if stats:
                self.log_performance_stats(stats)
                self.save_stats_to_file(stats)
            else:
                self.logger.info("无法计算统计数据")
        
        self.logger.info("分析完成")
        
        return high_correlation_periods

def main():
    parser = argparse.ArgumentParser(description='股票Pearson相关性分析工具')
    parser.add_argument('stock_code', help='股票代码')
    parser.add_argument('--log_dir', default='logs', help='日志目录 (默认: logs)')
    parser.add_argument('--window_size', type=int, default=20, help='分析窗口大小 (默认: 20)')
    parser.add_argument('--threshold', type=float, default=0.8, help='相关系数阈值 (默认: 0.8)')
    parser.add_argument('--debug', action='store_true', help='开启debug模式（会影响性能）')
    
    # 跨股票对比参数
    parser.add_argument('--comparison_mode', choices=['none', 'top100', 'industry', 'custom'], 
                       default='top100', help='对比模式: none(仅自身), top100(市值前100), industry(同行业), custom(自定义) (默认: top100)')
    parser.add_argument('--comparison_stocks', nargs='*', 
                       help='自定义对比股票列表，用空格分隔 (仅在comparison_mode=custom时有效)')
    parser.add_argument('--no_comparison', action='store_true', 
                       help='禁用跨股票对比，仅分析自身历史数据')
    
    args = parser.parse_args()
    
    # 清空logs文件夹
    def clear_logs_directory(log_dir):
        """清空logs目录下的所有内容"""
        import shutil
        if os.path.exists(log_dir):
            try:
                # 删除目录下的所有内容
                for item in os.listdir(log_dir):
                    item_path = os.path.join(log_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                print(f"已清空 {log_dir} 目录")
            except Exception as e:
                print(f"清空 {log_dir} 目录时出错: {e}")
        else:
            print(f"{log_dir} 目录不存在，将自动创建")
    
    # 清空logs目录
    clear_logs_directory(args.log_dir)
    
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
        log_dir=args.log_dir,
        window_size=args.window_size,
        threshold=args.threshold,
        debug=args.debug,
        comparison_mode=comparison_mode,
        comparison_stocks=comparison_stocks
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