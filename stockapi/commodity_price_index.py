import akshare as ak
import os
import glob
import datetime
import json
import pandas as pd

# 清理历史日志文件
for log_file in glob.glob('filtered_futures_*.log'):
    try:
        os.remove(log_file)
        print(f"已删除历史日志文件: {log_file}")
    except Exception as e:
        print(f"删除日志文件{log_file}失败: {e}")

# 清理历史数据文件
for log_file in glob.glob('futures_hist_data_*.log'):
    try:
        os.remove(log_file)
        print(f"已删除历史数据文件: {log_file}")
    except Exception as e:
        print(f"删除数据文件{log_file}失败: {e}")

# 获取期货数据
futures_data = ak.futures_hist_table_em()

# 过滤条件：只保留上期所和上期能源的主连合约，排除次主连
filtered_df = futures_data[(futures_data['市场简称'].isin(['上期所', '上期能源'])) & ~futures_data['合约中文代码'].str.contains('次主连') & futures_data['合约中文代码'].str.contains('主连')]
print(filtered_df)

# 保存过滤结果到统一日志文件
log_file = "commodity_data.log"
filtered_df.to_csv(log_file, index=False, encoding='utf-8-sig')
print(f"过滤结果已保存到: {log_file}")

# 获取每个合约的历史数据
all_hist_data = []
for symbol in filtered_df['合约中文代码']:
    try:
        hist_data = ak.futures_hist_em(symbol=symbol, period="daily")
        # 只保留前后各10条数据
        hist_data = pd.concat([hist_data.head(10), hist_data.tail(10)]).drop_duplicates()
        hist_data['合约代码'] = symbol
        all_hist_data.append(hist_data)
        print(f"已获取合约 {symbol} 的历史数据")
    except Exception as e:
        print(f"获取合约 {symbol} 历史数据失败: {e}")

# 合并所有历史数据并追加到日志文件
if all_hist_data:
    combined_df = pd.concat(all_hist_data)
    combined_df.to_csv(log_file, mode='a', index=False, encoding='utf-8-sig', header=False)
    print(f"所有合约历史数据已追加到: {log_file}")
    
    # 创建商品价格指数
    print("\n开始计算商品价格指数...")
    
    # 检查DataFrame列名并调整
    print(f"DataFrame列名: {list(combined_df.columns)}")
    
    # 根据实际列名进行处理
    date_col = None
    close_col = None
    
    for col in combined_df.columns:
        if '日期' in col or 'date' in col.lower():
            date_col = col
        elif '收盘' in col or 'close' in col.lower():
            close_col = col
    
    if date_col is None or close_col is None:
        print(f"无法找到日期或收盘价列，可用列: {list(combined_df.columns)}")
        print("使用默认列名处理...")
        # 尝试使用第一列作为日期，第四列作为收盘价（通常的期货数据格式）
        if len(combined_df.columns) >= 4:
            date_col = combined_df.columns[0]
            close_col = combined_df.columns[3]
        else:
            print("数据格式不符合预期，无法计算指数")
            date_col = close_col = None
    
    if date_col and close_col:
        # 按日期分组计算每日涨跌幅
        combined_df[date_col] = pd.to_datetime(combined_df[date_col])
        
        # 为每个合约计算涨跌幅
        combined_df = combined_df.sort_values([date_col, '合约代码'])
        combined_df['涨跌幅_计算'] = combined_df.groupby('合约代码')[close_col].pct_change() * 100
        
        # 计算每日所有品种的平均涨跌幅
        daily_returns = combined_df.groupby(date_col)['涨跌幅_计算'].mean().reset_index()
        daily_returns = daily_returns.sort_values(date_col)
        
        # 以100为基准点，累计涨跌幅计算指数
        if len(daily_returns) > 0:
            daily_returns['商品价格指数'] = 100.0
            for i in range(1, len(daily_returns)):
                prev_index = daily_returns.iloc[i-1]['商品价格指数']
                daily_change = daily_returns.iloc[i]['涨跌幅_计算']
                if pd.notna(daily_change):
                    daily_returns.iloc[i, daily_returns.columns.get_loc('商品价格指数')] = prev_index * (1 + daily_change / 100)
                else:
                    daily_returns.iloc[i, daily_returns.columns.get_loc('商品价格指数')] = prev_index
            
            index_data = daily_returns
            
            # 转换为JSON格式保存
            index_json = {
                "指数名称": "上期所商品价格指数",
                "基准日期": index_data.iloc[0][date_col].strftime('%Y-%m-%d'),
                "基准点位": 100.0,
                "计算方法": "基于每日涨跌幅平均值的累计指数",
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "包含品种": list(filtered_df['合约中文代码'].unique()),
                "指数数据": [
                    {
                        "日期": row[date_col].strftime('%Y-%m-%d'),
                        "指数值": round(row['商品价格指数'], 2),
                        "日涨跌幅": round(row['涨跌幅_计算'], 4) if pd.notna(row['涨跌幅_计算']) else 0.0
                    }
                    for _, row in index_data.iterrows()
                ]
            }
            
            # 保存指数到JSON文件
            with open('commodity_price_index.json', 'w', encoding='utf-8') as f:
                json.dump(index_json, f, ensure_ascii=False, indent=2)
            
            print(f"商品价格指数已保存到: commodity_price_index.json")
            print(f"指数包含 {len(index_json['包含品种'])} 个品种")
            print(f"指数数据包含 {len(index_json['指数数据'])} 个交易日")
            if len(index_data) > 0:
                print(f"最新指数值: {index_data.iloc[-1]['商品价格指数']:.2f}")
        else:
            print("没有足够的数据计算指数")
    else:
        print("无法识别数据列名，跳过指数计算")
else:
    print("没有获取到任何合约的历史数据")