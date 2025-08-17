import akshare as ak

# 获取上海房价数据
house_price_df = ak.macro_china_new_house_price(city_first="上海")
print(house_price_df)
