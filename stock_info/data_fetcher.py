import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time

# 缓存文件路径
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
LHB_CACHE_FILE = os.path.join(CACHE_DIR, 'lhb_top10_cache.json')
# 添加股票财务数据缓存目录
STOCK_FINANCE_CACHE_DIR = os.path.join(CACHE_DIR, 'stock_finance')

# 确保缓存目录存在
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
if not os.path.exists(STOCK_FINANCE_CACHE_DIR):
    os.makedirs(STOCK_FINANCE_CACHE_DIR)

def get_lhb_top10():
    """获取最近半年龙虎榜出现次数前10的股票，使用缓存机制"""
    # 检查缓存是否存在且有效
    cache_data = _read_cache(LHB_CACHE_FILE)
    if cache_data and not _is_cache_expired(cache_data.get('timestamp', 0)):
        print("使用缓存的龙虎榜数据")
        return cache_data.get('data')
    
    # 缓存不存在或已过期，重新获取数据
    print("重新获取龙虎榜数据")
    data = _fetch_lhb_data()
    
    # 保存到缓存
    _save_cache(LHB_CACHE_FILE, data)
    
    return data

def _fetch_lhb_data():
    """从API获取龙虎榜数据"""
    # 计算最近半年的日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
    
    try:
        # 获取龙虎榜数据
        df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
        
        # 统计每只股票出现的次数
        stock_count = df.groupby(['代码', '名称']).size().reset_index(name='出现次数')
        
        # 按出现次数降序排序并获取前10名
        top10 = stock_count.sort_values('出现次数', ascending=False).head(10)
        
        # 构建返回数据
        result = {
            'codes': [f"{row['名称']}({row['代码']})" for _, row in top10.iterrows()],
            'counts': top10['出现次数'].tolist()
        }
        
        return result
    except Exception as e:
        print(f"获取龙虎榜数据出错: {e}")
        # 返回示例数据，以防API调用失败
        return {
            'codes': [f"示例股票{i}(00000{i})" for i in range(1, 11)],
            'counts': [10-i for i in range(10)]
        }

def _read_cache(cache_file):
    """读取缓存文件"""
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取缓存文件出错: {e}")
        return None

