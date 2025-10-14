from xtquant import xtdata

# 获取所有A股股票的代码和名称
full_code = ['000001.SZ', '600000.SH']
daily_data = xtdata.get_market_data([], full_code, period='1d', start_time='19900101', dividend_type='none')
print("数据结构预览:")
print(f"数据类型: {type(daily_data)}")
print(f"主要键: {list(daily_data.keys())}")
print()

# 打印每个股票的收盘价
print("股票收盘价数据:")
for code in full_code:
    if code in daily_data['close'].index:
        close_prices = daily_data['close'].loc[code]
        print(f"{code} 的收盘价: {close_prices}")
    else:
        print(f"{code} 没有找到数据")
