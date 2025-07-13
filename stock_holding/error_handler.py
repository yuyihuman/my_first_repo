#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理和重试机制模块

提供统一的错误处理、重试机制和异常恢复功能
"""

import time
import functools
import logging
import traceback
from typing import Dict, List, Optional, Callable, Any, Type, Union
from datetime import datetime, timedelta
import json
import os
from enum import Enum
from dataclasses import dataclass, asdict
import random
import requests
import pandas as pd


class ErrorSeverity(Enum):
    """
    错误严重程度枚举
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryStrategy(Enum):
    """
    重试策略枚举
    """
    FIXED = "fixed"  # 固定间隔
    EXPONENTIAL = "exponential"  # 指数退避
    LINEAR = "linear"  # 线性增长
    RANDOM = "random"  # 随机间隔


@dataclass
class ErrorRecord:
    """
    错误记录数据类
    """
    timestamp: str
    function_name: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    stack_trace: str
    retry_count: int
    resolved: bool = False
    resolution_method: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data


class ErrorHandler:
    """
    错误处理器
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None,
                 max_error_history: int = 1000):
        """
        初始化错误处理器
        
        Args:
            logger: 日志记录器
            max_error_history: 最大错误历史记录数量
        """
        self.logger = logger or logging.getLogger(__name__)
        self.max_error_history = max_error_history
        
        # 错误记录存储
        self.error_history: List[ErrorRecord] = []
        self.error_counts: Dict[str, int] = {}
        
        # 错误分类规则
        self.error_classification = {
            # 网络相关错误
            'requests.exceptions.ConnectionError': ErrorSeverity.MEDIUM,
            'requests.exceptions.Timeout': ErrorSeverity.MEDIUM,
            'requests.exceptions.HTTPError': ErrorSeverity.MEDIUM,
            'urllib3.exceptions.MaxRetryError': ErrorSeverity.MEDIUM,
            
            # 数据相关错误
            'pandas.errors.EmptyDataError': ErrorSeverity.LOW,
            'pandas.errors.ParserError': ErrorSeverity.MEDIUM,
            'KeyError': ErrorSeverity.MEDIUM,
            'ValueError': ErrorSeverity.MEDIUM,
            'TypeError': ErrorSeverity.HIGH,
            
            # 文件系统错误
            'FileNotFoundError': ErrorSeverity.MEDIUM,
            'PermissionError': ErrorSeverity.HIGH,
            'OSError': ErrorSeverity.HIGH,
            
            # 内存和系统错误
            'MemoryError': ErrorSeverity.CRITICAL,
            'SystemError': ErrorSeverity.CRITICAL,
            'KeyboardInterrupt': ErrorSeverity.LOW,
            
            # 默认错误
            'Exception': ErrorSeverity.MEDIUM
        }
        
        # 可恢复错误类型
        self.recoverable_errors = {
            'requests.exceptions.ConnectionError',
            'requests.exceptions.Timeout',
            'requests.exceptions.HTTPError',
            'pandas.errors.EmptyDataError',
            'FileNotFoundError'
        }
        
        self.logger.info("错误处理器已初始化")
    
    def handle_error(self, error: Exception, function_name: str, 
                    retry_count: int = 0, context: Dict = None) -> ErrorRecord:
        """
        处理错误
        
        Args:
            error: 异常对象
            function_name: 函数名
            retry_count: 重试次数
            context: 错误上下文信息
            
        Returns:
            错误记录
        """
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        # 分类错误严重程度
        severity = self._classify_error_severity(error_type)
        
        # 创建错误记录
        error_record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            function_name=function_name,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            stack_trace=stack_trace,
            retry_count=retry_count
        )
        
        # 存储错误记录
        self._store_error_record(error_record)
        
        # 记录日志
        self._log_error(error_record, context)
        
        # 尝试自动恢复
        if self._is_recoverable_error(error_type):
            recovery_method = self._attempt_auto_recovery(error, context)
            if recovery_method:
                error_record.resolved = True
                error_record.resolution_method = recovery_method
                self.logger.info(f"错误已自动恢复: {recovery_method}")
        
        return error_record
    
    def _classify_error_severity(self, error_type: str) -> ErrorSeverity:
        """
        分类错误严重程度
        """
        # 精确匹配
        if error_type in self.error_classification:
            return self.error_classification[error_type]
        
        # 模糊匹配
        for pattern, severity in self.error_classification.items():
            if pattern.lower() in error_type.lower():
                return severity
        
        # 默认严重程度
        return ErrorSeverity.MEDIUM
    
    def _store_error_record(self, error_record: ErrorRecord):
        """
        存储错误记录
        """
        self.error_history.append(error_record)
        
        # 限制历史记录数量
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
        
        # 更新错误计数
        error_key = f"{error_record.function_name}:{error_record.error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
    
    def _log_error(self, error_record: ErrorRecord, context: Dict = None):
        """
        记录错误日志
        """
        log_message = (
            f"错误处理 - 函数: {error_record.function_name}, "
            f"类型: {error_record.error_type}, "
            f"严重程度: {error_record.severity.value}, "
            f"重试次数: {error_record.retry_count}, "
            f"消息: {error_record.error_message}"
        )
        
        if context:
            log_message += f", 上下文: {context}"
        
        # 根据严重程度选择日志级别
        if error_record.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_record.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _is_recoverable_error(self, error_type: str) -> bool:
        """
        判断错误是否可恢复
        """
        return error_type in self.recoverable_errors
    
    def _attempt_auto_recovery(self, error: Exception, context: Dict = None) -> Optional[str]:
        """
        尝试自动恢复
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复方法描述，如果无法恢复则返回None
        """
        error_type = type(error).__name__
        
        # 网络错误恢复
        if 'ConnectionError' in error_type or 'Timeout' in error_type:
            return "网络错误 - 建议稍后重试"
        
        # 空数据错误恢复
        if 'EmptyDataError' in error_type:
            return "空数据错误 - 跳过当前数据源"
        
        # 文件不存在错误恢复
        if 'FileNotFoundError' in error_type:
            if context and 'file_path' in context:
                try:
                    # 尝试创建目录
                    os.makedirs(os.path.dirname(context['file_path']), exist_ok=True)
                    return "文件路径不存在 - 已创建目录"
                except Exception:
                    pass
            return "文件不存在 - 建议检查文件路径"
        
        return None
    
    def get_error_statistics(self) -> Dict:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        if not self.error_history:
            return {'message': '暂无错误记录'}
        
        # 按类型统计
        error_type_counts = {}
        severity_counts = {severity.value: 0 for severity in ErrorSeverity}
        function_error_counts = {}
        resolved_count = 0
        
        for record in self.error_history:
            # 错误类型统计
            error_type_counts[record.error_type] = \
                error_type_counts.get(record.error_type, 0) + 1
            
            # 严重程度统计
            severity_counts[record.severity.value] += 1
            
            # 函数错误统计
            function_error_counts[record.function_name] = \
                function_error_counts.get(record.function_name, 0) + 1
            
            # 解决状态统计
            if record.resolved:
                resolved_count += 1
        
        # 计算时间范围
        timestamps = [datetime.fromisoformat(record.timestamp) for record in self.error_history]
        time_range = {
            'start': min(timestamps).isoformat(),
            'end': max(timestamps).isoformat(),
            'duration_hours': (max(timestamps) - min(timestamps)).total_seconds() / 3600
        }
        
        return {
            'total_errors': len(self.error_history),
            'resolved_errors': resolved_count,
            'resolution_rate': resolved_count / len(self.error_history) * 100,
            'time_range': time_range,
            'error_by_type': dict(sorted(error_type_counts.items(), 
                                       key=lambda x: x[1], reverse=True)),
            'error_by_severity': severity_counts,
            'error_by_function': dict(sorted(function_error_counts.items(), 
                                           key=lambda x: x[1], reverse=True)),
            'most_common_errors': self._get_most_common_errors(5)
        }
    
    def _get_most_common_errors(self, top_n: int = 5) -> List[Dict]:
        """
        获取最常见的错误
        """
        error_details = {}
        
        for record in self.error_history:
            key = f"{record.error_type}: {record.error_message[:100]}"
            if key not in error_details:
                error_details[key] = {
                    'error_type': record.error_type,
                    'error_message': record.error_message,
                    'count': 0,
                    'functions': set(),
                    'severity': record.severity.value
                }
            
            error_details[key]['count'] += 1
            error_details[key]['functions'].add(record.function_name)
        
        # 转换为列表并排序
        common_errors = []
        for details in error_details.values():
            details['functions'] = list(details['functions'])
            common_errors.append(details)
        
        return sorted(common_errors, key=lambda x: x['count'], reverse=True)[:top_n]
    
    def generate_report(self) -> str:
        """
        生成错误报告（别名方法）
        
        Returns:
            错误报告文本
        """
        return self.generate_error_report()
    
    def generate_error_report(self) -> str:
        """
        生成错误报告
        
        Returns:
            错误报告文本
        """
        stats = self.get_error_statistics()
        
        if 'message' in stats:
            return stats['message']
        
        report_lines = []
        report_lines.append("# 错误处理报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 基本统计
        report_lines.append("\n## 基本统计")
        report_lines.append(f"- 总错误数: {stats['total_errors']}")
        report_lines.append(f"- 已解决错误: {stats['resolved_errors']}")
        report_lines.append(f"- 解决率: {stats['resolution_rate']:.1f}%")
        report_lines.append(f"- 统计时间段: {stats['time_range']['start']} 到 {stats['time_range']['end']}")
        report_lines.append(f"- 统计时长: {stats['time_range']['duration_hours']:.1f} 小时")
        
        # 错误类型分布
        report_lines.append("\n## 错误类型分布")
        for error_type, count in list(stats['error_by_type'].items())[:10]:
            percentage = count / stats['total_errors'] * 100
            report_lines.append(f"- {error_type}: {count} 次 ({percentage:.1f}%)")
        
        # 严重程度分布
        report_lines.append("\n## 严重程度分布")
        for severity, count in stats['error_by_severity'].items():
            if count > 0:
                percentage = count / stats['total_errors'] * 100
                report_lines.append(f"- {severity.upper()}: {count} 次 ({percentage:.1f}%)")
        
        # 函数错误分布
        report_lines.append("\n## 函数错误分布")
        for function, count in list(stats['error_by_function'].items())[:10]:
            percentage = count / stats['total_errors'] * 100
            report_lines.append(f"- {function}: {count} 次 ({percentage:.1f}%)")
        
        # 最常见错误
        if stats['most_common_errors']:
            report_lines.append("\n## 最常见错误")
            for i, error in enumerate(stats['most_common_errors'], 1):
                report_lines.append(f"\n### {i}. {error['error_type']} ({error['count']} 次)")
                report_lines.append(f"- 严重程度: {error['severity'].upper()}")
                report_lines.append(f"- 影响函数: {', '.join(error['functions'])}")
                report_lines.append(f"- 错误信息: {error['error_message'][:200]}...")
        
        # 改进建议
        report_lines.append("\n## 改进建议")
        suggestions = self._generate_improvement_suggestions(stats)
        for i, suggestion in enumerate(suggestions, 1):
            report_lines.append(f"{i}. {suggestion}")
        
        return "\n".join(report_lines)
    
    def _generate_improvement_suggestions(self, stats: Dict) -> List[str]:
        """
        生成改进建议
        """
        suggestions = []
        
        # 基于解决率的建议
        if stats['resolution_rate'] < 50:
            suggestions.append(
                "错误解决率较低，建议增强自动恢复机制和错误处理逻辑"
            )
        
        # 基于错误类型的建议
        top_error_types = list(stats['error_by_type'].keys())[:3]
        if 'ConnectionError' in top_error_types or 'Timeout' in top_error_types:
            suggestions.append(
                "网络错误频发，建议增加重试机制和网络连接优化"
            )
        
        if 'KeyError' in top_error_types or 'ValueError' in top_error_types:
            suggestions.append(
                "数据处理错误较多，建议加强数据验证和异常处理"
            )
        
        # 基于严重程度的建议
        critical_rate = stats['error_by_severity'].get('critical', 0) / stats['total_errors'] * 100
        if critical_rate > 10:
            suggestions.append(
                "严重错误比例较高，建议优先处理系统稳定性问题"
            )
        
        # 基于函数分布的建议
        if len(stats['error_by_function']) > 0:
            top_error_function = list(stats['error_by_function'].keys())[0]
            top_error_count = stats['error_by_function'][top_error_function]
            if top_error_count > stats['total_errors'] * 0.3:
                suggestions.append(
                    f"函数 {top_error_function} 错误集中，建议重点优化该函数的错误处理"
                )
        
        # 通用建议
        if not suggestions:
            suggestions.append("错误处理表现良好，建议继续监控并完善错误预防机制")
        
        return suggestions
    
    def save_error_log(self, filepath: str):
        """
        保存错误日志到文件
        
        Args:
            filepath: 保存路径
        """
        try:
            error_data = {
                'statistics': self.get_error_statistics(),
                'error_records': [record.to_dict() for record in self.error_history],
                'export_time': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"错误日志已保存到 {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存错误日志失败: {e}")
    
    def clear_error_history(self):
        """
        清空错误历史
        """
        self.error_history.clear()
        self.error_counts.clear()
        self.logger.info("错误历史已清空")


class RetryHandler:
    """
    重试处理器
    """
    
    def __init__(self, max_retries: int = 3, 
                 strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化重试处理器
        
        Args:
            max_retries: 最大重试次数
            strategy: 重试策略
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子
            jitter: 是否添加随机抖动
            logger: 日志记录器
        """
        self.max_retries = max_retries
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.logger = logger or logging.getLogger(__name__)
        
        # 可重试的异常类型
        self.retryable_exceptions = {
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
            pd.errors.EmptyDataError,
            OSError,
            IOError
        }
    
    def retry_on_failure(self, func: Callable = None, *,
                        max_retries: Optional[int] = None,
                        strategy: Optional[RetryStrategy] = None,
                        exceptions: Optional[tuple] = None) -> Callable:
        """
        重试装饰器
        
        Args:
            func: 被装饰的函数
            max_retries: 最大重试次数（覆盖默认值）
            strategy: 重试策略（覆盖默认值）
            exceptions: 可重试的异常类型
            
        Returns:
            装饰后的函数
        """
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs) -> Any:
                return self._execute_with_retry(
                    f, args, kwargs, 
                    max_retries or self.max_retries,
                    strategy or self.strategy,
                    exceptions or tuple(self.retryable_exceptions)
                )
            return wrapper
        
        if func is None:
            return decorator
        else:
            return decorator(func)
    
    def _execute_with_retry(self, func: Callable, args: tuple, kwargs: dict,
                           max_retries: int, strategy: RetryStrategy,
                           exceptions: tuple) -> Any:
        """
        执行函数并处理重试
        """
        function_name = f"{func.__module__}.{func.__name__}"
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt, strategy)
                    self.logger.info(
                        f"重试 {function_name} (第 {attempt}/{max_retries} 次), "
                        f"延迟 {delay:.2f}s"
                    )
                    time.sleep(delay)
                
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"重试成功: {function_name} (第 {attempt} 次尝试)")
                
                return result
                
            except exceptions as e:
                last_exception = e
                
                if attempt < max_retries:
                    self.logger.warning(
                        f"函数 {function_name} 执行失败 (第 {attempt + 1} 次): {e}, "
                        f"将进行重试"
                    )
                else:
                    self.logger.error(
                        f"函数 {function_name} 重试 {max_retries} 次后仍然失败: {e}"
                    )
            
            except Exception as e:
                # 不可重试的异常，直接抛出
                self.logger.error(
                    f"函数 {function_name} 遇到不可重试的异常: {type(e).__name__}: {e}"
                )
                raise
        
        # 所有重试都失败，抛出最后一个异常
        raise last_exception
    
    def _calculate_delay(self, attempt: int, strategy: RetryStrategy) -> float:
        """
        计算延迟时间
        
        Args:
            attempt: 当前尝试次数（从1开始）
            strategy: 重试策略
            
        Returns:
            延迟时间（秒）
        """
        if strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        
        elif strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        
        elif strategy == RetryStrategy.RANDOM:
            delay = random.uniform(self.base_delay, self.base_delay * 3)
        
        else:
            delay = self.base_delay
        
        # 限制最大延迟
        delay = min(delay, self.max_delay)
        
        # 添加随机抖动
        if self.jitter:
            jitter_range = delay * 0.1  # 10% 抖动
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # 确保延迟不为负数
        
        return delay


