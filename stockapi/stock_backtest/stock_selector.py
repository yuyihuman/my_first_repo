# coding:utf-8
"""
选股模块 - 基于策略筛选股票

支持单股票测试、批量测试和全量测试
"""

import pandas as pd
import os
import logging
import multiprocessing as mp
from multiprocessing import Queue, Process, JoinableQueue
from functools import partial
import gc
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from data_loader import StockDataLoader, DataPreprocessor
from strategy_engine import StrategyEngine


class StockSelector:
    """股票选择器"""
    
    def __init__(self, data_folder: str, strategy_engine: StrategyEngine = None):
        """
        初始化股票选择器
        
        Args:
            data_folder: 股票数据文件夹路径
            strategy_engine: 策略引擎实例
        """
        self.data_folder = data_folder
        self.data_loader = StockDataLoader(data_folder)
        self.data_preprocessor = DataPreprocessor()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.logger = logging.getLogger(__name__)
    
    def test_single_stock(self, stock_code: str, verbose: bool = True) -> List[Dict[str, Any]]:
        """
        测试单个股票
        
        Args:
            stock_code: 股票代码
            verbose: 是否显示详细信息
            
        Returns:
            List[Dict[str, Any]]: 符合条件的信号列表
        """
        self.logger.info(f"开始测试股票: {stock_code}")
        
        # 加载股票数据
        df = self.data_loader.load_stock_data(stock_code)
        if df is None:
            self.logger.error(f"无法加载股票 {stock_code} 的数据")
            return []
        
        # 验证数据质量
        if not self.data_loader.validate_data_quality(df, stock_code):
            self.logger.error(f"股票 {stock_code} 数据质量不合格")
            return []
        
        # 清理数据
        df = self.data_preprocessor.clean_data(df, stock_code)
        
        # 添加技术指标
        df = self.data_preprocessor.add_technical_indicators(df)
        
        # 扫描信号
        signals = self.strategy_engine.scan_stock_for_signals(df, stock_code)
        
        if verbose:
            self.logger.info(f"股票 {stock_code} 找到 {len(signals)} 个符合条件的信号")
            for signal in signals:
                self.logger.info(f"  日期: {signal['date']}, 收盘价: {signal['close']:.4f}, "
                               f"次日收益: {signal['next_day_return']:.2f}%" if signal['next_day_return'] else "次日收益: N/A")
        
        return signals
    
    def test_single_stock_verbose(self, stock_code: str, target_date: str = None) -> Dict[str, Any]:
        """
        详细测试单个股票的特定日期
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，如果为None则测试最新日期
            
        Returns:
            Dict[str, Any]: 详细检查结果
        """
        self.logger.info(f"开始详细测试股票: {stock_code}")
        
        # 加载股票数据
        df = self.data_loader.load_stock_data(stock_code)
        if df is None:
            return {"error": f"无法加载股票 {stock_code} 的数据"}
        
        # 验证数据质量
        if not self.data_loader.validate_data_quality(df, stock_code):
            return {"error": f"股票 {stock_code} 数据质量不合格"}
        
        # 清理数据
        df = self.data_preprocessor.clean_data(df, stock_code)
        
        # 确定测试日期索引
        if target_date:
            target_datetime = pd.to_datetime(target_date)
            matching_rows = df[df['datetime'] == target_datetime]
            if matching_rows.empty:
                return {"error": f"未找到日期 {target_date} 的数据"}
            current_idx = matching_rows.index[0]
        else:
            current_idx = len(df) - 1  # 最新日期
        
        # 详细检查策略条件
        result, details = self.strategy_engine.check_strategy_conditions_verbose(
            df, current_idx, stock_code, verbose=True
        )
        
        return details
    
    def test_batch_stocks(self, stock_codes: List[str], num_processes: int = 4) -> pd.DataFrame:
        """
        批量测试多个股票
        
        Args:
            stock_codes: 股票代码列表
            num_processes: 进程数量
            
        Returns:
            pd.DataFrame: 回测结果
        """
        self.logger.info(f"开始批量测试 {len(stock_codes)} 个股票，使用 {num_processes} 个进程")
        
        if num_processes == 1:
            # 单进程处理
            all_signals = []
            for stock_code in stock_codes:
                signals = self.test_single_stock(stock_code, verbose=False)
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
        return result_df
    
    def test_all_stocks(self, num_processes: int = 20, limit: int = None) -> pd.DataFrame:
        """
        测试所有可用股票
        
        Args:
            num_processes: 进程数量
            limit: 限制测试的股票数量
            
        Returns:
            pd.DataFrame: 回测结果
        """
        # 获取所有可用股票
        all_stock_codes = self.data_loader.get_available_stocks()
        
        if limit:
            all_stock_codes = all_stock_codes[:limit]
        
        self.logger.info(f"开始全量测试，共 {len(all_stock_codes)} 个股票")
        
        return self.test_batch_stocks(all_stock_codes, num_processes)
    
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
        import time
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
        # 为每个进程创建独立的日志
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(script_dir, "process_logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        log_file = os.path.join(logs_dir, f"process_{process_id}.log")
        
        # 重新配置根日志器，确保所有模块的日志都只输出到文件
        root_logger = logging.getLogger()
        
        # 清除根日志器的所有处理器（包括控制台处理器）
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 只添加文件处理器到根日志器
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        
        # 获取进程专用的日志器
        process_logger = logging.getLogger(f"process_{process_id}")
        
        # 记录进程开始工作
        root_logger.info(f"进程 {process_id} 开始工作，日志文件: {log_file}")
        
        # 创建独立的数据加载器和策略引擎
        data_loader = StockDataLoader(self.data_folder)
        data_preprocessor = DataPreprocessor()
        strategy_engine = StrategyEngine()
        
        processed_count = 0
        
        while True:
            try:
                stock_code = task_queue.get(timeout=5)  # 增加超时时间
                if stock_code is None:
                    break
                
                try:
                    process_logger.info(f"进程 {process_id} 开始处理股票: {stock_code}")
                    
                    # 加载股票数据
                    df = data_loader.load_stock_data(stock_code)
                    if df is None:
                        process_logger.warning(f"无法加载股票 {stock_code} 的数据")
                        task_queue.task_done()
                        continue
                    
                    # 验证数据质量
                    if not data_loader.validate_data_quality(df, stock_code):
                        process_logger.warning(f"股票 {stock_code} 数据质量不合格")
                        task_queue.task_done()
                        continue
                    
                    # 清理数据
                    df = data_preprocessor.clean_data(df, stock_code)
                    
                    # 添加技术指标
                    df = data_preprocessor.add_technical_indicators(df)
                    
                    # 扫描信号
                    signals = strategy_engine.scan_stock_for_signals(df, stock_code)
                    
                    # 将结果放入结果队列
                    result_queue.put(signals)
                    
                    processed_count += 1
                    process_logger.info(f"进程 {process_id} 完成处理股票: {stock_code}, "
                                      f"找到 {len(signals)} 个信号, 已处理 {processed_count} 个股票")
                    
                    # 清理内存
                    del df
                    gc.collect()
                    
                except Exception as e:
                    process_logger.error(f"进程 {process_id} 处理股票 {stock_code} 时出错: {e}")
                
                finally:
                    task_queue.task_done()
                    
            except Exception as e:
                # 超时或其他异常时退出循环
                process_logger.info(f"进程 {process_id} 退出循环: {e}")
                break
        
        process_logger.info(f"进程 {process_id} 完成，共处理 {processed_count} 个股票")
    
    def filter_signals_by_date(self, signals: List[Dict[str, Any]], 
                             start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        按日期范围过滤信号
        
        Args:
            signals: 信号列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            List[Dict[str, Any]]: 过滤后的信号列表
        """
        filtered_signals = signals.copy()
        
        if start_date:
            start_date = pd.to_datetime(start_date)
            filtered_signals = [s for s in filtered_signals if pd.to_datetime(s['date']) >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            filtered_signals = [s for s in filtered_signals if pd.to_datetime(s['date']) <= end_date]
        
        return filtered_signals
    
    def get_top_signals(self, signals: List[Dict[str, Any]], 
                       top_n: int = 10, sort_by: str = 'next_day_return') -> List[Dict[str, Any]]:
        """
        获取排名前N的信号
        
        Args:
            signals: 信号列表
            top_n: 返回前N个
            sort_by: 排序字段
            
        Returns:
            List[Dict[str, Any]]: 排名前N的信号
        """
        # 过滤掉没有次日收益数据的信号
        valid_signals = [s for s in signals if s.get(sort_by) is not None]
        
        # 按指定字段排序
        sorted_signals = sorted(valid_signals, key=lambda x: x[sort_by], reverse=True)
        
        return sorted_signals[:top_n]


class BatchStockProcessor:
    """批量股票处理器（用于兼容原有接口）"""
    
    def __init__(self, data_folder: str):
        self.data_folder = data_folder
        self.stock_selector = StockSelector(data_folder)
        self.logger = logging.getLogger(__name__)
    
    def process_single_stock(self, stock_code: str, process_index: int = 1, 
                           log_to_file=None, verbose: bool = False) -> List[Dict[str, Any]]:
        """
        处理单个股票（兼容原有接口）
        
        Args:
            stock_code: 股票代码
            process_index: 进程序号
            log_to_file: 日志记录函数
            verbose: 是否详细输出
            
        Returns:
            List[Dict[str, Any]]: 符合条件的信号列表
        """
        return self.stock_selector.test_single_stock(stock_code, verbose)
    
    def run_stock_selection_strategy_dynamic(self, data_folder: str, output_file: str, 
                                           num_processes: int = 20, limit: int = None):
        """
        运行股票选择策略（兼容原有接口）
        
        Args:
            data_folder: 数据文件夹
            output_file: 输出文件路径
            num_processes: 进程数量
            limit: 限制处理的股票数量
        """
        # 测试所有股票
        result_df = self.stock_selector.test_all_stocks(num_processes, limit)
        
        # 保存结果
        if not result_df.empty:
            result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"结果已保存到: {output_file}")
        else:
            self.logger.warning("没有找到符合条件的股票")