#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：用于复现和调试akshare函数错误
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from debug_akshare_function import stock_gdfx_holding_detail_em_debug
import akshare as ak

def test_original_function():
    """
    测试原始akshare函数，复现错误
    """
    print("=== 测试原始akshare函数 ===")
    try:
        # 这是导致错误的调用
        result = ak.stock_gdfx_holding_detail_em(date="20250331", indicator="个人", symbol="新进")
        print(f"原始函数成功，返回 {len(result)} 行数据")
        return result
    except Exception as e:
        print(f"原始函数出错: {type(e).__name__}: {e}")
        return None

def test_debug_function():
    """
    测试带调试功能的函数
    """
    print("\n=== 测试调试函数 ===")
    try:
        # 使用相同参数测试调试函数
        result = stock_gdfx_holding_detail_em_debug(date="20250331", indicator="个人", symbol="新进")
        print(f"调试函数完成，返回 {len(result)} 行数据")
        return result
    except Exception as e:
        print(f"调试函数出错: {type(e).__name__}: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return None

def test_valid_parameters():
    """测试有效参数组合"""
    print("\n=== 测试有效参数组合 ===")
    
    # 有效的机构类型
    valid_indicators = ['社保基金', '公募基金', '券商', '信托', 'QFII']
    
    for indicator in valid_indicators:
        print(f"\n测试机构类型: {indicator}")
        try:
            # 使用原始函数
            result = ak.stock_gdfx_holding_detail_em(
                symbol="000001",
                indicator=indicator,
                date="20231231"
            )
            print(f"原始函数返回数据行数: {len(result)}")
            if len(result) > 0:
                print(f"列名: {list(result.columns)}")
                print(f"前3行数据:\n{result.head(3)}")
                return True  # 找到有效数据就返回
            
        except Exception as e:
            print(f"原始函数出错: {e}")
            
        # 使用调试函数
        try:
            debug_result = stock_gdfx_holding_detail_em_debug(
                symbol="000001",
                indicator=indicator,
                date="20231231"
            )
            if debug_result is not None and len(debug_result) > 0:
                print(f"调试函数返回数据行数: {len(debug_result)}")
                print(f"前3行数据:\n{debug_result.head(3)}")
                return True  # 找到有效数据就返回
            else:
                print("调试函数返回空数据或 None")
                
        except Exception as e:
            print(f"调试函数出错: {e}")
            
        print("-" * 50)
    
    return False  # 所有机构类型都没有返回有效数据

def analyze_error():
    """
    分析错误原因
    """
    print("\n=== 错误分析 ===")
    print("根据错误信息 'TypeError: 'NoneType' object is not subscriptable'")
    print("问题出现在: data_json['result']['pages']")
    print("可能的原因:")
    print("1. data_json 为 None (API返回空响应)")
    print("2. data_json['result'] 为 None (API返回格式异常)")
    print("3. 请求参数无效，API返回错误响应")
    print("4. 网络问题或API服务异常")
    print("5. 参数 'indicator=个人' 可能不是有效的机构类型")
    print("\n建议的修复方案:")
    print("1. 添加响应验证和错误处理")
    print("2. 检查API响应格式")
    print("3. 使用有效的机构类型参数")
    print("4. 添加重试机制")

def main():
    """
    主函数
    """
    print("股票机构持仓数据获取错误调试")
    print("=" * 50)
    
    # 1. 复现原始错误
    original_result = test_original_function()
    
    # 2. 使用调试函数分析
    debug_result = test_debug_function()
    
    # 3. 测试有效参数
    test_valid_parameters()
    
    # 4. 分析错误
    analyze_error()
    
    print("\n=== 调试完成 ===")
    print("请查看上面的调试输出来了解错误原因")

if __name__ == "__main__":
    print("开始测试 akshare 函数...")
    
    # 测试原始错误
    test_original_function()
    
    # 测试有效参数
    success = test_valid_parameters()
    
    if success:
        print("\n✅ 成功找到有效的机构类型和数据！")
    else:
        print("\n❌ 所有机构类型都没有返回有效数据")
        # 分析错误
        analyze_error()