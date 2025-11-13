import akshare as ak
import os
import time
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import pandas as pd
from pathlib import Path

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
base_path = Path(script_dir)
financial_dir = base_path / "financial_data"

def _code_to_symbol(code: str) -> str:
    """将股票代码转换为目录用的带交易所后缀的符号，如 000001 -> 000001.SZ / 600000 -> 600000.SH"""
    code_str = str(code)
    if code_str.startswith("6"):
        return f"{code_str}.SH"
    else:
        return f"{code_str}.SZ"

def _read_latest_quarter_profit(income_csv_path: Path) -> float | None:
    """读取指定 Income.csv，返回最新一期的净利润（优先使用归母净利润）。"""
    if not income_csv_path.exists():
        return None
    # 兼容不同编码
    df = None
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            df = pd.read_csv(income_csv_path, encoding=enc)
            break
        except Exception:
            df = None
    if df is None or df.empty:
        return None
    # 选择用于确定最新季度的时间字段
    time_col = None
    for col in ["m_timetag", "endDate", "m_anntime"]:
        if col in df.columns:
            time_col = col
            break
    if time_col is None:
        return None
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df = df.dropna(subset=[time_col])
    if df.empty:
        return None
    latest_row = df.loc[df[time_col].idxmax()]
    # 优先取归母净利润，其次取含少数股东损益的净利润
    profit_col = None
    for col in [
        "net_profit_excl_min_int_inc",  # 归属于母公司净利润
        "net_profit_incl_min_int_inc",  # 含少数股东损益
        "net_profit"                     # 兜底
    ]:
        if col in df.columns:
            profit_col = col
            break
    if profit_col is None:
        return None
    try:
        return float(latest_row[profit_col])
    except Exception:
        return None

# 将最近一个季度的利润加入到基本信息数据中
print("\n正在为每只股票追加最近一个季度的利润...")
code_col = "code" if "code" in stock_data_df.columns else ("代码" if "代码" in stock_data_df.columns else None)
if code_col is None:
    raise ValueError("未找到股票代码列，无法匹配财务数据。期望列名为 'code' 或 '代码'")

latest_profits = []
total = len(stock_data_df)
for idx, code in enumerate(stock_data_df[code_col].astype(str)):
    symbol = _code_to_symbol(code)
    income_csv = financial_dir / symbol / "Income.csv"
    profit = _read_latest_quarter_profit(income_csv)
    latest_profits.append(profit)
    # 简单进度提示，每处理500只打印一次
    if (idx + 1) % 500 == 0:
        print(f"已处理 {idx + 1}/{total} 支股票...")

# 添加新列
new_col_name = "最近一个季度的利润"
stock_data_df[new_col_name] = latest_profits
print("追加完成。\n前5行新列预览：")
print(stock_data_df[[code_col, new_col_name]].head())

# 生成固定的文件名（保存在脚本所在目录）
filename = "stock_data.csv"
full_path = os.path.join(script_dir, filename)

# 按最近一个季度的利润从大到小排序
print("\n按最近一个季度的利润降序排序...")
# 强制将新列转换为数值，无法解析的值置为 NaN，确保 NaN 排到最后
stock_data_df[new_col_name] = pd.to_numeric(stock_data_df[new_col_name], errors='coerce')
stock_data_df_sorted = stock_data_df.sort_values(by=new_col_name, ascending=False, na_position='last').reset_index(drop=True)
name_col = "name" if "name" in stock_data_df.columns else ("名称" if "名称" in stock_data_df.columns else None)
if name_col:
    print("排序后前5行预览：")
    print(stock_data_df_sorted[[code_col, name_col, new_col_name]].head())
else:
    print("排序后前5行预览：")
    print(stock_data_df_sorted[[code_col, new_col_name]].head())

# 保存到CSV文件
stock_data_df_sorted.to_csv(full_path, index=False, encoding='utf-8-sig')
print(f"\n数据已保存到文件: {full_path}")
print(f"文件大小: {os.path.getsize(full_path) / 1024:.2f} KB")

# 显示列名信息
print("\n数据字段列表:")
for i, col in enumerate(stock_data_df_sorted.columns, 1):
    print(f"{i:2d}. {col}")