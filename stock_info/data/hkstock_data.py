"""
港股通数据模块 - 提供港股通(南向资金)数据相关的获取函数
"""
import os
import json
import time
import requests
import urllib3
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from .cache_utils import CACHE_DIR, ensure_cache_directories

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

                '恒生指数': float(hsi_close) if hsi_close is not None else None
            })
        

        
        # 构建结果数据
        result = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'daily_data': daily_data,

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

        }

def get_us_interest_rate_data():
    """获取美国利率数据"""
    # 确保缓存目录存在
    ensure_cache_directories()
    
    # 设置缓存文件路径
    cache_file = os.path.join(CACHE_DIR, 'hkstock', 'us_interest_rate.json')
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    # 检查缓存文件是否存在且未过期
    if os.path.exists(cache_file):
        file_time = os.path.getmtime(cache_file)
        current_time = time.time()
        # 如果文件存在且未超过24小时，直接返回缓存数据
        if current_time - file_time < 24 * 60 * 60:  # 24小时
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    try:
        # 使用akshare获取美国利率数据
        df = ak.macro_bank_usa_interest_rate()
        
        # 过滤掉空值和未来日期的数据
        df = df.dropna(subset=['今值'])
        df = df[pd.to_datetime(df['日期']) <= datetime.now()]
        
        # 转换日期格式并排序
        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('日期')
        
        # 构建数据列表
        rate_data = []
        for _, row in df.iterrows():
            rate_data.append({
                '日期': row['日期'],
                '利率': float(row['今值'])
            })
        
        # 构建结果数据
        result = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'rate_data': rate_data
        }
        
        # 保存到缓存文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    except Exception as e:
        print(f"获取美国利率数据失败: {e}")
        # 如果获取失败但缓存文件存在，返回缓存数据
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # 否则返回空数据
        return {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'rate_data': []
        }

def get_hsi_historical_data():
    """获取恒生指数历史数据"""
    # 确保缓存目录存在
    ensure_cache_directories()
    
    # 设置缓存文件路径
    cache_file = os.path.join(CACHE_DIR, 'hkstock', 'hsi_historical.json')
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    # 检查缓存文件是否存在且未过期
    if os.path.exists(cache_file):
        file_time = os.path.getmtime(cache_file)
        current_time = time.time()
        # 如果文件存在且未超过24小时，直接返回缓存数据
        if current_time - file_time < 24 * 60 * 60:  # 24小时
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # 尝试多种方法获取数据
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 清除代理设置，避免代理连接问题
            old_http_proxy = os.environ.get('HTTP_PROXY')
            old_https_proxy = os.environ.get('HTTPS_PROXY')
            
            # 临时清除代理环境变量
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            print(f"尝试获取恒生指数数据 (第{retry_count + 1}次)")
            
            # 使用akshare东方财富接口获取恒生指数历史数据
            df = ak.stock_hk_index_daily_em(symbol="HSI")
            
            # 恢复代理设置
            if old_http_proxy:
                os.environ['HTTP_PROXY'] = old_http_proxy
            if old_https_proxy:
                os.environ['HTTPS_PROXY'] = old_https_proxy
            
            # 转换日期格式并排序
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df = df.sort_values('date')
            
            # 构建数据列表
            hsi_data = []
            for _, row in df.iterrows():
                hsi_data.append({
                    '日期': row['date'],
                    '收盘价': float(row['latest'])  # 东方财富接口使用'latest'作为收盘价
                })
            
            # 构建结果数据
            result = {
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'hsi_data': hsi_data
            }
            
            # 保存到缓存文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"成功获取恒生指数历史数据，共{len(hsi_data)}条记录")
            return result
            
        except Exception as e:
            retry_count += 1
            print(f"获取恒生指数历史数据失败 (第{retry_count}次): {e}")
            
            # 恢复代理设置
            if 'old_http_proxy' in locals() and old_http_proxy:
                os.environ['HTTP_PROXY'] = old_http_proxy
            if 'old_https_proxy' in locals() and old_https_proxy:
                os.environ['HTTPS_PROXY'] = old_https_proxy
            
            if retry_count < max_retries:
                print(f"等待5秒后重试...")
                time.sleep(5)
            else:
                print("已达到最大重试次数，尝试使用备用方案")
                break
    
    # 如果所有重试都失败，尝试使用新浪接口作为备用方案
    try:
        print("尝试使用新浪接口获取恒生指数数据...")
        df = ak.stock_hk_index_daily_sina(symbol="HSI")
        
        # 转换日期格式并排序
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('date')
        
        # 构建数据列表
        hsi_data = []
        for _, row in df.iterrows():
            hsi_data.append({
                '日期': row['date'],
                '收盘价': float(row['close'])  # 新浪接口使用'close'作为收盘价
            })
        
        # 构建结果数据
        result = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hsi_data': hsi_data
        }
        
        # 保存到缓存文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"使用新浪接口成功获取恒生指数历史数据，共{len(hsi_data)}条记录")
        return result
        
    except Exception as e:
        print(f"新浪接口也获取失败: {e}")
        
        # 如果获取失败但缓存文件存在，返回缓存数据
        if os.path.exists(cache_file):
            print("使用缓存数据")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 否则返回空数据
        print("返回空数据")
        return {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hsi_data': []
        }