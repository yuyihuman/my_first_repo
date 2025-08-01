"""
宏观经济数据模块 - 提供宏观经济数据相关的获取函数
"""
import os
import json
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from .cache_utils import CACHE_DIR

def fetch_macro_china_money_supply():
    """
    获取中国货币供应量数据（仅2000年以后的数据）
    
    Returns:
        dict: 包含货币供应量数据的字典，包括M2/M1/M0总量和增速，以及房价同比和环比数据
    """
    try:
        # 检查缓存
        cache_dir = os.path.join(CACHE_DIR, 'macro')
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, 'money_supply.json')
        
        # 检查缓存是否存在且在24小时内
        if os.path.exists(cache_file):
            file_time = os.path.getmtime(cache_file)
            current_time = datetime.now().timestamp()
            # 如果缓存文件在24小时内，直接返回缓存数据
            if current_time - file_time < 24 * 60 * 60:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        # 获取货币供应量数据（增速）
        money_supply_df = ak.macro_china_supply_of_money()
        
        # 获取货币供应量总量数据
        money_supply_total_df = ak.macro_china_money_supply()
        
        # 根据实际列名确定日期列和数据列
        # 尝试可能的日期列名
        date_col = None
        for possible_date_col in ['统计时间', '月份', '日期']:
            if possible_date_col in money_supply_df.columns:
                date_col = possible_date_col
                break
        
        if date_col is None:
            # 如果找不到预期的日期列，使用第一列作为日期列
            date_col = money_supply_df.columns[0]
        
        # 尝试可能的增长率列名
        m2_growth_col = None
        m1_growth_col = None
        m0_growth_col = None
        
        for col in money_supply_df.columns:
            if 'M2' in col and '同比' in col:
                m2_growth_col = col
            elif 'M1' in col and '同比' in col:
                m1_growth_col = col
            elif 'M0' in col and '同比' in col:
                m0_growth_col = col
        
        # 如果找不到特定的列，尝试使用可能的替代列
        if m2_growth_col is None:
            for col in money_supply_df.columns:
                if 'M2' in col or ('货币' in col and '广义' in col and '同比' in col):
                    m2_growth_col = col
                    break
        
        if m1_growth_col is None:
            for col in money_supply_df.columns:
                if 'M1' in col or ('货币' in col and '狭义' in col and '同比' in col):
                    m1_growth_col = col
                    break
        
        if m0_growth_col is None:
            for col in money_supply_df.columns:
                if 'M0' in col or ('流通中现金' in col and '同比' in col):
                    m0_growth_col = col
                    break
        
        # 创建货币总量的映射字典
        money_total_dict = {}
        
        # 确定货币总量数据的列名
        total_date_col = None
        for possible_date_col in ['统计时间', '月份', '日期']:
            if possible_date_col in money_supply_total_df.columns:
                total_date_col = possible_date_col
                break
        
        if total_date_col is None:
            # 如果找不到预期的日期列，使用第一列作为日期列
            total_date_col = money_supply_total_df.columns[0]
        
        # 确定总量数据的列名
        m2_total_col = '货币和准货币(M2)-数量(亿元)'
        m1_total_col = '货币(M1)-数量(亿元)'
        m0_total_col = '流通中的现金(M0)-数量(亿元)'
        
        # 处理货币总量数据，并准备计算环比数据
        # 首先将数据按日期排序
        money_supply_total_df['sort_date'] = money_supply_total_df[total_date_col].astype(str)
        money_supply_total_df = money_supply_total_df.sort_values(by='sort_date')
        
        # 创建一个列表来存储处理后的总量数据，以便计算环比
        processed_total_data = []
        
        for _, row in money_supply_total_df.iterrows():
            try:
                date_str = str(row[total_date_col])
                
                # 将"2025年03月份"格式转换为"2025.3"格式
                # 提取年份和月份
                import re
                match = re.search(r'(\d{4})年(\d{2})月', date_str)
                if match:
                    year = match.group(1)
                    month = match.group(2).lstrip('0')  # 去掉前导零
                    formatted_date = f"{year}.{month}"
                else:
                    # 如果无法匹配，保持原样
                    formatted_date = date_str
                
                # 使用正确的列名获取总量数据
                m2_total = None
                m1_total = None
                m0_total = None
                
                # 检查列是否存在并获取数据
                if m2_total_col in money_supply_total_df.columns:
                    m2_total = row[m2_total_col]
                    if pd.isna(m2_total):
                        m2_total = None
                    else:
                        try:
                            m2_total = float(m2_total)
                            m2_total = round(m2_total, 2)
                        except (ValueError, TypeError):
                            m2_total = None
                
                if m1_total_col in money_supply_total_df.columns:
                    m1_total = row[m1_total_col]
                    if pd.isna(m1_total):
                        m1_total = None
                    else:
                        try:
                            m1_total = float(m1_total)
                            m1_total = round(m1_total, 2)
                        except (ValueError, TypeError):
                            m1_total = None
                
                if m0_total_col in money_supply_total_df.columns:
                    m0_total = row[m0_total_col]
                    if pd.isna(m0_total):
                        m0_total = None
                    else:
                        try:
                            m0_total = float(m0_total)
                            m0_total = round(m0_total, 2)
                        except (ValueError, TypeError):
                            m0_total = None
                
                # 将处理后的数据添加到列表中
                processed_total_data.append({
                    'date': formatted_date,
                    'M2总量(亿元)': m2_total,
                    'M1总量(亿元)': m1_total,
                    'M0总量(亿元)': m0_total
                })
                
            except Exception as e:
                print(f"处理货币总量数据行时出错: {e}")
                continue
        
        # 计算环比数据
        for i in range(1, len(processed_total_data)):
            current = processed_total_data[i]
            previous = processed_total_data[i-1]
            
            # 计算M2环比
            if current['M2总量(亿元)'] is not None and previous['M2总量(亿元)'] is not None and previous['M2总量(亿元)'] != 0:
                m2_mom = ((current['M2总量(亿元)'] - previous['M2总量(亿元)']) / previous['M2总量(亿元)']) * 100
                current['M2总量环比(%)'] = round(m2_mom, 2)
            else:
                current['M2总量环比(%)'] = None
            
            # 计算M1环比
            # 特殊处理2024年1月的M1环比值
            current_date = current.get('date', '')
            if current_date == '2024.1':
                # 2024年1月M1计算方法变更，将环比值设为0
                current['M1总量环比(%)'] = 0
            elif current['M1总量(亿元)'] is not None and previous['M1总量(亿元)'] is not None and previous['M1总量(亿元)'] != 0:
                m1_mom = ((current['M1总量(亿元)'] - previous['M1总量(亿元)']) / previous['M1总量(亿元)']) * 100
                current['M1总量环比(%)'] = round(m1_mom, 2)
            else:
                current['M1总量环比(%)'] = None
            
            # 计算M0环比
            if current['M0总量(亿元)'] is not None and previous['M0总量(亿元)'] is not None and previous['M0总量(亿元)'] != 0:
                m0_mom = ((current['M0总量(亿元)'] - previous['M0总量(亿元)']) / previous['M0总量(亿元)']) * 100
                current['M0总量环比(%)'] = round(m0_mom, 2)
            else:
                current['M0总量环比(%)'] = None
        
        # 第一个数据点没有前值，所以环比为None
        if processed_total_data:
            processed_total_data[0]['M2总量环比(%)'] = None
            processed_total_data[0]['M1总量环比(%)'] = None
            processed_total_data[0]['M0总量环比(%)'] = None
        
        # 将处理后的数据转换为字典，以日期为键
        for item in processed_total_data:
            date = item.pop('date')
            money_total_dict[date] = item
        
        # 新增：计算从2011年1月开始的指数值
        # 首先找到2011年1月的数据作为基准点
        base_date = "2011.1"
        base_data = None
        
        # 创建一个按日期排序的数据列表，用于计算指数
        sorted_dates = []
        for date_str in money_total_dict.keys():
            try:
                # 解析日期格式为年和月
                if '.' in date_str:
                    year, month = date_str.split('.')
                    year = int(year)
                    month = int(month)
                    # 创建一个可排序的日期字符串 (YYYYMM格式)
                    sort_key = f"{year:04d}{month:02d}"
                    sorted_dates.append((sort_key, date_str))
            except Exception as e:
                print(f"解析日期 {date_str} 出错: {e}")
                continue
        
        # 按日期排序
        sorted_dates.sort()
        sorted_date_strings = [date_tuple[1] for date_tuple in sorted_dates]
        
        # 查找基准日期
        if base_date in money_total_dict:
            base_data = money_total_dict[base_date]
        else:
            # 如果找不到精确的2011.1，尝试找最接近的日期
            for date_str in sorted_date_strings:
                if '.' in date_str:
                    year, month = date_str.split('.')
                    if int(year) == 2011 and int(month) == 1:
                        base_date = date_str
                        base_data = money_total_dict[date_str]
                        break
        
        # 如果找到了基准日期，计算指数
        if base_data:
            # 获取基准值
            base_m2 = base_data.get('M2总量(亿元)')
            base_m1 = base_data.get('M1总量(亿元)')
            base_m0 = base_data.get('M0总量(亿元)')
            
            # 为每个日期计算指数值
            for date_str in sorted_date_strings:
                if date_str in money_total_dict:
                    current_data = money_total_dict[date_str]
                    
                    # 计算M2指数
                    if base_m2 is not None and current_data.get('M2总量(亿元)') is not None:
                        m2_index = (current_data['M2总量(亿元)'] / base_m2) * 100
                        current_data['M2指数(2011.1=100)'] = round(m2_index, 2)
                    else:
                        current_data['M2指数(2011.1=100)'] = None
                    
                    # 特殊处理M1指数
                    if date_str == '2023.12' and base_m1 is not None and current_data.get('M1总量(亿元)') is not None:
                        # 记录2023年12月的M1指数值
                        m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                        dec_2023_m1_index = round(m1_index, 2)
                        current_data['M1指数(2011.1=100)'] = dec_2023_m1_index
                    elif date_str == '2024.1':
                        # 2024年1月的M1指数与2023年12月保持一致
                        if dec_2023_m1_index is not None:
                            current_data['M1指数(2011.1=100)'] = dec_2023_m1_index
                        else:
                            # 如果没有找到2023年12月的数据，仍然使用常规计算方法
                            if base_m1 is not None and current_data.get('M1总量(亿元)') is not None:
                                m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                                current_data['M1指数(2011.1=100)'] = round(m1_index, 2)
                            else:
                                current_data['M1指数(2011.1=100)'] = None
                    elif date_str > '2024.1' and base_m1 is not None:
                        # 2024年1月之后的月份，基于2024年1月的指数值和总量变化计算
                        # 查找2024年1月的数据
                        jan_2024_data = None
                        for d in sorted_date_strings:
                            if d == '2024.1' and d in money_total_dict:
                                jan_2024_data = money_total_dict[d]
                                break
                        
                        if jan_2024_data and 'M1指数(2011.1=100)' in jan_2024_data and jan_2024_data['M1指数(2011.1=100)'] is not None and jan_2024_data.get('M1总量(亿元)') is not None and current_data.get('M1总量(亿元)') is not None:
                            # 基于2024年1月的指数和总量变化计算
                            m1_index = jan_2024_data['M1指数(2011.1=100)'] * (current_data['M1总量(亿元)'] / jan_2024_data['M1总量(亿元)'])
                            current_data['M1指数(2011.1=100)'] = round(m1_index, 2)
                        else:
                            # 如果没有找到2024年1月的数据，使用常规计算方法
                            if current_data.get('M1总量(亿元)') is not None:
                                m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                                current_data['M1指数(2011.1=100)'] = round(m1_index, 2)
                            else:
                                current_data['M1指数(2011.1=100)'] = None
                    else:
                        # 2024年1月之前的月份，使用常规计算方法
                        if base_m1 is not None and current_data.get('M1总量(亿元)') is not None:
                            m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                            current_data['M1指数(2011.1=100)'] = round(m1_index, 2)
                        else:
                            current_data['M1指数(2011.1=100)'] = None
                    
                    # 计算M0指数
                    if base_m0 is not None and current_data.get('M0总量(亿元)') is not None:
                        m0_index = (current_data['M0总量(亿元)'] / base_m0) * 100
                        current_data['M0指数(2011.1=100)'] = round(m0_index, 2)
                    else:
                        current_data['M0指数(2011.1=100)'] = None
        
        
        # 获取沪深300指数数据
        hs300_dict = {}
        try:
            # 获取沪深300指数历史数据
            hs300_df = ak.stock_zh_index_daily(symbol="sh000300")
            
            # 确保日期列是字符串类型
            hs300_df['date'] = hs300_df['date'].astype(str)
            
            # 按日期排序
            hs300_df = hs300_df.sort_values(by='date')
            
            # 处理沪深300数据，按月份聚合（取每月最后一个交易日的收盘价）
            hs300_monthly = {}
            hs300_monthly_dot = {}
            
            # 按月份分组，保留每月最后一个交易日的数据
            for _, row in hs300_df.iterrows():
                date_str = row['date']
                close_price = float(row['close'])
                
                # 提取年月
                if len(date_str) >= 7:  # 格式如 "2023-01-01"
                    year_month = date_str[:7]  # "2023-01"
                    year, month = year_month.split('-')
                    month = month.lstrip('0')  # 去掉前导零
                    year_month_dot = f"{year}.{month}"  # "2023.1"
                    
                    # 由于数据是按日期排序的，后面的日期会覆盖前面的，这样就能得到每月最后一个交易日的数据
                    hs300_monthly[year_month] = close_price
                    hs300_monthly_dot[year_month_dot] = close_price
            
            # 合并两个字典
            hs300_monthly.update(hs300_monthly_dot)
            
            # 计算沪深300指数的同比增长率
            sorted_months = sorted(hs300_monthly.keys())
            for month_key in sorted_months:
                if '.' in month_key:  # 只处理点格式的键
                    year, month = month_key.split('.')
                    current_year = int(year)
                    current_month = int(month)
                    
                    # 计算去年同期的键
                    prev_year = current_year - 1
                    prev_month_key = f"{prev_year}.{month}"
                    
                    if prev_month_key in hs300_monthly:
                        current_price = hs300_monthly[month_key]
                        prev_price = hs300_monthly[prev_month_key]
                        
                        if prev_price != 0:
                            yoy_growth = ((current_price - prev_price) / prev_price) * 100
                            hs300_dict[month_key] = {
                                '沪深300指数': current_price,
                                '沪深300指数_同比': round(yoy_growth, 2)
                            }
                        else:
                            hs300_dict[month_key] = {
                                '沪深300指数': current_price,
                                '沪深300指数_同比': None
                            }
                    else:
                        hs300_dict[month_key] = {
                            '沪深300指数': hs300_monthly[month_key],
                            '沪深300指数_同比': None
                        }
        
        except Exception as e:
            print(f"获取沪深300指数数据失败: {e}")
            hs300_dict = {}
        
        # 获取中证商品期货指数数据
        ccidx_dict = get_ccidx_futures_index()
        
        # 获取滚动4Q净利润和TTM市盈率数据
        rolling_4q_dict = get_rolling_4q_profit_data()
        print(f"DEBUG: 滚动4Q净利润和TTM市盈率数据获取成功，共{len(rolling_4q_dict)}条记录")
        
        # 获取上海新房价格数据
        house_price_dict = {}  # 初始化为空字典
        try:
            # 获取上海房价数据
            house_price_df = ak.macro_china_new_house_price(city_first="上海")
            
            # 确保日期列是字符串类型
            house_price_df['日期'] = house_price_df['日期'].astype(str)
            
            # 创建日期到房价数据的映射
            house_price_dict = {}
            
            # 按日期排序，用于计算环比数据
            house_price_df = house_price_df.sort_values(by='日期')
            
            for _, row in house_price_df.iterrows():
                date_str = row['日期']
                
                # 转换日期格式为 YYYY-MM 或 YYYY.MM
                if '-' in date_str:
                    # 如果日期格式为 "2023-01-01"，转换为 "2023-01"
                    year_month = '-'.join(date_str.split('-')[:2])
                    # 也创建 YYYY.MM 格式的键
                    year, month = year_month.split('-')
                    month = month.lstrip('0')  # 去掉前导零
                    year_month_dot = f"{year}.{month}"
                else:
                    # 处理其他可能的格式
                    year_month = date_str
                    year_month_dot = date_str
                
                # 获取房价指数并转换为同比增长率（即减去100）：
                new_house_price_yoy = float(row['新建商品住宅价格指数-同比']) if '新建商品住宅价格指数-同比' in row and not pd.isna(row['新建商品住宅价格指数-同比']) else None
                second_house_price_yoy = float(row['二手住宅价格指数-同比']) if '二手住宅价格指数-同比' in row and not pd.isna(row['二手住宅价格指数-同比']) else None
                
                # 获取环比数据
                new_house_price_mom = float(row['新建商品住宅价格指数-环比']) if '新建商品住宅价格指数-环比' in row and not pd.isna(row['新建商品住宅价格指数-环比']) else None
                second_house_price_mom = float(row['二手住宅价格指数-环比']) if '二手住宅价格指数-环比' in row and not pd.isna(row['二手住宅价格指数-环比']) else None
                
                # 将指数转换为增长率（减去100）
                if new_house_price_yoy is not None:
                    new_house_price_yoy = round(new_house_price_yoy - 100, 2)
                if second_house_price_yoy is not None:
                    second_house_price_yoy = round(second_house_price_yoy - 100, 2)
                
                # 环比数据也需要减去100，转换为与同比相同的格式
                if new_house_price_mom is not None:
                    new_house_price_mom = round(new_house_price_mom - 100, 2)
                if second_house_price_mom is not None:
                    second_house_price_mom = round(second_house_price_mom - 100, 2)
                
                # 使用两种格式的日期作为键，确保能匹配到货币供应量数据
                house_data = {
                    '新建商品住宅价格指数_同比': new_house_price_yoy,
                    '二手住宅价格指数_同比': second_house_price_yoy,
                    '新建商品住宅价格指数_环比': new_house_price_mom,
                    '二手住宅价格指数_环比': second_house_price_mom
                }
                
                house_price_dict[year_month] = house_data
                house_price_dict[year_month_dot] = house_data
        
        except Exception as e:
            print(f"获取上海房价数据失败: {e}")
            house_price_dict = {}

        # 新增：计算上海住宅价格指数
        # 找到基准日期（2011.1）的房价数据
        base_house_price_data = None
        for date_str in sorted_date_strings:
            if date_str in house_price_dict and '.' in date_str:
                year, month = date_str.split('.')
                if int(year) == 2011 and int(month) == 1:
                    base_date_house = date_str
                    base_house_price_data = house_price_dict[date_str]
                    break
        
        # 如果找不到2011.1的数据，使用最早的数据作为基准
        if base_house_price_data is None and house_price_dict:
            earliest_date = sorted_date_strings[0]
            for date_str in sorted_date_strings:
                if date_str in house_price_dict:
                    earliest_date = date_str
                    base_house_price_data = house_price_dict[date_str]
                    break
            print(f"未找到2011.1的房价数据，使用{earliest_date}作为基准")
        
        # 如果找到了基准日期的房价数据，计算指数
        if base_house_price_data:
            # 初始化基准指数值为100
            new_house_index_base = 100.0
            second_house_index_base = 100.0
            
            # 为每个日期计算房价指数
            for date_str in sorted_date_strings:
                if date_str in house_price_dict:
                    # 计算从基准日期到当前日期的累积变化
                    new_house_index = new_house_index_base
                    second_house_index = second_house_index_base
                    
                    # 使用环比数据累积计算
                    for i, curr_date in enumerate(sorted_date_strings):
                        if curr_date == date_str:
                            break
                        
                        if curr_date in house_price_dict:
                            mom_new = house_price_dict[curr_date].get('新建商品住宅价格指数_环比')
                            mom_second = house_price_dict[curr_date].get('二手住宅价格指数_环比')
                            
                            if mom_new is not None:
                                new_house_index *= (1 + mom_new / 100)
                            
                            if mom_second is not None:
                                second_house_index *= (1 + mom_second / 100)
                    
                    # 保存计算结果
                    house_price_dict[date_str]['新建商品住宅价格指数(2011.1=100)'] = round(new_house_index, 2)
                    house_price_dict[date_str]['二手住宅价格指数(2011.1=100)'] = round(second_house_index, 2)

        # 确保数据框不为空
        if money_supply_df.empty:
            return {
                'status': 'error',
                'message': '获取的数据为空'
            }
        
        # 转换为字典列表
        data = []
        
        # 修改排序逻辑：先将日期转换为可比较的格式再排序
        def convert_date_for_sorting(date_str):
            # 处理格式如 "2023.9" 或 "2023-09"
            if '.' in date_str:
                year, month = date_str.split('.')
                # 确保月份是两位数
                month = month.zfill(2)
                return f"{year}{month}"
            elif '-' in date_str:
                year, month = date_str.split('-')[:2]
                return f"{year}{month}"
            return date_str
        
        # 创建一个临时列用于排序
        money_supply_df['sort_date'] = money_supply_df[date_col].astype(str).apply(convert_date_for_sorting)
        # 按日期排序（从新到旧）
        money_supply_df = money_supply_df.sort_values(by='sort_date', ascending=False)
        
        # 获取所有历史数据，但只保留2000年以后的
        processed_rows = 0
        matched_with_total = 0
        
        for _, row in money_supply_df.iterrows():
            try:
                date_str = str(row[date_col])
                
                # 处理日期格式
                if '-' in date_str:
                    # 如果日期格式为 "2023-01"，保持原样
                    formatted_date = date_str
                    # 提取年份
                    year = int(formatted_date.split('-')[0])
                else:
                    # 处理格式如 "2023.01" 或 "2023.1"
                    formatted_date = date_str
                    # 提取年份
                    year = int(formatted_date.split('.')[0])
                
                # 只保留2000年以后的数据
                if year < 2000:
                    continue
                
                # 处理NaN值，将其转换为None，并保留两位小数
                m2_growth = None
                m1_growth = None
                m0_growth = None
                
                if m2_growth_col and m2_growth_col in row.index:
                    m2_growth = float(row[m2_growth_col]) if not pd.isna(row[m2_growth_col]) else None
                
                if m1_growth_col and m1_growth_col in row.index:
                    m1_growth = float(row[m1_growth_col]) if not pd.isna(row[m1_growth_col]) else None
                
                if m0_growth_col and m0_growth_col in row.index:
                    m0_growth = float(row[m0_growth_col]) if not pd.isna(row[m0_growth_col]) else None
                
                # 保留两位小数
                if m2_growth is not None:
                    m2_growth = round(m2_growth, 2)
                if m1_growth is not None:
                    m1_growth = round(m1_growth, 2)
                if m0_growth is not None:
                    m0_growth = round(m0_growth, 2)
                
                # 创建基本数据项
                item = {
                    '月份': formatted_date,
                    '货币和准货币_广义货币M2_同比': m2_growth,
                    '货币_狭义货币M1_同比': m1_growth,
                    '流通中现金_M0_同比': m0_growth
                }
                
                # 添加货币总量数据和环比数据（如果存在）
                if formatted_date in money_total_dict:
                    item['M2总量(亿元)'] = money_total_dict[formatted_date]['M2总量(亿元)']
                    item['M1总量(亿元)'] = money_total_dict[formatted_date]['M1总量(亿元)']
                    item['M0总量(亿元)'] = money_total_dict[formatted_date]['M0总量(亿元)']
                    # 添加环比数据
                    item['M2总量环比(%)'] = money_total_dict[formatted_date].get('M2总量环比(%)')
                    item['M1总量环比(%)'] = money_total_dict[formatted_date].get('M1总量环比(%)')
                    item['M0总量环比(%)'] = money_total_dict[formatted_date].get('M0总量环比(%)')
                    # 添加指数数据
                    item['M2指数(2011.1=100)'] = money_total_dict[formatted_date].get('M2指数(2011.1=100)')
                    item['M1指数(2011.1=100)'] = money_total_dict[formatted_date].get('M1指数(2011.1=100)')
                    item['M0指数(2011.1=100)'] = money_total_dict[formatted_date].get('M0指数(2011.1=100)')
                    matched_with_total += 1
                else:
                    # 尝试其他可能的日期格式
                    found = False
                    for key in money_total_dict.keys():
                        # 检查年份和月份是否匹配
                        if '.' in formatted_date and '.' in key:
                            if formatted_date.split('.')[0] == key.split('.')[0] and formatted_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                item['M2总量(亿元)'] = money_total_dict[key]['M2总量(亿元)']
                                item['M1总量(亿元)'] = money_total_dict[key]['M1总量(亿元)']
                                item['M0总量(亿元)'] = money_total_dict[key]['M0总量(亿元)']
                                # 添加环比数据
                                item['M2总量环比(%)'] = money_total_dict[key].get('M2总量环比(%)')
                                item['M1总量环比(%)'] = money_total_dict[key].get('M1总量环比(%)')
                                item['M0总量环比(%)'] = money_total_dict[key].get('M0总量环比(%)')
                                # 添加指数数据
                                item['M2指数(2011.1=100)'] = money_total_dict[key].get('M2指数(2011.1=100)')
                                item['M1指数(2011.1=100)'] = money_total_dict[key].get('M1指数(2011.1=100)')
                                item['M0指数(2011.1=100)'] = money_total_dict[key].get('M0指数(2011.1=100)')
                                found = True
                                matched_with_total += 1
                                break
                    
                    if not found:
                        item['M2总量(亿元)'] = None
                        item['M1总量(亿元)'] = None
                        item['M0总量(亿元)'] = None
                        item['M2总量环比(%)'] = None
                        item['M1总量环比(%)'] = None
                        item['M0总量环比(%)'] = None
                        item['M2指数(2011.1=100)'] = None
                        item['M1指数(2011.1=100)'] = None
                        item['M0指数(2011.1=100)'] = None
                
                # 添加沪深300指数数据（如果存在）
                if formatted_date in hs300_dict:
                    item['沪深300指数'] = hs300_dict[formatted_date]['沪深300指数']
                    item['沪深300指数_同比'] = hs300_dict[formatted_date]['沪深300指数_同比']
                else:
                    # 尝试其他可能的日期格式
                    found = False
                    for key in hs300_dict.keys():
                        # 检查年份和月份是否匹配
                        if '.' in formatted_date and '.' in key:
                            if formatted_date.split('.')[0] == key.split('.')[0] and formatted_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                item['沪深300指数'] = hs300_dict[key]['沪深300指数']
                                item['沪深300指数_同比'] = hs300_dict[key]['沪深300指数_同比']
                                found = True
                                break
                    
                    if not found:
                        item['沪深300指数'] = None
                        item['沪深300指数_同比'] = None
                
                # 添加中证商品期货价格指数数据（如果存在）
                if formatted_date in ccidx_dict:
                    item['中证商品期货价格指数'] = ccidx_dict[formatted_date]['中证商品期货价格指数']
                else:
                    # 尝试其他可能的日期格式
                    found = False
                    for key in ccidx_dict.keys():
                        # 检查年份和月份是否匹配
                        if '.' in formatted_date and '.' in key:
                            if formatted_date.split('.')[0] == key.split('.')[0] and formatted_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                item['中证商品期货价格指数'] = ccidx_dict[key]['中证商品期货价格指数']
                                found = True
                                break
                    
                    if not found:
                        item['中证商品期货价格指数'] = None
                
                # 添加滚动4Q净利润和TTM市盈率数据（如果存在）
                if formatted_date in rolling_4q_dict:
                    item['TTM市盈率'] = rolling_4q_dict[formatted_date]['TTM市盈率']
                    item['滚动4Q净利润'] = rolling_4q_dict[formatted_date]['滚动4Q净利润']
                    item['银行滚动4Q净利润'] = rolling_4q_dict[formatted_date]['银行滚动4Q净利润']
                    item['非银行滚动4Q净利润'] = rolling_4q_dict[formatted_date]['非银行滚动4Q净利润']
                    item['银行TTM市盈率'] = rolling_4q_dict[formatted_date]['银行TTM市盈率']
                    item['非银行TTM市盈率'] = rolling_4q_dict[formatted_date]['非银行TTM市盈率']
                    print(f"DEBUG: 直接匹配成功 {formatted_date} -> TTM: {item['TTM市盈率']}, 4Q净利润: {item['滚动4Q净利润']}, 银行4Q: {item['银行滚动4Q净利润']}, 非银行4Q: {item['非银行滚动4Q净利润']}, 银行TTM: {item['银行TTM市盈率']}, 非银行TTM: {item['非银行TTM市盈率']}")
                else:
                    # 尝试其他可能的日期格式
                    found = False
                    for key in rolling_4q_dict.keys():
                        # 检查年份和月份是否匹配
                        if '.' in formatted_date and '.' in key:
                            if formatted_date.split('.')[0] == key.split('.')[0] and formatted_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                item['TTM市盈率'] = rolling_4q_dict[key]['TTM市盈率']
                                item['滚动4Q净利润'] = rolling_4q_dict[key]['滚动4Q净利润']
                                item['银行滚动4Q净利润'] = rolling_4q_dict[key]['银行滚动4Q净利润']
                                item['非银行滚动4Q净利润'] = rolling_4q_dict[key]['非银行滚动4Q净利润']
                                item['银行TTM市盈率'] = rolling_4q_dict[key]['银行TTM市盈率']
                                item['非银行TTM市盈率'] = rolling_4q_dict[key]['非银行TTM市盈率']
                                print(f"DEBUG: 格式匹配成功 {formatted_date} -> {key} -> TTM: {item['TTM市盈率']}, 4Q净利润: {item['滚动4Q净利润']}, 银行4Q: {item['银行滚动4Q净利润']}, 非银行4Q: {item['非银行滚动4Q净利润']}, 银行TTM: {item['银行TTM市盈率']}, 非银行TTM: {item['非银行TTM市盈率']}")
                                found = True
                                break
                    
                    if not found:
                        item['TTM市盈率'] = None
                        item['滚动4Q净利润'] = None
                        item['银行滚动4Q净利润'] = None
                        item['非银行滚动4Q净利润'] = None
                        item['银行TTM市盈率'] = None
                        item['非银行TTM市盈率'] = None
                        if len(rolling_4q_dict) > 0:  # 只在前几条记录中打印调试信息
                            print(f"DEBUG: 未找到匹配 {formatted_date}，滚动4Q数据键示例: {list(rolling_4q_dict.keys())[:3]}")
                
                # 添加房价数据（如果存在）
                if formatted_date in house_price_dict:
                    item['上海新建商品住宅价格指数_同比'] = house_price_dict[formatted_date]['新建商品住宅价格指数_同比']
                    item['上海二手住宅价格指数_同比'] = house_price_dict[formatted_date]['二手住宅价格指数_同比']
                    item['上海新建商品住宅价格指数_环比'] = house_price_dict[formatted_date]['新建商品住宅价格指数_环比']
                    item['上海二手住宅价格指数_环比'] = house_price_dict[formatted_date]['二手住宅价格指数_环比']
                    item['上海新建商品住宅价格指数(2011.1=100)'] = house_price_dict[formatted_date].get('新建商品住宅价格指数(2011.1=100)')
                    item['上海二手住宅价格指数(2011.1=100)'] = house_price_dict[formatted_date].get('二手住宅价格指数(2011.1=100)')
                else:
                    # 尝试其他可能的日期格式
                    found = False
                    for key in house_price_dict.keys():
                        # 检查年份和月份是否匹配
                        if '-' in formatted_date and '-' in key:
                            if formatted_date.split('-')[0] == key.split('-')[0] and formatted_date.split('-')[1] == key.split('-')[1]:
                                item['上海新建商品住宅价格指数_同比'] = house_price_dict[key]['新建商品住宅价格指数_同比']
                                item['上海二手住宅价格指数_同比'] = house_price_dict[key]['二手住宅价格指数_同比']
                                item['上海新建商品住宅价格指数_环比'] = house_price_dict[key]['新建商品住宅价格指数_环比']
                                item['上海二手住宅价格指数_环比'] = house_price_dict[key]['二手住宅价格指数_环比']
                                item['上海新建商品住宅价格指数(2011.1=100)'] = house_price_dict[key].get('新建商品住宅价格指数(2011.1=100)')
                                item['上海二手住宅价格指数(2011.1=100)'] = house_price_dict[key].get('二手住宅价格指数(2011.1=100)')
                                found = True
                                break
                        elif '.' in formatted_date and '.' in key:
                            if formatted_date.split('.')[0] == key.split('.')[0] and formatted_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                item['上海新建商品住宅价格指数_同比'] = house_price_dict[key]['新建商品住宅价格指数_同比']
                                item['上海二手住宅价格指数_同比'] = house_price_dict[key]['二手住宅价格指数_同比']
                                item['上海新建商品住宅价格指数_环比'] = house_price_dict[key]['新建商品住宅价格指数_环比']
                                item['上海二手住宅价格指数_环比'] = house_price_dict[key]['二手住宅价格指数_环比']
                                item['上海新建商品住宅价格指数(2011.1=100)'] = house_price_dict[key].get('新建商品住宅价格指数(2011.1=100)')
                                item['上海二手住宅价格指数(2011.1=100)'] = house_price_dict[key].get('二手住宅价格指数(2011.1=100)')
                                found = True
                                break
                    
                    if not found:
                        item['上海新建商品住宅价格指数_同比'] = None
                        item['上海二手住宅价格指数_同比'] = None
                        item['上海新建商品住宅价格指数_环比'] = None
                        item['上海二手住宅价格指数_环比'] = None
                        item['上海新建商品住宅价格指数(2011.1=100)'] = None
                        item['上海二手住宅价格指数(2011.1=100)'] = None
                
                data.append(item)
                processed_rows += 1
                
            except (ValueError, TypeError, KeyError) as e:
                print(f"处理行数据时出错: {e}")
                continue
        
        print(f"成功获取并缓存货币供应量、总量和房价数据，共{len(data)}条记录（2000年以后）")

        # 准备返回数据
        result = {
            'status': 'success',
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data
        }
        
        # 保存到缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    except Exception as e:
        print(f"获取货币供应量数据失败: {e}")
        # 如果缓存文件存在，尝试读取缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as cache_e:
                print(f"读取缓存文件失败: {cache_e}")
        
        # 返回错误信息
        return {
            'status': 'error',
            'message': f'获取数据失败: {str(e)}',
            'data': []
        }

