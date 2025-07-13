import akshare as ak

# stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
# stock_zh_a_spot_em_df.to_csv('output.csv', index=False)

stock_index = "000001"
stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=stock_index, period="daily", start_date="20170301", end_date='20240907', adjust="qfq")
stock_zh_a_hist_df.to_csv(stock_index+'.csv', index=False)