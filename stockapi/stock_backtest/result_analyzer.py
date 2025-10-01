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
        # 转换为DataFrame便于计算
        if isinstance(signals, pd.DataFrame):
            df = signals
        else:
            if not signals:
                return {}
            df = pd.DataFrame(signals)
        
        if df.empty:
            return {}
        
        # 基本统计
        total_count = len(df)
        unique_stocks = df['stock_code'].nunique() if 'stock_code' in df.columns else 0
        
        # 次日表现统计
        next_open_up_count = len(df[df.get('next_open_change_pct', 0) > 0]) if 'next_open_change_pct' in df.columns else 0
        next_close_up_count = len(df[df.get('next_close_change_pct', 0) > 0]) if 'next_close_change_pct' in df.columns else 0
        
        # 开盘收盘组合统计
        high_open_high_close_count = 0  # 高开高走 (次日开盘上涨且收盘高于开盘)
        high_open_low_close_count = 0   # 高开低走 (次日开盘上涨且收盘低于开盘)
        high_open_flat_close_count = 0  # 高开平走 (次日开盘上涨且收盘等于开盘)
        low_open_close_up_count = 0     # 低开高走 (次日开盘下跌且收盘高于开盘)
        low_open_low_close_count = 0    # 低开低走 (次日开盘下跌且收盘低于开盘)
        low_open_flat_close_count = 0   # 低开平走 (次日开盘下跌且收盘等于开盘)
        flat_open_close_up_count = 0    # 平开高走 (次日开盘平盘且收盘上涨)
        flat_open_close_down_count = 0  # 平开低走 (次日开盘平盘且收盘下跌)
        flat_open_flat_close_count = 0  # 平开平走 (次日开盘平盘且收盘平盘)
        
        if 'next_open_change_pct' in df.columns and 'next_intraday_change_pct' in df.columns:
            high_open_high_close_count = len(df[(df['next_open_change_pct'] > 0) & (df['next_intraday_change_pct'] > 0)])
            high_open_low_close_count = len(df[(df['next_open_change_pct'] > 0) & (df['next_intraday_change_pct'] < 0)])
            high_open_flat_close_count = len(df[(df['next_open_change_pct'] > 0) & (df['next_intraday_change_pct'] == 0)])
            low_open_close_up_count = len(df[(df['next_open_change_pct'] < 0) & (df['next_intraday_change_pct'] > 0)])
            low_open_low_close_count = len(df[(df['next_open_change_pct'] < 0) & (df['next_intraday_change_pct'] < 0)])
            low_open_flat_close_count = len(df[(df['next_open_change_pct'] < 0) & (df['next_intraday_change_pct'] == 0)])
            flat_open_close_up_count = len(df[(df['next_open_change_pct'] == 0) & (df['next_intraday_change_pct'] > 0)])
            flat_open_close_down_count = len(df[(df['next_open_change_pct'] == 0) & (df['next_intraday_change_pct'] < 0)])
            flat_open_flat_close_count = len(df[(df['next_open_change_pct'] == 0) & (df['next_intraday_change_pct'] == 0)])
        
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
        
        # 计算高开平走股票的后续表现
        high_open_flat_close_day3_up = 0
        high_open_flat_close_day5_up = 0
        high_open_flat_close_day10_up = 0
        
        if high_open_flat_close_count > 0:
            high_open_flat_close_signals = df[(df.get('next_open_change_pct', 0) > 0) & (df.get('next_intraday_change_pct', 0) == 0)]
            if 'day3_from_next_change_pct' in df.columns:
                high_open_flat_close_day3_up = len(high_open_flat_close_signals[(high_open_flat_close_signals['day3_from_next_change_pct'] > 0) & pd.notna(high_open_flat_close_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                high_open_flat_close_day5_up = len(high_open_flat_close_signals[(high_open_flat_close_signals['day5_from_next_change_pct'] > 0) & pd.notna(high_open_flat_close_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                high_open_flat_close_day10_up = len(high_open_flat_close_signals[(high_open_flat_close_signals['day10_from_next_change_pct'] > 0) & pd.notna(high_open_flat_close_signals['day10_from_next_change_pct'])])
        
        # 计算低开平走股票的后续表现
        low_open_flat_close_day3_up = 0
        low_open_flat_close_day5_up = 0
        low_open_flat_close_day10_up = 0
        
        if low_open_flat_close_count > 0:
            low_open_flat_close_signals = df[(df.get('next_open_change_pct', 0) < 0) & (df.get('next_intraday_change_pct', 0) == 0)]
            if 'day3_from_next_change_pct' in df.columns:
                low_open_flat_close_day3_up = len(low_open_flat_close_signals[(low_open_flat_close_signals['day3_from_next_change_pct'] > 0) & pd.notna(low_open_flat_close_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                low_open_flat_close_day5_up = len(low_open_flat_close_signals[(low_open_flat_close_signals['day5_from_next_change_pct'] > 0) & pd.notna(low_open_flat_close_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                low_open_flat_close_day10_up = len(low_open_flat_close_signals[(low_open_flat_close_signals['day10_from_next_change_pct'] > 0) & pd.notna(low_open_flat_close_signals['day10_from_next_change_pct'])])
        
        # 计算平开高走股票的后续表现
        flat_open_close_up_day3_up = 0
        flat_open_close_up_day5_up = 0
        flat_open_close_up_day10_up = 0
        
        if flat_open_close_up_count > 0:
            flat_open_close_up_signals = df[(df.get('next_open_change_pct', 0) == 0) & (df.get('next_intraday_change_pct', 0) > 0)]
            if 'day3_from_next_change_pct' in df.columns:
                flat_open_close_up_day3_up = len(flat_open_close_up_signals[(flat_open_close_up_signals['day3_from_next_change_pct'] > 0) & pd.notna(flat_open_close_up_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                flat_open_close_up_day5_up = len(flat_open_close_up_signals[(flat_open_close_up_signals['day5_from_next_change_pct'] > 0) & pd.notna(flat_open_close_up_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                flat_open_close_up_day10_up = len(flat_open_close_up_signals[(flat_open_close_up_signals['day10_from_next_change_pct'] > 0) & pd.notna(flat_open_close_up_signals['day10_from_next_change_pct'])])
        
        # 计算平开低走股票的后续表现
        flat_open_close_down_day3_up = 0
        flat_open_close_down_day5_up = 0
        flat_open_close_down_day10_up = 0
        
        if flat_open_close_down_count > 0:
            flat_open_close_down_signals = df[(df.get('next_open_change_pct', 0) == 0) & (df.get('next_intraday_change_pct', 0) < 0)]
            if 'day3_from_next_change_pct' in df.columns:
                flat_open_close_down_day3_up = len(flat_open_close_down_signals[(flat_open_close_down_signals['day3_from_next_change_pct'] > 0) & pd.notna(flat_open_close_down_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                flat_open_close_down_day5_up = len(flat_open_close_down_signals[(flat_open_close_down_signals['day5_from_next_change_pct'] > 0) & pd.notna(flat_open_close_down_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                flat_open_close_down_day10_up = len(flat_open_close_down_signals[(flat_open_close_down_signals['day10_from_next_change_pct'] > 0) & pd.notna(flat_open_close_down_signals['day10_from_next_change_pct'])])
        
        # 计算平开平走股票的后续表现
        flat_open_flat_close_day3_up = 0
        flat_open_flat_close_day5_up = 0
        flat_open_flat_close_day10_up = 0
        
        if flat_open_flat_close_count > 0:
            flat_open_flat_close_signals = df[(df.get('next_open_change_pct', 0) == 0) & (df.get('next_intraday_change_pct', 0) == 0)]
            if 'day3_from_next_change_pct' in df.columns:
                flat_open_flat_close_day3_up = len(flat_open_flat_close_signals[(flat_open_flat_close_signals['day3_from_next_change_pct'] > 0) & pd.notna(flat_open_flat_close_signals['day3_from_next_change_pct'])])
            if 'day5_from_next_change_pct' in df.columns:
                flat_open_flat_close_day5_up = len(flat_open_flat_close_signals[(flat_open_flat_close_signals['day5_from_next_change_pct'] > 0) & pd.notna(flat_open_flat_close_signals['day5_from_next_change_pct'])])
            if 'day10_from_next_change_pct' in df.columns:
                flat_open_flat_close_day10_up = len(flat_open_flat_close_signals[(flat_open_flat_close_signals['day10_from_next_change_pct'] > 0) & pd.notna(flat_open_flat_close_signals['day10_from_next_change_pct'])])
        
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
        high_open_flat_close_with_data_count = len(df[(df.get('next_open_change_pct', 0) > 0) & (df.get('next_intraday_change_pct', 0) == 0) & 
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
        low_open_flat_close_with_data_count = len(df[(df.get('next_open_change_pct', 0) < 0) & (df.get('next_intraday_change_pct', 0) == 0) & 
                                                    pd.notna(df.get('day3_from_next_change_pct')) & 
                                                    pd.notna(df.get('day5_from_next_change_pct')) & 
                                                    pd.notna(df.get('day10_from_next_change_pct'))])
        flat_open_close_up_with_data_count = len(df[(df.get('next_open_change_pct', 0) == 0) & (df.get('next_intraday_change_pct', 0) > 0) & 
                                                   pd.notna(df.get('day3_from_next_change_pct')) & 
                                                   pd.notna(df.get('day5_from_next_change_pct')) & 
                                                   pd.notna(df.get('day10_from_next_change_pct'))])
        flat_open_close_down_with_data_count = len(df[(df.get('next_open_change_pct', 0) == 0) & (df.get('next_intraday_change_pct', 0) < 0) & 
                                                     pd.notna(df.get('day3_from_next_change_pct')) & 
                                                     pd.notna(df.get('day5_from_next_change_pct')) & 
                                                     pd.notna(df.get('day10_from_next_change_pct'))])
        flat_open_flat_close_with_data_count = len(df[(df.get('next_open_change_pct', 0) == 0) & (df.get('next_intraday_change_pct', 0) == 0) & 
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
            'high_open_flat_close_count': high_open_flat_close_count,
            'low_open_close_up_count': low_open_close_up_count,
            'low_open_low_close_count': low_open_low_close_count,
            'low_open_flat_close_count': low_open_flat_close_count,
            'flat_open_close_up_count': flat_open_close_up_count,
            'flat_open_close_down_count': flat_open_close_down_count,
            'flat_open_flat_close_count': flat_open_flat_close_count,
            'high_open_high_close_with_data_count': high_open_high_close_with_data_count,
            'high_open_low_close_with_data_count': high_open_low_close_with_data_count,
            'high_open_flat_close_with_data_count': high_open_flat_close_with_data_count,
            'low_open_close_up_with_data_count': low_open_close_up_with_data_count,
            'low_open_low_close_with_data_count': low_open_low_close_with_data_count,
            'low_open_flat_close_with_data_count': low_open_flat_close_with_data_count,
            'flat_open_close_up_with_data_count': flat_open_close_up_with_data_count,
            'flat_open_close_down_with_data_count': flat_open_close_down_with_data_count,
            'flat_open_flat_close_with_data_count': flat_open_flat_close_with_data_count,
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
            'high_open_flat_close_day3_up': high_open_flat_close_day3_up,
            'high_open_flat_close_day5_up': high_open_flat_close_day5_up,
            'high_open_flat_close_day10_up': high_open_flat_close_day10_up,
            'low_open_flat_close_day3_up': low_open_flat_close_day3_up,
            'low_open_flat_close_day5_up': low_open_flat_close_day5_up,
            'low_open_flat_close_day10_up': low_open_flat_close_day10_up,
            'flat_open_close_up_day3_up': flat_open_close_up_day3_up,
            'flat_open_close_up_day5_up': flat_open_close_up_day5_up,
            'flat_open_close_up_day10_up': flat_open_close_up_day10_up,
            'flat_open_close_down_day3_up': flat_open_close_down_day3_up,
            'flat_open_close_down_day5_up': flat_open_close_down_day5_up,
            'flat_open_close_down_day10_up': flat_open_close_down_day10_up,
            'flat_open_flat_close_day3_up': flat_open_flat_close_day3_up,
            'flat_open_flat_close_day5_up': flat_open_flat_close_day5_up,
            'flat_open_flat_close_day10_up': flat_open_flat_close_day10_up,
            'next_open_up_pct': safe_percentage(next_open_up_count, total_count),
            'next_close_up_pct': safe_percentage(next_close_up_count, total_count),
            'high_open_high_close_pct': safe_percentage(high_open_high_close_count, total_count),
            'high_open_low_close_pct': safe_percentage(high_open_low_close_count, total_count),
            'high_open_flat_close_pct': safe_percentage(high_open_flat_close_count, total_count),
            'low_open_close_up_pct': safe_percentage(low_open_close_up_count, total_count),
            'low_open_low_close_pct': safe_percentage(low_open_low_close_count, total_count),
            'low_open_flat_close_pct': safe_percentage(low_open_flat_close_count, total_count),
            'flat_open_close_up_pct': safe_percentage(flat_open_close_up_count, total_count),
            'flat_open_close_down_pct': safe_percentage(flat_open_close_down_count, total_count),
            'flat_open_flat_close_pct': safe_percentage(flat_open_flat_close_count, total_count),
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
            'low_open_low_close_day10_up_pct': safe_percentage(low_open_low_close_day10_up, low_open_low_close_with_data_count),
            'high_open_flat_close_day3_up_pct': safe_percentage(high_open_flat_close_day3_up, high_open_flat_close_with_data_count),
            'high_open_flat_close_day5_up_pct': safe_percentage(high_open_flat_close_day5_up, high_open_flat_close_with_data_count),
            'high_open_flat_close_day10_up_pct': safe_percentage(high_open_flat_close_day10_up, high_open_flat_close_with_data_count),
            'low_open_flat_close_day3_up_pct': safe_percentage(low_open_flat_close_day3_up, low_open_flat_close_with_data_count),
            'low_open_flat_close_day5_up_pct': safe_percentage(low_open_flat_close_day5_up, low_open_flat_close_with_data_count),
            'low_open_flat_close_day10_up_pct': safe_percentage(low_open_flat_close_day10_up, low_open_flat_close_with_data_count),
            'flat_open_close_up_day3_up_pct': safe_percentage(flat_open_close_up_day3_up, flat_open_close_up_with_data_count),
            'flat_open_close_up_day5_up_pct': safe_percentage(flat_open_close_up_day5_up, flat_open_close_up_with_data_count),
            'flat_open_close_up_day10_up_pct': safe_percentage(flat_open_close_up_day10_up, flat_open_close_up_with_data_count),
            'flat_open_close_down_day3_up_pct': safe_percentage(flat_open_close_down_day3_up, flat_open_close_down_with_data_count),
            'flat_open_close_down_day5_up_pct': safe_percentage(flat_open_close_down_day5_up, flat_open_close_down_with_data_count),
            'flat_open_close_down_day10_up_pct': safe_percentage(flat_open_close_down_day10_up, flat_open_close_down_with_data_count),
            'flat_open_flat_close_day3_up_pct': safe_percentage(flat_open_flat_close_day3_up, flat_open_flat_close_with_data_count),
            'flat_open_flat_close_day5_up_pct': safe_percentage(flat_open_flat_close_day5_up, flat_open_flat_close_with_data_count),
            'flat_open_flat_close_day10_up_pct': safe_percentage(flat_open_flat_close_day10_up, flat_open_flat_close_with_data_count)
        }
    


    def select_daily_signals(self, signals: List[Dict[str, Any]], 
                           selection_strategy: str = 'lowest_return') -> List[Dict[str, Any]]:
        """
        处理同一天的多个信号，根据策略选择信号
        
        Args:
            signals: 信号列表
            selection_strategy: 选择策略
                - 'lowest_return': 选择收益率最低的信号
                - 'highest_return': 选择收益率最高的信号
                - 'first': 选择第一个信号
                - 'all': 保留所有信号（不过滤）
            
        Returns:
            List[Dict[str, Any]]: 过滤后的信号列表
        """
        if not signals or selection_strategy == 'all':
            return signals
        
        # 转换为DataFrame便于处理
        df = pd.DataFrame(signals)
        if 'date' not in df.columns or 'next_day_return' not in df.columns:
            return signals
        
        # 过滤掉没有收益率数据的信号
        df = df.dropna(subset=['next_day_return'])
        if df.empty:
            return []
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 按日期分组，每天只选择一个信号
        selected_signals = []
        
        for date, group in df.groupby(df['date'].dt.date):
            if len(group) == 1:
                # 如果该天只有一个信号，直接添加
                selected_signals.append(group.iloc[0].to_dict())
            else:
                # 如果该天有多个信号，根据策略选择
                if selection_strategy == 'lowest_return':
                    # 选择收益率最低的信号
                    selected_row = group.loc[group['next_day_return'].idxmin()]
                    self.logger.info(f"日期 {date}: 从 {len(group)} 个信号中选择收益率最低的 "
                                   f"({selected_row['stock_code']}: {selected_row['next_day_return']:.2f}%)")
                elif selection_strategy == 'highest_return':
                    # 选择收益率最高的信号
                    selected_row = group.loc[group['next_day_return'].idxmax()]
                    self.logger.info(f"日期 {date}: 从 {len(group)} 个信号中选择收益率最高的 "
                                   f"({selected_row['stock_code']}: {selected_row['next_day_return']:.2f}%)")
                elif selection_strategy == 'first':
                    # 选择第一个信号（按原始顺序）
                    selected_row = group.iloc[0]
                    self.logger.info(f"日期 {date}: 从 {len(group)} 个信号中选择第一个 "
                                   f"({selected_row['stock_code']}: {selected_row['next_day_return']:.2f}%)")
                else:
                    # 默认选择第一个
                    selected_row = group.iloc[0]
                
                selected_signals.append(selected_row.to_dict())
        
        self.logger.info(f"信号选择完成: 原始信号数 {len(signals)}, 选择后信号数 {len(selected_signals)}")
        return selected_signals

    def calculate_portfolio_performance(self, signals: List[Dict[str, Any]], 
                                      initial_capital: float = 100000,
                                      position_size: float = 1.0,
                                      daily_selection_strategy: str = 'lowest_return') -> Dict[str, Any]:
        """
        计算投资组合表现 - 满仓/空仓策略
        
        Args:
            signals: 信号列表
            initial_capital: 初始资金
            position_size: 每次投资占总资金的比例（默认1.0表示满仓）
            daily_selection_strategy: 同一天多信号选择策略
            
        Returns:
            Dict[str, Any]: 投资组合表现
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 先进行同一天信号选择
        selected_signals = self.select_daily_signals(signals, daily_selection_strategy)
        if not selected_signals:
            return {"error": "信号选择后没有有效数据"}
        
        # 转换为DataFrame并按日期排序
        df = pd.DataFrame(selected_signals)
        if 'next_day_return' not in df.columns:
            return {"error": "缺少收益率数据"}
        
        df = df.dropna(subset=['next_day_return'])
        if df.empty:
            return {"error": "没有有效的收益率数据"}
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 计算投资组合表现 - 满仓/空仓策略
        capital = initial_capital
        portfolio_values = [capital]
        returns = []
        
        for _, row in df.iterrows():
            if capital <= 0:  # 如果资金不足，跳过这次投资
                returns.append(0)
                portfolio_values.append(capital)
                continue
                
            return_rate = row['next_day_return'] / 100  # 转换为小数
            
            if position_size >= 1.0:
                # 满仓策略：资金直接按收益率变化
                capital = capital * (1 + return_rate)
            else:
                # 部分仓位策略：只投资部分资金
                investment_amount = capital * position_size
                profit = investment_amount * return_rate
                capital = capital + profit
            
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
    

    
    def calculate_yearly_returns(self, signals: List[Dict[str, Any]], 
                                initial_capital: float = 100000,
                                position_size: float = 1.0,
                                daily_selection_strategy: str = 'lowest_return') -> Dict[str, Any]:
        """
        计算各年度收益率统计 - 满仓/空仓策略
        
        Args:
            signals: 信号列表
            initial_capital: 初始资金
            position_size: 每次投资占总资金的比例（默认1.0表示满仓）
            daily_selection_strategy: 同一天多信号选择策略
            
        Returns:
            Dict[str, Any]: 年度收益率统计
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 先进行同一天信号选择
        selected_signals = self.select_daily_signals(signals, daily_selection_strategy)
        if not selected_signals:
            return {"error": "信号选择后没有有效数据"}
        
        # 转换为DataFrame
        df = pd.DataFrame(selected_signals)
        
        # 检查必要字段
        if 'date' not in df.columns or 'next_day_return' not in df.columns:
            return {"error": "缺少必要的日期或收益率字段"}
        
        # 转换日期并过滤有效收益率
        df['date'] = pd.to_datetime(df['date'])
        df = df.dropna(subset=['next_day_return'])
        
        if df.empty:
            return {"error": "没有有效的收益率数据"}
        
        # 按日期排序，确保按时间顺序处理
        df = df.sort_values('date').reset_index(drop=True)
        
        # 添加年份列
        df['year'] = df['date'].dt.year
        
        # 模拟投资过程，计算每年年末的账户余额
        current_capital = initial_capital
        yearly_capital = {}  # 记录每年年末的账户余额
        
        # 按年份分组统计
        yearly_stats = {}
        
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year].copy()
            
            if len(year_data) == 0:
                continue
            
            year_start_capital = current_capital
            
            # 按日期顺序处理该年的每个信号
            for _, row in year_data.iterrows():
                if current_capital <= 0:
                    continue
                    
                return_rate = row['next_day_return'] / 100  # 转换为小数
                
                if position_size >= 1.0:
                    # 满仓策略：资金直接按收益率变化
                    current_capital = current_capital * (1 + return_rate)
                else:
                    # 部分仓位策略：只投资部分资金
                    investment_amount = current_capital * position_size
                    profit = investment_amount * return_rate
                    current_capital = current_capital + profit
            
            # 记录年末账户余额
            yearly_capital[year] = current_capital
            
            returns = year_data['next_day_return']
            
            yearly_stats[year] = {
                'total_signals': len(year_data),
                'mean_return': returns.mean(),
                'median_return': returns.median(),
                'std_return': returns.std(),
                'min_return': returns.min(),
                'max_return': returns.max(),
                'positive_return_ratio': (returns > 0).mean(),
                'negative_return_ratio': (returns < 0).mean(),
                'win_rate': (returns > 0).mean() * 100,
                'total_return': returns.sum(),
                'cumulative_return': (1 + returns / 100).prod() - 1,
                'unique_stocks': year_data['stock_code'].nunique() if 'stock_code' in year_data.columns else 0,
                'year_start_capital': year_start_capital,
                'year_end_capital': current_capital,
                'year_profit': current_capital - year_start_capital,
                'year_return_rate': ((current_capital - year_start_capital) / year_start_capital) * 100 if year_start_capital > 0 else 0
            }
        
        # 计算总体统计
        overall_stats = {
            'total_years': len(yearly_stats),
            'years_with_positive_return': sum(1 for stats in yearly_stats.values() if stats['total_return'] > 0),
            'years_with_negative_return': sum(1 for stats in yearly_stats.values() if stats['total_return'] < 0),
            'best_year': max(yearly_stats.items(), key=lambda x: x[1]['total_return']) if yearly_stats else None,
            'worst_year': min(yearly_stats.items(), key=lambda x: x[1]['total_return']) if yearly_stats else None,
            'avg_yearly_signals': np.mean([stats['total_signals'] for stats in yearly_stats.values()]) if yearly_stats else 0,
            'avg_yearly_return': np.mean([stats['total_return'] for stats in yearly_stats.values()]) if yearly_stats else 0,
            'initial_capital': initial_capital,
            'final_capital': current_capital
        }
        
        return {
            'yearly_stats': yearly_stats,
            'overall_stats': overall_stats,
            'yearly_capital': yearly_capital
        }
    
    def calculate_profitable_stocks_drawdown_stats(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算3日上涨、5日上涨、10日上涨股票的最大回撤统计
        
        Args:
            signals: 信号列表
            
        Returns:
            Dict[str, Any]: 股票回撤统计结果
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 转换为DataFrame
        df = pd.DataFrame(signals)
        
        # 检查必要的字段
        required_fields = ['day3_change_pct', 'day5_change_pct', 'day10_change_pct']
        for field in required_fields:
            if field not in df.columns:
                return {"error": f"缺少{field}字段"}
        
        def calculate_drawdown_for_group(group_df, group_name, target_days):
            """
            计算特定组的回撤统计
            
            Args:
                group_df: 股票数据DataFrame
                group_name: 组名称
                target_days: 目标天数（3, 5, 或 10）
            """
            if group_df.empty:
                return {
                    f'{group_name}_total_count': 0,
                    f'{group_name}_drawdown_lt_1pct_count': 0,
                    f'{group_name}_drawdown_lt_2pct_count': 0,
                    f'{group_name}_drawdown_lt_3pct_count': 0,
                    f'{group_name}_drawdown_lt_1pct_ratio': 0.0,
                    f'{group_name}_drawdown_lt_2pct_ratio': 0.0,
                    f'{group_name}_drawdown_lt_3pct_ratio': 0.0
                }
            
            total_count = len(group_df)
            drawdown_lt_1pct_count = 0
            drawdown_lt_2pct_count = 0
            drawdown_lt_3pct_count = 0
            
            for _, row in group_df.iterrows():
                # 买入价格（当日收盘价）
                buy_price = row.get('close', 0)
                if buy_price <= 0:
                    continue
                
                # 收集从次日到目标天数期间的所有最低价
                min_prices = []
                
                # 次日开盘价
                next_open = row.get('next_open')
                if pd.notna(next_open):
                    min_prices.append(next_open)
                
                # 次日最低价（如果有的话）
                next_low = row.get('next_low')
                if pd.notna(next_low):
                    min_prices.append(next_low)
                else:
                    # 如果没有次日最低价，使用次日收盘价作为备选
                    next_close = row.get('next_close')
                    if pd.notna(next_close):
                        min_prices.append(next_close)
                
                # 收集每日的最低价
                for day in range(2, target_days + 1):
                    day_low_field = f'day{day}_low'
                    if day_low_field in row and pd.notna(row[day_low_field]):
                        min_prices.append(row[day_low_field])
                
                if not min_prices:
                    continue
                
                # 找到期间内的最低价
                period_min_price = min(min_prices)
                
                # 计算最大回撤（从买入价到期间最低价）
                max_drawdown = (period_min_price - buy_price) / buy_price * 100
                
                # 统计回撤程度
                if max_drawdown < -3.0:
                    drawdown_lt_3pct_count += 1
                    drawdown_lt_2pct_count += 1
                    drawdown_lt_1pct_count += 1
                elif max_drawdown < -2.0:
                    drawdown_lt_2pct_count += 1
                    drawdown_lt_1pct_count += 1
                elif max_drawdown < -1.0:
                    drawdown_lt_1pct_count += 1
            
            # 计算比例
            drawdown_lt_1pct_ratio = drawdown_lt_1pct_count / total_count * 100 if total_count > 0 else 0
            drawdown_lt_2pct_ratio = drawdown_lt_2pct_count / total_count * 100 if total_count > 0 else 0
            drawdown_lt_3pct_ratio = drawdown_lt_3pct_count / total_count * 100 if total_count > 0 else 0
            
            return {
                f'{group_name}_total_count': total_count,
                f'{group_name}_drawdown_lt_1pct_count': drawdown_lt_1pct_count,
                f'{group_name}_drawdown_lt_2pct_count': drawdown_lt_2pct_count,
                f'{group_name}_drawdown_lt_3pct_count': drawdown_lt_3pct_count,
                f'{group_name}_drawdown_lt_1pct_ratio': drawdown_lt_1pct_ratio,
                f'{group_name}_drawdown_lt_2pct_ratio': drawdown_lt_2pct_ratio,
                f'{group_name}_drawdown_lt_3pct_ratio': drawdown_lt_3pct_ratio
            }
        
        # 分别过滤出3日上涨、5日上涨、10日上涨的股票
        day3_up_df = df[(df['day3_change_pct'] > 0) & pd.notna(df['day3_change_pct'])].copy()
        day5_up_df = df[(df['day5_change_pct'] > 0) & pd.notna(df['day5_change_pct'])].copy()
        day10_up_df = df[(df['day10_change_pct'] > 0) & pd.notna(df['day10_change_pct'])].copy()
        
        # 计算各组的回撤统计
        day3_stats = calculate_drawdown_for_group(day3_up_df, 'day3_up', 3)
        day5_stats = calculate_drawdown_for_group(day5_up_df, 'day5_up', 5)
        day10_stats = calculate_drawdown_for_group(day10_up_df, 'day10_up', 10)
        
        # 合并结果
        result = {}
        result.update(day3_stats)
        result.update(day5_stats)
        result.update(day10_stats)
        
        return result
    

    
    def generate_performance_report(self, signals: List[Dict[str, Any]], 
                                  output_file: str = None, 
                                  strategy_description: str = None) -> str:
        """
        生成性能报告
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
            strategy_description: 策略条件描述
            
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
        
        # 添加策略条件描述
        if strategy_description:
            report_lines.append("使用的策略条件:")
            # 将策略描述按行分割并添加缩进
            strategy_lines = strategy_description.strip().split('\n')
            for line in strategy_lines:
                if line.strip():  # 跳过空行
                    report_lines.append(f"  {line.strip()}")
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
        
        # 年度收益率统计
        yearly_returns = self.calculate_yearly_returns(signals)
        if 'error' not in yearly_returns and yearly_returns.get('yearly_stats'):
            yearly_stats = yearly_returns['yearly_stats']
            overall_stats = yearly_returns['overall_stats']
            
            report_lines.append("年度收益率统计:")
            report_lines.append(f"  统计年份数: {overall_stats.get('total_years', 0)}")
            report_lines.append(f"  盈利年份数: {overall_stats.get('years_with_positive_return', 0)}")
            report_lines.append(f"  亏损年份数: {overall_stats.get('years_with_negative_return', 0)}")
            report_lines.append(f"  年均信号数: {overall_stats.get('avg_yearly_signals', 0):.1f}")
            report_lines.append(f"  年均收益率: {overall_stats.get('avg_yearly_return', 0):.2f}%")
            
            # 最佳和最差年份
            if overall_stats.get('best_year'):
                best_year, best_stats = overall_stats['best_year']
                report_lines.append(f"  最佳年份: {best_year} (收益率: {best_stats['total_return']:.2f}%, 信号数: {best_stats['total_signals']})")
            
            if overall_stats.get('worst_year'):
                worst_year, worst_stats = overall_stats['worst_year']
                report_lines.append(f"  最差年份: {worst_year} (收益率: {worst_stats['total_return']:.2f}%, 信号数: {worst_stats['total_signals']})")
            
            report_lines.append("")
            
            # 详细年度数据
            report_lines.append("各年度详细统计:")
            report_lines.append("年份      信号数    平均收益率    胜率      总收益率    累计收益率    涉及股票    账户余额(万元)")
            report_lines.append("=" * 98)
            
            for year in sorted(yearly_stats.keys()):
                stats = yearly_stats[year]
                # 使用固定宽度格式化，确保对齐
                year_str = f"{year:<8}"
                signals_str = f"{stats['total_signals']:>8}"
                mean_return_str = f"{stats['mean_return']:>9.2f}%"
                win_rate_str = f"{stats['win_rate']:>8.1f}%"
                total_return_str = f"{stats['total_return']:>10.2f}%"
                cumulative_return_str = f"{stats['cumulative_return']*100:>10.2f}%"
                stocks_str = f"{stats['unique_stocks']:>8}"
                # 添加账户余额列，以万元为单位显示
                capital_str = f"{stats['year_end_capital']/10000:>15.2f}"
                
                report_lines.append(f"{year_str}{signals_str}{mean_return_str}{win_rate_str}{total_return_str}{cumulative_return_str}{stocks_str}{capital_str}")
            
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
            report_lines.append(f"  高开平走: {detailed_stats['high_open_flat_close_count']}/{detailed_stats['total_count']} = {detailed_stats['high_open_flat_close_pct']:.2f}%")
            report_lines.append(f"  低开高走: {detailed_stats['low_open_close_up_count']}/{detailed_stats['total_count']} = {detailed_stats['low_open_close_up_pct']:.2f}%")
            report_lines.append(f"  低开低走: {detailed_stats['low_open_low_close_count']}/{detailed_stats['total_count']} = {detailed_stats['low_open_low_close_pct']:.2f}%")
            report_lines.append(f"  低开平走: {detailed_stats['low_open_flat_close_count']}/{detailed_stats['total_count']} = {detailed_stats['low_open_flat_close_pct']:.2f}%")
            report_lines.append(f"  平开高走: {detailed_stats['flat_open_close_up_count']}/{detailed_stats['total_count']} = {detailed_stats['flat_open_close_up_pct']:.2f}%")
            report_lines.append(f"  平开低走: {detailed_stats['flat_open_close_down_count']}/{detailed_stats['total_count']} = {detailed_stats['flat_open_close_down_pct']:.2f}%")
            report_lines.append(f"  平开平走: {detailed_stats['flat_open_flat_close_count']}/{detailed_stats['total_count']} = {detailed_stats['flat_open_flat_close_pct']:.2f}%")
            
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
            
            if detailed_stats['high_open_flat_close_count'] > 0:
                report_lines.append("\n高开平走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['high_open_flat_close_day3_up']}/{detailed_stats['high_open_flat_close_with_data_count']} = {detailed_stats['high_open_flat_close_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['high_open_flat_close_day5_up']}/{detailed_stats['high_open_flat_close_with_data_count']} = {detailed_stats['high_open_flat_close_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['high_open_flat_close_day10_up']}/{detailed_stats['high_open_flat_close_with_data_count']} = {detailed_stats['high_open_flat_close_day10_up_pct']:.2f}%")
            
            if detailed_stats['low_open_flat_close_count'] > 0:
                report_lines.append("\n低开平走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['low_open_flat_close_day3_up']}/{detailed_stats['low_open_flat_close_with_data_count']} = {detailed_stats['low_open_flat_close_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['low_open_flat_close_day5_up']}/{detailed_stats['low_open_flat_close_with_data_count']} = {detailed_stats['low_open_flat_close_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['low_open_flat_close_day10_up']}/{detailed_stats['low_open_flat_close_with_data_count']} = {detailed_stats['low_open_flat_close_day10_up_pct']:.2f}%")
            
            if detailed_stats['flat_open_close_up_count'] > 0:
                report_lines.append("\n平开高走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['flat_open_close_up_day3_up']}/{detailed_stats['flat_open_close_up_with_data_count']} = {detailed_stats['flat_open_close_up_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['flat_open_close_up_day5_up']}/{detailed_stats['flat_open_close_up_with_data_count']} = {detailed_stats['flat_open_close_up_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['flat_open_close_up_day10_up']}/{detailed_stats['flat_open_close_up_with_data_count']} = {detailed_stats['flat_open_close_up_day10_up_pct']:.2f}%")
            
            if detailed_stats['flat_open_close_down_count'] > 0:
                report_lines.append("\n平开低走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['flat_open_close_down_day3_up']}/{detailed_stats['flat_open_close_down_with_data_count']} = {detailed_stats['flat_open_close_down_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['flat_open_close_down_day5_up']}/{detailed_stats['flat_open_close_down_with_data_count']} = {detailed_stats['flat_open_close_down_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['flat_open_close_down_day10_up']}/{detailed_stats['flat_open_close_down_with_data_count']} = {detailed_stats['flat_open_close_down_day10_up_pct']:.2f}%")
            
            if detailed_stats['flat_open_flat_close_count'] > 0:
                report_lines.append("\n平开平走情况下的后续表现:")
                report_lines.append(f"  3日收盘上涨: {detailed_stats['flat_open_flat_close_day3_up']}/{detailed_stats['flat_open_flat_close_with_data_count']} = {detailed_stats['flat_open_flat_close_day3_up_pct']:.2f}%")
                report_lines.append(f"  5日收盘上涨: {detailed_stats['flat_open_flat_close_day5_up']}/{detailed_stats['flat_open_flat_close_with_data_count']} = {detailed_stats['flat_open_flat_close_day5_up_pct']:.2f}%")
                report_lines.append(f"  10日收盘上涨: {detailed_stats['flat_open_flat_close_day10_up']}/{detailed_stats['flat_open_flat_close_with_data_count']} = {detailed_stats['flat_open_flat_close_day10_up_pct']:.2f}%")
            
            report_lines.append("")
        
        # 3日、5日、10日上涨股票最大回撤统计
        drawdown_stats = self.calculate_profitable_stocks_drawdown_stats(signals)
        if 'error' not in drawdown_stats:
            report_lines.append("3日、5日、10日上涨股票最大回撤统计 (从买入价到目标期间的最大回撤):")
            
            # 3日上涨股票回撤统计
            if 'day3_up_total_count' in drawdown_stats and drawdown_stats['day3_up_total_count'] > 0:
                report_lines.append(f"  3日上涨股票:")
                report_lines.append(f"    总数量: {drawdown_stats['day3_up_total_count']}")
                report_lines.append(f"    最大回撤 < -1%: {drawdown_stats['day3_up_drawdown_lt_1pct_count']}/{drawdown_stats['day3_up_total_count']} = {drawdown_stats['day3_up_drawdown_lt_1pct_ratio']:.2f}%")
                report_lines.append(f"    最大回撤 < -2%: {drawdown_stats['day3_up_drawdown_lt_2pct_count']}/{drawdown_stats['day3_up_total_count']} = {drawdown_stats['day3_up_drawdown_lt_2pct_ratio']:.2f}%")
                report_lines.append(f"    最大回撤 < -3%: {drawdown_stats['day3_up_drawdown_lt_3pct_count']}/{drawdown_stats['day3_up_total_count']} = {drawdown_stats['day3_up_drawdown_lt_3pct_ratio']:.2f}%")
            
            # 5日上涨股票回撤统计
            if 'day5_up_total_count' in drawdown_stats and drawdown_stats['day5_up_total_count'] > 0:
                report_lines.append(f"  5日上涨股票:")
                report_lines.append(f"    总数量: {drawdown_stats['day5_up_total_count']}")
                report_lines.append(f"    最大回撤 < -1%: {drawdown_stats['day5_up_drawdown_lt_1pct_count']}/{drawdown_stats['day5_up_total_count']} = {drawdown_stats['day5_up_drawdown_lt_1pct_ratio']:.2f}%")
                report_lines.append(f"    最大回撤 < -2%: {drawdown_stats['day5_up_drawdown_lt_2pct_count']}/{drawdown_stats['day5_up_total_count']} = {drawdown_stats['day5_up_drawdown_lt_2pct_ratio']:.2f}%")
                report_lines.append(f"    最大回撤 < -3%: {drawdown_stats['day5_up_drawdown_lt_3pct_count']}/{drawdown_stats['day5_up_total_count']} = {drawdown_stats['day5_up_drawdown_lt_3pct_ratio']:.2f}%")
            
            # 10日上涨股票回撤统计
            if 'day10_up_total_count' in drawdown_stats and drawdown_stats['day10_up_total_count'] > 0:
                report_lines.append(f"  10日上涨股票:")
                report_lines.append(f"    总数量: {drawdown_stats['day10_up_total_count']}")
                report_lines.append(f"    最大回撤 < -1%: {drawdown_stats['day10_up_drawdown_lt_1pct_count']}/{drawdown_stats['day10_up_total_count']} = {drawdown_stats['day10_up_drawdown_lt_1pct_ratio']:.2f}%")
                report_lines.append(f"    最大回撤 < -2%: {drawdown_stats['day10_up_drawdown_lt_2pct_count']}/{drawdown_stats['day10_up_total_count']} = {drawdown_stats['day10_up_drawdown_lt_2pct_ratio']:.2f}%")
                report_lines.append(f"    最大回撤 < -3%: {drawdown_stats['day10_up_drawdown_lt_3pct_count']}/{drawdown_stats['day10_up_total_count']} = {drawdown_stats['day10_up_drawdown_lt_3pct_ratio']:.2f}%")
            
            report_lines.append("")
        

        
        # 按年份显示所有交易信号
        if signals:
            # 转换为DataFrame以便处理
            df = pd.DataFrame(signals)
            
            if 'date' in df.columns and len(df) > 0:
                # 添加年份列
                df['year'] = pd.to_datetime(df['date']).dt.year
                
                # 按年份分组
                years = sorted(df['year'].unique(), reverse=True)
                
                for year in years:
                    year_data = df[df['year'] == year].sort_values('date', ascending=False)
                    
                    if len(year_data) > 0:
                        report_lines.append(f"{year}年交易信号 (共{len(year_data)}条):")
                        # 使用简单直接的表格格式化方法
                        # 构建表头
                        header = f"{'股票代码':<10} {'日期':<10} {'买入价':<6} {'买入时涨幅':<8} {'次日开盘卖出':<10} {'卖出价':<7} {'盈亏比例':<8}"
                        
                        report_lines.append(header)
                        report_lines.append("=" * len(header))
                        
                        for _, row in year_data.iterrows():
                            stock_code = row.get('stock_code', 'N/A')
                            date = row.get('date', 'N/A')
                            
                            # 格式化各列数据
                            # 买入价格
                            if pd.notna(row.get('close')):
                                buy_price = f"{row.get('close', 0):.2f}"
                            else:
                                buy_price = "N/A"
                            
                            # 买入时涨幅 (相对于上一交易日收盘价)
                            buy_gain = "N/A"
                            if pd.notna(row.get('close')):
                                close_val = row.get('close', 0)
                                stock_code_val = row.get('stock_code', '')
                                date_val = row.get('date', '')
                                
                                # 获取前一日收盘价
                                prev_close = self._get_previous_close_price(stock_code_val, date_val)
                                if prev_close is not None and prev_close > 0:
                                    buy_gain_val = ((close_val - prev_close) / prev_close) * 100
                                    buy_gain = f"{buy_gain_val:+.2f}%"
                            
                            # 卖出价格和盈亏比例
                            if pd.notna(row.get('next_open')) and pd.notna(row.get('close')):
                                sell_price = f"{row.get('next_open', 0):.2f}"
                                # 计算盈亏比例
                                buy_val = row.get('close', 0)
                                sell_val = row.get('next_open', 0)
                                if buy_val > 0:
                                    profit_loss_val = ((sell_val - buy_val) / buy_val) * 100
                                    profit_loss = f"{profit_loss_val:+.2f}%"
                                else:
                                    profit_loss = "N/A"
                            else:
                                sell_price = "N/A"
                                profit_loss = "N/A"
                            
                            # 组合数据行 - 使用与表头相同的格式
                            data_row = f"{stock_code:<10} {date:<12} {buy_price:>8} {buy_gain:>10} {'':<12} {sell_price:>8} {profit_loss:>10}"
                            
                            report_lines.append(data_row)
                        
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
  次日高开低走比例: {stats.get('high_open_low_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('high_open_low_close_pct', 0):.2f}%)
  次日高开平走比例: {stats.get('high_open_flat_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('high_open_flat_close_pct', 0):.2f}%)
  次日低开收盘上涨比例: {stats.get('low_open_close_up_count', 0)}/{stats.get('total_count', 0)} ({stats.get('low_open_close_up_pct', 0):.2f}%)
  次日低开低走比例: {stats.get('low_open_low_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('low_open_low_close_pct', 0):.2f}%)
  次日低开平走比例: {stats.get('low_open_flat_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('low_open_flat_close_pct', 0):.2f}%)
  次日平开高走比例: {stats.get('flat_open_close_up_count', 0)}/{stats.get('total_count', 0)} ({stats.get('flat_open_close_up_pct', 0):.2f}%)
  次日平开低走比例: {stats.get('flat_open_close_down_count', 0)}/{stats.get('total_count', 0)} ({stats.get('flat_open_close_down_pct', 0):.2f}%)
  次日平开平走比例: {stats.get('flat_open_flat_close_count', 0)}/{stats.get('total_count', 0)} ({stats.get('flat_open_flat_close_pct', 0):.2f}%)
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
    
    def _get_previous_close_price(self, stock_code: str, date_str: str) -> Optional[float]:
        """
        获取指定股票在指定日期的前一交易日收盘价
        
        Args:
            stock_code: 股票代码
            date_str: 日期字符串 (格式: YYYY-MM-DD)
            
        Returns:
            Optional[float]: 前一交易日收盘价，如果无法获取则返回None
        """
        try:
            from data_loader import StockDataLoader
            import os
            
            # 获取数据文件夹路径
            data_folder = r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info\all_stocks_data"
            
            # 创建数据加载器
            data_loader = StockDataLoader(data_folder)
            
            # 加载股票数据
            stock_data = data_loader.load_stock_data(stock_code)
            if stock_data is None or stock_data.empty:
                return None
            
            # 确保日期列为datetime类型
            if 'datetime' in stock_data.columns:
                stock_data['datetime'] = pd.to_datetime(stock_data['datetime'])
                stock_data = stock_data.sort_values('datetime')
            else:
                return None
            
            # 转换目标日期
            target_date = pd.to_datetime(date_str)
            
            # 找到目标日期的索引
            target_mask = stock_data['datetime'].dt.date == target_date.date()
            target_indices = stock_data[target_mask].index
            
            if len(target_indices) == 0:
                return None
            
            target_index = target_indices[0]
            
            # 找到前一个交易日的数据
            prev_data = stock_data[stock_data.index < target_index]
            if prev_data.empty:
                return None
            
            # 获取最近的前一个交易日的收盘价
            prev_close = prev_data.iloc[-1]['close']
            return float(prev_close) if pd.notna(prev_close) else None
            
        except Exception as e:
            self.logger.warning(f"获取前一日收盘价失败 {stock_code} {date_str}: {e}")
            return None


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