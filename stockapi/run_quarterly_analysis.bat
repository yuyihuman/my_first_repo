@echo off
cd /d "%~dp0"
python commodity_price_index.py
python true_quarterly_analysis.py
python pmi_data_fetcher.py
python stock_base_info\get_all_stocks_data.py