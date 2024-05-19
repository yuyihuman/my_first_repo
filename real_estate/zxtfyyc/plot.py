# -*- coding: utf-8 -*-

import json
import pandas as pd
import matplotlib.pyplot as plt
import os
from PIL import Image, ImageDraw, ImageFont

from get_data import current_community, filename

# 加载JSON文件并解析成Python对象
with open(filename, 'r', encoding='utf-8') as file:
    data = json.load(file)

# 转换成DataFrame格式
df = pd.DataFrame(data[current_community])

# 剔除价格为0的异常值
df = df[df['price'] != 0]

# 将面积转换为字符串类型，然后提取数字
df['area'] = df['area'].astype(str).str.extract('(\d+)').astype(float)

# 按日期排序
df['date'] = pd.to_datetime(df['date'], format='%Y.%m.%d')
df = df.sort_values(by='date')

# 计算每月价格的平均值
df['year_month'] = df['date'].dt.to_period('M')
monthly_avg_price = df.groupby('year_month')['price'].mean()

# 标记异常值
df['avg_price'] = df['year_month'].map(monthly_avg_price)
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
    filtered_df = df[(df['area'] >= area_min) & (df['area'] < area_max)]

    # 计算移动平均线
    filtered_df.loc[:, 'moving_avg'] = filtered_df['price'].rolling(window=5, min_periods=1).mean()

    # 绘制价格图表
    fig, axes = plt.subplots(nrows=2, figsize=(10, 10))

    # 绘制移动平均线
    axes[0].plot(filtered_df['date'], filtered_df['moving_avg'], label='Moving Average', color='blue')

    # 绘制价格散点图
    axes[0].scatter(filtered_df['date'], filtered_df['price'], label='Price', color='red', marker='o')

    # 计算每月成交数量并展示在图标题中
    monthly_transactions = filtered_df.groupby(filtered_df['date'].dt.to_period('M')).size()
    total_transactions = monthly_transactions.sum()

    # 构建标题
    title = f'Moving Average Price vs Date (Area: {area_min}-{area_max})\n'
    title += f'Total Transactions: {total_transactions}'
    axes[0].set_title(title)
    axes[0].set_xlabel('Date')
    axes[0].set_ylabel('Price')
    axes[0].legend(loc='upper left')

    # 绘制成交量柱状图
    bars = axes[1].bar(monthly_transactions.index.to_timestamp(), monthly_transactions.values, color='orange')
    axes[1].set_xlabel('Month')
    axes[1].set_ylabel('Transactions')

    # 设置x轴刻度为所有月份
    axes[1].set_xticks(monthly_transactions.index.to_timestamp())
    axes[1].set_xticklabels(monthly_transactions.index.strftime('%Y-%m'), rotation=45)

    # 在每个柱子中间添加数值标签
    for bar in bars:
        height = bar.get_height()
        axes[1].annotate('{}'.format(height),
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),
                         textcoords="offset points",
                         ha='center', va='bottom')

    # 保存图片
    image_path = f'price_and_transactions_{area_min}_{area_max}.png'
    plt.savefig(image_path)
    images.append(image_path)

    # 关闭图表
    plt.close()

# 合并图片并添加标题
image_height = 0
combined_image_width = 0

# 获取最宽的图片宽度
for image_path in images:
    with Image.open(image_path) as img:
        if img.width > combined_image_width:
            combined_image_width = img.width
        image_height += img.height

# 创建一个新的图片
combined_image = Image.new('RGB', (combined_image_width, image_height), color='white')

# 组合图片
y_offset = 0
for image_path in images:
    with Image.open(image_path) as img:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.height

# 创建字体对象
font_path = "C:\Windows\Fonts\simkai.ttf"  # 替换为您系统中的英文字体文件路径
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
combined_image.save(current_community + '.png')
