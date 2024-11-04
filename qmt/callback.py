# coding:utf-8
import time
import sys
from xtquant import xtdata
import io
from datetime import datetime

# 重定向标准输出到 UTF-8 编码的输出流并确保实时输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

# 设置股票代码
code_list = ['600039.SH',"600000.SH",'600481.SH']
# code = '600039.SH'

# 获取全推数据
# full_tick = xtdata.get_full_tick([code])
# print('全推数据 日线最新值:', full_tick)

# 下载历史数据，下载接口本身不返回数据
# xtdata.download_history_data(code, period='1m', start_time='20230701')

# 订阅最新行情
def callback_func(data):
    # 获取当前时间，格式化为字符串
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 实时打印回调触发的数据，确保中文输出
    print(f'回调触发 [{current_time}]:', data)

for code in code_list:
    xtdata.subscribe_quote(code, period='1m', count=-1, callback=callback_func)

# 一次性取数据
# data = xtdata.get_market_data(['close'], [code], period='1m', start_time='20230701')
# print('一次性取数据:', data)

# 死循环，阻塞主线程退出
xtdata.run()
