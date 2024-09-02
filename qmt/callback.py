
# coding:utf-8
import time

from xtquant import xtdata

code = '600000.SH'

#取全推数据
full_tick = xtdata.get_full_tick([code])
print('全推数据 日线最新值', full_tick)

#下载历史数据 下载接口本身不返回数据
xtdata.download_history_data(code, period='1m', start_time='20230701')

#订阅最新行情
def callback_func(data):
    print('回调触发', data)

xtdata.subscribe_quote(code, period='1m', count=-1, callback= callback_func)
data = xtdata.get_market_data(['close'], [code], period='1m', start_time='20230701')
print('一次性取数据', data)

#死循环 阻塞主线程退出
xtdata.run()