def _save_cache(cache_file, data):
    """保存数据到缓存文件"""
    try:
        # 确保缓存目录存在
        cache_dir = os.path.dirname(cache_file)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        cache_data = {
            'data': data,
            'timestamp': time.time()
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存缓存文件出错: {e}")

def _is_cache_expired(timestamp):
    """检查缓存是否已过期（超过24小时）"""
    # 24小时 = 86400秒
    return (time.time() - timestamp) > 86400

def get_stock_financial_data(stock_code):
    """获取股票财务数据，使用缓存机制"""
    # 检查股票代码格式
    if not stock_code.isdigit() or len(stock_code) != 6:
        return {'error': '请输入正确的股票代码（6位数字）'}
    
    # 构建缓存文件路径
    cache_file = os.path.join(STOCK_FINANCE_CACHE_DIR, f'{stock_code}_finance.json')
    
    # 检查缓存是否存在且有效
    cache_data = _read_cache(cache_file)
    if cache_data and not _is_cache_expired(cache_data.get('timestamp', 0)):
        print(f"使用缓存的股票{stock_code}财务数据")
        return cache_data.get('data')
    
    # 缓存不存在或已过期，重新获取数据
    print(f"重新获取股票{stock_code}财务数据")
    data = _fetch_stock_financial_data(stock_code)
    
    # 保存到缓存
    _save_cache(cache_file, data)
    
    return data

def _convert_to_float(value_str):
    """将字符串格式的财务数据转换为浮点数"""
    if pd.isna(value_str) or value_str == 'False' or value_str == '--' or value_str == '':
        return 0.0
    
    if isinstance(value_str, (int, float)):
        return float(value_str)
    
    # 确保value_str是字符串类型
    value_str = str(value_str).strip()
    
    # 处理带单位的数字，如"123.45亿"、"5.77万"或"5.77万亿"
    if '万亿' in value_str:
        try:
            return float(value_str.replace('万亿', '')) * 1000000000000  # 万亿 = 10^12
        except ValueError:
            print(f"无法转换值: {value_str}")
            return 0.0
    elif '亿' in value_str:
        try:
            return float(value_str.replace('亿', '')) * 100000000  # 亿 = 10^8
        except ValueError:
            print(f"无法转换值: {value_str}")
            return 0.0
    elif '万' in value_str:
        try:
            return float(value_str.replace('万', '')) * 10000  # 万 = 10^4
        except ValueError:
            print(f"无法转换值: {value_str}")
            return 0.0
    
    try:
        return float(value_str)
    except ValueError:
        print(f"无法转换值: {value_str}")
        return 0.0

def _fetch_stock_financial_data(stock_code):
    """从API获取股票财务数据"""
    try:
        # 获取资产负债表数据
        debt_df = ak.stock_financial_debt_ths(symbol=stock_code, indicator="按年度")  # 改为按年度
        
        # 获取利润表数据
        benefit_df = ak.stock_financial_benefit_ths(symbol=stock_code, indicator="按年度")  # 改为按年度
        
        # 确保报告期列是字符串类型
        debt_df['报告期'] = debt_df['报告期'].astype(str)
        benefit_df['报告期'] = benefit_df['报告期'].astype(str)
        
        # 处理资产负债表数据，计算负债率，并提取实收资本
        # 检查是否存在实收资本列
        has_registered_capital = '实收资本（或股本）' in debt_df.columns
        
        if has_registered_capital:
            debt_df = debt_df[['报告期', '*资产合计', '*负债合计', '实收资本（或股本）']]
            debt_df['负债率'] = debt_df.apply(
                lambda x: _convert_to_float(x['*负债合计']) / _convert_to_float(x['*资产合计']) * 100 
                if _convert_to_float(x['*资产合计']) != 0 else 0, 
                axis=1
            )
            debt_df['实收资本'] = debt_df.apply(
                lambda x: _convert_to_float(x['实收资本（或股本）']), 
                axis=1
            )
            debt_df = debt_df[['报告期', '负债率', '实收资本']]
        else:
            debt_df = debt_df[['报告期', '*资产合计', '*负债合计']]
            debt_df['负债率'] = debt_df.apply(
                lambda x: _convert_to_float(x['*负债合计']) / _convert_to_float(x['*资产合计']) * 100 
                if _convert_to_float(x['*资产合计']) != 0 else 0, 
                axis=1
            )
            debt_df['实收资本'] = None
            debt_df = debt_df[['报告期', '负债率', '实收资本']]
        
        # 处理利润表数据，计算净利率、毛利率和提取稀释每股收益
        # 检查必要的列是否存在
        required_columns = ['报告期', '*净利润', '*营业总收入']
        
        # 检查是否存在稀释每股收益列和归属于母公司所有者的净利润列
        has_diluted_eps = '（二）稀释每股收益' in benefit_df.columns
        has_parent_net_profit = '归属于母公司所有者的净利润' in benefit_df.columns
        
        if not all(col in benefit_df.columns for col in required_columns):
            print(f"利润表缺少必要的列: {[col for col in required_columns if col not in benefit_df.columns]}")
            # 只计算存在的列
            benefit_df = benefit_df[['报告期', '*净利润', '*营业总收入']]
            benefit_df['净利率'] = benefit_df.apply(
                lambda x: _convert_to_float(x['*净利润']) / _convert_to_float(x['*营业总收入']) * 100 
                if _convert_to_float(x['*营业总收入']) != 0 else 0, 
                axis=1
            )
            # 由于缺少营业成本，无法计算毛利率
            benefit_df['毛利率'] = None
            # 添加稀释每股收益列，但值为None
            benefit_df['稀释每股收益'] = None
            # 添加归属于母公司所有者的净利润列，但值为None
            benefit_df['归属母公司净利润'] = None
        else:
            # 检查是否有营业成本列
            if '其中：营业成本' in benefit_df.columns:
                # 选择需要的列，如果有稀释每股收益列和归属于母公司所有者的净利润列，也一并选择
                cols_to_select = ['报告期', '*净利润', '*营业总收入', '其中：营业成本']
                if has_diluted_eps:
                    cols_to_select.append('（二）稀释每股收益')
                if has_parent_net_profit:
                    cols_to_select.append('归属于母公司所有者的净利润')
                
                benefit_df = benefit_df[cols_to_select]
                
                benefit_df['净利率'] = benefit_df.apply(
                    lambda x: _convert_to_float(x['*净利润']) / _convert_to_float(x['*营业总收入']) * 100 
                    if _convert_to_float(x['*营业总收入']) != 0 else 0, 
                    axis=1
                )
                benefit_df['毛利率'] = benefit_df.apply(
                    lambda x: ((_convert_to_float(x['*营业总收入']) - _convert_to_float(x['其中：营业成本'])) 
                            / _convert_to_float(x['*营业总收入'])) * 100 
                    if _convert_to_float(x['*营业总收入']) != 0 else 0, 
                    axis=1
                )
                
                # 处理稀释每股收益
                if has_diluted_eps:
                    benefit_df['稀释每股收益'] = benefit_df.apply(
                        lambda x: _convert_to_float(x['（二）稀释每股收益']), 
                        axis=1
                    )
                else:
                    benefit_df['稀释每股收益'] = None
                
                # 处理归属于母公司所有者的净利润
                if has_parent_net_profit:
                    benefit_df['归属母公司净利润'] = benefit_df.apply(
                        lambda x: _convert_to_float(x['归属于母公司所有者的净利润']), 
                        axis=1
                    )
                else:
                    benefit_df['归属母公司净利润'] = None
            else:
                print("缺少'其中：营业成本'列，无法计算毛利率")
                # 选择需要的列，如果有稀释每股收益列和归属于母公司所有者的净利润列，也一并选择
                cols_to_select = ['报告期', '*净利润', '*营业总收入']
                if has_diluted_eps:
                    cols_to_select.append('（二）稀释每股收益')
                if has_parent_net_profit:
                    cols_to_select.append('归属于母公司所有者的净利润')
                
                benefit_df = benefit_df[cols_to_select]
                
                benefit_df['净利率'] = benefit_df.apply(
                    lambda x: _convert_to_float(x['*净利润']) / _convert_to_float(x['*营业总收入']) * 100 
                    if _convert_to_float(x['*营业总收入']) != 0 else 0, 
                    axis=1
                )
                benefit_df['毛利率'] = None
                
                # 处理稀释每股收益
                if has_diluted_eps:
                    benefit_df['稀释每股收益'] = benefit_df.apply(
                        lambda x: _convert_to_float(x['（二）稀释每股收益']), 
                        axis=1
                    )
                else:
                    benefit_df['稀释每股收益'] = None
                
                # 处理归属于母公司所有者的净利润
                if has_parent_net_profit:
                    benefit_df['归属母公司净利润'] = benefit_df.apply(
                        lambda x: _convert_to_float(x['归属于母公司所有者的净利润']), 
                        axis=1
                    )
                else:
                    benefit_df['归属母公司净利润'] = None
        
        # 选择需要的列
        benefit_df = benefit_df[['报告期', '净利率', '毛利率', '稀释每股收益', '归属母公司净利润']]
        
        # 合并数据
        try:
            merged_df = pd.merge(debt_df, benefit_df, on='报告期', how='outer')
        except Exception as e:
            print(f"合并数据出错: {e}")
            # 尝试使用concat方法合并
            print("尝试使用concat方法合并数据...")
            debt_df.set_index('报告期', inplace=True)
            benefit_df.set_index('报告期', inplace=True)
            merged_df = pd.concat([debt_df, benefit_df], axis=1)
            merged_df.reset_index(inplace=True)
        
        # 按报告期排序并获取最近10个年度的数据
        merged_df = merged_df.sort_values('报告期', ascending=False).head(10)
        
        # 转换为字典列表
        result = []
        for _, row in merged_df.iterrows():
            result.append({
                '报告期': row['报告期'],
                '负债率': round(row['负债率'], 2) if not pd.isna(row['负债率']) else None,
                '净利率': round(row['净利率'], 2) if not pd.isna(row['净利率']) else None,
                '毛利率': round(row['毛利率'], 2) if not pd.isna(row['毛利率']) else None,
                '稀释每股收益': round(row['稀释每股收益'], 4) if not pd.isna(row['稀释每股收益']) else None,
                '归属母公司净利润': round(row['归属母公司净利润'], 2) if not pd.isna(row['归属母公司净利润']) else None,
                '实收资本': round(row['实收资本'], 2) if not pd.isna(row['实收资本']) else None
            })
        
        # 获取股票名称
        stock_name = _get_stock_name(stock_code)
        
        return {
            'code': stock_code,
            'name': stock_name,
            'financial_data': result
        }
    except Exception as e:
        print(f"获取股票{stock_code}财务数据出错: {e}")
        # 返回空数据
        return {
            'code': stock_code,
            'name': "获取失败",
            'financial_data': []
        }

def _get_stock_name(stock_code):
    """获取股票名称的函数，尝试多种方法"""
    try:
        # 方法1：使用stock_zh_a_spot_em接口获取当前A股行情数据
        spot_df = ak.stock_zh_a_spot_em()
        # 确保代码格式一致（有些接口返回的代码可能带有市场前缀）
        stock_row = spot_df[spot_df['代码'] == stock_code]
        if not stock_row.empty:
            return stock_row.iloc[0]['名称']
    except Exception as e:
        print(f"方法1获取股票名称失败: {e}")
    
    try:
        # 方法2：使用stock_lhb_detail_em接口获取龙虎榜数据
        # 使用最近一个月的数据
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        lhb_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
        stock_row = lhb_df[lhb_df['代码'] == stock_code]
        if not stock_row.empty:
            return stock_row.iloc[0]['名称']
    except Exception as e:
        print(f"方法2获取股票名称失败: {e}")
    
    try:
        # 方法3：使用stock_zh_a_hist接口获取历史行情数据
        # 只获取最近一天的数据
        today = datetime.now().strftime('%Y%m%d')
        one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date=one_month_ago, end_date=today, adjust="")
        if not hist_df.empty and '名称' in hist_df.columns:
            return hist_df.iloc[0]['名称']
        # 如果没有名称列，但有股票代码列，可以尝试从其他列获取信息
        elif not hist_df.empty:
            # 尝试从其他接口获取名称
            try:
                # 使用stock_individual_info_em接口
                stock_info = ak.stock_individual_info_em(symbol=stock_code)
                if not stock_info.empty:
                    # 股票名称通常在第二列
                    return stock_info.iloc[0, 1]
            except:
                pass
    except Exception as e:
        print(f"方法3获取股票名称失败: {e}")
    
    # 所有方法都失败，返回一个更友好的格式
    return f"股票{stock_code}"

