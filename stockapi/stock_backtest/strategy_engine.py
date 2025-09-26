# coding:utf-8
"""
策略执行模块 - 独立的策略条件检查逻辑

策略条件：
1、股票价格必须大于1（最低价和收盘价都必须大于1）
2、前面10个交易日20，30，60日均线都是逐渐升高的
3、前面三个交易日中每天的收盘价在20日均线正负1%范围内或者30日均线正负1%范围内
4、当日是阳线，并且收盘价高于前面三个交易日的最高价
5、当日成交量小于之前一个交易日10日成交量均值的1.5倍
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod


class StrategyCondition(ABC):
    """策略条件基类"""
    
    @abstractmethod
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        """
        检查策略条件
        
        Args:
            df: 股票数据
            current_idx: 当前日期索引
            **kwargs: 其他参数
            
        Returns:
            bool: 是否满足条件
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取条件描述"""
        pass


class PriceCondition(StrategyCondition):
    """价格条件：股票价格必须大于1"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        current_data = df.iloc[current_idx]
        close_price = current_data['close']
        low_price = current_data['low']
        
        return close_price > 1 and low_price > 1
    
    def get_description(self) -> str:
        return "股票价格必须大于1（最低价和收盘价都必须大于1）"


class MovingAverageUpwardCondition(StrategyCondition):
    """均线上升条件：前面10个交易日20，30，60日均线都是逐渐升高的"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        # 需要至少前10个交易日的数据
        if current_idx < 10:
            return False
        
        for i in range(1, 11):  # 检查前1到前10个交易日
            if current_idx - i < 0:
                return False
            
            current_day = df.iloc[current_idx - i + 1] if i > 1 else df.iloc[current_idx]
            prev_day = df.iloc[current_idx - i]
            
            # 检查20日均线
            current_ma20 = current_day['ma20'] if 'ma20' in current_day and not pd.isna(current_day['ma20']) else None
            prev_ma20 = prev_day['ma20'] if 'ma20' in prev_day and not pd.isna(prev_day['ma20']) else None
            
            # 检查30日均线
            current_ma30 = current_day['ma30'] if 'ma30' in current_day and not pd.isna(current_day['ma30']) else None
            prev_ma30 = prev_day['ma30'] if 'ma30' in prev_day and not pd.isna(prev_day['ma30']) else None
            
            # 检查60日均线
            current_ma60 = current_day['ma60'] if 'ma60' in current_day and not pd.isna(current_day['ma60']) else None
            prev_ma60 = prev_day['ma60'] if 'ma60' in prev_day and not pd.isna(prev_day['ma60']) else None
            
            # 如果任何一个均线数据缺失或不是上升的，则条件不满足
            if (current_ma20 is None or prev_ma20 is None or current_ma20 <= prev_ma20 or
                current_ma30 is None or prev_ma30 is None or current_ma30 <= prev_ma30 or
                current_ma60 is None or prev_ma60 is None or current_ma60 <= prev_ma60):
                return False
        
        return True
    
    def get_description(self) -> str:
        return "前面10个交易日20，30，60日均线都是逐渐升高的"


class ClosePriceNearMACondition(StrategyCondition):
    """收盘价接近均线条件：前面三个交易日中每天的收盘价在20日均线正负1%范围内或者30日均线正负1%范围内"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        for i in range(1, 4):  # 检查前1、2、3个交易日
            if current_idx - i < 0:
                return False
            
            day_data = df.iloc[current_idx - i]
            day_close = day_data['close']
            day_ma20 = day_data['ma20'] if 'ma20' in day_data and not pd.isna(day_data['ma20']) else None
            day_ma30 = day_data['ma30'] if 'ma30' in day_data and not pd.isna(day_data['ma30']) else None
            
            # 检查是否在20日均线正负1%范围内
            in_ma20_range = False
            if day_ma20 is not None and day_ma20 > 0:
                ma20_diff_percent = abs(day_close - day_ma20) / day_ma20
                in_ma20_range = ma20_diff_percent <= 0.01
            
            # 检查是否在30日均线正负1%范围内
            in_ma30_range = False
            if day_ma30 is not None and day_ma30 > 0:
                ma30_diff_percent = abs(day_close - day_ma30) / day_ma30
                in_ma30_range = ma30_diff_percent <= 0.01
            
            # 如果既不在20日均线范围内，也不在30日均线范围内，则条件不满足
            if not (in_ma20_range or in_ma30_range):
                return False
        
        return True
    
    def get_description(self) -> str:
        return "前面三个交易日中每天的收盘价在20日均线正负1%范围内或者30日均线正负1%范围内"


