import json
import os
import matplotlib.pyplot as plt
import numpy as np
import re
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
matplotlib.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 设置输出文件夹
output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 读取JSON文件
json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'fund_info.json')
with open(json_file_path, 'r', encoding='utf-8') as f:
    fund_data = json.load(f)

# 修改为提取字典中的值（基金信息）组成列表
fund_list = list(fund_data.values())

# 提取包含ETF的基金
etf_funds = []
for fund in fund_list:
    if 'ETF' in fund.get('基金名称', ''):
        etf_funds.append(fund)

# 定义函数将规模字符串转换为数值（单位：亿）
def convert_scale_to_number(scale_str):
    if not scale_str or scale_str == '0万':
        return 0
    
    # 提取数字部分
    match = re.search(r'([\d.]+)(亿|万)', scale_str)
    if not match:
        return 0
    
    value = float(match.group(1))
    unit = match.group(2)
    
    # 转换为亿
    if unit == '万':
        value = value / 10000
    
    return value

# 为每个基金添加数值化的规模
for fund in etf_funds:
    fund['规模数值'] = convert_scale_to_number(fund.get('最新规模', '0万'))

# 按规模排序（降序）
sorted_etf_funds = sorted(etf_funds, key=lambda x: x['规模数值'], reverse=True)

# 取前30个基金
top_30_funds = sorted_etf_funds[:30]

# 准备绘图数据
fund_names = [fund['基金名称'] for fund in top_30_funds]
fund_scales = [fund['规模数值'] for fund in top_30_funds]

# 创建图表
plt.figure(figsize=(15, 10))
bars = plt.bar(range(len(fund_names)), fund_scales, color='skyblue')

# 添加标题和标签
plt.title('ETF基金规模排名前30', fontsize=16)
plt.xlabel('基金名称', fontsize=12)
plt.ylabel('规模（亿元）', fontsize=12)

# 设置x轴刻度
plt.xticks(range(len(fund_names)), fund_names, rotation=45, ha='right', fontsize=8)

# 在柱状图上显示具体数值
for i, bar in enumerate(bars):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
             f'{height:.2f}亿',
             ha='center', va='bottom', fontsize=8)

# 调整布局
plt.tight_layout()

# 保存图表
output_file = os.path.join(output_folder, 'top_30_etf_funds.png')
plt.savefig(output_file, dpi=300)
print(f'图表已保存至: {output_file}')

# 显示图表（可选）
# plt.show()