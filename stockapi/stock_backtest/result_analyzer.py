# coding:utf-8
"""
结果整理输出模块 - 处理和展示回测结果

包含结果分析、统计计算、可视化和报告生成功能
"""

import pandas as pd
import numpy as np
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json


class ResultAnalyzer:
    """回测结果分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析信号数据
        
        Args:
            signals: 信号列表
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 转换为DataFrame便于分析
        df = pd.DataFrame(signals)
        
        # 基本统计
        total_signals = len(df)
        unique_stocks = df['stock_code'].nunique() if 'stock_code' in df.columns else 0
        
        # 收益率分析
        returns_analysis = {}
        if 'next_day_return' in df.columns:
            valid_returns = df['next_day_return'].dropna()
            if len(valid_returns) > 0:
                returns_analysis = {
                    'total_valid_returns': len(valid_returns),
                    'mean_return': valid_returns.mean(),
                    'median_return': valid_returns.median(),
                    'std_return': valid_returns.std(),
                    'min_return': valid_returns.min(),
                    'max_return': valid_returns.max(),
                    'positive_return_ratio': (valid_returns > 0).mean(),
                    'negative_return_ratio': (valid_returns < 0).mean(),
                    'zero_return_ratio': (valid_returns == 0).mean()
                }
        
        # 时间分布分析
        time_analysis = {}
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            time_analysis = {
                'date_range': {
                    'start_date': df['date'].min().strftime('%Y-%m-%d'),
                    'end_date': df['date'].max().strftime('%Y-%m-%d')
                },
                'signals_by_month': {str(k): v for k, v in df.groupby(df['date'].dt.to_period('M')).size().to_dict().items()},
                'signals_by_weekday': df.groupby(df['date'].dt.day_name()).size().to_dict()
            }
        
        # 股票分布分析
        stock_analysis = {}
        if 'stock_code' in df.columns:
            stock_counts = df['stock_code'].value_counts()
            stock_analysis = {
                'top_10_stocks': stock_counts.head(10).to_dict(),
                'stocks_with_single_signal': (stock_counts == 1).sum(),
                'stocks_with_multiple_signals': (stock_counts > 1).sum()
            }
        
        return {
            'basic_stats': {
                'total_signals': total_signals,
                'unique_stocks': unique_stocks
            },
            'returns_analysis': returns_analysis,
            'time_analysis': time_analysis,
            'stock_analysis': stock_analysis
        }
    
    def calculate_portfolio_performance(self, signals: List[Dict[str, Any]], 
                                      initial_capital: float = 100000,
                                      position_size: float = 0.1) -> Dict[str, Any]:
        """
        计算投资组合表现
        
        Args:
            signals: 信号列表
            initial_capital: 初始资金
            position_size: 每次投资占总资金的比例
            
        Returns:
            Dict[str, Any]: 投资组合表现
        """
        if not signals:
            return {"error": "没有信号数据"}
        
        # 转换为DataFrame并按日期排序
        df = pd.DataFrame(signals)
        if 'next_day_return' not in df.columns:
            return {"error": "缺少收益率数据"}
        
        df = df.dropna(subset=['next_day_return'])
        if df.empty:
            return {"error": "没有有效的收益率数据"}
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 计算投资组合表现
        capital = initial_capital
        portfolio_values = [capital]
        returns = []
        
        for _, row in df.iterrows():
            investment_amount = capital * position_size
            return_rate = row['next_day_return'] / 100  # 转换为小数
            profit = investment_amount * return_rate
            capital += profit
            portfolio_values.append(capital)
            returns.append(return_rate)
        
        # 计算性能指标
        total_return = (capital - initial_capital) / initial_capital
        num_trades = len(returns)
        
        if num_trades > 0:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            win_rate = sum(1 for r in returns if r > 0) / num_trades
            
            # 计算最大回撤
            portfolio_series = pd.Series(portfolio_values)
            running_max = portfolio_series.expanding().max()
            drawdown = (portfolio_series - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # 计算夏普比率（假设无风险利率为0）
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
            
            return {
                'initial_capital': initial_capital,
                'final_capital': capital,
                'total_return': total_return,
                'total_return_pct': total_return * 100,
                'num_trades': num_trades,
                'avg_return_per_trade': avg_return,
                'avg_return_per_trade_pct': avg_return * 100,
                'win_rate': win_rate,
                'win_rate_pct': win_rate * 100,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown * 100,
                'sharpe_ratio': sharpe_ratio,
                'volatility': std_return,
                'portfolio_values': portfolio_values,
                'dates': ['Initial'] + df['date'].dt.strftime('%Y-%m-%d').tolist()
            }
        else:
            return {"error": "没有有效的交易数据"}
    
    def generate_performance_report(self, signals: List[Dict[str, Any]], 
                                  output_file: str = None) -> str:
        """
        生成性能报告
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
            
        Returns:
            str: 报告内容
        """
        # 分析信号
        analysis = self.analyze_signals(signals)
        
        # 计算投资组合表现
        portfolio_perf = self.calculate_portfolio_performance(signals)
        
        # 生成报告
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("回测结果分析报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 基本统计
        if 'basic_stats' in analysis:
            stats = analysis['basic_stats']
            report_lines.append("基本统计:")
            report_lines.append(f"  总信号数量: {stats.get('total_signals', 0)}")
            report_lines.append(f"  涉及股票数量: {stats.get('unique_stocks', 0)}")
            report_lines.append("")
        
        # 收益率分析
        if 'returns_analysis' in analysis and analysis['returns_analysis']:
            returns = analysis['returns_analysis']
            report_lines.append("收益率分析:")
            report_lines.append(f"  有效收益率数量: {returns.get('total_valid_returns', 0)}")
            report_lines.append(f"  平均收益率: {returns.get('mean_return', 0):.4f}%")
            report_lines.append(f"  中位数收益率: {returns.get('median_return', 0):.4f}%")
            report_lines.append(f"  收益率标准差: {returns.get('std_return', 0):.4f}%")
            report_lines.append(f"  最小收益率: {returns.get('min_return', 0):.4f}%")
            report_lines.append(f"  最大收益率: {returns.get('max_return', 0):.4f}%")
            report_lines.append(f"  正收益比例: {returns.get('positive_return_ratio', 0):.2%}")
            report_lines.append(f"  负收益比例: {returns.get('negative_return_ratio', 0):.2%}")
            report_lines.append("")
        
        # 投资组合表现
        if 'error' not in portfolio_perf:
            report_lines.append("投资组合表现:")
            report_lines.append(f"  初始资金: ¥{portfolio_perf.get('initial_capital', 0):,.2f}")
            report_lines.append(f"  最终资金: ¥{portfolio_perf.get('final_capital', 0):,.2f}")
            report_lines.append(f"  总收益率: {portfolio_perf.get('total_return_pct', 0):.2f}%")
            report_lines.append(f"  交易次数: {portfolio_perf.get('num_trades', 0)}")
            report_lines.append(f"  平均每笔收益: {portfolio_perf.get('avg_return_per_trade_pct', 0):.4f}%")
            report_lines.append(f"  胜率: {portfolio_perf.get('win_rate_pct', 0):.2f}%")
            report_lines.append(f"  最大回撤: {portfolio_perf.get('max_drawdown_pct', 0):.2f}%")
            report_lines.append(f"  夏普比率: {portfolio_perf.get('sharpe_ratio', 0):.4f}")
            report_lines.append(f"  波动率: {portfolio_perf.get('volatility', 0):.4f}")
            report_lines.append("")
        
        # 时间分布
        if 'time_analysis' in analysis and analysis['time_analysis']:
            time_info = analysis['time_analysis']
            if 'date_range' in time_info:
                date_range = time_info['date_range']
                report_lines.append("时间分布:")
                report_lines.append(f"  时间范围: {date_range.get('start_date')} 至 {date_range.get('end_date')}")
                report_lines.append("")
        
        # 股票分布
        if 'stock_analysis' in analysis and analysis['stock_analysis']:
            stock_info = analysis['stock_analysis']
            if 'top_10_stocks' in stock_info:
                report_lines.append("热门股票 (前10):")
                for stock, count in stock_info['top_10_stocks'].items():
                    report_lines.append(f"  {stock}: {count} 次信号")
                report_lines.append("")
        
        report_lines.append("=" * 60)
        
        report_content = "\n".join(report_lines)
        
        # 保存到文件
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                self.logger.info(f"报告已保存到: {output_file}")
            except Exception as e:
                self.logger.error(f"保存报告失败: {e}")
        
        return report_content


class ResultExporter:
    """结果导出器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def export_to_csv(self, signals: List[Dict[str, Any]], output_file: str, 
                     include_analysis: bool = True):
        """
        导出结果到CSV文件
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
            include_analysis: 是否包含分析结果
        """
        try:
            if not signals:
                self.logger.warning("没有信号数据可导出")
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(signals)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 导出主要数据
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"信号数据已导出到: {output_file}")
            
            # 如果需要，导出分析结果
            if include_analysis:
                analyzer = ResultAnalyzer()
                analysis = analyzer.analyze_signals(signals)
                
                # 保存分析结果到JSON文件
                analysis_file = output_file.replace('.csv', '_analysis.json')
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
                self.logger.info(f"分析结果已导出到: {analysis_file}")
                
                # 生成文本报告
                report_file = output_file.replace('.csv', '_report.txt')
                report_content = analyzer.generate_performance_report(signals, report_file)
                
        except Exception as e:
            self.logger.error(f"导出CSV文件失败: {e}")
    
    def export_to_excel(self, signals: List[Dict[str, Any]], output_file: str):
        """
        导出结果到Excel文件
        
        Args:
            signals: 信号列表
            output_file: 输出文件路径
        """
        try:
            if not signals:
                self.logger.warning("没有信号数据可导出")
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(signals)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 创建Excel写入器
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 写入主要数据
                df.to_excel(writer, sheet_name='信号数据', index=False)
                
                # 分析结果
                analyzer = ResultAnalyzer()
                analysis = analyzer.analyze_signals(signals)
                
                # 基本统计
                if 'basic_stats' in analysis:
                    stats_df = pd.DataFrame([analysis['basic_stats']])
                    stats_df.to_excel(writer, sheet_name='基本统计', index=False)
                
                # 收益率分析
                if 'returns_analysis' in analysis and analysis['returns_analysis']:
                    returns_df = pd.DataFrame([analysis['returns_analysis']])
                    returns_df.to_excel(writer, sheet_name='收益率分析', index=False)
                
                # 投资组合表现
                portfolio_perf = analyzer.calculate_portfolio_performance(signals)
                if 'error' not in portfolio_perf:
                    portfolio_df = pd.DataFrame([{k: v for k, v in portfolio_perf.items() 
                                                if k not in ['portfolio_values', 'dates']}])
                    portfolio_df.to_excel(writer, sheet_name='投资组合表现', index=False)
            
            self.logger.info(f"Excel文件已导出到: {output_file}")
            
        except Exception as e:
            self.logger.error(f"导出Excel文件失败: {e}")
    
    def export_summary_statistics(self, signals: List[Dict[str, Any]], output_dir: str):
        """
        导出汇总统计信息
        
        Args:
            signals: 信号列表
            output_dir: 输出目录
        """
        try:
            if not signals:
                self.logger.warning("没有信号数据可导出")
                return
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 分析结果
            analyzer = ResultAnalyzer()
            analysis = analyzer.analyze_signals(signals)
            portfolio_perf = analyzer.calculate_portfolio_performance(signals)
            
            # 导出各种统计信息
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 1. 完整分析结果 (JSON)
            analysis_file = os.path.join(output_dir, f'analysis_{timestamp}.json')
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'signal_analysis': analysis,
                    'portfolio_performance': portfolio_perf
                }, f, ensure_ascii=False, indent=2, default=str)
            
            # 2. 文本报告
            report_file = os.path.join(output_dir, f'report_{timestamp}.txt')
            analyzer.generate_performance_report(signals, report_file)
            
            # 3. 信号数据CSV
            csv_file = os.path.join(output_dir, f'signals_{timestamp}.csv')
            df = pd.DataFrame(signals)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"汇总统计信息已导出到目录: {output_dir}")
            
        except Exception as e:
            self.logger.error(f"导出汇总统计信息失败: {e}")


