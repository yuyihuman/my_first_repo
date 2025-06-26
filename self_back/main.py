#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票回测程序主入口

包含选股、买入策略、卖出策略、收益率计算和报告生成模块
"""

import os
from datetime import datetime
from modules.stock_selector import StockSelector
from modules.buy_strategy import BuyStrategy
from modules.sell_strategy import SellStrategy
from modules.return_calculator import ReturnCalculator
from modules.report_generator import ReportGenerator
from utils.logger import setup_logger

class BacktestEngine:
    """
    回测引擎主类
    
    整合所有模块，提供完整的回测功能
    """
    
    def __init__(self):
        """
        初始化回测引擎
        """
        self.logger = setup_logger('backtest_engine', 'backtest_engine.log')
        self.logger.info("回测引擎初始化开始")
        
        # 初始化各个模块
        self.stock_selector = StockSelector()
        self.buy_strategy = BuyStrategy()
        self.sell_strategy = SellStrategy()
        self.return_calculator = ReturnCalculator()
        self.report_generator = ReportGenerator()
        
        self.logger.info("所有模块初始化完成")
        self.logger.debug("回测引擎初始化完成")
    
    def run_single_trade_backtest(self, stock_code: str, buy_date: str, sell_date: str, 
                                 dividend_type: str = 'none') -> dict:
        """
        运行单笔交易回测
        
        Args:
            stock_code (str): 股票代码
            buy_date (str): 买入日期
            sell_date (str): 卖出日期
            dividend_type (str): 除权方式
        
        Returns:
            dict: 回测结果
        """
        self.logger.info(f"开始单笔交易回测 - {stock_code}: {buy_date} -> {sell_date}")
        
        try:
            # 计算收益率
            result = self.return_calculator.calculate_return(
                stock_code=stock_code,
                buy_date=buy_date,
                sell_date=sell_date,
                dividend_type=dividend_type
            )
            
            if not result['success']:
                self.logger.error(f"收益率计算失败: {result['error']}")
                return result
            
            self.logger.info(f"单笔交易回测完成 - 收益率: {result['return_percentage']:.2f}%")
            return result
            
        except Exception as e:
            error_msg = f"单笔交易回测失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def run_batch_backtest(self, trades: list) -> dict:
        """
        运行批量交易回测
        
        Args:
            trades (list): 交易列表
        
        Returns:
            dict: 批量回测结果
        """
        self.logger.info(f"开始批量交易回测 - 共 {len(trades)} 笔交易")
        
        try:
            # 批量计算收益率
            result = self.return_calculator.calculate_batch_returns(trades)
            
            if not result['success']:
                self.logger.error(f"批量回测失败: {result.get('error', 'Unknown error')}")
                return result
            
            summary = result['summary']
            self.logger.info(f"批量回测完成 - 成功: {summary['successful_trades']}/{summary['total_trades']}, "
                           f"平均收益率: {summary['average_return_percentage']:.2f}%")
            
            return result
            
        except Exception as e:
            error_msg = f"批量回测失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def generate_backtest_report(self, backtest_result: dict, report_type: str = 'detailed', 
                               output_format: str = 'dict', save_to_file: bool = False) -> dict:
        """
        生成回测报告
        
        Args:
            backtest_result (dict): 回测结果
            report_type (str): 报告类型
            output_format (str): 输出格式
            save_to_file (bool): 是否保存到文件
        
        Returns:
            dict: 报告生成结果
        """
        self.logger.info(f"生成回测报告 - 类型: {report_type}, 格式: {output_format}")
        
        try:
            # 生成报告
            report_result = self.report_generator.generate_report(
                data=backtest_result,
                report_type=report_type,
                output_format=output_format
            )
            
            if not report_result['success']:
                self.logger.error(f"报告生成失败: {report_result['error']}")
                return report_result
            
            # 保存到文件
            if save_to_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"backtest_report_{timestamp}.{output_format if output_format != 'dict' else 'json'}"
                filepath = os.path.join('logs', filename)
                
                save_result = self.report_generator.save_report(
                    report=report_result,
                    filename=filepath,
                    format_type=output_format if output_format != 'dict' else 'json'
                )
                
                if save_result['success']:
                    self.logger.info(f"报告已保存到: {filepath}")
                    report_result['saved_file'] = filepath
                else:
                    self.logger.warning(f"报告保存失败: {save_result['error']}")
            
            self.logger.info("回测报告生成完成")
            return report_result
            
        except Exception as e:
            error_msg = f"生成回测报告失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def run_complete_backtest(self, trades: list, report_type: str = 'detailed', 
                            save_report: bool = True) -> dict:
        """
        运行完整回测流程
        
        Args:
            trades (list): 交易列表
            report_type (str): 报告类型
            save_report (bool): 是否保存报告
        
        Returns:
            dict: 完整回测结果
        """
        self.logger.info(f"开始完整回测流程 - {len(trades)} 笔交易")
        
        try:
            # 执行回测
            if len(trades) == 1:
                trade = trades[0]
                backtest_result = self.run_single_trade_backtest(
                    stock_code=trade['stock_code'],
                    buy_date=trade['buy_date'],
                    sell_date=trade['sell_date'],
                    dividend_type=trade.get('dividend_type', 'none')
                )
            else:
                backtest_result = self.run_batch_backtest(trades)
            
            if not backtest_result['success']:
                return backtest_result
            
            # 生成报告
            report_result = self.generate_backtest_report(
                backtest_result=backtest_result,
                report_type=report_type,
                output_format='dict',
                save_to_file=save_report
            )
            
            # 整合结果
            complete_result = {
                'success': True,
                'backtest_result': backtest_result,
                'report_result': report_result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.logger.info("完整回测流程完成")
            return complete_result
            
        except Exception as e:
            error_msg = f"完整回测流程失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}

def run_example_single_trade():
    """
    运行单笔交易示例
    """
    print("=== 单笔交易回测示例 ===")
    
    engine = BacktestEngine()
    
    # 示例交易
    result = engine.run_single_trade_backtest(
        stock_code='000001.SZ',
        buy_date='20240101',
        sell_date='20240201'
    )
    
    if result['success']:
        print(f"股票代码: {result['stock_code']}")
        print(f"买入日期: {result['actual_buy_date']} (价格: {result['buy_price']:.2f})")
        print(f"卖出日期: {result['actual_sell_date']} (价格: {result['sell_price']:.2f})")
        print(f"收益率: {result['return_percentage']:.2f}%")
        print(f"年化收益率: {result['annual_return_percentage']:.2f}%")
        print(f"持有天数: {result['hold_days']} 天")
        
        # 生成报告
        report_result = engine.generate_backtest_report(
            backtest_result=result,
            report_type='summary',
            save_to_file=True
        )
        
        if report_result['success']:
            print("\n=== 报告摘要 ===")
            content = report_result['content']
            if 'performance_summary' in content:
                print(content['performance_summary'])
    else:
        print(f"回测失败: {result['error']}")

def run_example_batch_trades():
    """
    运行批量交易示例
    """
    print("\n=== 批量交易回测示例 ===")
    
    engine = BacktestEngine()
    
    # 示例交易列表
    trades = [
        {
            'stock_code': '000001.SZ',
            'buy_date': '20240101',
            'sell_date': '20240201'
        },
        {
            'stock_code': '000002.SZ',
            'buy_date': '20240115',
            'sell_date': '20240215'
        },
        {
            'stock_code': '600000.SH',
            'buy_date': '20240201',
            'sell_date': '20240301'
        }
    ]
    
    # 运行完整回测
    result = engine.run_complete_backtest(trades, report_type='detailed')
    
    if result['success']:
        backtest_result = result['backtest_result']
        summary = backtest_result['summary']
        
        print(f"总交易次数: {summary['total_trades']}")
        print(f"成功交易次数: {summary['successful_trades']}")
        print(f"失败交易次数: {summary['failed_trades']}")
        print(f"总收益率: {summary['total_return']*100:.2f}%")
        print(f"平均收益率: {summary['average_return_percentage']:.2f}%")
        
        # 显示报告信息
        report_result = result['report_result']
        if report_result['success'] and 'saved_file' in report_result:
            print(f"\n详细报告已保存到: {report_result['saved_file']}")
    else:
        print(f"批量回测失败: {result['error']}")

def main():
    """
    主函数
    """
    # 设置日志
    logger = setup_logger('main', 'main.log')
    logger.info("股票回测程序启动")
    
    try:
        print("股票回测程序")
        print("=" * 50)
        
        # 运行示例
        run_example_single_trade()
        run_example_batch_trades()
        
        print("\n=== 程序运行完成 ===")
        print("详细日志请查看 logs 目录")
        
        logger.info("股票回测程序正常结束")
        
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}", exc_info=True)
        print(f"程序运行出错: {str(e)}")
        print("详细错误信息请查看日志文件")

if __name__ == '__main__':
    main()