# 在文件开头的导入部分之后添加以下函数

def ensure_cache_directories():
    """确保所有缓存目录存在"""
    directories = [
        CACHE_DIR,
        STOCK_FINANCE_CACHE_DIR
    ]
    for directory in directories:
        if not os.path.exists(directory):
            print(f"创建缓存目录: {directory}")
            os.makedirs(directory)

def get_hkstock_data():
    """获取港股通(南向资金)数据"""
    # 确保缓存目录存在
    ensure_cache_directories()
    
    # 设置缓存文件路径
    cache_file = os.path.join(CACHE_DIR, 'hkstock', 'southbound_flow.json')
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    # 检查缓存文件是否存在且未过期
    if os.path.exists(cache_file):
        file_time = os.path.getmtime(cache_file)
        current_time = time.time()
        # 如果文件存在且未超过4小时，直接返回缓存数据
        if current_time - file_time < 4 * 60 * 60:  # 4小时 = 4 * 60 * 60秒
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    try:
        # 使用akshare获取南向资金数据
        import akshare as ak
        df = ak.stock_hsgt_hist_em(symbol="南向资金")
        
        # 转换日期列为标准格式
        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        
        # 获取最近半年的数据
        half_year_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        recent_data = df[df['日期'] >= half_year_ago].copy()
        
        # 计算每日净买额和累计净买额
        daily_data = []
        for _, row in recent_data.iterrows():
            daily_data.append({
                '日期': row['日期'],
                '当日成交净买额': float(row['当日成交净买额']),
                '买入成交额': float(row['买入成交额']),
                '卖出成交额': float(row['卖出成交额']),
                '历史累计净买额': float(row['历史累计净买额']),
                '领涨股': row['领涨股'],
                '领涨股代码': row['领涨股-代码'],
                '领涨股涨跌幅': float(row['领涨股-涨跌幅'])
            })
        
        # 统计领涨股出现次数
        leading_stocks = {}
        for item in daily_data:
            stock_name = item['领涨股']
            stock_code = item['领涨股代码']
            if stock_name in leading_stocks:
                leading_stocks[stock_name]['count'] += 1
            else:
                leading_stocks[stock_name] = {
                    'code': stock_code,
                    'count': 1
                }
        
        # 转换为列表并按出现次数排序
        leading_stocks_list = [{'name': k, 'code': v['code'], 'count': v['count']} 
                              for k, v in leading_stocks.items()]
        leading_stocks_list.sort(key=lambda x: x['count'], reverse=True)
        
        # 取前20名领涨股（修改这里，从10改为20）
        top_leading_stocks = leading_stocks_list[:20]
        
        # 构建结果数据
        result = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'daily_data': daily_data,
            'top_leading_stocks': top_leading_stocks
        }
        
        # 保存到缓存文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    except Exception as e:
        print(f"获取港股通数据失败: {e}")
        # 如果获取失败但缓存文件存在，返回缓存数据
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # 否则返回空数据
        return {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'daily_data': [],
            'top_leading_stocks': []
        }