import subprocess
import time
import pytesseract
import os
import re
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
from pypinyin import pinyin, Style
import datetime
import matplotlib.dates as mdates
import numpy as np
from PIL import ImageEnhance
import logging
import sys

# 创建logs目录
os.makedirs("logs", exist_ok=True)

# 设置日志
log_timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join("logs", f"{log_timestamp}_house_price.log")

# 配置日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# 重定向标准输出和标准错误到日志文件
sys.stdout = open(log_file, 'a', encoding='utf-8')
sys.stderr = open(log_file, 'a', encoding='utf-8')

# 在绘图前设置全局字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

# 设置Tesseract OCR的路径（如果不在系统路径中）
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def get_pinyin_initials(text):
    return ''.join([item[0][0] for item in pinyin(text, style=Style.FIRST_LETTER)])

def adb_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Error executing command: {command}\n{result.stderr}")
    return result.stdout.strip()

def set_resolution(width, height):
    adb_command(f"adb shell wm size {width}x{height}")

def capture_screenshot(filename="screenshot.png"):
    adb_command(f"adb shell screencap -p /sdcard/{filename}")
    adb_command(f"adb pull /sdcard/{filename} images/temp/{filename}")
    adb_command(f"adb shell rm /sdcard/{filename}")

def scroll_up():
    start_x = 500  # X coordinate remains the same
    start_y = 1700  # Starting Y coordinate
    end_x = 500    # X coordinate remains the same
    end_y = 1100  # Ending Y coordinate is `pixels` amount up from start_y
    adb_command(f"adb shell input swipe {start_x} {start_y} {end_x} {end_y}")
    time.sleep(1)  # wait for the scroll to finish

def tap_screen(x, y):
    """点击屏幕上的指定坐标"""
    logger.info(f"点击屏幕坐标: ({x}, {y})")
    adb_command(f"adb shell input tap {x} {y}")
    time.sleep(1)  # 等待点击操作完成

def check_and_click_load_more(filename="screenshot.png"):
    """检查屏幕底部是否有"点击加载更多"文字或"加载失败"文字，如果有则点击"""
    input_path = f"images/temp/{filename}"
    
    # 打开图片
    img = Image.open(input_path)
    
    # 截取屏幕底部区域进行OCR识别
    bottom_height = 200  # 底部区域高度
    bottom_area = img.crop((0, img.height - bottom_height, img.width, img.height))
    
    # 对底部区域进行OCR识别
    text = pytesseract.image_to_string(bottom_area, lang='chi_sim', config='--psm 6')
    text = text.replace(' ', '')
    
    # 检查是否包含"点击加载更多"或类似文字，或"加载失败"
    load_more_patterns = ["点击加载更多", "加载更多", "点击查看更多", "查看更多", "加载失败"]
    found_pattern = None
    
    for pattern in load_more_patterns:
        if pattern in text:
            found_pattern = pattern
            break
    
    if found_pattern:
        logger.info(f'检测到"{found_pattern}"文字，准备点击')
        # 计算点击位置（屏幕底部中间位置）
        tap_x = img.width // 2
        tap_y = img.height - bottom_height // 2
        
        # 点击该位置
        tap_screen(tap_x, tap_y)
        return True
    
    return False

def preprocess_image(filename):
    # 更新文件路径
    input_path = f"images/temp/{filename}"
    output_path = f"images/temp/preprocessed_{filename}"
    
    # 确保目录存在
    os.makedirs("images/temp", exist_ok=True)
    
    # 图像处理代码
    img = Image.open(input_path)
    # Remove top 210 pixels
    img = img.crop((0, 210, img.width, img.height))
    # Enhance image contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)  # Increase contrast
    # Convert the image to grayscale
    img = img.convert("L")
    # Convert the image to binary (black and white) using a threshold
    threshold = 127
    img = img.point(lambda p: p > threshold and 255)
    img.save(output_path)
    return f"preprocessed_{filename}"

def parse_text(text, valid_communities):
    entries = []
    logger.info("parse text")
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        logger.info(line)
        if not line:
            continue
        if "号楼" in line:
            # Ensure there are enough lines available
            if i + 1 < len(lines):
                date_line = lines[i + 1].strip()
                logger.info(date_line)
                area_line = lines[i].strip().split("号楼")[-1]
                logger.info(area_line)
                price_line = lines[i + 1].strip()
                logger.info(price_line)
                match_date = re.search(r'(\d{4}\.\d{2}\.\d{2})成交', date_line)
                logger.info(str(match_date))
                match_area = re.search(r'(\d{2,3})[a-zA-Z]', area_line)
                logger.info(str(match_area))
                match_price = re.search(r'(\d+)元', price_line)
                logger.info(str(match_price))
                if match_date and match_area and match_price:
                    date = match_date.group(1)
                    area = int(match_area.group(1))
                    price = int(match_price.group(1))
                    entries.append({
                        'date': date,
                        'area': area,
                        'price': price
                    })
    return entries

