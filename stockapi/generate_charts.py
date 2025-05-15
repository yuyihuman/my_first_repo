import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
import datetime  # 添加datetime模块用于获取当前日期

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
stock_names = {}

# 首先从hk_ggt_stocks.csv文件中读取股票代码和名称的对应关系
stocks_list_file = os.path.join(data_dir, 'hk_ggt_stocks.csv')
if os.path.exists(stocks_list_file):
    try:
        stocks_df = pd.read_csv(stocks_list_file, encoding='utf-8-sig')
        # 确保股票代码列是字符串类型，保留前导零
        stocks_df['代码'] = stocks_df['代码'].astype(str).str.zfill(5)
        # 构建股票代码和名称的对应字典
        for _, row in stocks_df.iterrows():
            stock_names[row['代码']] = row['名称']
        print(f"从{stocks_list_file}中读取了{len(stock_names)}个股票代码和名称的对应关系")
    except Exception as e:
        print(f"读取{stocks_list_file}时出错: {e}")

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
        
        # 按日期排序（确保数据是按时间顺序排列的）
        df = df.sort_values('日期')
        
        # 将数值列转换为数值类型，处理'-'的情况
        for col in ['持股数量', '持股市值', '持股占比', '当日增持', '5日增持', '10日增持']:
            if col in df.columns:
                # 先处理亿和万的单位
                df[col] = df[col].astype(str).apply(lambda x: 
                    float(x.replace('亿', '')) * 100000000 if '亿' in x else 
                    (float(x.replace('万', '')) * 10000 if '万' in x else 
                     (float(x) if x != '-' else float('nan'))))
                
                # 处理'-'值，用前一天的值填充（使用ffill()代替fillna(method='ffill')）
                df[col] = df[col].ffill()
                
                # 如果第一行就是'-'，那么向后填充（使用bfill()代替fillna(method='bfill')）
                if pd.isna(df[col].iloc[0]):
                    df[col] = df[col].bfill()
                    
                # 如果仍然有NaN值（整列都是'-'的极端情况），则用0填充
                df[col] = df[col].fillna(0.0)
        
        # 存储到字典中
        stocks_data[stock_code] = df
        
        # 如果在stock_names中没有找到对应的名称，则使用代码作为名称
        if stock_code not in stock_names:
            stock_names[stock_code] = stock_code
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
    names = [stock_names.get(code, code) for code in codes]
    # 创建横坐标标签：名称和代码
    labels = [f"{name}\n{code}" for name, code in zip(names, codes)]
    increases = [item['ten_day_increase'] / 100000000 for item in top_10]
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, increases, color='red')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{height:.2f}亿',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近10日增持最多的10支股票')
    plt.xlabel('股票名称')
    plt.ylabel('10日增持金额（亿元）')
    plt.xticks(rotation=45)  # 横坐标旋转
    plt.tight_layout()
    
    # 获取当前日期作为文件名后缀
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 保存图表（添加日期后缀）
    plt.savefig(os.path.join(charts_dir, f'近10日增持最多的10支股票_{today}.png'))
    plt.close()

