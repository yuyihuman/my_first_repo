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

# 确保缓存目录存在的辅助函数
def ensure_cache_directories():
    """确保所有缓存目录存在"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    if not os.path.exists(STOCK_FINANCE_CACHE_DIR):
        os.makedirs(STOCK_FINANCE_CACHE_DIR)
    # 确保港股通南向数据缓存目录存在
    if not os.path.exists(os.path.join(CACHE_DIR, 'hkstock')):
        os.makedirs(os.path.join(CACHE_DIR, 'hkstock'))
    # 确保港股通北向数据缓存目录存在
    if not os.path.exists(os.path.join(CACHE_DIR, 'northbound')):
        os.makedirs(os.path.join(CACHE_DIR, 'northbound'))

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
        
        # 获取恒生指数数据
        hsi_df = ak.stock_hk_index_daily_sina(symbol="HSI")
        # 将日期列转换为相同格式以便合并
        hsi_df['date'] = pd.to_datetime(hsi_df['date']).dt.strftime('%Y-%m-%d')
        # 创建一个日期到收盘价的映射
        hsi_close_dict = dict(zip(hsi_df['date'], hsi_df['close']))
        
        # 转换日期列为标准格式
        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        
        # 计算每日净买额和累计净买额
        daily_data = []
        for _, row in df.iterrows():
            date = row['日期']
            # 获取对应日期的恒生指数收盘价，如果不存在则为None
            hsi_close = hsi_close_dict.get(date)
            
            daily_data.append({
                '日期': date,
                '当日成交净买额': float(row['当日成交净买额']),
                '买入成交额': float(row['买入成交额']),
                '卖出成交额': float(row['卖出成交额']),
                '历史累计净买额': float(row['历史累计净买额']),
                '领涨股': row['领涨股'],
                '领涨股代码': row['领涨股-代码'],
                '领涨股涨跌幅': float(row['领涨股-涨跌幅']),
                '恒生指数': float(hsi_close) if hsi_close is not None else None
            })
        
        # 获取最近半年的数据
        half_year_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        recent_data = df[df['日期'] >= half_year_ago].copy()
        
        # 统计领涨股出现次数
        leading_stocks = {}
        for _, row in recent_data.iterrows():
            stock_name = row['领涨股']
            stock_code = row['领涨股-代码']
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
        
        # 取前20名领涨股
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

def get_northbound_data(refresh=False):
    """获取港股通(北向资金)数据"""
    # 确保缓存目录存在
    ensure_cache_directories()
    
    # 设置缓存文件路径
    cache_file = os.path.join(CACHE_DIR, 'northbound', 'northbound_flow.json')
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    # 检查缓存文件是否存在且未过期，除非强制刷新
    if not refresh and os.path.exists(cache_file):
        file_time = os.path.getmtime(cache_file)
        current_time = time.time()
        # 如果文件存在且未超过4小时，直接返回缓存数据
        if current_time - file_time < 4 * 60 * 60:  # 4小时 = 4 * 60 * 60秒
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    try:
        # 使用akshare获取北向资金数据
        import akshare as ak
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        
        # 获取沪深300指数数据
        sh300_df = ak.stock_zh_index_daily_em(symbol="sh000300")
        # 将日期列转换为相同格式以便合并
        sh300_df['date'] = pd.to_datetime(sh300_df['date']).dt.strftime('%Y-%m-%d')
        # 创建一个日期到收盘价的映射
        sh300_close_dict = dict(zip(sh300_df['date'], sh300_df['close']))
        
        # 转换日期列为标准格式
        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        
        # 计算每日净买额和累计净买额
        daily_data = []
        for _, row in df.iterrows():
            date = row['日期']
            # 获取对应日期的沪深300指数收盘价，如果不存在则为None
            sh300_close = sh300_close_dict.get(date)
            
            # 处理可能的NaN值，将其转换为None，这样在JSON序列化时会变成null而不是NaN
            daily_net_buy = row['当日成交净买额']
            buy_amount = row['买入成交额']
            sell_amount = row['卖出成交额']
            cumulative_net_buy = row['历史累计净买额']
            leading_stock_change = row['领涨股-涨跌幅']
            
            # 检查并处理NaN值
            daily_net_buy = None if pd.isna(daily_net_buy) else float(daily_net_buy)
            buy_amount = None if pd.isna(buy_amount) else float(buy_amount)
            sell_amount = None if pd.isna(sell_amount) else float(sell_amount)
            cumulative_net_buy = None if pd.isna(cumulative_net_buy) else float(cumulative_net_buy)
            leading_stock_change = None if pd.isna(leading_stock_change) else float(leading_stock_change)
            
            daily_data.append({
                '日期': date,
                '当日成交净买额': daily_net_buy,
                '买入成交额': buy_amount,
                '卖出成交额': sell_amount,
                '历史累计净买额': cumulative_net_buy,
                '领涨股': row['领涨股'],
                '领涨股代码': row['领涨股-代码'],
                '领涨股涨跌幅': leading_stock_change,
                '沪深300指数': float(sh300_close) if sh300_close is not None else None
            })
        
        # 获取最近半年的数据
        half_year_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        recent_data = df[df['日期'] >= half_year_ago].copy()
        
        # 统计领涨股出现次数
        leading_stocks = {}
        for _, row in recent_data.iterrows():
            stock_name = row['领涨股']
            stock_code = row['领涨股-代码']
            if pd.isna(stock_name) or pd.isna(stock_code):
                continue  # 跳过包含NaN值的记录
                
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
        
        # 取前20名领涨股
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
        print(f"获取北向资金数据失败: {e}")
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

def get_hkstock_finance(stock_code):
    """获取港股财务数据"""
    # 确保股票代码格式正确（5位数字）
    stock_code = stock_code.zfill(5)
    
    # 检查缓存
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'hkstock_finance')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{stock_code}_finance.json")
    
    # 如果缓存存在且未过期（24小时内），则使用缓存
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期（24小时）
        if time.time() - cache_data.get('timestamp', 0) < 86400:
            return cache_data['data']
    
    try:
        # 获取资产负债表数据
        balance_sheet_df = ak.stock_financial_hk_report_em(stock=stock_code, symbol="资产负债表", indicator="年度")
        
        # 获取利润表数据
        income_statement_df = ak.stock_financial_hk_report_em(stock=stock_code, symbol="利润表", indicator="年度")
        
        # 获取股票名称
        stock_name = "未知"
        if not balance_sheet_df.empty and 'SECURITY_NAME_ABBR' in balance_sheet_df.columns:
            stock_name = balance_sheet_df['SECURITY_NAME_ABBR'].iloc[0]
        
        # 处理财务数据
        financial_data = []
        
        # 获取所有报告期
        report_dates = sorted(balance_sheet_df['REPORT_DATE'].unique(), reverse=True)
        
        for report_date in report_dates:
            # 提取年份
            year = report_date.split('-')[0] if '-' in report_date else report_date
            
            # 资产负债表数据 - 总资产
            total_assets_query = balance_sheet_df[
                (balance_sheet_df['REPORT_DATE'] == report_date) & 
                (balance_sheet_df['STD_ITEM_NAME'] == '总资产')
            ]
            total_assets = total_assets_query['AMOUNT'].values[0] if not total_assets_query.empty else None
            
            # 总负债
            total_liabilities_query = balance_sheet_df[
                (balance_sheet_df['REPORT_DATE'] == report_date) & 
                (balance_sheet_df['STD_ITEM_NAME'] == '总负债')
            ]
            total_liabilities = total_liabilities_query['AMOUNT'].values[0] if not total_liabilities_query.empty else None
            
            # 股东权益
            equity_query = balance_sheet_df[
                (balance_sheet_df['REPORT_DATE'] == report_date) & 
                (balance_sheet_df['STD_ITEM_NAME'] == '股东权益')
            ]
            equity = equity_query['AMOUNT'].values[0] if not equity_query.empty else None
            
            # 利润表数据
            # 营业额
            revenue_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '营业额')
            ]
            revenue = revenue_query['AMOUNT'].values[0] if not revenue_query.empty else None
            
            # 股东应占溢利 (归属母公司净利润)
            net_profit_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '股东应占溢利')
            ]
            net_profit = net_profit_query['AMOUNT'].values[0] if not net_profit_query.empty else None
            
            # 毛利
            gross_profit_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '毛利')
            ]
            gross_profit = gross_profit_query['AMOUNT'].values[0] if not gross_profit_query.empty else None
            
            # 每股摊薄盈利
            eps_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '每股摊薄盈利')
            ]
            eps = eps_query['AMOUNT'].values[0] if not eps_query.empty else None
            
            # 计算财务指标
            debt_ratio = None
            if total_assets is not None and total_liabilities is not None and total_assets != 0:
                debt_ratio = (total_liabilities / total_assets) * 100
            
            net_profit_margin = None
            if revenue is not None and net_profit is not None and revenue != 0:
                net_profit_margin = (net_profit / revenue) * 100
            
            gross_profit_margin = None
            if revenue is not None and gross_profit is not None and revenue != 0:
                gross_profit_margin = (gross_profit / revenue) * 100
            
            # 添加到财务数据列表
            financial_data.append({
                "报告期": year,
                "负债率": debt_ratio,
                "净利率": net_profit_margin,
                "毛利率": gross_profit_margin,
                "稀释每股收益": eps,
                "归属母公司净利润": net_profit,
                "实收资本": equity
            })
        
        # 构建结果
        result = {
            "code": stock_code,
            "name": stock_name,
            "financial_data": financial_data
        }
        
        # 缓存结果
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({"data": result, "timestamp": time.time()}, f, ensure_ascii=False, indent=2)
        
        return result
    
    except Exception as e:
        print(f"获取港股财务数据出错: {e}")
        # 添加更详细的错误日志
        import traceback
        print(traceback.format_exc())
        raise Exception(f"获取港股财务数据失败: {e}")

def fetch_macro_china_money_supply():
    """
    获取中国货币供应量数据（仅2000年以后的数据）
    
    Returns:
        dict: 包含货币供应量数据的字典，包括M2/M1/M0总量和增速，以及房价同比和环比数据
    """
    try:
        # 检查缓存
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'macro')
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
                    '货币和准货币_广义货币M2_同比增长': m2_growth,
                    '货币_狭义货币M1_同比增长': m1_growth,
                    '流通中现金_M0_同比增长': m0_growth
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