def get_ccidx_futures_index():
    """
    获取中证商品期货价格指数数据
    
    Returns:
        dict: 包含日期和指数值的字典
    """
    try:
        # 获取中证商品期货价格指数数据
        futures_index_ccidx_df = ak.futures_index_ccidx(symbol="中证商品期货价格指数")
        
        # 创建字典存储数据
        ccidx_dict = {}
        
        for _, row in futures_index_ccidx_df.iterrows():
            try:
                # 获取日期和指数值
                date_str = str(row['日期'])
                index_value = float(row['收盘点位']) if not pd.isna(row['收盘点位']) else None
                
                # 将日期转换为YYYY.M格式
                if '-' in date_str:
                    date_parts = date_str.split('-')
                    if len(date_parts) >= 2:
                        year = date_parts[0]
                        month = str(int(date_parts[1]))  # 去掉前导零
                        formatted_date = f"{year}.{month}"
                        
                        # 如果该月份已存在，取最新的值（通常是月末值）
                        if formatted_date not in ccidx_dict or date_str > ccidx_dict[formatted_date]['original_date']:
                            ccidx_dict[formatted_date] = {
                                '中证商品期货价格指数': round(index_value, 2) if index_value is not None else None,
                                'original_date': date_str
                            }
                            
            except Exception as e:
                print(f"处理中证商品期货指数数据行时出错: {e}")
                continue
        
        print(f"成功获取中证商品期货价格指数数据，共{len(ccidx_dict)}条记录")
        # 调试：输出部分数据
        if ccidx_dict:
            sample_keys = list(ccidx_dict.keys())[:5]
            print(f"中证商品期货价格指数数据样本: {[(k, ccidx_dict[k]) for k in sample_keys]}")
        return ccidx_dict
        
    except Exception as e:
        print(f"获取中证商品期货价格指数数据失败: {e}")
        return {}

