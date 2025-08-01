#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管理模块

负责统一管理股票数据的获取、缓存和分发
减少重复的数据获取调用，提高系统效率
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import setup_logger

try:
    from xtquant import xtdata
except ImportError:
    xtdata = None

class DataManager:
    """
    数据管理器类
    
    统一管理股票数据的获取、缓存和分发
    """
    
    def __init__(self):
        """
        初始化数据管理器
        """
        self.logger = setup_logger('data_manager', 'data_manager.log')
        self.logger.info("数据管理器初始化开始")
        
        # 检查xtdata是否可用
        if xtdata is None:
            self.logger.error("xtdata模块未安装，无法获取真实数据")
            raise ImportError("xtdata模块未安装，项目只支持真实数据")
        else:
            self.logger.info("xtdata模块已加载")
        
        # 数据缓存
        self.data_cache = {}
        
        self.logger.info("数据管理器初始化完成")
    
    def batch_download_data(self, stock_codes: List[str], start_date: str, end_date: str = None, 
                           period: str = '1d') -> Dict[str, bool]:
        """
        批量下载股票历史数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期，格式为YYYYMMDD
            end_date: 结束日期，格式为YYYYMMDD，默认为None（到当前日期）
            period: 数据周期，支持'1d'（日线）和'1m'（分钟线），默认为'1d'
        
        Returns:
            Dict[str, bool]: 每只股票的下载结果
        """
        self.logger.info(f"开始批量下载股票数据，股票数量: {len(stock_codes)}，周期: {period}")
        self.logger.info(f"时间范围: {start_date} - {end_date or '当前'}")
        
        download_results = {}
        
        try:
            # 批量下载历史数据
            for stock_code in stock_codes:
                try:
                    self.logger.debug(f"下载股票数据: {stock_code}, 周期: {period}")
                    xtdata.download_history_data(
                        stock_code, 
                        period=period, 
                        start_time=start_date,
                        end_time=end_date
                    )
                    download_results[stock_code] = True
                    self.logger.debug(f"股票 {stock_code} {period}数据下载完成")
                except Exception as e:
                    self.logger.error(f"下载股票 {stock_code} {period}数据失败: {str(e)}")
                    download_results[stock_code] = False
            
            success_count = sum(download_results.values())
            self.logger.info(f"批量下载完成，成功: {success_count}/{len(stock_codes)}")
            
            return download_results
            
        except Exception as e:
            self.logger.error(f"批量下载数据失败: {str(e)}", exc_info=True)
            return {code: False for code in stock_codes}
    
    def batch_get_data(self, stock_codes: List[str], start_date: str, end_date: str = None, 
                      fields: List[str] = None, period: str = '1d') -> Dict[str, Any]:
        """
        批量获取股票数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期，格式为YYYYMMDD
            end_date: 结束日期，格式为YYYYMMDD，默认为None（到当前日期）
            fields: 数据字段列表，默认为['open', 'high', 'low', 'close', 'volume']
            period: 数据周期，支持'1d'（日线）和'1m'（分钟线），默认为'1d'
        
        Returns:
            Dict[str, Any]: 包含所有股票数据的字典
        """
        if fields is None:
            fields = ['open', 'high', 'low', 'close', 'volume']
        
        self.logger.info(f"开始批量获取股票数据，股票数量: {len(stock_codes)}，周期: {period}")
        self.logger.info(f"时间范围: {start_date} - {end_date or '当前'}")
        self.logger.debug(f"数据字段: {fields}")
        
        try:
            # 使用xtdata一次性获取所有股票数据
            data = xtdata.get_market_data(
                field_list=fields,
                stock_list=stock_codes,
                period=period,
                start_time=start_date,
                end_time=end_date,
                dividend_type='none',
                fill_data=True
            )
            
            if data and all(field in data for field in fields):
                self.logger.info(f"成功获取批量{period}数据，字段数: {len(fields)}")
                
                # 缓存数据（包含周期信息）
                cache_key = f"{'-'.join(stock_codes)}_{start_date}_{end_date}_{'-'.join(fields)}_{period}"
                self.data_cache[cache_key] = {
                    'data': data,
                    'period': period,
                    'fields': fields,
                    'stock_codes': stock_codes,
                    'start_date': start_date,
                    'end_date': end_date
                }
                
                return {
                    'success': True,
                    'data': data,
                    'period': period,
                    'cache_key': cache_key
                }
            else:
                error_msg = f"xtdata未返回有效{period}数据"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"批量获取{period}数据失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def batch_get_multi_period_data(self, stock_codes: List[str], start_date: str, end_date: str = None,
                                   periods: List[str] = None, fields: List[str] = None) -> Dict[str, Any]:
        """
        批量获取多周期股票数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期，格式为YYYYMMDD
            end_date: 结束日期，格式为YYYYMMDD，默认为None（到当前日期）
            periods: 数据周期列表，默认为['1d', '1m']
            fields: 数据字段列表，默认为['open', 'high', 'low', 'close', 'volume']
        
        Returns:
            Dict[str, Any]: 包含多周期数据的字典
        """
        if periods is None:
            periods = ['1d', '1m']
        if fields is None:
            fields = ['open', 'high', 'low', 'close', 'volume']
        
        self.logger.info(f"开始批量获取多周期股票数据，股票数量: {len(stock_codes)}，周期: {periods}")
        
        multi_period_data = {}
        success_count = 0
        
        try:
            for period in periods:
                self.logger.info(f"获取{period}周期数据...")
                result = self.batch_get_data(
                    stock_codes=stock_codes,
                    start_date=start_date,
                    end_date=end_date,
                    fields=fields,
                    period=period
                )
                
                if result['success']:
                    multi_period_data[period] = result
                    success_count += 1
                    self.logger.info(f"{period}周期数据获取成功")
                else:
                    self.logger.error(f"{period}周期数据获取失败: {result.get('error', '未知错误')}")
                    multi_period_data[period] = result
            
            return {
                'success': success_count > 0,
                'data': multi_period_data,
                'success_periods': [p for p in periods if multi_period_data[p]['success']],
                'failed_periods': [p for p in periods if not multi_period_data[p]['success']],
                'total_periods': len(periods),
                'success_count': success_count
            }
            
        except Exception as e:
            error_msg = f"批量获取多周期数据失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def get_stock_dataframe(self, stock_code: str, data: Dict[str, Any] = None, 
                           start_date: str = None, end_date: str = None, period: str = '1d') -> Optional[pd.DataFrame]:
        """
        从批量数据中提取单只股票的DataFrame
        
        Args:
            stock_code: 股票代码
            data: 批量数据字典，如果为None则尝试从缓存获取
            start_date: 开始日期，用于过滤数据
            end_date: 结束日期，用于过滤数据
            period: 数据周期，默认为'1d'
        
        Returns:
            pd.DataFrame: 股票数据DataFrame，包含OHLCV数据
        """
        self.logger.debug(f"提取股票DataFrame: {stock_code}, 时间范围: {start_date} - {end_date}, 周期: {period}")
        
        try:
            # 如果没有提供数据，尝试从缓存获取
            if data is None:
                self.logger.warning(f"未提供数据，无法提取 {stock_code} 的DataFrame")
                return None
            
            self.logger.debug(f"批量数据字段: {list(data.keys())}")
            
            # 检查股票代码是否在数据中
            if 'close' not in data:
                self.logger.warning(f"批量数据中缺少'close'字段")
                return None
                
            if stock_code not in data['close'].index:
                self.logger.warning(f"股票 {stock_code} 不在批量数据的close字段中")
                self.logger.debug(f"可用股票代码: {data['close'].index.tolist()}")
                return None
            
            self.logger.debug(f"股票 {stock_code} 在批量数据中找到")
            
            # 构建DataFrame
            df_data = {}
            field_mapping = {
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            
            self.logger.debug(f"开始构建DataFrame，字段映射: {field_mapping}")
            
            for field, col_name in field_mapping.items():
                if field in data:
                    if stock_code in data[field].index:
                        df_data[col_name] = data[field].loc[stock_code]
                        self.logger.debug(f"字段 {field} -> {col_name}: 数据长度 {len(data[field].loc[stock_code])}")
                    else:
                        self.logger.debug(f"股票 {stock_code} 在字段 {field} 中不存在")
                else:
                    self.logger.debug(f"批量数据中缺少字段: {field}")
            
            if not df_data:
                self.logger.warning(f"无法为股票 {stock_code} 构建DataFrame - 没有有效数据")
                return None
            
            self.logger.debug(f"DataFrame数据字段: {list(df_data.keys())}")
            
            df = pd.DataFrame(df_data)
            self.logger.debug(f"原始DataFrame形状: {df.shape}")
            self.logger.debug(f"原始索引范围: {df.index[0]} 到 {df.index[-1]}")
            
            # 根据周期选择合适的时间格式
            if period == '1m':
                # 分钟线数据格式: YYYYMMDDHHMMSS
                try:
                    df.index = pd.to_datetime(df.index, format='%Y%m%d%H%M%S')
                except ValueError:
                    # 如果上述格式失败，尝试其他可能的格式
                    try:
                        df.index = pd.to_datetime(df.index, format='%Y%m%d %H%M%S')
                    except ValueError:
                        # 最后尝试自动推断格式
                        df.index = pd.to_datetime(df.index)
            else:
                # 日线数据格式: YYYYMMDD
                df.index = pd.to_datetime(df.index, format='%Y%m%d')
            
            df.index.name = 'Date'
            self.logger.debug(f"转换后时间索引范围: {df.index[0]} 到 {df.index[-1]}")
            
            # 过滤日期范围
            original_len = len(df)
            if start_date:
                start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                df = df[df.index >= start_dt]
                self.logger.debug(f"按开始日期 {start_date} 过滤后: {len(df)} 条 (原 {original_len} 条)")
            
            if end_date:
                end_dt = pd.to_datetime(end_date, format='%Y%m%d')
                df = df[df.index <= end_dt]
                self.logger.debug(f"按结束日期 {end_date} 过滤后: {len(df)} 条")
            
            if len(df) == 0:
                self.logger.warning(f"过滤后DataFrame为空，股票: {stock_code}")
                return None
            
            self.logger.debug(f"✅ 成功提取 {stock_code} 的DataFrame，最终数据量: {len(df)}")
            self.logger.debug(f"最终时间范围: {df.index[0]} 到 {df.index[-1]}")
            return df
            
        except Exception as e:
            self.logger.error(f"提取股票DataFrame失败: {str(e)}", exc_info=True)
            return None
    
    def get_stock_dataframe_from_multi_period(self, stock_code: str, multi_period_data: Dict[str, Any], 
                                             period: str = '1d', start_date: str = None, 
                                             end_date: str = None) -> Optional[pd.DataFrame]:
        """
        从多周期数据中提取特定周期的单只股票DataFrame
        
        Args:
            stock_code: 股票代码
            multi_period_data: 多周期数据字典
            period: 要提取的数据周期，默认为'1d'
            start_date: 开始日期，用于过滤数据
            end_date: 结束日期，用于过滤数据
        
        Returns:
            pd.DataFrame: 股票数据DataFrame，包含OHLCV数据
        """
        self.logger.debug(f"从多周期数据提取股票DataFrame: {stock_code}, 周期: {period}")
        
        try:
            if period not in multi_period_data['data']:
                self.logger.warning(f"多周期数据中不包含{period}周期数据")
                return None
            
            period_data = multi_period_data['data'][period]
            if not period_data['success']:
                self.logger.warning(f"{period}周期数据获取失败: {period_data.get('error', '未知错误')}")
                return None
            
            return self.get_stock_dataframe(
                stock_code=stock_code,
                data=period_data['data'],
                start_date=start_date,
                end_date=end_date,
                period=period
            )
            
        except Exception as e:
            self.logger.error(f"从多周期数据提取DataFrame失败: {str(e)}", exc_info=True)
            return None
    
    def get_stock_price_series(self, stock_code: str, data: Dict[str, Any], 
                              field: str = 'close', period: str = '1d') -> Optional[pd.Series]:
        """
        从批量数据中提取单只股票的价格序列
        
        Args:
            stock_code: 股票代码
            data: 批量数据字典
            field: 价格字段，默认为'close'
        
        Returns:
            pd.Series: 价格序列
        """
        self.logger.debug(f"提取股票价格序列: {stock_code}, 字段: {field}")
        
        try:
            if field not in data or stock_code not in data[field].index:
                self.logger.warning(f"股票 {stock_code} 的 {field} 数据不存在")
                return None
            
            price_series = data[field].loc[stock_code]
            
            # 根据周期选择合适的时间格式
            if period == '1m':
                # 分钟线数据格式: YYYYMMDDHHMMSS
                try:
                    price_series.index = pd.to_datetime(price_series.index, format='%Y%m%d%H%M%S')
                except ValueError:
                    # 如果上述格式失败，尝试其他可能的格式
                    try:
                        price_series.index = pd.to_datetime(price_series.index, format='%Y%m%d %H%M%S')
                    except ValueError:
                        # 最后尝试自动推断格式
                        price_series.index = pd.to_datetime(price_series.index)
            else:
                # 日线数据格式: YYYYMMDD
                price_series.index = pd.to_datetime(price_series.index, format='%Y%m%d')
            
            self.logger.debug(f"成功提取 {stock_code} 的 {field} 价格序列，数据量: {len(price_series)}")
            return price_series
            
        except Exception as e:
            self.logger.error(f"提取价格序列失败: {str(e)}", exc_info=True)
            return None
    
    def clear_cache(self):
        """
        清空数据缓存
        """
        self.logger.info("清空数据缓存")
        self.data_cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            Dict[str, Any]: 缓存信息
        """
        cache_info = {
            'cache_count': len(self.data_cache),
            'cache_keys': list(self.data_cache.keys())
        }
        self.logger.debug(f"缓存信息: {cache_info}")
        return cache_info