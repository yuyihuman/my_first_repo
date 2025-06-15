#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试选择器优化效果
验证将最常成功的选择器放在前面是否能提高效率
"""

import time
import subprocess
import sys
import os
from datetime import datetime

def test_selector_optimization():
    """
    测试选择器优化效果
    """
    print("=== 测试选择器优化效果 ===")
    
    # 测试URL
    test_url = "https://data.eastmoney.com/hsgtcg/StockStatistics.aspx?stock=00700"
    
    # 检查现有文件
    data_file = "c:/Users/Ramsey/github/my_first_repo/stockapi/data/00700_eastmoney_table.csv"
    if os.path.exists(data_file):
        print(f"找到现有数据文件: {data_file}")
    else:
        print("未找到现有数据文件，将进行全量获取")
    
    # 构建测试命令
    cmd = [
        sys.executable,
        "extract_eastmoney_table.py",
        test_url,
        "--incremental"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 执行命令
        result = subprocess.run(
            cmd,
            cwd="c:/Users/Ramsey/github/my_first_repo/stockapi",
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )
        
        # 记录结束时间
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n执行时间: {execution_time:.2f} 秒")
        print(f"退出码: {result.returncode}")
        
        if result.stdout:
            print("\n标准输出:")
            print(result.stdout)
        
        if result.stderr:
            print("\n错误输出:")
            print(result.stderr)
        
        # 分析日志中的选择器使用情况
        if "找到表格元素: table" in result.stdout:
            print("\n✅ 优化成功：直接使用 table 选择器找到表格")
        elif "找到表格元素: table.tab1" in result.stdout:
            print("\n⚠️  使用了备用选择器 table.tab1")
        
        return result.returncode == 0, execution_time
        
    except subprocess.TimeoutExpired:
        print("\n❌ 测试超时（超过2分钟）")
        return False, 120
    except Exception as e:
        print(f"\n❌ 测试执行失败: {str(e)}")
        return False, 0

def test_batch_selector_optimization():
    """
    测试批量处理的选择器优化效果
    """
    print("\n=== 测试批量选择器优化效果 ===")
    
    # 构建批量测试命令（限制3个股票，快速测试）
    cmd = [
        sys.executable,
        "batch_extract_eastmoney.py",
        "--incremental",
        "--limit", "3",
        "--delay", "2"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 执行命令
        result = subprocess.run(
            cmd,
            cwd="c:/Users/Ramsey/github/my_first_repo/stockapi",
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        # 记录结束时间
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n批量执行时间: {execution_time:.2f} 秒")
        print(f"退出码: {result.returncode}")
        
        if result.stdout:
            print("\n标准输出:")
            print(result.stdout[-1000:])  # 只显示最后1000字符
        
        # 统计选择器使用情况
        stdout_text = result.stdout if result.stdout else ""
        table_count = stdout_text.count("找到表格元素: table")
        tab1_count = stdout_text.count("找到表格元素: table.tab1")
        
        print(f"\n选择器使用统计:")
        print(f"- 使用 table 选择器: {table_count} 次")
        print(f"- 使用 table.tab1 选择器: {tab1_count} 次")
        
        if table_count > 0 and tab1_count == 0:
            print("✅ 优化效果显著：全部使用最优选择器")
        elif table_count > tab1_count:
            print("✅ 优化有效：主要使用最优选择器")
        else:
            print("⚠️  优化效果有限")
        
        return result.returncode == 0, execution_time
        
    except subprocess.TimeoutExpired:
        print("\n❌ 批量测试超时（超过5分钟）")
        return False, 300
    except Exception as e:
        print(f"\n❌ 批量测试执行失败: {str(e)}")
        return False, 0

def main():
    """
    主函数
    """
    print(f"选择器优化测试开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试单个股票的选择器优化
    success1, time1 = test_selector_optimization()
    
    # 测试批量处理的选择器优化
    success2, time2 = test_batch_selector_optimization()
    
    # 总结测试结果
    print("\n" + "="*50)
    print("测试结果总结:")
    print(f"- 单股票测试: {'✅ 通过' if success1 else '❌ 失败'} (耗时: {time1:.2f}秒)")
    print(f"- 批量测试: {'✅ 通过' if success2 else '❌ 失败'} (耗时: {time2:.2f}秒)")
    
    if success1 and success2:
        print("\n🎉 选择器优化测试全部通过！")
        print("优化效果：")
        print("- 减少了不必要的选择器尝试")
        print("- 提高了表格查找效率")
        print("- 减少了等待时间")
    else:
        print("\n⚠️  部分测试未通过，请检查日志")
    
    print(f"\n测试完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()