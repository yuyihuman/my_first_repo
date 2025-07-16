#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股模块

负责根据各种条件筛选股票
目前仅预留接口，后续可扩展具体的选股逻辑
"""

from typing import List, Dict, Any
import pandas as pd
import os
import random
from utils.logger import setup_logger

class StockSelector:
    """
    选股器类
    
    提供各种选股策略的接口
    """
    
    def __init__(self):
        """
        初始化选股器
        """
        self.logger = setup_logger('stock_selector', 'stock_selector.log')
        self.logger.info("选股模块初始化")
        
        # 选股策略注册表
        self.strategies = {}
        
        # 注册内置策略
        self._register_builtin_strategies()
        
        self.logger.debug("选股器初始化完成")
    
    def register_strategy(self, name: str, strategy_func):
        """
        注册选股策略
        
        Args:
            name (str): 策略名称
            strategy_func: 策略函数
        """
        self.logger.info(f"注册选股策略: {name}")
        self.strategies[name] = strategy_func
        self.logger.debug(f"当前已注册策略数量: {len(self.strategies)}")
    
    def select_stocks(self, strategy_name: str = None, **kwargs) -> List[str]:
        """
        执行选股
        
        Args:
            strategy_name (str): 策略名称，如果为None则使用默认策略
            **kwargs: 策略参数
        
        Returns:
            List[str]: 选中的股票代码列表
        """
        self.logger.info(f"开始执行选股，策略: {strategy_name}")
        self.logger.debug(f"选股参数: {kwargs}")
        
        try:
            if strategy_name is None:
                # 默认策略：返回一些示例股票
                result = self._default_strategy(**kwargs)
            elif strategy_name in self.strategies:
                # 执行指定策略
                result = self.strategies[strategy_name](**kwargs)
            else:
                self.logger.error(f"未找到策略: {strategy_name}")
                raise ValueError(f"未找到策略: {strategy_name}")
            
            self.logger.info(f"选股完成，共选中 {len(result)} 只股票")
            self.logger.debug(f"选中股票: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"选股过程中发生错误: {str(e)}", exc_info=True)
            raise
    
    def _default_strategy(self, **kwargs) -> List[str]:
        """
        默认选股策略：随机选取沪深10支股票
        
        Args:
            **kwargs: 策略参数
        
        Returns:
            List[str]: 股票代码列表
        """
        self.logger.info("执行默认选股策略：随机选取沪深10支股票")
        
        # 沪深股票池（包含主要的蓝筹股和活跃股票）
        stock_pool = [
            # 上海主板
            "600000.SH", "600036.SH", "600519.SH", "600887.SH", "601318.SH",
            "601398.SH", "601857.SH", "601988.SH", "600276.SH", "600585.SH",
            "600690.SH", "600703.SH", "600809.SH", "600837.SH", "600893.SH",
            "601012.SH", "601066.SH", "601088.SH", "601166.SH", "601169.SH",
            "601186.SH", "601211.SH", "601229.SH", "601288.SH", "601328.SH",
            "601336.SH", "601390.SH", "601601.SH", "601628.SH", "601668.SH",
            "601688.SH", "601766.SH", "601788.SH", "601818.SH", "601828.SH",
            "601838.SH", "601888.SH", "601898.SH", "601919.SH", "601939.SH",
            # 深圳主板
            "000001.SZ", "000002.SZ", "000858.SZ", "000895.SZ", "000938.SZ",
            "000063.SZ", "000069.SZ", "000100.SZ", "000157.SZ", "000166.SZ",
            "000333.SZ", "000338.SZ", "000402.SZ", "000413.SZ", "000423.SZ",
            "000425.SZ", "000503.SZ", "000538.SZ", "000540.SZ", "000559.SZ",
            "000568.SZ", "000596.SZ", "000623.SZ", "000625.SZ", "000627.SZ",
            "000630.SZ", "000651.SZ", "000671.SZ", "000709.SZ", "000725.SZ",
            "000728.SZ", "000729.SZ", "000738.SZ", "000750.SZ", "000768.SZ",
            "000776.SZ", "000783.SZ", "000792.SZ", "000826.SZ", "000839.SZ",
            # 中小板
            "002001.SZ", "002007.SZ", "002024.SZ", "002027.SZ", "002032.SZ",
            "002044.SZ", "002050.SZ", "002065.SZ", "002081.SZ", "002120.SZ",
            "002129.SZ", "002142.SZ", "002146.SZ", "002153.SZ", "002174.SZ",
            "002202.SZ", "002230.SZ", "002236.SZ", "002241.SZ", "002252.SZ",
            "002304.SZ", "002311.SZ", "002352.SZ", "002385.SZ", "002415.SZ",
            "002456.SZ", "002460.SZ", "002466.SZ", "002475.SZ", "002493.SZ",
            # 创业板
            "300001.SZ", "300002.SZ", "300003.SZ", "300009.SZ", "300014.SZ",
            "300015.SZ", "300017.SZ", "300024.SZ", "300027.SZ", "300033.SZ",
            "300059.SZ", "300070.SZ", "300072.SZ", "300104.SZ", "300122.SZ",
            "300124.SZ", "300136.SZ", "300142.SZ", "300144.SZ", "300146.SZ",
            "300166.SZ", "300168.SZ", "300182.SZ", "300207.SZ", "300251.SZ",
            "300274.SZ", "300285.SZ", "300296.SZ", "300315.SZ", "300347.SZ"
        ]
        
        # 随机选择10支股票
        selected_stocks = random.sample(stock_pool, min(10, len(stock_pool)))
        
        self.logger.info(f"随机选股完成，选中股票: {selected_stocks}")
        self.logger.debug(f"默认策略返回股票: {selected_stocks}")
        
        return selected_stocks
    
    def get_available_strategies(self) -> List[str]:
        """
        获取可用的选股策略列表
        
        Returns:
            List[str]: 策略名称列表
        """
        strategies = list(self.strategies.keys())
        self.logger.debug(f"获取可用策略列表: {strategies}")
        return strategies
    
    def validate_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码格式
        
        Args:
            stock_code (str): 股票代码
        
        Returns:
            bool: 是否有效
        """
        self.logger.debug(f"验证股票代码: {stock_code}")
        
        # 简单的格式验证：6位数字.市场代码
        if not stock_code or '.' not in stock_code:
            self.logger.warning(f"股票代码格式无效: {stock_code}")
            return False
        
        code, market = stock_code.split('.')
        
        # 检查代码部分是否为6位数字
        if len(code) != 6 or not code.isdigit():
            self.logger.warning(f"股票代码格式无效: {stock_code}")
            return False
        
        # 检查市场代码
        if market not in ['SH', 'SZ']:
            self.logger.warning(f"不支持的市场代码: {market}")
            return False
        
        self.logger.debug(f"股票代码验证通过: {stock_code}")
        return True
    
    def _register_builtin_strategies(self):
        """
        注册内置选股策略
        """
        self.register_strategy('qfii_stocks', self._qfii_strategy)
        self.register_strategy('random_stocks', self._random_strategy)
        self.logger.info("已注册内置选股策略: qfii_stocks, random_stocks")
    
    def _random_strategy(self, count: int = 1, **kwargs) -> List[str]:
        """
        随机选股策略：从股票池中随机选择指定数量的股票
        
        Args:
            count (int): 选择的股票数量，默认1支
            **kwargs: 其他参数
        
        Returns:
            List[str]: 随机选中的股票代码列表
        """
        self.logger.info(f"执行随机选股策略，选择 {count} 支股票")
        
        # 使用与默认策略相同的股票池
        stock_pool = [
            # 上海主板
            "600000.SH", "600036.SH", "600519.SH", "600887.SH", "601318.SH",
            "601398.SH", "601857.SH", "601988.SH", "600276.SH", "600585.SH",
            "600690.SH", "600703.SH", "600809.SH", "600837.SH", "600893.SH",
            "601012.SH", "601066.SH", "601088.SH", "601166.SH", "601169.SH",
            "601186.SH", "601211.SH", "601229.SH", "601288.SH", "601328.SH",
            "601336.SH", "601390.SH", "601601.SH", "601628.SH", "601668.SH",
            "601688.SH", "601766.SH", "601788.SH", "601818.SH", "601828.SH",
            "601838.SH", "601888.SH", "601898.SH", "601919.SH", "601939.SH",
            # 深圳主板
            "000001.SZ", "000002.SZ", "000858.SZ", "000895.SZ", "000938.SZ",
            "000063.SZ", "000069.SZ", "000100.SZ", "000157.SZ", "000166.SZ",
            "000333.SZ", "000338.SZ", "000402.SZ", "000413.SZ", "000423.SZ",
            "000425.SZ", "000503.SZ", "000538.SZ", "000540.SZ", "000559.SZ",
            "000568.SZ", "000596.SZ", "000623.SZ", "000625.SZ", "000627.SZ",
            "000630.SZ", "000651.SZ", "000671.SZ", "000709.SZ", "000725.SZ",
            "000728.SZ", "000729.SZ", "000738.SZ", "000750.SZ", "000768.SZ",
            "000776.SZ", "000783.SZ", "000792.SZ", "000826.SZ", "000839.SZ",
            # 中小板
            "002001.SZ", "002007.SZ", "002024.SZ", "002027.SZ", "002032.SZ",
            "002044.SZ", "002050.SZ", "002065.SZ", "002081.SZ", "002120.SZ",
            "002129.SZ", "002142.SZ", "002146.SZ", "002153.SZ", "002174.SZ",
            "002202.SZ", "002230.SZ", "002236.SZ", "002241.SZ", "002252.SZ",
            "002304.SZ", "002311.SZ", "002352.SZ", "002385.SZ", "002415.SZ",
            "002456.SZ", "002460.SZ", "002466.SZ", "002475.SZ", "002493.SZ",
            # 创业板
            "300001.SZ", "300002.SZ", "300003.SZ", "300009.SZ", "300014.SZ",
            "300015.SZ", "300017.SZ", "300024.SZ", "300027.SZ", "300033.SZ",
            "300059.SZ", "300070.SZ", "300072.SZ", "300104.SZ", "300122.SZ",
            "300124.SZ", "300136.SZ", "300142.SZ", "300144.SZ", "300146.SZ",
            "300166.SZ", "300168.SZ", "300182.SZ", "300207.SZ", "300251.SZ",
            "300274.SZ", "300285.SZ", "300296.SZ", "300315.SZ", "300347.SZ"
        ]
        
        # 确保选择数量不超过股票池大小
        actual_count = min(count, len(stock_pool))
        selected_stocks = random.sample(stock_pool, actual_count)
        
        self.logger.info(f"随机选股完成，实际选中 {len(selected_stocks)} 支股票: {selected_stocks}")
        
        return selected_stocks

    def _qfii_strategy(self, data_file_path: str = None, **kwargs) -> List[str]:
        """
        QFII选股策略：选出曾经出现过QFII持仓的所有股票
        
        Args:
            data_file_path (str): 机构持仓数据文件路径
            **kwargs: 其他参数
        
        Returns:
            List[str]: 曾经有QFII持仓的股票代码列表
        """
        self.logger.info("执行QFII选股策略")
        
        # 默认数据文件路径
        if data_file_path is None:
            data_file_path = "c:/Users/Ramsey/github/my_first_repo/stock_holding/institutional_holdings_data/processed_data/merged_holdings_data.csv"
        
        try:
            # 检查文件是否存在
            if not os.path.exists(data_file_path):
                self.logger.error(f"数据文件不存在: {data_file_path}")
                return []
            
            self.logger.info(f"读取机构持仓数据: {data_file_path}")
            
            # 读取CSV文件
            df = pd.read_csv(data_file_path, encoding='utf-8')
            self.logger.info(f"成功读取数据，共 {len(df)} 条记录")
            
            # 筛选QFII持仓记录
            qfii_records = df[df['institution_type'] == 'QFII持仓']
            self.logger.info(f"找到 {len(qfii_records)} 条QFII持仓记录")
            
            # 统计每只股票的出现次数和获取总股本信息
            stock_stats = {}
            processed_count = 0
            valid_count = 0
            invalid_count = 0
            
            for _, record in qfii_records.iterrows():
                stock_code = record['stock_code']
                processed_count += 1
                
                if pd.notna(stock_code):
                    # 转换为整数字符串（去掉小数点）
                    try:
                        raw_code = str(int(float(stock_code))).zfill(6)
                        
                        # 根据代码规则添加市场后缀
                        formatted_code = self._format_stock_code(raw_code)
                        
                        if formatted_code:
                            # 暂时跳过股票代码验证，因为验证可能过于严格
                            if formatted_code not in stock_stats:
                                stock_stats[formatted_code] = {
                                    'count': 0,
                                    'total_shares': 0  # 总股本
                                }
                            
                            # 增加出现次数
                            stock_stats[formatted_code]['count'] += 1
                            valid_count += 1
                            
                            # 获取总股本（如果有的话）
                            total_shares = record.get('总股本', 0)
                            if pd.notna(total_shares) and total_shares > 0:
                                # 取最大值作为该股票的总股本
                                stock_stats[formatted_code]['total_shares'] = max(
                                    stock_stats[formatted_code]['total_shares'], 
                                    float(total_shares)
                                )
                        else:
                            invalid_count += 1
                            if invalid_count <= 5:  # 只记录前5个无效代码
                                self.logger.warning(f"无法格式化股票代码: {stock_code} -> {raw_code}")
                    except (ValueError, TypeError) as e:
                        invalid_count += 1
                        if invalid_count <= 5:  # 只记录前5个处理失败的代码
                            self.logger.warning(f"处理股票代码失败: {stock_code} - {e}")
                else:
                    invalid_count += 1
                    if invalid_count <= 5:  # 只记录前5个空代码
                        self.logger.warning(f"空的股票代码: {stock_code}")
            
            self.logger.info(f"处理统计: 总记录{processed_count}, 有效{valid_count}, 无效{invalid_count}")
            
            self.logger.info(f"统计完成，共有 {len(stock_stats)} 只不重复的QFII持仓股票")
            
            # 按出现次数降序排列，相同次数时按总股本降序排列
            sorted_stocks = sorted(
                stock_stats.items(),
                key=lambda x: (x[1]['count'], x[1]['total_shares']),
                reverse=True
            )
            
            # 选取前100只股票
            top_stocks = [stock_code for stock_code, stats in sorted_stocks[:100]]
            
            self.logger.info(f"QFII选股策略完成，按出现次数和总股本排序后选出前 {len(top_stocks)} 只股票")
            
            # 记录排序统计信息
            if sorted_stocks:
                top_5 = sorted_stocks[:5]
                self.logger.info("排序前5名股票统计:")
                for i, (code, stats) in enumerate(top_5, 1):
                    self.logger.info(f"  {i}. {code}: 出现{stats['count']}次, 总股本{stats['total_shares']:.0f}万股")
            
            return top_stocks
            
        except FileNotFoundError:
            self.logger.error(f"文件未找到: {data_file_path}")
            return []
        except pd.errors.EmptyDataError:
            self.logger.error("数据文件为空")
            return []
        except KeyError as e:
            self.logger.error(f"数据文件缺少必要字段: {e}")
            return []
        except Exception as e:
             self.logger.error(f"QFII选股策略执行失败: {str(e)}", exc_info=True)
             return []
    
    def _format_stock_code(self, stock_code: str) -> str:
        """
        根据股票代码规则添加市场后缀
        
        Args:
            stock_code (str): 6位数字的股票代码
        
        Returns:
            str: 格式化后的股票代码（包含市场后缀）
        """
        if len(stock_code) != 6 or not stock_code.isdigit():
            return None
        
        # 根据股票代码规则判断市场
        # 上海证券交易所（SH）：
        # - 主板：600xxx, 601xxx, 603xxx, 605xxx
        # - 科创板：688xxx
        # 深圳证券交易所（SZ）：
        # - 主板：000xxx, 001xxx
        # - 中小板：002xxx
        # - 创业板：300xxx
        
        if stock_code.startswith(('600', '601', '603', '605', '688')):
            return f"{stock_code}.SH"
        elif stock_code.startswith(('000', '001', '002', '300')):
            return f"{stock_code}.SZ"
        else:
            # 对于不常见的代码，尝试根据首位数字判断
            first_digit = stock_code[0]
            if first_digit in ['6', '9']:  # 6开头通常是上海，9开头是上海B股
                return f"{stock_code}.SH"
            elif first_digit in ['0', '1', '2', '3']:  # 0-3开头通常是深圳
                return f"{stock_code}.SZ"
            else:
                self.logger.warning(f"无法确定市场代码: {stock_code}")
                return None