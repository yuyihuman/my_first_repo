#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
买入策略模块

负责定义各种买入策略
目前仅预留接口，后续可扩展具体的买入策略逻辑
"""

from typing import List, Dict, Any, Callable, Tuple
from datetime import datetime
from utils.logger import setup_logger

class BuyStrategy:
    """
    买入策略类
    
    提供各种买入策略的接口
    """
    
    def __init__(self):
        """
        初始化买入策略
        """
        self.logger = setup_logger('buy_strategy', 'buy_strategy.log')
        self.logger.info("买入策略模块初始化")
        
        # 买入策略注册表
        self.strategies = {}
        
        # 注册默认策略
        self.register_strategy("default", self._default_strategy)
        
        self.logger.debug("买入策略初始化完成")
    
    def register_strategy(self, name: str, strategy_func: Callable):
        """
        注册买入策略
        
        Args:
            name (str): 策略名称
            strategy_func (Callable): 策略函数，接收股票代码和其他参数，返回买入信号和买入时间
        """
        self.logger.info(f"注册买入策略: {name}")
        self.strategies[name] = strategy_func
        self.logger.debug(f"当前已注册买入策略数量: {len(self.strategies)}")
    
    def execute_strategy(self, strategy_name: str, stock_code: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        执行买入策略
        
        Args:
            strategy_name (str): 策略名称
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表，每个信号包含买入日期、价格等信息
        """
        self.logger.info(f"执行买入策略: {strategy_name}, 股票: {stock_code}, 时间范围: {start_date} - {end_date}")
        self.logger.debug(f"买入策略参数: {kwargs}")
        
        try:
            if strategy_name in self.strategies:
                # 执行指定策略
                signals = self.strategies[strategy_name](stock_code, start_date, end_date, **kwargs)
                self.logger.info(f"买入策略执行完成，生成 {len(signals)} 个买入信号")
                self.logger.debug(f"买入信号: {signals}")
                return signals
            else:
                self.logger.error(f"未找到买入策略: {strategy_name}")
                raise ValueError(f"未找到买入策略: {strategy_name}")
        except Exception as e:
            self.logger.error(f"执行买入策略时发生错误: {str(e)}", exc_info=True)
            raise
    
    def _default_strategy(self, stock_code: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        默认买入策略：简单的定期买入
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
                - interval (int): 买入间隔天数，默认为20个交易日
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表
        """
        self.logger.info(f"执行默认买入策略，股票: {stock_code}")
        
        # 这里仅返回一个示例买入信号
        # 实际实现中应该根据行情数据生成真实的买入信号
        signals = [
            {
                "date": start_date,
                "price": 10.0,  # 示例价格
                "volume": 100,   # 示例数量
                "reason": "默认策略示例买入"
            }
        ]
        
        self.logger.debug(f"默认买入策略生成信号: {signals}")
        return signals
    
    def get_available_strategies(self) -> List[str]:
        """
        获取可用的买入策略列表
        
        Returns:
            List[str]: 策略名称列表
        """
        strategies = list(self.strategies.keys())
        self.logger.debug(f"获取可用买入策略列表: {strategies}")
        return strategies