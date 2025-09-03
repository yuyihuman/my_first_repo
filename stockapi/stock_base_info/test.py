from xtquant import xtdata
import pandas as pd
import os

# 设置股票代码
code_list = ['600039.SH',"600000.SH",'600481.SH']

def callback_func(data):
    print(data)

xtdata.download_financial_data2(code_list, table_list=[], start_time='19900101', end_time='', callback=callback_func)

data = xtdata.get_financial_data(code_list, table_list=[], start_time='', end_time='', report_type='report_time')
print(data)

# 将数据保存到CSV文件
if data is not None:
    # 创建输出目录
    base_output_dir = "financial_data"
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)
    
    # 检查数据类型并处理
    if isinstance(data, dict):
        print(f"获取到 {len(data)} 个股票的财务数据")
        
        # 为每个股票代码分别保存数据
        for stock_code, stock_data in data.items():
            # 为每个股票创建单独的文件夹
            stock_dir = os.path.join(base_output_dir, stock_code)
            if not os.path.exists(stock_dir):
                os.makedirs(stock_dir)
                
            if isinstance(stock_data, dict):
                # 如果股票数据也是字典（包含多个报表类型）
                for table_name, table_data in stock_data.items():
                    if hasattr(table_data, 'to_csv') and not table_data.empty:
                        csv_filename = os.path.join(stock_dir, f"{table_name}.csv")
                        table_data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
                        print(f"已保存 {stock_code} 的 {table_name} 数据到: {csv_filename}")
                        print(f"数据形状: {table_data.shape}")
            elif hasattr(stock_data, 'to_csv') and not stock_data.empty:
                # 如果股票数据直接是DataFrame
                csv_filename = os.path.join(stock_dir, "financial_data.csv")
                stock_data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
                print(f"已保存 {stock_code} 的财务数据到: {csv_filename}")
                print(f"数据形状: {stock_data.shape}")
            
    elif hasattr(data, 'to_csv'):
        # 如果已经是DataFrame
        if not data.empty:
            csv_filename = os.path.join(base_output_dir, "financial_data.csv")
            data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
            print(f"财务数据已保存到: {csv_filename}")
            print(f"数据形状: {data.shape}")
        else:
            print("数据为空")
    else:
        print(f"数据类型: {type(data)}")
        print(f"数据内容: {data}")
else:
    print("没有获取到财务数据")