def get_rolling_4q_profit_data():
    """
    获取滚动4Q净利润和TTM市盈率数据
    从true_quarterly_analysis.json文件中读取pe_ratio和rolling_4q_profit数据
    只有stock_count大于50时，当季数据才被采用
    
    Returns:
        dict: 包含日期、TTM市盈率、滚动4Q净利润、银行滚动4Q净利润和非银行滚动4Q净利润的字典
    """
    try:
        # 读取JSON文件
        json_file_path = r'C:\Users\17701\github\my_first_repo\stockapi\true_quarterly_analysis.json'
        
        if not os.path.exists(json_file_path):
            print(f"TTM市盈率数据文件不存在: {json_file_path}")
            print("返回空数据字典")
            return {}
        
        print(f"DEBUG: 开始读取TTM市盈率数据文件: {json_file_path}")
        
        # 检查文件是否为空
        if os.path.getsize(json_file_path) == 0:
            print(f"TTM市盈率数据文件为空: {json_file_path}")
            return {}
            
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"TTM市盈率数据文件内容为空: {json_file_path}")
                return {}
            data = json.loads(content)
        
        print(f"DEBUG: JSON文件读取成功，包含 {len(data.get('quarterly_data', {}))} 个季度数据")
        rolling_4q_dict = {}
        
        # 遍历季度数据
        quarterly_data = data.get('quarterly_data', {})
        
        for quarter, quarter_info in quarterly_data.items():
            # 获取pe_ratio和rolling_4q_profit数据
            pe_ratio = quarter_info.get('pe_ratio')
            rolling_4q_profit = quarter_info.get('rolling_4q_profit')
            # 获取银行和非银行滚动4Q净利润数据
            bank_rolling_4q_profit = quarter_info.get('bank_rolling_4q_profit')
            non_bank_rolling_4q_profit = quarter_info.get('non_bank_rolling_4q_profit')
            # 获取银行和非银行TTM市盈率数据
            bank_pe_ratio = quarter_info.get('bank_pe_ratio')
            non_bank_pe_ratio = quarter_info.get('non_bank_pe_ratio')
            stock_count = quarter_info.get('stock_count', 0)
            
            # 检查stock_count是否大于50
            if stock_count > 50 and (pe_ratio is not None or rolling_4q_profit is not None or bank_rolling_4q_profit is not None or non_bank_rolling_4q_profit is not None or bank_pe_ratio is not None or non_bank_pe_ratio is not None):
                # 将季度格式转换为年月格式
                # 例如：2024-Q1 -> 2024.3, 2024-Q2 -> 2024.6, 2024-Q3 -> 2024.9, 2024-Q4 -> 2024.12
                year, quarter_num = quarter.split('-Q')
                quarter_month_map = {'1': '3', '2': '6', '3': '9', '4': '12'}
                month = quarter_month_map.get(quarter_num, '12')
                formatted_date = f"{year}.{month}"
                
                rolling_4q_dict[formatted_date] = {
                    'TTM市盈率': round(pe_ratio, 2) if pe_ratio is not None else None,
                    '滚动4Q净利润': round(rolling_4q_profit / 100000000, 2) if rolling_4q_profit is not None else None,  # 转换为亿元
                    '银行滚动4Q净利润': round(bank_rolling_4q_profit / 100000000, 2) if bank_rolling_4q_profit is not None else None,  # 转换为亿元
                    '非银行滚动4Q净利润': round(non_bank_rolling_4q_profit / 100000000, 2) if non_bank_rolling_4q_profit is not None else None,  # 转换为亿元
                    '银行TTM市盈率': round(bank_pe_ratio, 2) if bank_pe_ratio is not None else None,
                    '非银行TTM市盈率': round(non_bank_pe_ratio, 2) if non_bank_pe_ratio is not None else None,
                    'success_count': stock_count
                    }
        
        print(f"成功获取滚动4Q净利润和TTM市盈率数据，共{len(rolling_4q_dict)}条记录")
        # 调试：输出部分数据
        if rolling_4q_dict:
            sample_keys = list(rolling_4q_dict.keys())[:5]
            print(f"滚动4Q净利润和TTM市盈率数据样本: {[(k, rolling_4q_dict[k]) for k in sample_keys]}")
        
        return rolling_4q_dict
        
    except Exception as e:
        print(f"获取TTM市盈率数据失败: {e}")
        return {}