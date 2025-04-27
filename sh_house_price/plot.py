import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
from pypinyin import pinyin, Style
import argparse
import datetime
import matplotlib.dates as mdates
import numpy as np

# 在绘图前设置全局字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

def get_pinyin_initials(text):
    return ''.join([item[0][0] for item in pinyin(text, style=Style.FIRST_LETTER)])

# 设置命令行参数解析
parser = argparse.ArgumentParser(description="Generate real estate analysis charts.")
parser.add_argument("-n", "--name", type=str, required=True, help="Name of the community")
args = parser.parse_args()

current_community = args.name
filename = get_pinyin_initials(current_community)  # 自动提取拼音首字母

# 确保目录存在
os.makedirs("data_files", exist_ok=True)
os.makedirs("images/temp", exist_ok=True)
os.makedirs("images/final", exist_ok=True)

# 加载JSON文件并解析成Python对象
with open(f"data_files/{filename}", 'r', encoding='utf-8') as file:
    data = json.load(file)

# 转换成DataFrame格式
df = pd.DataFrame(data)

# 剔除价格为0和小于20000的异常值
df = df[(df['price'] != 0) & (df['price'] >= 20000)]

# 将面积转换为字符串类型，然后提取数字 - 修复无效的转义序列
df['area'] = df['area'].astype(str).str.extract(r'(\d+)').astype(float)

# 按日期排序
df['date'] = pd.to_datetime(df['date'], format='%Y.%m.%d')
df = df.sort_values(by='date')

# 计算每年价格的平均值
df['year'] = df['date'].dt.year
yearly_avg_price = df.groupby('year')['price'].mean()

# 标记异常值
df['avg_price'] = df['year'].map(yearly_avg_price)
df['is_outlier'] = df['price'] > 2 * df['avg_price']

# 剔除异常值
df = df[~df['is_outlier']]

# 定义面积范围
area_ranges = [(0, 60), (60, 80), (80, 100), (100, 120), (120, float('inf'))]

# 用于存储每个子图的路径
images = []

