#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票名称检查和更新脚本（简化版）
快速检查和更新股票历史名称
"""

import json
import akshare as ak
import os
import logging
from datetime import datetime

def setup_logging():
    """
    设置日志配置
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建logs文件夹（在脚本所在目录下）
    logs_dir = os.path.join(script_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"check_and_update_names_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return log_filename

def main():
    """主函数"""
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"日志文件: {log_filename}")
    logging.info("正在检查股票名称变化...")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_file = os.path.join(script_dir, 'stock_name_history.json')
    
    # 1. 加载历史数据
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        logging.info(f"成功加载历史数据，包含 {len(history_data)} 只股票")
    except Exception as e:
        logging.error(f"加载历史数据失败: {e}")
        return
    
    # 2. 获取当前数据
    try:
        logging.info("正在获取当前股票数据...")
        df = ak.stock_info_a_code_name()
        current_names = {str(row['code']).zfill(6): row['name'] for _, row in df.iterrows()}
        logging.info(f"成功获取当前股票数据，共 {len(current_names)} 只股票")
    except Exception as e:
        logging.error(f"获取当前数据失败: {e}")
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
                # 先记录变化（使用旧名称），再更新历史数据
                old_name = history_names[-1]
                updates.append((code, old_name, current_name))
                history_data[code].append(current_name)
        else:
            history_data[code] = [current_name]
            new_stocks.append((code, current_name))
    
    # 4. 显示结果
    if updates:
        logging.info(f"发现 {len(updates)} 个股票名称变化:")
        for code, old_name, new_name in updates:
            logging.info(f"  {code}: '{old_name}' -> '{new_name}'")
    
    if new_stocks:
        logging.info(f"发现 {len(new_stocks)} 个新股票:")
        for code, name in new_stocks[:10]:  # 只显示前10个
            logging.info(f"  {code}: '{name}'")
        if len(new_stocks) > 10:
            logging.info(f"  ... 还有 {len(new_stocks) - 10} 个新股票")
    
    if not updates and not new_stocks:
        logging.info("没有发现名称变化或新股票")
        return
    
    # 5. 保存更新
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        logging.info("已更新历史数据文件")
        logging.info(f"总计: {len(updates)} 个名称变化, {len(new_stocks)} 个新股票")
    except Exception as e:
        logging.error(f"保存文件失败: {e}")

if __name__ == "__main__":
    main()