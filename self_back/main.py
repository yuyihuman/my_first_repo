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
from modules.chart_generator import ChartGenerator
from modules.data_manager import DataManager
from utils.logger import setup_logger

class BacktestEngine:
    """
    回测引擎主类
    
    整合所有模块，提供完整的回测功能
    支持持续监控买卖信号的量化交易回测
    """
    
    def __init__(self):
        """
        初始化回测引擎
        """
        self.logger = setup_logger('backtest_engine', 'backtest_engine.log')
        self.logger.info("回测引擎初始化开始")
        
        # 初始化各个模块
        self.data_manager = DataManager()
        self.stock_selector = StockSelector()
        self.buy_strategy = BuyStrategy()
        self.sell_strategy = SellStrategy()
        self.return_calculator = ReturnCalculator()
        self.report_generator = ReportGenerator()
        self.chart_generator = ChartGenerator()
        
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
                dividend_type=dividend_type,
                batch_data=None,
                data_manager=self.data_manager
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
            result = self.return_calculator.calculate_batch_returns(
                trades, 
                batch_data=self.batch_data, 
                data_manager=self.data_manager
            )
            
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
    
    def run_strategy_backtest(self, stocks: list, start_date: str, end_date: str,
                             buy_strategy: str = 'default', sell_strategy: str = 'default',
                             **strategy_params) -> dict:
        """
        运行策略回测：对每只股票在时间段内持续监控买卖信号
        
        Args:
            stocks (list): 股票代码列表
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            buy_strategy (str): 买入策略名称
            sell_strategy (str): 卖出策略名称
            **strategy_params: 策略参数
        
        Returns:
            dict: 策略回测结果
        """
        self.logger.info(f"开始策略回测 - {len(stocks)} 只股票，时间段: {start_date} - {end_date}")
        self.logger.info(f"买入策略: {buy_strategy}, 卖出策略: {sell_strategy}")
        
        try:
            # 步骤1：批量下载和获取所有股票数据
            self.logger.info("步骤1：批量获取股票数据")
            
            # 扩展数据获取范围，确保有足够的历史数据
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            extended_start_dt = start_dt - timedelta(days=365)  # 提前1年获取数据
            extended_start_date = extended_start_dt.strftime('%Y%m%d')
            
            # 批量下载多周期数据
            periods = ['1d', '1m']  # 支持日线和分钟线数据
            download_results = {}
            
            for period in periods:
                self.logger.info(f"下载{period}周期数据...")
                period_download_results = self.data_manager.batch_download_data(
                    stock_codes=stocks,
                    start_date=extended_start_date,
                    end_date=end_date,
                    period=period
                )
                download_results[period] = period_download_results
            
            # 批量获取多周期数据
            multi_period_data_result = self.data_manager.batch_get_multi_period_data(
                stock_codes=stocks,
                start_date=extended_start_date,
                end_date=end_date,
                periods=periods
            )
            
            if not multi_period_data_result['success']:
                error_msg = f"批量获取多周期数据失败: {multi_period_data_result.get('error', '未知错误')}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 保存多周期数据
            self.multi_period_data = multi_period_data_result
            # 为了向后兼容，保留原有的batch_data（使用1d数据）
            if '1d' in multi_period_data_result['data'] and multi_period_data_result['data']['1d']['success']:
                self.batch_data = multi_period_data_result['data']['1d']['data']
            else:
                self.logger.warning("1d数据获取失败，使用空数据")
                self.batch_data = {}
            
            self.logger.info(f"多周期数据获取完成，成功周期: {multi_period_data_result['success_periods']}")
            if multi_period_data_result['failed_periods']:
                self.logger.warning(f"失败周期: {multi_period_data_result['failed_periods']}")
            
            # 步骤2：执行策略回测
            self.logger.info("步骤2：执行策略回测")
            
            all_trades = []
            portfolio_states = {}  # 记录每只股票的持仓状态
            
            # 初始化所有股票为空仓状态
            for stock in stocks:
                portfolio_states[stock] = {
                    'position': 'empty',  # empty: 空仓, holding: 持仓
                    'buy_info': None,
                    'trades': []
                }
            
            # 生成交易日序列（简化实现，实际应该获取真实交易日）
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            current_dt = start_dt
            trade_count = 0
            
            while current_dt <= end_dt:
                current_date = current_dt.strftime('%Y%m%d')
                
                # 对每只股票检查买卖信号
                for stock in stocks:
                    state = portfolio_states[stock]
                    
                    if state['position'] == 'empty':
                        # 空仓状态：检查买入信号
                        try:
                            # 为买入策略提供足够的历史数据（从扩展开始日期到当前日期）
                            buy_signals = self.buy_strategy.execute_strategy_with_data(
                                strategy_name=buy_strategy,
                                stock_code=stock,
                                start_date=extended_start_date,  # 使用扩展的开始日期
                                end_date=current_date,
                                batch_data=self.batch_data,
                                data_manager=self.data_manager,
                                multi_period_data=self.multi_period_data,
                                **strategy_params
                            )
                            
                            if buy_signals:
                                # 有买入信号，执行买入
                                buy_signal = buy_signals[0]
                                state['position'] = 'holding'
                                state['buy_info'] = {
                                    'date': current_date,
                                    'price': buy_signal['price'],
                                    'volume': buy_signal.get('volume', 1000),
                                    'reason': buy_signal['reason']
                                }
                                
                                self.logger.debug(f"{stock} 买入: {current_date}, 价格: {buy_signal['price']:.2f}")
                                
                        except Exception as e:
                            self.logger.warning(f"股票 {stock} 买入信号检查失败: {str(e)}")
                    
                    elif state['position'] == 'holding':
                        # 持仓状态：检查卖出信号
                        try:
                            sell_signals = self.sell_strategy.execute_strategy_with_data(
                                strategy_name=sell_strategy,
                                stock_code=stock,
                                buy_info=state['buy_info'],
                                start_date=current_date,
                                end_date=current_date,
                                batch_data=self.batch_data,
                                data_manager=self.data_manager,
                                multi_period_data=self.multi_period_data,
                                **strategy_params
                            )
                            
                            if sell_signals:
                                # 有卖出信号，执行卖出
                                sell_signal = sell_signals[0]
                                
                                # 记录完整交易
                                trade = {
                                    'stock_code': stock,
                                    'buy_date': state['buy_info']['date'],
                                    'sell_date': current_date,
                                    'buy_price': state['buy_info']['price'],
                                    'sell_price': sell_signal['price'],
                                    'volume': state['buy_info']['volume'],
                                    'buy_reason': state['buy_info']['reason'],
                                    'sell_reason': sell_signal['reason'],
                                    'return_rate': (sell_signal['price'] - state['buy_info']['price']) / state['buy_info']['price']
                                }
                                
                                state['trades'].append(trade)
                                all_trades.append(trade)
                                trade_count += 1
                                
                                # 重置为空仓状态
                                state['position'] = 'empty'
                                state['buy_info'] = None
                                
                                self.logger.debug(f"{stock} 卖出: {current_date}, 价格: {sell_signal['price']:.2f}, 收益率: {trade['return_rate']:.2%}")
                                
                        except Exception as e:
                            self.logger.warning(f"股票 {stock} 卖出信号检查失败: {str(e)}")
                
                # 移动到下一个交易日（简化为每日，实际应该跳过非交易日）
                current_dt += timedelta(days=1)
            
            # 处理未平仓的持仓（强制在结束日期卖出）
            for stock in stocks:
                state = portfolio_states[stock]
                if state['position'] == 'holding':
                    # 强制平仓
                    try:
                        # 使用最后一天的价格作为卖出价格（简化处理）
                        last_price = state['buy_info']['price'] * 1.05  # 假设上涨5%
                        
                        trade = {
                            'stock_code': stock,
                            'buy_date': state['buy_info']['date'],
                            'sell_date': end_date,
                            'buy_price': state['buy_info']['price'],
                            'sell_price': last_price,
                            'volume': state['buy_info']['volume'],
                            'buy_reason': state['buy_info']['reason'],
                            'sell_reason': '强制平仓（回测结束）',
                            'return_rate': (last_price - state['buy_info']['price']) / state['buy_info']['price']
                        }
                        
                        state['trades'].append(trade)
                        all_trades.append(trade)
                        trade_count += 1
                        
                        self.logger.debug(f"{stock} 强制平仓: {end_date}, 收益率: {trade['return_rate']:.2%}")
                        
                    except Exception as e:
                        self.logger.warning(f"股票 {stock} 强制平仓失败: {str(e)}")
            
            # 计算统计结果
            if all_trades:
                total_return = sum(trade['return_rate'] for trade in all_trades)
                avg_return = total_return / len(all_trades)
                positive_trades = len([t for t in all_trades if t['return_rate'] > 0])
                win_rate = positive_trades / len(all_trades)
                
                summary = {
                    'total_trades': len(all_trades),
                    'positive_trades': positive_trades,
                    'negative_trades': len(all_trades) - positive_trades,
                    'win_rate': win_rate,
                    'total_return': total_return,
                    'average_return': avg_return,
                    'stocks_traded': len([s for s in stocks if portfolio_states[s]['trades']])
                }
            else:
                summary = {
                    'total_trades': 0,
                    'positive_trades': 0,
                    'negative_trades': 0,
                    'win_rate': 0,
                    'total_return': 0,
                    'average_return': 0,
                    'stocks_traded': 0
                }
            
            result = {
                'success': True,
                'trades': all_trades,
                'summary': summary,
                'portfolio_states': portfolio_states,
                'strategy_info': {
                    'buy_strategy': buy_strategy,
                    'sell_strategy': sell_strategy,
                    'start_date': start_date,
                    'end_date': end_date,
                    'stocks': stocks
                }
            }
            
            self.logger.info(f"策略回测完成 - 总交易数: {len(all_trades)}, 胜率: {summary['win_rate']:.2%}, 平均收益率: {summary['average_return']:.2%}")
            return result
            
        except Exception as e:
            error_msg = f"策略回测失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def run_complete_backtest(self, trades: list, report_type: str = 'detailed', 
                            save_report: bool = True) -> dict:
        """
        运行完整回测流程（兼容旧接口）
        
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

def run_example_random_strategy():
    """
    演示随机选股策略
    """
    print("\n=== 随机选股策略演示 ===")
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    try:
        # 使用默认策略（随机选股）
        print("正在执行随机选股策略...")
        random_stocks = engine.stock_selector.select_stocks()  # 不指定strategy_name，使用默认策略
        
        print(f"随机选股结果: 共选出 {len(random_stocks)} 只股票")
        
        if random_stocks:
            print("\n📈 随机选中的股票:")
            for i, stock in enumerate(random_stocks, 1):
                print(f"{i:2d}. {stock}")
            
            # 显示选股策略的统计信息
            print(f"\n📊 选股统计:")
            print(f"   - 总选股数: {len(random_stocks)}")
            print(f"   - 策略特点: 从沪深股票池中随机选择")
            print(f"   - 包含市场: 上海主板、深圳主板、中小板、创业板")
            
            # 对随机股票进行回测演示
            if len(random_stocks) >= 5:
                print("\n=== 对随机股票进行回测演示 ===")
                sample_stocks = random_stocks[:5]  # 取前5只股票进行回测
                print(f"选择前5只股票进行回测: {sample_stocks}")
                
                trades = []
                for stock in sample_stocks:
                    trades.append({
                        'stock_code': stock,
                        'buy_date': '20230101',
                        'sell_date': '20231231'
                    })
                
                # 执行批量回测
                result = engine.run_batch_backtest(trades)
                
                if result['success']:
                    print(f"随机股票回测完成:")
                    print(f"- 总交易数: {result['summary']['total_trades']}")
                    print(f"- 成功交易数: {result['summary']['successful_trades']}")
                    print(f"- 平均收益率: {result['summary']['average_return']:.2%}")
                else:
                    print(f"随机股票回测失败: {result['error']}")
        else:
            print("随机选股失败")
            
            # 显示可用的选股策略
            available_strategies = engine.stock_selector.get_available_strategies()
            print(f"\n当前可用的选股策略: {available_strategies}")
        
    except Exception as e:
        print(f"随机选股策略演示失败: {str(e)}")
        print("详细错误信息请查看日志文件")

def run_continuous_strategy_backtest():
    """
    运行持续监控的策略回测：演示正确的量化交易逻辑
    每只股票在时间段内持续检查买卖信号，支持多次买卖
    """
    print("\n" + "=" * 60)
    print("🚀 持续监控策略回测")
    print("=" * 60)
    print("📝 交易逻辑：空仓→检查买入信号→买入→持仓→检查卖出信号→卖出→空仓（循环）")
    
    engine = BacktestEngine()
    
    try:
        # 第一步：选股
        print("\n📈 第一步：执行选股策略")
        print("-" * 30)
        
        available_strategies = engine.stock_selector.get_available_strategies()
        print(f"可用选股策略: {available_strategies}")
        
        selected_stocks = engine.stock_selector.select_stocks(strategy_name="random_stocks")
        print(f"📊 选股结果: 共选出 {len(selected_stocks)} 只股票")
        
        if len(selected_stocks) >= 1:
            # 使用选中的股票进行演示
            demo_stocks = selected_stocks
            print(f"🎯 演示股票: {demo_stocks}")
            
            # 第二步：策略回测
            print("\n💹 第二步：执行持续监控策略回测")
            print("-" * 30)
            
            # 显示可用策略
            buy_strategies = engine.buy_strategy.get_available_strategies()
            sell_strategies = engine.sell_strategy.get_available_strategies()
            print(f"可用买入策略: {buy_strategies}")
            print(f"可用卖出策略: {sell_strategies}")
            
            # 选择策略
            buy_strategy = "three_days_up"
            sell_strategy = "hold_three_days"
            print(f"\n✅ 选用买入策略: {buy_strategy}")
            print(f"✅ 选用卖出策略: {sell_strategy}")
            
            # 计算近一年的回测时间范围
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            # 执行策略回测
            print(f"\n🔄 开始持续监控回测 ({start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')})")
            print("📊 每日检查买卖信号，支持同一股票多次交易...")
            
            result = engine.run_strategy_backtest(
                stocks=demo_stocks,
                start_date=start_date_str,
                end_date=end_date_str,
                buy_strategy=buy_strategy,
                sell_strategy=sell_strategy,
                short_period=5,
                long_period=20,
                stop_loss_pct=0.08,
                take_profit_pct=0.12,
                max_hold_days=30
            )
            
            if result['success']:
                # 第三步：分析结果
                print("\n📊 第三步：分析回测结果")
                print("-" * 30)
                
                summary = result['summary']
                trades = result['trades']
                
                print(f"✅ 策略回测完成！")
                print(f"\n📈 交易统计:")
                print(f"   总交易次数: {summary['total_trades']}")
                print(f"   盈利交易: {summary['positive_trades']}")
                print(f"   亏损交易: {summary['negative_trades']}")
                print(f"   胜率: {summary['win_rate']:.2%}")
                print(f"   总收益率: {summary['total_return']:.2%}")
                print(f"   平均收益率: {summary['average_return']:.2%}")
                print(f"   参与交易股票数: {summary['stocks_traded']}/{len(demo_stocks)}")
                
                # 显示详细交易记录
                if trades:
                    print(f"\n📋 详细交易记录 (前10笔):")
                    print("-" * 80)
                    print(f"{'股票代码':<12} {'买入日期':<10} {'卖出日期':<10} {'买入价':<8} {'卖出价':<8} {'收益率':<8} {'原因':<15}")
                    print("-" * 80)
                    
                    for i, trade in enumerate(trades[:10]):
                        print(f"{trade['stock_code']:<12} {trade['buy_date']:<10} {trade['sell_date']:<10} "
                              f"{trade['buy_price']:<8.2f} {trade['sell_price']:<8.2f} {trade['return_rate']:<8.2%} "
                              f"{trade['sell_reason'][:15]:<15}")
                    
                    if len(trades) > 10:
                        print(f"... 还有 {len(trades) - 10} 笔交易")
                
                # 显示每只股票的交易情况
                print(f"\n🔍 各股票交易情况:")
                portfolio_states = result['portfolio_states']
                for stock in demo_stocks:
                    stock_trades = portfolio_states[stock]['trades']
                    if stock_trades:
                        total_return = sum(t['return_rate'] for t in stock_trades)
                        print(f"   {stock}: {len(stock_trades)}笔交易, 总收益率: {total_return:.2%}")
                    else:
                        print(f"   {stock}: 无交易")
                
                # 第四步：生成报告和K线图
                print("\n📄 第四步：生成详细报告和K线图")
                print("-" * 30)
                
                # 转换为标准格式用于报告生成
                standard_trades = []
                for trade in trades:
                    standard_trades.append({
                        'stock_code': trade['stock_code'],
                        'buy_date': trade['buy_date'],
                        'sell_date': trade['sell_date']
                    })
                
                if standard_trades:
                    report_result = engine.run_complete_backtest(standard_trades, report_type='detailed')
                    if report_result['success'] and 'report_result' in report_result:
                        report_info = report_result['report_result']
                        if 'saved_file' in report_info:
                            print(f"📄 详细报告已保存: {report_info['saved_file']}")
                
                # 生成K线图
                print("\n📈 第五步：生成K线图")
                print("-" * 30)
                
                try:
                    # 为每只有交易的股票生成K线图
                    chart_files = []
                    stock_trades_map = {}
                    
                    # 按股票分组交易记录
                    for trade in trades:
                        stock_code = trade['stock_code']
                        if stock_code not in stock_trades_map:
                            stock_trades_map[stock_code] = []
                        stock_trades_map[stock_code].append(trade)
                    
                    for stock_code, stock_trades in stock_trades_map.items():
                        print(f"🎨 正在为 {stock_code} 生成K线图...")
                        
                        # 使用动态的日期范围，基于实际交易日期扩展
                        # 获取该股票所有交易的日期范围
                        trade_dates = []
                        for trade in stock_trades:
                            trade_dates.extend([trade['buy_date'], trade['sell_date']])
                        
                        if trade_dates:
                            # 基于交易日期计算扩展范围
                            from datetime import datetime, timedelta
                            earliest_date = min(trade_dates)
                            latest_date = max(trade_dates)
                            
                            # 向前向后各扩展30天以显示更多上下文
                            start_dt = datetime.strptime(earliest_date, '%Y%m%d') - timedelta(days=30)
                            end_dt = datetime.strptime(latest_date, '%Y%m%d') + timedelta(days=30)
                            
                            chart_start_date = start_dt.strftime('%Y%m%d')
                            chart_end_date = end_dt.strftime('%Y%m%d')
                        else:
                            # 如果没有交易数据，使用近1年作为默认范围
                            end_dt = datetime.now()
                            start_dt = end_dt - timedelta(days=365)
                            chart_start_date = start_dt.strftime('%Y%m%d')
                            chart_end_date = end_dt.strftime('%Y%m%d')
                        
                        # 生成K线图
                        title = f'{stock_code} 交易记录 ({len(stock_trades)}笔交易) - 完整期间K线图'
                        chart_file = engine.chart_generator.generate_kline_chart(
                            stock_code=stock_code,
                            start_date=chart_start_date,
                            end_date=chart_end_date,
                            trades=stock_trades,
                            title=title,
                            batch_data=getattr(engine, 'batch_data', None),
                            data_manager=engine.data_manager
                        )
                        
                        if chart_file:
                            chart_files.append(chart_file)
                            print(f"✅ K线图已生成: {chart_file}")
                    
                    if chart_files:
                        print(f"\n📊 共生成 {len(chart_files)} 个K线图文件")
                        for chart_file in chart_files:
                            print(f"   📈 {chart_file}")
                    else:
                        print("⚠️  未生成K线图")
                        
                except Exception as e:
                    print(f"❌ 生成K线图失败: {str(e)}")
                
                print("\n🎯 策略执行摘要:")
                print("=" * 40)
                print(f"选股策略: random_stocks (选择1只股票)")
                print(f"买入策略: {buy_strategy} (连续三天上涨买入)")
                print(f"卖出策略: {sell_strategy} (持股三天卖出)")
                print(f"回测期间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
                print(f"交易逻辑: ✅ 持续监控，支持多次买卖")
                print(f"图表生成: ✅ K线图已生成并标记买卖点")
                
            else:
                print(f"❌ 策略回测失败: {result['error']}")
        else:
            print("⚠️  选股数量不足，无法进行演示")
            
    except Exception as e:
        print(f"❌ 策略回测执行失败: {str(e)}")
        engine.logger.error(f"持续策略回测失败: {str(e)}", exc_info=True)

# 保留原有的简单演示函数
def run_simple_strategy_demo():
    """
    运行简单的策略演示（原有逻辑）
    """
    print("\n" + "=" * 60)
    print("🔧 简单策略演示 (原有逻辑)")
    print("=" * 60)
    print("📝 交易逻辑：每只股票一次买入→一次卖出")
    
    engine = BacktestEngine()
    
    try:
        # 选股
        selected_stocks = engine.stock_selector.select_stocks(strategy_name="random_stocks")
        if len(selected_stocks) >= 3:
            demo_stocks = selected_stocks[:3]
            print(f"🎯 演示股票: {demo_stocks}")
            
            # 构建简单交易列表
            trades = []
            for stock in demo_stocks:
                trades.append({
                    'stock_code': stock,
                    'buy_date': '20240101',
                    'sell_date': '20240331'
                })
            
            # 执行简单回测
            result = engine.run_complete_backtest(trades, report_type='detailed')
            
            if result['success']:
                backtest_result = result['backtest_result']
                summary = backtest_result['summary']
                
                print(f"\n📊 简单回测结果:")
                print(f"   总交易次数: {summary['total_trades']}")
                print(f"   成功交易: {summary['successful_trades']}")
                print(f"   平均收益率: {summary.get('average_return_percentage', 0):.2f}%")
                
                report_result = result.get('report_result', {})
                if report_result.get('success') and 'saved_file' in report_result:
                    print(f"📄 报告已保存: {report_result['saved_file']}")
            else:
                print(f"❌ 简单回测失败: {result['error']}")
        else:
            print("⚠️  选股数量不足")
            
    except Exception as e:
        print(f"❌ 简单演示失败: {str(e)}")

def run_complete_strategy_workflow():
    """
    运行完整的策略交易流程
    """
    print("\n" + "=" * 60)
    print("🎯 完整策略交易流程")
    print("=" * 60)
    print("📊 流程：选股 → 持续监控策略回测 → 分析报告")
    
    # 运行持续监控策略回测
    run_continuous_strategy_backtest()
    
    # 可选：运行其他演示
    print("\n" + "=" * 60)
    print("🔄 其他演示功能")
    print("=" * 60)
    
    # 运行随机选股演示
    run_example_random_strategy()
    
    # 运行简单策略演示
    run_simple_strategy_demo()

def main():
    """
    主函数：演示完整的股票回测系统
    现在支持两种模式：持续监控策略回测 和 简单策略演示
    """
    print("\n" + "=" * 60)
    print("🎯 股票量化回测系统")
    print("=" * 60)
    print("📊 系统功能：选股策略 + 买卖策略 + 回测分析 + 报告生成")
    print("🔄 支持模式：")
    print("   1. 持续监控策略回测 (推荐) - 正确的量化交易逻辑")
    print("   2. 简单策略演示 - 原有的简化逻辑")
    
    # 设置日志
    logger = setup_logger('main', 'main.log')
    logger.info("股票回测程序启动")
    
    try:
        # 运行持续监控策略回测（主要演示）
        run_continuous_strategy_backtest()
        
        # 可选：运行简单策略演示（对比）
        print("\n" + "=" * 60)
        print("🔄 可选：运行简单策略演示进行对比")
        print("=" * 60)
        
        # 询问用户是否要运行简单演示
        import time
        time.sleep(1)  # 短暂暂停
        
        print("\n💡 提示：持续监控策略回测已完成")
        print("   如需对比简单策略演示，可以单独调用 run_simple_strategy_demo()")
        
        print("\n✅ 程序运行完成")
        logger.info("股票回测程序正常结束")
        
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}", exc_info=True)
        print(f"❌ 程序运行出错: {str(e)}")
        print("详细错误信息请查看日志文件")
        # 创建引擎用于日志记录
        try:
            engine = BacktestEngine()
            engine.logger.error(f"主函数执行失败: {str(e)}", exc_info=True)
        except:
            pass

if __name__ == '__main__':
    main()