# 全局错误处理器和重试处理器实例
_global_error_handler = None
_global_retry_handler = None


def get_global_error_handler() -> ErrorHandler:
    """
    获取全局错误处理器实例
    
    Returns:
        全局错误处理器
    """
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def get_global_retry_handler() -> RetryHandler:
    """
    获取全局重试处理器实例
    
    Returns:
        全局重试处理器
    """
    global _global_retry_handler
    if _global_retry_handler is None:
        _global_retry_handler = RetryHandler()
    return _global_retry_handler


def handle_errors(func: Callable = None) -> Callable:
    """
    便捷的错误处理装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            error_handler = get_global_error_handler()
            try:
                return f(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, f"{f.__module__}.{f.__name__}")
                raise
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def retry_on_failure(max_retries: int = 3, 
                    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL) -> Callable:
    """
    便捷的重试装饰器
    
    Args:
        max_retries: 最大重试次数
        strategy: 重试策略
        
    Returns:
        装饰器函数
    """
    retry_handler = get_global_retry_handler()
    return retry_handler.retry_on_failure(max_retries=max_retries, strategy=strategy)


if __name__ == "__main__":
    # 测试错误处理和重试机制
    print("错误处理和重试机制测试")
    print("=" * 40)
    
    # 创建处理器
    error_handler = ErrorHandler()
    retry_handler = RetryHandler(max_retries=3)
    
    # 测试函数
    @retry_handler.retry_on_failure
    @handle_errors
    def test_network_function(fail_count: int = 2):
        """模拟网络请求函数"""
        if not hasattr(test_network_function, 'call_count'):
            test_network_function.call_count = 0
        
        test_network_function.call_count += 1
        
        if test_network_function.call_count <= fail_count:
            raise requests.exceptions.ConnectionError("模拟网络连接失败")
        
        return f"成功！调用了 {test_network_function.call_count} 次"
    
    @handle_errors
    def test_data_function():
        """模拟数据处理函数"""
        raise ValueError("模拟数据处理错误")
    
    try:
        # 测试重试机制
        print("测试重试机制...")
        result = test_network_function(fail_count=2)
        print(f"结果: {result}")
        
        # 测试错误处理
        print("\n测试错误处理...")
        test_data_function()
        
    except Exception as e:
        print(f"捕获异常: {e}")
    
    # 生成错误报告
    print("\n错误统计:")
    stats = error_handler.get_error_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    print("\n错误报告:")
    report = error_handler.generate_error_report()
    print(report)
    
    print("\n测试完成")