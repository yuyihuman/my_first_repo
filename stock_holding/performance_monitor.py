#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控和优化模块

提供运行时性能监控、内存使用跟踪和性能优化建议
"""

import time
import psutil
import functools
import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import json
import os
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import gc


@dataclass
class PerformanceMetrics:
    """
    性能指标数据类
    """
    function_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class PerformanceMonitor:
    """
    性能监控器
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, 
                 max_history: int = 1000):
        """
        初始化性能监控器
        
        Args:
            logger: 日志记录器
            max_history: 最大历史记录数量
        """
        self.logger = logger or logging.getLogger(__name__)
        self.max_history = max_history
        
        # 性能数据存储
        self.metrics_history: deque = deque(maxlen=max_history)
        self.function_stats: Dict[str, List[float]] = defaultdict(list)
        self.memory_usage_history: deque = deque(maxlen=max_history)
        
        # 监控状态
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        # 性能阈值
        self.thresholds = {
            'slow_function_seconds': 5.0,
            'high_memory_mb': 500.0,
            'memory_leak_threshold': 0.1,  # 10% 增长
            'cpu_high_percent': 80.0
        }
        
        self.logger.info("性能监控器已初始化")
    
    def monitor_function(self, func: Callable = None, *, 
                        track_memory: bool = True,
                        track_cpu: bool = True) -> Callable:
        """
        函数性能监控装饰器
        
        Args:
            func: 被装饰的函数
            track_memory: 是否跟踪内存使用
            track_cpu: 是否跟踪CPU使用
            
        Returns:
            装饰后的函数
        """
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs) -> Any:
                return self._execute_with_monitoring(
                    f, args, kwargs, track_memory, track_cpu
                )
            return wrapper
        
        if func is None:
            return decorator
        else:
            return decorator(func)
    
    def _execute_with_monitoring(self, func: Callable, args: tuple, 
                               kwargs: dict, track_memory: bool, 
                               track_cpu: bool) -> Any:
        """
        执行函数并监控性能
        """
        function_name = f"{func.__module__}.{func.__name__}"
        
        # 记录开始状态
        start_time = time.time()
        memory_before = self._get_memory_usage() if track_memory else 0
        cpu_before = psutil.cpu_percent() if track_cpu else 0
        
        # 强制垃圾回收以获得更准确的内存测量
        if track_memory:
            gc.collect()
            memory_before = self._get_memory_usage()
        
        success = True
        error_message = None
        result = None
        memory_peak = memory_before
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 监控执行期间的峰值内存
            if track_memory:
                current_memory = self._get_memory_usage()
                memory_peak = max(memory_peak, current_memory)
            
        except Exception as e:
            success = False
            error_message = str(e)
            self.logger.error(f"函数 {function_name} 执行失败: {error_message}")
            raise
        
        finally:
            # 记录结束状态
            end_time = time.time()
            duration = end_time - start_time
            memory_after = self._get_memory_usage() if track_memory else 0
            cpu_after = psutil.cpu_percent() if track_cpu else 0
            cpu_percent = max(cpu_after - cpu_before, 0) if track_cpu else 0
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                function_name=function_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_peak=memory_peak,
                cpu_percent=cpu_percent,
                success=success,
                error_message=error_message
            )
            
            # 存储指标
            self._store_metrics(metrics)
            
            # 检查性能警告
            self._check_performance_warnings(metrics)
        
        return result
    
    def _get_memory_usage(self) -> float:
        """
        获取当前内存使用量（MB）
        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _store_metrics(self, metrics: PerformanceMetrics):
        """
        存储性能指标
        """
        self.metrics_history.append(metrics)
        self.function_stats[metrics.function_name].append(metrics.duration)
        
        # 限制每个函数的历史记录数量
        if len(self.function_stats[metrics.function_name]) > 100:
            self.function_stats[metrics.function_name] = \
                self.function_stats[metrics.function_name][-100:]
    
    def _check_performance_warnings(self, metrics: PerformanceMetrics):
        """
        检查性能警告
        """
        # 检查执行时间
        if metrics.duration > self.thresholds['slow_function_seconds']:
            self.logger.warning(
                f"慢函数警告: {metrics.function_name} 执行时间 "
                f"{metrics.duration:.2f}s 超过阈值 "
                f"{self.thresholds['slow_function_seconds']}s"
            )
        
        # 检查内存使用
        memory_increase = metrics.memory_after - metrics.memory_before
        if memory_increase > self.thresholds['high_memory_mb']:
            self.logger.warning(
                f"高内存使用警告: {metrics.function_name} 内存增长 "
                f"{memory_increase:.1f}MB 超过阈值 "
                f"{self.thresholds['high_memory_mb']}MB"
            )
        
        # 检查CPU使用
        if metrics.cpu_percent > self.thresholds['cpu_high_percent']:
            self.logger.warning(
                f"高CPU使用警告: {metrics.function_name} CPU使用率 "
                f"{metrics.cpu_percent:.1f}% 超过阈值 "
                f"{self.thresholds['cpu_high_percent']}%"
            )
    
    def start_system_monitoring(self, interval: float = 1.0):
        """
        开始系统监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.monitoring_active:
            self.logger.warning("系统监控已在运行")
            return
        
        self.monitoring_active = True
        self.stop_monitoring.clear()
        
        def monitor_loop():
            while not self.stop_monitoring.wait(interval):
                try:
                    memory_usage = self._get_memory_usage()
                    cpu_percent = psutil.cpu_percent()
                    
                    self.memory_usage_history.append({
                        'timestamp': time.time(),
                        'memory_mb': memory_usage,
                        'cpu_percent': cpu_percent
                    })
                    
                    # 检查内存泄漏
                    self._check_memory_leak()
                    
                except Exception as e:
                    self.logger.error(f"系统监控错误: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"系统监控已启动，间隔 {interval}s")
    
    def stop_system_monitoring(self):
        """
        停止系统监控
        """
        if not self.monitoring_active:
            return
        
        self.stop_monitoring.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        self.monitoring_active = False
        self.logger.info("系统监控已停止")
    
    def _check_memory_leak(self):
        """
        检查内存泄漏
        """
        if len(self.memory_usage_history) < 10:
            return
        
        # 获取最近10个内存使用记录
        recent_memory = [record['memory_mb'] for record in 
                        list(self.memory_usage_history)[-10:]]
        
        # 计算内存增长趋势
        if len(recent_memory) >= 2:
            memory_growth = (recent_memory[-1] - recent_memory[0]) / recent_memory[0]
            
            if memory_growth > self.thresholds['memory_leak_threshold']:
                self.logger.warning(
                    f"可能的内存泄漏: 最近内存增长 {memory_growth*100:.1f}% "
                    f"(从 {recent_memory[0]:.1f}MB 到 {recent_memory[-1]:.1f}MB)"
                )
    
    def get_performance_summary(self) -> Dict:
        """
        获取性能摘要
        
        Returns:
            性能摘要字典
        """
        if not self.metrics_history:
            return {'message': '暂无性能数据'}
        
        summary = {
            'total_functions_monitored': len(self.function_stats),
            'total_executions': len(self.metrics_history),
            'monitoring_period': {
                'start': datetime.fromtimestamp(self.metrics_history[0].start_time).isoformat(),
                'end': datetime.fromtimestamp(self.metrics_history[-1].end_time).isoformat()
            },
            'function_statistics': {},
            'system_statistics': {},
            'performance_warnings': self._get_performance_warnings()
        }
        
        # 函数统计
        for func_name, durations in self.function_stats.items():
            if durations:
                summary['function_statistics'][func_name] = {
                    'call_count': len(durations),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'total_duration': sum(durations)
                }
        
        # 系统统计
        if self.memory_usage_history:
            memory_values = [record['memory_mb'] for record in self.memory_usage_history]
            cpu_values = [record['cpu_percent'] for record in self.memory_usage_history]
            
            summary['system_statistics'] = {
                'current_memory_mb': memory_values[-1] if memory_values else 0,
                'peak_memory_mb': max(memory_values) if memory_values else 0,
                'avg_memory_mb': sum(memory_values) / len(memory_values) if memory_values else 0,
                'avg_cpu_percent': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'peak_cpu_percent': max(cpu_values) if cpu_values else 0
            }
        
        return summary
    
    def _get_performance_warnings(self) -> List[Dict]:
        """
        获取性能警告列表
        """
        warnings = []
        
        # 检查慢函数
        for func_name, durations in self.function_stats.items():
            if durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration > self.thresholds['slow_function_seconds']:
                    warnings.append({
                        'type': 'slow_function',
                        'function': func_name,
                        'avg_duration': avg_duration,
                        'threshold': self.thresholds['slow_function_seconds']
                    })
        
        # 检查内存使用
        if self.memory_usage_history:
            current_memory = self.memory_usage_history[-1]['memory_mb']
            if current_memory > self.thresholds['high_memory_mb']:
                warnings.append({
                    'type': 'high_memory',
                    'current_memory_mb': current_memory,
                    'threshold_mb': self.thresholds['high_memory_mb']
                })
        
        return warnings
    
    def generate_report(self) -> str:
        """
        生成性能报告（别名方法）
        
        Returns:
            性能报告文本
        """
        return self.generate_performance_report()
    
    def generate_performance_report(self) -> str:
        """
        生成性能报告
        
        Returns:
            性能报告文本
        """
        summary = self.get_performance_summary()
        
        if 'message' in summary:
            return summary['message']
        
        report_lines = []
        report_lines.append("# 性能监控报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 基本信息
        report_lines.append("\n## 基本信息")
        report_lines.append(f"- 监控函数数量: {summary['total_functions_monitored']}")
        report_lines.append(f"- 总执行次数: {summary['total_executions']}")
        report_lines.append(f"- 监控时间段: {summary['monitoring_period']['start']} 到 {summary['monitoring_period']['end']}")
        
        # 函数性能统计
        if summary['function_statistics']:
            report_lines.append("\n## 函数性能统计")
            for func_name, stats in summary['function_statistics'].items():
                report_lines.append(f"\n### {func_name}")
                report_lines.append(f"- 调用次数: {stats['call_count']}")
                report_lines.append(f"- 平均耗时: {stats['avg_duration']:.3f}s")
                report_lines.append(f"- 最短耗时: {stats['min_duration']:.3f}s")
                report_lines.append(f"- 最长耗时: {stats['max_duration']:.3f}s")
                report_lines.append(f"- 总耗时: {stats['total_duration']:.3f}s")
        
        # 系统资源统计
        if summary['system_statistics']:
            report_lines.append("\n## 系统资源统计")
            sys_stats = summary['system_statistics']
            report_lines.append(f"- 当前内存使用: {sys_stats['current_memory_mb']:.1f}MB")
            report_lines.append(f"- 峰值内存使用: {sys_stats['peak_memory_mb']:.1f}MB")
            report_lines.append(f"- 平均内存使用: {sys_stats['avg_memory_mb']:.1f}MB")
            report_lines.append(f"- 平均CPU使用率: {sys_stats['avg_cpu_percent']:.1f}%")
            report_lines.append(f"- 峰值CPU使用率: {sys_stats['peak_cpu_percent']:.1f}%")
        
        # 性能警告
        if summary['performance_warnings']:
            report_lines.append("\n## 性能警告")
            for i, warning in enumerate(summary['performance_warnings'], 1):
                if warning['type'] == 'slow_function':
                    report_lines.append(
                        f"{i}. 慢函数: {warning['function']} "
                        f"(平均耗时 {warning['avg_duration']:.3f}s > "
                        f"阈值 {warning['threshold']}s)"
                    )
                elif warning['type'] == 'high_memory':
                    report_lines.append(
                        f"{i}. 高内存使用: {warning['current_memory_mb']:.1f}MB > "
                        f"阈值 {warning['threshold_mb']}MB"
                    )
        
        # 优化建议
        report_lines.append("\n## 优化建议")
        suggestions = self._generate_optimization_suggestions(summary)
        for i, suggestion in enumerate(suggestions, 1):
            report_lines.append(f"{i}. {suggestion}")
        
        return "\n".join(report_lines)
    
    def _generate_optimization_suggestions(self, summary: Dict) -> List[str]:
        """
        生成优化建议
        """
        suggestions = []
        
        # 基于函数性能的建议
        if summary['function_statistics']:
            slow_functions = [
                (name, stats) for name, stats in summary['function_statistics'].items()
                if stats['avg_duration'] > self.thresholds['slow_function_seconds']
            ]
            
            if slow_functions:
                suggestions.append(
                    f"优化慢函数: {', '.join([name for name, _ in slow_functions[:3]])} "
                    "等函数执行时间较长，建议进行性能优化"
                )
        
        # 基于内存使用的建议
        if summary.get('system_statistics', {}).get('peak_memory_mb', 0) > self.thresholds['high_memory_mb']:
            suggestions.append(
                "内存优化: 峰值内存使用较高，建议检查是否存在内存泄漏或优化数据结构"
            )
        
        # 基于调用频率的建议
        if summary['function_statistics']:
            frequent_functions = [
                (name, stats) for name, stats in summary['function_statistics'].items()
                if stats['call_count'] > 100
            ]
            
            if frequent_functions:
                suggestions.append(
                    "缓存优化: 考虑为高频调用的函数添加缓存机制以提升性能"
                )
        
        # 通用建议
        if not suggestions:
            suggestions.append("当前性能表现良好，建议继续监控以发现潜在的性能问题")
        
        return suggestions
    
    def save_metrics_to_file(self, filepath: str):
        """
        保存性能指标到文件
        
        Args:
            filepath: 保存路径
        """
        try:
            metrics_data = {
                'summary': self.get_performance_summary(),
                'detailed_metrics': [metrics.to_dict() for metrics in self.metrics_history],
                'system_history': list(self.memory_usage_history)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"性能指标已保存到 {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存性能指标失败: {e}")
    
    def clear_metrics(self):
        """
        清空性能指标
        """
        self.metrics_history.clear()
        self.function_stats.clear()
        self.memory_usage_history.clear()
        self.logger.info("性能指标已清空")
    
    def set_thresholds(self, **thresholds):
        """
        设置性能阈值
        
        Args:
            **thresholds: 阈值参数
        """
        for key, value in thresholds.items():
            if key in self.thresholds:
                self.thresholds[key] = value
                self.logger.info(f"阈值已更新: {key} = {value}")
            else:
                self.logger.warning(f"未知阈值参数: {key}")


# 全局性能监控器实例
_global_monitor = None


def get_global_monitor() -> PerformanceMonitor:
    """
    获取全局性能监控器实例
    
    Returns:
        全局性能监控器
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def monitor_performance(func: Callable = None, *, 
                       track_memory: bool = True,
                       track_cpu: bool = True) -> Callable:
    """
    便捷的性能监控装饰器
    
    Args:
        func: 被装饰的函数
        track_memory: 是否跟踪内存使用
        track_cpu: 是否跟踪CPU使用
        
    Returns:
        装饰后的函数
    """
    monitor = get_global_monitor()
    return monitor.monitor_function(func, track_memory=track_memory, track_cpu=track_cpu)


if __name__ == "__main__":
    # 测试性能监控器
    print("性能监控器测试")
    print("=" * 30)
    
    # 创建监控器
    monitor = PerformanceMonitor()
    
    # 测试函数
    @monitor.monitor_function
    def test_function(duration: float = 1.0):
        """测试函数"""
        time.sleep(duration)
        return f"执行了 {duration} 秒"
    
    @monitor.monitor_function
    def memory_intensive_function():
        """内存密集型函数"""
        data = [i for i in range(1000000)]  # 创建大列表
        return len(data)
    
    # 启动系统监控
    monitor.start_system_monitoring(interval=0.5)
    
    try:
        # 执行测试函数
        print("执行测试函数...")
        result1 = test_function(0.5)
        print(f"结果1: {result1}")
        
        result2 = test_function(1.5)  # 触发慢函数警告
        print(f"结果2: {result2}")
        
        result3 = memory_intensive_function()
        print(f"结果3: {result3}")
        
        # 等待一段时间以收集系统监控数据
        time.sleep(2)
        
        # 生成性能报告
        print("\n性能摘要:")
        summary = monitor.get_performance_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        print("\n性能报告:")
        report = monitor.generate_performance_report()
        print(report)
        
    finally:
        # 停止系统监控
        monitor.stop_system_monitoring()
        print("\n测试完成")