# 生成图表2：近10日持股占比上升最多的10支股票
def plot_top_10_ratio_increase():
    top_10 = get_top_10_ratio_increase()
    
    if not top_10:
        print("没有足够的数据生成近10日持股占比上升最多的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    names = [stock_names.get(code, code) for code in codes]
    # 创建横坐标标签：名称和代码
    labels = [f"{name}\n{code}" for name, code in zip(names, codes)]
    ratio_changes = [item['ratio_change'] for item in top_10]
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, ratio_changes, color='green')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                 f'{height:.2f}%',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近10日持股占比上升最多的10支股票')
    plt.xlabel('股票名称')
    plt.ylabel('持股占比变化（%）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 获取当前日期作为文件名后缀
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 保存图表（添加日期后缀）
    plt.savefig(os.path.join(charts_dir, f'近10日持股占比上升最多的10支股票_{today}.png'))
    plt.close()

# 生成图表3：近5日连续增持的股票中持股占比最高的10支股票
def plot_top_10_continuous_increase():
    top_10 = get_top_10_continuous_increase()
    
    if not top_10:
        print("没有足够的数据生成近5日连续增持的股票中持股占比最高的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    names = [stock_names.get(code, code) for code in codes]
    # 创建横坐标标签：名称和代码
    labels = [f"{name}\n{code}" for name, code in zip(names, codes)]
    # 这里将'ratio'改为'shareholding_ratio'
    ratios = [item['shareholding_ratio'] for item in top_10]
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, ratios, color='blue')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                 f'{height:.2f}%',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近5日连续增持的股票中持股占比最高的10支股票')
    plt.xlabel('股票名称')
    plt.ylabel('持股占比（%）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 获取当前日期作为文件名后缀
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 保存图表（添加日期后缀）
    plt.savefig(os.path.join(charts_dir, f'近5日连续增持的股票中持股占比最高的10支股票_{today}.png'))
    plt.close()

# 4. 近5日连续增持的股票中跌幅最大的10支股票
def get_top_10_continuous_increase_with_price_drop():
    results = []
    
    for code, df in stocks_data.items():
        if len(df) >= 5:  # 确保有足够的数据
            # 获取最近5天的记录
            recent_5_days = df.iloc[-5:]
            
            # 检查是否连续5天增持（当日增持为正）
            is_continuous_increase = all(recent_5_days['当日增持'] > 0)
            
            if is_continuous_increase:
                # 获取最近的记录和5天前的记录
                latest_record = df.iloc[-1]
                past_record = df.iloc[-6] if len(df) > 5 else df.iloc[0]
                
                # 计算跌幅（负值表示下跌）
                price_change_percent = (latest_record['收盘价'] - past_record['收盘价']) / past_record['收盘价'] * 100
                
                # 添加到结果列表
                results.append({
                    'code': code,
                    'price_change_percent': price_change_percent,
                    'latest_price': latest_record['收盘价'],
                    'past_price': past_record['收盘价'],
                    'latest_date': latest_record['日期'],
                    'five_day_increase': latest_record['5日增持']
                })
    
    # 按跌幅排序（从大到小，即价格变化百分比从小到大）
    top_10 = sorted(results, key=lambda x: x['price_change_percent'])[:10]
    return top_10

# 生成图表4：近5日连续增持的股票中跌幅最大的10支股票
def plot_top_10_continuous_increase_with_price_drop():
    top_10 = get_top_10_continuous_increase_with_price_drop()
    
    if not top_10:
        print("没有足够的数据生成近5日连续增持的股票中跌幅最大的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    names = [stock_names.get(code, code) for code in codes]
    # 创建横坐标标签：名称和代码
    labels = [f"{name}\n{code}" for name, code in zip(names, codes)]
    price_changes = [item['price_change_percent'] for item in top_10]
    
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, price_changes, color='purple')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height - 0.5 if height < 0 else height + 0.5,
                 f'{height:.2f}%',
                 ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
    
    plt.title('近5日连续增持的股票中跌幅最大的10支股票')
    plt.xlabel('股票名称')
    plt.ylabel('5日价格变化（%）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 获取当前日期作为文件名后缀
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 保存图表（添加日期后缀）
    plt.savefig(os.path.join(charts_dir, f'近5日连续增持的股票中跌幅最大的10支股票_{today}.png'))
    plt.close()

# 5. 近5日连续增持的股票中持股占比上升最多的10支股票
def get_top_10_continuous_increase_with_ratio_rise():
    results = []
    
    for code, df in stocks_data.items():
        if len(df) >= 5:  # 确保有足够的数据
            # 获取最近5天的记录
            recent_5_days = df.iloc[-5:]
            
            # 检查是否连续5天增持（当日增持为正）
            is_continuous_increase = all(recent_5_days['当日增持'] > 0)
            
            if is_continuous_increase:
                # 获取最近的记录和5天前的记录
                latest_record = df.iloc[-1]
                past_record = df.iloc[-6] if len(df) > 5 else df.iloc[0]
                
                # 计算持股占比变化
                ratio_change = latest_record['持股占比'] - past_record['持股占比']
                
                # 添加到结果列表
                results.append({
                    'code': code,
                    'ratio_change': ratio_change,
                    'latest_ratio': latest_record['持股占比'],
                    'past_ratio': past_record['持股占比'],
                    'latest_date': latest_record['日期'],
                    'five_day_increase': latest_record['5日增持']
                })
    
    # 按持股占比变化排序并获取前10名
    top_10 = sorted(results, key=lambda x: x['ratio_change'], reverse=True)[:10]
    return top_10

# 生成图表5：近5日连续增持的股票中持股占比上升最多的10支股票
def plot_top_10_continuous_increase_with_ratio_rise():
    top_10 = get_top_10_continuous_increase_with_ratio_rise()
    
    if not top_10:
        print("没有足够的数据生成近5日连续增持的股票中持股占比上升最多的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    names = [stock_names.get(code, code) for code in codes]
    # 创建横坐标标签：名称和代码
    labels = [f"{name}\n{code}" for name, code in zip(names, codes)]
    ratio_changes = [item['ratio_change'] for item in top_10]
    
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, ratio_changes, color='orange')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                 f'{height:.2f}%',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近5日连续增持的股票中持股占比上升最多的10支股票')
    plt.xlabel('股票名称')
    plt.ylabel('持股占比变化（%）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(os.path.join(charts_dir, '近5日连续增持的股票中持股占比上升最多的10支股票.png'))
    plt.close()

# 6. 近5日连续增持的股票中增持数额最多的10支股票
def get_top_10_continuous_increase_with_amount():
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
                    'five_day_increase': latest_record['5日增持'],
                    'latest_ratio': latest_record['持股占比'],
                    'latest_date': latest_record['日期'],
                    'latest_price': latest_record['收盘价']
                })
    
    # 按5日增持数额排序并获取前10名
    top_10 = sorted(results, key=lambda x: x['five_day_increase'], reverse=True)[:10]
    return top_10

# 生成图表6：近5日连续增持的股票中增持数额最多的10支股票
def plot_top_10_continuous_increase_with_amount():
    top_10 = get_top_10_continuous_increase_with_amount()
    
    if not top_10:
        print("没有足够的数据生成近5日连续增持的股票中增持数额最多的10支股票图表")
        return
    
    # 准备数据
    codes = [item['code'] for item in top_10]
    names = [stock_names.get(code, code) for code in codes]
    # 创建横坐标标签：名称和代码
    labels = [f"{name}\n{code}" for name, code in zip(names, codes)]
    increases = [item['five_day_increase'] / 100000000 for item in top_10]  # 转换为亿元
    
    plt.figure(figsize=(12, 8))
    bars = plt.bar(labels, increases, color='teal')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{height:.2f}亿',
                 ha='center', va='bottom', fontsize=9)
    
    plt.title('近5日连续增持的股票中增持数额最多的10支股票')
    plt.xlabel('股票名称')
    plt.ylabel('5日增持金额（亿元）')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 获取当前日期作为文件名后缀
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 保存图表（添加日期后缀）
    plt.savefig(os.path.join(charts_dir, f'近5日连续增持的股票中增持数额最多的10支股票_{today}.png'))
    plt.close()

# 生成所有图表
def generate_all_charts():
    print("开始生成图表...")
    plot_top_10_day_increase()
    plot_top_10_ratio_increase()
    plot_top_10_continuous_increase()
    plot_top_10_continuous_increase_with_price_drop()
    plot_top_10_continuous_increase_with_ratio_rise()  # 添加新图表
    plot_top_10_continuous_increase_with_amount()      # 添加新图表
    print(f"图表已生成并保存到 {charts_dir} 文件夹")

# 如果直接运行此脚本，则生成所有图表
if __name__ == "__main__":
    generate_all_charts()

# 读取股票代码和名称的对应关系
code2name = {}
stock_list_path = os.path.join(os.path.dirname(__file__), 'data', 'hk_ggt_stocks.csv')
df_code_name = pd.read_csv(stock_list_path, encoding='utf-8')
for _, row in df_code_name.iterrows():
    code2name[str(row['代码']).zfill(5)] = row['名称']