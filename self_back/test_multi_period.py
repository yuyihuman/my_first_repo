#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多周期数据功能测试脚本

测试新增的多周期数据获取和处理功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.data_manager import DataManager
from modules.buy_strategy import BuyStrategy
from modules.sell_strategy import SellStrategy
from utils.logger import setup_logger
from datetime import datetime, timedelta

def test_multi_period_data():
    """
    测试多周期数据获取功能
    """
    logger = setup_logger('test_multi_period', 'test_multi_period.log')
    logger.info("开始测试多周期数据功能")
    
    # 初始化数据管理器
    data_manager = DataManager()
    
    # 测试股票列表
    test_stocks = ['300003.SZ', '300251.SZ']
    
    # 测试时间范围
    end_date = '20241201'
    start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)
    start_date = start_dt.strftime('%Y%m%d')
    
    logger.info(f"测试股票: {test_stocks}")
    logger.info(f"测试时间范围: {start_date} - {end_date}")
    
    try:
        # 测试1：批量下载多周期数据
        logger.info("\n=== 测试1：批量下载多周期数据 ===")
        periods = ['1d', '1m']
        
        for period in periods:
            logger.info(f"下载{period}周期数据...")
            download_result = data_manager.batch_download_data(
                stock_codes=test_stocks,
                start_date=start_date,
                end_date=end_date,
                period=period
            )
            logger.info(f"{period}周期下载结果: {download_result}")
        
        # 测试2：批量获取多周期数据
        logger.info("\n=== 测试2：批量获取多周期数据 ===")
        multi_period_result = data_manager.batch_get_multi_period_data(
            stock_codes=test_stocks,
            start_date=start_date,
            end_date=end_date,
            periods=periods
        )
        
        logger.info(f"多周期数据获取结果: {multi_period_result['success']}")
        logger.info(f"成功周期: {multi_period_result['success_periods']}")
        logger.info(f"失败周期: {multi_period_result['failed_periods']}")
        
        if multi_period_result['success']:
            # 测试3：从多周期数据中提取特定周期数据
            logger.info("\n=== 测试3：从多周期数据中提取数据 ===")
            
            for stock in test_stocks:
                for period in periods:
                    if period in multi_period_result['success_periods']:
                        df = data_manager.get_stock_dataframe_from_multi_period(
                            stock_code=stock,
                            multi_period_data=multi_period_result,
                            period=period,
                            start_date=start_date,
                            end_date=end_date
                        )
                        
                        if df is not None and not df.empty:
                            logger.info(f"✅ {stock} {period}周期数据: {len(df)}条记录")
                            logger.info(f"   时间范围: {df.index[0]} - {df.index[-1]}")
                            logger.info(f"   数据列: {df.columns.tolist()}")
                        else:
                            logger.warning(f"❌ {stock} {period}周期数据为空")
            
            # 测试4：买入策略使用多周期数据
            logger.info("\n=== 测试4：买入策略使用多周期数据 ===")
            buy_strategy = BuyStrategy()
            
            test_stock = test_stocks[0]
            logger.info(f"测试股票: {test_stock}")
            
            # 使用多周期数据执行买入策略
            buy_signals = buy_strategy.execute_strategy_with_data(
                strategy_name='three_days_up',
                stock_code=test_stock,
                start_date=start_date,
                end_date=end_date,
                multi_period_data=multi_period_result,
                data_manager=data_manager
            )
            
            logger.info(f"买入信号数量: {len(buy_signals)}")
            for signal in buy_signals:
                logger.info(f"买入信号: {signal}")
            
            # 测试5：卖出策略使用多周期数据
            logger.info("\n=== 测试5：卖出策略使用多周期数据 ===")
            sell_strategy = SellStrategy()
            
            if buy_signals:
                # 模拟买入信息
                buy_info = {
                    'date': buy_signals[0]['date'],
                    'price': buy_signals[0]['price'],
                    'volume': 1000,
                    'reason': buy_signals[0]['reason']
                }
                
                # 使用多周期数据执行卖出策略
                sell_signals = sell_strategy.execute_strategy_with_data(
                    strategy_name='hold_three_days',
                    stock_code=test_stock,
                    buy_info=buy_info,
                    start_date=buy_info['date'],
                    end_date=end_date,
                    multi_period_data=multi_period_result,
                    data_manager=data_manager
                )
                
                logger.info(f"卖出信号数量: {len(sell_signals)}")
                for signal in sell_signals:
                    logger.info(f"卖出信号: {signal}")
            else:
                logger.info("没有买入信号，跳过卖出策略测试")
        
        logger.info("\n=== 多周期数据功能测试完成 ===")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}", exc_info=True)
        return False

def main():
    """
    主函数
    """
    print("开始多周期数据功能测试...")
    
    success = test_multi_period_data()
    
    if success:
        print("✅ 多周期数据功能测试成功完成")
    else:
        print("❌ 多周期数据功能测试失败")
    
    print("\n详细日志请查看 test_multi_period.log 文件")

if __name__ == '__main__':
    main()