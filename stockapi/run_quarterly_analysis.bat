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
python commodity_price_index.py
python true_quarterly_analysis.py
python pmi_data_fetcher.py
