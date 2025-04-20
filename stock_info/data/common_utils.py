"""
通用工具模块 - 提供各种数据处理的通用函数
"""
import pandas as pd
from datetime import datetime, timedelta

def convert_to_float(value_str):
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

def convert_date_for_sorting(date_str):
    """
    将不同格式的日期字符串转换为可排序的格式
    
    Args:
        date_str: 日期字符串，如 "2023.9" 或 "2023-09"
        
    Returns:
        str: 可排序的日期字符串，格式为 "YYYYMM"
    """
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