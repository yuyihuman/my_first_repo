import sys
import os
import json
import time
from datetime import datetime

# 添加上级目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import akshare as ak
import pandas as pd
from extract_fund_scale import extract_fund_scale_table, setup_logger

def get_fund_list():
    """
    获取ETF基金列表
    """
    print("正在获取ETF基金列表...")
    df = ak.fund_etf_spot_em()
    
    # 将总市值转换为亿单位
    df['总市值'] = df['总市值'] / 100000000
    
    # 按总市值降序排序
    df = df.sort_values('总市值', ascending=False)
    
    # 保存基金列表到CSV
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    df.to_csv('output/fund_data.csv', index=False, encoding='utf-8-sig')
    print(f"基金列表已保存到 output/fund_data.csv，共 {len(df)} 只基金")
    
    return df

def batch_extract_fund_scales(fund_df, max_funds=10, wait_time=10):
    """
    批量提取基金规模信息
    
    参数:
        fund_df: 基金列表DataFrame
        max_funds: 最大处理基金数量（默认10只，避免请求过多）
        wait_time: 每个请求的等待时间
    """
    logger = setup_logger()
    
    # 限制处理的基金数量
    funds_to_process = fund_df.head(max_funds)
    
    all_fund_data = []
    successful_extractions = 0
    failed_extractions = 0
    
    print(f"开始批量提取 {len(funds_to_process)} 只基金的规模信息...")
    
    for process_index, (index, fund_row) in enumerate(funds_to_process.iterrows(), 1):
        fund_code = fund_row['代码']
        fund_name = fund_row['名称']
        
        print(f"\n正在处理第 {process_index}/{len(funds_to_process)} 只基金: {fund_code} - {fund_name}")
        
        try:
            # 构建URL
            url = f"https://fundf10.eastmoney.com/gmbd_{fund_code}.html"
            
            # 提取规模数据
            scale_df = extract_fund_scale_table(
                url=url,
                output_file=f"{fund_code}_fund_scale.csv",
                wait_time=wait_time,
                log_file=None,
                output_dir="output"
            )
            
            if scale_df is not None and not scale_df.empty:
                # 准备基金信息
                fund_info = {
                    "基金代码": fund_code,
                    "基金名称": fund_name,
                    "总市值_亿元": float(fund_row['总市值']),
                    "最新价": float(fund_row['最新价']) if pd.notna(fund_row['最新价']) else None,
                    "涨跌幅": float(fund_row['涨跌幅']) if pd.notna(fund_row['涨跌幅']) else None,
                    "规模变动数据": scale_df.to_dict('records'),
                    "数据提取时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "数据条数": len(scale_df)
                }
                
                all_fund_data.append(fund_info)
                successful_extractions += 1
                print(f"✓ 成功提取 {fund_code} 的规模数据，共 {len(scale_df)} 条记录")
                
                # 每处理完一个基金就保存一次JSON
                save_to_json(all_fund_data, "all_fund_scales.json")
                print(f"已保存 {len(all_fund_data)} 只基金的数据到JSON文件")
                
            else:
                print(f"✗ 未能提取到 {fund_code} 的规模数据")
                failed_extractions += 1
                
        except Exception as e:
            print(f"✗ 处理 {fund_code} 时发生错误: {str(e)}")
            logger.error(f"处理基金 {fund_code} 时发生错误: {str(e)}", exc_info=True)
            failed_extractions += 1
        
        # 添加延迟，避免请求过于频繁
        if process_index < len(funds_to_process):
            print(f"等待 {wait_time} 秒后处理下一只基金...")
            time.sleep(wait_time)
    
    print(f"\n批量提取完成！成功: {successful_extractions}, 失败: {failed_extractions}")
    return all_fund_data

def save_to_json(data, filename="all_fund_scales.json"):
    """
    将数据保存为JSON格式
    """
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = os.path.join(output_dir, filename)
    
    # 添加汇总信息
    summary_data = {
        "汇总信息": {
            "提取时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "基金总数": len(data),
            "数据来源": "东方财富网"
        },
        "基金数据": data
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    print(f"所有基金数据已保存到 {output_path}")
    return output_path

def main():
    """
    主函数
    """
    print("=== 批量提取基金规模信息脚本 ===")
    print("第一步：获取基金列表")
    
    try:
        # 第一步：获取基金列表
        fund_df = get_fund_list()
        
        print("\n第二步：批量提取基金规模信息")
        print("注意：为避免对服务器造成过大压力，默认只处理前10只基金")
        print("如需处理更多基金，请修改 max_funds 参数")
        
        # 第二步：批量提取规模信息
        all_fund_data = batch_extract_fund_scales(
            fund_df=fund_df,
            max_funds=10,  # 可以根据需要调整
            wait_time=15   # 增加等待时间，避免被限制
        )
        
        if all_fund_data:
            print("\n第三步：保存JSON数据")
            # 保存为JSON格式
            json_file = save_to_json(all_fund_data)
            
            print(f"\n=== 处理完成 ===")
            print(f"基金列表CSV: output/fund_data.csv")
            print(f"各基金规模CSV: output/{{基金代码}}_fund_scale.csv")
            print(f"汇总JSON文件: {json_file}")
            print(f"成功处理 {len(all_fund_data)} 只基金")
        else:
            print("\n未能成功提取任何基金的规模数据")
            
    except Exception as e:
        print(f"脚本执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="批量提取基金规模信息")
    parser.add_argument("--max-funds", type=int, default=10, help="最大处理基金数量（默认10）")
    parser.add_argument("--wait-time", type=int, default=15, help="每个请求的等待时间（秒，默认15）")
    parser.add_argument("--output-json", default="all_fund_scales.json", help="输出JSON文件名")
    
    args = parser.parse_args()
    
    # 如果有命令行参数，使用参数值
    if len(sys.argv) > 1:
        try:
            fund_df = get_fund_list()
            all_fund_data = batch_extract_fund_scales(
                fund_df=fund_df,
                max_funds=args.max_funds,
                wait_time=args.wait_time
            )
            if all_fund_data:
                save_to_json(all_fund_data, args.output_json)
        except Exception as e:
            print(f"执行错误: {str(e)}")
    else:
        # 直接运行主函数
        main()