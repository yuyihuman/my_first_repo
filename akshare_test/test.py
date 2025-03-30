import akshare as ak

stock_financial_cash_ths_df = ak.stock_financial_cash_ths(symbol="000063", indicator="按单季度")
print(stock_financial_cash_ths_df.info())