@echo off
cd /d "%~dp0"

echo 正在清除日志文件夹...
if exist "stock_base_info\logs" (
    del /q /s "stock_base_info\logs\*.*" > nul 2>&1
    echo 日志文件夹内容已清除
)

python stock_base_info\stock_data_fetcher.py
python stock_base_info\get_all_stocks_data.py
python stock_base_info\save_stocks_to_csv.py
python stock_base_info\download_financial_data.py
python stock_base_info\check_data_structure.py
python stock_base_info\financial_data_structure_reader.py
python stock_base_info\check_and_update_names.py
python macro_data_fetch\true_quarterly_analysis.py
python macro_data_fetch\commodity_price_index.py
python macro_data_fetch\pmi_data_fetcher.py

echo 正在清空回测数据目录...
if exist "stock_backtest\data" (
    del /q /s "stock_backtest\data\*.*" > nul 2>&1
    for /d %%i in ("stock_backtest\data\*") do rd /s /q "%%i" > nul 2>&1
    echo 回测数据目录已清空
) else (
    mkdir "stock_backtest\data"
    echo 创建回测数据目录
)

echo 正在复制股票数据到回测目录...
if exist "stock_base_info\all_stocks_data" (
    xcopy "stock_base_info\all_stocks_data" "stock_backtest\data\all_stocks_data\" /e /i /y > nul
    echo all_stocks_data 文件夹复制完成
)

if exist "stock_base_info\financial_data" (
    xcopy "stock_base_info\financial_data" "stock_backtest\data\financial_data\" /e /i /y > nul
    echo financial_data 文件夹复制完成
)

if exist "stock_base_info\stock_name_history.json" (
    copy "stock_base_info\stock_name_history.json" "stock_backtest\data\" > nul
    echo stock_name_history.json 文件复制完成
)

if exist "stock_base_info\stock_data.csv" (
    copy "stock_base_info\stock_data.csv" "stock_backtest\data\" > nul
    echo stock_data.csv 文件复制完成
)

echo 数据复制完成！
