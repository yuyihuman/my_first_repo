import akshare as ak
import json
import pandas as pd
from datetime import datetime
import logging
import glob
import os
import shutil

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 设置日志配置
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = os.path.join(script_dir, f'pmi_fetcher_{current_time}.log')

# 清理历史日志文件
logger = logging.getLogger()
logger.info("清理历史日志文件...")
for old_log in glob.glob(os.path.join(script_dir, 'pmi_fetcher_*.log')):
    if old_log != log_filename:  # 跳过当前日志文件
        try:
            os.remove(old_log)
            print(f"已删除历史日志文件: {old_log}")
        except Exception as e:
            print(f"删除日志文件失败 {old_log}: {e}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger()
logger.info("开始获取PMI数据...")

# 获取PMI数据
macro_china_nbs_nation_df = ak.macro_china_nbs_nation(kind="月度数据", path="采购经理指数 > 制造业采购经理指数", period="2010-")
logger.info(f"成功获取PMI数据，数据维度: {macro_china_nbs_nation_df.shape}")

# 获取工业生产者购进价格指数数据
logger.info("开始获取工业生产者购进价格指数数据...")
ppi_purchase_df = ak.macro_china_nbs_nation(kind="月度数据", path="价格指数 > 工业生产者购进价格指数 > 工业生产者购进价格指数(上月=100)", period="2010-")
logger.info(f"成功获取工业生产者购进价格指数数据，数据维度: {ppi_purchase_df.shape}")

# 计算工业生产者购进价格指数（以2010年1月为基数100）
logger.info("开始计算工业生产者购进价格指数...")
ppi_cumulative_index = {}

# 计算燃料、动力类购进价格指数（以2010年1月为基数100）
logger.info("开始计算燃料、动力类购进价格指数...")
fuel_power_cumulative_index = {}

# 获取所有月份并排序
all_months = []
for col in ppi_purchase_df.columns:
    try:
        year_month = col.replace('年', '-').replace('月', '')
        date_obj = datetime.strptime(year_month, '%Y-%m')
        all_months.append((date_obj.strftime('%Y-%m'), col))
    except (ValueError, TypeError):
        continue

all_months.sort(key=lambda x: x[0])

# 计算累积指数
base_value = 100.0  # 2010年1月基数
current_index = base_value

for date_str, col in all_months:
    # 获取主要指数值（第一行：工业生产者购进价格指数(上月=100)）
    monthly_change = ppi_purchase_df.iloc[0][col]
    
    if pd.notna(monthly_change):
        # 计算累积指数：当前指数 = 上月指数 * (本月指数/100)
        current_index = current_index * (monthly_change / 100.0)
        ppi_cumulative_index[date_str] = round(current_index, 2)

# 计算燃料、动力类购进价格指数的累积指数
fuel_power_base_value = 100.0  # 2010年1月基数
fuel_power_current_index = fuel_power_base_value

for date_str, col in all_months:
    # 获取燃料、动力类指数值（第二行：燃料、动力类购进价格指数(上月=100)）
    fuel_power_monthly_change = ppi_purchase_df.iloc[1][col]
    
    if pd.notna(fuel_power_monthly_change):
        # 计算累积指数：当前指数 = 上月指数 * (本月指数/100)
        fuel_power_current_index = fuel_power_current_index * (fuel_power_monthly_change / 100.0)
        fuel_power_cumulative_index[date_str] = round(fuel_power_current_index, 2)
        
logger.info(f"工业生产者购进价格指数计算完成，共{len(ppi_cumulative_index)}个月份")
logger.info(f"前5个月份的指数值: {dict(list(ppi_cumulative_index.items())[:5])}")
logger.info(f"后5个月份的指数值: {dict(list(ppi_cumulative_index.items())[-5:])}")

logger.info(f"燃料、动力类购进价格指数计算完成，共{len(fuel_power_cumulative_index)}个月份")
logger.info(f"燃料、动力类前5个月份的指数值: {dict(list(fuel_power_cumulative_index.items())[:5])}")
logger.info(f"燃料、动力类后5个月份的指数值: {dict(list(fuel_power_cumulative_index.items())[-5:])}")

# 为2011年1月设置基数100（作为新的基准点）
if '2011-01' in ppi_cumulative_index:
    # 获取2011年1月的原始计算值
    original_2011_01 = ppi_cumulative_index['2011-01']
    # 重新计算所有月份，以2011年1月为基数100
    adjustment_factor = 100.0 / original_2011_01
    for date_str in ppi_cumulative_index:
        ppi_cumulative_index[date_str] = round(ppi_cumulative_index[date_str] * adjustment_factor, 2)
    logger.info(f"已将工业生产者购进价格指数2011年1月设置为基数100，调整系数: {adjustment_factor:.4f}")

# 为燃料、动力类购进价格指数2011年1月设置基数100
if '2011-01' in fuel_power_cumulative_index:
    # 获取2011年1月的原始计算值
    fuel_power_original_2011_01 = fuel_power_cumulative_index['2011-01']
    # 重新计算所有月份，以2011年1月为基数100
    fuel_power_adjustment_factor = 100.0 / fuel_power_original_2011_01
    for date_str in fuel_power_cumulative_index:
        fuel_power_cumulative_index[date_str] = round(fuel_power_cumulative_index[date_str] * fuel_power_adjustment_factor, 2)
    logger.info(f"已将燃料、动力类购进价格指数2011年1月设置为基数100，调整系数: {fuel_power_adjustment_factor:.4f}")

# 重新组织数据格式：将同一月份的多个指标合并到一个时间条目下
logger.info("开始重新组织数据格式...")
reshaped_data = {}

# 遍历每个指标（行）
for index, row in macro_china_nbs_nation_df.iterrows():
    indicator_name = row.name if hasattr(row, 'name') else macro_china_nbs_nation_df.index[index]
    
    # 遍历每个月份（列）
    for col in macro_china_nbs_nation_df.columns:
        value = row[col]
        if pd.notna(value):  # 只记录非空值
            try:
                # 解析日期
                year_month = col.replace('年', '-').replace('月', '')
                date_obj = datetime.strptime(year_month, '%Y-%m')
                date_str = date_obj.strftime('%Y-%m')
                
                # 如果该日期还没有记录，创建新的条目
                if date_str not in reshaped_data:
                    reshaped_data[date_str] = {
                        'date': date_str,
                        'indicators': {}
                    }
                
                # 添加指标数据
                reshaped_data[date_str]['indicators'][indicator_name] = float(value)
                
            except (ValueError, TypeError):
                continue

# 将工业生产者购进价格指数添加到对应月份（仅2011年及以后）
logger.info(f"开始添加工业生产者购进价格指数到数据中，共{len(ppi_cumulative_index)}个月份")
added_count = 0
for date_str, ppi_value in ppi_cumulative_index.items():
    # 只添加2011年及以后的数据
    if date_str >= '2011-01':
        if date_str in reshaped_data:
            reshaped_data[date_str]['indicators']['工业生产者购进价格指数(2011年1月=100)'] = ppi_value
            added_count += 1
            if added_count <= 5:  # 只记录前5个
                logger.info(f"已添加{date_str}的工业生产者购进价格指数: {ppi_value}")
        else:
            # 如果PMI数据中没有该月份，创建新条目
            reshaped_data[date_str] = {
                'date': date_str,
                'indicators': {'工业生产者购进价格指数(2011年1月=100)': ppi_value}
            }
            added_count += 1
            if added_count <= 5:  # 只记录前5个
                logger.info(f"为{date_str}创建新条目，工业生产者购进价格指数: {ppi_value}")

logger.info(f"工业生产者购进价格指数添加完成，共添加{added_count}个月份（仅2011年及以后）")

# 将燃料、动力类购进价格指数添加到对应月份（仅2011年及以后）
logger.info(f"开始添加燃料、动力类购进价格指数到数据中，共{len(fuel_power_cumulative_index)}个月份")
fuel_power_added_count = 0
for date_str, fuel_power_value in fuel_power_cumulative_index.items():
    # 只添加2011年及以后的数据
    if date_str >= '2011-01':
        if date_str in reshaped_data:
            reshaped_data[date_str]['indicators']['燃料、动力类购进价格指数(2011年1月=100)'] = fuel_power_value
            fuel_power_added_count += 1
            if fuel_power_added_count <= 5:  # 只记录前5个
                logger.info(f"已添加{date_str}的燃料、动力类购进价格指数: {fuel_power_value}")
        else:
            # 如果PMI数据中没有该月份，创建新条目
            reshaped_data[date_str] = {
                'date': date_str,
                'indicators': {'燃料、动力类购进价格指数(2011年1月=100)': fuel_power_value}
            }
            fuel_power_added_count += 1
            if fuel_power_added_count <= 5:  # 只记录前5个
                logger.info(f"为{date_str}创建新条目，燃料、动力类购进价格指数: {fuel_power_value}")

logger.info(f"燃料、动力类购进价格指数添加完成，共添加{fuel_power_added_count}个月份（仅2011年及以后）")

# 转换为列表并按日期排序
reshaped_data_list = list(reshaped_data.values())
reshaped_data_list.sort(key=lambda x: x['date'])

# 保存重新组织的数据
logger.info("保存重新组织的数据到JSON文件...")
json_file_path = os.path.join(script_dir, 'pmi_data.json')
with open(json_file_path, 'w', encoding='utf-8') as f:
    json.dump(reshaped_data_list, f, ensure_ascii=False, indent=4)

logger.info(f"数据已重新组织并保存到: {json_file_path}，共{len(reshaped_data_list)}个月份的记录")

# 备份JSON文件到指定目录
backup_dir = r'C:\Users\17701\github\my_first_repo\stock_info\cache\outsource'
try:
    # 确保备份目录存在
    os.makedirs(backup_dir, exist_ok=True)
    # 复制文件到备份目录
    backup_path = os.path.join(backup_dir, 'pmi_data.json')
    shutil.copy2(json_file_path, backup_path)
    logger.info(f"PMI数据已备份到: {backup_path}")
except Exception as e:
    logger.error(f"备份文件失败: {e}")

logger.info(f"日期范围：{reshaped_data_list[0]['date']} 至 {reshaped_data_list[-1]['date']}")
logger.info(f"每个月份包含{len(reshaped_data_list[0]['indicators'])}个指标")
logger.info("PMI数据获取和处理完成！")