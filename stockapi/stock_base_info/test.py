import akshare as ak

# 查询股票代码为 000503 的曾用名
stock_info_change_name_list = ak.stock_info_change_name(symbol="000503")
print(stock_info_change_name_list)