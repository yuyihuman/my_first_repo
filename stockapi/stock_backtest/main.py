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
import multiprocessing as mp
from multiprocessing import Queue, Process, JoinableQueue
import time

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
    
    def _setup_worker_logging(self, process_id: int):
        """
        为工作进程配置日志系统
        
        Args:
            process_id: 进程ID
        """
        # 清除当前进程的日志配置
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 使用主进程的日志文件
        if hasattr(self, 'log_file') and self.log_file:
            # 创建文件处理器和控制台处理器
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            console_handler = logging.StreamHandler(sys.stdout)
            
            # 设置格式
            formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - [Process-{process_id}] %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 配置根日志器
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
    
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
                    self.result_analyzer.write_backtest_result_to_file(
                        signals, self.get_strategy_description(), current_dir
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
            self.logger.info(f"开始批量测试 {len(stock_codes)} 个股票，使用 {num_processes} 个进程")
            
            if num_processes == 1:
                # 单进程处理
                all_signals = []
                for stock_code in stock_codes:
                    signals = self.stock_selector.test_single_stock(stock_code, verbose=False)
                    all_signals.extend(signals)
            else:
                # 多进程处理
                all_signals = self._process_stocks_multiprocessing(stock_codes, num_processes)
            
            # 转换为DataFrame
            if all_signals:
                result_df = pd.DataFrame(all_signals)
                result_df = result_df.sort_values(['date', 'stock_code']).reset_index(drop=True)
            else:
                result_df = pd.DataFrame()
            
            self.logger.info(f"批量测试完成，共找到 {len(all_signals)} 个信号")
            
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
            
            # 应用过滤条件：剔除次日开盘涨幅>4.5%且开盘价等于收盘价的信号
            original_count = len(signals)
            signals, filtered_count = self.result_analyzer.filter_high_open_flat_signals(signals)
            
            if filtered_count > 0:
                self.logger.info(f"过滤掉 {filtered_count} 个次日高开平盘信号，剩余 {len(signals)} 个信号")
            
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
            self.result_analyzer.write_backtest_result_to_file(
                signals, self.get_strategy_description(), current_dir
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
            
            # 执行全量测试 - 使用本地的批量处理逻辑
            self.logger.info(f"开始全量测试 {len(all_stock_codes)} 个股票，使用 {num_processes} 个进程")
            
            if num_processes == 1:
                # 单进程处理
                all_signals = []
                for stock_code in all_stock_codes:
                    signals = self.stock_selector.test_single_stock(stock_code, verbose=False)
                    all_signals.extend(signals)
            else:
                # 多进程处理
                all_signals = self._process_stocks_multiprocessing(all_stock_codes, num_processes)
            
            # 转换为DataFrame
            if all_signals:
                result_df = pd.DataFrame(all_signals)
                result_df = result_df.sort_values(['date', 'stock_code']).reset_index(drop=True)
            else:
                result_df = pd.DataFrame()
            
            self.logger.info(f"全量测试完成，共找到 {len(all_signals)} 个信号")
            
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
            
            # 应用过滤条件：剔除次日开盘涨幅>4.5%且开盘价等于收盘价的信号
            original_count = len(signals)
            signals, filtered_count = self.result_analyzer.filter_high_open_flat_signals(signals)
            
            if filtered_count > 0:
                self.logger.info(f"过滤掉 {filtered_count} 个次日高开平盘信号，剩余 {len(signals)} 个信号")
            
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
            self.result_analyzer.write_backtest_result_to_file(
                signals, self.get_strategy_description(), current_dir
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
    
    def _process_stocks_multiprocessing(self, stock_codes: List[str], num_processes: int) -> List[Dict[str, Any]]:
        """
        多进程处理股票
        
        Args:
            stock_codes: 股票代码列表
            num_processes: 进程数量
            
        Returns:
            List[Dict[str, Any]]: 所有信号列表
        """
        # 创建任务队列
        task_queue = JoinableQueue()
        result_queue = Queue()
        
        # 添加任务到队列
        for stock_code in stock_codes:
            task_queue.put(stock_code)
        
        # 创建工作进程
        processes = []
        for i in range(num_processes):
            p = Process(
                target=self._worker_process,
                args=(task_queue, result_queue, i + 1)
            )
            p.start()
            processes.append(p)
        
        # 等待所有任务完成
        self.logger.info("等待所有任务完成...")
        task_queue.join()
        self.logger.info("所有任务已完成，开始收集结果并终止进程")
        
        # 等待进程完成结果提交
        self.logger.info("等待进程完成结果提交...")
        time.sleep(3)
        
        # 收集所有可用的结果
        self.logger.info("开始收集进程结果...")
        all_signals = []
        result_count = 0
        
        while not result_queue.empty():
            try:
                signals = result_queue.get_nowait()
                all_signals.extend(signals)
                result_count += 1
                self.logger.info(f"收集到结果批次 {result_count}，当前总信号数: {len(all_signals)}")
            except:
                break
        
        # 再等待一下，确保所有进程都有机会提交结果
        if result_count == 0:
            self.logger.info("第一次未收集到结果，再等待2秒...")
            time.sleep(2)
            while not result_queue.empty():
                try:
                    signals = result_queue.get_nowait()
                    all_signals.extend(signals)
                    result_count += 1
                    self.logger.info(f"延迟收集到结果批次 {result_count}，当前总信号数: {len(all_signals)}")
                except:
                    break
        
        # 现在强制终止所有进程
        self.logger.info("开始强制终止所有进程...")
        for i, p in enumerate(processes):
            if p.is_alive():
                self.logger.info(f"强制终止进程 {i+1} (PID: {p.pid})")
                p.terminate()
                p.join(timeout=3)  # 给一点时间让进程清理
                if p.is_alive():
                    self.logger.warning(f"进程 {i+1} (PID: {p.pid}) 仍未结束，使用kill")
                    p.kill()
            else:
                self.logger.info(f"进程 {i+1} (PID: {p.pid}) 已自然结束")
        
        self.logger.info("所有进程已完成")
        self.logger.info(f"结果收集完成！共收集了 {result_count} 个进程的结果")
        self.logger.info(f"多进程处理完成！总共找到 {len(all_signals)} 个信号")
        
        return all_signals
    
    def _worker_process(self, task_queue: JoinableQueue, result_queue: Queue, process_id: int):
        """
        工作进程函数
        
        Args:
            task_queue: 任务队列
            result_queue: 结果队列
            process_id: 进程ID
        """
        # 在工作进程中重新配置日志系统
        self._setup_worker_logging(process_id)
        
        # 在工作进程中创建新的StockSelector实例
        try:
            stock_selector = StockSelector(self.data_folder, self.strategy_engine)
            
            while True:
                try:
                    # 从队列获取任务
                    stock_code = task_queue.get(timeout=1)
                    
                    try:
                        # 处理单个股票
                        signals = stock_selector.test_single_stock(stock_code, verbose=False)
                        
                        # 将结果放入结果队列
                        result_queue.put(signals)
                        
                    except Exception as e:
                        # 处理单个股票时出错，记录错误但继续处理其他股票
                        print(f"进程 {process_id} 处理股票 {stock_code} 时出错: {e}")
                        result_queue.put([])  # 放入空列表表示该股票处理失败
                    
                    finally:
                        # 标记任务完成
                        task_queue.task_done()
                        
                except:
                    # 队列为空或超时，退出循环
                    break
                    
        except Exception as e:
            print(f"工作进程 {process_id} 初始化失败: {e}")
        
        print(f"工作进程 {process_id} 结束")


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