@echo off
del /q C:\Users\Ramsey\github\my_first_repo\stockapi\logs\*.log
echo 开始执行股票数据分析任务 - %date% %time% >> C:\Users\Ramsey\github\my_first_repo\stockapi\logs\schedule_log.txt
cd /d C:\Users\Ramsey\github\my_first_repo\stockapi
python run_stock_analysis.py >> C:\Users\Ramsey\github\my_first_repo\stockapi\logs\schedule_log.txt 2>&1
echo 任务执行完成 - %date% %time% >> C:\Users\Ramsey\github\my_first_repo\stockapi\logs\schedule_log.txt