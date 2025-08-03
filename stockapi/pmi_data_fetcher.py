import akshare as ak
import json
import pandas as pd
from datetime import datetime
import logging
import glob
import os

# 设置日志配置
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f'pmi_fetcher_{current_time}.log'

# 清理历史日志文件
logger = logging.getLogger()
logger.info("清理历史日志文件...")
for old_log in glob.glob('pmi_fetcher_*.log'):
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

# 转换为列表并按日期排序
reshaped_data_list = list(reshaped_data.values())
reshaped_data_list.sort(key=lambda x: x['date'])

# 保存重新组织的数据
logger.info("保存重新组织的数据到JSON文件...")
with open('pmi_data.json', 'w', encoding='utf-8') as f:
    json.dump(reshaped_data_list, f, ensure_ascii=False, indent=4)

logger.info(f"数据已重新组织并保存，共{len(reshaped_data_list)}个月份的记录")
logger.info(f"日期范围：{reshaped_data_list[0]['date']} 至 {reshaped_data_list[-1]['date']}")
logger.info(f"每个月份包含{len(reshaped_data_list[0]['indicators'])}个指标")
logger.info("PMI数据获取和处理完成！")