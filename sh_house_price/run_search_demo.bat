@echo off
cd /d %~dp0
if exist "images\final\*" del /q "images\final\*"
python search_demo.py