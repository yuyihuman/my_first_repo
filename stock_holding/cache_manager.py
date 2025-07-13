#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理模块

提供多层缓存机制，包括内存缓存、文件缓存和数据库缓存
"""

import os
import json
import pickle
import hashlib
import time
import functools
import logging
import threading
from typing import Dict, Any, Optional, Callable, Union, List
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from dataclasses import dataclass, asdict
from collections import OrderedDict
import sqlite3
import gzip
import shutil


@dataclass
class CacheEntry:
    """
    缓存条目数据类
    """
    key: str
    value: Any
    created_time: float
    last_accessed: float
    access_count: int
    ttl: Optional[float] = None  # 生存时间（秒）
    size: int = 0  # 数据大小（字节）
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_time > self.ttl
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class MemoryCache:
    """
    内存缓存
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        """
        初始化内存缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认生存时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                return None
            
            # 更新访问信息
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # 移动到末尾（LRU）
            self._cache.move_to_end(key)
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），为None时使用默认值
        """
        with self._lock:
            current_time = time.time()
            
            # 计算数据大小
            try:
                size = len(pickle.dumps(value))
            except Exception:
                size = 0
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_time=current_time,
                last_accessed=current_time,
                access_count=0,
                ttl=ttl or self.default_ttl,
                size=size
            )
            
            # 如果键已存在，删除旧条目
            if key in self._cache:
                del self._cache[key]
            
            # 添加新条目
            self._cache[key] = entry
            
            # 检查缓存大小限制
            while len(self._cache) > self.max_size:
                # 删除最久未使用的条目
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """
        清空缓存
        """
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        清理过期条目
        
        Returns:
            清理的条目数量
        """
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_size = sum(entry.size for entry in self._cache.values())
            total_access = sum(entry.access_count for entry in self._cache.values())
            
            return {
                'total_entries': len(self._cache),
                'max_size': self.max_size,
                'total_size_bytes': total_size,
                'total_access_count': total_access,
                'average_size_bytes': total_size / len(self._cache) if self._cache else 0
            }


class FileCache:
    """
    文件缓存
    """
    
    def __init__(self, cache_dir: str, default_ttl: Optional[float] = None,
                 compress: bool = True, max_size_mb: float = 1000):
        """
        初始化文件缓存
        
        Args:
            cache_dir: 缓存目录
            default_ttl: 默认生存时间（秒）
            compress: 是否压缩缓存文件
            max_size_mb: 最大缓存大小（MB）
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.compress = compress
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 元数据文件
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """
        加载缓存元数据
        """
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {}
        except Exception:
            self.metadata = {}
    
    def _save_metadata(self) -> None:
        """
        保存缓存元数据
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass
    
    def _get_cache_path(self, key: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            key: 缓存键
            
        Returns:
            缓存文件路径
        """
        # 使用MD5哈希避免文件名过长或包含特殊字符
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        extension = '.gz' if self.compress else '.pkl'
        return self.cache_dir / f"{key_hash}{extension}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._lock:
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                return None
            
            # 检查元数据
            if key in self.metadata:
                entry_info = self.metadata[key]
                
                # 检查是否过期
                if entry_info.get('ttl') is not None:
                    if time.time() - entry_info['created_time'] > entry_info['ttl']:
                        self.delete(key)
                        return None
                
                # 更新访问信息
                entry_info['last_accessed'] = time.time()
                entry_info['access_count'] = entry_info.get('access_count', 0) + 1
                self._save_metadata()
            
            # 读取缓存文件
            try:
                if self.compress:
                    with gzip.open(cache_path, 'rb') as f:
                        return pickle.load(f)
                else:
                    with open(cache_path, 'rb') as f:
                        return pickle.load(f)
            except Exception:
                # 文件损坏，删除缓存
                self.delete(key)
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），为None时使用默认值
        """
        with self._lock:
            cache_path = self._get_cache_path(key)
            current_time = time.time()
            
            # 写入缓存文件
            try:
                if self.compress:
                    with gzip.open(cache_path, 'wb') as f:
                        pickle.dump(value, f)
                else:
                    with open(cache_path, 'wb') as f:
                        pickle.dump(value, f)
                
                # 更新元数据
                file_size = cache_path.stat().st_size
                self.metadata[key] = {
                    'created_time': current_time,
                    'last_accessed': current_time,
                    'access_count': 0,
                    'ttl': ttl or self.default_ttl,
                    'size': file_size,
                    'file_path': str(cache_path)
                }
                
                self._save_metadata()
                
                # 检查缓存大小限制
                self._cleanup_if_needed()
                
            except Exception:
                # 写入失败，清理可能的部分文件
                if cache_path.exists():
                    cache_path.unlink()
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            cache_path = self._get_cache_path(key)
            
            deleted = False
            
            # 删除文件
            if cache_path.exists():
                cache_path.unlink()
                deleted = True
            
            # 删除元数据
            if key in self.metadata:
                del self.metadata[key]
                self._save_metadata()
                deleted = True
            
            return deleted
    
    def clear(self) -> None:
        """
        清空缓存
        """
        with self._lock:
            # 删除所有缓存文件
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            for cache_file in self.cache_dir.glob("*.gz"):
                cache_file.unlink()
            
            # 清空元数据
            self.metadata.clear()
            self._save_metadata()
    
    def cleanup_expired(self) -> int:
        """
        清理过期条目
        
        Returns:
            清理的条目数量
        """
        with self._lock:
            expired_keys = []
            current_time = time.time()
            
            for key, entry_info in self.metadata.items():
                if entry_info.get('ttl') is not None:
                    if current_time - entry_info['created_time'] > entry_info['ttl']:
                        expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
            
            return len(expired_keys)
    
    def _cleanup_if_needed(self) -> None:
        """
        如果需要则清理缓存以保持在大小限制内
        """
        total_size = sum(entry.get('size', 0) for entry in self.metadata.values())
        
        if total_size > self.max_size_bytes:
            # 按最后访问时间排序，删除最久未使用的条目
            sorted_entries = sorted(
                self.metadata.items(),
                key=lambda x: x[1].get('last_accessed', 0)
            )
            
            for key, _ in sorted_entries:
                if total_size <= self.max_size_bytes * 0.8:  # 清理到80%
                    break
                
                entry_size = self.metadata[key].get('size', 0)
                self.delete(key)
                total_size -= entry_size
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_size = sum(entry.get('size', 0) for entry in self.metadata.values())
            total_access = sum(entry.get('access_count', 0) for entry in self.metadata.values())
            
            return {
                'total_entries': len(self.metadata),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'total_access_count': total_access,
                'average_size_bytes': total_size / len(self.metadata) if self.metadata else 0
            }


class CacheManager:
    """
    缓存管理器 - 统一管理多层缓存
    """
    
    def __init__(self, cache_dir: str = "cache", 
                 memory_cache_size: int = 1000,
                 file_cache_size_mb: float = 1000,
                 default_ttl: Optional[float] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 文件缓存目录
            memory_cache_size: 内存缓存最大条目数
            file_cache_size_mb: 文件缓存最大大小（MB）
            default_ttl: 默认生存时间（秒）
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # 初始化多层缓存
        self.memory_cache = MemoryCache(max_size=memory_cache_size, default_ttl=default_ttl)
        self.file_cache = FileCache(
            cache_dir=cache_dir, 
            default_ttl=default_ttl,
            max_size_mb=file_cache_size_mb
        )
        
        # 缓存统计
        self.stats = {
            'memory_hits': 0,
            'file_hits': 0,
            'misses': 0,
            'sets': 0
        }
        
        self.logger.info(f"缓存管理器已初始化 - 内存缓存: {memory_cache_size} 条目, "
                        f"文件缓存: {file_cache_size_mb}MB")
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（先查内存缓存，再查文件缓存）
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        # 先查内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            self.stats['memory_hits'] += 1
            return value
        
        # 再查文件缓存
        value = self.file_cache.get(key)
        if value is not None:
            self.stats['file_hits'] += 1
            # 将文件缓存的值提升到内存缓存
            self.memory_cache.set(key, value)
            return value
        
        # 缓存未命中
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None,
           memory_only: bool = False) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            memory_only: 是否只存储在内存缓存中
        """
        self.stats['sets'] += 1
        
        # 存储到内存缓存
        self.memory_cache.set(key, value, ttl)
        
        # 存储到文件缓存（除非指定只存内存）
        if not memory_only:
            try:
                self.file_cache.set(key, value, ttl)
            except Exception as e:
                self.logger.warning(f"文件缓存存储失败: {e}")
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        memory_deleted = self.memory_cache.delete(key)
        file_deleted = self.file_cache.delete(key)
        return memory_deleted or file_deleted
    
    def clear(self) -> None:
        """
        清空所有缓存
        """
        self.memory_cache.clear()
        self.file_cache.clear()
        
        # 重置统计
        self.stats = {
            'memory_hits': 0,
            'file_hits': 0,
            'misses': 0,
            'sets': 0
        }
        
        self.logger.info("所有缓存已清空")
    
    def cleanup_expired(self) -> Dict[str, int]:
        """
        清理过期条目
        
        Returns:
            清理统计信息
        """
        memory_cleaned = self.memory_cache.cleanup_expired()
        file_cleaned = self.file_cache.cleanup_expired()
        
        result = {
            'memory_cleaned': memory_cleaned,
            'file_cleaned': file_cleaned,
            'total_cleaned': memory_cleaned + file_cleaned
        }
        
        if result['total_cleaned'] > 0:
            self.logger.info(f"清理过期缓存: 内存 {memory_cleaned} 条目, 文件 {file_cleaned} 条目")
        
        return result
    
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        memory_stats = self.memory_cache.get_stats()
        file_stats = self.file_cache.get_stats()
        
        total_requests = sum(self.stats.values())
        hit_rate = ((self.stats['memory_hits'] + self.stats['file_hits']) / 
                   total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate_percent': hit_rate,
            'total_requests': total_requests,
            'memory_hits': self.stats['memory_hits'],
            'file_hits': self.stats['file_hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'memory_cache': memory_stats,
            'file_cache': file_stats
        }
    
    def cache_function(self, ttl: Optional[float] = None, 
                      memory_only: bool = False,
                      key_func: Optional[Callable] = None) -> Callable:
        """
        函数缓存装饰器
        
        Args:
            ttl: 缓存生存时间（秒）
            memory_only: 是否只使用内存缓存
            key_func: 自定义键生成函数
            
        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(func, args, kwargs)
                
                # 尝试从缓存获取
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl, memory_only)
                
                return result
            
            # 添加缓存控制方法
            wrapper.cache_clear = lambda: self._clear_function_cache(func)
            wrapper.cache_info = lambda: self._get_function_cache_info(func)
            
            return wrapper
        
        return decorator
    
    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """
        生成缓存键
        
        Args:
            func: 函数对象
            args: 位置参数
            kwargs: 关键字参数
            
        Returns:
            缓存键
        """
        # 创建包含函数名和参数的键
        key_parts = [
            func.__module__,
            func.__name__,
            str(args),
            str(sorted(kwargs.items()))
        ]
        
        key_string = "|".join(key_parts)
        
        # 使用MD5哈希避免键过长
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _clear_function_cache(self, func: Callable) -> None:
        """
        清空特定函数的缓存
        
        Args:
            func: 函数对象
        """
        # 这里简化实现，实际应该维护函数到缓存键的映射
        self.logger.info(f"清空函数 {func.__name__} 的缓存")
    
    def _get_function_cache_info(self, func: Callable) -> Dict:
        """
        获取特定函数的缓存信息
        
        Args:
            func: 函数对象
            
        Returns:
            缓存信息字典
        """
        # 这里简化实现，实际应该维护详细的函数缓存统计
        return {'function': func.__name__, 'cache_enabled': True}
    
    def generate_report(self) -> str:
        """
        生成缓存报告（别名方法）
        
        Returns:
            缓存报告文本
        """
        return self.generate_cache_report()
    
    def generate_cache_report(self) -> str:
        """
        生成缓存报告
        
        Returns:
            缓存报告文本
        """
        stats = self.get_cache_stats()
        
        report_lines = []
        report_lines.append("# 缓存管理报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 总体统计
        report_lines.append("\n## 总体统计")
        report_lines.append(f"- 缓存命中率: {stats['hit_rate_percent']:.1f}%")
        report_lines.append(f"- 总请求数: {stats['total_requests']:,}")
        report_lines.append(f"- 内存命中: {stats['memory_hits']:,}")
        report_lines.append(f"- 文件命中: {stats['file_hits']:,}")
        report_lines.append(f"- 缓存未命中: {stats['misses']:,}")
        report_lines.append(f"- 缓存写入: {stats['sets']:,}")
        
        # 内存缓存统计
        memory_stats = stats['memory_cache']
        report_lines.append("\n## 内存缓存")
        report_lines.append(f"- 条目数: {memory_stats['total_entries']:,} / {memory_stats['max_size']:,}")
        report_lines.append(f"- 总大小: {memory_stats['total_size_bytes']:,} 字节")
        report_lines.append(f"- 平均大小: {memory_stats['average_size_bytes']:.0f} 字节")
        report_lines.append(f"- 总访问次数: {memory_stats['total_access_count']:,}")
        
        # 文件缓存统计
        file_stats = stats['file_cache']
        report_lines.append("\n## 文件缓存")
        report_lines.append(f"- 条目数: {file_stats['total_entries']:,}")
        report_lines.append(f"- 总大小: {file_stats['total_size_mb']:.1f} MB / {file_stats['max_size_mb']:.1f} MB")
        report_lines.append(f"- 平均大小: {file_stats['average_size_bytes']:.0f} 字节")
        report_lines.append(f"- 总访问次数: {file_stats['total_access_count']:,}")
        
        # 性能建议
        report_lines.append("\n## 性能建议")
        suggestions = self._generate_cache_suggestions(stats)
        for i, suggestion in enumerate(suggestions, 1):
            report_lines.append(f"{i}. {suggestion}")
        
        return "\n".join(report_lines)
    
    def _generate_cache_suggestions(self, stats: Dict) -> List[str]:
        """
        生成缓存优化建议
        
        Args:
            stats: 缓存统计信息
            
        Returns:
            建议列表
        """
        suggestions = []
        
        # 基于命中率的建议
        hit_rate = stats['hit_rate_percent']
        if hit_rate < 50:
            suggestions.append(
                "缓存命中率较低，建议检查缓存策略和TTL设置"
            )
        elif hit_rate > 90:
            suggestions.append(
                "缓存命中率很高，可以考虑增加缓存大小以存储更多数据"
            )
        
        # 基于内存使用的建议
        memory_usage = (stats['memory_cache']['total_entries'] / 
                       stats['memory_cache']['max_size'] * 100)
        if memory_usage > 90:
            suggestions.append(
                "内存缓存使用率较高，建议增加内存缓存大小或调整TTL"
            )
        
        # 基于文件缓存的建议
        file_usage = (stats['file_cache']['total_size_mb'] / 
                     stats['file_cache']['max_size_mb'] * 100)
        if file_usage > 90:
            suggestions.append(
                "文件缓存使用率较高，建议增加文件缓存大小或清理过期数据"
            )
        
        # 基于访问模式的建议
        if stats['file_hits'] > stats['memory_hits']:
            suggestions.append(
                "文件缓存命中较多，建议增加内存缓存大小以提升性能"
            )
        
        if not suggestions:
            suggestions.append("缓存性能良好，建议继续监控使用情况")
        
        return suggestions


# 全局缓存管理器实例
_global_cache_manager = None


def get_global_cache_manager() -> CacheManager:
    """
    获取全局缓存管理器实例
    
    Returns:
        全局缓存管理器
    """
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def cache_result(ttl: Optional[float] = None, memory_only: bool = False) -> Callable:
    """
    便捷的缓存装饰器
    
    Args:
        ttl: 缓存生存时间（秒）
        memory_only: 是否只使用内存缓存
        
    Returns:
        装饰器函数
    """
    cache_manager = get_global_cache_manager()
    return cache_manager.cache_function(ttl=ttl, memory_only=memory_only)


if __name__ == "__main__":
    # 测试缓存管理器
    print("缓存管理器测试")
    print("=" * 30)
    
    # 创建缓存管理器
    cache_manager = CacheManager(cache_dir="test_cache")
    
    # 测试函数
    @cache_manager.cache_function(ttl=10.0)
    def expensive_function(x: int, y: int) -> int:
        """模拟耗时计算"""
        print(f"执行计算: {x} + {y}")
        time.sleep(0.1)  # 模拟耗时操作
        return x + y
    
    @cache_manager.cache_function(memory_only=True)
    def fast_function(data: str) -> str:
        """快速函数，只使用内存缓存"""
        print(f"处理数据: {data}")
        return data.upper()
    
    # 测试缓存功能
    print("测试缓存功能...")
    
    # 第一次调用（缓存未命中）
    result1 = expensive_function(1, 2)
    print(f"结果1: {result1}")
    
    # 第二次调用（缓存命中）
    result2 = expensive_function(1, 2)
    print(f"结果2: {result2}")
    
    # 不同参数（缓存未命中）
    result3 = expensive_function(3, 4)
    print(f"结果3: {result3}")
    
    # 测试内存缓存
    result4 = fast_function("hello")
    print(f"结果4: {result4}")
    
    result5 = fast_function("hello")
    print(f"结果5: {result5}")
    
    # 显示缓存统计
    print("\n缓存统计:")
    stats = cache_manager.get_cache_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 生成缓存报告
    print("\n缓存报告:")
    report = cache_manager.generate_cache_report()
    print(report)
    
    # 清理测试缓存
    cache_manager.clear()
    print("\n测试完成，缓存已清空")