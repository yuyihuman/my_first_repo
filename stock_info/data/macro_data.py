"""
宏观经济数据模块 - 提供宏观经济数据相关的获取函数
"""
import os
import json
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cache_utils import CACHE_DIR

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
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # 检查文件是否为空
                            return json.loads(content)
                        else:
                            print(f"缓存文件为空，将重新获取数据: {cache_file}")
                except (json.JSONDecodeError, Exception) as e:
                    print(f"读取缓存文件失败: {e}，将重新获取数据")
        
        # 获取货币供应量数据（统一接口包含所有数据）
        money_supply_df = ak.macro_china_money_supply()
        
        # 使用同一个DataFrame，因为新接口包含了所有数据
        money_supply_total_df = money_supply_df.copy()
        
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
        
        # 根据新接口的列名设置增长率列名
        m2_growth_col = '货币和准货币(M2)-同比增长'
        m1_growth_col = '货币(M1)-同比增长'
        m0_growth_col = '流通中的现金(M0)-同比增长'
        
        # 验证列名是否存在，如果不存在则尝试查找
        if m2_growth_col not in money_supply_df.columns:
            for col in money_supply_df.columns:
                if 'M2' in col and '同比' in col:
                    m2_growth_col = col
                    break
        
        if m1_growth_col not in money_supply_df.columns:
            for col in money_supply_df.columns:
                if 'M1' in col and '同比' in col:
                    m1_growth_col = col
                    break
        
        if m0_growth_col not in money_supply_df.columns:
            for col in money_supply_df.columns:
                if 'M0' in col and '同比' in col:
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
        
        # 新增：计算从2016年1月开始的指数值
        # 首先找到2016年1月的数据作为基准点
        base_date = "2016.1"
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
            # 如果找不到精确的2016.1，尝试找最接近的日期
            for date_str in sorted_date_strings:
                if '.' in date_str:
                    year, month = date_str.split('.')
                    if int(year) == 2016 and int(month) == 1:
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
                        current_data['M2指数(2016.1=100)'] = round(m2_index, 2)
                    else:
                        current_data['M2指数(2016.1=100)'] = None
                    
                    # 特殊处理M1指数
                    if date_str == '2023.12' and base_m1 is not None and current_data.get('M1总量(亿元)') is not None:
                        # 记录2023年12月的M1指数值
                        m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                        dec_2023_m1_index = round(m1_index, 2)
                        current_data['M1指数(2016.1=100)'] = dec_2023_m1_index
                    elif date_str == '2024.1':
                        # 2024年1月的M1指数与2023年12月保持一致
                        if dec_2023_m1_index is not None:
                            current_data['M1指数(2016.1=100)'] = dec_2023_m1_index
                        else:
                            # 如果没有找到2023年12月的数据，仍然使用常规计算方法
                            if base_m1 is not None and current_data.get('M1总量(亿元)') is not None:
                                m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                                current_data['M1指数(2016.1=100)'] = round(m1_index, 2)
                            else:
                                current_data['M1指数(2016.1=100)'] = None
                    elif date_str > '2024.1' and base_m1 is not None:
                        # 2024年1月之后的月份，基于2024年1月的指数值和总量变化计算
                        # 查找2024年1月的数据
                        jan_2024_data = None
                        for d in sorted_date_strings:
                            if d == '2024.1' and d in money_total_dict:
                                jan_2024_data = money_total_dict[d]
                                break
                        
                        if jan_2024_data and 'M1指数(2016.1=100)' in jan_2024_data and jan_2024_data['M1指数(2016.1=100)'] is not None and jan_2024_data.get('M1总量(亿元)') is not None and current_data.get('M1总量(亿元)') is not None:
                            # 基于2024年1月的指数和总量变化计算
                            m1_index = jan_2024_data['M1指数(2016.1=100)'] * (current_data['M1总量(亿元)'] / jan_2024_data['M1总量(亿元)'])
                            current_data['M1指数(2016.1=100)'] = round(m1_index, 2)
                        else:
                            # 如果没有找到2024年1月的数据，使用常规计算方法
                            if current_data.get('M1总量(亿元)') is not None:
                                m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                                current_data['M1指数(2016.1=100)'] = round(m1_index, 2)
                            else:
                                current_data['M1指数(2016.1=100)'] = None
                    else:
                        # 2024年1月之前的月份，使用常规计算方法
                        if base_m1 is not None and current_data.get('M1总量(亿元)') is not None:
                            m1_index = (current_data['M1总量(亿元)'] / base_m1) * 100
                            current_data['M1指数(2016.1=100)'] = round(m1_index, 2)
                        else:
                            current_data['M1指数(2016.1=100)'] = None
                    
                    # 计算M0指数
                    if base_m0 is not None and current_data.get('M0总量(亿元)') is not None:
                        m0_index = (current_data['M0总量(亿元)'] / base_m0) * 100
                        current_data['M0指数(2016.1=100)'] = round(m0_index, 2)
                    else:
                        current_data['M0指数(2016.1=100)'] = None
        
        
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
        
        # 获取商品价格指数数据
        print("DEBUG: 开始获取商品价格指数数据...")
        commodity_dict = get_commodity_price_index_data()
        print(f"DEBUG: 商品价格指数数据获取完成，共{len(commodity_dict)}条记录")
        if len(commodity_dict) > 0:
            sample_keys = list(commodity_dict.keys())[:3]
            print(f"DEBUG: 商品价格指数数据样本键: {sample_keys}")
        else:
            print("DEBUG: 警告 - 商品价格指数数据为空！")
        
        # 获取上海新房价格数据
        house_price_dict = {}  # 初始化为空字典
        try:
            print("DEBUG: 开始获取上海房价数据...")
            # 获取上海房价数据
            house_price_df = ak.macro_china_new_house_price(city_first="上海")
            print(f"DEBUG: 成功获取房价数据，共{len(house_price_df)}条记录")
            
            # 确保日期列是字符串类型
            house_price_df['日期'] = house_price_df['日期'].astype(str)
            print(f"DEBUG: 房价数据列名: {list(house_price_df.columns)}")
            print(f"DEBUG: 房价数据前3行: {house_price_df.head(3).to_dict('records')}")
            
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
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            house_price_dict = {}
        
        print(f"房价数据获取完成，house_price_dict长度: {len(house_price_dict)}")
        if house_price_dict:
            print(f"房价数据样本: {list(house_price_dict.items())[:3]}")

        # 新增：计算上海住宅价格指数
        # 找到基准日期（2016.1）的房价数据
        base_house_price_data = None
        for date_str in sorted_date_strings:
            if date_str in house_price_dict and '.' in date_str:
                year, month = date_str.split('.')
                if int(year) == 2016 and int(month) == 1:
                    base_date_house = date_str
                    base_house_price_data = house_price_dict[date_str]
                    break
        
        # 如果找不到2016.1的数据，使用最早的数据作为基准
        if base_house_price_data is None and house_price_dict:
            earliest_date = sorted_date_strings[0]
            for date_str in sorted_date_strings:
                if date_str in house_price_dict:
                    earliest_date = date_str
                    base_house_price_data = house_price_dict[date_str]
                    break
            print(f"未找到2016.1的房价数据，使用{earliest_date}作为基准")
        
        # 如果找到了基准日期的房价数据，计算指数
        if base_house_price_data:
            # 使用累积环比方法计算以2016.1=100为基准的指数
            try:
                house_price_df_full = ak.macro_china_new_house_price(city_first="上海")
                house_price_df_full['日期'] = house_price_df_full['日期'].astype(str)
                
                # 按日期排序
                house_price_df_full = house_price_df_full.sort_values(by='日期')
                
                # 找到2016年1月的数据作为基准
                base_date = None
                base_new_mom = None
                base_second_mom = None
                
                for _, row in house_price_df_full.iterrows():
                    date_str = row['日期']
                    if '2016-01' in date_str:
                        base_date = date_str
                        base_new_mom = row.get('新建商品住宅价格指数-环比', 100.0)
                        base_second_mom = row.get('二手住宅价格指数-环比', 100.0)
                        break
                
                if base_date is None:
                    print("警告：未找到2016年1月数据，无法计算基准指数")
                else:
                    print(f"DEBUG: 找到基准日期 {base_date}，开始计算累积指数")
                    
                    # 初始化累积指数
                    new_house_index = 100.0  # 2016年1月设为100
                    second_house_index = 100.0
                    
                    for _, row in house_price_df_full.iterrows():
                        date_str = row['日期']
                        
                        # 转换日期格式
                        if '-' in date_str:
                            year_month = '-'.join(date_str.split('-')[:2])
                            year, month = year_month.split('-')
                            month = month.lstrip('0')
                            year_month_dot = f"{year}.{month}"
                        else:
                            year_month_dot = date_str
                            year_month = date_str.replace('.', '-')
                        
                        if date_str == base_date:
                            # 2016年1月设为基准100
                            calculated_new_index = 100.0
                            calculated_second_index = 100.0
                        elif date_str < base_date:
                            # 2016年1月之前的数据，向前推算
                            continue  # 暂时跳过，先处理2016年1月之后的数据
                        else:
                            # 2016年1月之后的数据，使用环比累积计算
                            new_mom = row.get('新建商品住宅价格指数-环比')
                            second_mom = row.get('二手住宅价格指数-环比')
                            
                            if new_mom is not None:
                                new_house_index = new_house_index * (new_mom / 100.0)
                                calculated_new_index = new_house_index
                            else:
                                calculated_new_index = None
                                
                            if second_mom is not None:
                                second_house_index = second_house_index * (second_mom / 100.0)
                                calculated_second_index = second_house_index
                            else:
                                calculated_second_index = None
                        
                        # 更新house_price_dict中的数据
                        if year_month_dot in house_price_dict:
                            house_price_dict[year_month_dot]['新建商品住宅价格指数(2016.1=100)'] = round(calculated_new_index, 2) if calculated_new_index is not None else None
                            house_price_dict[year_month_dot]['二手住宅价格指数(2016.1=100)'] = round(calculated_second_index, 2) if calculated_second_index is not None else None
                        
                        if year_month in house_price_dict:
                            house_price_dict[year_month]['新建商品住宅价格指数(2016.1=100)'] = round(calculated_new_index, 2) if calculated_new_index is not None else None
                            house_price_dict[year_month]['二手住宅价格指数(2016.1=100)'] = round(calculated_second_index, 2) if calculated_second_index is not None else None
                        
                        print(f"DEBUG: 计算 {year_month_dot} 指数 - 新建: {calculated_new_index}, 二手: {calculated_second_index}")
                        
            except Exception as e:
                print(f"计算房价指数失败: {e}")
                import traceback
                print(f"详细错误: {traceback.format_exc()}")

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
        
        # 确定数据获取的起始月份：使用沪深300指数的最新月份作为截止点
        end_year_month = None
        if hs300_dict:
            # 找到沪深300指数的最新月份
            latest_hs300_date = max(hs300_dict.keys(), key=lambda x: (int(x.split('.')[0]), int(x.split('.')[1])))
            end_year_month = latest_hs300_date
            print(f"使用沪深300指数最新月份作为截止点: {end_year_month}")
        else:
            # 如果没有沪深300数据，默认获取所有数据
            end_year_month = None
            print("未找到沪深300指数数据，获取所有可用数据")
        
        # 解析截止年月
        end_year = None
        end_month = None
        if end_year_month:
            end_year, end_month = end_year_month.split('.')
            end_year = int(end_year)
            end_month = int(end_month)
        
        processed_rows = 0
        matched_with_total = 0
        
        for _, row in money_supply_df.iterrows():
            try:
                date_str = str(row[date_col])
                
                # 处理日期格式
                if '年' in date_str and '月' in date_str:
                    # 处理格式如 "2025年07月份"
                    import re
                    match = re.search(r'(\d{4})年(\d{1,2})月', date_str)
                    if match:
                        year = int(match.group(1))
                        month = int(match.group(2))
                        formatted_date = f"{year}.{month}"
                    else:
                        continue
                elif '-' in date_str:
                    # 如果日期格式为 "2023-01"，转换为点格式
                    year = int(date_str.split('-')[0])
                    month = int(date_str.split('-')[1])
                    formatted_date = f"{year}.{month}"
                else:
                    # 处理格式如 "2023.01" 或 "2023.1"
                    formatted_date = date_str
                    # 提取年份和月份
                    year = int(formatted_date.split('.')[0])
                    month = int(formatted_date.split('.')[1])
                
                # 只保留2000年以后且不超过沪深300指数最新月份的数据
                if year < 2000:
                    continue
                
                # 如果设置了截止月份，则过滤超出该月份的数据
                if end_year is not None and end_month is not None:
                    if year > end_year or (year == end_year and month > end_month):
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
                    item['M2指数(2016.1=100)'] = money_total_dict[formatted_date].get('M2指数(2016.1=100)')
                    item['M1指数(2016.1=100)'] = money_total_dict[formatted_date].get('M1指数(2016.1=100)')
                    item['M0指数(2016.1=100)'] = money_total_dict[formatted_date].get('M0指数(2016.1=100)')
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
                                item['M2指数(2016.1=100)'] = money_total_dict[key].get('M2指数(2016.1=100)')
                                item['M1指数(2016.1=100)'] = money_total_dict[key].get('M1指数(2016.1=100)')
                                item['M0指数(2016.1=100)'] = money_total_dict[key].get('M0指数(2016.1=100)')
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
                        item['M2指数(2016.1=100)'] = None
                        item['M1指数(2016.1=100)'] = None
                        item['M0指数(2016.1=100)'] = None
                
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
                def find_latest_rolling_data(target_date, rolling_dict):
                    """查找最近一次的滚动4Q数据"""
                    if target_date in rolling_dict:
                        return rolling_dict[target_date], target_date
                    
                    # 尝试其他可能的日期格式匹配
                    for key in rolling_dict.keys():
                        if '.' in target_date and '.' in key:
                            if target_date.split('.')[0] == key.split('.')[0] and target_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                return rolling_dict[key], key
                    
                    # 如果没有精确匹配，查找最近一次的数据
                    try:
                        target_year = int(target_date.split('.')[0])
                        target_month = int(target_date.split('.')[1].lstrip('0'))
                        
                        # 按时间倒序排列所有可用的数据键
                        available_dates = []
                        for key in rolling_dict.keys():
                            try:
                                key_year = int(key.split('.')[0])
                                key_month = int(key.split('.')[1].lstrip('0'))
                                key_date = key_year * 12 + key_month
                                target_date_num = target_year * 12 + target_month
                                
                                # 只考虑目标日期之前的数据
                                if key_date <= target_date_num:
                                    available_dates.append((key_date, key))
                            except:
                                continue
                        
                        if available_dates:
                            # 按时间倒序排列，取最近的一个
                            available_dates.sort(reverse=True)
                            latest_key = available_dates[0][1]
                            return rolling_dict[latest_key], latest_key
                    except:
                        pass
                    
                    return None, None
                
                rolling_data, matched_key = find_latest_rolling_data(formatted_date, rolling_4q_dict)
                
                if rolling_data:
                    # 检查当前月份是否超过了最新的季度数据，如果是，则不设置净利润数据
                    # 这样可以避免显示补全的净利润数据
                    should_set_profit_data = (matched_key == formatted_date)
                    
                    if should_set_profit_data:
                        # 获取滚动4Q净利润数据（只有当月份有真实季度数据时才设置）
                        item['滚动4Q净利润'] = rolling_data['滚动4Q净利润']
                        item['银行滚动4Q净利润'] = rolling_data['银行滚动4Q净利润']
                        item['非银行滚动4Q净利润'] = rolling_data['非银行滚动4Q净利润']
                    else:
                        # 对于没有真实季度数据的月份，净利润保持为None
                        item['滚动4Q净利润'] = None
                        item['银行滚动4Q净利润'] = None
                        item['非银行滚动4Q净利润'] = None
                    
                    # 根据当月沪深300指数重新计算TTM市盈率
                    # TTM市盈率 = 当月市值 / 滚动4Q净利润
                    # 假设基准季度的市值 = 基准季度TTM市盈率 * 滚动4Q净利润
                    # 当月市值 = 基准市值 * (当月沪深300指数 / 基准沪深300指数)
                    # 当月TTM市盈率 = 当月市值 / 滚动4Q净利润
                    
                    base_ttm_pe = rolling_data['TTM市盈率']
                    base_bank_ttm_pe = rolling_data['银行TTM市盈率']
                    base_non_bank_ttm_pe = rolling_data['非银行TTM市盈率']
                    
                    # 获取基准季度的沪深300指数（从matched_key对应的数据中获取）
                    base_hs300_index = None
                    if matched_key in hs300_dict:
                        base_hs300_index = hs300_dict[matched_key]['沪深300指数']
                    
                    # 获取当月的沪深300指数
                    current_hs300_index = item.get('沪深300指数')
                    
                    if (base_ttm_pe is not None and base_hs300_index is not None and 
                        current_hs300_index is not None and base_hs300_index != 0):
                        # 计算指数比率
                        index_ratio = current_hs300_index / base_hs300_index
                        # 重新计算TTM市盈率
                        item['TTM市盈率'] = round(base_ttm_pe * index_ratio, 2)
                    else:
                        item['TTM市盈率'] = base_ttm_pe
                    
                    # 计算银行TTM市盈率
                    if (base_bank_ttm_pe is not None and base_hs300_index is not None and 
                        current_hs300_index is not None and base_hs300_index != 0):
                        index_ratio = current_hs300_index / base_hs300_index
                        item['银行TTM市盈率'] = round(base_bank_ttm_pe * index_ratio, 2)
                    else:
                        item['银行TTM市盈率'] = base_bank_ttm_pe
                    
                    # 计算非银行TTM市盈率
                    if (base_non_bank_ttm_pe is not None and base_hs300_index is not None and 
                        current_hs300_index is not None and base_hs300_index != 0):
                        index_ratio = current_hs300_index / base_hs300_index
                        item['非银行TTM市盈率'] = round(base_non_bank_ttm_pe * index_ratio, 2)
                    else:
                        item['非银行TTM市盈率'] = base_non_bank_ttm_pe
                    
                    if matched_key == formatted_date:
                        print(f"DEBUG: 直接匹配成功 {formatted_date} -> TTM: {item['TTM市盈率']}, 4Q净利润: {item['滚动4Q净利润']}")
                    else:
                        print(f"DEBUG: 使用最近数据 {formatted_date} -> {matched_key} -> TTM: {item['TTM市盈率']}, 4Q净利润: {item['滚动4Q净利润']}")
                else:
                    item['TTM市盈率'] = None
                    item['滚动4Q净利润'] = None
                    item['银行滚动4Q净利润'] = None
                    item['非银行滚动4Q净利润'] = None
                    item['银行TTM市盈率'] = None
                    item['非银行TTM市盈率'] = None
                    if len(rolling_4q_dict) > 0:
                        print(f"DEBUG: 未找到任何匹配数据 {formatted_date}，滚动4Q数据键示例: {list(rolling_4q_dict.keys())[:3]}")
                
                # 添加房价数据（如果存在）
                if formatted_date in house_price_dict:
                    item['上海新建商品住宅价格指数_同比'] = house_price_dict[formatted_date]['新建商品住宅价格指数_同比']
                    item['上海二手住宅价格指数_同比'] = house_price_dict[formatted_date]['二手住宅价格指数_同比']
                    item['上海新建商品住宅价格指数_环比'] = house_price_dict[formatted_date]['新建商品住宅价格指数_环比']
                    item['上海二手住宅价格指数_环比'] = house_price_dict[formatted_date]['二手住宅价格指数_环比']
                    item['上海新建商品住宅价格指数(2016.1=100)'] = house_price_dict[formatted_date].get('新建商品住宅价格指数(2016.1=100)')
                    item['上海二手住宅价格指数(2016.1=100)'] = house_price_dict[formatted_date].get('二手住宅价格指数(2016.1=100)')
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
                                item['上海新建商品住宅价格指数(2016.1=100)'] = house_price_dict[key].get('新建商品住宅价格指数(2016.1=100)')
                                item['上海二手住宅价格指数(2016.1=100)'] = house_price_dict[key].get('二手住宅价格指数(2016.1=100)')
                                found = True
                                break
                        elif '.' in formatted_date and '.' in key:
                            if formatted_date.split('.')[0] == key.split('.')[0] and formatted_date.split('.')[1].lstrip('0') == key.split('.')[1].lstrip('0'):
                                item['上海新建商品住宅价格指数_同比'] = house_price_dict[key]['新建商品住宅价格指数_同比']
                                item['上海二手住宅价格指数_同比'] = house_price_dict[key]['二手住宅价格指数_同比']
                                item['上海新建商品住宅价格指数_环比'] = house_price_dict[key]['新建商品住宅价格指数_环比']
                                item['上海二手住宅价格指数_环比'] = house_price_dict[key]['二手住宅价格指数_环比']
                                item['上海新建商品住宅价格指数(2016.1=100)'] = house_price_dict[key].get('新建商品住宅价格指数(2016.1=100)')
                                item['上海二手住宅价格指数(2016.1=100)'] = house_price_dict[key].get('二手住宅价格指数(2016.1=100)')
                                found = True
                                break
                    
                    if not found:
                        item['上海新建商品住宅价格指数_同比'] = None
                        item['上海二手住宅价格指数_同比'] = None
                        item['上海新建商品住宅价格指数_环比'] = None
                        item['上海二手住宅价格指数_环比'] = None
                        item['上海新建商品住宅价格指数(2016.1=100)'] = None
                        item['上海二手住宅价格指数(2016.1=100)'] = None
                
                # 添加商品价格指数数据（如果存在）
                # 商品价格指数数据现在使用日期格式（YYYY-MM-DD）作为键
                commodity_value = None
                print(f"DEBUG: 处理日期 {formatted_date}，商品价格指数数据条数: {len(commodity_dict)}")
                if len(commodity_dict) == 0:
                    print("WARNING: 商品价格指数数据为空！")
                
                # 解析目标年月，支持多种格式：YYYY.MM, YYYY-MM, YYYY.M, YYYY-M
                target_year = None
                target_month = None
                
                # 尝试解析日期格式
                if '.' in formatted_date:
                    parts = formatted_date.split('.')
                    if len(parts) == 2:
                        target_year = int(parts[0])
                        target_month = int(parts[1].lstrip('0'))
                elif '-' in formatted_date:
                    parts = formatted_date.split('-')
                    if len(parts) == 2:
                        target_year = int(parts[0])
                        target_month = int(parts[1].lstrip('0'))
                
                if target_year is not None and target_month is not None:
                    # 查找该月份的最新商品价格指数数据
                    latest_date = None
                    matching_count = 0
                    for date_key in commodity_dict.keys():
                        try:
                            # 解析日期格式 YYYY-MM-DD
                            date_parts = date_key.split('-')
                            if len(date_parts) == 3:
                                year = int(date_parts[0])
                                month = int(date_parts[1])
                                
                                # 如果年月匹配
                                if year == target_year and month == target_month:
                                    matching_count += 1
                                    # 找到该月份的最新日期
                                    if latest_date is None or date_key > latest_date:
                                        latest_date = date_key
                                        commodity_value = commodity_dict[date_key]['商品价格指数']
                        except (ValueError, IndexError):
                            continue
                    print(f"DEBUG: {formatted_date} 找到 {matching_count} 个匹配日期，最新日期: {latest_date}，指数值: {commodity_value}")
                else:
                    # 如果格式不匹配，设置为None但不跳过整个数据项
                    commodity_value = None
                

                
                item['商品价格指数'] = commodity_value
                
                data.append(item)
                processed_rows += 1
                
            except (ValueError, TypeError, KeyError) as e:
                print(f"处理行数据时出错: {e}")
                continue
        
        # 确保包含所有沪深300指数有数据但货币供应量没有数据的月份
        if hs300_dict:
            # 获取现有数据中的所有月份
            existing_months = set(item['月份'] for item in data)

            
            # 检查沪深300指数数据中是否有缺失的月份
            for hs300_month in hs300_dict.keys():
                if hs300_month not in existing_months:
                    # 解析年月，确保是2000年以后的数据
                    try:
                        year, month = hs300_month.split('.')
                        if int(year) >= 2000:
                            print(f"添加沪深300指数月份数据: {hs300_month}")
                            
                            # 创建基本数据项，货币供应量相关字段设为null
                            item = {
                                '月份': hs300_month,
                                '货币和准货币_广义货币M2_同比': None,
                                '货币_狭义货币M1_同比': None,
                                '流通中现金_M0_同比': None,
                                'M2总量(亿元)': None,
                                'M1总量(亿元)': None,
                                'M0总量(亿元)': None,
                                'M2总量环比(%)': None,
                                'M1总量环比(%)': None,
                                'M0总量环比(%)': None,
                                'M2指数(2016.1=100)': None,
                                'M1指数(2016.1=100)': None,
                                'M0指数(2016.1=100)': None
                            }
                            
                            # 添加沪深300指数数据
                            item['沪深300指数'] = hs300_dict[hs300_month]['沪深300指数']
                            item['沪深300指数_同比'] = hs300_dict[hs300_month]['沪深300指数_同比']
                            
                            # 添加中证商品期货价格指数数据（如果存在）
                            if hs300_month in ccidx_dict:
                                item['中证商品期货价格指数'] = ccidx_dict[hs300_month]['中证商品期货价格指数']
                            else:
                                item['中证商品期货价格指数'] = None
                            
                            # 添加滚动4Q净利润和TTM市盈率数据（使用最近一次数据）
                            def find_latest_rolling_data_for_new_month(target_date, rolling_dict):
                                """为新增月份查找最近一次的滚动4Q数据"""
                                if target_date in rolling_dict:
                                    return rolling_dict[target_date], target_date
                                
                                # 如果没有精确匹配，查找最近一次的数据
                                try:
                                    target_year = int(target_date.split('.')[0])
                                    target_month = int(target_date.split('.')[1].lstrip('0'))
                                    
                                    # 按时间倒序排列所有可用的数据键
                                    available_dates = []
                                    for key in rolling_dict.keys():
                                        try:
                                            key_year = int(key.split('.')[0])
                                            key_month = int(key.split('.')[1].lstrip('0'))
                                            key_date = key_year * 12 + key_month
                                            target_date_num = target_year * 12 + target_month
                                            
                                            # 只考虑目标日期之前的数据
                                            if key_date <= target_date_num:
                                                available_dates.append((key_date, key))
                                        except:
                                            continue
                                    
                                    if available_dates:
                                        # 按时间倒序排列，取最近的一个
                                        available_dates.sort(reverse=True)
                                        latest_key = available_dates[0][1]
                                        return rolling_dict[latest_key], latest_key
                                except:
                                    pass
                                
                                return None, None
                            
                            rolling_data_new, matched_key_new = find_latest_rolling_data_for_new_month(hs300_month, rolling_4q_dict)
                            
                            if rolling_data_new:
                                # 注意：为了满足用户需求，这里只补全TTM市盈率用于计算，不补全净利润数据用于图表显示
                                # 净利润数据保持为None，这样前端图表就不会显示这些补全的数据点
                                
                                # 根据当月沪深300指数重新计算TTM市盈率（用于TTM计算）
                                base_ttm_pe = rolling_data_new['TTM市盈率']
                                base_bank_ttm_pe = rolling_data_new['银行TTM市盈率']
                                base_non_bank_ttm_pe = rolling_data_new['非银行TTM市盈率']
                                
                                # 获取基准季度的沪深300指数
                                base_hs300_index = None
                                if matched_key_new in hs300_dict:
                                    base_hs300_index = hs300_dict[matched_key_new]['沪深300指数']
                                
                                # 获取当月的沪深300指数
                                current_hs300_index = item.get('沪深300指数')
                                
                                if (base_ttm_pe is not None and base_hs300_index is not None and 
                                    current_hs300_index is not None and base_hs300_index != 0):
                                    # 计算指数比率
                                    index_ratio = current_hs300_index / base_hs300_index
                                    # 重新计算TTM市盈率
                                    item['TTM市盈率'] = round(base_ttm_pe * index_ratio, 2)
                                else:
                                    item['TTM市盈率'] = base_ttm_pe
                                
                                # 计算银行TTM市盈率
                                if (base_bank_ttm_pe is not None and base_hs300_index is not None and 
                                    current_hs300_index is not None and base_hs300_index != 0):
                                    index_ratio = current_hs300_index / base_hs300_index
                                    item['银行TTM市盈率'] = round(base_bank_ttm_pe * index_ratio, 2)
                                else:
                                    item['银行TTM市盈率'] = base_bank_ttm_pe
                                
                                # 计算非银行TTM市盈率
                                if (base_non_bank_ttm_pe is not None and base_hs300_index is not None and 
                                    current_hs300_index is not None and base_hs300_index != 0):
                                    index_ratio = current_hs300_index / base_hs300_index
                                    item['非银行TTM市盈率'] = round(base_non_bank_ttm_pe * index_ratio, 2)
                                else:
                                    item['非银行TTM市盈率'] = base_non_bank_ttm_pe
                                
                                # 净利润数据保持为None，不进行补全，这样图表就不会显示这些数据点
                                item['滚动4Q净利润'] = None
                                item['银行滚动4Q净利润'] = None
                                item['非银行滚动4Q净利润'] = None
                            else:
                                item['TTM市盈率'] = None
                                item['滚动4Q净利润'] = None
                                item['银行滚动4Q净利润'] = None
                                item['非银行滚动4Q净利润'] = None
                                item['银行TTM市盈率'] = None
                                item['非银行TTM市盈率'] = None
                            
                            # 添加房价数据（如果存在）
                            if hs300_month in house_price_dict:
                                item['上海新建商品住宅价格指数_同比'] = house_price_dict[hs300_month]['新建商品住宅价格指数_同比']
                                item['上海二手住宅价格指数_同比'] = house_price_dict[hs300_month]['二手住宅价格指数_同比']
                                item['上海新建商品住宅价格指数_环比'] = house_price_dict[hs300_month]['新建商品住宅价格指数_环比']
                                item['上海二手住宅价格指数_环比'] = house_price_dict[hs300_month]['二手住宅价格指数_环比']
                                item['上海新建商品住宅价格指数(2016.1=100)'] = house_price_dict[hs300_month].get('新建商品住宅价格指数(2016.1=100)')
                                item['上海二手住宅价格指数(2016.1=100)'] = house_price_dict[hs300_month].get('二手住宅价格指数(2016.1=100)')
                            else:
                                item['上海新建商品住宅价格指数_同比'] = None
                                item['上海二手住宅价格指数_同比'] = None
                                item['上海新建商品住宅价格指数_环比'] = None
                                item['上海二手住宅价格指数_环比'] = None
                                item['上海新建商品住宅价格指数(2016.1=100)'] = None
                                item['上海二手住宅价格指数(2016.1=100)'] = None
                            
                            # 添加商品价格指数数据（如果存在）
                            commodity_value = None
                            print(f"DEBUG: 处理新增沪深300月份 {hs300_month}，商品价格指数数据条数: {len(commodity_dict)}")
                            
                            # 解析目标年月
                            target_year = None
                            target_month = None
                            
                            if '.' in hs300_month:
                                parts = hs300_month.split('.')
                                if len(parts) == 2:
                                    target_year = int(parts[0])
                                    target_month = int(parts[1].lstrip('0'))
                            
                            if target_year is not None and target_month is not None:
                                # 查找该月份的最新商品价格指数数据
                                latest_date = None
                                matching_count = 0
                                for date_key in commodity_dict.keys():
                                    try:
                                        # 解析日期格式 YYYY-MM-DD
                                        date_parts = date_key.split('-')
                                        if len(date_parts) == 3:
                                            year = int(date_parts[0])
                                            month = int(date_parts[1])
                                            
                                            # 如果年月匹配
                                            if year == target_year and month == target_month:
                                                matching_count += 1
                                                # 找到该月份的最新日期
                                                if latest_date is None or date_key > latest_date:
                                                    latest_date = date_key
                                                    commodity_value = commodity_dict[date_key]['商品价格指数']
                                    except (ValueError, IndexError):
                                        continue
                                print(f"DEBUG: 新增月份 {hs300_month} 找到 {matching_count} 个匹配日期，最新日期: {latest_date}，指数值: {commodity_value}")
                            
                            item['商品价格指数'] = commodity_value
                            
                            data.append(item)
                    except (ValueError, IndexError):
                        continue
        
        print(f"成功获取并缓存货币供应量、总量和房价数据，共{len(data)}条记录（2000年以后）")
        
        # 合并PMI数据中的新订单指数和新出口订单指数
        try:
            pmi_file_path = r'C:\Users\17701\github\my_first_repo\stockapi\pmi_data.json'
            if os.path.exists(pmi_file_path):
                with open(pmi_file_path, 'r', encoding='utf-8') as f:
                    pmi_data = json.load(f)
                
                # 创建PMI数据的月份到指数的映射
                pmi_mapping = {}
                for item in pmi_data:
                    date_str = item['date']  # 格式: "2010-01"
                    year, month = date_str.split('-')
                    # 转换为货币供应量数据的月份格式: "2010.1"
                    formatted_date = f"{year}.{int(month)}"
                    
                    # 获取新订单指数和新出口订单指数
                    new_order_index = item['indicators'].get('新订单指数(%)', None)
                    new_export_order_index = item['indicators'].get('新出口订单指数(%)', None)
                    # 获取工业生产者购进价格指数和燃料、动力类购进价格指数
                    producer_price_index = item['indicators'].get('工业生产者购进价格指数(2011年1月=100)', None)
                    fuel_power_price_index = item['indicators'].get('燃料、动力类购进价格指数(2011年1月=100)', None)
                    
                    pmi_mapping[formatted_date] = {
                        '新订单指数(%)': new_order_index,
                        '新出口订单指数(%)': new_export_order_index,
                        '工业生产者购进价格指数(2011年1月=100)': producer_price_index,
                        '燃料、动力类购进价格指数(2011年1月=100)': fuel_power_price_index
                    }
                
                # 为每个月份数据添加PMI指数
                for item in data:
                    month = item['月份']
                    if month in pmi_mapping:
                        item['新订单指数(%)'] = pmi_mapping[month]['新订单指数(%)']
                        item['新出口订单指数(%)'] = pmi_mapping[month]['新出口订单指数(%)']
                        item['工业生产者购进价格指数(2011年1月=100)'] = pmi_mapping[month]['工业生产者购进价格指数(2011年1月=100)']
                        item['燃料、动力类购进价格指数(2011年1月=100)'] = pmi_mapping[month]['燃料、动力类购进价格指数(2011年1月=100)']
                    else:
                        item['新订单指数(%)'] = None
                        item['新出口订单指数(%)'] = None
                        item['工业生产者购进价格指数(2011年1月=100)'] = None
                        item['燃料、动力类购进价格指数(2011年1月=100)'] = None
                
                new_order_count = len([item for item in data if item.get('新订单指数(%)') is not None])
                new_export_order_count = len([item for item in data if item.get('新出口订单指数(%)') is not None])
                print(f"成功合并PMI数据，共{new_order_count}条记录有新订单指数数据，{new_export_order_count}条记录有新出口订单指数数据")
            else:
                print(f"PMI数据文件不存在: {pmi_file_path}")
                # 如果PMI文件不存在，为所有数据添加None值
                for item in data:
                    item['新订单指数(%)'] = None
                    item['新出口订单指数(%)'] = None
                    item['工业生产者购进价格指数(2011年1月=100)'] = None
                    item['燃料、动力类购进价格指数(2011年1月=100)'] = None
        except Exception as e:
            print(f"合并PMI数据时出错: {e}")
            # 出错时为所有数据添加None值
            for item in data:
                item['新订单指数(%)'] = None
                item['新出口订单指数(%)'] = None
                item['工业生产者购进价格指数(2011年1月=100)'] = None
                item['燃料、动力类购进价格指数(2011年1月=100)'] = None

        # 按时间正序排列数据
        def parse_date_key(date_str):
            """解析日期字符串，返回用于排序的元组 (年, 月)"""
            try:
                if '.' in date_str:
                    year, month = date_str.split('.')
                    return (int(year), int(month))
                elif '-' in date_str:
                    year, month = date_str.split('-')
                    return (int(year), int(month))
                else:
                    return (0, 0)  # 默认值
            except (ValueError, IndexError):
                return (0, 0)  # 默认值
        
        # 按时间倒序排序（从晚到早）
        data.sort(key=lambda x: parse_date_key(x['月份']), reverse=True)
        
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

