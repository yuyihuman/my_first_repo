# coding:utf-8
"""
选股模块 - 基于策略筛选股票

专注于单股票测试和信号筛选功能
"""

import pandas as pd
import os
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from data_loader import StockDataLoader, DataPreprocessor
from strategy_engine import StrategyEngine


class StockSelector:
    """股票选择器"""
    
    def __init__(self, data_folder: str, strategy_engine: StrategyEngine = None):
        """
        初始化股票选择器
        
        Args:
            data_folder: 股票数据文件夹路径
            strategy_engine: 策略引擎实例
        """
        self.data_folder = data_folder
        self.data_loader = StockDataLoader(data_folder)
        self.data_preprocessor = DataPreprocessor()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.logger = logging.getLogger(__name__)
    
    def test_single_stock(self, stock_code: str, verbose: bool = True) -> List[Dict[str, Any]]:
        """
        测试单个股票
        
        Args:
            stock_code: 股票代码
            verbose: 是否显示详细信息
            
        Returns:
            List[Dict[str, Any]]: 符合条件的信号列表
        """
        # 记录开始时间
        start_time = time.time()
        self.logger.info(f"开始测试股票: {stock_code}")
        
        try:
            # 加载股票数据
            df = self.data_loader.load_stock_data(stock_code)
            if df is None:
                self.logger.error(f"无法加载股票 {stock_code} 的数据")
                return []
            
            # 验证数据质量
            if not self.data_loader.validate_data_quality(df, stock_code):
                self.logger.error(f"股票 {stock_code} 数据质量不合格")
                return []
            
            # 清理数据
            df = self.data_preprocessor.clean_data(df, stock_code)
            
            # 添加技术指标
            df = self.data_preprocessor.add_technical_indicators(df)
            
            # 扫描信号
            signals = self.strategy_engine.scan_stock_for_signals(df, stock_code)
            
            if verbose:
                self.logger.info(f"股票 {stock_code} 找到 {len(signals)} 个符合条件的信号")
                for signal in signals:
                    self.logger.info(f"  日期: {signal['date']}, 收盘价: {signal['close']:.4f}, "
                                   f"次日收益: {signal['next_day_return']:.2f}%" if signal['next_day_return'] else "次日收益: N/A")
            
            return signals
            
        finally:
            # 计算耗时并记录结束日志
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.logger.info(f"完成测试股票: {stock_code}, 耗时: {elapsed_time:.3f}秒")
    
    def test_single_stock_verbose(self, stock_code: str, target_date: str = None) -> Dict[str, Any]:
        """
        详细测试单个股票的特定日期
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，如果为None则测试最新日期
            
        Returns:
            Dict[str, Any]: 详细检查结果
        """
        # 记录开始时间
        start_time = time.time()
        self.logger.info(f"开始详细测试股票: {stock_code}")
        
        try:
            # 加载股票数据
            df = self.data_loader.load_stock_data(stock_code)
            if df is None:
                return {"error": f"无法加载股票 {stock_code} 的数据"}
            
            # 验证数据质量
            if not self.data_loader.validate_data_quality(df, stock_code):
                return {"error": f"股票 {stock_code} 数据质量不合格"}
            
            # 清理数据
            df = self.data_preprocessor.clean_data(df, stock_code)
            
            # 确定测试日期索引
            if target_date:
                target_datetime = pd.to_datetime(target_date)
                matching_rows = df[df['datetime'] == target_datetime]
                if matching_rows.empty:
                    return {"error": f"未找到日期 {target_date} 的数据"}
                current_idx = matching_rows.index[0]
            else:
                current_idx = len(df) - 1  # 最新日期
            
            # 详细检查策略条件
            result, details = self.strategy_engine.check_strategy_conditions_verbose(
                df, current_idx, stock_code, verbose=True
            )
            
            return details
            
        finally:
            # 计算耗时并记录结束日志
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.logger.info(f"完成详细测试股票: {stock_code}, 耗时: {elapsed_time:.3f}秒")
    

    

    

    

    
    def filter_signals_by_date(self, signals: List[Dict[str, Any]], 
                             start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        按日期范围过滤信号
        
        Args:
            signals: 信号列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            List[Dict[str, Any]]: 过滤后的信号列表
        """
        filtered_signals = signals.copy()
        
        if start_date:
            start_date = pd.to_datetime(start_date)
            filtered_signals = [s for s in filtered_signals if pd.to_datetime(s['date']) >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            filtered_signals = [s for s in filtered_signals if pd.to_datetime(s['date']) <= end_date]
        
        return filtered_signals
    
    def get_top_signals(self, signals: List[Dict[str, Any]], 
                       top_n: int = 10, sort_by: str = 'next_day_return') -> List[Dict[str, Any]]:
        """
        获取排名前N的信号
        
        Args:
            signals: 信号列表
            top_n: 返回前N个
            sort_by: 排序字段
            
        Returns:
            List[Dict[str, Any]]: 排名前N的信号
        """
        # 过滤掉没有次日收益数据的信号
        valid_signals = [s for s in signals if s.get(sort_by) is not None]
        
        # 按指定字段排序
        sorted_signals = sorted(valid_signals, key=lambda x: x[sort_by], reverse=True)
        
        return sorted_signals[:top_n]


class BatchStockProcessor:
    """批量股票处理器（用于兼容原有接口）"""
    
    def __init__(self, data_folder: str):
        self.data_folder = data_folder
        self.stock_selector = StockSelector(data_folder)
        self.logger = logging.getLogger(__name__)
    
    def process_single_stock(self, stock_code: str, process_index: int = 1, 
                           log_to_file=None, verbose: bool = False) -> List[Dict[str, Any]]:
        """
        处理单个股票（兼容原有接口）
        
        Args:
            stock_code: 股票代码
            process_index: 进程序号
            log_to_file: 日志记录函数
            verbose: 是否详细输出
            
        Returns:
            List[Dict[str, Any]]: 符合条件的信号列表
        """
        return self.stock_selector.test_single_stock(stock_code, verbose)
    
    def run_stock_selection_strategy_dynamic(self, data_folder: str, output_file: str, 
                                           num_processes: int = 20, limit: int = None):
        """
        运行股票选择策略（兼容原有接口）
        
        Args:
            data_folder: 数据文件夹
            output_file: 输出文件路径
            num_processes: 进程数量
            limit: 限制处理的股票数量
        """
        # 测试所有股票
        result_df = self.stock_selector.test_all_stocks(num_processes, limit)
        
        # 保存结果
        if not result_df.empty:
            result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"结果已保存到: {output_file}")
        else:
            self.logger.warning("没有找到符合条件的股票")