from xtquant import xtdata
import pandas as pd
import os
from datetime import datetime
import time
import logging

def save_stock_data_to_csv(stock_code, stock_name, base_folder="all_stocks_data"):
    """
    将单个股票的数据保存为CSV文件
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        base_folder: 数据保存的基础文件夹
    """
    logging.info(f"开始保存股票 {stock_code} ({stock_name}) 的数据到CSV...")
    
    # 创建股票专用数据文件夹
    stock_folder = os.path.join(base_folder, f"stock_{stock_code}_data")
    if not os.path.exists(stock_folder):
        os.makedirs(stock_folder)
    
    success_count = 0
    total_attempts = 2  # 1分钟数据 + 日线数据
    
    # 构造股票代码格式（需要添加交易所后缀）
    if stock_code.startswith('6'):
        full_code = f"{stock_code}.SH"  # 上海交易所（包括主板和科创板）
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        full_code = f"{stock_code}.SZ"  # 深圳交易所
    else:
        logging.warning(f"  跳过不支持的股票代码: {stock_code}")
        return 0, 0
    
    try:
        # 获取从1990年开始的全部日线数据
        logging.info(f"  获取日线数据（从1990年开始）...")
        daily_data = xtdata.get_market_data([], [full_code], period='1d', start_time='19900101')
        
        if daily_data and isinstance(daily_data, dict):
            # xtquant返回的数据结构：每个字段都是DataFrame，行为股票代码，列为日期
            # 需要重新组织数据结构
            try:
                # 获取时间序列（日期）
                time_df = daily_data.get('time')
                if time_df is not None and not time_df.empty:
                    # 获取股票在DataFrame中的数据
                    if full_code in time_df.index:
                        dates = time_df.loc[full_code].values
                        
                        # 构建新的DataFrame，行为日期，列为各个指标
                        df_data = {'date': dates}
                        
                        # 提取各个字段的数据
                        for field_name, field_df in daily_data.items():
                            if field_name != 'time' and field_df is not None and not field_df.empty:
                                if full_code in field_df.index:
                                    df_data[field_name] = field_df.loc[full_code].values
                        
                        # 创建最终的DataFrame
                        daily_df = pd.DataFrame(df_data)
                        
                        # 按时间排序（确保数据按时间顺序排列）
                        daily_df = daily_df.sort_values('date').reset_index(drop=True)
                        
                        # 计算移动平均值（如果有收盘价数据）
                        if 'close' in daily_df.columns:
                            data_count = len(daily_df)
                            # 只有在数据量足够时才计算相应的移动平均值
                            if data_count >= 5:
                                daily_df['close_5d_avg'] = daily_df['close'].rolling(window=5, min_periods=5).mean()
                            if data_count >= 10:
                                daily_df['close_10d_avg'] = daily_df['close'].rolling(window=10, min_periods=10).mean()
                            if data_count >= 20:
                                daily_df['close_20d_avg'] = daily_df['close'].rolling(window=20, min_periods=20).mean()
                            if data_count >= 30:
                                daily_df['close_30d_avg'] = daily_df['close'].rolling(window=30, min_periods=30).mean()
                            if data_count >= 60:
                                daily_df['close_60d_avg'] = daily_df['close'].rolling(window=60, min_periods=60).mean()
                        
                        daily_filename = os.path.join(stock_folder, f"{stock_code}_daily_history.csv")
                        daily_df.to_csv(daily_filename, encoding='utf-8-sig', index=False)
                        logging.info(f"    日线数据已保存到CSV: {len(daily_df)} 条")
                        success_count += 1
                    else:
                        logging.error(f"    股票代码 {full_code} 不在返回数据中")
                else:
                    logging.error(f"    时间数据为空")
            except Exception as e:
                logging.error(f"    日线数据处理失败: {e}")
        else:
            logging.error(f"    日线数据获取失败: 无数据返回")
        
        # 尝试获取1分钟数据（从1990年开始，如果支持的话）
        logging.info(f"  获取1分钟数据（从1990年开始）...")
        try:
            minute_data = xtdata.get_market_data([], [full_code], period='1m', start_time='19900101')
            
            if minute_data and isinstance(minute_data, dict):
                # xtquant返回的数据结构：每个字段都是DataFrame，行为股票代码，列为时间
                # 需要重新组织数据结构
                try:
                    # 获取时间序列
                    time_df = minute_data.get('time')
                    if time_df is not None and not time_df.empty:
                        # 获取股票在DataFrame中的数据
                        if full_code in time_df.index:
                            times = time_df.loc[full_code].values
                            
                            # 构建新的DataFrame，行为时间，列为各个指标
                            df_data = {'time': times}
                            
                            # 提取各个字段的数据
                            for field_name, field_df in minute_data.items():
                                if field_name != 'time' and field_df is not None and not field_df.empty:
                                    if full_code in field_df.index:
                                        df_data[field_name] = field_df.loc[full_code].values
                            
                            # 创建最终的DataFrame
                            minute_df = pd.DataFrame(df_data)
                            minute_filename = os.path.join(stock_folder, f"{stock_code}_1minute_history.csv")
                            minute_df.to_csv(minute_filename, encoding='utf-8-sig', index=False)
                            logging.info(f"    1分钟数据已保存到CSV: {len(minute_df)} 条")
                            success_count += 1
                        else:
                            logging.info(f"    股票代码 {full_code} 不在返回数据中，跳过")
                    else:
                        logging.info(f"    时间数据为空，跳过")
                except Exception as e:
                    logging.info(f"    1分钟数据处理失败，跳过: {e}")
            else:
                logging.info(f"    1分钟数据不可用，跳过")
        except Exception as e:
            logging.info(f"    1分钟数据获取失败，跳过: {e}")
        
    except Exception as e:
        logging.error(f"    数据获取失败: {e}")
    
    # 生成单个股票的数据报告
    data_files_info = f"""获取的数据文件:
1. {stock_code}_1minute_history.csv - 1分钟历史数据 (xtquant)
2. {stock_code}_daily_history.csv - 日线历史数据 (xtquant)"""
    encoding_info = "- 文件编码：UTF-8-BOM，支持中文显示"
    
    summary_content = f"""股票代码: {stock_code}
股票名称: {stock_name}
完整代码: {full_code}
数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
成功获取数据类型: {success_count}/{total_attempts}

{data_files_info}

数据来源说明:
- 历史价格数据：xtquant (迅投量化)
{encoding_info}
- 数据周期：1分钟K线 + 日线K线
"""
    
    report_filename = os.path.join(stock_folder, "data_summary.txt")
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    logging.info(f"  股票 {stock_code} 数据保存完成，成功率: {success_count}/{total_attempts}")
    return success_count, total_attempts

