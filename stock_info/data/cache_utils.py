"""
缓存工具模块 - 提供缓存相关的工具函数
"""
import os
import json
import time
from datetime import datetime

# 缓存目录路径
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
STOCK_FINANCE_CACHE_DIR = os.path.join(CACHE_DIR, 'stock_finance')

def ensure_cache_directories():
    """确保所有缓存目录存在"""
    # 主缓存目录
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    # A股财务数据缓存目录
    if not os.path.exists(STOCK_FINANCE_CACHE_DIR):
        os.makedirs(STOCK_FINANCE_CACHE_DIR)
    # 港股通南向数据缓存目录
    if not os.path.exists(os.path.join(CACHE_DIR, 'hkstock')):
        os.makedirs(os.path.join(CACHE_DIR, 'hkstock'))
    # 港股通北向数据缓存目录

    # 港股财务数据缓存目录
    if not os.path.exists(os.path.join(CACHE_DIR, 'hkstock_finance')):
        os.makedirs(os.path.join(CACHE_DIR, 'hkstock_finance'))
    # 宏观数据缓存目录
    if not os.path.exists(os.path.join(CACHE_DIR, 'macro')):
        os.makedirs(os.path.join(CACHE_DIR, 'macro'))

def read_cache(cache_file):
    """读取缓存文件"""
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取缓存文件出错: {e}")
        return None

def save_cache(cache_file, data):
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

def is_cache_expired(timestamp, hours=24):
    """
    检查缓存是否已过期
    
    Args:
        timestamp: 缓存时间戳
        hours: 过期时间(小时)，默认24小时
        
    Returns:
        bool: 是否已过期
    """
    # 转换小时为秒
    expiry_seconds = hours * 60 * 60
    return (time.time() - timestamp) > expiry_seconds