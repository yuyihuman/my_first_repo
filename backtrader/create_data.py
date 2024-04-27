from datetime import datetime
 
import backtrader as bt
import matplotlib.pyplot as plt
import akshare as ak
import pandas as pd
 
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
 
stock_hfq_df = ak.stock_zh_a_daily(symbol="sh600000", adjust="hfq")  # 利用 AkShare 获取后复权数据
pd.set_option('display.max_columns', None) # 展示所有列
 
stock_hfq_df.rename(columns={'date':'datetime'},inplace=True)

stock_hfq_df.to_csv('output_file.csv', index=False)