# 循环处理每个面积范围
for area_range in area_ranges:
    area_min, area_max = area_range

    # 筛选符合面积范围的数据
    filtered_df = df[(df['area'] >= area_min) & (df['area'] < area_max)].copy()  # 使用.copy()创建副本避免SettingWithCopyWarning

    # 添加月份列
    filtered_df['year_month'] = filtered_df['date'].dt.strftime('%Y-%m')
    
    # 计算每月平均价格
    monthly_avg = filtered_df.groupby('year_month')['price'].mean().reset_index()
    monthly_avg['date'] = pd.to_datetime(monthly_avg['year_month'])
    
    # 确保每月都有数据（如果某月没有数据，使用上个月的数据）
    all_months = pd.date_range(start=filtered_df['date'].min(), end=filtered_df['date'].max(), freq='MS')
    all_months_df = pd.DataFrame({'date': all_months})
    all_months_df['year_month'] = all_months_df['date'].dt.strftime('%Y-%m')
    
    # 合并实际数据和所有月份
    monthly_avg_complete = pd.merge(all_months_df, monthly_avg[['year_month', 'price']], 
                                    on='year_month', how='left')
    
    # 向前填充缺失值（使用上个月的数据）- 修复弃用警告
    monthly_avg_complete['price'] = monthly_avg_complete['price'].ffill()
    
    # 创建一个图形对象
    fig, axes = plt.subplots(nrows=3, figsize=(10, 15))

    # 绘制价格月度均值图
    axes[0].plot(monthly_avg_complete['date'], monthly_avg_complete['price'], label='月度均价', color='blue')
    axes[0].scatter(filtered_df['date'], filtered_df['price'], label='成交价', color='red', marker='o', alpha=0.3)
    
    # 添加固定价格水平线
    price_levels = range(30000, 100000, 10000)  # 从30000到90000每隔10000的水平线
    for level in price_levels:
        axes[0].axhline(level, color='grey', linestyle='--', linewidth=0.7, alpha=0.7)
        axes[0].text(filtered_df['date'].min(), level, f'{level}', color='grey', alpha=0.7, va='center')

    # 添加平均价格的水平线
    avg_price = filtered_df['price'].mean()
    axes[0].axhline(avg_price, color='green', linestyle='--', linewidth=1, label=f'总均价: {avg_price:.2f}')

    axes[0].set_title(f'月度均价 vs 日期 (面积: {area_min}-{area_max})')
    axes[0].set_xlabel('日期')
    axes[0].set_ylabel('价格')
    axes[0].legend(loc='upper left')

    # 绘制年度成交量柱状图
    yearly_transactions = filtered_df.groupby(filtered_df['date'].dt.year).size()
    
    # 获取当前年份
    current_year = datetime.datetime.now().year
    
    # 检查是否有当前年份的数据
    if current_year in yearly_transactions.index:
        # 计算前几年每月销售占比
        filtered_df['month'] = filtered_df['date'].dt.month
        
        # 获取历史年份（不包括当前年份）
        historical_years = [year for year in yearly_transactions.index if year < current_year]
        
        if len(historical_years) > 0:
            # 计算历史年份的月度销售占比
            monthly_ratios = {}
            for year in historical_years:
                year_data = filtered_df[filtered_df['year'] == year]
                year_total = year_data.shape[0]
                if year_total > 0:  # 避免除以零
                    for month in range(1, 13):
                        month_data = year_data[year_data['month'] == month]
                        month_count = month_data.shape[0]
                        if month not in monthly_ratios:
                            monthly_ratios[month] = []
                        monthly_ratios[month].append(month_count / year_total)
            
            # 计算每月平均占比
            avg_monthly_ratios = {month: sum(ratios)/len(ratios) if ratios else 0 
                                for month, ratios in monthly_ratios.items()}
            
            # 获取当前年份已有数据的最后一个月
            current_year_data = filtered_df[filtered_df['year'] == current_year]
            current_months = current_year_data['month'].unique()
            last_month = max(current_months) if len(current_months) > 0 else 0
            
            # 计算当前年份已有销量
            current_year_sales = current_year_data.shape[0]
            
            # 如果当前年份有数据且不是12月（即年份未结束）
            if last_month > 0 and last_month < 12:
                # 计算已有月份的总占比
                completed_ratio = sum([avg_monthly_ratios.get(m, 0) for m in range(1, last_month + 1)])
                
                # 避免除以零
                if completed_ratio > 0:
                    # 预测全年销量
                    predicted_total = current_year_sales / completed_ratio
                    
                    # 创建预测数据
                    actual_sales = yearly_transactions[current_year]
                    predicted_additional = max(0, predicted_total - actual_sales)  # 确保预测增量为正
                    
                    # 绘制实际销量和预测销量
                    bars = axes[1].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
                    
                    # 在当前年份的柱子上叠加预测部分
                    if predicted_additional > 0:
                        axes[1].bar([current_year], [predicted_additional], bottom=[actual_sales], 
                                   color='lightblue', alpha=0.7, label='预测销量')
                        
                        # 在柱子顶部添加预测总量标签
                        total_height = actual_sales + predicted_additional
                        axes[1].annotate(f'预测: {int(total_height)}',
                                       xy=(current_year, total_height),
                                       xytext=(0, 5),
                                       textcoords="offset points",
                                       ha='center', va='bottom')
                else:
                    bars = axes[1].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
            else:
                bars = axes[1].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
        else:
            bars = axes[1].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
    else:
        bars = axes[1].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
    
    axes[1].set_title(f'年度成交量 (面积: {area_min}-{area_max})')
    axes[1].set_xlabel('年份')
    axes[1].set_ylabel('成交量')
    axes[1].set_xticks(yearly_transactions.index)
    axes[1].set_xticklabels(yearly_transactions.index, rotation=45)
    
    # 为每个柱子添加数值标签
    for bar in bars:
        height = bar.get_height()
        axes[1].annotate('{}'.format(int(height)),
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),
                         textcoords="offset points",
                         ha='center', va='bottom')
    
    # 添加图例
    if current_year in yearly_transactions.index:
        axes[1].legend(loc='upper left')

    # 绘制月度成交量柱状图（改进版）
    monthly_transactions = filtered_df.groupby(filtered_df['date'].dt.to_period('M')).size()
    
    # 将月度数据按年份分组
    monthly_df = pd.DataFrame({
        'date': monthly_transactions.index.to_timestamp(),
        'count': monthly_transactions.values
    })
    monthly_df['year'] = monthly_df['date'].dt.year
    
    # 设置柱子宽度
    width = 20  # 以天为单位的宽度
    
    # 定义两种交替的颜色
    colors = ['#4CAF50', '#2196F3']  # 绿色和蓝色
    
    # 获取所有年份并排序
    years = sorted(monthly_df['year'].unique())
    
    # 为每个年份绘制柱状图，使用交替的颜色
    for i, year in enumerate(years):
        year_data = monthly_df[monthly_df['year'] == year]
        color = colors[i % len(colors)]  # 交替使用两种颜色
        
        # 绘制该年份的柱状图
        bars2 = axes[2].bar(year_data['date'], year_data['count'], 
                           width=width, color=color, alpha=0.7, 
                           align='center', label=f'{year}年')
    
    axes[2].set_title(f'月度成交量 (面积: {area_min}-{area_max})')
    axes[2].set_xlabel('年份')
    axes[2].set_ylabel('成交量')
    axes[2].legend(loc='upper left')
    
    # 设置横坐标只显示年份
    unique_years = sorted(set(monthly_df['year']))
    axes[2].set_xticks([pd.Timestamp(year=year, month=1, day=1) for year in unique_years])
    axes[2].set_xticklabels(unique_years, rotation=45)
    
    # 调整x轴范围，确保所有柱子都能显示
    if len(monthly_df) > 0:
        date_min = min(monthly_df['date'])
        date_max = max(monthly_df['date'])
        # 在两端各增加一个月的空间
        axes[2].set_xlim(date_min - pd.Timedelta(days=30), date_max + pd.Timedelta(days=30))
    
    # 保存图像
    image_path = f'images/temp/plot_{area_min}_{area_max}.png'
    plt.tight_layout()
    plt.savefig(image_path, dpi=300, bbox_inches='tight')
    plt.close()
    images.append(image_path)

