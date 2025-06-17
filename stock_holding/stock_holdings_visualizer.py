# -*- coding: utf-8 -*-
"""
个股机构持仓可视化工具

基于merged_holdings_data.csv数据，创建个股的机构持仓情况曲线图
支持按股票代码查询，显示不同机构类型的持仓比例变化趋势
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StockHoldingsVisualizer:
    """
    个股机构持仓可视化类
    """
    
    def __init__(self, data_file_path: str = None):
        """
        初始化可视化工具
        
        Args:
            data_file_path: 数据文件路径，默认使用项目中的merged_holdings_data.csv
        """
        if data_file_path is None:
            # 默认数据文件路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_file_path = os.path.join(
                current_dir, 
                'institutional_holdings_data', 
                'processed_data', 
                'merged_holdings_data.csv'
            )
        
        self.data_file_path = data_file_path
        self.data = None
        self.load_data()
    
    def load_data(self):
        """
        加载数据文件
        """
        try:
            if not os.path.exists(self.data_file_path):
                raise FileNotFoundError(f"数据文件不存在: {self.data_file_path}")
            
            print(f"正在加载数据文件: {self.data_file_path}")
            self.data = pd.read_csv(self.data_file_path, encoding='utf-8')
            
            # 数据预处理
            self._preprocess_data()
            
            print(f"数据加载成功，共 {len(self.data)} 条记录")
            print(f"包含股票数量: {self.data['股票代码'].nunique()}")
            print(f"机构类型: {', '.join(self.data['institution_type'].unique())}")
            print(f"报告期范围: {self.data['report_date'].min()} - {self.data['report_date'].max()}")
            
        except Exception as e:
            print(f"加载数据失败: {str(e)}")
            sys.exit(1)
    
    def _preprocess_data(self):
        """
        数据预处理
        """
        # 确保股票代码为字符串格式
        self.data['股票代码'] = self.data['股票代码'].astype(str).str.zfill(6)
        
        # 转换报告日期为datetime格式
        self.data['report_date'] = pd.to_datetime(self.data['report_date'], format='%Y%m%d')
        
        # 确保数值列为数值类型
        numeric_columns = ['占总股本比例', '占流通股比例', '持股变动比例']
        for col in numeric_columns:
            if col in self.data.columns:
                self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
        
        # 按日期排序
        self.data = self.data.sort_values(['股票代码', 'report_date', 'institution_type'])
    
    def get_available_stocks(self) -> List[str]:
        """
        获取可用的股票代码列表
        
        Returns:
            股票代码列表
        """
        return sorted(self.data['股票代码'].unique())
    
    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票信息字典
        """
        stock_data = self.data[self.data['股票代码'] == stock_code]
        
        if stock_data.empty:
            return {}
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_data['股票简称'].iloc[0],
            'industry': stock_data.get('所属行业', pd.Series(['未知'])).iloc[0],
            'data_points': len(stock_data),
            'date_range': f"{stock_data['report_date'].min().strftime('%Y-%m-%d')} 至 {stock_data['report_date'].max().strftime('%Y-%m-%d')}",
            'institution_types': sorted(stock_data['institution_type'].unique())
        }
    
    def plot_holdings_trend(self, stock_code: str, save_path: str = None, show_plot: bool = True) -> bool:
        """
        绘制个股机构持仓趋势图（仅显示占流通股比例变化）
        
        Args:
            stock_code: 股票代码
            save_path: 保存路径，为None时不保存
            show_plot: 是否显示图表
            
        Returns:
            是否成功绘制
        """
        # 确保股票代码格式正确
        stock_code = str(stock_code).zfill(6)
        
        # 筛选股票数据
        stock_data = self.data[self.data['股票代码'] == stock_code].copy()
        
        if stock_data.empty:
            print(f"未找到股票代码 {stock_code} 的数据")
            return False
        
        # 获取股票信息
        stock_info = self.get_stock_info(stock_code)
        
        # 创建单个图表
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.suptitle(f'{stock_info["stock_name"]} ({stock_code}) 机构持仓占流通股比例变化', fontsize=16, fontweight='bold')
        
        # 绘制占流通股比例趋势
        self._plot_ratio_trend(stock_data, ax, '占流通股比例', '占流通股比例 (%)')
        
        # 调整布局
        plt.tight_layout()
        
        # 添加信息文本
        info_text = f"行业: {stock_info.get('industry', '未知')}\n数据点: {stock_info['data_points']}\n时间范围: {stock_info['date_range']}"
        fig.text(0.02, 0.02, info_text, fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        # 保存图表
        if save_path:
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"图表已保存至: {save_path}")
            except Exception as e:
                print(f"保存图表失败: {str(e)}")
        
        # 显示图表
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return True
    
    def _plot_ratio_trend(self, data: pd.DataFrame, ax, column: str, ylabel: str):
        """
        绘制持仓比例趋势图
        """
        # 按机构类型分组绘制
        for inst_type in data['institution_type'].unique():
            inst_data = data[data['institution_type'] == inst_type]
            if not inst_data.empty and column in inst_data.columns:
                ax.plot(inst_data['report_date'], inst_data[column], 
                       marker='o', linewidth=2, markersize=6, label=inst_type)
        
        ax.set_title(f'{ylabel}变化趋势', fontsize=12, fontweight='bold')
        ax.set_xlabel('报告期', fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴日期
        ax.tick_params(axis='x', rotation=45)
    

    

    
    def generate_summary_report(self, stock_code: str) -> str:
        """
        生成股票持仓摘要报告（专注于占流通股比例）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            摘要报告文本
        """
        stock_code = str(stock_code).zfill(6)
        stock_data = self.data[self.data['股票代码'] == stock_code]
        
        if stock_data.empty:
            return f"未找到股票代码 {stock_code} 的数据"
        
        stock_info = self.get_stock_info(stock_code)
        
        report = []
        report.append(f"\n{'='*50}")
        report.append(f"股票持仓占流通股比例分析报告")
        report.append(f"{'='*50}")
        report.append(f"股票代码: {stock_code}")
        report.append(f"股票名称: {stock_info['stock_name']}")
        report.append(f"所属行业: {stock_info.get('industry', '未知')}")
        report.append(f"数据时间: {stock_info['date_range']}")
        report.append(f"数据点数: {stock_info['data_points']}")
        report.append(f"\n机构类型: {', '.join(stock_info['institution_types'])}")
        
        # 最新持仓情况
        latest_date = stock_data['report_date'].max()
        latest_data = stock_data[stock_data['report_date'] == latest_date]
        
        report.append(f"\n最新占流通股比例情况 ({latest_date.strftime('%Y-%m-%d')}):")
        
        # 计算总计占流通股比例
        total_latest = latest_data['占流通股比例'].sum()
        report.append(f"机构总计占流通股比例: {total_latest:.2f}%")
        report.append("")
        
        for _, row in latest_data.iterrows():
            report.append(f"  {row['institution_type']}: 占流通股 {row.get('占流通股比例', 0):.2f}%")
        
        # 持仓变化趋势
        if len(stock_data) > 1:
            report.append(f"\n占流通股比例变化趋势:")
            
            # 计算总体趋势
            total_by_date = stock_data.groupby('report_date')['占流通股比例'].sum().sort_index()
            
            if len(total_by_date) >= 2:
                first_total = total_by_date.iloc[0]
                last_total = total_by_date.iloc[-1]
                change = last_total - first_total
                change_pct = (change / first_total * 100) if first_total > 0 else 0
                
                report.append(f"  总体变化: {first_total:.2f}% → {last_total:.2f}% ({change:+.2f}%, {change_pct:+.1f}%)")
                
                # 最高和最低
                max_ratio = total_by_date.max()
                min_ratio = total_by_date.min()
                max_date = total_by_date.idxmax().strftime('%Y-%m-%d')
                min_date = total_by_date.idxmin().strftime('%Y-%m-%d')
                report.append(f"  期间最高: {max_ratio:.2f}% ({max_date})")
                report.append(f"  期间最低: {min_ratio:.2f}% ({min_date})")
            
            # 各机构类型趋势
            report.append(f"\n各机构类型趋势:")
            for inst_type in stock_data['institution_type'].unique():
                inst_data = stock_data[stock_data['institution_type'] == inst_type].sort_values('report_date')
                if len(inst_data) > 1 and '占流通股比例' in inst_data.columns:
                    first_ratio = inst_data['占流通股比例'].iloc[0]
                    last_ratio = inst_data['占流通股比例'].iloc[-1]
                    change = last_ratio - first_ratio
                    trend = "上升" if change > 0 else "下降" if change < 0 else "持平"
                    avg_ratio = inst_data['占流通股比例'].mean()
                    report.append(f"  {inst_type}: {trend} ({change:+.2f}个百分点), 平均{avg_ratio:.2f}%")
        
        return "\n".join(report)

def main():
    """
    主函数 - 命令行接口
    """
    parser = argparse.ArgumentParser(description='个股机构持仓可视化工具')
    parser.add_argument('stock_code', help='股票代码（6位数字）')
    parser.add_argument('--data-file', help='数据文件路径')
    parser.add_argument('--save-path', help='图表保存路径')
    parser.add_argument('--no-show', action='store_true', help='不显示图表')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告，不绘制图表')
    
    args = parser.parse_args()
    
    # 初始化可视化工具
    visualizer = StockHoldingsVisualizer(args.data_file)
    
    # 检查股票代码是否存在
    available_stocks = visualizer.get_available_stocks()
    stock_code = str(args.stock_code).zfill(6)
    
    if stock_code not in available_stocks:
        print(f"错误: 股票代码 {stock_code} 不存在")
        print(f"可用股票代码示例: {', '.join(available_stocks[:10])}")
        return
    
    # 生成摘要报告
    report = visualizer.generate_summary_report(stock_code)
    print(report)
    
    # 绘制图表（如果需要）
    if not args.report_only:
        success = visualizer.plot_holdings_trend(
            stock_code=stock_code,
            save_path=args.save_path,
            show_plot=not args.no_show
        )
        
        if not success:
            print("绘制图表失败")
            return
    
    print("\n分析完成！")

if __name__ == "__main__":
    # 如果直接运行，提供交互式界面
    if len(sys.argv) == 1:
        print("个股机构持仓可视化工具")
        print("=" * 30)
        
        # 初始化工具
        visualizer = StockHoldingsVisualizer()
        
        # 显示可用股票
        available_stocks = visualizer.get_available_stocks()
        print(f"\n数据库中共有 {len(available_stocks)} 只股票")
        print(f"股票代码示例: {', '.join(available_stocks[:10])}")
        
        # 用户输入
        while True:
            stock_code = input("\n请输入股票代码（6位数字，输入'quit'退出）: ").strip()
            
            if stock_code.lower() == 'quit':
                break
            
            if not stock_code.isdigit() or len(stock_code) != 6:
                print("请输入正确的6位股票代码")
                continue
            
            if stock_code not in available_stocks:
                print(f"股票代码 {stock_code} 不存在于数据库中")
                continue
            
            # 生成报告和图表
            print(visualizer.generate_summary_report(stock_code))
            
            show_chart = input("\n是否显示图表？(y/n): ").strip().lower()
            if show_chart in ['y', 'yes', '是']:
                visualizer.plot_holdings_trend(stock_code)
    else:
        main()