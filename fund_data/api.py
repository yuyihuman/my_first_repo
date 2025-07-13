import akshare as ak
import pandas as pd

# 获取ETF数据
df = ak.fund_etf_spot_em()

# 将总市值转换为亿单位
df['总市值'] = df['总市值'] / 100000000

# 按总市值降序排序
df = df.sort_values('总市值', ascending=False)

# 保存到CSV文件
df.to_csv('output/fund_data.csv', index=False, encoding='utf-8-sig')
print(df)