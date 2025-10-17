# coding:utf-8
"""
股票回测系统

一个模块化的股票回测框架，包含以下模块：
- data_loader: 数据加载和预处理
- strategy_engine: 策略执行引擎
- stock_selector: 股票选择器
- result_analyzer: 结果分析和输出
- main: 主程序入口

使用示例:
    from stock_backtest import BacktestingSystem
    
    # 初始化回测系统
    system = BacktestingSystem(data_folder="path/to/data")
    
    # 测试单个股票
    result = system.test_single_stock("000001")
    
    # 批量测试
    result = system.test_batch_stocks(["000001", "000002"])
    
    # 全量测试
    result = system.test_all_stocks()
"""

from main import BacktestingSystem
from data_loader import StockDataLoader, DataPreprocessor
from strategy_engine import StrategyEngine, ModelBasedStrategy
from stock_selector import StockSelector, BatchStockProcessor
from result_analyzer import ResultAnalyzer, ResultExporter, ResultFormatter

__version__ = "1.0.0"
__author__ = "Stock Backtest System"

__all__ = [
    'BacktestingSystem',
    'StockDataLoader',
    'DataPreprocessor', 
    'StrategyEngine',
    'ModelBasedStrategy',
    'StockSelector',
    'BatchStockProcessor',
    'ResultAnalyzer',
    'ResultExporter',
    'ResultFormatter'
]