@echo off
cd /d "%~dp0"
python commodity_price_index.py
python true_quarterly_analysis.py