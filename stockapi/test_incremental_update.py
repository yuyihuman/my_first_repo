#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增量更新功能
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import subprocess
import sys

def test_incremental_update():
    """
    测试增量更新功能
    """
    print("=== 增量更新功能测试 ===")
    
    # 测试股票代码
    test_stock = "00700"  # 腾讯控股
    test_file = f"data/{test_stock}_eastmoney_table.csv"
    
    print(f"\n1. 检查测试文件: {test_file}")
    if os.path.exists(test_file):
        df = pd.read_csv(test_file, encoding='utf-8-sig')
        print(f"   现有数据行数: {len(df)}")
        if not df.empty and '日期' in df.columns:
            print(f"   最新数据日期: {df['日期'].iloc[0]}")
            print(f"   最旧数据日期: {df['日期'].iloc[-1]}")
    else:
        print("   文件不存在，将进行完整数据获取")
    
    # 构建测试URL（使用昨天的日期）
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    test_url = f"https://data.eastmoney.com/hsgtcg/StockHdDetail/{test_stock}.html?date={date_str}"
    
    print(f"\n2. 测试增量更新")
    print(f"   测试URL: {test_url}")
    
    # 执行增量更新
    cmd = [
        "python", "extract_eastmoney_table.py",
        test_url,
        "--incremental",
        "--wait", "15"
    ]
    
    print(f"   执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("   ✓ 增量更新执行成功")
        else:
            print(f"   ✗ 增量更新执行失败")
            print(f"   错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ✗ 执行过程中出现异常: {e}")
        return False
    
    # 检查更新后的文件
    print(f"\n3. 检查更新后的文件")
    if os.path.exists(test_file):
        df_after = pd.read_csv(test_file, encoding='utf-8-sig')
        print(f"   更新后数据行数: {len(df_after)}")
        if not df_after.empty and '日期' in df_after.columns:
            print(f"   最新数据日期: {df_after['日期'].iloc[0]}")
    else:
        print("   ✗ 更新后文件仍不存在")
        return False
    
    print("\n=== 测试完成 ===")
    return True

def test_batch_incremental():
    """
    测试批量增量更新
    """
    print("\n=== 批量增量更新测试 ===")
    
    cmd = [
        "python", "batch_extract_eastmoney.py",
        "--incremental",
        "--limit", "3",  # 只测试3只股票
        "--delay", "5"   # 减少延迟时间
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✓ 批量增量更新执行成功")
            return True
        else:
            print(f"✗ 批量增量更新执行失败")
            print(f"错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ 执行过程中出现异常: {e}")
        return False

if __name__ == "__main__":
    print("开始测试增量更新功能...")
    
    # 测试单个股票增量更新
    success1 = test_incremental_update()
    
    # 测试批量增量更新
    success2 = test_batch_incremental()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！增量更新功能正常工作。")
    else:
        print("\n❌ 部分测试失败，请检查日志文件获取详细信息。")
        sys.exit(1)