#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说创作助手 - 统一日志系统
提供统一的日志配置和管理功能
"""

import logging
import os
from datetime import datetime
from pathlib import Path
import sys

# 日志目录配置
LOG_DIR = "logs"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

class NovelLogger:
    """小说创作助手统一日志管理器"""
    
    _loggers = {}
    _log_dir_created = False
    
    @classmethod
    def setup_log_directory(cls):
        """创建日志目录"""
        if not cls._log_dir_created:
            log_path = Path(LOG_DIR)
            log_path.mkdir(exist_ok=True)
            cls._log_dir_created = True
    
    @classmethod
    def get_logger(cls, name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
        """获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件名（可选，默认使用name.log）
            level: 日志级别
            
        Returns:
            配置好的日志记录器
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        # 确保日志目录存在
        cls.setup_log_directory()
        
        # 创建日志记录器
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 设置日志文件名
        if log_file is None:
            log_file = f"{name}.log"
        
        log_file_path = Path(LOG_DIR) / log_file
        
        # 创建文件处理器（带轮转）
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 缓存日志记录器
        cls._loggers[name] = logger
        
        return logger
    
    @classmethod
    def get_main_logger(cls) -> logging.Logger:
        """获取主程序日志记录器"""
        return cls.get_logger('novel_main', 'main.log')
    
    @classmethod
    def get_generator_logger(cls) -> logging.Logger:
        """获取生成器日志记录器"""
        return cls.get_logger('novel_generator', 'generator.log')
    
    @classmethod
    def get_gui_logger(cls) -> logging.Logger:
        """获取GUI日志记录器"""
        return cls.get_logger('novel_gui', 'gui.log')
    
    @classmethod
    def get_batch_logger(cls) -> logging.Logger:
        """获取批量处理日志记录器"""
        return cls.get_logger('novel_batch', 'batch.log')
    
    @classmethod
    def get_api_logger(cls) -> logging.Logger:
        """获取API调用日志记录器"""
        return cls.get_logger('novel_api', 'api.log')
    
    @classmethod
    def log_session_start(cls, logger: logging.Logger, session_type: str):
        """记录会话开始"""
        logger.info(f"="*50)
        logger.info(f"会话开始 - {session_type}")
        logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"="*50)
    
    @classmethod
    def log_session_end(cls, logger: logging.Logger, session_type: str):
        """记录会话结束"""
        logger.info(f"会话结束 - {session_type}")
        logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"="*50)
    
    @classmethod
    def log_error_with_context(cls, logger: logging.Logger, error: Exception, context: str = ""):
        """记录带上下文的错误信息"""
        logger.error(f"错误发生: {context}")
        logger.error(f"错误类型: {type(error).__name__}")
        logger.error(f"错误信息: {str(error)}")
        logger.error(f"错误详情:", exc_info=True)
    
    @classmethod
    def log_api_call(cls, logger: logging.Logger, api_name: str, params: dict = None, response_size: int = None):
        """记录API调用信息"""
        logger.info(f"API调用: {api_name}")
        if params:
            # 过滤敏感信息
            safe_params = {k: v for k, v in params.items() if 'key' not in k.lower() and 'token' not in k.lower()}
            logger.info(f"参数: {safe_params}")
        if response_size:
            logger.info(f"响应大小: {response_size} 字符")
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 30):
        """清理旧日志文件"""
        try:
            log_path = Path(LOG_DIR)
            if not log_path.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for log_file in log_path.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    print(f"已删除旧日志文件: {log_file}")
        except Exception as e:
            print(f"清理日志文件时出错: {e}")

# 便捷函数
def get_logger(name: str = 'novel_main') -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return NovelLogger.get_logger(name)

def log_info(message: str, logger_name: str = 'novel_main'):
    """记录信息日志的便捷函数"""
    logger = NovelLogger.get_logger(logger_name)
    logger.info(message)

def log_error(message: str, error: Exception = None, logger_name: str = 'novel_main'):
    """记录错误日志的便捷函数"""
    logger = NovelLogger.get_logger(logger_name)
    if error:
        NovelLogger.log_error_with_context(logger, error, message)
    else:
        logger.error(message)

def log_warning(message: str, logger_name: str = 'novel_main'):
    """记录警告日志的便捷函数"""
    logger = NovelLogger.get_logger(logger_name)
    logger.warning(message)

# 初始化时创建日志目录
NovelLogger.setup_log_directory()