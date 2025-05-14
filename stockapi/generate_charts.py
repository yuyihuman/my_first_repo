import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 创建保存图表的文件夹
charts_dir = os.path.join(os.path.dirname(__file__), 'charts')
if not os.path.exists(charts_dir):
    os.makedirs(charts_dir)

# 读取所有CSV文件
data_dir = os.path.join(os.path.dirname(__file__), 'data')
all_files = [f for f in os.listdir(data_dir) if f.endswith('_eastmoney_table.csv')]

# 存储所有股票数据的字典
stocks_data = {}

# 读取每个文件的数据
for file in all_files:
    file_path = os.path.join(data_dir, file)
    try:
        # 从文件名中提取股票代码
        stock_code = file.split('_')[0]
        
        # 读取CSV文件
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 将日期列转换为日期类型
        df['日期'] = pd.to_datetime(df['日期'])
        
        # 将数值列转换为数值类型
        for col in ['持股数量', '持股市值', '持股占比', '当日增持', '5日增持', '10日增持']:
            if col in df.columns:
                # 处理中文数值表示（亿、万）和特殊字符'-'
                df[col] = df[col].astype(str).apply(lambda x: 
                    float(x.replace('亿', '')) * 100000000 if '亿' in x else 
                    (float(x.replace('万', '')) * 10000 if '万' in x else 
                     (0.0 if x == '-' else float(x))))
        
        # 按日期排序
        df = df.sort_values('日期')
        
        # 存储到字典中
        stocks_data[stock_code] = df
    except Exception as e:
        print(f"处理文件 {file} 时出错: {e}")

# 1. 近10日增持最多的10支股票
def get_top_10_day_increase():
    results = []
    
    for code, df in stocks_data.items():
        if len(df) >= 10:  # 确保有足够的数据
            # 获取最近的记录
            latest_record = df.iloc[-1]
            
            # 获取10日增持数据
            ten_day_increase = latest_record['10日增持']
            
            # 添加到结果列表
            results.append({
                'code': code,
                'ten_day_increase': ten_day_increase,
                'latest_date': latest_record['日期'],
                'latest_price': latest_record['收盘价'],
                'shareholding_ratio': latest_record['持股占比']
            })
    
    # 按10日增持排序并获取前10名
    top_10 = sorted(results, key=lambda x: x['ten_day_increase'], reverse=True)[:10]
    return top_10

# 2. 近10日持股占比上升最多的10支股票
def get_top_10_ratio_increase():
    results = []
    
    for code, df in stocks_data.items():
        if len(df) >= 10:  # 确保有足够的数据
            # 获取最近的记录和10天前的记录
            latest_record = df.iloc[-1]
            if len(df) > 10:
                past_record = df.iloc[-11]  # 10天前的记录
            else:
                past_record = df.iloc[0]  # 如果没有足够的数据，使用最早的记录
            
            # 计算持股占比变化
            ratio_change = latest_record['持股占比'] - past_record['持股占比']
            
            # 添加到结果列表
            results.append({
                'code': code,
                'ratio_change': ratio_change,
                'latest_ratio': latest_record['持股占比'],
                'past_ratio': past_record['持股占比'],
                'latest_date': latest_record['日期']
            })
    
    # 按持股占比变化排序并获取前10名
    top_10 = sorted(results, key=lambda x: x['ratio_change'], reverse=True)[:10]
    return top_10

# 3. 近5日连续增持的股票中持股占比最高的10支股票
def get_top_10_continuous_increase():
    results = []
    
    for code, df in stocks_data.items():
        if len(df) >= 5:  # 确保有足够的数据
            # 获取最近5天的记录
            recent_5_days = df.iloc[-5:]
            
            # 检查是否连续5天增持（当日增持为正）
            is_continuous_increase = all(recent_5_days['当日增持'] > 0)
            
            if is_continuous_increase:
                # 获取最近的记录
                latest_record = df.iloc[-1]
                
                # 添加到结果列表
                results.append({
                    'code': code,
                    'shareholding_ratio': latest_record['持股占比'],
                    'latest_date': latest_record['日期'],
                    'five_day_increase': latest_record['5日增持']
                })
    
    # 按持股占比排序并获取前10名
    top_10 = sorted(results, key=lambda x: x['shareholding_ratio'], reverse=True)[:10]
    return top_10

# 生成图表1：近10日增持最多的10支股票
def plot_top_10_day_increase():
    top_10 = get_top_10_day_increase()
    
    if not top_10:
        print("没有足够的数据生成近10日增持最多的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    increases = [item['ten_day_increase'] / 100000000 for item in top_10]  # 转换为亿
    
    # 创建图表
    plt.figure(figsize=(12, 8))
    bars = plt.bar(codes, increases, color='red')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{height:.2f}亿',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近10日增持最多的10支股票')
    plt.xlabel('股票代码')
    plt.ylabel('10日增持金额（亿元）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(os.path.join(charts_dir, '近10日增持最多的10支股票.png'))
    plt.close()

# 生成图表2：近10日持股占比上升最多的10支股票
def plot_top_10_ratio_increase():
    top_10 = get_top_10_ratio_increase()
    
    if not top_10:
        print("没有足够的数据生成近10日持股占比上升最多的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    ratio_changes = [item['ratio_change'] for item in top_10]
    
    # 创建图表
    plt.figure(figsize=(12, 8))
    bars = plt.bar(codes, ratio_changes, color='green')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                 f'{height:.2f}%',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近10日持股占比上升最多的10支股票')
    plt.xlabel('股票代码')
    plt.ylabel('持股占比变化（%）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(os.path.join(charts_dir, '近10日持股占比上升最多的10支股票.png'))
    plt.close()

# 生成图表3：近5日连续增持的股票中持股占比最高的10支股票
def plot_top_10_continuous_increase():
    top_10 = get_top_10_continuous_increase()
    
    if not top_10:
        print("没有足够的数据生成近5日连续增持的股票中持股占比最高的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    ratios = [item['shareholding_ratio'] for item in top_10]
    
    # 创建图表
    plt.figure(figsize=(12, 8))
    bars = plt.bar(codes, ratios, color='blue')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                 f'{height:.2f}%',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近5日连续增持的股票中持股占比最高的10支股票')
    plt.xlabel('股票代码')
    plt.ylabel('持股占比（%）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(os.path.join(charts_dir, '近5日连续增持的股票中持股占比最高的10支股票.png'))
    plt.close()

# 生成所有图表
def generate_all_charts():
    print("开始生成图表...")
    plot_top_10_day_increase()
    plot_top_10_ratio_increase()
    plot_top_10_continuous_increase()
    print(f"图表已生成并保存到 {charts_dir} 文件夹")

if __name__ == "__main__":
    generate_all_charts()