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
        # 注册10分钟快速上涨策略
        self.register_strategy("rapid_rise_10min", self._rapid_rise_10min_strategy)
        
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
                                  batch_data: dict = None, data_manager=None, multi_period_data: dict = None, 
                                  **kwargs) -> List[Dict[str, Any]]:
        """
        使用批量数据执行买入策略（支持多周期数据）
        
        Args:
            strategy_name (str): 策略名称
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            batch_data (dict): 批量数据（向后兼容，优先使用multi_period_data）
            data_manager: 数据管理器实例
            multi_period_data (dict): 多周期数据
            **kwargs: 策略参数
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表
        """
        self.logger.info(f"使用数据执行买入策略: {strategy_name}, 股票: {stock_code}")
        
        try:
            if strategy_name in self.strategies:
                # 传递数据给策略函数
                if multi_period_data:
                    kwargs['multi_period_data'] = multi_period_data
                    kwargs['batch_data'] = batch_data  # 保持向后兼容
                    self.logger.debug(f"使用多周期数据，可用周期: {list(multi_period_data.get('data', {}).keys())}")
                else:
                    kwargs['batch_data'] = batch_data
                    self.logger.debug("使用单周期批量数据")
                
                kwargs['data_manager'] = data_manager
                
                signals = self.strategies[strategy_name](stock_code, start_date, end_date, **kwargs)
                self.logger.info(f"买入策略执行完成，生成 {len(signals)} 个买入信号")
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
        
        # 检查数据来源
        multi_period_data = kwargs.get('multi_period_data')
        batch_data = kwargs.get('batch_data')
        data_manager = kwargs.get('data_manager')
        
        # 优先使用多周期数据，回退到批量数据
        if multi_period_data and data_manager:
            # 使用多周期数据（默认使用1d数据进行分析）
            self.logger.info(f"使用多周期数据进行策略分析: {stock_code}")
            available_periods = list(multi_period_data.get('data', {}).keys())
            self.logger.debug(f"可用周期: {available_periods}")
            
            # 优先使用1d数据，如果没有则使用第一个可用周期
            period_to_use = '1d' if '1d' in available_periods else (available_periods[0] if available_periods else None)
            
            if period_to_use:
                self.logger.debug(f"使用周期: {period_to_use}")
                df = data_manager.get_stock_dataframe_from_multi_period(
                    stock_code=stock_code,
                    multi_period_data=multi_period_data,
                    period=period_to_use,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                self.logger.warning(f"多周期数据中没有可用的数据周期")
                df = None
                
        elif batch_data and data_manager:
            # 使用批量数据
            self.logger.info(f"使用批量数据进行策略分析: {stock_code}")
            self.logger.debug(f"批量数据键: {list(batch_data.keys()) if batch_data else 'None'}")
            
            df = data_manager.get_stock_dataframe(stock_code, batch_data, start_date, end_date)
        else:
            df = None
            
        if df is None:
            self.logger.warning(f"无法获取股票 {stock_code} 的数据 - DataFrame为None")
        elif df.empty:
            self.logger.warning(f"无法获取股票 {stock_code} 的数据 - DataFrame为空")
        else:
            self.logger.debug(f"成功获取 {len(df)} 条数据，时间范围: {df.index[0]} 到 {df.index[-1]}")
            self.logger.debug(f"数据列: {df.columns.tolist()}")
            self.logger.debug(f"前5行数据:\n{df.head()}")
            
        # 如果没有获取到数据，尝试传统方式
        if df is None or df.empty:
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
    
    def _rapid_rise_10min_strategy(self, stock_code: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        10分钟快速上涨买入策略：当股价在10分钟内上涨超过指定百分比时买入
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            **kwargs: 策略参数
                - rise_threshold (float): 上涨阈值，默认为0.03（3%）
                - time_window_minutes (int): 时间窗口（分钟），默认为10分钟
                - multi_period_data: 多周期数据（可选）
                - data_manager: 数据管理器（可选）
        
        Returns:
            List[Dict[str, Any]]: 买入信号列表
        """
        self.logger.info(f"执行10分钟快速上涨买入策略，股票: {stock_code}")
        
        # 获取策略参数
        rise_threshold = kwargs.get('rise_threshold', 0.03)  # 默认3%
        time_window_minutes = kwargs.get('time_window_minutes', 10)  # 默认10分钟
        
        self.logger.debug(f"策略参数 - 上涨阈值: {rise_threshold:.1%}, 时间窗口: {time_window_minutes}分钟")
        
        signals = []
        
        from datetime import datetime, timedelta
        import pandas as pd
        
        # 检查数据来源
        multi_period_data = kwargs.get('multi_period_data')
        batch_data = kwargs.get('batch_data')
        data_manager = kwargs.get('data_manager')
        
        # 优先使用多周期数据中的分钟线数据
        if multi_period_data and data_manager:
            self.logger.info(f"使用多周期数据进行策略分析: {stock_code}")
            available_periods = list(multi_period_data.get('data', {}).keys())
            self.logger.debug(f"可用周期: {available_periods}")
            
            # 优先使用1m数据，如果没有则使用1d数据（虽然不太适合10分钟策略）
            period_to_use = '1m' if '1m' in available_periods else ('1d' if '1d' in available_periods else None)
            
            if period_to_use:
                self.logger.debug(f"使用周期: {period_to_use}")
                df = data_manager.get_stock_dataframe_from_multi_period(
                    stock_code=stock_code,
                    multi_period_data=multi_period_data,
                    period=period_to_use,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if period_to_use == '1d':
                    self.logger.warning("使用日线数据进行10分钟策略分析，精度可能不够")
            else:
                self.logger.warning(f"多周期数据中没有可用的数据周期")
                df = None
                
        elif batch_data and data_manager:
            # 使用批量数据（通常是日线数据）
            self.logger.info(f"使用批量数据进行策略分析: {stock_code}")
            self.logger.warning("使用日线数据进行10分钟策略分析，精度可能不够")
            df = data_manager.get_stock_dataframe(stock_code, batch_data, start_date, end_date)
        else:
            df = None
            
        if df is None:
            self.logger.warning(f"无法获取股票 {stock_code} 的数据 - DataFrame为None")
        elif df.empty:
            self.logger.warning(f"无法获取股票 {stock_code} 的数据 - DataFrame为空")
        else:
            self.logger.debug(f"成功获取 {len(df)} 条数据，时间范围: {df.index[0]} 到 {df.index[-1]}")
            self.logger.debug(f"数据列: {df.columns.tolist()}")
            
        # 如果没有获取到数据，尝试传统方式获取分钟线数据
        if df is None or df.empty:
            self.logger.info(f"使用传统方式获取分钟线数据: {stock_code}")
            try:
                from xtquant import xtdata
            except ImportError:
                xtdata = None
                
            if xtdata is None:
                self.logger.error("xtdata模块未安装，无法获取真实数据")
                raise ImportError("xtdata模块未安装，项目只支持真实数据")
            
            # 获取分钟线数据
            self.logger.debug(f"获取股票分钟线数据: {stock_code}, 时间范围: {start_date} - {end_date}")
            
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock_code],
                period='1m',  # 使用1分钟数据
                start_time=start_date,
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
                df.index = pd.to_datetime(df.index, format='%Y%m%d %H%M%S')
                df.index.name = 'DateTime'
                
                self.logger.debug(f"成功获取 {len(df)} 条分钟线数据")
            else:
                self.logger.error(f"无法获取股票 {stock_code} 的分钟线数据")
                return signals
        
        # 统一的数据分析逻辑
        try:
            self.logger.debug(f"开始数据分析，原始数据形状: {df.shape}")
            
            # 确保数据按时间排序
            df = df.sort_index()
            self.logger.debug(f"数据排序后，时间范围: {df.index[0]} 到 {df.index[-1]}")
            
            # 根据数据类型确定时间窗口
            if 'DateTime' in str(df.index.name) or len(df) > 1000:  # 分钟线数据
                # 分钟线数据：直接使用时间窗口
                window_size = time_window_minutes
                self.logger.debug(f"使用分钟线数据，时间窗口: {window_size}分钟")
            else:
                # 日线数据：模拟处理（不太准确，但可以作为备选）
                window_size = max(1, time_window_minutes // (6.5 * 60))  # 假设一个交易日6.5小时
                self.logger.debug(f"使用日线数据模拟，时间窗口: {window_size}天")
            
            # 遍历数据，寻找快速上涨的情况
            self.logger.debug(f"开始遍历数据寻找快速上涨，窗口大小: {window_size}")
            
            for i in range(window_size, len(df)):
                current_time = df.index[i]
                current_date = current_time.strftime('%Y%m%d')
                
                # 只在当前检查日期生成信号
                if current_date == end_date:
                    self.logger.debug(f"检查时间 {current_time} (索引 {i})")
                    
                    # 获取时间窗口内的价格数据
                    window_start_idx = i - window_size
                    window_data = df.iloc[window_start_idx:i+1]
                    
                    if len(window_data) < 2:
                        continue
                    
                    # 计算时间窗口内的最大涨幅
                    start_price = window_data['Close'].iloc[0]
                    end_price = window_data['Close'].iloc[-1]
                    max_price = window_data['Close'].max()
                    
                    # 计算涨幅
                    rise_rate = (max_price - start_price) / start_price
                    current_rise_rate = (end_price - start_price) / start_price
                    
                    self.logger.debug(f"时间窗口 {window_data.index[0]} - {window_data.index[-1]}")
                    self.logger.debug(f"起始价格: {start_price:.2f}, 结束价格: {end_price:.2f}, 最高价格: {max_price:.2f}")
                    self.logger.debug(f"最大涨幅: {rise_rate:.2%}, 当前涨幅: {current_rise_rate:.2%}")
                    
                    # 检查是否满足快速上涨条件
                    if rise_rate >= rise_threshold:
                        # 快速上涨，生成买入信号
                        buy_price = float(end_price)
                        
                        signal = {
                            "date": current_date,
                            "time": current_time.strftime('%H:%M:%S') if hasattr(current_time, 'hour') else '15:00:00',
                            "price": round(buy_price, 2),
                            "volume": 1000,
                            "reason": f"10分钟快速上涨买入信号 (涨幅: {rise_rate:.2%}, 阈值: {rise_threshold:.2%})",
                            "strategy": "rapid_rise_10min",
                            "rise_rate": float(rise_rate),
                            "time_window_minutes": time_window_minutes,
                            "start_price": float(start_price),
                            "max_price": float(max_price)
                        }
                        
                        signals.append(signal)
                        self.logger.info(f"✅ 发现10分钟快速上涨买入信号: {current_time}, 价格: {buy_price:.2f}, 涨幅: {rise_rate:.2%}")
                    else:
                        self.logger.debug(f"❌ {current_time} 不满足快速上涨条件 (涨幅: {rise_rate:.2%} < 阈值: {rise_threshold:.2%})")
                else:
                    self.logger.debug(f"跳过 {current_date}，不在回测期间内 ({start_date} - {end_date})")
            
            self.logger.info(f"数据分析完成，发现 {len(signals)} 个快速上涨的买入机会")
                    
        except Exception as e:
            self.logger.error(f"执行10分钟快速上涨策略时发生错误: {str(e)}")
            raise
        
        self.logger.debug(f"10分钟快速上涨策略生成 {len(signals)} 个信号: {signals}")
        return signals