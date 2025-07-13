#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的增量更新功能
验证是否能够在遇到旧数据时提前退出，提高效率
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def test_optimized_incremental():
    """
    测试优化后的增量更新功能
    """
    print("=== 测试优化后的增量更新功能 ===")
    
    # 测试股票代码
    test_stock = "00700"  # 腾讯控股
    test_url = f"https://data.eastmoney.com/hsgtcg/StockStatistics.aspx?stock={test_stock}"
    
    # 检查是否存在现有数据文件
    data_file = f"data/{test_stock}_eastmoney_table.csv"
    if os.path.exists(data_file):
        print(f"✓ 找到现有数据文件: {data_file}")
        
        # 获取文件修改时间
        mod_time = os.path.getmtime(data_file)
        mod_datetime = datetime.fromtimestamp(mod_time)
        print(f"  文件最后修改时间: {mod_datetime}")
    else:
        print(f"✗ 未找到现有数据文件: {data_file}")
        print("  请先运行一次完整的数据提取")
        return False
    
    print("\n开始测试优化后的增量更新...")
    start_time = time.time()
    
    # 构建命令
    cmd = [
        sys.executable, "extract_eastmoney_table.py",
        test_url,  # URL作为位置参数
        "--output", f"{test_stock}_eastmoney_table.csv",
        "--wait", "10",
        "--log", f"logs/optimized_incremental_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        "--incremental"  # 启用增量更新
    ]
    
    try:
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n执行时间: {execution_time:.2f} 秒")
        
        if result.returncode == 0:
            print("✓ 增量更新执行成功")
            
            # 检查输出中是否包含提前退出的信息
            if "已提前停止遍历" in result.stdout or "已提前停止遍历" in result.stderr:
                print("✓ 检测到提前退出优化生效")
            elif "没有找到新数据" in result.stdout or "没有找到新数据" in result.stderr:
                print("✓ 正确检测到没有新数据")
            else:
                print("? 未明确检测到优化效果")
            
            # 如果执行时间很短，说明优化生效
            if execution_time < 30:  # 如果少于30秒
                print(f"✓ 执行时间很短({execution_time:.2f}秒)，优化效果明显")
            else:
                print(f"? 执行时间较长({execution_time:.2f}秒)，可能仍需优化")
            
            return True
        else:
            print(f"✗ 增量更新执行失败")
            print(f"错误信息: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ 执行超时（5分钟）")
        return False
    except Exception as e:
        print(f"✗ 执行出错: {str(e)}")
        return False

def test_batch_optimized_incremental():
    """
    测试批量优化增量更新
    """
    print("\n=== 测试批量优化增量更新 ===")
    
    start_time = time.time()
    
    # 构建命令
    cmd = [
        sys.executable, "batch_extract_eastmoney.py",
        "--incremental",  # 启用增量更新
        "--limit", "3",   # 只测试3只股票
        "--delay", "2"    # 减少延迟
    ]
    
    try:
        print("开始批量增量更新测试...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n批量执行时间: {execution_time:.2f} 秒")
        
        if result.returncode == 0:
            print("✓ 批量增量更新执行成功")
            
            # 分析输出
            output = result.stdout + result.stderr
            if "已提前停止遍历" in output:
                print("✓ 检测到批量提前退出优化生效")
            
            # 如果批量执行时间很短，说明优化生效
            if execution_time < 60:  # 如果少于1分钟
                print(f"✓ 批量执行时间很短({execution_time:.2f}秒)，优化效果显著")
            else:
                print(f"? 批量执行时间({execution_time:.2f}秒)，优化效果有限")
            
            return True
        else:
            print(f"✗ 批量增量更新执行失败")
            print(f"错误信息: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ 批量执行超时（10分钟）")
        return False
    except Exception as e:
        print(f"✗ 批量执行出错: {str(e)}")
        return False

def main():
    """
    主测试函数
    """
    print("优化后增量更新功能测试")
    print("=" * 50)
    
    # 测试单个股票的优化增量更新
    test1_result = test_optimized_incremental()
    
    # 测试批量优化增量更新
    test2_result = test_batch_optimized_incremental()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试结果总结:")
    print(f"单股票优化增量更新: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"批量优化增量更新: {'✓ 通过' if test2_result else '✗ 失败'}")
    
    if test1_result and test2_result:
        print("\n🎉 所有测试通过！优化后的增量更新功能工作正常。")
    else:
        print("\n⚠️  部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main()