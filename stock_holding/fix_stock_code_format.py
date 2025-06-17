#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票代码格式修复工具

用于检查和修复数据文件中的股票代码格式，确保所有股票代码都是6位数字格式
"""

import os
import pandas as pd
import logging
from typing import List, Tuple


class StockCodeFormatter:
    """
    股票代码格式化工具
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def format_stock_code(self, code) -> str:
        """
        格式化单个股票代码为6位数字
        
        Args:
            code: 原始股票代码
            
        Returns:
            格式化后的6位数字股票代码
        """
        try:
            # 转换为字符串并去除空白
            code_str = str(code).strip()
            
            # 如果包含非数字字符，尝试提取数字部分
            if not code_str.isdigit():
                # 提取数字部分
                digits = ''.join(filter(str.isdigit, code_str))
                if digits:
                    code_str = digits
                else:
                    self.logger.warning(f"无法从 '{code}' 中提取有效数字")
                    return code_str
            
            # 补齐为6位
            return code_str.zfill(6)
            
        except Exception as e:
            self.logger.error(f"格式化股票代码 '{code}' 时出错: {str(e)}")
            return str(code)
    
    def check_file_format(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        检查文件中股票代码的格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否需要修复, 问题列表)
        """
        try:
            data = pd.read_csv(file_path, encoding='utf-8-sig')
            
            if '股票代码' not in data.columns:
                return False, ["文件中未找到'股票代码'列"]
            
            issues = []
            needs_fix = False
            
            # 检查股票代码格式
            for idx, code in enumerate(data['股票代码']):
                code_str = str(code).strip()
                
                # 检查是否为6位数字
                if not (code_str.isdigit() and len(code_str) == 6):
                    issues.append(f"行 {idx + 2}: '{code}' 不是6位数字格式")
                    needs_fix = True
            
            if not needs_fix:
                self.logger.info(f"文件 {file_path} 中的股票代码格式正确")
            else:
                self.logger.warning(f"文件 {file_path} 中发现 {len(issues)} 个格式问题")
            
            return needs_fix, issues
            
        except Exception as e:
            self.logger.error(f"检查文件 {file_path} 时出错: {str(e)}")
            return False, [f"文件读取错误: {str(e)}"]
    
    def fix_file_format(self, file_path: str, backup: bool = True) -> bool:
        """
        修复文件中的股票代码格式
        
        Args:
            file_path: 文件路径
            backup: 是否创建备份
            
        Returns:
            是否修复成功
        """
        try:
            # 创建备份
            if backup:
                backup_path = file_path + '.backup'
                if os.path.exists(file_path):
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    self.logger.info(f"已创建备份文件: {backup_path}")
            
            # 读取数据
            data = pd.read_csv(file_path, encoding='utf-8-sig')
            
            if '股票代码' not in data.columns:
                self.logger.error(f"文件 {file_path} 中未找到'股票代码'列")
                return False
            
            # 记录修复前的统计信息
            original_codes = data['股票代码'].nunique()
            
            # 格式化股票代码
            data['股票代码'] = data['股票代码'].apply(self.format_stock_code)
            
            # 记录修复后的统计信息
            formatted_codes = data['股票代码'].nunique()
            
            # 保存修复后的文件
            data.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"文件 {file_path} 修复完成")
            self.logger.info(f"股票代码数量: {original_codes} -> {formatted_codes}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"修复文件 {file_path} 时出错: {str(e)}")
            return False
    
    def process_directory(self, directory: str, pattern: str = "*.csv") -> None:
        """
        处理目录中的所有CSV文件
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式
        """
        import glob
        
        if not os.path.exists(directory):
            self.logger.error(f"目录不存在: {directory}")
            return
        
        # 查找CSV文件
        csv_files = glob.glob(os.path.join(directory, pattern))
        
        if not csv_files:
            self.logger.info(f"目录 {directory} 中未找到CSV文件")
            return
        
        self.logger.info(f"找到 {len(csv_files)} 个CSV文件")
        
        for file_path in csv_files:
            self.logger.info(f"\n处理文件: {file_path}")
            
            # 检查格式
            needs_fix, issues = self.check_file_format(file_path)
            
            if needs_fix:
                self.logger.info(f"发现 {len(issues)} 个问题，开始修复...")
                if self.fix_file_format(file_path):
                    self.logger.info("修复成功")
                else:
                    self.logger.error("修复失败")
            else:
                self.logger.info("格式正确，无需修复")


def main():
    """
    主函数
    """
    formatter = StockCodeFormatter()
    
    # 获取项目目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 处理原始数据目录
    raw_data_dir = os.path.join(current_dir, "institutional_holdings_data", "raw_data")
    if os.path.exists(raw_data_dir):
        print(f"\n=== 处理原始数据目录: {raw_data_dir} ===")
        formatter.process_directory(raw_data_dir)
    
    # 处理已处理数据目录
    processed_data_dir = os.path.join(current_dir, "institutional_holdings_data", "processed_data")
    if os.path.exists(processed_data_dir):
        print(f"\n=== 处理已处理数据目录: {processed_data_dir} ===")
        formatter.process_directory(processed_data_dir)
    
    print("\n=== 股票代码格式检查和修复完成 ===")


if __name__ == "__main__":
    main()