def get_commodity_price_index_data():
    """
    获取商品价格指数数据
    从commodity_price_index.json文件中读取指数数据
    
    Returns:
        dict: 包含日期和商品价格指数的字典
    """
    try:
        # 读取JSON文件 - 使用相对路径
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_file_path = os.path.join(current_dir, '..', 'stockapi', 'commodity_price_index.json')
        json_file_path = os.path.abspath(json_file_path)
        
        print(f"DEBUG: 尝试读取商品价格指数文件: {json_file_path}")
        
        if not os.path.exists(json_file_path):
            print(f"商品价格指数数据文件不存在: {json_file_path}")
            return {}
        
        print(f"DEBUG: 开始读取商品价格指数数据文件: {json_file_path}")
        
        # 检查文件是否为空
        if os.path.getsize(json_file_path) == 0:
            print(f"商品价格指数数据文件为空: {json_file_path}")
            return {}
            
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"商品价格指数数据文件内容为空: {json_file_path}")
                return {}
            data = json.loads(content)
        
        print(f"DEBUG: 商品价格指数JSON文件读取成功，包含 {len(data.get('指数数据', []))} 条数据")
        commodity_dict = {}
        
        # 遍历指数数据
        index_data = data.get('指数数据', [])
        
        for item in index_data:
            date_str = item.get('日期')
            index_value = item.get('指数值')
            
            if date_str and index_value is not None:
                # 保持原始日期格式，不进行月份聚合
                try:
                    # 验证日期格式
                    datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # 直接使用原始日期作为键
                    commodity_dict[date_str] = {
                        '商品价格指数': round(index_value, 2)
                    }
                except ValueError:
                    continue
        
        print(f"成功获取商品价格指数数据，共{len(commodity_dict)}条记录")
        # 调试：输出部分数据
        if commodity_dict:
            sample_keys = list(commodity_dict.keys())[-5:]  # 显示最新的5条数据
            print(f"商品价格指数数据样本: {[(k, commodity_dict[k]) for k in sample_keys]}")
        
        return commodity_dict
        
    except Exception as e:
        print(f"获取商品价格指数数据失败: {e}")
        return {}

if __name__ == '__main__':
    # 执行数据获取
    print("开始获取宏观经济数据...")
    data = fetch_macro_china_money_supply()
    print("宏观经济数据获取完成！")