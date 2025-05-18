import os
import logging
from datetime import datetime

# 全局变量，用于跟踪当前日志文件
_current_log_file = None
_current_logger = None
# 添加一个全局变量，用于存储用户指定的默认日志文件名
_default_log_file = None

def set_default_log_file(log_file):
    """
    设置默认的日志文件名
    :param log_file: 日志文件名
    """
    global _default_log_file
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    _default_log_file = os.path.join(logs_dir, log_file)
    print(f"已设置默认日志文件: {_default_log_file}")
    return _default_log_file

def setup_logger(name=None, log_file=None, reset=False, print_config=True):
    """
    配置日志记录器
    :param name: 日志记录器名称，默认为None（使用root logger）
    :param log_file: 指定日志文件名，默认为None（使用默认日志文件或自动生成）
    :param reset: 是否重置现有的日志处理器
    :return: 配置好的日志记录器
    """
    global _current_log_file, _current_logger, _default_log_file
    
    # 创建logs文件夹（如果不存在）
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"创建日志目录: {logs_dir}")
    
    # 配置日志格式，包含行号
    log_format = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
    
    # 如果没有指定日志文件名，则使用默认日志文件或自动生成
    if log_file is None:
        if _default_log_file is not None:
            log_file = _default_log_file
        else:
            log_file = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    else:
        log_file = os.path.join(logs_dir, log_file)
    
    # 保存当前日志文件路径
    _current_log_file = log_file
    
    # 获取logger实例
    logger = logging.getLogger(name)
    _current_logger = logger
    
    # 检查是否已经配置了相同的文件处理器
    has_file_handler = False
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == os.path.abspath(log_file):
            has_file_handler = True
            break
    
    # 如果需要重置或者没有处理器，则配置新的处理器
    if reset or (not logger.handlers and not has_file_handler):
        # 如果需要重置，先移除所有现有处理器
        if reset:
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
        
        # 设置日志级别
        logger.setLevel(logging.DEBUG)  # 修改为DEBUG级别，捕获更多日志
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别的日志
        logger.addHandler(file_handler)
        
        # 移除控制台处理器，只保留文件处理器
        # 不再创建控制台处理器
        if print_config:
            print(f"日志配置完成，日志文件: {log_file}")
    
    return logger

# 获取当前日志文件路径
def get_current_log_file():
    return _current_log_file

# 获取当前日志记录器
def get_current_logger():
    return _current_logger

# 创建一个延迟初始化的logger
class LazyLogger:
    def __init__(self):
        self._logger = None
    
    def __getattr__(self, name):
        if self._logger is None:
            self._logger = setup_logger()
        return getattr(self._logger, name)
    
    def set_logger(self, new_logger):
        self._logger = new_logger

# 使用延迟初始化的logger替代直接创建
logger = LazyLogger()

# 添加一些辅助函数
def log_execution_time(func):
    """
    装饰器：记录函数执行时间
    """
    import time
    def wrapper(*args, **kwargs):
        start_time = time.time()
        current_logger = get_current_logger() or init_default_logger()
        current_logger.debug(f"开始执行函数: {func.__name__}")
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        current_logger.debug(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.4f}秒")
        return result
    return wrapper

def log_exception(func):
    """
    装饰器：捕获并记录函数执行过程中的异常
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_logger = get_current_logger() or init_default_logger()
            current_logger.error(f"函数 {func.__name__} 执行出错: {e}", exc_info=True)
            raise
    return wrapper