import akshare as ak
import pandas as pd
from datetime import datetime
import os

# 获取A股实时行情数据
print("正在获取A股实时行情数据...")
stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

# 显示基本信息
print(f"获取到 {len(stock_zh_a_spot_em_df)} 只股票的数据")
print(f"数据包含 {len(stock_zh_a_spot_em_df.columns)} 个字段")
print("\n前5只股票预览:")
print(stock_zh_a_spot_em_df.head())

# 生成固定的文件名
filename = "stock_data.csv"

# 保存到CSV文件
stock_zh_a_spot_em_df.to_csv(filename, index=False, encoding='utf-8-sig')
print(f"\n数据已保存到文件: {filename}")
print(f"文件大小: {os.path.getsize(filename) / 1024:.2f} KB")

# 显示列名信息
print("\n数据字段列表:")
for i, col in enumerate(stock_zh_a_spot_em_df.columns, 1):
    print(f"{i:2d}. {col}")