"""
北向资金数据模块 - 提供北向资金数据相关的获取函数
"""
import os
import json
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from .cache_utils import CACHE_DIR, ensure_cache_directories

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