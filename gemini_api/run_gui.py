#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说创作助手 - GUI启动脚本
双击此文件即可启动图形界面版本的小说创作助手
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """检查依赖是否安装"""
    missing_deps = []
    
    try:
        import requests
    except ImportError:
        missing_deps.append('requests')
    
    try:
        import json5
    except ImportError:
        missing_deps.append('json5')
    
    return missing_deps

def check_api_key():
    """检查API密钥是否存在"""
    return os.path.exists('apikey.md')

def main():
    """主启动函数"""
    print("🖋️ AI小说创作助手 - GUI版本")
    print("正在启动...")
    
    # 尝试导入日志系统（如果可用）
    logger = None
    try:
        from logger_config import NovelLogger
        logger = NovelLogger.get_main_logger()
        NovelLogger.log_session_start(logger, "GUI启动脚本")
        logger.info("开始启动GUI程序")
    except ImportError:
        print("日志系统不可用，继续启动...")
    
    # 检查依赖
    missing_deps = check_dependencies()
    if missing_deps:
        error_msg = f"缺少以下依赖包：{', '.join(missing_deps)}\n\n请运行以下命令安装：\npip install {' '.join(missing_deps)}"
        print(f"❌ {error_msg}")
        if logger:
            logger.error(f"依赖缺失: {missing_deps}")
        
        # 显示错误对话框
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror("依赖缺失", error_msg)
        if logger:
            NovelLogger.log_session_end(logger, "GUI启动脚本")
        return
    
    # 检查API密钥
    if not check_api_key():
        warning_msg = "未找到 apikey.md 文件\n\n请确保在程序目录下创建 apikey.md 文件并填入您的 Gemini API 密钥"
        print(f"⚠️ {warning_msg}")
        if logger:
            logger.warning("API密钥文件缺失")
        
        root = tk.Tk()
        root.withdraw()
        result = messagebox.askquestion("API密钥缺失", f"{warning_msg}\n\n是否继续启动程序？")
        if result != 'yes':
            if logger:
                logger.info("用户选择不继续启动程序")
                NovelLogger.log_session_end(logger, "GUI启动脚本")
            return
    
    try:
        # 导入并启动GUI
        if logger:
            logger.info("开始导入GUI模块")
        from novel_gui import main as gui_main
        print("✅ 启动成功！")
        if logger:
            logger.info("GUI模块导入成功，启动界面")
        gui_main()
        if logger:
            logger.info("GUI程序正常结束")
        
    except ImportError as e:
        error_msg = f"导入GUI模块失败：{e}\n\n请确保 novel_gui.py 文件存在且完整"
        print(f"❌ {error_msg}")
        if logger:
            NovelLogger.log_error_with_context(logger, e, "导入GUI模块")
        
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("导入错误", error_msg)
        
    except Exception as e:
        error_msg = f"程序运行时发生错误：{e}"
        print(f"❌ {error_msg}")
        if logger:
            NovelLogger.log_error_with_context(logger, e, "程序运行")
        
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("运行错误", error_msg)
    
    finally:
        if logger:
            NovelLogger.log_session_end(logger, "GUI启动脚本")

if __name__ == "__main__":
    main()