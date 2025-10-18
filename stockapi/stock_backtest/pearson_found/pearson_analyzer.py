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


class PearsonAnalyzer:
    def __init__(self, stock_code, log_dir='logs', window_size=20, threshold=0.8, debug=False):
        """
        初始化Pearson相关性分析器
        
        Args:
            stock_code: 股票代码
            log_dir: 日志目录
            window_size: 分析窗口大小（交易日数量）
            threshold: 相关系数阈值
            debug: 是否开启debug模式（影响性能）
        """
        self.stock_code = stock_code
        self.log_dir = log_dir
        self.window_size = window_size
        self.threshold = threshold
        self.debug = debug
        self.data_loader = None
        self.logger = None
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志
        self._setup_logging()
        
        self.logger.info(f"初始化Pearson分析器，股票代码: {stock_code}")
        self.logger.info(f"窗口大小: {window_size}, 阈值: {threshold}, Debug模式: {debug}")
    
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
        """加载股票数据"""
        self.logger.info("初始化数据加载器")
        self.data_loader = StockDataLoader()
        
        self.logger.info(f"开始加载股票 {self.stock_code} 的数据")
        data = self.data_loader.load_stock_data(self.stock_code)
        
        if data is None or data.empty:
            self.logger.error(f"无法加载股票 {self.stock_code} 的数据")
            return None
        
        # 数据过滤：确保价格为正数，成交量大于0
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
            self.logger.info(f"数据过滤完成，移除 {removed_count} 条异常数据")
        
        self.logger.info(f"成功加载 {len(data)} 条记录，日期范围: {data.index[0]} 到 {data.index[-1]}")
        return data
    
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
            ax1.set_title(f'Historical High Correlation Period ({historical_start} to {historical_end})\nAvg Correlation: {correlation_info["avg_correlation"]:.4f}')
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
            ax2.set_title(f'Recent Trading Period ({recent_start} to {recent_end})')
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
    
    def analyze(self):
        """执行Pearson相关性分析"""
        # 加载数据
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
        self.logger.info(f"分析的最近交易日期间: {recent_start_date} 到 {recent_end_date}")
        self.logger.info(f"窗口大小: {self.window_size}, 阈值: {self.threshold}")
        
        # 存储高相关性结果
        high_correlation_periods = []
        max_correlation = 0
        max_correlation_period = None
        
        # 遍历历史数据
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
                max_correlation_period = (historical_start_date, historical_end_date)
            
            # Debug模式下的详细日志
            if self.debug and comparison_count % 500 == 0:
                self.logger.info(f"DEBUG - 第{comparison_count}次比较:")
                self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  各字段相关系数:")
                for field, corr_data in correlations.items():
                    corr = corr_data['correlation']
                    p_val = corr_data['p_value']
                    if not np.isnan(corr):
                        self.logger.info(f"    {field}: {corr:.6f} (p-value: {p_val:.6f})")
                    else:
                        self.logger.info(f"    {field}: NaN")
                self.logger.info(f"  平均相关系数: {avg_correlation:.6f}")
                
                # Debug模式下计算统计信息
                self.logger.info(f"  历史数据统计:")
                for field in ['open', 'high', 'low', 'close', 'volume']:
                    mean_val = historical_data[field].mean()
                    std_val = historical_data[field].std()
                    self.logger.info(f"    {field}: 均值={mean_val:.4f}, 标准差={std_val:.4f}")
                self.logger.info("----------------------------------------")
            
            # 检查是否超过阈值
            if avg_correlation >= self.threshold:
                high_correlation_periods.append({
                    'start_date': historical_start_date,
                    'end_date': historical_end_date,
                    'avg_correlation': avg_correlation,
                    'correlations': correlations
                })
                
                # 记录发现的高相关性数据
                self.logger.info("发现高相关性数据:")
                self.logger.info(f"  历史期间: {historical_start_date.strftime('%Y-%m-%d')} 到 {historical_end_date.strftime('%Y-%m-%d')}")
                self.logger.info(f"  平均相关系数: {avg_correlation:.4f}")
                for field, corr_data in correlations.items():
                    corr = corr_data['correlation']
                    p_val = corr_data['p_value']
                    if not np.isnan(corr):
                        self.logger.info(f"    {field}: {corr:.4f} (p-value: {p_val:.4f})")
                    else:
                        self.logger.info(f"    {field}: NaN")
                self.logger.info("------------------------------------------------------------")
        
        # 输出分析结果
        self.logger.info("=" * 80)
        self.logger.info("分析总结")
        self.logger.info("=" * 80)
        self.logger.info(f"股票代码: {self.stock_code}")
        self.logger.info(f"分析的最近交易日期间: {recent_start_date.strftime('%Y-%m-%d')} 到 {recent_end_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"总共比较的历史期间数: {comparison_count}")
        self.logger.info(f"相关系数阈值: {self.threshold}")
        self.logger.info(f"发现的高相关性期间数: {len(high_correlation_periods)}")
        
        if max_correlation_period:
            self.logger.info(f"最高平均相关系数: {max_correlation:.4f}")
            self.logger.info(f"对应历史期间: {max_correlation_period[0].strftime('%Y-%m-%d')} 到 {max_correlation_period[1].strftime('%Y-%m-%d')}")
        
        if high_correlation_periods:
            avg_high_correlation = np.mean([period['avg_correlation'] for period in high_correlation_periods])
            self.logger.info(f"高相关性期间的平均相关系数: {avg_high_correlation:.4f}")
            
            # Debug模式下输出最高相关性期间的详细信息
            if self.debug and max_correlation_period:
                # 找到最高相关性期间的详细数据
                for period in high_correlation_periods:
                    if (period['start_date'] == max_correlation_period[0] and 
                        period['end_date'] == max_correlation_period[1]):
                        self.logger.info("最高相关性期间详细信息:")
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
            
            # 获取历史数据
            historical_data = data.loc[max_period_start:max_period_end]
            
            # 准备相关性信息
            correlation_info = {
                'start_date': max_period_start,
                'end_date': max_period_end,
                'avg_correlation': max_correlation
            }
            
            # 绘制K线图对比
            self.plot_kline_comparison(recent_data, historical_data, correlation_info)
        
        self.logger.info("分析完成")
        
        return high_correlation_periods

def main():
    parser = argparse.ArgumentParser(description='股票Pearson相关性分析工具')
    parser.add_argument('stock_code', help='股票代码')
    parser.add_argument('--log_dir', default='logs', help='日志目录 (默认: logs)')
    parser.add_argument('--window_size', type=int, default=20, help='分析窗口大小 (默认: 20)')
    parser.add_argument('--threshold', type=float, default=0.8, help='相关系数阈值 (默认: 0.8)')
    parser.add_argument('--debug', action='store_true', help='开启debug模式（会影响性能）')
    
    args = parser.parse_args()
    
    # 创建分析器并执行分析
    analyzer = PearsonAnalyzer(
        stock_code=args.stock_code,
        log_dir=args.log_dir,
        window_size=args.window_size,
        threshold=args.threshold,
        debug=args.debug
    )
    
    results = analyzer.analyze()
    
    # 输出简要结果到控制台
    if results:
        print(f"分析完成！发现 {len(results)} 个高相关性期间，相关系数阈值: {args.threshold}")
        if results:
            max_corr = max(results, key=lambda x: x['avg_correlation'])
            print(f"最高平均相关系数: {max_corr['avg_correlation']:.4f}")
            print(f"对应期间: {max_corr['start_date'].strftime('%Y-%m-%d')} 到 {max_corr['end_date'].strftime('%Y-%m-%d')}")
    else:
        print(f"分析完成！未发现相关系数超过 {args.threshold} 的历史期间")
    
    print(f"详细结果请查看日志文件: {analyzer.log_dir}")

if __name__ == "__main__":
    main()