class PositiveLineAndHigherCloseCondition(StrategyCondition):
    """阳线且收盘价更高条件：当日是阳线，并且收盘价高于前面三个交易日的最高价"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        current_data = df.iloc[current_idx]
        open_price = current_data['open']
        close_price = current_data['close']
        
        # 检查是否是阳线
        is_positive_line = close_price > open_price
        
        # 获取前面三个交易日的最高价
        if is_positive_line and current_idx >= 3:
            prev_3days_high_prices = []
            for i in range(1, 4):  # 前1、2、3个交易日
                if current_idx - i >= 0:
                    prev_3days_high_prices.append(df.iloc[current_idx - i]['high'])
            
            if prev_3days_high_prices:
                max_prev_3days_high = max(prev_3days_high_prices)
                return close_price > max_prev_3days_high
        
        return False
    
    def get_description(self) -> str:
        return "当日是阳线，并且收盘价高于前面三个交易日的最高价"


class VolumeCondition(StrategyCondition):
    """成交量条件：当日成交量小于之前一个交易日10日成交量均值的1.5倍"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        current_data = df.iloc[current_idx]
        prev_data = df.iloc[current_idx - 1] if current_idx > 0 else None
        
        if prev_data is None:
            return False
        
        volume = current_data['volume'] if 'volume' in current_data and not pd.isna(current_data['volume']) else None
        prev_vol10 = prev_data['vol10'] if 'vol10' in prev_data and not pd.isna(prev_data['vol10']) else None
        
        if volume is not None and prev_vol10 is not None and prev_vol10 > 0:
            return volume < prev_vol10 * 1.5
        
        return False
    
    def get_description(self) -> str:
        return "当日成交量小于之前一个交易日10日成交量均值的1.5倍"