def clean_old_logs(logs_dir="logs", keep_days=7):
    """清理旧的日志文件
    
    Args:
        logs_dir: 日志文件夹路径
        keep_days: 保留最近几天的日志，默认7天
    """
    if not os.path.exists(logs_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 60 * 60)  # 转换为秒
    
    deleted_count = 0
    for filename in os.listdir(logs_dir):
        if filename.endswith('.log'):
            file_path = os.path.join(logs_dir, filename)
            file_time = os.path.getmtime(file_path)
            
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"删除日志文件 {filename} 失败: {e}")
    
    if deleted_count > 0:
        print(f"已清理 {deleted_count} 个旧日志文件")

def setup_logging():
    """
    设置日志配置
    """
    # 创建logs文件夹
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 清理旧日志文件
    clean_old_logs(logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"save_stocks_csv_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

def main():
    """
    主函数：批量将所有股票数据保存为CSV文件
    """
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"日志文件: {log_filename}")
    
    # 读取股票列表CSV文件
    csv_file = "stock_data.csv"
    
    if not os.path.exists(csv_file):
        logging.error(f"错误：找不到文件 {csv_file}")
        return
    
    logging.info(f"读取股票列表文件: {csv_file}")
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        logging.info(f"共找到 {len(df)} 只股票")
        
        # 过滤掉8开头的股票（北交所）
        df = df[~df['代码'].astype(str).str.startswith('8')]
        logging.info(f"过滤8开头股票后剩余 {len(df)} 只股票")
        
        # 创建总的数据文件夹
        base_folder = "all_stocks_data"
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            logging.info(f"创建总文件夹: {base_folder}")
        
        # 统计信息
        total_stocks = len(df)
        processed_stocks = 0
        successful_stocks = 0
        total_success_count = 0
        total_attempts = 0
        
        # 批量处理前5只股票
        for index, row in df.head(5).iterrows():
            stock_code = str(row['代码']).zfill(6)  # 确保股票代码是6位数字
            stock_name = row['名称']
            
            processed_stocks += 1
            logging.info(f"{'='*60}")
            logging.info(f"处理进度: {processed_stocks}/{total_stocks} ({processed_stocks/total_stocks*100:.1f}%)")
            logging.info(f"当前股票: {stock_code} - {stock_name}")
            
            try:
                success_count, attempt_count = save_stock_data_to_csv(stock_code, stock_name, base_folder)
                total_success_count += success_count
                total_attempts += attempt_count
                
                if success_count > 0:
                    successful_stocks += 1
                
                # 添加延时，避免请求过于频繁
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"处理股票 {stock_code} 时发生错误: {e}")
                continue
        
        # 计算失败数量
        failed_stocks = total_stocks - successful_stocks
        
        # 生成总体报告
        logging.info(f"{'='*60}")
        logging.info("批量数据保存完成！")
        logging.info(f"总共处理股票: {total_stocks}")
        logging.info(f"成功保存数据的股票: {successful_stocks}")
        logging.info(f"总体成功率: {successful_stocks/total_stocks*100:.1f}%")
        logging.info(f"数据保存成功率: {total_success_count/total_attempts*100:.1f}%")
        
        # 保存总体报告
        storage_info = f"数据存储位置: {base_folder}/\n每个股票的数据存储在独立的子文件夹中"
        file_info = "- 所有文件使用UTF-8-BOM编码"
        process_info = "- 需要先下载数据到本地，然后读取保存为CSV文件"
        
        overall_report = f"""批量股票1分钟和日线数据保存报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计信息:
- 总共处理股票: {total_stocks}
- 成功保存数据的股票: {successful_stocks}
- 失败数量: {failed_stocks}
- 股票处理成功率: {successful_stocks/total_stocks*100:.1f}%
- 数据保存成功率: {total_success_count/total_attempts*100:.1f}%

{storage_info}

数据来源:
- xtquant库 (迅投量化)

数据类型:
- 1分钟K线数据
- 日线K线数据

注意事项:
{file_info}
- 部分股票可能因为数据源限制无法获取完整数据
- 建议定期更新数据
{process_info}
"""
        
        report_filename = os.path.join(base_folder, "batch_csv_save_report.txt")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(overall_report)
        
        logging.info(f"\n批量保存完成!")
        logging.info(f"总共处理 {total_stocks} 只股票，成功 {successful_stocks} 只，失败 {failed_stocks} 只")
        logging.info(f"详细报告已保存到: {report_filename}")
        
    except Exception as e:
        logging.error(f"读取CSV文件时发生错误: {e}")
        return

if __name__ == "__main__":
    main()