#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成模块

生成回测报告，包括收益率分析、交易统计等
"""

import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import setup_logger

class ReportGenerator:
    """
    报告生成器类
    
    提供各种报告生成功能
    """
    
    def __init__(self):
        """
        初始化报告生成器
        """
        self.logger = setup_logger('report_generator', 'report_generator.log')
        self.logger.info("报告生成模块初始化")
        
        # 注册的报告类型
        self.report_types = {
            'simple': self._generate_simple_report,
            'detailed': self._generate_detailed_report,
            'summary': self._generate_summary_report
        }
        
        self.logger.debug(f"已注册报告类型: {list(self.report_types.keys())}")
        self.logger.debug("报告生成器初始化完成")
    
    def generate_report(self, data: Dict[str, Any], report_type: str = 'simple', 
                       output_format: str = 'dict') -> Dict[str, Any]:
        """
        生成报告
        
        Args:
            data (Dict[str, Any]): 回测数据
            report_type (str): 报告类型，默认为'simple'
            output_format (str): 输出格式，支持'dict', 'json', 'html'
        
        Returns:
            Dict[str, Any]: 生成的报告
        """
        self.logger.info(f"开始生成报告 - 类型: {report_type}, 格式: {output_format}")
        self.logger.debug(f"输入数据键: {list(data.keys()) if isinstance(data, dict) else 'non-dict'}")
        
        try:
            # 验证报告类型
            if report_type not in self.report_types:
                error_msg = f"不支持的报告类型: {report_type}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 生成报告内容
            report_func = self.report_types[report_type]
            report_content = report_func(data)
            
            # 格式化输出
            formatted_report = self._format_output(report_content, output_format)
            
            result = {
                'success': True,
                'report_type': report_type,
                'output_format': output_format,
                'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'content': formatted_report
            }
            
            self.logger.info(f"报告生成完成 - 类型: {report_type}")
            self.logger.debug(f"报告内容长度: {len(str(formatted_report))}")
            
            return result
            
        except Exception as e:
            error_msg = f"生成报告时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def _generate_simple_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成简单报告
        
        Args:
            data (Dict[str, Any]): 回测数据
        
        Returns:
            Dict[str, Any]: 简单报告内容
        """
        self.logger.debug("生成简单报告")
        
        report = {
            'title': '股票回测简单报告',
            'summary': {
                'total_trades': 0,
                'successful_trades': 0,
                'total_return': 0.0,
                'average_return': 0.0
            },
            'details': []
        }
        
        # 处理单笔交易数据
        if 'return_rate' in data:
            report['summary']['total_trades'] = 1
            report['summary']['successful_trades'] = 1 if data.get('success', False) else 0
            report['summary']['total_return'] = data.get('return_rate', 0.0)
            report['summary']['average_return'] = data.get('return_rate', 0.0)
            
            report['details'].append({
                'stock_code': data.get('stock_code', 'N/A'),
                'buy_date': data.get('buy_date', 'N/A'),
                'sell_date': data.get('sell_date', 'N/A'),
                'return_rate': data.get('return_rate', 0.0),
                'return_percentage': data.get('return_percentage', 0.0)
            })
        
        # 处理批量交易数据
        elif 'summary' in data and 'results' in data:
            summary = data['summary']
            report['summary'].update({
                'total_trades': summary.get('total_trades', 0),
                'successful_trades': summary.get('successful_trades', 0),
                'total_return': summary.get('total_return', 0.0),
                'average_return': summary.get('average_return', 0.0)
            })
            
            for result in data['results']:
                if result.get('success', False):
                    report['details'].append({
                        'stock_code': result.get('stock_code', 'N/A'),
                        'buy_date': result.get('buy_date', 'N/A'),
                        'sell_date': result.get('sell_date', 'N/A'),
                        'return_rate': result.get('return_rate', 0.0),
                        'return_percentage': result.get('return_percentage', 0.0)
                    })
        
        self.logger.debug(f"简单报告生成完成，包含 {len(report['details'])} 条交易记录")
        return report
    
    def _generate_detailed_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成详细报告
        
        Args:
            data (Dict[str, Any]): 回测数据
        
        Returns:
            Dict[str, Any]: 详细报告内容
        """
        self.logger.debug("生成详细报告")
        
        # 先生成简单报告作为基础
        report = self._generate_simple_report(data)
        report['title'] = '股票回测详细报告'
        
        # 添加详细统计信息
        report['statistics'] = self._calculate_statistics(data)
        
        # 添加风险指标（预留）
        report['risk_metrics'] = {
            'max_drawdown': 'N/A',
            'volatility': 'N/A',
            'sharpe_ratio': 'N/A'
        }
        
        # 添加交易分析
        report['trade_analysis'] = self._analyze_trades(data)
        
        self.logger.debug("详细报告生成完成")
        return report
    
    def _generate_summary_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成摘要报告
        
        Args:
            data (Dict[str, Any]): 回测数据
        
        Returns:
            Dict[str, Any]: 摘要报告内容
        """
        self.logger.debug("生成摘要报告")
        
        report = {
            'title': '股票回测摘要报告',
            'key_metrics': {},
            'performance_summary': ''
        }
        
        # 提取关键指标
        if 'summary' in data:
            summary = data['summary']
            report['key_metrics'] = {
                '总交易次数': summary.get('total_trades', 0),
                '成功交易次数': summary.get('successful_trades', 0),
                '成功率': f"{(summary.get('successful_trades', 0) / max(summary.get('total_trades', 1), 1) * 100):.2f}%",
                '总收益率': f"{summary.get('total_return', 0.0) * 100:.2f}%",
                '平均收益率': f"{summary.get('average_return', 0.0) * 100:.2f}%"
            }
        elif 'return_rate' in data:
            report['key_metrics'] = {
                '总交易次数': 1,
                '成功交易次数': 1 if data.get('success', False) else 0,
                '成功率': '100.00%' if data.get('success', False) else '0.00%',
                '收益率': f"{data.get('return_percentage', 0.0):.2f}%"
            }
        
        # 生成性能摘要
        report['performance_summary'] = self._generate_performance_summary(report['key_metrics'])
        
        self.logger.debug("摘要报告生成完成")
        return report
    
    def _calculate_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算统计信息
        
        Args:
            data (Dict[str, Any]): 回测数据
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        self.logger.debug("计算统计信息")
        
        stats = {
            'return_distribution': {},
            'holding_period_analysis': {},
            'stock_performance': {}
        }
        
        returns = []
        holding_days = []
        stock_returns = {}
        
        # 收集数据
        if 'results' in data:
            for result in data['results']:
                if result.get('success', False):
                    returns.append(result.get('return_rate', 0.0))
                    holding_days.append(result.get('hold_days', 0))
                    
                    stock_code = result.get('stock_code', 'Unknown')
                    if stock_code not in stock_returns:
                        stock_returns[stock_code] = []
                    stock_returns[stock_code].append(result.get('return_rate', 0.0))
        elif 'return_rate' in data:
            returns.append(data.get('return_rate', 0.0))
            holding_days.append(data.get('hold_days', 0))
            stock_code = data.get('stock_code', 'Unknown')
            stock_returns[stock_code] = [data.get('return_rate', 0.0)]
        
        # 收益率分布
        if returns:
            stats['return_distribution'] = {
                'min_return': min(returns),
                'max_return': max(returns),
                'median_return': sorted(returns)[len(returns)//2] if returns else 0,
                'positive_trades': len([r for r in returns if r > 0]),
                'negative_trades': len([r for r in returns if r < 0])
            }
        
        # 持有期分析
        if holding_days:
            stats['holding_period_analysis'] = {
                'min_days': min(holding_days),
                'max_days': max(holding_days),
                'avg_days': sum(holding_days) / len(holding_days)
            }
        
        # 个股表现
        for stock, stock_rets in stock_returns.items():
            stats['stock_performance'][stock] = {
                'trades_count': len(stock_rets),
                'total_return': sum(stock_rets),
                'avg_return': sum(stock_rets) / len(stock_rets)
            }
        
        self.logger.debug(f"统计信息计算完成，包含 {len(returns)} 笔交易")
        return stats
    
    def _analyze_trades(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析交易
        
        Args:
            data (Dict[str, Any]): 回测数据
        
        Returns:
            Dict[str, Any]: 交易分析结果
        """
        self.logger.debug("分析交易")
        
        analysis = {
            'best_trade': None,
            'worst_trade': None,
            'longest_hold': None,
            'shortest_hold': None
        }
        
        trades = []
        
        # 收集交易数据
        if 'results' in data:
            trades = [result for result in data['results'] if result.get('success', False)]
        elif 'return_rate' in data and data.get('success', False):
            trades = [data]
        
        if not trades:
            self.logger.debug("无有效交易数据")
            return analysis
        
        # 找出最佳和最差交易
        best_trade = max(trades, key=lambda x: x.get('return_rate', 0))
        worst_trade = min(trades, key=lambda x: x.get('return_rate', 0))
        
        analysis['best_trade'] = {
            'stock_code': best_trade.get('stock_code', 'N/A'),
            'return_rate': best_trade.get('return_rate', 0.0),
            'return_percentage': best_trade.get('return_percentage', 0.0),
            'buy_date': best_trade.get('buy_date', 'N/A'),
            'sell_date': best_trade.get('sell_date', 'N/A')
        }
        
        analysis['worst_trade'] = {
            'stock_code': worst_trade.get('stock_code', 'N/A'),
            'return_rate': worst_trade.get('return_rate', 0.0),
            'return_percentage': worst_trade.get('return_percentage', 0.0),
            'buy_date': worst_trade.get('buy_date', 'N/A'),
            'sell_date': worst_trade.get('sell_date', 'N/A')
        }
        
        # 找出持有期最长和最短的交易
        if all('hold_days' in trade for trade in trades):
            longest_hold = max(trades, key=lambda x: x.get('hold_days', 0))
            shortest_hold = min(trades, key=lambda x: x.get('hold_days', 0))
            
            analysis['longest_hold'] = {
                'stock_code': longest_hold.get('stock_code', 'N/A'),
                'hold_days': longest_hold.get('hold_days', 0),
                'return_percentage': longest_hold.get('return_percentage', 0.0)
            }
            
            analysis['shortest_hold'] = {
                'stock_code': shortest_hold.get('stock_code', 'N/A'),
                'hold_days': shortest_hold.get('hold_days', 0),
                'return_percentage': shortest_hold.get('return_percentage', 0.0)
            }
        
        self.logger.debug("交易分析完成")
        return analysis
    
    def _generate_performance_summary(self, key_metrics: Dict[str, Any]) -> str:
        """
        生成性能摘要文本
        
        Args:
            key_metrics (Dict[str, Any]): 关键指标
        
        Returns:
            str: 性能摘要文本
        """
        self.logger.debug("生成性能摘要")
        
        if not key_metrics:
            return "无可用数据生成性能摘要。"
        
        summary_parts = []
        
        # 交易概况
        total_trades = key_metrics.get('总交易次数', 0)
        success_rate = key_metrics.get('成功率', '0.00%')
        summary_parts.append(f"本次回测共执行 {total_trades} 笔交易，成功率为 {success_rate}。")
        
        # 收益情况
        if '平均收益率' in key_metrics:
            avg_return = key_metrics['平均收益率']
            total_return = key_metrics.get('总收益率', '0.00%')
            summary_parts.append(f"总收益率为 {total_return}，平均单笔收益率为 {avg_return}。")
        elif '收益率' in key_metrics:
            return_rate = key_metrics['收益率']
            summary_parts.append(f"本笔交易收益率为 {return_rate}。")
        
        # 简单评价
        if '平均收益率' in key_metrics:
            avg_return_num = float(key_metrics['平均收益率'].replace('%', ''))
            if avg_return_num > 5:
                summary_parts.append("整体表现优秀。")
            elif avg_return_num > 0:
                summary_parts.append("整体表现良好。")
            else:
                summary_parts.append("整体表现需要改进。")
        
        summary = " ".join(summary_parts)
        self.logger.debug(f"性能摘要生成完成，长度: {len(summary)}")
        
        return summary
    
    def _format_output(self, content: Dict[str, Any], output_format: str) -> Any:
        """
        格式化输出
        
        Args:
            content (Dict[str, Any]): 报告内容
            output_format (str): 输出格式
        
        Returns:
            Any: 格式化后的内容
        """
        self.logger.debug(f"格式化输出: {output_format}")
        
        if output_format == 'json':
            return json.dumps(content, ensure_ascii=False, indent=2)
        elif output_format == 'html':
            return self._convert_to_html(content)
        else:
            return content
    
    def _convert_to_html(self, content: Dict[str, Any]) -> str:
        """
        转换为HTML格式
        
        Args:
            content (Dict[str, Any]): 报告内容
        
        Returns:
            str: HTML格式的报告
        """
        self.logger.debug("转换为HTML格式")
        
        html_parts = [
            "<html><head><title>股票回测报告</title></head><body>",
            f"<h1>{content.get('title', '股票回测报告')}</h1>"
        ]
        
        # 添加摘要信息
        if 'summary' in content:
            html_parts.append("<h2>摘要信息</h2>")
            html_parts.append("<ul>")
            for key, value in content['summary'].items():
                html_parts.append(f"<li>{key}: {value}</li>")
            html_parts.append("</ul>")
        
        # 添加关键指标
        if 'key_metrics' in content:
            html_parts.append("<h2>关键指标</h2>")
            html_parts.append("<ul>")
            for key, value in content['key_metrics'].items():
                html_parts.append(f"<li>{key}: {value}</li>")
            html_parts.append("</ul>")
        
        # 添加性能摘要
        if 'performance_summary' in content:
            html_parts.append("<h2>性能摘要</h2>")
            html_parts.append(f"<p>{content['performance_summary']}</p>")
        
        html_parts.append("</body></html>")
        
        html_content = "\n".join(html_parts)
        self.logger.debug(f"HTML转换完成，长度: {len(html_content)}")
        
        return html_content
    
    def register_report_type(self, name: str, generator_func):
        """
        注册新的报告类型
        
        Args:
            name (str): 报告类型名称
            generator_func: 报告生成函数
        """
        self.logger.info(f"注册新报告类型: {name}")
        self.report_types[name] = generator_func
        self.logger.debug(f"当前已注册报告类型: {list(self.report_types.keys())}")
    
    def get_available_report_types(self) -> List[str]:
        """
        获取可用的报告类型
        
        Returns:
            List[str]: 可用的报告类型列表
        """
        return list(self.report_types.keys())
    
    def save_report(self, report: Dict[str, Any], filename: str, format_type: str = 'json') -> Dict[str, Any]:
        """
        保存报告到文件
        
        Args:
            report (Dict[str, Any]): 报告内容
            filename (str): 文件名
            format_type (str): 保存格式
        
        Returns:
            Dict[str, Any]: 保存结果
        """
        self.logger.info(f"保存报告到文件: {filename}, 格式: {format_type}")
        
        try:
            content = report.get('content', report)
            
            if format_type == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    if isinstance(content, str):
                        f.write(content)
                    else:
                        json.dump(content, f, ensure_ascii=False, indent=2)
            elif format_type == 'html':
                html_content = content if isinstance(content, str) else self._convert_to_html(content)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            else:
                error_msg = f"不支持的保存格式: {format_type}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            self.logger.info(f"报告已保存到: {filename}")
            return {'success': True, 'filename': filename, 'format': format_type}
            
        except Exception as e:
            error_msg = f"保存报告失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}