class StrategyEngine:
    """策略执行引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conditions = [
            PriceCondition(),
            MovingAverageUpwardCondition(),
            ClosePriceNearMACondition(),
            PositiveLineAndHigherCloseCondition(),
            VolumeCondition()
        ]
    
    def get_strategy_description(self) -> str:
        """
        获取完整的策略条件描述
        
        Returns:
            str: 格式化的策略条件描述
        """
        description_lines = ["策略条件："]
        for i, condition in enumerate(self.conditions, 1):
            description_lines.append(f"{i}、{condition.get_description()}")
        
        return "\n".join(description_lines)
    
    def check_strategy_conditions(self, df: pd.DataFrame, current_idx: int) -> bool:
        """
        检查当前日期是否符合策略条件
        
        Args:
            df: 股票数据DataFrame
            current_idx: 当前日期的索引
        
        Returns:
            bool: 是否符合条件
        """
        # 需要至少前10个交易日的数据
        if current_idx < 10:
            return False
        
        # 检查所有条件
        for condition in self.conditions:
            if not condition.check(df, current_idx):
                return False
        
        return True
    
    def check_strategy_conditions_verbose(self, df: pd.DataFrame, current_idx: int, 
                                        stock_code: str, verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        检查当前日期是否符合策略条件（详细版本）
        
        Args:
            df: 股票数据DataFrame
            current_idx: 当前日期的索引
            stock_code: 股票代码
            verbose: 是否打印详细信息
        
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否符合条件, 详细检查结果)
        """
        # 需要至少前10个交易日的数据
        if current_idx < 10:
            if verbose:
                self.logger.info(f"股票 {stock_code} 索引 {current_idx}: 数据不足，需要至少前10个交易日数据")
            return False, {"error": "数据不足"}
        
        current_date = df.iloc[current_idx]['datetime'].strftime('%Y-%m-%d')
        current_data = df.iloc[current_idx]
        
        if verbose:
            self.logger.info(f"\n=== 股票 {stock_code} 日期 {current_date} 策略条件检查 ===")
            self.logger.info(f"当日价格信息:")
            self.logger.info(f"  开盘价: {current_data['open']:.4f}")
            self.logger.info(f"  收盘价: {current_data['close']:.4f}")
            self.logger.info(f"  最低价: {current_data['low']:.4f}")
            self.logger.info(f"  成交量: {current_data['volume'] if 'volume' in current_data and not pd.isna(current_data['volume']) else 'N/A'}")
        
        # 检查各个条件
        condition_results = {}
        all_conditions_met = True
        
        for i, condition in enumerate(self.conditions, 1):
            condition_met = condition.check(df, current_idx)
            condition_results[f"condition_{i}"] = {
                "description": condition.get_description(),
                "result": condition_met
            }
            
            if verbose:
                self.logger.info(f"\n策略条件{i}检查: {condition.get_description()}")
                self.logger.info(f"  结果: {'✓' if condition_met else '✗'}")
            
            if not condition_met:
                all_conditions_met = False
        
        if verbose:
            self.logger.info(f"\n最终结果: {'✓' if all_conditions_met else '✗'}")
            if all_conditions_met:
                self.logger.info(f"*** 股票 {stock_code} 在 {current_date} 符合选股条件! ***")
            self.logger.info("=" * 60)
        
        return all_conditions_met, {
            "stock_code": stock_code,
            "date": current_date,
            "conditions": condition_results,
            "final_result": all_conditions_met
        }
    
    def scan_stock_for_signals(self, df: pd.DataFrame, stock_code: str, 
                             start_idx: int = None, end_idx: int = None) -> List[Dict[str, Any]]:
        """
        扫描股票数据寻找符合策略的信号
        
        Args:
            df: 股票数据
            stock_code: 股票代码
            start_idx: 开始索引
            end_idx: 结束索引
            
        Returns:
            List[Dict[str, Any]]: 符合条件的信号列表
        """
        signals = []
        
        if start_idx is None:
            start_idx = 10  # 至少需要前10个交易日数据
        if end_idx is None:
            end_idx = len(df) - 1
        
        for idx in range(start_idx, min(end_idx + 1, len(df))):
            if self.check_strategy_conditions(df, idx):
                current_data = df.iloc[idx]
                current_close = current_data['close']
                
                # 初始化次日数据
                next_day_return = None
                next_day_close = None
                next_open = None
                next_open_change_pct = None
                next_close_change_pct = None
                
                # 计算次日数据（如果有次日数据）
                if idx + 1 < len(df):
                    next_day_data = df.iloc[idx + 1]
                    next_open = next_day_data['open']
                    next_day_close = next_day_data['close']
                    next_day_return = (next_day_close - current_close) / current_close * 100
                    next_open_change_pct = (next_open - current_close) / current_close * 100
                    next_close_change_pct = (next_day_close - current_close) / current_close * 100
                
                # 计算3日、5日、10日后的数据
                day3_close = None
                day3_change_pct = None
                day5_close = None
                day5_change_pct = None
                day10_close = None
                day10_change_pct = None
                
                if idx + 3 < len(df):
                    day3_close = df.iloc[idx + 3]['close']
                    day3_change_pct = (day3_close - current_close) / current_close * 100
                
                if idx + 5 < len(df):
                    day5_close = df.iloc[idx + 5]['close']
                    day5_change_pct = (day5_close - current_close) / current_close * 100
                
                if idx + 10 < len(df):
                    day10_close = df.iloc[idx + 10]['close']
                    day10_change_pct = (day10_close - current_close) / current_close * 100
                
                signal = {
                    "stock_code": stock_code,
                    "date": current_data['datetime'].strftime('%Y-%m-%d'),
                    "open": current_data['open'],
                    "close": current_close,
                    "high": current_data['high'],
                    "low": current_data['low'],
                    "volume": current_data['volume'],
                    "next_open": next_open,
                    "next_close": next_day_close,
                    "next_day_return": next_day_return,
                    "next_open_change_pct": next_open_change_pct,
                    "next_close_change_pct": next_close_change_pct,
                    "day3_close": day3_close,
                    "day3_change_pct": day3_change_pct,
                    "day5_close": day5_close,
                    "day5_change_pct": day5_change_pct,
                    "day10_close": day10_close,
                    "day10_change_pct": day10_change_pct
                }
                
                signals.append(signal)
        
        return signals
    
    def add_custom_condition(self, condition: StrategyCondition):
        """
        添加自定义策略条件
        
        Args:
            condition: 策略条件实例
        """
        self.conditions.append(condition)
        self.logger.info(f"添加自定义策略条件: {condition.get_description()}")
    
    def remove_condition(self, condition_index: int):
        """
        移除策略条件
        
        Args:
            condition_index: 条件索引（从0开始）
        """
        if 0 <= condition_index < len(self.conditions):
            removed_condition = self.conditions.pop(condition_index)
            self.logger.info(f"移除策略条件: {removed_condition.get_description()}")
        else:
            self.logger.warning(f"无效的条件索引: {condition_index}")
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            str: 策略描述
        """
        description = "当前策略条件：\n"
        for i, condition in enumerate(self.conditions, 1):
            description += f"{i}、{condition.get_description()}\n"
        return description


class ModelBasedStrategy(StrategyEngine):
    """基于模型的策略引擎（为未来模型接入预留接口）"""
    
    def __init__(self, model=None):
        super().__init__()
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def set_model(self, model):
        """
        设置预测模型
        
        Args:
            model: 预测模型实例
        """
        self.model = model
        self.logger.info("已设置预测模型")
    
    def predict_with_model(self, df: pd.DataFrame, current_idx: int) -> Dict[str, Any]:
        """
        使用模型进行预测（预留接口）
        
        Args:
            df: 股票数据
            current_idx: 当前索引
            
        Returns:
            Dict[str, Any]: 预测结果
        """
        if self.model is None:
            return {"prediction": None, "confidence": 0.0}
        
        # 这里是模型预测的接口，具体实现取决于模型类型
        # 示例：
        # features = self.extract_features(df, current_idx)
        # prediction = self.model.predict(features)
        # confidence = self.model.predict_proba(features)
        
        return {"prediction": None, "confidence": 0.0}
    
    def check_strategy_with_model(self, df: pd.DataFrame, current_idx: int) -> Tuple[bool, Dict[str, Any]]:
        """
        结合传统策略和模型预测进行判断
        
        Args:
            df: 股票数据
            current_idx: 当前索引
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否符合条件, 详细结果)
        """
        # 首先检查传统策略条件
        traditional_result = self.check_strategy_conditions(df, current_idx)
        
        # 如果有模型，进行模型预测
        model_result = self.predict_with_model(df, current_idx)
        
        # 结合两种结果（这里可以根据需要调整逻辑）
        final_result = traditional_result  # 暂时只使用传统策略
        
        return final_result, {
            "traditional_strategy": traditional_result,
            "model_prediction": model_result,
            "final_result": final_result
        }