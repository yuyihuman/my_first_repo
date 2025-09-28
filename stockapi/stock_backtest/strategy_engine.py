# coding:utf-8
"""
策略执行模块 - 独立的策略条件检查逻辑

策略条件：
1、开盘高开3%以上，收盘下跌3%以上
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


class HighOpenLowCloseCondition(StrategyCondition):
    """高开低收条件：开盘高开3%以上，收盘下跌3%以上"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        # 需要至少前1个交易日的数据来计算高开
        if current_idx < 1:
            return False
        
        current_data = df.iloc[current_idx]
        prev_data = df.iloc[current_idx - 1]
        
        current_open = current_data['open']
        current_close = current_data['close']
        prev_close = prev_data['close']
        
        # 检查开盘高开3%以上（相对于上一日收盘价）
        open_change_pct = (current_open - prev_close) / prev_close * 100
        high_open = open_change_pct >= 3.0
        
        # 检查收盘下跌3%以上（相对于上一日收盘价）
        close_change_pct = (current_close - prev_close) / prev_close * 100
        low_close = close_change_pct <= -3.0
        
        return high_open and low_close
    
    def get_description(self) -> str:
        return "开盘高开3%以上，收盘下跌3%以上"


class PriceAboveOneCondition(StrategyCondition):
    """价格大于1条件：股票价格必须大于1"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        current_data = df.iloc[current_idx]
        current_close = current_data['close']
        
        # 检查收盘价是否大于1
        return current_close > 1.0
    
    def get_description(self) -> str:
        return "股票价格必须大于1"


class VolumeDoubleCondition(StrategyCondition):
    """成交量翻倍条件：当日成交量大于上一日成交量2倍以上"""
    
    def check(self, df: pd.DataFrame, current_idx: int, **kwargs) -> bool:
        # 需要至少前1个交易日的数据来比较成交量
        if current_idx < 1:
            return False
        
        current_data = df.iloc[current_idx]
        prev_data = df.iloc[current_idx - 1]
        
        current_volume = current_data['volume']
        prev_volume = prev_data['volume']
        
        # 检查前一日成交量是否为0，避免除零错误
        if prev_volume <= 0:
            return False
        
        # 检查当日成交量是否大于上一日成交量的2倍
        volume_ratio = current_volume / prev_volume
        return volume_ratio > 2.0
    
    def get_description(self) -> str:
        return "当日成交量大于上一日成交量2倍以上"


class StrategyEngine:
    """策略执行引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conditions = [
            HighOpenLowCloseCondition(),
            PriceAboveOneCondition(),
            VolumeDoubleCondition()
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
        # 需要至少前1个交易日的数据
        if current_idx < 1:
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
        # 需要至少前1个交易日的数据
        if current_idx < 1:
            if verbose:
                self.logger.info(f"股票 {stock_code} 索引 {current_idx}: 数据不足，需要至少前1个交易日数据")
            return False, {"error": "数据不足"}
        
        current_date = df.iloc[current_idx]['datetime'].strftime('%Y-%m-%d')
        current_data = df.iloc[current_idx]
        prev_data = df.iloc[current_idx - 1]
        
        if verbose:
            self.logger.info(f"\n=== 股票 {stock_code} 日期 {current_date} 策略条件检查 ===")
            self.logger.info(f"前日收盘价: {prev_data['close']:.4f}")
            self.logger.info(f"当日价格信息:")
            self.logger.info(f"  开盘价: {current_data['open']:.4f}")
            self.logger.info(f"  收盘价: {current_data['close']:.4f}")
            self.logger.info(f"  最高价: {current_data['high']:.4f}")
            self.logger.info(f"  最低价: {current_data['low']:.4f}")
            
            # 计算变化幅度
            open_change_pct = (current_data['open'] - prev_data['close']) / prev_data['close'] * 100
            close_change_pct = (current_data['close'] - current_data['open']) / current_data['open'] * 100
            self.logger.info(f"  开盘涨幅: {open_change_pct:.2f}%")
            self.logger.info(f"  收盘跌幅: {close_change_pct:.2f}%")
        
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
            start_idx = 1  # 至少需要前1个交易日数据
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
                next_intraday_change_pct = None  # 次日收盘价相对于次日开盘价的变化
                
                # 计算次日数据（如果有次日数据）
                if idx + 1 < len(df):
                    next_day_data = df.iloc[idx + 1]
                    next_open = next_day_data['open']
                    next_day_close = next_day_data['close']
                    next_day_return = (next_day_close - current_close) / current_close * 100
                    next_open_change_pct = (next_open - current_close) / current_close * 100
                    next_close_change_pct = (next_day_close - current_close) / current_close * 100
                    next_intraday_change_pct = (next_day_close - next_open) / next_open * 100 if next_open != 0 else None
                
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
                
                # 基于次日收盘价的3日、5日、10日涨跌幅计算
                day3_from_next_change_pct = None
                day5_from_next_change_pct = None
                day10_from_next_change_pct = None
                
                if next_day_close is not None:
                    if idx + 3 < len(df):
                        day3_from_next_change_pct = (day3_close - next_day_close) / next_day_close * 100 if day3_close is not None else None
                    
                    if idx + 5 < len(df):
                        day5_from_next_change_pct = (day5_close - next_day_close) / next_day_close * 100 if day5_close is not None else None
                    
                    if idx + 10 < len(df):
                        day10_from_next_change_pct = (day10_close - next_day_close) / next_day_close * 100 if day10_close is not None else None
                
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
                    "next_intraday_change_pct": next_intraday_change_pct,
                    "day3_close": day3_close,
                    "day3_change_pct": day3_change_pct,
                    "day5_close": day5_close,
                    "day5_change_pct": day5_change_pct,
                    "day10_close": day10_close,
                    "day10_change_pct": day10_change_pct,
                    "day3_from_next_change_pct": day3_from_next_change_pct,
                    "day5_from_next_change_pct": day5_from_next_change_pct,
                    "day10_from_next_change_pct": day10_from_next_change_pct
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