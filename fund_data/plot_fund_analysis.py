import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
from collections import defaultdict

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def is_quarter_end_date(date_str):
    """
    判断是否为季度末日期
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        # 季度末日期：03-31, 06-30, 09-30, 12-31
        quarter_ends = [
            (3, 31), (6, 30), (9, 30), (12, 31)
        ]
        return (date_obj.month, date_obj.day) in quarter_ends
    except ValueError:
        return False

def load_fund_data(json_file):
    """
    加载基金数据
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['基金数据']

def aggregate_fund_data(fund_data):
    """
    汇总所有基金的数据，只保留季度末数据
    """
    # 用于存储汇总数据
    aggregated_data = defaultdict(lambda: {
        '期间申购': 0,
        '期间赎回': 0,
        '期末总份额': 0,
        '基金数量': 0
    })
    
    print(f"正在处理 {len(fund_data)} 只基金的数据...")
    
    total_records = 0
    quarter_records = 0
    
    for fund in fund_data:
        fund_code = fund['基金代码']
        fund_name = fund['基金名称']
        scale_data = fund['规模变动数据']
        
        fund_quarter_records = 0
        
        for record in scale_data:
            date = record['日期']
            total_records += 1
            
            # 只处理季度末数据
            if not is_quarter_end_date(date):
                continue
                
            quarter_records += 1
            fund_quarter_records += 1
            
            # 处理期间申购
            try:
                purchase = record['期间申购（亿份）']
                if purchase != '---' and purchase != '' and purchase != '0.00':
                    purchase_value = float(purchase)
                    aggregated_data[date]['期间申购'] += purchase_value
            except (ValueError, TypeError):
                pass
            
            # 处理期间赎回
            try:
                redemption = record['期间赎回（亿份）']
                if redemption != '---' and redemption != '' and redemption != '0.00':
                    redemption_value = float(redemption)
                    aggregated_data[date]['期间赎回'] += redemption_value
            except (ValueError, TypeError):
                pass
            
            # 处理期末总份额
            try:
                total_shares = record['期末总份额（亿份）']
                if total_shares != '---' and total_shares != '' and total_shares != '0.00':
                    shares_value = float(total_shares)
                    aggregated_data[date]['期末总份额'] += shares_value
            except (ValueError, TypeError):
                pass
            
            # 记录该日期有数据的基金数量
            aggregated_data[date]['基金数量'] += 1
        
        if fund_quarter_records > 0:
            print(f"处理基金: {fund_code} - {fund_name}, 季度数据条数: {fund_quarter_records}")
    
    print(f"\n数据过滤统计:")
    print(f"总记录数: {total_records}")
    print(f"季度末记录数: {quarter_records}")
    print(f"过滤掉的记录数: {total_records - quarter_records}")
    
    return aggregated_data

def prepare_plot_data(aggregated_data):
    """
    准备绘图数据
    """
    # 转换为DataFrame
    df_data = []
    for date_str, values in aggregated_data.items():
        try:
            # 尝试解析日期
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            df_data.append({
                '日期': date_obj,
                '日期字符串': date_str,
                '期间申购总计': values['期间申购'],
                '期间赎回总计': values['期间赎回'],
                '期末总份额总计': values['期末总份额'],
                '基金数量': values['基金数量']
            })
        except ValueError:
            continue
    
    df = pd.DataFrame(df_data)
    df = df.sort_values('日期')
    
    print(f"\n数据汇总完成:")
    print(f"时间范围: {df['日期'].min().strftime('%Y-%m-%d')} 到 {df['日期'].max().strftime('%Y-%m-%d')}")
    print(f"数据点数量: {len(df)}")
    print(f"期间申购总计范围: {df['期间申购总计'].min():.2f} - {df['期间申购总计'].max():.2f} 亿份")
    print(f"期间赎回总计范围: {df['期间赎回总计'].min():.2f} - {df['期间赎回总计'].max():.2f} 亿份")
    print(f"期末总份额总计范围: {df['期末总份额总计'].min():.2f} - {df['期末总份额总计'].max():.2f} 亿份")
    
    # 显示前几个和后几个数据点
    print(f"\n前5个数据点:")
    for _, row in df.head().iterrows():
        print(f"{row['日期字符串']}: 申购={row['期间申购总计']:.2f}, 赎回={row['期间赎回总计']:.2f}, 份额={row['期末总份额总计']:.2f}")
    
    return df