def save_entries(entries, filename):
    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 加载现有数据
    existing_entries = []
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                existing_entries = json.loads(content)
    
    # 合并条目
    all_entries = existing_entries + entries
    
    # 按日期排序（降序：最新的日期在前）
    all_entries.sort(key=lambda x: x['date'], reverse=True)
    
    # 保存排序后的数据
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=4)
    logger.info(f"已保存 {len(entries)} 条记录到 {filename}，总计 {len(all_entries)} 条")

def capture_and_ocr(screenshot_count=50000, width=1080, height=1920, save_interval=10, json_filename="entries.json", max_duplicates=3):
    # 设置设备分辨率
    set_resolution(width, height)
    entries = []
    valid_communities = ['浦东', '嘉定', '金山', '松江', '青浦', '黄浦', '虹口', '崇明', '宝山']
    
    # 确保目录存在
    os.makedirs("data_files", exist_ok=True)
    os.makedirs("images/temp", exist_ok=True)
    os.makedirs("images/final", exist_ok=True)
    
    # 更新JSON文件路径
    json_filepath = os.path.join("data_files", json_filename)
    
    # 加载现有条目用于检查重复
    existing_entries = []
    if os.path.exists(json_filepath):
        with open(json_filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                existing_entries = json.loads(content)
    
    # 创建一个集合来快速检查条目是否存在
    existing_entries_set = {(entry['date'], entry['area'], entry['price']) for entry in existing_entries}
    
    # 用于跟踪连续重复的条目数量
    consecutive_duplicates = 0
    screenshot_count = 0
    
    while True:  # 无限循环，直到满足退出条件
        screenshot_count += 1
        filename = "screenshot.png"
        capture_screenshot(filename)
        logger.info(f"截图 #{screenshot_count} 保存为 images/temp/{filename}")
        
        # 检查并点击"加载更多"按钮
        clicked_load_more = check_and_click_load_more(filename)
        if clicked_load_more:
            # 如果点击了加载更多，等待内容加载并重新截图
            time.sleep(2)  # 等待内容加载
            capture_screenshot(filename)
            logger.info(f"点击加载更多后重新截图: images/temp/{filename}")
        
        # Preprocess the image
        preprocessed_filename = preprocess_image(filename)
        logger.info(f"预处理图像保存为 images/temp/{preprocessed_filename}")
        # OCR
        img = Image.open(f"images/temp/{preprocessed_filename}")
        text = pytesseract.image_to_string(img, lang='chi_sim', config='--psm 6')
        text = text.replace(' ', '')
        logger.info(f"文本提取结果（第 {screenshot_count} 部分）：\n{text}\n")

        # 检查是否包含"没有更多数据"
        if "没有更多数据" in text:
            logger.info("检测到'没有更多数据'，退出循环")
            save_entries(entries, json_filepath)
            break

        new_entries = parse_text(text, valid_communities)
        
        # 检查新条目是否已存在
        all_duplicates = True
        if new_entries:  # 确保有解析到条目
            for entry in new_entries:
                entry_tuple = (entry['date'], entry['area'], entry['price'])
                if entry_tuple not in existing_entries_set:
                    all_duplicates = False
                    consecutive_duplicates = 0
                    existing_entries_set.add(entry_tuple)  # 添加到已存在集合中
                    
            if all_duplicates:
                consecutive_duplicates += 1
                logger.info(f"连续重复数据: {consecutive_duplicates}/{max_duplicates}")
                
            # 如果max_duplicates为0或负数，则禁用重复检测功能
            if max_duplicates > 0 and consecutive_duplicates >= max_duplicates:
                logger.info(f"检测到连续{max_duplicates}条重复数据，停止获取")
                save_entries(entries, json_filepath)
                break
        else:
            # 如果没有解析到条目，不计入连续重复
            consecutive_duplicates = 0
            
        entries.extend(new_entries)
        if screenshot_count % save_interval == 0:
            save_entries(entries, json_filepath)
            entries = []  # 清空已保存的条目
        
        scroll_up()
    
    # 确保最后的条目被保存
    if entries:
        save_entries(entries, json_filepath)
    
    return entries

def generate_plots(community_name):
    filename = get_pinyin_initials(community_name)  # 自动提取拼音首字母
    
    # 确保目录存在
    os.makedirs("data_files", exist_ok=True)
    os.makedirs("images/temp", exist_ok=True)
    os.makedirs("images/final", exist_ok=True)
    
    # 加载JSON文件并解析成Python对象
    json_file_path = f"data_files/{filename}"
    with open(json_file_path, 'r', encoding='utf-8') as file:
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

    # 获取最新的日期
    latest_date = df['date'].max()
    latest_date_str = latest_date.strftime('%Y年%m月%d日')
    
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
        
        # 检查筛选后的数据框是否为空
        if filtered_df.empty:
            logger.info(f"面积范围 {area_min}-{area_max} 没有数据，跳过")
            continue
    
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
    
        # 绘制月度成交量柱状图（改进版）- 现在是第二张图
        monthly_transactions = filtered_df.groupby(filtered_df['date'].dt.to_period('M')).size()
        
        # 将月度数据按年份分组
        monthly_df = pd.DataFrame({
            'date': monthly_transactions.index.to_timestamp(),
            'count': monthly_transactions.values
        })
        monthly_df['year'] = monthly_df['date'].dt.year
        monthly_df['month'] = monthly_df['date'].dt.month
        
        # 获取数据截至年月日（使用数据的最新日期而不是当前系统日期）
        data_latest_date = latest_date  # 使用之前计算的最新数据日期
        current_year = data_latest_date.year
        current_month = data_latest_date.month
        current_day = data_latest_date.day
        
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
            bars2 = axes[1].bar(year_data['date'], year_data['count'], 
                               width=width, color=color, alpha=0.7, 
                               align='center', label=f'{year}年')
        
        # 为当前月份添加预测柱子
        current_month_data = monthly_df[(monthly_df['year'] == current_year) & (monthly_df['month'] == current_month)]
        if not current_month_data.empty:
            # 获取当前月份的实际成交量
            actual_count = current_month_data['count'].iloc[0]
            current_month_date = current_month_data['date'].iloc[0]
            
            # 计算当前月份的总天数
            import calendar
            days_in_month = calendar.monthrange(current_year, current_month)[1]
            
            # 基于天数比例预测全月成交量
            if current_day < days_in_month:
                predicted_total = actual_count * days_in_month / current_day
                predicted_additional = predicted_total - actual_count
                
                # 找到当前年份对应的颜色
                year_index = years.index(current_year) if current_year in years else 0
                color = colors[year_index % len(colors)]
                
                # 绘制预测部分（在实际柱子上方）
                axes[1].bar(current_month_date, predicted_additional, 
                           width=width, color='orange', alpha=0.8, 
                           align='center', bottom=actual_count, 
                           label=f'{current_year}年预测')
        
        axes[1].set_title(f'月度成交量 (面积: {area_min}-{area_max})')
        axes[1].set_xlabel('年份')
        axes[1].set_ylabel('成交量')
        axes[1].legend(loc='upper left')
        
        # 设置横坐标只显示年份
        unique_years = sorted(set(monthly_df['year']))
        axes[1].set_xticks([pd.Timestamp(year=year, month=1, day=1) for year in unique_years])
        axes[1].set_xticklabels(unique_years, rotation=45)
        
        # 调整x轴范围，确保所有柱子都能显示
        if len(monthly_df) > 0:
            date_min = min(monthly_df['date'])
            date_max = max(monthly_df['date'])
            # 在两端各增加一个月的空间
            axes[1].set_xlim(date_min - pd.Timedelta(days=30), date_max + pd.Timedelta(days=30))
    
        # 绘制年度成交量柱状图 - 现在是第三张图
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
                        bars = axes[2].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
                        
                        # 在当前年份的柱子上叠加预测部分
                        if predicted_additional > 0:
                            axes[2].bar([current_year], [predicted_additional], bottom=[actual_sales], 
                                       color='lightblue', alpha=0.7, label='预测销量')
                            
                            # 在柱子顶部添加预测总量标签
                            total_height = actual_sales + predicted_additional
                            axes[2].annotate(f'预测: {int(total_height)}',
                                           xy=(current_year, total_height),
                                           xytext=(0, 5),
                                           textcoords="offset points",
                                           ha='center', va='bottom')
                    else:
                        bars = axes[2].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
                else:
                    bars = axes[2].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
            else:
                bars = axes[2].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
        else:
            bars = axes[2].bar(yearly_transactions.index, yearly_transactions.values, color='orange')
        
        axes[2].set_title(f'年度成交量 (面积: {area_min}-{area_max})')
        axes[2].set_xlabel('年份')
        axes[2].set_ylabel('成交量')
        axes[2].set_xticks(yearly_transactions.index)
        axes[2].set_xticklabels(yearly_transactions.index, rotation=45)
        
        # 为每个柱子添加数值标签
        for bar in bars:
            height = bar.get_height()
            axes[2].annotate('{}'.format(int(height)),
                             xy=(bar.get_x() + bar.get_width() / 2, height),
                             xytext=(0, 3),
                             textcoords="offset points",
                             ha='center', va='bottom')
        
        # 添加图例
        if current_year in yearly_transactions.index:
            axes[2].legend(loc='upper left')
        
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
    font_path = "C:\\Windows\\Fonts\\SimHei.ttf"  # 修改为黑体字体文件路径
    font_size = 72  # 您设置的字体大小
    # 修改标题文本以包含最新日期
    title_text = f"{community_name} (数据截至: {latest_date_str})"
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
    current_date = datetime.datetime.now().strftime('%Y%m%d')
    final_image_path = f"images/final/{community_name}_{current_date}.png"
    
    # 删除旧的图像文件（相同社区名称但不同日期的图像）
    import glob
    old_images_pattern = f"images/final/{community_name}_*.png"
    old_images = glob.glob(old_images_pattern)
    for old_image in old_images:
        try:
            os.remove(old_image)
            logger.info(f"已删除旧图像: {old_image}")
        except FileNotFoundError:
            # 文件不存在，忽略
            pass
        except Exception as e:
            logger.warning(f"删除旧图像失败 {old_image}: {e}")
    
    # 缩放图像到30%
    combined_image_resized = combined_image.resize(
        (int(combined_image.width * 0.3), int(combined_image.height * 0.3)), 
        Image.LANCZOS  # 使用LANCZOS算法提供更好的缩小质量
    )
    
    # 保存缩放后的图像
    combined_image_resized.save(final_image_path)
    
    # 删除中间过程的图像文件
    for image_path in images:
        os.remove(image_path)
    
    logger.info(f"Combined image saved as {final_image_path}")
    return final_image_path

def deduplicate_json_file(json_filepath):
    """对JSON文件中的数据进行去重处理"""
    logger.info(f"开始对 {json_filepath} 进行去重处理...")
    
    # 读取JSON文件
    if not os.path.exists(json_filepath):
        logger.warning(f"文件 {json_filepath} 不存在，无法进行去重")
        return False
    
    with open(json_filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            logger.warning(f"文件 {json_filepath} 为空，无法进行去重")
            return False
        entries = json.loads(content)
    
    original_count = len(entries)
    logger.info(f"原始数据条数: {original_count}")
    
    # 使用集合进行去重
    unique_entries = []
    unique_tuples = set()
    
    for entry in entries:
        entry_tuple = (entry['date'], entry['area'], entry['price'])
        if entry_tuple not in unique_tuples:
            unique_tuples.add(entry_tuple)
            unique_entries.append(entry)
    
    # 按日期排序（降序：最新的日期在前）
    unique_entries.sort(key=lambda x: x['date'], reverse=True)
    
    # 保存去重后的数据
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(unique_entries, f, ensure_ascii=False, indent=4)
    
    new_count = len(unique_entries)
    removed_count = original_count - new_count
    logger.info(f"去重后数据条数: {new_count}，移除了 {removed_count} 条重复数据")
    
    return True

if __name__ == "__main__":
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description="房价数据采集与分析工具")
    parser.add_argument("-n", "--name", type=str, required=True, help="小区名称")
    parser.add_argument("-c", "--count", type=int, default=100, help="截图数量")
    parser.add_argument("--collect", action="store_true", help="采集数据模式")
    parser.add_argument("--plot", action="store_true", help="生成图表模式")
    parser.add_argument("--ignore_duplicates", action="store_true", help="忽略重复数据检测（默认检测3组重复后停止）")
    
    args = parser.parse_args()
    
    # 获取小区名称并转换为拼音首字母
    community_name = args.name
    filename = get_pinyin_initials(community_name)
    
    # 确保目录存在
    os.makedirs("data_files", exist_ok=True)
    os.makedirs("images/temp", exist_ok=True)
    os.makedirs("images/final", exist_ok=True)
    
    # 如果没有指定模式，默认执行两种操作
    if not args.collect and not args.plot:
        args.collect = True
        args.plot = True
    
    # 执行数据采集
    if args.collect:
        logger.info(f"开始采集 {community_name} 的房价数据...")
        # 设置max_duplicates参数
        max_duplicates = 0 if args.ignore_duplicates else 3
        capture_and_ocr(screenshot_count=args.count, json_filename=filename, max_duplicates=max_duplicates)
        
        # 数据采集完成后进行去重处理
        logger.info(f"数据采集完成，对 {community_name} 的房价数据进行去重...")
        deduplicate_json_file(os.path.join("data_files", filename))
    
    # 执行图表生成
    if args.plot:
        logger.info(f"开始生成 {community_name} 的房价分析图表...")
        image_path = generate_plots(community_name)
        logger.info(f"图表已生成: {image_path}")
