#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票名称检查和更新脚本（简化版）
快速检查和更新股票历史名称
"""

import json
import akshare as ak
import os
from datetime import datetime

def main():
    """主函数"""
    print("正在检查股票名称变化...")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_file = os.path.join(script_dir, 'stock_name_history.json')
    
    # 1. 加载历史数据
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    except Exception as e:
        print(f"加载历史数据失败: {e}")
        return
    
    # 2. 获取当前数据
    try:
        df = ak.stock_info_a_code_name()
        current_names = {str(row['code']).zfill(6): row['name'] for _, row in df.iterrows()}
    except Exception as e:
        print(f"获取当前数据失败: {e}")
        return
    
    # 3. 检查更新
    updates = []
    new_stocks = []
    
    for code, current_name in current_names.items():
        if code in history_data:
            history_names = history_data[code]
            if len(history_names) == 0:
                history_data[code] = [current_name]
                new_stocks.append((code, current_name))
            elif history_names[-1] != current_name:
                history_data[code].append(current_name)
                updates.append((code, history_names[-1], current_name))
        else:
            history_data[code] = [current_name]
            new_stocks.append((code, current_name))
    
    # 4. 显示结果
    if updates:
        print(f"\n发现 {len(updates)} 个股票名称变化:")
        for code, old_name, new_name in updates:
            print(f"  {code}: '{old_name}' -> '{new_name}'")
    
    if new_stocks:
        print(f"\n发现 {len(new_stocks)} 个新股票:")
        for code, name in new_stocks[:10]:  # 只显示前10个
            print(f"  {code}: '{name}'")
        if len(new_stocks) > 10:
            print(f"  ... 还有 {len(new_stocks) - 10} 个新股票")
    
    if not updates and not new_stocks:
        print("没有发现名称变化或新股票")
        return
    
    # 5. 保存更新
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        print(f"\n已更新历史数据文件")
        print(f"总计: {len(updates)} 个名称变化, {len(new_stocks)} 个新股票")
    except Exception as e:
        print(f"保存文件失败: {e}")

if __name__ == "__main__":
    main()