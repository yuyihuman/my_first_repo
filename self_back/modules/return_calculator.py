#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收益率计算模块

根据股票代码、买入时间、卖出时间计算收益率
使用xtdata获取股票1d周期的行情数据
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import setup_logger

try:
    from xtquant import xtdata
except ImportError:
    xtdata = None

class ReturnCalculator:
    """
    收益率计算器类
    
    提供各种收益率计算功能
    """
    
    def __init__(self):
        """
        初始化收益率计算器
        """
        self.logger = setup_logger('return_calculator', 'return_calculator.log')
        self.logger.info("收益率计算模块初始化")
        
        # 检查xtdata是否可用
        if xtdata is None:
            self.logger.error("xtdata模块未安装，无法获取真实数据")
            raise ImportError("xtdata模块未安装，项目只支持真实数据")
        else:
            self.logger.info("xtdata模块已加载")
        
        self.logger.debug("收益率计算器初始化完成")
    
    def calculate_return(self, stock_code: str, buy_date: str, sell_date: str, 
                        dividend_type: str = 'none', batch_data: dict = None, data_manager=None) -> Dict[str, Any]:
        """
        计算股票收益率
        
        Args:
            stock_code (str): 股票代码，格式如'000001.SZ'
            buy_date (str): 买入日期，格式为'YYYYMMDD'
            sell_date (str): 卖出日期，格式为'YYYYMMDD'
            dividend_type (str): 除权方式，默认为'none'
            batch_data (dict): 批量数据（可选）
            data_manager: 数据管理器（可选）
        
        Returns:
            Dict[str, Any]: 包含收益率计算结果的字典
        """
        self.logger.info(f"开始计算收益率 - 股票: {stock_code}, 买入: {buy_date}, 卖出: {sell_date}")
        self.logger.debug(f"除权方式: {dividend_type}")
        
        try:
            # 验证输入参数
            if not self._validate_inputs(stock_code, buy_date, sell_date):
                error_msg = "输入参数验证失败"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 获取股票数据
            if batch_data and data_manager:
                # 使用批量数据
                self.logger.info(f"使用批量数据计算收益率: {stock_code}")
                stock_data = data_manager.get_stock_price_series(stock_code, batch_data, 'close')
                if stock_data is None:
                    error_msg = f"无法从批量数据中获取股票 {stock_code} 的价格数据"
                    self.logger.error(error_msg)
                    return {'success': False, 'error': error_msg}
            else:
                # 使用传统方式获取数据
                data_result = self._get_stock_data(stock_code, buy_date, sell_date, dividend_type)
                if not data_result['success']:
                    self.logger.error(f"获取股票数据失败: {data_result['error']}")
                    return data_result
                
                stock_data = data_result['data']
            
            # 获取买入和卖出价格
            price_result = self._get_buy_sell_prices(stock_data, buy_date, sell_date)
            if not price_result['success']:
                self.logger.error(f"获取买卖价格失败: {price_result['error']}")
                return price_result
            
            # 在第89行之前添加价格验证
            buy_price = price_result['buy_price']
            sell_price = price_result['sell_price']
            actual_buy_date = price_result['actual_buy_date']
            actual_sell_date = price_result['actual_sell_date']
            
            # 验证价格有效性
            if buy_price <= 0:
                error_msg = f"买入价格无效: {buy_price}，股票: {stock_code}，日期: {actual_buy_date}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            if sell_price <= 0:
                error_msg = f"卖出价格无效: {sell_price}，股票: {stock_code}，日期: {actual_sell_date}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 计算收益率
            return_rate = (sell_price - buy_price) / buy_price
            
            # 计算持有天数
            buy_dt = datetime.strptime(actual_buy_date, '%Y%m%d')
            sell_dt = datetime.strptime(actual_sell_date, '%Y%m%d')
            hold_days = (sell_dt - buy_dt).days
            
            # 计算年化收益率
            annual_return = return_rate * (365 / hold_days) if hold_days > 0 else 0
            
            result = {
                'success': True,
                'stock_code': stock_code,
                'buy_date': buy_date,
                'sell_date': sell_date,
                'actual_buy_date': actual_buy_date,
                'actual_sell_date': actual_sell_date,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'return_rate': return_rate,
                'return_percentage': return_rate * 100,
                'annual_return': annual_return,
                'annual_return_percentage': annual_return * 100,
                'hold_days': hold_days,
                'dividend_type': dividend_type
            }
            
            self.logger.info(f"收益率计算完成 - 收益率: {return_rate:.4f} ({return_rate*100:.2f}%)")
            self.logger.debug(f"详细结果: {result}")
            
            return result
            
        except Exception as e:
            error_msg = f"计算收益率时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def _validate_inputs(self, stock_code: str, buy_date: str, sell_date: str) -> bool:
        """
        验证输入参数
        
        Args:
            stock_code (str): 股票代码
            buy_date (str): 买入日期
            sell_date (str): 卖出日期
        
        Returns:
            bool: 验证是否通过
        """
        self.logger.debug(f"验证输入参数: {stock_code}, {buy_date}, {sell_date}")
        
        # 验证股票代码格式
        if not stock_code or '.' not in stock_code:
            self.logger.error(f"股票代码格式错误: {stock_code}")
            return False
        
        code, market = stock_code.split('.')
        if len(code) != 6 or not code.isdigit() or market not in ['SH', 'SZ']:
            self.logger.error(f"股票代码格式错误: {stock_code}")
            return False
        
        # 验证日期格式
        try:
            buy_dt = datetime.strptime(buy_date, '%Y%m%d')
            sell_dt = datetime.strptime(sell_date, '%Y%m%d')
        except ValueError as e:
            self.logger.error(f"日期格式错误: {e}")
            return False
        
        # 验证日期逻辑
        if buy_dt >= sell_dt:
            self.logger.error(f"买入日期必须早于卖出日期: {buy_date} >= {sell_date}")
            return False
        
        self.logger.debug("输入参数验证通过")
        return True
    
    def _get_stock_data(self, stock_code: str, start_date: str, end_date: str, 
                       dividend_type: str) -> Dict[str, Any]:
        """
        获取股票数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            dividend_type (str): 除权方式
        
        Returns:
            Dict[str, Any]: 包含股票数据的结果字典
        """
        self.logger.info(f"获取股票数据: {stock_code}, {start_date} - {end_date}")
        
        try:
            # 使用xtdata获取真实数据
            self.logger.info("使用xtdata获取真实数据")
            return self._get_real_data(stock_code, start_date, end_date, dividend_type)
                
        except Exception as e:
            error_msg = f"获取股票数据失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def _get_real_data(self, stock_code: str, start_date: str, end_date: str, 
                      dividend_type: str) -> Dict[str, Any]:
        """
        使用xtdata获取真实股票数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            dividend_type (str): 除权方式
        
        Returns:
            Dict[str, Any]: 包含股票数据的结果字典
        """
        self.logger.info(f"调用xtdata获取数据: {stock_code}")
        
        try:
            # 先尝试下载数据
            self.logger.debug(f"下载历史数据: {stock_code}")
            xtdata.download_history_data(stock_code, '1d', start_date, end_date)
            
            # 获取数据
            self.logger.debug(f"获取市场数据: {stock_code}")
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=end_date,
                dividend_type=dividend_type,
                fill_data=True
            )
            
            if not data or 'close' not in data:
                error_msg = "未获取到有效的股票数据"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            close_data = data['close']
            if close_data.empty or stock_code not in close_data.index:
                error_msg = f"股票 {stock_code} 无收盘价数据"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 转换为Series，便于后续处理
            stock_series = close_data.loc[stock_code]
            
            self.logger.info(f"成功获取 {len(stock_series)} 条数据")
            self.logger.debug(f"数据时间范围: {stock_series.index[0]} - {stock_series.index[-1]}")
            
            return {
                'success': True,
                'data': stock_series,
                'data_source': 'xtdata'
            }
            
        except Exception as e:
            error_msg = f"xtdata获取数据失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    

    
    def _get_buy_sell_prices(self, stock_data: pd.Series, buy_date: str, sell_date: str) -> Dict[str, Any]:
        """
        从股票数据中获取买入和卖出价格
        
        Args:
            stock_data (pd.Series): 股票价格数据
            buy_date (str): 买入日期
            sell_date (str): 卖出日期
        
        Returns:
            Dict[str, Any]: 包含买卖价格的结果字典
        """
        self.logger.debug(f"获取买卖价格: {buy_date}, {sell_date}")
        
        try:
            # 查找最接近的买入日期
            buy_price, actual_buy_date = self._find_closest_price(stock_data, buy_date, 'buy')
            if buy_price is None:
                error_msg = f"无法找到买入日期 {buy_date} 附近的价格数据"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 查找最接近的卖出日期
            sell_price, actual_sell_date = self._find_closest_price(stock_data, sell_date, 'sell')
            if sell_price is None:
                error_msg = f"无法找到卖出日期 {sell_date} 附近的价格数据"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            self.logger.info(f"买入价格: {buy_price:.2f} ({actual_buy_date}), 卖出价格: {sell_price:.2f} ({actual_sell_date})")
            
            return {
                'success': True,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'actual_buy_date': actual_buy_date,
                'actual_sell_date': actual_sell_date
            }
            
        except Exception as e:
            error_msg = f"获取买卖价格失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def _find_closest_price(self, stock_data: pd.Series, target_date: str, operation: str) -> Tuple[Optional[float], Optional[str]]:
        """
        查找最接近目标日期的价格
        
        Args:
            stock_data (pd.Series): 股票价格数据
            target_date (str): 目标日期
            operation (str): 操作类型（'buy' 或 'sell'）
        
        Returns:
            Tuple[Optional[float], Optional[str]]: (价格, 实际日期)
        """
        self.logger.debug(f"查找最接近价格: {target_date}, 操作: {operation}")
        
        # 如果目标日期存在，直接返回
        if target_date in stock_data.index:
            price = stock_data[target_date]
            self.logger.debug(f"找到精确日期 {target_date}: {price:.2f}")
            return price, target_date
        
        # 查找最接近的日期
        available_dates = stock_data.index.tolist()
        available_dates.sort()
        
        if operation == 'buy':
            # 买入：查找目标日期之后的第一个交易日
            for date in available_dates:
                if date >= target_date:
                    price = stock_data[date]
                    self.logger.debug(f"买入找到最近日期 {date}: {price:.2f}")
                    return price, date
        else:
            # 卖出：查找目标日期之前的最后一个交易日
            for date in reversed(available_dates):
                if date <= target_date:
                    price = stock_data[date]
                    self.logger.debug(f"卖出找到最近日期 {date}: {price:.2f}")
                    return price, date
        
        self.logger.warning(f"未找到 {operation} 操作的合适日期")
        return None, None
    
    def calculate_batch_returns(self, trades: list, batch_data: dict = None, data_manager=None) -> Dict[str, Any]:
        """
        批量计算多笔交易的收益率
        
        Args:
            trades (list): 交易列表，每个元素包含股票代码、买入日期、卖出日期
            batch_data (dict): 批量数据（可选）
            data_manager: 数据管理器（可选）
        
        Returns:
            Dict[str, Any]: 批量计算结果
        """
        self.logger.info(f"开始批量计算收益率，共 {len(trades)} 笔交易")
        
        results = []
        total_return = 0
        successful_trades = 0
        
        for i, trade in enumerate(trades):
            self.logger.debug(f"处理第 {i+1} 笔交易: {trade}")
            
            try:
                result = self.calculate_return(
                    stock_code=trade['stock_code'],
                    buy_date=trade['buy_date'],
                    sell_date=trade['sell_date'],
                    dividend_type=trade.get('dividend_type', 'none'),
                    batch_data=batch_data,
                    data_manager=data_manager
                )
                
                results.append(result)
                
                if result['success']:
                    total_return += result['return_rate']
                    successful_trades += 1
                    
            except Exception as e:
                self.logger.error(f"第 {i+1} 笔交易计算失败: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'trade_index': i
                })
        
        # 计算平均收益率
        avg_return = total_return / successful_trades if successful_trades > 0 else 0
        
        summary = {
            'total_trades': len(trades),
            'successful_trades': successful_trades,
            'failed_trades': len(trades) - successful_trades,
            'total_return': total_return,
            'average_return': avg_return,
            'average_return_percentage': avg_return * 100
        }
        
        self.logger.info(f"批量计算完成 - 成功: {successful_trades}/{len(trades)}, 平均收益率: {avg_return:.4f}")
        
        return {
            'success': True,
            'results': results,
            'summary': summary
        }