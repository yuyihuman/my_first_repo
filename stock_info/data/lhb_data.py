"""
龙虎榜数据模块 - 提供龙虎榜相关的数据获取函数
"""
import os
import akshare as ak
from datetime import datetime, timedelta
from .cache_utils import CACHE_DIR, read_cache, save_cache, is_cache_expired

# 缓存文件路径，统一放到 cache 文件夹下
LHB_CACHE_DIR = os.path.join(CACHE_DIR, 'lhb')
os.makedirs(LHB_CACHE_DIR, exist_ok=True)
LHB_CACHE_FILE = os.path.join(LHB_CACHE_DIR, 'lhb_top1000_cache.json')

def get_lhb_top10():
    """
    获取近三年龙虎榜出现次数前300的股票，使用缓存机制
    
    Returns:
        dict: 包含龙虎榜前300股票的代码和出现次数
    """
    # 检查缓存是否存在且有效
    cache_data = read_cache(LHB_CACHE_FILE)
    if cache_data and not is_cache_expired(cache_data.get('timestamp', 0)):
        print("使用缓存的龙虎榜数据")
        return cache_data.get('data')
    
    # 缓存不存在或已过期，重新获取数据
    print("重新获取龙虎榜数据")
    data = _fetch_lhb_data()
    
    # 保存到缓存
    save_cache(LHB_CACHE_FILE, data)
    
    return data

def _fetch_lhb_data():
    """
    从API获取龙虎榜数据
    
    Returns:
        dict: 包含龙虎榜前1000股票的代码和出现次数
    """
    # 计算最近一年的日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
    try:
        # 获取龙虎榜数据
        df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
        # 统计每只股票出现的次数
        stock_count = df.groupby(['代码', '名称']).size().reset_index(name='出现次数')
        # 按出现次数降序排序并获取前1000名
        top1000 = stock_count.sort_values('出现次数', ascending=False).head(1000)
        # 构建返回数据
        result = {
            'codes': [f"{row['名称']}({row['代码']})" for _, row in top1000.iterrows()],
            'counts': top1000['出现次数'].tolist()
        }
        return result
    except Exception as e:
        print(f"获取龙虎榜数据出错: {e}")
        # 返回示例数据，以防API调用失败
        return {
            'codes': [f"示例股票{i}(00000{i})" for i in range(1, 11)],
            'counts': [10-i for i in range(10)]
        }