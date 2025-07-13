import akshare as ak
import pandas as pd
import os

def get_hk_ggt_stocks(output_dir="data"):
    """
    获取港股通成分股列表
    
    参数:
        output_dir: 输出文件夹路径
    
    返回:
        DataFrame: 包含港股通成分股代码和名称的DataFrame
    """
    print("正在获取港股通成分股列表...")
    
    # 使用akshare获取港股通成分股数据
    df = ak.stock_hk_ggt_components_em()
    
    # 只保留代码和名称列
    result_df = df[['代码', '名称']]
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 保存到CSV文件
    output_file = os.path.join(output_dir, "hk_ggt_stocks.csv")
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"港股通成分股列表已保存到: {output_file}")
    
    return result_df

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="获取港股通成分股列表")
    parser.add_argument("--dir", default="data", help="输出文件夹路径（默认为'data'）")
    
    args = parser.parse_args()
    
    # 获取港股通成分股列表
    stocks_df = get_hk_ggt_stocks(args.dir)
    
    # 打印前10条记录
    print("\n港股通成分股列表（前10条）:")
    print(stocks_df.head(10))
    
    # 统计信息
    print(f"\n共获取到 {len(stocks_df)} 只港股通成分股")