# coding:utf-8
"""
主程序脚本 - 整合所有模块

提供统一的回测程序入口点，支持单股票测试、批量测试和全量测试
"""

import argparse
import logging
import os
import sys
import shutil
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from data_loader import StockDataLoader, DataPreprocessor
from strategy_engine import StrategyEngine, ModelBasedStrategy
from stock_selector import StockSelector, BatchStockProcessor
from result_analyzer import ResultAnalyzer, ResultExporter, ResultFormatter

# 策略条件描述现在从StrategyEngine动态获取，确保一致性


class BacktestingSystem:
    """回测系统主类"""
    
    def __init__(self, data_folder: str, output_folder: str = None):
        """
        初始化回测系统
        
        Args:
            data_folder: 股票数据文件夹路径
            output_folder: 输出文件夹路径
        """
        self.data_folder = data_folder
        self.output_folder = output_folder or os.path.join(current_dir, "output")
        
        # 确保输出目录存在
        os.makedirs(self.output_folder, exist_ok=True)
        
        # 初始化各个模块
        self.data_loader = StockDataLoader(data_folder)
        self.data_preprocessor = DataPreprocessor()
        self.strategy_engine = StrategyEngine()
        self.stock_selector = StockSelector(data_folder, self.strategy_engine)
        self.result_analyzer = ResultAnalyzer()
        self.result_exporter = ResultExporter()
        
        # 初始化日志相关属性，但不立即配置日志
        self.log_file = None
        self.logger = None
    
    def _setup_logging(self):
        """配置日志系统"""
        if self.logger is not None:
            return  # 日志已经配置过了
            
        self.log_file = os.path.join(self.output_folder, f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # 清除之前的日志配置
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建文件处理器和控制台处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        
        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 配置根日志器
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"日志系统已配置，日志文件: {self.log_file}")
    
    def clear_output_folder(self):
        """清空output文件夹"""
        if os.path.exists(self.output_folder):
            deleted_count = 0
            skipped_count = 0
            
            # 获取当前日志文件名（如果已经配置了日志）
            current_log_filename = None
            if self.log_file:
                current_log_filename = os.path.basename(self.log_file)
            
            for filename in os.listdir(self.output_folder):
                file_path = os.path.join(self.output_folder, filename)
                try:
                    if os.path.isfile(file_path):
                        # 跳过当前会话的日志文件
                        if current_log_filename and filename == current_log_filename:
                            skipped_count += 1
                            continue
                        
                        os.remove(file_path)
                        deleted_count += 1
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"删除文件 {filename} 时出错: {e}")
                    skipped_count += 1
            
            if deleted_count > 0 or skipped_count > 0:
                print(f"已清理输出文件夹: 删除 {deleted_count} 个文件/文件夹，跳过 {skipped_count} 个")
        else:
            # 如果文件夹不存在，创建它
            os.makedirs(self.output_folder, exist_ok=True)
            print(f"创建输出文件夹: {self.output_folder}")
    
    def clear_process_logs(self):
        """清理进程日志文件夹"""
        process_logs_dir = os.path.join(current_dir, "process_logs")
        if os.path.exists(process_logs_dir):
            try:
                shutil.rmtree(process_logs_dir)
                self.logger.info(f"已清理进程日志文件夹: {process_logs_dir}")
            except Exception as e:
                self.logger.warning(f"清理进程日志文件夹失败: {e}")
        
        # 重新创建进程日志文件夹
        os.makedirs(process_logs_dir, exist_ok=True)
        self.logger.info(f"已创建进程日志文件夹: {process_logs_dir}")
    
    def write_backtest_result_to_file(self, total_count, next_open_up_count, next_close_up_count, 
                                     high_open_high_close_count, day3_up_count, day5_up_count, day10_up_count,
                                     high_open_high_close_day3_up, high_open_high_close_day5_up, high_open_high_close_day10_up,
                                     low_open_close_up_count, low_open_close_up_day3_up, 
                                     low_open_close_up_day5_up, low_open_close_up_day10_up,
                                     low_open_low_close_count, low_open_low_close_day3_up,
                                     low_open_low_close_day5_up, low_open_low_close_day10_up,
                                     result_df):
        """
        将回测结果以增量方式写入final_result文件
        """
        try:
            # 获取当前时间戳
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 计算百分比，避免除零错误
            next_open_up_pct = (next_open_up_count/total_count*100) if total_count > 0 else 0.00
            next_close_up_pct = (next_close_up_count/total_count*100) if total_count > 0 else 0.00
            high_open_high_close_pct = (high_open_high_close_count/total_count*100) if total_count > 0 else 0.00
            low_open_close_up_pct = (low_open_close_up_count/total_count*100) if total_count > 0 else 0.00
            day3_up_pct = (day3_up_count/total_count*100) if total_count > 0 else 0.00
            day5_up_pct = (day5_up_count/total_count*100) if total_count > 0 else 0.00
            day10_up_pct = (day10_up_count/total_count*100) if total_count > 0 else 0.00
            
            high_open_high_close_day3_up_pct = (high_open_high_close_day3_up/high_open_high_close_count*100) if high_open_high_close_count > 0 else 0.00
            high_open_high_close_day5_up_pct = (high_open_high_close_day5_up/high_open_high_close_count*100) if high_open_high_close_count > 0 else 0.00
            high_open_high_close_day10_up_pct = (high_open_high_close_day10_up/high_open_high_close_count*100) if high_open_high_close_count > 0 else 0.00
            
            # 计算次日低开收盘上涨的百分比
            low_open_close_up_day3_up_pct = (low_open_close_up_day3_up/low_open_close_up_count*100) if low_open_close_up_count > 0 else 0.00
            low_open_close_up_day5_up_pct = (low_open_close_up_day5_up/low_open_close_up_count*100) if low_open_close_up_count > 0 else 0.00
            low_open_close_up_day10_up_pct = (low_open_close_up_day10_up/low_open_close_up_count*100) if low_open_close_up_count > 0 else 0.00
            
            # 计算次日低开低走的百分比
            low_open_low_close_pct = (low_open_low_close_count/total_count*100) if total_count > 0 else 0.00
            low_open_low_close_day3_up_pct = (low_open_low_close_day3_up/low_open_low_close_count*100) if low_open_low_close_count > 0 else 0.00
            low_open_low_close_day5_up_pct = (low_open_low_close_day5_up/low_open_low_close_count*100) if low_open_low_close_count > 0 else 0.00
            low_open_low_close_day10_up_pct = (low_open_low_close_day10_up/low_open_low_close_count*100) if low_open_low_close_count > 0 else 0.00
            
            # 构建统计信息
            statistics_info = f"""
统计信息:
总共符合条件的交易日数: {total_count}
涉及股票数: {result_df['stock_code'].nunique() if len(result_df) > 0 else 0}
关键比例统计:
次日表现:
  次日高开比例: {next_open_up_count}/{total_count} ({next_open_up_pct:.2f}%)
  次日收盘上涨比例: {next_close_up_count}/{total_count} ({next_close_up_pct:.2f}%)
  次日高开高走比例: {high_open_high_close_count}/{total_count} ({high_open_high_close_pct:.2f}%)
  次日低开收盘上涨比例: {low_open_close_up_count}/{total_count} ({low_open_close_up_pct:.2f}%)
  次日低开低走比例: {low_open_low_close_count}/{total_count} ({low_open_low_close_pct:.2f}%)
中长期表现:
  3日收盘上涨比例: {day3_up_count}/{total_count} ({day3_up_pct:.2f}%)
  5日收盘上涨比例: {day5_up_count}/{total_count} ({day5_up_pct:.2f}%)
  10日收盘上涨比例: {day10_up_count}/{total_count} ({day10_up_pct:.2f}%)

次日高开高走股票中的后续表现:
3日收盘上涨比例: {high_open_high_close_day3_up}/{high_open_high_close_count} ({high_open_high_close_day3_up_pct:.2f}%)
5日收盘上涨比例: {high_open_high_close_day5_up}/{high_open_high_close_count} ({high_open_high_close_day5_up_pct:.2f}%)
10日收盘上涨比例: {high_open_high_close_day10_up}/{high_open_high_close_count} ({high_open_high_close_day10_up_pct:.2f}%)

次日低开收盘上涨股票中的后续表现:
3日收盘上涨比例: {low_open_close_up_day3_up}/{low_open_close_up_count} ({low_open_close_up_day3_up_pct:.2f}%)
5日收盘上涨比例: {low_open_close_up_day5_up}/{low_open_close_up_count} ({low_open_close_up_day5_up_pct:.2f}%)
10日收盘上涨比例: {low_open_close_up_day10_up}/{low_open_close_up_count} ({low_open_close_up_day10_up_pct:.2f}%)

次日低开低走股票中的后续表现:
3日收盘上涨比例: {low_open_low_close_day3_up}/{low_open_low_close_count} ({low_open_low_close_day3_up_pct:.2f}%)
5日收盘上涨比例: {low_open_low_close_day5_up}/{low_open_low_close_count} ({low_open_low_close_day5_up_pct:.2f}%)
10日收盘上涨比例: {low_open_low_close_day10_up}/{low_open_low_close_count} ({low_open_low_close_day10_up_pct:.2f}%)"""
            
            # 从StrategyEngine获取策略描述
            strategy_description = self.strategy_engine.get_strategy_description()
            
            # 构建完整的回测记录
            backtest_record = f"""
{'='*80}
回测时间: {current_time}
{strategy_description}

{statistics_info}
{'='*80}

"""
            
            # 确定final_result文件路径
            final_result_path = os.path.join(current_dir, "final_result")
            
            # 以追加模式写入文件，确保使用UTF-8编码（不使用BOM）
            with open(final_result_path, 'a', encoding='utf-8') as f:
                f.write(backtest_record)
            
            self.logger.info(f"回测结果已追加写入: {final_result_path}")
            
        except Exception as e:
            self.logger.error(f"写入final_result文件失败: {e}")
    
    def calculate_detailed_statistics(self, signals: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        计算详细的统计数据，用于生成测试简报
        
        Args:
            signals: 信号列表
            
        Returns:
            Dict[str, int]: 统计数据
        """
        if not signals:
            return {
                'total_count': 0,
                'next_open_up_count': 0,
                'next_close_up_count': 0,
                'high_open_high_close_count': 0,
                'day3_up_count': 0,
                'day5_up_count': 0,
                'day10_up_count': 0,
                'high_open_high_close_day3_up': 0,
                'high_open_high_close_day5_up': 0,
                'high_open_high_close_day10_up': 0,
                'low_open_close_up_count': 0,
                'low_open_close_up_day3_up': 0,
                'low_open_close_up_day5_up': 0,
                'low_open_close_up_day10_up': 0,
                'low_open_low_close_count': 0,
                'low_open_low_close_day3_up': 0,
                'low_open_low_close_day5_up': 0,
                'low_open_low_close_day10_up': 0
            }
        
        total_count = len(signals)
        next_open_up_count = len([s for s in signals if s.get('next_open_change_pct', 0) > 0])
        next_close_up_count = len([s for s in signals if s.get('next_close_change_pct', 0) > 0])
        
        # 筛选次日高开高走的股票
        high_open_high_close_signals = [s for s in signals if s.get('next_open_change_pct', 0) > 0 and s.get('next_close_change_pct', 0) > 0]
        high_open_high_close_count = len(high_open_high_close_signals)
        
        # 筛选次日低开收盘上涨的股票
        low_open_close_up_signals = [s for s in signals if s.get('next_open_change_pct', 0) < 0 and s.get('next_close_change_pct', 0) > 0]
        low_open_close_up_count = len(low_open_close_up_signals)
        
        # 筛选次日低开低走的股票
        low_open_low_close_signals = [s for s in signals if s.get('next_open_change_pct', 0) < 0 and s.get('next_close_change_pct', 0) < 0]
        low_open_low_close_count = len(low_open_low_close_signals)
        
        # 计算中长期表现
        day3_up_count = len([s for s in signals if s.get('day3_change_pct') is not None and s.get('day3_change_pct', 0) > 0])
        day5_up_count = len([s for s in signals if s.get('day5_change_pct') is not None and s.get('day5_change_pct', 0) > 0])
        day10_up_count = len([s for s in signals if s.get('day10_change_pct') is not None and s.get('day10_change_pct', 0) > 0])
        
        # 计算次日高开高走股票中的后续表现
        high_open_high_close_day3_up = len([s for s in high_open_high_close_signals if s.get('day3_change_pct') is not None and s.get('day3_change_pct', 0) > 0])
        high_open_high_close_day5_up = len([s for s in high_open_high_close_signals if s.get('day5_change_pct') is not None and s.get('day5_change_pct', 0) > 0])
        high_open_high_close_day10_up = len([s for s in high_open_high_close_signals if s.get('day10_change_pct') is not None and s.get('day10_change_pct', 0) > 0])
        
        # 计算次日低开收盘上涨股票中的后续表现
        low_open_close_up_day3_up = len([s for s in low_open_close_up_signals if s.get('day3_change_pct') is not None and s.get('day3_change_pct', 0) > 0])
        low_open_close_up_day5_up = len([s for s in low_open_close_up_signals if s.get('day5_change_pct') is not None and s.get('day5_change_pct', 0) > 0])
        low_open_close_up_day10_up = len([s for s in low_open_close_up_signals if s.get('day10_change_pct') is not None and s.get('day10_change_pct', 0) > 0])
        
        # 计算次日低开低走股票中的后续表现
        low_open_low_close_day3_up = len([s for s in low_open_low_close_signals if s.get('day3_change_pct') is not None and s.get('day3_change_pct', 0) > 0])
        low_open_low_close_day5_up = len([s for s in low_open_low_close_signals if s.get('day5_change_pct') is not None and s.get('day5_change_pct', 0) > 0])
        low_open_low_close_day10_up = len([s for s in low_open_low_close_signals if s.get('day10_change_pct') is not None and s.get('day10_change_pct', 0) > 0])
        
        return {
            'total_count': total_count,
            'next_open_up_count': next_open_up_count,
            'next_close_up_count': next_close_up_count,
            'high_open_high_close_count': high_open_high_close_count,
            'day3_up_count': day3_up_count,
            'day5_up_count': day5_up_count,
            'day10_up_count': day10_up_count,
            'high_open_high_close_day3_up': high_open_high_close_day3_up,
            'high_open_high_close_day5_up': high_open_high_close_day5_up,
            'high_open_high_close_day10_up': high_open_high_close_day10_up,
            'low_open_close_up_count': low_open_close_up_count,
            'low_open_close_up_day3_up': low_open_close_up_day3_up,
            'low_open_close_up_day5_up': low_open_close_up_day5_up,
            'low_open_close_up_day10_up': low_open_close_up_day10_up,
            'low_open_low_close_count': low_open_low_close_count,
            'low_open_low_close_day3_up': low_open_low_close_day3_up,
            'low_open_low_close_day5_up': low_open_low_close_day5_up,
            'low_open_low_close_day10_up': low_open_low_close_day10_up
        }
    
    def test_single_stock(self, stock_code: str, verbose: bool = True, 
                         target_date: str = None) -> Dict[str, Any]:
        """
        测试单个股票
        
        Args:
            stock_code: 股票代码
            verbose: 是否显示详细信息
            target_date: 目标日期 (YYYY-MM-DD)，用于详细测试
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        # 配置日志系统
        self._setup_logging()
        
        # 清空输出文件夹和进程日志
        self.clear_output_folder()
        self.clear_process_logs()
        
        self.logger.info(f"开始单股票测试: {stock_code}")
        
        try:
            if target_date:
                # 详细测试特定日期
                result = self.stock_selector.test_single_stock_verbose(stock_code, target_date)
                
                if verbose and 'error' not in result:
                    print(f"\n股票 {stock_code} 在 {target_date} 的详细检查结果:")
                    print(f"策略条件满足: {'是' if result.get('strategy_met', False) else '否'}")
                    
                    if 'condition_details' in result:
                        print("\n各条件检查结果:")
                        for condition, details in result['condition_details'].items():
                            status = "✓" if details.get('met', False) else "✗"
                            print(f"  {status} {condition}: {details.get('description', '')}")
                    
                    if 'market_data' in result:
                        market_data = result['market_data']
                        print(f"\n市场数据:")
                        print(f"  收盘价: {market_data.get('close', 'N/A')}")
                        print(f"  成交量: {market_data.get('volume', 'N/A')}")
                        if 'next_day_return' in market_data:
                            print(f"  次日收益: {market_data['next_day_return']:.2f}%")
                
                return result
            else:
                # 扫描所有信号
                signals = self.stock_selector.test_single_stock(stock_code, verbose)
                
                if verbose:
                    print(f"\n股票 {stock_code} 信号扫描结果:")
                    print(f"找到 {len(signals)} 个符合条件的信号")
                    
                    if signals:
                        print("\n信号详情:")
                        for i, signal in enumerate(signals[:10], 1):  # 只显示前10个
                            print(f"  {i}. {ResultFormatter.format_signal_for_display(signal)}")
                        
                        if len(signals) > 10:
                            print(f"  ... 还有 {len(signals) - 10} 个信号")
                
                # 生成测试简报
                if signals:
                    result_df = pd.DataFrame(signals)
                    stats = self.calculate_detailed_statistics(signals)
                    self.write_backtest_result_to_file(
                        stats['total_count'], stats['next_open_up_count'], stats['next_close_up_count'],
                        stats['high_open_high_close_count'], stats['day3_up_count'], stats['day5_up_count'], stats['day10_up_count'],
                        stats['high_open_high_close_day3_up'], stats['high_open_high_close_day5_up'], stats['high_open_high_close_day10_up'],
                        stats['low_open_close_up_count'], stats['low_open_close_up_day3_up'], 
                        stats['low_open_close_up_day5_up'], stats['low_open_close_up_day10_up'],
                        stats['low_open_low_close_count'], stats['low_open_low_close_day3_up'],
                        stats['low_open_low_close_day5_up'], stats['low_open_low_close_day10_up'],
                        result_df
                    )
                
                return {
                    'stock_code': stock_code,
                    'signals': signals,
                    'total_signals': len(signals)
                }
                
        except Exception as e:
            error_msg = f"测试股票 {stock_code} 时出错: {e}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def test_batch_stocks(self, stock_codes: List[str], num_processes: int = 4, 
                         save_results: bool = True) -> Dict[str, Any]:
        """
        批量测试多个股票
        
        Args:
            stock_codes: 股票代码列表
            num_processes: 进程数量
            save_results: 是否保存结果
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        # 配置日志系统
        self._setup_logging()
        
        # 清空输出文件夹和进程日志
        self.clear_output_folder()
        self.clear_process_logs()

        self.logger.info(f"开始批量测试 {len(stock_codes)} 个股票")
        
        try:
            # 执行批量测试
            result_df = self.stock_selector.test_batch_stocks(stock_codes, num_processes)
            
            if result_df.empty:
                self.logger.warning("批量测试未找到任何信号")
                return {
                    'stock_codes': stock_codes,
                    'signals': [],
                    'total_signals': 0,
                    'result_df': result_df
                }
            
            # 转换为信号列表
            signals = result_df.to_dict('records')
            
            # 分析结果
            analysis = self.result_analyzer.analyze_signals(signals)
            portfolio_perf = self.result_analyzer.calculate_portfolio_performance(signals)
            
            # 显示摘要
            print(f"\n批量测试完成:")
            print(f"  测试股票数量: {len(stock_codes)}")
            print(f"  找到信号数量: {len(signals)}")
            print(f"  涉及股票数量: {analysis.get('basic_stats', {}).get('unique_stocks', 0)}")
            
            if 'error' not in portfolio_perf:
                print(f"\n投资组合表现:")
                print(f"  总收益率: {portfolio_perf.get('total_return_pct', 0):.2f}%")
                print(f"  胜率: {portfolio_perf.get('win_rate_pct', 0):.2f}%")
                print(f"  最大回撤: {portfolio_perf.get('max_drawdown_pct', 0):.2f}%")
            
            # 保存结果
            if save_results:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = os.path.join(self.output_folder, f"batch_test_{timestamp}.csv")
                # 只导出CSV数据文件，不生成额外的分析文件
                self.result_exporter.export_to_csv(signals, output_file, include_analysis=False)
            
            # 生成测试简报
            stats = self.calculate_detailed_statistics(signals)
            self.write_backtest_result_to_file(
                stats['total_count'], stats['next_open_up_count'], stats['next_close_up_count'],
                stats['high_open_high_close_count'], stats['day3_up_count'], stats['day5_up_count'], stats['day10_up_count'],
                stats['high_open_high_close_day3_up'], stats['high_open_high_close_day5_up'], stats['high_open_high_close_day10_up'],
                stats['low_open_close_up_count'], stats['low_open_close_up_day3_up'], 
                stats['low_open_close_up_day5_up'], stats['low_open_close_up_day10_up'],
                stats['low_open_low_close_count'], stats['low_open_low_close_day3_up'],
                stats['low_open_low_close_day5_up'], stats['low_open_low_close_day10_up'],
                result_df
            )
            
            return {
                'stock_codes': stock_codes,
                'signals': signals,
                'total_signals': len(signals),
                'analysis': analysis,
                'portfolio_performance': portfolio_perf,
                'result_df': result_df
            }
            
        except Exception as e:
            error_msg = f"批量测试时出错: {e}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def test_all_stocks(self, num_processes: int = 20, limit: int = None, 
                       save_results: bool = True) -> Dict[str, Any]:
        """
        测试所有可用股票
        
        Args:
            num_processes: 进程数量
            limit: 限制测试的股票数量
            save_results: 是否保存结果
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        # 配置日志系统
        self._setup_logging()
        
        # 清空输出文件夹和进程日志
        self.clear_output_folder()
        self.clear_process_logs()

        self.logger.info(f"开始全量测试，进程数: {num_processes}")
        
        try:
            # 获取所有可用股票
            all_stock_codes = self.data_loader.get_available_stocks()
            
            if limit:
                all_stock_codes = all_stock_codes[:limit]
                self.logger.info(f"限制测试股票数量为: {limit}")
            
            self.logger.info(f"共找到 {len(all_stock_codes)} 个可用股票")
            
            # 执行全量测试
            result_df = self.stock_selector.test_all_stocks(num_processes, limit)
            
            if result_df.empty:
                self.logger.warning("全量测试未找到任何信号")
                return {
                    'total_stocks': len(all_stock_codes),
                    'signals': [],
                    'total_signals': 0,
                    'result_df': result_df
                }
            
            # 转换为信号列表
            signals = result_df.to_dict('records')
            
            # 分析结果
            analysis = self.result_analyzer.analyze_signals(signals)
            portfolio_perf = self.result_analyzer.calculate_portfolio_performance(signals)
            
            # 显示摘要
            print(f"\n全量测试完成:")
            print(f"  总股票数量: {len(all_stock_codes)}")
            print(f"  找到信号数量: {len(signals)}")
            print(f"  涉及股票数量: {analysis.get('basic_stats', {}).get('unique_stocks', 0)}")
            print(f"  信号覆盖率: {analysis.get('basic_stats', {}).get('unique_stocks', 0) / len(all_stock_codes) * 100:.2f}%")
            
            if 'error' not in portfolio_perf:
                print(f"\n投资组合表现:")
                print(f"  总收益率: {portfolio_perf.get('total_return_pct', 0):.2f}%")
                print(f"  胜率: {portfolio_perf.get('win_rate_pct', 0):.2f}%")
                print(f"  最大回撤: {portfolio_perf.get('max_drawdown_pct', 0):.2f}%")
                print(f"  夏普比率: {portfolio_perf.get('sharpe_ratio', 0):.4f}")
            
            # 保存结果
            if save_results:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # 只导出CSV数据文件和一个报告文件
                output_file = os.path.join(self.output_folder, f"full_test_{timestamp}.csv")
                self.result_exporter.export_to_csv(signals, output_file, include_analysis=False)
                
                # 生成一个简单的报告文件
                report_file = os.path.join(self.output_folder, f"full_report_{timestamp}.txt")
                self.result_analyzer.generate_performance_report(signals, report_file)
            
            # 生成测试简报
            stats = self.calculate_detailed_statistics(signals)
            self.write_backtest_result_to_file(
                stats['total_count'], stats['next_open_up_count'], stats['next_close_up_count'],
                stats['high_open_high_close_count'], stats['day3_up_count'], stats['day5_up_count'], stats['day10_up_count'],
                stats['high_open_high_close_day3_up'], stats['high_open_high_close_day5_up'], stats['high_open_high_close_day10_up'],
                stats['low_open_close_up_count'], stats['low_open_close_up_day3_up'], 
                stats['low_open_close_up_day5_up'], stats['low_open_close_up_day10_up'],
                stats['low_open_low_close_count'], stats['low_open_low_close_day3_up'],
                stats['low_open_low_close_day5_up'], stats['low_open_low_close_day10_up'],
                result_df
            )
            
            return {
                'total_stocks': len(all_stock_codes),
                'signals': signals,
                'total_signals': len(signals),
                'analysis': analysis,
                'portfolio_performance': portfolio_perf,
                'result_df': result_df
            }
            
        except Exception as e:
            error_msg = f"全量测试时出错: {e}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def set_custom_strategy(self, strategy_engine: StrategyEngine):
        """
        设置自定义策略引擎
        
        Args:
            strategy_engine: 自定义策略引擎
        """
        self.strategy_engine = strategy_engine
        self.stock_selector.strategy_engine = strategy_engine
        self.logger.info("已设置自定义策略引擎")
    
    def get_strategy_description(self) -> str:
        """
        获取当前策略描述
        
        Returns:
            str: 策略描述
        """
        return self.strategy_engine.get_strategy_description()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票回测系统')
    parser.add_argument('--data_folder', type=str, 
                        default=r"c:\Users\17701\github\my_first_repo\stockapi\stock_base_info\all_stocks_data",
                        help='股票数据文件夹路径')
    parser.add_argument('--output_folder', type=str, help='输出文件夹路径')
    parser.add_argument('--mode', type=str, choices=['single', 'batch', 'full'], 
                       default='full', help='测试模式')
    parser.add_argument('--stock_code', type=str, help='股票代码（单股票模式）')
    parser.add_argument('--stock_codes', type=str, nargs='+', help='股票代码列表（批量模式）')
    parser.add_argument('--target_date', type=str, help='目标日期 YYYY-MM-DD（详细测试）')
    parser.add_argument('--num_processes', type=int, default=20, help='进程数量')
    parser.add_argument('--limit', type=int, help='限制测试的股票数量')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    parser.add_argument('--no_save', action='store_true', help='不保存结果')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.mode == 'single' and not args.stock_code:
        print("错误: 单股票模式需要指定 --stock_code")
        return
    
    if args.mode == 'batch' and not args.stock_codes:
        print("错误: 批量模式需要指定 --stock_codes")
        return
    
    # 初始化回测系统
    try:
        backtest_system = BacktestingSystem(args.data_folder, args.output_folder)
        
        print("=" * 60)
        print("股票回测系统")
        print("=" * 60)
        print(f"数据文件夹: {args.data_folder}")
        print(f"输出文件夹: {backtest_system.output_folder}")
        print(f"测试模式: {args.mode}")
        print(f"策略描述: {backtest_system.get_strategy_description()}")
        print("=" * 60)
        
        # 根据模式执行测试
        if args.mode == 'single':
            result = backtest_system.test_single_stock(
                args.stock_code, 
                args.verbose, 
                args.target_date
            )
            
            if 'error' in result:
                print(f"错误: {result['error']}")
            else:
                print("单股票测试完成")
        
        elif args.mode == 'batch':
            # 处理股票代码列表，支持逗号分隔的字符串
            stock_codes = []
            for code_item in args.stock_codes:
                if ',' in code_item:
                    # 如果包含逗号，则分割
                    codes = [code.strip() for code in code_item.split(',')]
                else:
                    codes = [code_item.strip()]
                
                # 处理每个股票代码，补齐前导零
                for code in codes:
                    if not code:
                        continue
                    
                    # 检查是否为纯数字（可能缺少前导零）
                    if code.isdigit():
                        # 如果是纯数字且长度小于等于6位，自动补齐前导零
                        if len(code) <= 6:
                            original_code = code
                            code = code.zfill(6)
                            if args.verbose:
                                print(f"股票代码自动补齐前导零: {original_code} -> {code}")
                        elif len(code) > 6:
                            print(f"警告: 股票代码长度超过6位，跳过: {code}")
                            continue
                    
                    # 验证股票代码格式（6位数字）
                    if len(code) == 6 and code.isdigit():
                        stock_codes.append(code)
                    else:
                        print(f"警告: 股票代码格式无效，跳过: {code}")
            
            result = backtest_system.test_batch_stocks(
                stock_codes,
                args.num_processes,
                not args.no_save
            )
            
            if 'error' in result:
                print(f"错误: {result['error']}")
            else:
                print("批量测试完成")
        
        elif args.mode == 'full':
            result = backtest_system.test_all_stocks(
                args.num_processes,
                args.limit,
                not args.no_save
            )
            
            if 'error' in result:
                print(f"错误: {result['error']}")
            else:
                print("全量测试完成")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"系统错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()