# 合并所有面积区间的图像并添加标题
combined_image_height = 0
combined_image_width = 0

# 获取最宽的图片宽度
for image_path in images:
    with Image.open(image_path) as img:
        if img.width > combined_image_width:
            combined_image_width = img.width
        combined_image_height += img.height

# 增加标题所需的高度
title_height = 80  # 根据需要调整高度
combined_image_height += title_height

# 创建一个新的图片
combined_image = Image.new('RGB', (combined_image_width, combined_image_height), color='white')

# 组合图片
y_offset = title_height
for image_path in images:
    with Image.open(image_path) as img:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.height

# 创建字体对象
font_path = "C:\\Windows\\Fonts\\simkai.ttf"  # 替换为您系统中的英文字体文件路径
font_size = 36
title_text = current_community
title_font = ImageFont.truetype(font_path, font_size)

# 计算标题的大小和位置
# 创建一个临时的画布来测量文本的宽度
temp_image = Image.new("RGB", (1, 1))  # 创建一个1x1像素的画布
temp_draw = ImageDraw.Draw(temp_image)
# 获取文本的边界框
text_bbox = temp_draw.textbbox((0, 0), title_text, font=title_font)
# 计算文本的宽度
title_width = text_bbox[2] - text_bbox[0]
title_position = ((combined_image.width - title_width) // 2, 20)

# 绘制标题
ImageDraw.Draw(combined_image).text(title_position, title_text, fill='black', font=title_font)

# 保存组合图像
final_image_path = f"images/final/{current_community}.png"

# 缩放图像到50%
combined_image_resized = combined_image.resize(
    (int(combined_image.width * 0.3), int(combined_image.height * 0.3)), 
    Image.LANCZOS  # 使用LANCZOS算法提供更好的缩小质量
)

# 保存缩放后的图像
combined_image_resized.save(final_image_path)

# 删除中间过程的图像文件
for image_path in images:
    os.remove(image_path)

print(f"Combined image saved as {final_image_path}")