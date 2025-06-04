import akshare as ak
import pandas as pd
import json
import os
import time
from tqdm import tqdm

# 输出目录
OUTPUT_DIR = "output"
# 保存基金详细信息的JSON文件
FUND_INFO_JSON = os.path.join(OUTPUT_DIR, "fund_info.json")
# 每批处理的基金数量
BATCH_SIZE = 100

# 确保输出目录存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 获取已处理的基金列表
def get_processed_funds():
    if not os.path.exists(FUND_INFO_JSON):
        return set()
    
    try:
        with open(FUND_INFO_JSON, "r", encoding="utf-8") as f:
            fund_info = json.load(f)
            return set(fund_info.keys())
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

# 处理NA值，使其可以被JSON序列化
def handle_na_values(obj):
    if isinstance(obj, dict):
        return {k: handle_na_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [handle_na_values(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj

# 保存基金信息到JSON文件
def save_fund_info(fund_info):
    # 处理NA值
    fund_info = handle_na_values(fund_info)
    
    # 如果文件已存在，先读取现有数据
    existing_data = {}
    if os.path.exists(FUND_INFO_JSON):
        try:
            with open(FUND_INFO_JSON, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    # 合并新数据
    existing_data.update(fund_info)
    
    # 保存合并后的数据
    with open(FUND_INFO_JSON, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

# 主函数
def main():
    print("开始获取所有基金代码...")
    # 获取所有基金代码
    fund_name_df = ak.fund_name_em()
    print(f"共获取到 {len(fund_name_df)} 个基金")
    
    # 获取已处理的基金列表
    processed_funds = get_processed_funds()
    print(f"已处理 {len(processed_funds)} 个基金")
    
    # 筛选未处理的基金
    fund_codes = fund_name_df["基金代码"].tolist()
    funds_to_process = [code for code in fund_codes if code not in processed_funds]
    print(f"待处理 {len(funds_to_process)} 个基金")
    
    # 批量处理基金
    current_batch = {}
    batch_count = 0
    
    for i, fund_code in enumerate(tqdm(funds_to_process)):
        try:
            # 获取基金详细信息
            try:
                fund_info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
                
                # 转换为字典格式
                fund_info = {}
                for _, row in fund_info_df.iterrows():
                    fund_info[row["item"]] = row["value"]
                
                # 添加到当前批次
                current_batch[fund_code] = fund_info
            except KeyError as e:
                print(f"获取基金 {fund_code} 详细信息时出错: {e}，跳过此基金")
                continue
            
            # 每处理BATCH_SIZE个基金或处理完最后一个基金时保存一次
            if (i + 1) % BATCH_SIZE == 0 or i == len(funds_to_process) - 1:
                if current_batch:  # 确保有数据才保存
                    batch_count += 1
                    print(f"\n保存第 {batch_count} 批数据，包含 {len(current_batch)} 个基金")
                    save_fund_info(current_batch)
                    current_batch = {}
                
                # 避免频繁请求被限制，每批处理后暂停一下
                if i < len(funds_to_process) - 1:
                    time.sleep(2)  # 增加等待时间，减少被限制的可能性
                    
        except Exception as e:
            print(f"处理基金 {fund_code} 时出错: {e}")
            # 出错时也保存当前批次的数据
            if current_batch:
                batch_count += 1
                print(f"\n保存第 {batch_count} 批数据，包含 {len(current_batch)} 个基金")
                save_fund_info(current_batch)
                current_batch = {}
                time.sleep(5)  # 出错后多等待一段时间
    
    print("\n所有基金处理完成！")

if __name__ == "__main__":
    main()