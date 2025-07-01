@echo off
chcp 65001 >nul
echo.
echo 🖋️ AI小说创作助手 - GUI版本
echo ================================
echo.
echo 正在启动图形界面...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python
    echo 请先安装Python 3.7或更高版本
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 启动GUI程序
python run_gui.py

REM 如果程序异常退出，显示错误信息
if errorlevel 1 (
    echo.
    echo ❌ 程序启动失败
    echo 可能的解决方案：
    echo 1. 运行：pip install -r requirements.txt
    echo 2. 检查 apikey.md 文件是否存在
    echo 3. 运行：python test_gui.py 进行诊断
    echo.
    pause
)