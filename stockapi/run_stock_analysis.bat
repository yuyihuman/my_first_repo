@echo off
cd /d %~dp0
del /q logs\*.log
echo 开始执行股票数据分析任务 - %date% %time% >> logs\schedule_log.txt
python run_stock_analysis.py >> logs\schedule_log.txt 2>&1
echo 任务执行完成 - %date% %time% >> logs\schedule_log.txt