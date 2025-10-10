import akshare as ak

# 获取所有A股股票的代码和名称
df = ak.stock_info_a_code_name()
print(df.head()) # 查看前几行数据