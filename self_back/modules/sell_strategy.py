#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卖出策略模块

负责定义各种卖出策略
目前仅预留接口，后续可扩展具体的卖出策略逻辑
"""

from typing import List, Dict, Any, Callable
from datetime import datetime
from utils.logger import setup_logger

class SellStrategy:
    """
    卖出策略类
    
    提供各种卖出策略的接口
    """
    
    # 在__init__方法中添加新策略注册
    def __init__(self):
        """
        初始化卖出策略
        """
        self.logger = setup_logger('sell_strategy', 'sell_strategy.log')
        self.logger.info("卖出策略模块初始化")
        
        # 卖出策略注册表
        self.strategies = {}
        
        # 注册默认策略
        self.register_strategy("default", self._default_strategy)
        # 注册止盈止损策略
        self.register_strategy("stop_profit_loss", self._stop_profit_loss_strategy)
        # 注册持股三天策略
        self.register_strategy("hold_three_days", self._hold_three_days_strategy)
        
        self.logger.debug("卖出策略初始化完成")
    
    def register_strategy(self, name: str, strategy_func: Callable):
        """
        注册卖出策略
        
        Args:
            name (str): 策略名称
            strategy_func (Callable): 策略函数，接收股票代码、买入信息和其他参数，返回卖出信号
        """
        self.logger.info(f"注册卖出策略: {name}")
        self.strategies[name] = strategy_func
        self.logger.debug(f"当前已注册卖出策略数量: {len(self.strategies)}")
    
    def execute_strategy(self, strategy_name: str, stock_code: str, buy_info: Dict[str, Any], 
                        start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        执行卖出策略
        
        Args:
            strategy_name (str): 策略名称
            stock_code (str): 股票代码
            buy_info (Dict[str, Any]): 买入信息，包含买入日期、价格等
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
        
        Returns:
            List[Dict[str, Any]]: 卖出信号列表，每个信号包含卖出日期、价格等信息
        """
        self.logger.info(f"执行卖出策略: {strategy_name}, 股票: {stock_code}, 时间范围: {start_date} - {end_date}")
        self.logger.debug(f"买入信息: {buy_info}")
        self.logger.debug(f"卖出策略参数: {kwargs}")
        
        try:
            if strategy_name in self.strategies:
                # 执行指定策略
                signals = self.strategies[strategy_name](stock_code, buy_info, start_date, end_date, **kwargs)
                self.logger.info(f"卖出策略执行完成，生成 {len(signals)} 个卖出信号")
                self.logger.debug(f"卖出信号: {signals}")
                return signals
            else:
                self.logger.error(f"未找到卖出策略: {strategy_name}")
                raise ValueError(f"未找到卖出策略: {strategy_name}")
        except Exception as e:
            self.logger.error(f"执行卖出策略时发生错误: {str(e)}", exc_info=True)
            raise
    
    def execute_strategy_with_data(self, strategy_name: str, stock_code: str, buy_info: Dict[str, Any],
                                  start_date: str, end_date: str, batch_data: dict, data_manager=None, **kwargs) -> List[Dict[str, Any]]:
        """
        使用预先获取的批量数据执行卖出策略
        
        Args:
            strategy_name (str): 策略名称
            stock_code (str): 股票代码
            buy_info (Dict[str, Any]): 买入信息，包含买入日期、价格等
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            batch_data (dict): 批量数据
            data_manager: 数据管理器实例
            **kwargs: 策略参数
        
        Returns:
            List[Dict[str, Any]]: 卖出信号列表
        """
        self.logger.info(f"使用批量数据执行卖出策略: {strategy_name}, 股票: {stock_code}")
        
        try:
            if strategy_name in self.strategies:
                # 将批量数据和数据管理器传递给策略函数
                kwargs['batch_data'] = batch_data
                kwargs['data_manager'] = data_manager
                
                signals = self.strategies[strategy_name](stock_code, buy_info, start_date, end_date, **kwargs)
                self.logger.info(f"批量数据卖出策略执行完成，生成 {len(signals)} 个卖出信号")
                return signals
            else:
                self.logger.error(f"未找到卖出策略: {strategy_name}")
                raise ValueError(f"未找到卖出策略: {strategy_name}")
        except Exception as e:
            self.logger.error(f"执行批量数据卖出策略时发生错误: {str(e)}", exc_info=True)
            raise
    
    def _default_strategy(self, stock_code: str, buy_info: Dict[str, Any], 
                         start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        默认卖出策略：简单的持有期卖出
        
        Args:
            stock_code (str): 股票代码
            buy_info (Dict[str, Any]): 买入信息
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
                - hold_days (int): 持有天数，默认为30个交易日
                - stop_loss (float): 止损比例，默认为0.1（10%）
                - take_profit (float): 止盈比例，默认为0.2（20%）
        
        Returns:
            List[Dict[str, Any]]: 卖出信号列表
        """
        self.logger.info(f"执行默认卖出策略，股票: {stock_code}")
        
        # 获取策略参数
        hold_days = kwargs.get('hold_days', 30)
        stop_loss = kwargs.get('stop_loss', 0.1)
        take_profit = kwargs.get('take_profit', 0.2)
        
        self.logger.debug(f"策略参数 - 持有天数: {hold_days}, 止损: {stop_loss}, 止盈: {take_profit}")
        
        # 这里仅返回一个示例卖出信号
        # 实际实现中应该根据行情数据和买入信息生成真实的卖出信号
        signals = [
            {
                "date": end_date,
                "price": buy_info.get('price', 10.0) * 1.1,  # 示例：比买入价高10%
                "volume": buy_info.get('volume', 100),
                "reason": "默认策略示例卖出"
            }
        ]
        
        self.logger.debug(f"默认卖出策略生成信号: {signals}")
        return signals
    
    def get_available_strategies(self) -> List[str]:
        """
        获取可用的卖出策略列表
        
        Returns:
            List[str]: 策略名称列表
        """
        strategies = list(self.strategies.keys())
        self.logger.debug(f"获取可用卖出策略列表: {strategies}")
        return strategies
    
    def _stop_profit_loss_strategy(self, stock_code: str, buy_info: Dict[str, Any], 
                                  start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        止盈止损卖出策略：达到止盈或止损条件时卖出
        
        Args:
            stock_code (str): 股票代码
            buy_info (Dict[str, Any]): 买入信息
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
                - stop_loss_pct (float): 止损比例，默认为0.1（10%）
                - take_profit_pct (float): 止盈比例，默认为0.15（15%）
                - max_hold_days (int): 最大持有天数，默认为30天
        
        Returns:
            List[Dict[str, Any]]: 卖出信号列表
        """
        self.logger.info(f"执行止盈止损卖出策略，股票: {stock_code}")
        
        # 获取策略参数
        stop_loss_pct = kwargs.get('stop_loss_pct', 0.1)
        take_profit_pct = kwargs.get('take_profit_pct', 0.15)
        max_hold_days = kwargs.get('max_hold_days', 30)
        
        buy_price = buy_info.get('price', 10.0)
        buy_date = buy_info.get('date', start_date)
        
        self.logger.debug(f"策略参数 - 止损: {stop_loss_pct:.1%}, 止盈: {take_profit_pct:.1%}, 最大持有: {max_hold_days}天")
        self.logger.debug(f"买入信息 - 价格: {buy_price}, 日期: {buy_date}")
        
        # 计算止盈止损价格
        stop_loss_price = buy_price * (1 - stop_loss_pct)
        take_profit_price = buy_price * (1 + take_profit_pct)
        
        # 简化实现：假设在买入后15天达到止盈条件
        from datetime import datetime, timedelta
        
        buy_dt = datetime.strptime(buy_date, '%Y%m%d')
        sell_dt = buy_dt + timedelta(days=15)
        sell_date = sell_dt.strftime('%Y%m%d')
        
        # 示例：假设达到止盈条件
        sell_price = take_profit_price
        sell_reason = f"止盈卖出 (目标价格: {take_profit_price:.2f})"
        
        signals = [
            {
                "date": sell_date,
                "price": sell_price,
                "volume": buy_info.get('volume', 1000),
                "reason": sell_reason,
                "strategy": "stop_profit_loss",
                "buy_price": buy_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "return_rate": (sell_price - buy_price) / buy_price
            }
        ]
        
        self.logger.debug(f"止盈止损策略生成信号: {signals}")
        return signals
    
    def _hold_three_days_strategy(self, stock_code: str, buy_info: Dict[str, Any], 
                                 start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        持股三天卖出策略：买入后持股三天自动卖出
        
        Args:
            stock_code (str): 股票代码
            buy_info (Dict[str, Any]): 买入信息
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
        
        Returns:
            List[Dict[str, Any]]: 卖出信号列表
        """
        self.logger.info(f"执行持股三天卖出策略，股票: {stock_code}")
        
        buy_price = buy_info.get('price', 10.0)
        buy_date = buy_info.get('date', start_date)
        buy_volume = buy_info.get('volume', 1000)
        
        self.logger.debug(f"买入信息 - 价格: {buy_price}, 日期: {buy_date}, 数量: {buy_volume}")
        
        # 计算卖出日期：买入后第3个交易日
        from datetime import datetime, timedelta
        import random
        
        buy_dt = datetime.strptime(buy_date, '%Y%m%d')
        # 持股3天后卖出（考虑周末，实际可能是3-5个自然日）
        sell_dt = buy_dt + timedelta(days=3)
        
        # 如果卖出日期超过回测结束日期，则在结束日期卖出
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        if sell_dt > end_dt:
            sell_dt = end_dt
        
        sell_date = sell_dt.strftime('%Y%m%d')
        
        # 示例卖出价格：在买入价格基础上随机波动-5%到+8%
        price_change = random.uniform(-0.05, 0.08)
        sell_price = round(buy_price * (1 + price_change), 2)
        
        return_rate = (sell_price - buy_price) / buy_price
        
        signals = [
            {
                "date": sell_date,
                "price": sell_price,
                "volume": buy_volume,
                "reason": "持股三天自动卖出",
                "strategy": "hold_three_days",
                "buy_price": buy_price,
                "buy_date": buy_date,
                "hold_days": 3,
                "return_rate": return_rate
            }
        ]
        
        self.logger.debug(f"持股三天策略生成信号: {signals}")
        return signals