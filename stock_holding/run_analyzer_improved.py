#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进的机构持股数据分析器运行脚本
包含错误恢复、断点续传和内存优化功能
"""

import os
import sys
import time
import gc
import psutil
from datetime import datetime
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from institutional_holdings_analyzer import InstitutionalHoldingsAnalyzer
from config import get_config
from performance_monitor import PerformanceMonitor
from error_handler import ErrorHandler

# 获取配置
CONFIG = get_config()

class ImprovedAnalyzerRunner:
    """
    改进的分析器运行器
    """
    
    def __init__(self):
        self.analyzer = None
        self.performance_monitor = None
        self.error_handler = None
        self.start_time = None
        
    def check_system_resources(self) -> bool:
        """
        检查系统资源是否足够
        """
        # 检查可用内存
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        print("系统内存状态:")
        print(f"- 总内存: {memory.total / (1024**3):.1f} GB")
        print(f"- 可用内存: {available_gb:.1f} GB")
        print(f"- 内存使用率: {memory.percent:.1f}%%")
        
        if available_gb < 2.0:  # 至少需要2GB可用内存
            print("警告: 可用内存不足2GB，可能影响程序运行")
            return False
            
        # 检查磁盘空间
        disk = psutil.disk_usage('.')
        available_gb_disk = disk.free / (1024**3)
        
        print("磁盘空间状态:")
        print(f"- 可用空间: {available_gb_disk:.1f} GB")
        
        if available_gb_disk < 1.0:  # 至少需要1GB磁盘空间
            print("警告: 可用磁盘空间不足1GB，可能影响数据存储")
            return False
            
        return True
    
    def setup_monitoring(self):
        """
        设置性能监控和错误处理
        """
        try:
            self.performance_monitor = PerformanceMonitor()
            self.performance_monitor.start_system_monitoring()
            print("✓ 性能监控已启动")
        except Exception as e:
            print("警告: 性能监控启动失败:", str(e))
            
        try:
            self.error_handler = ErrorHandler()
            print("✓ 错误处理器已初始化")
        except Exception as e:
            print("警告: 错误处理器初始化失败:", str(e))
    
    def create_analyzer(self) -> bool:
        """
        创建分析器实例
        """
        try:
            self.analyzer = InstitutionalHoldingsAnalyzer()
            print("✓ 分析器实例创建成功")
            return True
        except Exception as e:
            print("✗ 分析器实例创建失败:", str(e))
            return False
    
    def run_with_recovery(self, start_year: int = None, end_year: int = None, 
                         target_stock: str = None, max_attempts: int = 3) -> bool:
        """
        带错误恢复的运行方法
        """
        # 使用配置文件中的默认值
        start_year = start_year or CONFIG.get('start_year', 2025)
        end_year = end_year or CONFIG.get('end_year', None)
        target_stock = target_stock or CONFIG.get('target_stock_code', None)
        
        print(f"\n开始分析 (最大尝试次数: {max_attempts})")
        print(f"参数: 开始年份={start_year}, 结束年份={end_year or '当前'}, 目标股票={target_stock or '全市场'}")
        
        for attempt in range(1, max_attempts + 1):
            print(f"\n=== 第 {attempt} 次尝试 ===")
            
            try:
                # 记录开始时间
                self.start_time = time.time()
                
                # 运行分析
                self.analyzer.run_full_analysis(
                    start_year=start_year,
                    end_year=end_year,
                    target_stock=target_stock
                )
                
                # 成功完成
                elapsed_time = time.time() - self.start_time
                print(f"\n✓ 分析成功完成！耗时: {elapsed_time/60:.1f} 分钟")
                return True
                
            except KeyboardInterrupt:
                print("\n用户中断程序")
                return False
                
            except Exception as e:
                elapsed_time = time.time() - self.start_time if self.start_time else 0
                print(f"\n✗ 第 {attempt} 次尝试失败 (耗时: {elapsed_time/60:.1f} 分钟)")
                print("错误:", str(e))
                
                if self.error_handler:
                    self.error_handler.handle_error(e, f"run_attempt_{attempt}")
                
                if attempt < max_attempts:
                    # 等待一段时间后重试
                    wait_time = min(60 * attempt, 300)  # 最多等待5分钟
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    
                    # 强制垃圾回收
                    gc.collect()
                    
                    # 重新创建分析器实例
                    print("重新创建分析器实例...")
                    if not self.create_analyzer():
                        print("重新创建分析器失败，终止重试")
                        return False
                else:
                    print(f"\n✗ 所有尝试均失败，程序终止")
                    return False
        
        return False
    
    def cleanup(self):
        """
        清理资源
        """
        try:
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
                print("✓ 性能监控已停止")
        except Exception as e:
            print("警告: 停止性能监控时出错:", str(e))
        
        # 强制垃圾回收
        gc.collect()
        print("✓ 资源清理完成")
    
    def generate_summary_report(self):
        """
        生成运行总结报告
        """
        try:
            if self.performance_monitor:
                # 生成性能报告
                perf_report = self.performance_monitor.generate_report()
                print("\n=== 性能报告 ===")
                print(perf_report)
                
            if self.error_handler:
                # 生成错误报告
                error_report = self.error_handler.generate_report()
                if error_report.strip():
                    print("\n=== 错误报告 ===")
                    print(error_report)
                    
        except Exception as e:
            print("生成报告时出错:", str(e))

def main():
    """
    主函数
    """
    print("机构持股数据分析器 (改进版)")
    print("=" * 50)
    print("启动时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    runner = ImprovedAnalyzerRunner()
    
    try:
        # 1. 检查系统资源
        print("\n1. 检查系统资源...")
        if not runner.check_system_resources():
            print("系统资源不足，建议释放内存或磁盘空间后重试")
            return
        
        # 2. 设置监控
        print("\n2. 设置监控...")
        runner.setup_monitoring()
        
        # 3. 创建分析器
        print("\n3. 创建分析器...")
        if not runner.create_analyzer():
            print("分析器创建失败，程序终止")
            return
        
        # 4. 运行分析
        print("\n4. 运行分析...")
        success = runner.run_with_recovery()
        
        # 5. 生成报告
        print("\n5. 生成总结报告...")
        runner.generate_summary_report()
        
        if success:
            print("\n🎉 程序执行成功！")
        else:
            print("\n❌ 程序执行失败")
            
    except Exception as e:
        print("\n💥 程序发生未预期错误:", str(e))
        
    finally:
        # 6. 清理资源
        print("\n6. 清理资源...")
        runner.cleanup()
        
        print("\n程序结束时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 50)

if __name__ == "__main__":
    main()