# coding:utf-8
from xtquant import xtdata

# 设置股票代码
code_list = ['600039.SH',"600000.SH",'600481.SH']

# 下载历史数据，下载接口本身不返回数据
for code in code_list:
    xtdata.download_history_data(code, period='1d', start_time='20230701')

# 一次性取数据
data = xtdata.get_market_data(['close'], code_list, period='1d', start_time='20230701')
print('一次性取数据:', data)
