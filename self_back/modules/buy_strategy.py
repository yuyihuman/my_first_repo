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
    
    # 在__init__方法中添加新策略注册
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
        # 注册移动平均线策略
        self.register_strategy("ma_crossover", self._ma_crossover_strategy)
        # 注册连续三天上涨策略
        self.register_strategy("three_days_up", self._three_days_up_strategy)
        
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
    
    def execute_strategy_with_data(self, strategy_name: str, stock_code: str, start_date: str, end_date: str, 
                                  batch_data: dict, data_manager=None, **kwargs) -> List[Dict[str, Any]]:
        """
        使用预先获取的批量数据执行买入策略
        
        Args:
            strategy_name (str): 策略名称
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            batch_data (dict): 批量数据
            data_manager: 数据管理器实例
            **kwargs: 策略参数
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表
        """
        self.logger.info(f"使用批量数据执行买入策略: {strategy_name}, 股票: {stock_code}")
        
        try:
            if strategy_name in self.strategies:
                # 将批量数据和数据管理器传递给策略函数
                kwargs['batch_data'] = batch_data
                kwargs['data_manager'] = data_manager
                
                signals = self.strategies[strategy_name](stock_code, start_date, end_date, **kwargs)
                self.logger.info(f"批量数据买入策略执行完成，生成 {len(signals)} 个买入信号")
                return signals
            else:
                self.logger.error(f"未找到买入策略: {strategy_name}")
                raise ValueError(f"未找到买入策略: {strategy_name}")
        except Exception as e:
            self.logger.error(f"执行批量数据买入策略时发生错误: {str(e)}", exc_info=True)
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
    
    # 在文件末尾添加新的策略方法
    def _ma_crossover_strategy(self, stock_code: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        移动平均线交叉买入策略：当短期均线上穿长期均线时买入
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
                - short_period (int): 短期均线周期，默认为5
                - long_period (int): 长期均线周期，默认为20
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表
        """
        self.logger.info(f"执行移动平均线交叉买入策略，股票: {stock_code}")
        
        # 获取策略参数
        short_period = kwargs.get('short_period', 5)
        long_period = kwargs.get('long_period', 20)
        
        self.logger.debug(f"策略参数 - 短期均线: {short_period}天, 长期均线: {long_period}天")
        
        # 简化实现：在开始日期后的第一个交易日买入
        # 实际实现中应该获取真实股价数据并计算移动平均线
        from datetime import datetime, timedelta
        
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        # 假设在开始日期后10天触发买入信号
        buy_dt = start_dt + timedelta(days=10)
        buy_date = buy_dt.strftime('%Y%m%d')
        
        signals = [
            {
                "date": buy_date,
                "price": 12.5,  # 示例价格
                "volume": 1000,
                "reason": f"移动平均线交叉买入信号 (MA{short_period} > MA{long_period})",
                "strategy": "ma_crossover",
                "short_ma": short_period,
                "long_ma": long_period
            }
        ]
        
        self.logger.debug(f"移动平均线策略生成信号: {signals}")
        return signals
    
    def _three_days_up_strategy(self, stock_code: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        连续三天上涨买入策略：当股价连续三天上涨时买入
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
                - batch_data: 批量数据（可选）
                - data_manager: 数据管理器（可选）
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表
        """
        self.logger.info(f"执行连续三天上涨买入策略，股票: {stock_code}")
        
        signals = []
        
        from datetime import datetime, timedelta
        import pandas as pd
        
        # 检查是否有批量数据
        batch_data = kwargs.get('batch_data')
        data_manager = kwargs.get('data_manager')
        
        if batch_data and data_manager:
            # 使用批量数据
            self.logger.info(f"使用批量数据进行策略分析: {stock_code}")
            self.logger.debug(f"批量数据键: {list(batch_data.keys()) if batch_data else 'None'}")
            
            df = data_manager.get_stock_dataframe(stock_code, batch_data, start_date, end_date)
            
            if df is None:
                self.logger.warning(f"无法从批量数据中获取股票 {stock_code} 的数据 - DataFrame为None")
                return signals
            elif df.empty:
                self.logger.warning(f"无法从批量数据中获取股票 {stock_code} 的数据 - DataFrame为空")
                return signals
            else:
                self.logger.debug(f"成功从批量数据获取 {len(df)} 条数据，时间范围: {df.index[0]} 到 {df.index[-1]}")
                self.logger.debug(f"数据列: {df.columns.tolist()}")
                self.logger.debug(f"前5行数据:\n{df.head()}")
                
        else:
            # 回退到原有的数据获取方式
            self.logger.info(f"使用传统方式获取数据: {stock_code}")
            try:
                from xtquant import xtdata
            except ImportError:
                xtdata = None
                
            if xtdata is None:
                self.logger.error("xtdata模块未安装，无法获取真实数据")
                raise ImportError("xtdata模块未安装，项目只支持真实数据")
            
            # 扩展数据获取范围，确保有足够的历史数据用于判断连续上涨
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            # 向前扩展30天以获取足够的历史数据
            extended_start_dt = start_dt - timedelta(days=30)
            extended_start_date = extended_start_dt.strftime('%Y%m%d')
            
            self.logger.debug(f"获取股票数据: {stock_code}, 扩展时间范围: {extended_start_date} - {end_date}")
            
            # 获取日K线数据
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock_code],
                period='1d',
                start_time=extended_start_date,
                end_time=end_date,
                dividend_type='none',
                fill_data=True
            )
            
            if data and 'close' in data and stock_code in data['close'].index:
                # 构建DataFrame
                df_data = {
                    'Open': data['open'].loc[stock_code],
                    'High': data['high'].loc[stock_code],
                    'Low': data['low'].loc[stock_code],
                    'Close': data['close'].loc[stock_code],
                    'Volume': data['volume'].loc[stock_code]
                }
                
                df = pd.DataFrame(df_data)
                df.index = pd.to_datetime(df.index, format='%Y%m%d')
                df.index.name = 'Date'
                
                self.logger.debug(f"成功获取 {len(df)} 条K线数据")
            else:
                self.logger.error(f"无法获取股票 {stock_code} 的数据")
                return signals
        
        # 统一的数据分析逻辑（无论是批量数据还是传统获取的数据）
        try:
            self.logger.debug(f"开始数据分析，原始数据形状: {df.shape}")
            
            # 确保数据按日期排序
            df = df.sort_index()
            self.logger.debug(f"数据排序后，时间范围: {df.index[0]} 到 {df.index[-1]}")
            
            # 计算每日涨跌
            df['price_change'] = df['Close'].pct_change()
            self.logger.debug(f"计算价格变化完成，前10个变化值: {df['price_change'].head(10).tolist()}")
            
            # 统计有效数据
            valid_changes = df['price_change'].dropna()
            self.logger.debug(f"有效价格变化数据: {len(valid_changes)} 条")
            
            # 遍历数据，寻找连续三天上涨的情况
            self.logger.debug(f"开始遍历数据寻找连续三天上涨，从索引3开始到{len(df)}")
            
            for i in range(3, len(df)):
                current_date = df.index[i].strftime('%Y%m%d')
                
                # 只在当前检查日期生成信号（策略应该只在当天产生信号）
                if current_date == end_date:  # end_date是当前检查的日期
                    self.logger.debug(f"检查日期 {current_date} (索引 {i})")
                    
                    # 检查前三天是否连续上涨
                    prev_3_changes = df['price_change'].iloc[i-2:i+1]
                    self.logger.debug(f"前三天变化: {prev_3_changes.tolist()}")
                    
                    # 检查是否有NaN值
                    if prev_3_changes.isna().any():
                        self.logger.debug(f"跳过 {current_date}，包含NaN值")
                        continue
                    
                    if len(prev_3_changes) == 3 and all(change > 0 for change in prev_3_changes):
                        # 连续三天上涨，生成买入信号
                        buy_price = float(df['Close'].iloc[i])
                        
                        signal = {
                            "date": current_date,
                            "price": round(buy_price, 2),
                            "volume": 1000,
                            "reason": f"连续三天上涨买入信号 (涨幅: {prev_3_changes.iloc[0]:.2%}, {prev_3_changes.iloc[1]:.2%}, {prev_3_changes.iloc[2]:.2%})",
                            "strategy": "three_days_up",
                            "three_day_changes": [float(x) for x in prev_3_changes]
                        }
                        
                        signals.append(signal)
                        self.logger.info(f"✅ 发现连续三天上涨买入信号: {current_date}, 价格: {buy_price:.2f}, 涨幅: {[f'{x:.2%}' for x in prev_3_changes]}")
                    else:
                        self.logger.debug(f"❌ {current_date} 不满足连续三天上涨条件")
                else:
                    self.logger.debug(f"跳过 {current_date}，不在回测期间内 ({start_date} - {end_date})")
            
            self.logger.info(f"数据分析完成，发现 {len(signals)} 个连续三天上涨的买入机会")
                    
        except Exception as e:
            self.logger.error(f"执行连续三天上涨策略时发生错误: {str(e)}")
            raise
        
        self.logger.debug(f"连续三天上涨策略生成 {len(signals)} 个信号: {signals}")
        return signals