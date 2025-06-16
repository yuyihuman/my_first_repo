#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机构持股数据分析器配置文件
# Configuration file for Institutional Holdings Analyzer

用户可以通过修改此文件来自定义分析参数
"""

from datetime import datetime

# =============================================================================
# 基础配置
# =============================================================================

# 数据存储目录
BASE_DATA_DIR = "institutional_holdings_data"
base_dir = 'institutional_holdings_data'  # 数据存储基础目录

# 分析时间范围
START_YEAR = 2020  # 开始年份
END_YEAR = None    # 结束年份，None表示当前年份

# 默认分析参数
default_start_year = 2025
default_end_year = 2024
default_target_stock_code = None  # 默认分析所有股票，可设置为具体股票代码如 '000001'

# 目标股票代码（可选）
# None: 分析全市场
# "000001": 分析指定股票
TARGET_STOCK_CODE = None

# =============================================================================
# 数据获取配置
# =============================================================================

# 支持的机构类型
INSTITUTION_TYPES = [
    "基金持仓",
    "QFII持仓", 
    "社保持仓",
    "券商持仓",
    "保险持仓",
    "信托持仓"
]

# 性能优化配置
BATCH_SIZE = 100  # 股票信息获取批处理大小
REQUEST_DELAY = 0.1  # 请求间隔（秒），避免请求过于频繁
MAX_RETRIES = 3  # 最大重试次数
TIMEOUT = 30  # 请求超时时间（秒）

# 内存管理配置
MEMORY_CLEANUP_INTERVAL = 100  # 每处理多少只股票后进行内存清理
MAX_CONCURRENT_REQUESTS = 5  # 最大并发请求数

# 机构类型配置
institution_types = {
    '基金': 'fund',
    '社保': 'social_security', 
    '券商': 'broker',
    '保险': 'insurance',
    'QFII': 'qfii',
    '信托': 'trust'
}

# API请求配置
MAX_RETRIES = 3        # 最大重试次数
REQUEST_DELAY = 1      # 请求间隔（秒）
RETRY_DELAY_BASE = 2   # 重试延时基数（指数退避）

# 数据获取配置
request_delay = 1.0  # 请求间隔（秒）
retry_delay_base = 2.0  # 重试延迟基数（秒）
max_retries = 3  # 最大重试次数
skip_existing_files = True  # 是否跳过已存在的文件

# =============================================================================
# 分析配置
# =============================================================================

# 重仓股排行榜数量
TOP_HOLDINGS_COUNT = 20

# 分析配置
top_holdings_count = 10  # 显示前N个持仓

# 数值精度
NUMERIC_PRECISION = 2

# =============================================================================
# 日志配置
# =============================================================================

# 日志级别
# DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# 日志格式
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# 是否输出到控制台
LOG_TO_CONSOLE = True

# 日志配置
logging_config = {
    'level': 'INFO',  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'console_output': True,  # 是否输出到控制台
    'file_encoding': 'utf-8-sig'  # 文件编码
}

# 数据验证配置
data_validation_config = {
    'enable_validation': True,  # 是否启用数据验证
    'outlier_detection': True,  # 是否检测异常值
    'outlier_threshold': 3.0,  # 异常值检测阈值（标准差倍数）
    'missing_value_threshold': 0.5,  # 缺失值比例阈值
    'auto_clean': True  # 是否自动清洗数据
}

# 性能监控配置
performance_config = {
    'enable_monitoring': True,  # 是否启用性能监控
    'memory_threshold_mb': 1000,  # 内存使用阈值（MB）
    'runtime_threshold_seconds': 300,  # 运行时间阈值（秒）
    'monitoring_interval': 5,  # 监控间隔（秒）
    'save_detailed_logs': True  # 是否保存详细日志
}

# 错误处理配置
error_handling_config = {
    'enable_error_handling': True,  # 是否启用错误处理
    'auto_recovery': True,  # 是否自动恢复
    'max_recovery_attempts': 3,  # 最大恢复尝试次数
    'error_log_level': 'ERROR',  # 错误日志级别
    'save_error_details': True  # 是否保存错误详情
}

# 缓存配置
cache_config = {
    'enable_cache': True,  # 是否启用缓存
    'cache_memory_limit': 50,  # 内存缓存限制（项数）- 减少内存使用，主要依赖文件缓存
    'cache_file_ttl': 72000,  # 文件缓存TTL（秒）- 20小时缓存
    'cache_compression': True,  # 是否压缩缓存
    'auto_cleanup': True  # 是否自动清理过期缓存
}

# 重试策略配置
retry_config = {
    'default_strategy': 'exponential_backoff',  # 默认重试策略
    'max_retries': 3,  # 最大重试次数
    'base_delay': 1.0,  # 基础延迟（秒）
    'max_delay': 60.0,  # 最大延迟（秒）
    'backoff_factor': 2.0  # 退避因子
}

# =============================================================================
# 文件配置
# =============================================================================

# 文件编码
FILE_ENCODING = 'utf-8-sig'

# CSV分隔符
CSV_SEPARATOR = ','

# =============================================================================
# 高级配置
# =============================================================================

# 数据验证
ENABLE_DATA_VALIDATION = True

# 跳过已存在的文件
SKIP_EXISTING_FILES = True

# 生成详细报告
GENERATE_DETAILED_REPORT = True

# 保存中间结果
SAVE_INTERMEDIATE_RESULTS = True

# =============================================================================
# 自定义季度配置（高级用户）
# =============================================================================

# 自定义季度末日期（如果需要特殊的日期）
# 格式: YYYYMMDD
# 留空使用默认的季度末日期
CUSTOM_QUARTER_DATES = [
    # "20200331",
    # "20200630", 
    # "20200930",
    # "20201231",
]

# =============================================================================
# 输出配置
# =============================================================================

# 报告格式
REPORT_FORMATS = ['markdown', 'json']  # 支持: markdown, json, excel

# 图表配置（如果启用可视化）
ENABLE_CHARTS = False
CHART_STYLE = 'seaborn'  # matplotlib样式
CHART_DPI = 300

# =============================================================================
# 性能配置
# =============================================================================

# 并发处理（实验性功能）
ENABLE_CONCURRENT_PROCESSING = False
MAX_WORKERS = 4

# 内存优化
CHUNK_SIZE = 10000  # 大文件分块处理大小

# =============================================================================
# 验证配置
# =============================================================================

def validate_config():
    """
    验证配置参数的有效性
    """
    errors = []
    
    # 验证年份
    current_year = datetime.now().year
    if START_YEAR < 2010 or START_YEAR > current_year:
        errors.append(f"开始年份应在2010-{current_year}之间")
    
    if END_YEAR is not None and (END_YEAR < START_YEAR or END_YEAR > current_year):
        errors.append(f"结束年份应在{START_YEAR}-{current_year}之间")
    
    # 验证机构类型
    valid_types = ["基金持仓", "QFII持仓", "社保持仓", "券商持仓", "保险持仓", "信托持仓"]
    for inst_type in INSTITUTION_TYPES:
        if inst_type not in valid_types:
            errors.append(f"无效的机构类型: {inst_type}")
    
    # 验证数值参数
    if MAX_RETRIES < 1 or MAX_RETRIES > 10:
        errors.append("最大重试次数应在1-10之间")
    
    if REQUEST_DELAY < 0.1 or REQUEST_DELAY > 10:
        errors.append("请求延时应在0.1-10秒之间")
    
    if TOP_HOLDINGS_COUNT < 1 or TOP_HOLDINGS_COUNT > 100:
        errors.append("重仓股数量应在1-100之间")
    
    # 验证日志级别
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if LOG_LEVEL not in valid_log_levels:
        errors.append(f"无效的日志级别: {LOG_LEVEL}")
    
    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(f"- {error}" for error in errors))
    
    return True

# =============================================================================
# 配置加载函数
# =============================================================================

def get_config():
    """
    获取当前配置
    
    Returns:
        dict: 配置字典
    """
    validate_config()
    
    config = {
        'base_data_dir': BASE_DATA_DIR,
        'start_year': START_YEAR,
        'end_year': END_YEAR,
        'target_stock_code': TARGET_STOCK_CODE,
        'institution_types': INSTITUTION_TYPES,
        'max_retries': MAX_RETRIES,
        'request_delay': REQUEST_DELAY,
        'retry_delay_base': RETRY_DELAY_BASE,
        'top_holdings_count': TOP_HOLDINGS_COUNT,
        'numeric_precision': NUMERIC_PRECISION,
        'log_level': LOG_LEVEL,
        'log_format': LOG_FORMAT,
        'log_to_console': LOG_TO_CONSOLE,
        'file_encoding': FILE_ENCODING,
        'csv_separator': CSV_SEPARATOR,
        'enable_data_validation': ENABLE_DATA_VALIDATION,
        'skip_existing_files': SKIP_EXISTING_FILES,
        'generate_detailed_report': GENERATE_DETAILED_REPORT,
        'save_intermediate_results': SAVE_INTERMEDIATE_RESULTS,
        'custom_quarter_dates': CUSTOM_QUARTER_DATES,
        'report_formats': REPORT_FORMATS,
        'enable_charts': ENABLE_CHARTS,
        'chart_style': CHART_STYLE,
        'chart_dpi': CHART_DPI,
        'enable_concurrent_processing': ENABLE_CONCURRENT_PROCESSING,
        'max_workers': MAX_WORKERS,
        'chunk_size': CHUNK_SIZE,
        'batch_size': BATCH_SIZE,
        'timeout': TIMEOUT,
        'memory_cleanup_interval': MEMORY_CLEANUP_INTERVAL,
        'max_concurrent_requests': MAX_CONCURRENT_REQUESTS
    }
    
    return config

def print_config():
    """
    打印当前配置
    """
    config = get_config()
    
    print("当前配置:")
    print("=" * 50)
    
    for key, value in config.items():
        if isinstance(value, list) and len(value) > 3:
            print(f"{key}: [{', '.join(map(str, value[:3]))}, ...] (共{len(value)}项)")
        else:
            print(f"{key}: {value}")
    
    print("=" * 50)

if __name__ == "__main__":
    # 测试配置
    try:
        print_config()
        print("\n✓ 配置验证通过")
    except ValueError as e:
        print(f"\n✗ 配置验证失败: {e}")