import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time

# 缓存文件路径
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
LHB_CACHE_FILE = os.path.join(CACHE_DIR, 'lhb_top10_cache.json')

# 确保缓存目录存在
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

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