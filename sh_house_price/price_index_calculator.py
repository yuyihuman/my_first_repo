import json
import os
import shutil
from datetime import datetime
from collections import defaultdict
import statistics
from datetime import datetime as dt

def load_data_from_file(file_path):
    """从文件加载房价数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"加载文件 {file_path} 时出错: {e}")
        return []

def parse_date(date_str):
    """解析日期字符串，返回年月"""
    try:
        date_obj = datetime.strptime(date_str, '%Y.%m.%d')
        return date_obj.year, date_obj.month, date_obj.day
    except:
        return None, None, None

def calculate_monthly_stats(data_files_dir):
    """计算每月统计数据"""
    monthly_data = defaultdict(lambda: defaultdict(lambda: {'total_price': 0, 'total_area': 0, 'count': 0}))  # {(year, month): {day: {total_price, total_area, count}}}
    latest_date = None  # 记录最新的具体日期
    
    # 指定要处理的文件列表
    target_files = ['jdxc', 'sjxc', 'tz', 'wjc']
    
    # 遍历指定的数据文件
    for filename in target_files:
        file_path = os.path.join(data_files_dir, filename)
        if os.path.isfile(file_path):
            print(f"处理文件: {filename}")
            data = load_data_from_file(file_path)
            
            for record in data:
                year, month, day = parse_date(record['date'])
                # 添加面积限制：只计算70-140平米之间的数据
                if year and month and day and 70 <= record['area'] <= 140 and record['price'] > 0:
                    # 更新最新日期
                    current_date = record['date']
                    if latest_date is None or current_date > latest_date:
                        latest_date = current_date
                    
                    # 计算总价 = 面积 × 单价
                    total_price = record['area'] * record['price']
                    monthly_data[(year, month)][day]['total_price'] += total_price
                    monthly_data[(year, month)][day]['total_area'] += record['area']
                    monthly_data[(year, month)][day]['count'] += 1
        else:
            print(f"警告: 文件 {filename} 不存在，跳过处理")
    
    return monthly_data, latest_date

def calculate_4month_avg_index(monthly_stats, base_avg_price, target_year, target_month):
    """计算指定月份的4个月移动平均价格指数"""
    indices = []
    
    # 收集目标月份前3个月到目标月份的数据（共4个月）
    for i in range(3, -1, -1):  # 3, 2, 1, 0
        year = target_year
        month = target_month - i
        
        # 处理跨年情况
        while month <= 0:
            month += 12
            year -= 1
        
        key = (year, month)
        if key in monthly_stats:
            index = (monthly_stats[key]['avg_price'] / base_avg_price) * 100
            indices.append(index)
    
    # 必须有完整的4个月数据才计算移动平均值
    if len(indices) == 4:
        return sum(indices) / len(indices)
    else:
        return None

def calculate_price_index(monthly_data, base_year=2016, base_month=1):
    """计算价格指数，以指定年月为基数100"""
    # 计算每月统计数据
    monthly_stats = {}
    
    for (year, month), daily_data in monthly_data.items():

            
        # 计算有效天数
        valid_days = len([day for day, data in daily_data.items() if data['count'] > 0])
        
        if valid_days > 0:
            # 汇总当月所有数据
            month_total_price = 0
            month_total_area = 0
            month_total_records = 0
            
            for day_data in daily_data.values():
                month_total_price += day_data['total_price']
                month_total_area += day_data['total_area']
                month_total_records += day_data['count']
            
            if month_total_area > 0:
                # 计算月平均单价 = 总价 / 总面积
                avg_price = month_total_price / month_total_area
                monthly_stats[(year, month)] = {
                    'total_price': month_total_price,
                    'total_area': month_total_area,
                    'avg_price': avg_price,
                    'valid_days': valid_days,
                    'total_records': month_total_records
                }
    
    # 获取基准月份的平均价格
    base_stats = monthly_stats.get((base_year, base_month))
    if not base_stats:
        print(f"警告: 未找到基准月份 {base_year}年{base_month}月 的数据")
        return {}
    
    base_avg_price = base_stats['avg_price']
    print(f"基准月份 {base_year}年{base_month}月 平均单价: {base_avg_price:.2f} 元/平米")
    print(f"基准月份总价: {base_stats['total_price']:,.0f} 元, 总面积: {base_stats['total_area']:,.0f} 平米")
    
    # 计算价格指数
    price_index = {}
    for (year, month), stats in monthly_stats.items():
        index = (stats['avg_price'] / base_avg_price) * 100
        
        # 计算4个月移动平均的同比涨跌幅
        yoy_change = None
        
        # 计算当前月份的4个月移动平均价格指数
        current_4m_avg = calculate_4month_avg_index(monthly_stats, base_avg_price, year, month)
        
        # 计算去年同月的4个月移动平均价格指数
        prev_year_4m_avg = calculate_4month_avg_index(monthly_stats, base_avg_price, year - 1, month)
        
        if current_4m_avg is not None and prev_year_4m_avg is not None:
            yoy_change = round(((current_4m_avg - prev_year_4m_avg) / prev_year_4m_avg) * 100, 2)
        
        price_index[f"{year}-{month:02d}"] = {
            'year': year,
            'month': month,
            'price_index': round(index, 2),
            'yoy_change': yoy_change,
            'total_price': round(stats['total_price'], 2),
            'total_area': round(stats['total_area'], 2),
            'avg_price': round(stats['avg_price'], 2),
            'valid_days': stats['valid_days'],
            'total_records': stats['total_records']
        }
    
    return price_index

def main():
    """主函数"""
    data_files_dir = 'data_files'
    output_file = 'shanghai_house_price_index.json'
    
    print("开始计算上海房价指数...")
    print(f"数据目录: {data_files_dir}")
    print("基准: 2016年1月 = 100")
    print("条件: 包含所有有效数据的月份\n")
    
    # 计算月度统计数据
    monthly_data, latest_date = calculate_monthly_stats(data_files_dir)
    print(f"\n共处理 {len(monthly_data)} 个月份的数据")
    print(f"最新数据日期: {latest_date}" if latest_date else "未找到有效数据日期")
    
    # 计算价格指数
    price_index = calculate_price_index(monthly_data, base_year=2016, base_month=1)
    
    if price_index:
        # 按时间排序
        sorted_index = dict(sorted(price_index.items(), key=lambda x: (x[1]['year'], x[1]['month'])))
        
        # 输出到JSON文件
        output_data = {
            'latest_data_date': latest_date,
            'base_period': '2016-01',
            'base_index': 100,
            'description': '上海房价指数 (以2016年1月为基数100)',
            'data': sorted_index
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n价格指数已保存到: {output_file}")
        print(f"共计算出 {len(price_index)} 个月份的价格指数")
        
        # 自动备份JSON文件到outsource文件夹
        backup_dir = r'C:\Users\17701\github\my_first_repo\stock_info\cache\outsource'
        backup_file = os.path.join(backup_dir, output_file)
        try:
            # 确保备份目录存在
            os.makedirs(backup_dir, exist_ok=True)
            # 复制文件
            shutil.copy2(output_file, backup_file)
            print(f"JSON文件已自动备份到: {backup_file}")
        except Exception as e:
            print(f"备份文件时出错: {e}")
        
        # 显示部分结果
        print("\n部分结果预览:")
        for i, (period, data) in enumerate(sorted_index.items()):
            if i < 10:  # 只显示前10个
                print(f"{period}: 指数 {data['price_index']}, 平均单价 {data['avg_price']} 元/平米, 有效天数 {data['valid_days']}")
            elif i == 10:
                print("...")
                break
    else:
        print("未能计算出价格指数，请检查数据")



if __name__ == '__main__':
    main()