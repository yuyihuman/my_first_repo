import pandas as pd
import os
import subprocess
import datetime
import time
import random
import argparse
import pandas as pd

def log(msg):
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{now} {msg}", flush=True)

def get_yesterday_date():
    """获取上一个自然日的日期，格式为YYYY-MM-DD"""
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

def get_latest_data_date_for_stock(stock_code):
    """获取指定股票的最新数据日期"""
    data_dir = "data"
    stock_file = os.path.join(data_dir, f"{stock_code}_eastmoney_table.csv")
    
    if not os.path.exists(stock_file):
        return None
    
    try:
        df = pd.read_csv(stock_file, encoding='utf-8-sig')
        if not df.empty and '日期' in df.columns:
            # 获取第一行的日期（最新日期）
            latest_date = pd.to_datetime(df['日期'].iloc[0]).date()
            return latest_date
    except Exception as e:
        log(f"读取文件 {stock_file} 时出错: {e}")
        return None
    
    return None

def needs_update(stock_code, target_date):
    """判断指定股票是否需要更新到目标日期"""
    latest_date = get_latest_data_date_for_stock(stock_code)
    
    if latest_date is None:
        return True  # 文件不存在，需要获取数据
    
    target_date_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    
    return latest_date < target_date_obj

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="批量提取东方财富网港股通持股数据")
    parser.add_argument("--limit", type=int, default=None, help="限制处理的股票数量，默认处理全部")
    parser.add_argument("--retry", type=int, default=3, help="失败时的重试次数，默认为3次")
    parser.add_argument("--delay", type=float, default=2, help="请求之间的延迟时间(秒)，默认为2秒")
    parser.add_argument("--incremental", action="store_true", help="启用增量更新模式，只更新需要更新的股票")
    parser.add_argument("--date", default=None, help="指定更新的日期，格式为YYYY-MM-DD，默认为昨天")
    args = parser.parse_args()
    
    # 设置数据目录
    data_dir = "data"
    
    # 读取港股通成分股列表
    stocks_file = os.path.join(data_dir, "hk_ggt_stocks.csv")
    if not os.path.exists(stocks_file):
        log(f"错误：找不到文件 {stocks_file}")
        log("请先运行 get_hk_ggt_stocks.py 获取港股通成分股列表")
        return
    
    # 读取CSV文件
    stocks_df = pd.read_csv(stocks_file, encoding='utf-8-sig')
    log(f"成功读取 {len(stocks_df)} 只港股通成分股")
    
    # 确保股票代码列是字符串类型，保留前导零
    stocks_df['代码'] = stocks_df['代码'].astype(str).str.zfill(5)
    log("已确保股票代码格式正确（保留前导零）")
    
    # 限制处理的股票数量
    if args.limit is not None and args.limit > 0:
        stocks_df = stocks_df.head(args.limit)
        log(f"根据参数限制，将只处理前 {args.limit} 只股票")
    
    # 获取目标日期
    target_date = args.date if args.date else get_yesterday_date()
    log(f"使用日期: {target_date}")
    
    # 如果启用增量更新模式，筛选需要更新的股票
    if args.incremental:
        log("启用增量更新模式")
        stocks_to_process = []
        for index, row in stocks_df.iterrows():
            stock_code = row['代码'].zfill(5)
            stock_name = row['名称']
            
            if needs_update(stock_code, target_date):
                stocks_to_process.append((index, row))
            else:
                log(f"股票 {stock_code} {stock_name} 数据已是最新，跳过")
        
        if not stocks_to_process:
            log("所有股票数据都已是最新，无需更新")
            return
        
        log(f"需要更新 {len(stocks_to_process)} 只股票的数据")
        # 重新构建DataFrame
        stocks_df = pd.DataFrame([row for index, row in stocks_to_process])
    else:
        log("使用全量更新模式")
    
    # 为每个股票运行脚本
    success_count = 0
    error_count = 0
    
    for index, row in stocks_df.iterrows():
        stock_code = row['代码']
        stock_name = row['名称']
        
        # 确保股票代码是5位数，不足前面补0
        stock_code = stock_code.zfill(5)
        
        # 构建URL
        url = f"https://data.eastmoney.com/hsgt/StockHdDetail/{stock_code}/{target_date}.html"
        
        log(f"\n处理第 {index+1}/{len(stocks_df)} 只股票: {stock_code} {stock_name}")
        log(f"URL: {url}")
        
        # 重试机制
        retry_count = 0
        success = False
        
        while retry_count < args.retry and not success:
            if retry_count > 0:
                log(f"第 {retry_count} 次重试...")
            
            try:
                # 运行extract_eastmoney_table.py脚本
                cmd = ["python", "extract_eastmoney_table.py", url]
                
                # 如果是增量更新模式，添加增量参数
                if args.incremental:
                    cmd.append("--incremental")
                    
                log(f"执行命令: {' '.join(cmd)}")
                
                # 执行命令
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    log(f"成功提取 {stock_code} {stock_name} 的数据")
                    success = True
                    success_count += 1
                else:
                    log(f"提取 {stock_code} {stock_name} 的数据时出错:")
                    log(result.stderr)
                    retry_count += 1
                
            except Exception as e:
                log(f"处理 {stock_code} {stock_name} 时发生异常: {str(e)}")
                retry_count += 1
            
            # 如果失败且还有重试次数，等待一段时间后重试
            if not success and retry_count < args.retry:
                retry_delay = random.uniform(args.delay, args.delay * 2)
                log(f"等待 {retry_delay:.2f} 秒后重试...")
                time.sleep(retry_delay)
        
        # 如果所有重试都失败
        if not success:
            error_count += 1
            log(f"在 {args.retry} 次尝试后仍然无法提取 {stock_code} {stock_name} 的数据")
        
        # 添加随机延迟，避免请求过于频繁
        if index < len(stocks_df) - 1:  # 如果不是最后一只股票
            delay = random.uniform(args.delay * 0.5, args.delay * 1.5)
            log(f"等待 {delay:.2f} 秒后继续...")
            time.sleep(delay)
    
    # 打印统计信息
    log("\n批量处理完成!")
    log(f"总计: {len(stocks_df)} 只股票")
    log(f"成功: {success_count} 只")
    log(f"失败: {error_count} 只")

if __name__ == "__main__":
    main()