class ResultFormatter:
    """结果格式化器"""
    
    @staticmethod
    def format_signal_for_display(signal: Dict[str, Any]) -> str:
        """
        格式化单个信号用于显示
        
        Args:
            signal: 信号字典
            
        Returns:
            str: 格式化后的字符串
        """
        stock_code = signal.get('stock_code', 'N/A')
        date = signal.get('date', 'N/A')
        close_price = signal.get('close', 0)
        next_return = signal.get('next_day_return', None)
        
        if next_return is not None:
            return f"{stock_code} | {date} | 收盘价: {close_price:.4f} | 次日收益: {next_return:.2f}%"
        else:
            return f"{stock_code} | {date} | 收盘价: {close_price:.4f} | 次日收益: N/A"
    
    @staticmethod
    def format_signals_table(signals: List[Dict[str, Any]], max_rows: int = 20) -> str:
        """
        格式化信号列表为表格
        
        Args:
            signals: 信号列表
            max_rows: 最大显示行数
            
        Returns:
            str: 格式化后的表格字符串
        """
        if not signals:
            return "没有信号数据"
        
        # 转换为DataFrame
        df = pd.DataFrame(signals)
        
        # 选择要显示的列
        display_columns = ['stock_code', 'date', 'close']
        if 'next_day_return' in df.columns:
            display_columns.append('next_day_return')
        
        # 过滤列
        display_df = df[display_columns].copy()
        
        # 限制行数
        if len(display_df) > max_rows:
            display_df = display_df.head(max_rows)
        
        # 格式化数值
        if 'close' in display_df.columns:
            display_df['close'] = display_df['close'].apply(lambda x: f"{x:.4f}")
        if 'next_day_return' in display_df.columns:
            display_df['next_day_return'] = display_df['next_day_return'].apply(
                lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
            )
        
        # 重命名列
        column_names = {
            'stock_code': '股票代码',
            'date': '日期',
            'close': '收盘价',
            'next_day_return': '次日收益'
        }
        display_df = display_df.rename(columns=column_names)
        
        return display_df.to_string(index=False)
    
    @staticmethod
    def format_performance_summary(portfolio_perf: Dict[str, Any]) -> str:
        """
        格式化投资组合表现摘要
        
        Args:
            portfolio_perf: 投资组合表现字典
            
        Returns:
            str: 格式化后的摘要字符串
        """
        if 'error' in portfolio_perf:
            return f"无法计算投资组合表现: {portfolio_perf['error']}"
        
        lines = []
        lines.append("投资组合表现摘要:")
        lines.append(f"  总收益率: {portfolio_perf.get('total_return_pct', 0):.2f}%")
        lines.append(f"  交易次数: {portfolio_perf.get('num_trades', 0)}")
        lines.append(f"  胜率: {portfolio_perf.get('win_rate_pct', 0):.2f}%")
        lines.append(f"  最大回撤: {portfolio_perf.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"  夏普比率: {portfolio_perf.get('sharpe_ratio', 0):.4f}")
        
        return "\n".join(lines)