import akshare as ak
import os
import time
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告
urllib3.disable_warnings(InsecureRequestWarning)

# 禁用代理设置
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
              'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']
for var in proxy_vars:
    os.environ.pop(var, None)

# 强制设置为空
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

print("正在获取A股实时行情数据...")

# 使用可用的股票基本信息接口
try:
    print("正在获取A股基本信息...")
    stock_data_df = ak.stock_info_a_code_name()
    
    # 检查数据是否有效
    if stock_data_df is None or len(stock_data_df) == 0:
        raise ValueError("获取到的数据为空")
    
    print("✅ 数据获取成功！")
    successful_source = "股票基本信息接口"
    
except Exception as e:
    print(f"❌ 数据获取失败: {e}")
    print("可能的解决方案:")
    print("1. 检查网络连接")
    print("2. 稍后再试")
    print("3. 检查防火墙设置")
    exit(1)

print(f"\n成功使用 {successful_source} 获取数据！")

# 显示基本信息
print(f"获取到 {len(stock_data_df)} 只股票的数据")
print(f"数据包含 {len(stock_data_df.columns)} 个字段")
print("\n前5只股票预览:")
print(stock_data_df.head())

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 生成固定的文件名（保存在脚本所在目录）
filename = "stock_data.csv"
full_path = os.path.join(script_dir, filename)

# 保存到CSV文件
stock_data_df.to_csv(full_path, index=False, encoding='utf-8-sig')
print(f"\n数据已保存到文件: {full_path}")
print(f"文件大小: {os.path.getsize(full_path) / 1024:.2f} KB")

# 显示列名信息
print("\n数据字段列表:")
for i, col in enumerate(stock_data_df.columns, 1):
    print(f"{i:2d}. {col}")