def plot_individual_charts(df, output_dir="output"):
    """
    绘制三张单独的图表
    """
    import os
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 图表1: 期间申购总计
    plt.figure(figsize=(12, 6))
    plt.plot(df['日期'], df['期间申购总计'], marker='o', linewidth=2, markersize=4, color='#2E8B57')
    plt.title('所有基金期间申购总计趋势图', fontsize=16, fontweight='bold')
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('期间申购总计 (亿份)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    # 修复横坐标显示 - 使用正确的日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3,6,9,12]))
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fund_purchase_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: fund_purchase_trend.png")
    
    # 图表2: 期间赎回总计
    plt.figure(figsize=(12, 6))
    plt.plot(df['日期'], df['期间赎回总计'], marker='s', linewidth=2, markersize=4, color='#DC143C')
    plt.title('所有基金期间赎回总计趋势图', fontsize=16, fontweight='bold')
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('期间赎回总计 (亿份)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    # 修复横坐标显示 - 使用正确的日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3,6,9,12]))
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fund_redemption_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: fund_redemption_trend.png")
    
    # 图表3: 期末总份额总计
    plt.figure(figsize=(12, 6))
    plt.plot(df['日期'], df['期末总份额总计'], marker='^', linewidth=2, markersize=4, color='#4169E1')
    plt.title('所有基金期末总份额总计趋势图', fontsize=16, fontweight='bold')
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('期末总份额总计 (亿份)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    # 修复横坐标显示 - 使用正确的日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3,6,9,12]))
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fund_total_shares_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: fund_total_shares_trend.png")

def plot_combined_chart(df, output_dir="output"):
    """
    绘制汇总图表
    """
    # 创建汇总图表，增加高度并调整布局
    fig, axes = plt.subplots(3, 1, figsize=(12, 20))
    # 调整总标题位置，避免与第一个子图重叠
    fig.suptitle('基金规模变动汇总分析', fontsize=20, fontweight='bold', y=0.99)
    
    # 子图1: 期间申购总计
    axes[0].plot(df['日期'], df['期间申购总计'], marker='o', linewidth=2, markersize=4, color='#2E8B57')
    axes[0].set_title('期间申购总计趋势', fontsize=14, fontweight='bold', pad=20)  # 增加标题间距
    axes[0].set_ylabel('期间申购总计 (亿份)', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    axes[0].tick_params(axis='x', rotation=45)
    # 修复横坐标显示
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[0].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3,6,9,12]))
    
    # 子图2: 期间赎回总计
    axes[1].plot(df['日期'], df['期间赎回总计'], marker='s', linewidth=2, markersize=4, color='#DC143C')
    axes[1].set_title('期间赎回总计趋势', fontsize=14, fontweight='bold', pad=20)
    axes[1].set_ylabel('期间赎回总计 (亿份)', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis='x', rotation=45)
    # 修复横坐标显示
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3,6,9,12]))
    
    # 子图3: 期末总份额总计
    axes[2].plot(df['日期'], df['期末总份额总计'], marker='^', linewidth=2, markersize=4, color='#4169E1')
    axes[2].set_title('期末总份额总计趋势', fontsize=14, fontweight='bold', pad=20)
    axes[2].set_xlabel('日期', fontsize=12)
    axes[2].set_ylabel('期末总份额总计 (亿份)', fontsize=12)
    axes[2].grid(True, alpha=0.3)
    axes[2].tick_params(axis='x', rotation=45)
    # 修复横坐标显示
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[2].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3,6,9,12]))
    
    # 调整子图间距，避免重叠
    plt.subplots_adjust(top=0.95, hspace=0.4)
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # 为总标题留出空间
    plt.savefig(f'{output_dir}/fund_combined_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: fund_combined_analysis.png")

def generate_summary_report(df, output_dir="output"):
    """
    生成数据汇总报告
    """
    report = f"""
# 基金规模变动数据分析报告

## 数据概览
- 分析时间范围: {df['日期'].min().strftime('%Y-%m-%d')} 至 {df['日期'].max().strftime('%Y-%m-%d')}
- 数据点数量: {len(df)} 个时间点
- 涵盖基金数量: 最多 {df['基金数量'].max()} 只基金

## 关键指标统计

### 期间申购总计 (亿份)
- 最大值: {df['期间申购总计'].max():.2f}
- 最小值: {df['期间申购总计'].min():.2f}
- 平均值: {df['期间申购总计'].mean():.2f}
- 标准差: {df['期间申购总计'].std():.2f}

### 期间赎回总计 (亿份)
- 最大值: {df['期间赎回总计'].max():.2f}
- 最小值: {df['期间赎回总计'].min():.2f}
- 平均值: {df['期间赎回总计'].mean():.2f}
- 标准差: {df['期间赎回总计'].std():.2f}

### 期末总份额总计 (亿份)
- 最大值: {df['期末总份额总计'].max():.2f}
- 最小值: {df['期末总份额总计'].min():.2f}
- 平均值: {df['期末总份额总计'].mean():.2f}
- 标准差: {df['期末总份额总计'].std():.2f}

## 生成的图表文件
1. fund_purchase_trend.png - 期间申购总计趋势图
2. fund_redemption_trend.png - 期间赎回总计趋势图
3. fund_total_shares_trend.png - 期末总份额总计趋势图
4. fund_combined_analysis.png - 汇总分析图

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(f'{output_dir}/analysis_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("已保存: analysis_report.md")

def main():
    """
    主函数
    """
    json_file = 'output/my_fund_data.json'
    output_dir = 'output'
    
    print("=== 基金规模变动数据分析 ===")
    
    try:
        # 1. 加载数据
        print("\n1. 加载基金数据...")
        fund_data = load_fund_data(json_file)
        print(f"成功加载 {len(fund_data)} 只基金的数据")
        
        # 2. 汇总数据
        print("\n2. 汇总所有基金数据...")
        aggregated_data = aggregate_fund_data(fund_data)
        
        # 3. 准备绘图数据
        print("\n3. 准备绘图数据...")
        df = prepare_plot_data(aggregated_data)
        
        if len(df) == 0:
            print("错误: 没有有效的数据用于绘图")
            return
        
        # 4. 绘制单独图表
        print("\n4. 绘制单独图表...")
        plot_individual_charts(df, output_dir)
        
        # 5. 绘制汇总图表
        print("\n5. 绘制汇总图表...")
        plot_combined_chart(df, output_dir)
        
        # 6. 生成分析报告
        print("\n6. 生成分析报告...")
        generate_summary_report(df, output_dir)
        
        print("\n=== 分析完成 ===")
        print(f"所有图表和报告已保存到 {output_dir} 目录")
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {json_file}")
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()