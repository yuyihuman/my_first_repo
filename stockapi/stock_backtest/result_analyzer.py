# coding:utf-8
"""
结果整理输出模块 - 处理和展示回测结果

包含结果分析、统计计算、可视化和报告生成功能
"""

import pandas as pd
import numpy as np
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json


class ResultAnalyzer:
    """回测结果分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析信号数据
        
        Args:
            signals: 信号列表
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 转换为DataFrame便于分析
        df = pd.DataFrame(signals)
        
        # 基本统计
        total_signals = len(df)
        unique_stocks = df['stock_code'].nunique() if 'stock_code' in df.columns else 0
        
        # 收益率分析
        returns_analysis = {}
        if 'next_day_return' in df.columns:
            valid_returns = df['next_day_return'].dropna()
            if len(valid_returns) > 0:
                returns_analysis = {
                    'total_valid_returns': len(valid_returns),
                    'mean_return': valid_returns.mean(),
                    'median_return': valid_returns.median(),
                    'std_return': valid_returns.std(),
                    'min_return': valid_returns.min(),
                    'max_return': valid_returns.max(),
                    'positive_return_ratio': (valid_returns > 0).mean(),
                    'negative_return_ratio': (valid_returns < 0).mean(),
                    'zero_return_ratio': (valid_returns == 0).mean()
                }
        
        # 时间分布分析
        time_analysis = {}
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            time_analysis = {
                'date_range': {
                    'start_date': df['date'].min().strftime('%Y-%m-%d'),
                    'end_date': df['date'].max().strftime('%Y-%m-%d')
                },
                'signals_by_month': {str(k): v for k, v in df.groupby(df['date'].dt.to_period('M')).size().to_dict().items()},
                'signals_by_weekday': df.groupby(df['date'].dt.day_name()).size().to_dict()
            }
        
        # 股票分布分析
        stock_analysis = {}
        if 'stock_code' in df.columns:
            stock_counts = df['stock_code'].value_counts()
            stock_analysis = {
                'top_10_stocks': stock_counts.head(10).to_dict(),
                'stocks_with_single_signal': (stock_counts == 1).sum(),
                'stocks_with_multiple_signals': (stock_counts > 1).sum()
            }
        
        return {
            'basic_stats': {
                'total_signals': total_signals,
                'unique_stocks': unique_stocks
            },
            'returns_analysis': returns_analysis,
            'time_analysis': time_analysis,
            'stock_analysis': stock_analysis
        }
    
    def calculate_detailed_statistics(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算详细的关键比例统计信息
        
        Args:
            signals: 信号列表
            
        Returns:
            dict: 详细统计信息
        """
        if not signals:
            return {}
        
        # 转换为DataFrame便于计算
        df = pd.DataFrame(signals)
        
        # 基本统计
        total_count = len(df)
        unique_stocks = df['stock_code'].nunique() if 'stock_code' in df.columns else 0
        
        # 次日表现统计
        next_open_up_count = len(df[df.get('next_open_change_pct', 0) > 0]) if 'next_open_change_pct' in df.columns else 0
        next_close_up_count = len(df[df.get('next_close_change_pct', 0) > 0]) if 'next_close_change_pct' in df.columns else 0
        
        # 开盘收盘组合统计
        high_open_high_close_count = 0  # 高开高走 (次日开盘上涨且收盘高于开盘)
        high_open_low_close_count = 0   # 高开低走 (次日开盘上涨且收盘低于开盘)
        low_open_close_up_count = 0     # 低开高走 (次日开盘下跌且收盘高于开盘)
        low_open_low_close_count = 0    # 低开低走 (次日开盘下跌且收盘低于开盘)
        
        if 'next_open_change_pct' in df.columns and 'next_intraday_change_pct' in df.columns:
            high_open_high_close_count = len(df[(df['next_open_change_pct'] > 0) & (df['next_intraday_change_pct'] > 0)])
            high_open_low_close_count = len(df[(df['next_open_change_pct'] > 0) & (df['next_intraday_change_pct'] < 0)])
            low_open_close_up_count = len(df[(df['next_open_change_pct'] < 0) & (df['next_intraday_change_pct'] > 0)])
            low_open_low_close_count = len(df[(df['next_open_change_pct'] < 0) & (df['next_intraday_change_pct'] < 0)])
        
        # 中长期表现统计 - 只统计有完整数据的交易日
        day3_up_count = len(df[(df.get('day3_change_pct', 0) > 0) & pd.notna(df.get('day3_change_pct'))]) if 'day3_change_pct' in df.columns else 0
        day5_up_count = len(df[(df.get('day5_change_pct', 0) > 0) & pd.notna(df.get('day5_change_pct'))]) if 'day5_change_pct' in df.columns else 0
        day10_up_count = len(df[(df.get('day10_change_pct', 0) > 0) & pd.notna(df.get('day10_change_pct'))]) if 'day10_change_pct' in df.columns else 0
        
        # 统计有完整数据的交易日总数
        day3_total_count = len(df[pd.notna(df.get('day3_change_pct'))]) if 'day3_change_pct' in df.columns else 0
        day5_total_count = len(df[pd.notna(df.get('day5_change_pct'))]) if 'day5_change_pct' in df.columns else 0
        day10_total_count = len(df[pd.notna(df.get('day10_change_pct'))]) if 'day10_change_pct' in df.columns else 0
        
        # 计算高开高走股票的后续表现
        high_open_high_close_day3_up = 0
        high_open_high_close_day5_up = 0
        high_open_high_close_day10_up = 0
        
        if high_open_high_close_count > 0:
            high_open_high_close_signals = df[(df.get('next_open_change_pct', 0) > 0) & (df.get('next_intraday_change_pct', 0) > 0)]
            if 'day3_from_next_change_pct' in df.columns:
                high_open_high_close_day3_up = len(high_open_high_close_signals[(high_open_high_close_signals['day3_from_next_change_pct'] > 0) & pd.notna(high_open_high_close_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                high_open_high_close_day5_up = len(high_open_high_close_signals[(high_open_high_close_signals['day5_from_next_change_pct'] > 0) & pd.notna(high_open_high_close_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                high_open_high_close_day10_up = len(high_open_high_close_signals[(high_open_high_close_signals['day10_from_next_change_pct'] > 0) & pd.notna(high_open_high_close_signals['day10_from_next_change_pct'])])
        
        # 计算高开低走股票的后续表现
        high_open_low_close_day3_up = 0
        high_open_low_close_day5_up = 0
        high_open_low_close_day10_up = 0
        
        if high_open_low_close_count > 0:
            high_open_low_close_signals = df[(df.get('next_open_change_pct', 0) > 0) & (df.get('next_intraday_change_pct', 0) < 0)]
            if 'day3_from_next_change_pct' in df.columns:
                high_open_low_close_day3_up = len(high_open_low_close_signals[(high_open_low_close_signals['day3_from_next_change_pct'] > 0) & pd.notna(high_open_low_close_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                high_open_low_close_day5_up = len(high_open_low_close_signals[(high_open_low_close_signals['day5_from_next_change_pct'] > 0) & pd.notna(high_open_low_close_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                high_open_low_close_day10_up = len(high_open_low_close_signals[(high_open_low_close_signals['day10_from_next_change_pct'] > 0) & pd.notna(high_open_low_close_signals['day10_from_next_change_pct'])])
        
        # 计算低开收盘上涨股票的后续表现
        low_open_close_up_day3_up = 0
        low_open_close_up_day5_up = 0
        low_open_close_up_day10_up = 0
        
        if low_open_close_up_count > 0:
            low_open_close_up_signals = df[(df.get('next_open_change_pct', 0) < 0) & (df.get('next_intraday_change_pct', 0) > 0)]
            if 'day3_from_next_change_pct' in df.columns:
                low_open_close_up_day3_up = len(low_open_close_up_signals[(low_open_close_up_signals['day3_from_next_change_pct'] > 0) & pd.notna(low_open_close_up_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                low_open_close_up_day5_up = len(low_open_close_up_signals[(low_open_close_up_signals['day5_from_next_change_pct'] > 0) & pd.notna(low_open_close_up_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                low_open_close_up_day10_up = len(low_open_close_up_signals[(low_open_close_up_signals['day10_from_next_change_pct'] > 0) & pd.notna(low_open_close_up_signals['day10_from_next_change_pct'])])
        
        # 计算低开低走股票的后续表现
        low_open_low_close_day3_up = 0
        low_open_low_close_day5_up = 0
        low_open_low_close_day10_up = 0
        
        if low_open_low_close_count > 0:
            low_open_low_close_signals = df[(df.get('next_open_change_pct', 0) < 0) & (df.get('next_intraday_change_pct', 0) < 0)]
            if 'day3_from_next_change_pct' in df.columns:
                low_open_low_close_day3_up = len(low_open_low_close_signals[(low_open_low_close_signals['day3_from_next_change_pct'] > 0) & pd.notna(low_open_low_close_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                low_open_low_close_day5_up = len(low_open_low_close_signals[(low_open_low_close_signals['day5_from_next_change_pct'] > 0) & pd.notna(low_open_low_close_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                low_open_low_close_day10_up = len(low_open_low_close_signals[(low_open_low_close_signals['day10_from_next_change_pct'] > 0) & pd.notna(low_open_low_close_signals['day10_from_next_change_pct'])])
        
        # 计算百分比
        def safe_percentage(numerator, denominator):
            return (numerator / denominator * 100) if denominator > 0 else 0.0
        
        # 计算有完整数据的各种开盘收盘组合的总数
        high_open_high_close_with_data_count = len(df[(df.get('next_open_change_pct', 0) > 0) & (df.get('next_intraday_change_pct', 0) > 0) & 
                                                     pd.notna(df.get('day3_from_next_change_pct')) & 
                                                     pd.notna(df.get('day5_from_next_change_pct')) & 
                                                     pd.notna(df.get('day10_from_next_change_pct'))])
        high_open_low_close_with_data_count = len(df[(df.get('next_open_change_pct', 0) > 0) & (df.get('next_intraday_change_pct', 0) < 0) & 
                                                    pd.notna(df.get('day3_from_next_change_pct')) & 
                                                    pd.notna(df.get('day5_from_next_change_pct')) & 
                                                    pd.notna(df.get('day10_from_next_change_pct'))])
        low_open_close_up_with_data_count = len(df[(df.get('next_open_change_pct', 0) < 0) & (df.get('next_intraday_change_pct', 0) > 0) & 
                                                  pd.notna(df.get('day3_from_next_change_pct')) & 
                                                  pd.notna(df.get('day5_from_next_change_pct')) & 
                                                  pd.notna(df.get('day10_from_next_change_pct'))])
        low_open_low_close_with_data_count = len(df[(df.get('next_open_change_pct', 0) < 0) & (df.get('next_intraday_change_pct', 0) < 0) & 
                                                   pd.notna(df.get('day3_from_next_change_pct')) & 
                                                   pd.notna(df.get('day5_from_next_change_pct')) & 
                                                   pd.notna(df.get('day10_from_next_change_pct'))])

        return {
            'total_count': total_count,
            'unique_stocks': unique_stocks,
            'next_open_up_count': next_open_up_count,
            'next_close_up_count': next_close_up_count,
            'high_open_high_close_count': high_open_high_close_count,
            'high_open_low_close_count': high_open_low_close_count,
            'low_open_close_up_count': low_open_close_up_count,
            'low_open_low_close_count': low_open_low_close_count,
            'high_open_high_close_with_data_count': high_open_high_close_with_data_count,
            'high_open_low_close_with_data_count': high_open_low_close_with_data_count,
            'low_open_close_up_with_data_count': low_open_close_up_with_data_count,
            'low_open_low_close_with_data_count': low_open_low_close_with_data_count,
            'day3_up_count': day3_up_count,
            'day5_up_count': day5_up_count,
            'day10_up_count': day10_up_count,
            'day3_total_count': day3_total_count,
            'day5_total_count': day5_total_count,
            'day10_total_count': day10_total_count,
            'high_open_high_close_day3_up': high_open_high_close_day3_up,
            'high_open_high_close_day5_up': high_open_high_close_day5_up,
            'high_open_high_close_day10_up': high_open_high_close_day10_up,
            'high_open_low_close_day3_up': high_open_low_close_day3_up,
            'high_open_low_close_day5_up': high_open_low_close_day5_up,
            'high_open_low_close_day10_up': high_open_low_close_day10_up,
            'low_open_close_up_day3_up': low_open_close_up_day3_up,
            'low_open_close_up_day5_up': low_open_close_up_day5_up,
            'low_open_close_up_day10_up': low_open_close_up_day10_up,
            'low_open_low_close_day3_up': low_open_low_close_day3_up,
            'low_open_low_close_day5_up': low_open_low_close_day5_up,
            'low_open_low_close_day10_up': low_open_low_close_day10_up,
            'next_open_up_pct': safe_percentage(next_open_up_count, total_count),
            'next_close_up_pct': safe_percentage(next_close_up_count, total_count),
            'high_open_high_close_pct': safe_percentage(high_open_high_close_count, total_count),
            'high_open_low_close_pct': safe_percentage(high_open_low_close_count, total_count),
            'low_open_close_up_pct': safe_percentage(low_open_close_up_count, total_count),
            'low_open_low_close_pct': safe_percentage(low_open_low_close_count, total_count),
            'day3_up_pct': safe_percentage(day3_up_count, day3_total_count),
            'day5_up_pct': safe_percentage(day5_up_count, day5_total_count),
            'day10_up_pct': safe_percentage(day10_up_count, day10_total_count),
            'high_open_high_close_day3_up_pct': safe_percentage(high_open_high_close_day3_up, high_open_high_close_with_data_count),
            'high_open_high_close_day5_up_pct': safe_percentage(high_open_high_close_day5_up, high_open_high_close_with_data_count),
            'high_open_high_close_day10_up_pct': safe_percentage(high_open_high_close_day10_up, high_open_high_close_with_data_count),
            'high_open_low_close_day3_up_pct': safe_percentage(high_open_low_close_day3_up, high_open_low_close_with_data_count),
            'high_open_low_close_day5_up_pct': safe_percentage(high_open_low_close_day5_up, high_open_low_close_with_data_count),
            'high_open_low_close_day10_up_pct': safe_percentage(high_open_low_close_day10_up, high_open_low_close_with_data_count),
            'low_open_close_up_day3_up_pct': safe_percentage(low_open_close_up_day3_up, low_open_close_up_with_data_count),
            'low_open_close_up_day5_up_pct': safe_percentage(low_open_close_up_day5_up, low_open_close_up_with_data_count),
            'low_open_close_up_day10_up_pct': safe_percentage(low_open_close_up_day10_up, low_open_close_up_with_data_count),
            'low_open_low_close_day3_up_pct': safe_percentage(low_open_low_close_day3_up, low_open_low_close_with_data_count),
            'low_open_low_close_day5_up_pct': safe_percentage(low_open_low_close_day5_up, low_open_low_close_with_data_count),
            'low_open_low_close_day10_up_pct': safe_percentage(low_open_low_close_day10_up, low_open_low_close_with_data_count)
        }
    
    def filter_high_open_flat_signals(self, signals: List[Dict[str, Any]], 
                                     open_threshold: float = 4.5) -> Tuple[List[Dict[str, Any]], int]:
        """
        过滤掉次日开盘涨幅>4.5%且次日开盘价和收盘价一致的信号
        
        Args:
            signals: 原始信号列表
            open_threshold: 开盘涨幅阈值，默认4.5%
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: (过滤后的信号列表, 被过滤掉的信号数量)
        """
        if not signals:
            return signals, 0
        
        filtered_signals = []
        filtered_count = 0
        
        for signal in signals:
            # 获取次日开盘涨幅
            next_open_change_pct = signal.get('next_open_change_pct')
            next_open = signal.get('next_open')
            next_close = signal.get('next_day_close')
            
            # 如果没有次日数据，保留信号
            if next_open_change_pct is None or next_open is None or next_close is None:
                filtered_signals.append(signal)
                continue
            
            # 检查是否满足过滤条件：次日开盘涨幅>4.5% 且 次日开盘价=收盘价
            high_open = next_open_change_pct > open_threshold
            flat_trading = abs(next_open - next_close) < 0.001  # 考虑浮点数精度，使用小的阈值
            
            # 如果满足过滤条件，则剔除该信号
            if high_open and flat_trading:
                filtered_count += 1
                self.logger.info(f"过滤信号: {signal.get('stock_code', 'N/A')} {signal.get('date', 'N/A')} "
                               f"次日开盘涨幅: {next_open_change_pct:.2f}% "
                               f"次日开盘价: {next_open:.4f} 收盘价: {next_close:.4f}")
            else:
                filtered_signals.append(signal)
        
        self.logger.info(f"信号过滤完成: 原始信号数 {len(signals)}, 过滤后信号数 {len(filtered_signals)}, "
                        f"被过滤信号数 {filtered_count}")
        
        return filtered_signals, filtered_count
    
    def calculate_portfolio_performance(self, signals: List[Dict[str, Any]], 
                                      initial_capital: float = 100000,
                                      position_size: float = 0.1) -> Dict[str, Any]:
        """
        计算投资组合表现
        
        Args:
            signals: 信号列表
            initial_capital: 初始资金
            position_size: 每次投资占总资金的比例
            
        Returns:
            Dict[str, Any]: 投资组合表现
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 转换为DataFrame并按日期排序
        df = pd.DataFrame(signals)
        if 'next_day_return' not in df.columns:
            return {"error": "缺少收益率数据"}
        
        df = df.dropna(subset=['next_day_return'])
        if df.empty:
            return {"error": "没有有效的收益率数据"}
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 计算投资组合表现
        capital = initial_capital
        portfolio_values = [capital]
        returns = []
        
        for _, row in df.iterrows():
            # 每次投资固定金额，而不是按比例投资
            investment_amount = min(capital * position_size, capital)  # 确保不超过现有资金
            
            if investment_amount <= 0:  # 如果资金不足，跳过这次投资
                returns.append(0)
                portfolio_values.append(capital)
                continue
                
            return_rate = row['next_day_return'] / 100  # 转换为小数
            profit = investment_amount * return_rate
            
            # 更新资金：原资金 - 投资金额 + 投资收益
            capital = capital - investment_amount + investment_amount * (1 + return_rate)
            
            portfolio_values.append(capital)
            returns.append(return_rate)
        
        # 计算性能指标
        total_return = (capital - initial_capital) / initial_capital
        num_trades = len(returns)
        
        if num_trades > 0:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            win_rate = sum(1 for r in returns if r > 0) / num_trades
            
            # 计算最大回撤
            portfolio_series = pd.Series(portfolio_values)
            running_max = portfolio_series.expanding().max()
            drawdown = (portfolio_series - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # 计算夏普比率（假设无风险利率为0）
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
            
            return {
                'initial_capital': initial_capital,
                'final_capital': capital,
                'total_return': total_return,
                'total_return_pct': total_return * 100,
                'num_trades': num_trades,
                'avg_return_per_trade': avg_return,
                'avg_return_per_trade_pct': avg_return * 100,
                'win_rate': win_rate,
                'win_rate_pct': win_rate * 100,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown * 100,
                'sharpe_ratio': sharpe_ratio,
                'volatility': std_return,
                'portfolio_values': portfolio_values,
                'dates': ['Initial'] + df['date'].dt.strftime('%Y-%m-%d').tolist()
            }
        else:
            return {"error": "没有有效的交易数据"}
    
    def generate_performance_report(self, signals: List[Dict[str, Any]], 
                                  output_file: str = None) -> str:
        """
        生成性能报告
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
            
        Returns:
            str: 报告内容
        """
        # 分析信号
        analysis = self.analyze_signals(signals)
        
        # 计算投资组合表现
        portfolio_perf = self.calculate_portfolio_performance(signals)
        
        # 生成报告
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("回测结果分析报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 基本统计
        if 'basic_stats' in analysis:
            stats = analysis['basic_stats']
            report_lines.append("基本统计:")
            report_lines.append(f"  总信号数量: {stats.get('total_signals', 0)}")
            report_lines.append(f"  涉及股票数量: {stats.get('unique_stocks', 0)}")
            report_lines.append("")
        
        # 收益率分析
        if 'returns_analysis' in analysis and analysis['returns_analysis']:
            returns = analysis['returns_analysis']
            report_lines.append("收益率分析:")
            report_lines.append(f"  有效收益率数量: {returns.get('total_valid_returns', 0)}")
            report_lines.append(f"  平均收益率: {returns.get('mean_return', 0):.4f}%")
            report_lines.append(f"  中位数收益率: {returns.get('median_return', 0):.4f}%")
            report_lines.append(f"  收益率标准差: {returns.get('std_return', 0):.4f}%")
            report_lines.append(f"  最小收益率: {returns.get('min_return', 0):.4f}%")
            report_lines.append(f"  最大收益率: {returns.get('max_return', 0):.4f}%")
            report_lines.append(f"  正收益比例: {returns.get('positive_return_ratio', 0):.2%}")
            report_lines.append(f"  负收益比例: {returns.get('negative_return_ratio', 0):.2%}")
            report_lines.append("")
        
        # 投资组合表现
        if 'error' not in portfolio_perf:
            report_lines.append("投资组合表现:")
            report_lines.append(f"  初始资金: ¥{portfolio_perf.get('initial_capital', 0):,.2f}")
            report_lines.append(f"  最终资金: ¥{portfolio_perf.get('final_capital', 0):,.2f}")
            report_lines.append(f"  总收益率: {portfolio_perf.get('total_return_pct', 0):.2f}%")
            report_lines.append(f"  交易次数: {portfolio_perf.get('num_trades', 0)}")
            report_lines.append(f"  平均每笔收益: {portfolio_perf.get('avg_return_per_trade_pct', 0):.4f}%")
            report_lines.append(f"  胜率: {portfolio_perf.get('win_rate_pct', 0):.2f}%")
            report_lines.append(f"  最大回撤: {portfolio_perf.get('max_drawdown_pct', 0):.2f}%")
            report_lines.append(f"  夏普比率: {portfolio_perf.get('sharpe_ratio', 0):.4f}")
            report_lines.append(f"  波动率: {portfolio_perf.get('volatility', 0):.4f}")
            report_lines.append("")
        
        # 时间分布
        if 'time_analysis' in analysis and analysis['time_analysis']:
            time_info = analysis['time_analysis']
            if 'date_range' in time_info:
                date_range = time_info['date_range']
                report_lines.append("时间分布:")
                report_lines.append(f"  时间范围: {date_range.get('start_date')} 至 {date_range.get('end_date')}")
                report_lines.append("")
        
        # 股票分布
        if 'stock_analysis' in analysis and analysis['stock_analysis']:
            stock_info = analysis['stock_analysis']
            if 'top_10_stocks' in stock_info:
                report_lines.append("热门股票 (前10):")
                for stock, count in stock_info['top_10_stocks'].items():
                    report_lines.append(f"  {stock}: {count} 次信号")
                report_lines.append("")
        
        # 详细关键比例统计信息
        detailed_stats = self.calculate_detailed_statistics(signals)
        if detailed_stats:
            report_lines.append("关键比例统计:")
            
            # 基本统计
            report_lines.append(f"总交易天数: {detailed_stats['total_count']}")
            report_lines.append(f"涉及股票数量: {detailed_stats['unique_stocks']}")
            
            # 次日表现关键比例
            report_lines.append("\n次日表现关键比例:")
            report_lines.append(f"  高开: {detailed_stats['next_open_up_count']}/{detailed_stats['total_count']} = {detailed_stats['next_open_up_pct']:.2f}%")
            report_lines.append(f"  收盘上涨: {detailed_stats['next_close_up_count']}/{detailed_stats['total_count']} = {detailed_stats['next_close_up_pct']:.2f}%")
            report_lines.append(f"  高开高走: {detailed_stats['high_open_high_close_count']}/{detailed_stats['total_count']} = {detailed_stats['high_open_high_close_pct']:.2f}%")
            report_lines.append(f"  高开低走: {detailed_stats['high_open_low_close_count']}/{detailed_stats['total_count']} = {detailed_stats['high_open_low_close_pct']:.2f}%")
            report_lines.append(f"  低开高走: {detailed_stats['low_open_close_up_count']}/{detailed_stats['total_count']} = {detailed_stats['low_open_close_up_pct']:.2f}%")
            report_lines.append(f"  低开低走: {detailed_stats['low_open_low_close_count']}/{detailed_stats['total_count']} = {detailed_stats['low_open_low_close_pct']:.2f}%")
            
            # 中长期表现关键比例
            report_lines.append("\n中长期表现关键比例:")
            report_lines.append(f"  3日收盘上涨: {detailed_stats['day3_up_count']}/{detailed_stats['day3_total_count']} = {detailed_stats['day3_up_pct']:.2f}%")
            report_lines.append(f"  5日收盘上涨: {detailed_stats['day5_up_count']}/{detailed_stats['day5_total_count']} = {detailed_stats['day5_up_pct']:.2f}%")
            report_lines.append(f"  10日收盘上涨: {detailed_stats['day10_up_count']}/{detailed_stats['day10_total_count']} = {detailed_stats['day10_up_pct']:.2f}%")
            
            # 次日情况下的后续表现
            if detailed_stats['high_open_high_close_count'] > 0:
                report_lines.append("\n高开高走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['high_open_high_close_day3_up']}/{detailed_stats['high_open_high_close_with_data_count']} = {detailed_stats['high_open_high_close_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['high_open_high_close_day5_up']}/{detailed_stats['high_open_high_close_with_data_count']} = {detailed_stats['high_open_high_close_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['high_open_high_close_day10_up']}/{detailed_stats['high_open_high_close_with_data_count']} = {detailed_stats['high_open_high_close_day10_up_pct']:.2f}%")
            
            if detailed_stats['high_open_low_close_count'] > 0:
                report_lines.append("\n高开低走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['high_open_low_close_day3_up']}/{detailed_stats['high_open_low_close_with_data_count']} = {detailed_stats['high_open_low_close_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['high_open_low_close_day5_up']}/{detailed_stats['high_open_low_close_with_data_count']} = {detailed_stats['high_open_low_close_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['high_open_low_close_day10_up']}/{detailed_stats['high_open_low_close_with_data_count']} = {detailed_stats['high_open_low_close_day10_up_pct']:.2f}%")
            
            if detailed_stats['low_open_close_up_count'] > 0:
                report_lines.append("\n低开高走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['low_open_close_up_day3_up']}/{detailed_stats['low_open_close_up_with_data_count']} = {detailed_stats['low_open_close_up_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['low_open_close_up_day5_up']}/{detailed_stats['low_open_close_up_with_data_count']} = {detailed_stats['low_open_close_up_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['low_open_close_up_day10_up']}/{detailed_stats['low_open_close_up_with_data_count']} = {detailed_stats['low_open_close_up_day10_up_pct']:.2f}%")
            
            if detailed_stats['low_open_low_close_count'] > 0:
                report_lines.append("\n低开低走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['low_open_low_close_day3_up']}/{detailed_stats['low_open_low_close_with_data_count']} = {detailed_stats['low_open_low_close_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['low_open_low_close_day5_up']}/{detailed_stats['low_open_low_close_with_data_count']} = {detailed_stats['low_open_low_close_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['low_open_low_close_day10_up']}/{detailed_stats['low_open_low_close_with_data_count']} = {detailed_stats['low_open_low_close_day10_up_pct']:.2f}%")
            
            report_lines.append("")
        
        # 添加最近10条3日上涨和下跌数据
        if signals:
            # 转换为DataFrame以便处理
            df = pd.DataFrame(signals)
            
            # 筛选有效的3日涨跌幅数据
            if 'day3_change_pct' in df.columns:
                valid_day3_data = df[pd.notna(df['day3_change_pct'])]
                
                if len(valid_day3_data) > 0:
                    # 按日期排序，获取最近的数据
                    if 'date' in valid_day3_data.columns:
                        valid_day3_data = valid_day3_data.sort_values('date', ascending=False)
                    
                    # 最近10条3日上涨数据
                    day3_up_data = valid_day3_data[valid_day3_data['day3_change_pct'] > 0].head(10)
                    if len(day3_up_data) > 0:
                        report_lines.append("最近10条3日上涨数据:")
                        report_lines.append(f"{'股票代码':<10} {'日期':<12} {'收盘价':<10} {'3日涨跌幅':<12} {'3日后价格':<12}")
                        report_lines.append("-" * 60)
                        for _, row in day3_up_data.iterrows():
                            stock_code = row.get('stock_code', 'N/A')
                            date = row.get('date', 'N/A')
                            close_price = f"{row.get('close', 0):.2f}" if pd.notna(row.get('close')) else 'N/A'
                            day3_change = f"{row['day3_change_pct']:.2f}%"
                            day3_close = f"{row.get('day3_close', 0):.2f}" if pd.notna(row.get('day3_close')) else 'N/A'
                            report_lines.append(f"{stock_code:<10} {date:<12} {close_price:<10} {day3_change:<12} {day3_close:<12}")
                        report_lines.append("")
                    
                    # 最近10条3日下跌数据
                    day3_down_data = valid_day3_data[valid_day3_data['day3_change_pct'] < 0].head(10)
                    if len(day3_down_data) > 0:
                        report_lines.append("最近10条3日下跌数据:")
                        report_lines.append(f"{'股票代码':<10} {'日期':<12} {'收盘价':<10} {'3日涨跌幅':<12} {'3日后价格':<12}")
                        report_lines.append("-" * 60)
                        for _, row in day3_down_data.iterrows():
                            stock_code = row.get('stock_code', 'N/A')
                            date = row.get('date', 'N/A')
                            close_price = f"{row.get('close', 0):.2f}" if pd.notna(row.get('close')) else 'N/A'
                            day3_change = f"{row['day3_change_pct']:.2f}%"
                            day3_close = f"{row.get('day3_close', 0):.2f}" if pd.notna(row.get('day3_close')) else 'N/A'
                            report_lines.append(f"{stock_code:<10} {date:<12} {close_price:<10} {day3_change:<12} {day3_close:<12}")
                        report_lines.append("")
        
        report_lines.append("=" * 60)
        
        report_content = "\n".join(report_lines)
        
        # 保存到文件
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                self.logger.info(f"报告已保存到: {output_file}")
            except Exception as e:
                self.logger.error(f"保存报告失败: {e}")
        
        return report_content
    
    def write_backtest_result_to_file(self, signals: List[Dict[str, Any]], 
                                     strategy_description: str = None, output_dir: str = None):
        """
        将回测结果以增量方式写入final_result文件
        
        Args:
            signals: 信号列表
            strategy_description: 策略描述
            output_dir: 输出目录
        """
        try:
            # 获取当前时间戳
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 使用现有的calculate_detailed_statistics方法计算统计数据
            stats = self.calculate_detailed_statistics(signals)
            
            # 构建统计信息
            statistics_info = f"""
统计信息:
总共符合条件的交易日数: {stats.get('total_count', 0)}
涉及股票数: {stats.get('unique_stocks', 0)}
关键比例统计:
次日表现:
  次日高开比例: {stats.get('next_open_up_count', 0)}/{stats.get('total_count', 0)} ({stats.get('next_open_up_pct', 0):.2f}%)
  次日收盘上涨比例: {stats.get('next_close_up_count', 0)}/{stats.get('total_count', 0)} ({stats.get('next_close_up_pct', 0):.2f}%)
  次日高开高走比例: {stats.get('high_open_high_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('high_open_high_close_pct', 0):.2f}%)
  次日低开收盘上涨比例: {stats.get('low_open_close_up_count', 0)}/{stats.get('total_count', 0)} ({stats.get('low_open_close_up_pct', 0):.2f}%)
  次日低开低走比例: {stats.get('low_open_low_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('low_open_low_close_pct', 0):.2f}%)
中长期表现:
  3日收盘上涨比例: {stats.get('day3_up_count', 0)}/{stats.get('day3_total_count', 0)} ({stats.get('day3_up_pct', 0):.2f}%)
  5日收盘上涨比例: {stats.get('day5_up_count', 0)}/{stats.get('day5_total_count', 0)} ({stats.get('day5_up_pct', 0):.2f}%)
  10日收盘上涨比例: {stats.get('day10_up_count', 0)}/{stats.get('day10_total_count', 0)} ({stats.get('day10_up_pct', 0):.2f}%)

次日高开高走股票中的后续表现:
3日收盘上涨比例: {stats.get('high_open_high_close_day3_up', 0)}/{stats.get('high_open_high_close_with_data_count', 0)} ({stats.get('high_open_high_close_day3_up_pct', 0):.2f}%)
5日收盘上涨比例: {stats.get('high_open_high_close_day5_up', 0)}/{stats.get('high_open_high_close_with_data_count', 0)} ({stats.get('high_open_high_close_day5_up_pct', 0):.2f}%)
10日收盘上涨比例: {stats.get('high_open_high_close_day10_up', 0)}/{stats.get('high_open_high_close_with_data_count', 0)} ({stats.get('high_open_high_close_day10_up_pct', 0):.2f}%)

次日低开收盘上涨股票中的后续表现:
3日收盘上涨比例: {stats.get('low_open_close_up_day3_up', 0)}/{stats.get('low_open_close_up_with_data_count', 0)} ({stats.get('low_open_close_up_day3_up_pct', 0):.2f}%)
5日收盘上涨比例: {stats.get('low_open_close_up_day5_up', 0)}/{stats.get('low_open_close_up_with_data_count', 0)} ({stats.get('low_open_close_up_day5_up_pct', 0):.2f}%)
10日收盘上涨比例: {stats.get('low_open_close_up_day10_up', 0)}/{stats.get('low_open_close_up_with_data_count', 0)} ({stats.get('low_open_close_up_day10_up_pct', 0):.2f}%)

次日低开低走股票中的后续表现:
3日收盘上涨比例: {stats.get('low_open_low_close_day3_up', 0)}/{stats.get('low_open_low_close_with_data_count', 0)} ({stats.get('low_open_low_close_day3_up_pct', 0):.2f}%)
5日收盘上涨比例: {stats.get('low_open_low_close_day5_up', 0)}/{stats.get('low_open_low_close_with_data_count', 0)} ({stats.get('low_open_low_close_day5_up_pct', 0):.2f}%)
10日收盘上涨比例: {stats.get('low_open_low_close_day10_up', 0)}/{stats.get('low_open_low_close_with_data_count', 0)} ({stats.get('low_open_low_close_day10_up_pct', 0):.2f}%)"""
            
            # 构建完整的回测记录
            backtest_record = f"""
{'='*80}
回测时间: {current_time}
{strategy_description or "策略描述未提供"}

{statistics_info}
{'='*80}

"""
            
            # 确定final_result文件路径
            if output_dir:
                final_result_path = os.path.join(output_dir, "final_result")
            else:
                # 默认使用当前目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                final_result_path = os.path.join(current_dir, "final_result")
            
            # 以追加模式写入文件，确保使用UTF-8编码（不使用BOM）
            with open(final_result_path, 'a', encoding='utf-8') as f:
                f.write(backtest_record)
            
            self.logger.info(f"回测结果已追加写入: {final_result_path}")
            
        except Exception as e:
            self.logger.error(f"写入final_result文件失败: {e}")


class ResultExporter:
    """结果导出器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def export_to_csv(self, signals: List[Dict[str, Any]], output_file: str, 
                     include_analysis: bool = True):
        """
        导出结果到CSV文件
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
            include_analysis: 是否包含分析结果
        """
        try:
            if not signals:
                self.logger.warning("没有信号数据可导出")
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(signals)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 导出主要数据
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"信号数据已导出到: {output_file}")
            
            # 如果需要，导出分析结果
            if include_analysis:
                analyzer = ResultAnalyzer()
                analysis = analyzer.analyze_signals(signals)
                
                # 保存分析结果到JSON文件
                analysis_file = output_file.replace('.csv', '_analysis.json')
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
                self.logger.info(f"分析结果已导出到: {analysis_file}")
                
                # 生成文本报告
                report_file = output_file.replace('.csv', '_report.txt')
                report_content = analyzer.generate_performance_report(signals, report_file)
                
        except Exception as e:
            self.logger.error(f"导出CSV文件失败: {e}")
    
    def export_to_excel(self, signals: List[Dict[str, Any]], output_file: str):
        """
        导出结果到Excel文件
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
        """
        try:
            if not signals:
                self.logger.warning("没有信号数据可导出")
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(signals)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 创建Excel写入器
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 写入主要数据
                df.to_excel(writer, sheet_name='信号数据', index=False)
                
                # 分析结果
                analyzer = ResultAnalyzer()
                analysis = analyzer.analyze_signals(signals)
                
                # 基本统计
                if 'basic_stats' in analysis:
                    stats_df = pd.DataFrame([analysis['basic_stats']])
                    stats_df.to_excel(writer, sheet_name='基本统计', index=False)
                
                # 收益率分析
                if 'returns_analysis' in analysis and analysis['returns_analysis']:
                    returns_df = pd.DataFrame([analysis['returns_analysis']])
                    returns_df.to_excel(writer, sheet_name='收益率分析', index=False)
                
                # 投资组合表现
                portfolio_perf = analyzer.calculate_portfolio_performance(signals)
                if 'error' not in portfolio_perf:
                    portfolio_df = pd.DataFrame([{k: v for k, v in portfolio_perf.items() 
                                                if k not in ['portfolio_values', 'dates']}])
                    portfolio_df.to_excel(writer, sheet_name='投资组合表现', index=False)
            
            self.logger.info(f"Excel文件已导出到: {output_file}")
            
        except Exception as e:
            self.logger.error(f"导出Excel文件失败: {e}")
    
    def export_summary_statistics(self, signals: List[Dict[str, Any]], output_dir: str):
        """
        导出汇总统计信息
        
        Args:
            signals: 信号列表
            output_dir: 输出目录
        """
        try:
            if not signals:
                self.logger.warning("没有信号数据可导出")
                return
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 分析结果
            analyzer = ResultAnalyzer()
            analysis = analyzer.analyze_signals(signals)
            portfolio_perf = analyzer.calculate_portfolio_performance(signals)
            
            # 导出各种统计信息
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 1. 完整分析结果 (JSON)
            analysis_file = os.path.join(output_dir, f'analysis_{timestamp}.json')
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'signal_analysis': analysis,
                    'portfolio_performance': portfolio_perf
                }, f, ensure_ascii=False, indent=2, default=str)
            
            # 2. 文本报告
            report_file = os.path.join(output_dir, f'report_{timestamp}.txt')
            analyzer.generate_performance_report(signals, report_file)
            
            # 3. 信号数据CSV
            csv_file = os.path.join(output_dir, f'signals_{timestamp}.csv')
            df = pd.DataFrame(signals)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"汇总统计信息已导出到目录: {output_dir}")
            
        except Exception as e:
            self.logger.error(f"导出汇总统计信息失败: {e}")


class ResultFormatter:
    """结果格式化器"""
    
    @staticmethod
    def format_signal_for_display(signal: Dict[str, Any]) -> str:
        """
        格式化单个信号用于显示
        
        Args:
            signal: 信号字典
            
        Returns:
            str: 格式化后的字符串
        """
        stock_code = signal.get('stock_code', 'N/A')
        date = signal.get('date', 'N/A')
        close_price = signal.get('close', 0)
        next_return = signal.get('next_day_return', None)
        
        if next_return is not None:
            return f"{stock_code} | {date} | 收盘价: {close_price:.4f} | 次日收益: {next_return:.2f}%"
        else:
            return f"{stock_code} | {date} | 收盘价: {close_price:.4f} | 次日收益: N/A"
    
    @staticmethod
    def format_signals_table(signals: List[Dict[str, Any]], max_rows: int = 20) -> str:
        """
        格式化信号列表为表格
        
        Args:
            signals: 信号列表
            max_rows: 最大显示行数
            
        Returns:
            str: 格式化后的表格字符串
        """
        if not signals:
            return "没有信号数据"
        
        # 转换为DataFrame
        df = pd.DataFrame(signals)
        
        # 选择要显示的列
        display_columns = ['stock_code', 'date', 'close']
        if 'next_day_return' in df.columns:
            display_columns.append('next_day_return')
        
        # 过滤列
        display_df = df[display_columns].copy()
        
        # 限制行数
        if len(display_df) > max_rows:
            display_df = display_df.head(max_rows)
        
        # 格式化数值
        if 'close' in display_df.columns:
            display_df['close'] = display_df['close'].apply(lambda x: f"{x:.4f}")
        if 'next_day_return' in display_df.columns:
            display_df['next_day_return'] = display_df['next_day_return'].apply(
                lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
            )
        
        # 重命名列
        column_names = {
            'stock_code': '股票代码',
            'date': '日期',
            'close': '收盘价',
            'next_day_return': '次日收益'
        }
        display_df = display_df.rename(columns=column_names)
        
        return display_df.to_string(index=False)
    
    @staticmethod
    def format_performance_summary(portfolio_perf: Dict[str, Any]) -> str:
        """
        格式化投资组合表现摘要
        
        Args:
            portfolio_perf: 投资组合表现字典
            
        Returns:
            str: 格式化后的摘要字符串
        """
        if 'error' in portfolio_perf:
            return f"无法计算投资组合表现: {portfolio_perf['error']}"
        
        lines = []
        lines.append("投资组合表现摘要:")
        lines.append(f"  总收益率: {portfolio_perf.get('total_return_pct', 0):.2f}%")
        lines.append(f"  交易次数: {portfolio_perf.get('num_trades', 0)}")
        lines.append(f"  胜率: {portfolio_perf.get('win_rate_pct', 0):.2f}%")
        lines.append(f"  最大回撤: {portfolio_perf.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"  夏普比率: {portfolio_perf.get('sharpe_ratio', 0):.4f}")
        
        return "\n".join(lines)