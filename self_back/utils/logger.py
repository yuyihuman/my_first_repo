#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具类

提供统一的日志管理功能，所有模块的日志都通过此类进行记录
"""

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logger(name, log_file, level=logging.DEBUG):
    """
    设置日志记录器
    
    Args:
        name (str): 日志记录器名称
        log_file (str): 日志文件名
        level: 日志级别
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建logs目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建日期子目录
    date_str = datetime.now().strftime("%Y%m%d")
    date_log_dir = log_dir / date_str
    date_log_dir.mkdir(exist_ok=True)
    
    # 完整的日志文件路径
    log_path = date_log_dir / log_file
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"日志记录器 {name} 初始化完成，日志文件: {log_path}")
    
    return logger

def get_logger(name):
    """
    获取已存在的日志记录器
    
    Args:
        name (str): 日志记录器名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)