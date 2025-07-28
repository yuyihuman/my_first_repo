# coding:utf-8
import pandas as pd
import os
from xtquant import xtdata

def read_csi300_constituents(file_path):
    """
    从沪深300成分股Excel文件中读取股票代码和名称。
    假设文件包含'Constituent Code'和'Constituent Name'列。
    """
    if not os.path.exists(file_path):
        print(f"错误：文件 '{file_path}' 不存在。")
        return []

    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)

        # 检查所需列是否存在
        required_columns = ['成份券代码Constituent Code', '成份券名称Constituent Name']
        if not all(col in df.columns for col in required_columns):
            print(f"错误：Excel文件缺少必要的列。所需列：{required_columns}，实际列：{df.columns.tolist()}")
            return []

        # 提取股票代码和名称
        constituents_list = []
        for index, row in df.iterrows():
            code = str(row['成份券代码Constituent Code']).strip().zfill(6)
            name = str(row['成份券名称Constituent Name']).strip()
            # 根据交易所信息添加后缀
            exchange = str(row['交易所Exchange']).strip()
            if exchange == '上海证券交易所':
                code_with_suffix = f"{code}.SH"
            elif exchange == '深圳证券交易所':
                code_with_suffix = f"{code}.SZ"
            else:
                print(f"警告：股票 {code} 的交易所信息 '{exchange}' 无法识别，将跳过此股票。")
                continue # 跳过当前循环，不将此股票添加到列表中
            
            constituents_list.append(code_with_suffix)
        
        return constituents_list

    except Exception as e:
        print(f"读取或处理Excel文件时发生错误: {e}")
        return []

def filter_stocks_with_data_since_2010(stock_list):
    """
    过滤掉2010年之前没有交易数据的股票
    """
    valid_stocks = []
    
    print(f"开始检查 {len(stock_list)} 只股票的历史数据...")
    
    # 先批量下载所有股票的历史数据，从2000年开始
    print("正在批量下载历史数据...")
    for stock_code in stock_list:
        try:
            xtdata.download_history_data(stock_code, period='1d', start_time='20000101')
        except Exception as e:
            print(f"下载 {stock_code} 数据时发生错误: {e}")
    
    print("下载完成，开始检查数据有效性...")
    
    # 分批处理，每次处理50只股票
    batch_size = 50
    for batch_start in range(0, len(stock_list), batch_size):
        batch_end = min(batch_start + batch_size, len(stock_list))
        batch_stocks = stock_list[batch_start:batch_end]
        
        print(f"\n处理第 {batch_start//batch_size + 1} 批股票 ({batch_start+1}-{batch_end})...")
        
        try:
            # 批量获取所有历史数据
            data = xtdata.get_market_data(['close'], batch_stocks, period='1d', 
                                        start_time='20000101')
            
            if data and 'close' in data:
                df = data['close']
                # 找出2010年的日期列
                dates_2010 = [d for d in df.columns if str(d).startswith('2010')]
                
                if dates_2010:
                    print(f"  找到 {len(dates_2010)} 个2010年交易日")
                    
                    for stock_code in batch_stocks:
                        if stock_code in df.index:
                            # 获取该股票2010年的数据
                            stock_data_2010 = df.loc[stock_code, dates_2010]
                            valid_data_2010 = stock_data_2010.dropna()
                            
                            if len(valid_data_2010) > 0:
                                valid_stocks.append(stock_code)
                                print(f"  ✓ {stock_code} 在2010年有 {len(valid_data_2010)} 个交易日数据")
                            else:
                                print(f"  ✗ {stock_code} 在2010年没有有效数据")
                        else:
                            print(f"  ✗ {stock_code} 不在返回的数据中")
                else:
                    print(f"  ✗ 没有找到2010年的数据")
            else:
                print(f"  ✗ 批量获取数据失败")
                
        except Exception as e:
            print(f"  ✗ 批量处理时发生错误: {e}")
            # 如果批量处理失败，尝试单个处理
            for stock_code in batch_stocks:
                try:
                    data = xtdata.get_market_data(['close'], [stock_code], period='1d', 
                                                start_time='20000101')
                    if data and 'close' in data:
                        df = data['close']
                        dates_2010 = [d for d in df.columns if str(d).startswith('2010')]
                        
                        if dates_2010 and stock_code in df.index:
                            stock_data_2010 = df.loc[stock_code, dates_2010]
                            valid_data_2010 = stock_data_2010.dropna()
                            
                            if len(valid_data_2010) > 0:
                                valid_stocks.append(stock_code)
                                print(f"  ✓ {stock_code} 在2010年有 {len(valid_data_2010)} 个交易日数据")
                            else:
                                print(f"  ✗ {stock_code} 在2010年没有有效数据")
                        else:
                            print(f"  ✗ {stock_code} 无法获取2010年数据")
                    else:
                        print(f"  ✗ {stock_code} 无法获取数据")
                except Exception as e2:
                    print(f"  ✗ {stock_code} 单独检查时发生错误: {e2}")
    
    return valid_stocks

def main():
    # 连接xtdata
    print("正在连接xtdata...")
    xtdata.connect()
    
    # 读取沪深300成分股列表
    xls_file_path = "000300cons.xls"
    print("正在读取沪深300成分股列表...")
    
    constituents = read_csi300_constituents(xls_file_path)
    
    if not constituents:
        print("无法读取沪深300成分股列表，程序退出。")
        return
    
    print(f"成功读取 {len(constituents)} 只沪深300成分股")
    
    # 过滤掉2010年之前没有交易数据的股票
    valid_stocks = filter_stocks_with_data_since_2010(constituents)
    
    print(f"\n=== 过滤结果 ===")
    print(f"原始股票数量: {len(constituents)}")
    print(f"有效股票数量: {len(valid_stocks)}")
    print(f"被过滤股票数量: {len(constituents) - len(valid_stocks)}")
    
    print(f"\n=== 有效股票列表 ===")
    for i, stock_code in enumerate(valid_stocks, 1):
        print(f"{i:3d}. {stock_code}")
    
    # 保存结果到文件
    output_file = "filtered_csi300_stocks.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 沪深300成分股（过滤掉2010年之前没有交易数据的股票）\n")
        f.write(f"# 原始数量: {len(constituents)}\n")
        f.write(f"# 有效数量: {len(valid_stocks)}\n")
        f.write(f"# 生成时间: {pd.Timestamp.now()}\n\n")
        for stock_code in valid_stocks:
            f.write(f"{stock_code}\n")
    
    print(f"\n结果已保存到文件: {output_file}")
    
    return valid_stocks

if __name__ == "__main__":
    valid_stocks = main()