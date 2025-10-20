#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票回测运行器
功能：对指定股票进行逐交易日回测分析
作者：AI Assistant
创建时间：2025年
"""

import os
import sys
import argparse
import subprocess
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# 导入当前目录下的data_loader
from data_loader import StockDataLoader


class StockBacktestRunner:
    """股票回测运行器类"""
    
    def __init__(self, stock_code, data_base_path=None, pearson_analyzer_path=None):
        """
        初始化回测运行器
        
        Args:
            stock_code (str): 股票代码，如 '000001'
            data_base_path (str): 数据基础路径
            pearson_analyzer_path (str): pearson_analyzer.py 脚本路径
        """
        self.stock_code = stock_code
        
        # 设置默认路径
        if data_base_path is None:
            self.data_base_path = project_root / "data" / "all_stocks_data"
        else:
            self.data_base_path = Path(data_base_path)
            
        if pearson_analyzer_path is None:
            self.pearson_analyzer_path = current_dir / "pearson_analyzer.py"
        else:
            self.pearson_analyzer_path = Path(pearson_analyzer_path)
            
        # 初始化数据加载器
        self.data_loader = StockDataLoader(str(self.data_base_path))
        
        # 验证文件存在
        if not self.pearson_analyzer_path.exists():
            raise FileNotFoundError(f"找不到 pearson_analyzer.py 文件: {self.pearson_analyzer_path}")
    
    def get_trading_dates(self, start_date=None, end_date=None, days_back=30):
        """
        获取股票的交易日期列表
        
        Args:
            start_date (str): 开始日期，格式 'YYYY-MM-DD'
            end_date (str): 结束日期，格式 'YYYY-MM-DD'
            days_back (int): 如果未指定日期，从最近日期往前推的天数
            
        Returns:
            list: 交易日期列表，按时间倒序排列（最新日期在前）
        """
        try:
            # 加载股票日线数据
            stock_data = self.data_loader.load_stock_data(
                stock_code=self.stock_code,
                time_frame='daily',
                start_date=start_date,
                end_date=end_date
            )
            
            if stock_data is None or stock_data.empty:
                print(f"警告：无法获取股票 {self.stock_code} 的数据")
                return []
            
            # 获取日期列表 - 使用索引
            if stock_data.index.name == 'datetime':
                dates = stock_data.index.tolist()
            elif 'date' in stock_data.columns:
                dates = stock_data['date'].tolist()
            elif 'datetime' in stock_data.columns:
                dates = stock_data['datetime'].tolist()
            else:
                print("错误：数据中没有找到日期字段")
                return []
            
            # 转换为日期格式并排序（最新日期在前）
            trading_dates = []
            for date in dates:
                if isinstance(date, (int, float)):
                    # 时间戳格式
                    date_obj = datetime.fromtimestamp(date / 1000)
                else:
                    # 字符串格式
                    date_obj = pd.to_datetime(date)
                
                trading_dates.append(date_obj.strftime('%Y-%m-%d'))
            
            # 按日期倒序排列（最新日期在前）
            trading_dates.sort(reverse=True)
            
            # 如果指定了天数限制
            if not start_date and not end_date and days_back:
                trading_dates = trading_dates[:days_back]
            
            print(f"获取到 {len(trading_dates)} 个交易日")
            if trading_dates:
                print(f"日期范围：{trading_dates[-1]} 到 {trading_dates[0]}")
            
            return trading_dates
            
        except Exception as e:
            print(f"获取交易日期时出错：{e}")
            return []
    
    def run_pearson_analysis(self, backtest_date, csv_filename=None, 
                           comparison_mode='top10', window_size=15, threshold=0.8,
                           debug=False):
        """
        运行单日的皮尔逊相关性分析
        
        Args:
            backtest_date (str): 回测日期，格式 'YYYY-MM-DD'
            csv_filename (str): 输出CSV文件名
            comparison_mode (str): 比较模式，默认 'industry'
            window_size (int): 窗口大小，默认 20
            threshold (float): 相关性阈值，默认 0.8
            debug (bool): 是否开启调试模式
            
        Returns:
            tuple: (success, output) 成功标志和输出信息
        """
        try:
            # 构建CSV文件名 - 只使用股票代码，不包含日期
            if csv_filename is None:
                csv_filename = f"{self.stock_code}.csv"
            
            # 构建命令行参数
            cmd = [
                'python',
                str(self.pearson_analyzer_path),
                self.stock_code,
                '--comparison_mode', comparison_mode,
                '--csv_filename', csv_filename,
                '--backtest_date', backtest_date,
                '--window_size', str(window_size),
                '--threshold', str(threshold)
            ]
            
            if debug:
                cmd.append('--debug')
            
            print(f"执行命令：{' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(current_dir),
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print(f"✓ {backtest_date} 分析完成")
                if debug:
                    print(f"输出：{result.stdout}")
                return True, result.stdout
            else:
                print(f"✗ {backtest_date} 分析失败")
                print(f"错误：{result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            print(f"✗ {backtest_date} 分析超时")
            return False, "分析超时"
        except Exception as e:
            print(f"✗ {backtest_date} 分析出错：{e}")
            return False, str(e)
    
    def run_backtest(self, start_date=None, end_date=None, days_back=30,
                    comparison_mode='top10', window_size=15, threshold=0.8,
                    debug=False, max_parallel=1):
        """
        运行完整的回测流程
        
        Args:
            start_date (str): 开始日期
            end_date (str): 结束日期
            days_back (int): 回测天数
            comparison_mode (str): 比较模式
            window_size (int): 窗口大小
            threshold (float): 相关性阈值
            debug (bool): 调试模式
            max_parallel (int): 最大并行数（暂未实现）
            
        Returns:
            dict: 回测结果统计
        """
        print(f"开始对股票 {self.stock_code} 进行回测分析")
        print(f"参数：comparison_mode={comparison_mode}, window_size={window_size}, threshold={threshold}")
        
        # 获取交易日期
        trading_dates = self.get_trading_dates(start_date, end_date, days_back)
        
        if not trading_dates:
            print("没有找到可用的交易日期")
            return {'success': 0, 'failed': 0, 'total': 0}
        
        # 统计结果
        results = {
            'success': 0,
            'failed': 0,
            'total': len(trading_dates),
            'failed_dates': []
        }
        
        # 逐日执行分析
        for i, date in enumerate(trading_dates, 1):
            print(f"\n[{i}/{len(trading_dates)}] 分析日期：{date}")
            
            success, output = self.run_pearson_analysis(
                backtest_date=date,
                comparison_mode=comparison_mode,
                window_size=window_size,
                threshold=threshold,
                debug=debug
            )
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_dates'].append(date)
        
        # 输出统计结果
        print(f"\n{'='*50}")
        print(f"回测完成！")
        print(f"总计：{results['total']} 个交易日")
        print(f"成功：{results['success']} 个")
        print(f"失败：{results['failed']} 个")
        
        if results['failed_dates']:
            print(f"失败日期：{', '.join(results['failed_dates'])}")
        
        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票回测分析工具')
    
    # 必需参数
    parser.add_argument('stock_code', help='股票代码，如 000001')
    
    # 可选参数
    parser.add_argument('--start_date', help='开始日期，格式 YYYY-MM-DD')
    parser.add_argument('--end_date', help='结束日期，格式 YYYY-MM-DD')
    parser.add_argument('--days_back', type=int, default=30, 
                       help='从最近日期往前推的天数（默认30天）')
    
    # 分析参数
    parser.add_argument('--comparison_mode', default='top10',
                       help='比较模式（默认 top10）')
    parser.add_argument('--window_size', type=int, default=20,
                       help='窗口大小（默认 20）')
    parser.add_argument('--threshold', type=float, default=0.8,
                       help='相关性阈值（默认 0.8）')
    
    # 其他选项
    parser.add_argument('--debug', action='store_true',
                       help='开启调试模式')
    parser.add_argument('--data_path', 
                       help='数据路径（可选）')
    parser.add_argument('--analyzer_path',
                       help='pearson_analyzer.py 路径（可选）')
    
    args = parser.parse_args()
    
    try:
        # 创建回测运行器
        runner = StockBacktestRunner(
            stock_code=args.stock_code,
            data_base_path=args.data_path,
            pearson_analyzer_path=args.analyzer_path
        )
        
        # 运行回测
        results = runner.run_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            days_back=args.days_back,
            comparison_mode=args.comparison_mode,
            window_size=args.window_size,
            threshold=args.threshold,
            debug=args.debug
        )
        
        # 根据结果设置退出码
        if results['failed'] == 0:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"程序执行出错：{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()