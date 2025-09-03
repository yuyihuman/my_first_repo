from xtquant import xtdata
import pandas as pd
import os
from datetime import datetime
import time
import logging

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
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建logs文件夹（在脚本所在目录下）
    logs_dir = os.path.join(script_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 清理旧日志文件
    clean_old_logs(logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"financial_data_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

def callback_func(data):
    """财务数据下载回调函数"""
    logging.info(f"财务数据下载回调: {data}")

def download_financial_data_batch(stock_codes, batch_name, base_output_dir):
    """
    批量下载财务数据
    
    Args:
        stock_codes: 股票代码列表
        batch_name: 批次名称
        base_output_dir: 输出目录
    
    Returns:
        成功下载的股票数量
    """
    logging.info(f"开始下载 {batch_name} 的财务数据，共 {len(stock_codes)} 只股票")
    logging.info(f"股票代码: {stock_codes}")
    
    success_count = 0
    
    try:
        # 下载财务数据
        logging.info("正在下载财务数据...")
        xtdata.download_financial_data2(stock_codes, table_list=[], start_time='19900101', end_time='', callback=callback_func)
        
        # 获取财务数据
        logging.info("正在获取财务数据...")
        data = xtdata.get_financial_data(stock_codes, table_list=[], start_time='', end_time='', report_type='report_time')
        
        if data is not None and isinstance(data, dict):
            logging.info(f"成功获取到 {len(data)} 个股票的财务数据")
            
            # 为每个股票代码分别保存数据
            for stock_code, stock_data in data.items():
                try:
                    # 为每个股票创建单独的文件夹
                    stock_dir = os.path.join(base_output_dir, stock_code)
                    if not os.path.exists(stock_dir):
                        os.makedirs(stock_dir)
                        
                    if isinstance(stock_data, dict):
                        # 如果股票数据也是字典（包含多个报表类型）
                        table_count = 0
                        for table_name, table_data in stock_data.items():
                            if hasattr(table_data, 'to_csv') and not table_data.empty:
                                csv_filename = os.path.join(stock_dir, f"{table_name}.csv")
                                table_data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
                                logging.info(f"已保存 {stock_code} 的 {table_name} 数据，形状: {table_data.shape}")
                                table_count += 1
                        
                        if table_count > 0:
                            success_count += 1
                            logging.info(f"股票 {stock_code} 成功保存 {table_count} 个财务报表")
                        else:
                            logging.warning(f"股票 {stock_code} 没有有效的财务数据")
                            
                    elif hasattr(stock_data, 'to_csv') and not stock_data.empty:
                        # 如果股票数据直接是DataFrame
                        csv_filename = os.path.join(stock_dir, "financial_data.csv")
                        stock_data.to_csv(csv_filename, index=True, encoding='utf-8-sig')
                        logging.info(f"已保存 {stock_code} 的财务数据，形状: {stock_data.shape}")
                        success_count += 1
                    else:
                        logging.warning(f"股票 {stock_code} 的数据格式不支持或为空")
                        
                except Exception as e:
                    logging.error(f"保存股票 {stock_code} 财务数据时发生错误: {e}")
                    
        else:
            logging.warning(f"{batch_name} 没有获取到有效的财务数据")
            
    except Exception as e:
        logging.error(f"下载 {batch_name} 财务数据时发生错误: {e}")
    
    logging.info(f"{batch_name} 完成，成功处理 {success_count}/{len(stock_codes)} 只股票")
    return success_count

def main():
    """
    主函数：批量下载所有0、3、6开头股票的财务数据
    """
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"日志文件: {log_filename}")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取股票列表CSV文件（在脚本所在目录下）
    csv_file = os.path.join(script_dir, "stock_data.csv")
    
    if not os.path.exists(csv_file):
        logging.error(f"错误：找不到文件 {csv_file}")
        return
    
    logging.info(f"读取股票列表文件: {csv_file}")
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        logging.info(f"共找到 {len(df)} 只股票")
        
        # 过滤出0、3、6开头的股票
        df['代码_str'] = df['代码'].astype(str).str.zfill(6)
        filtered_df = df[df['代码_str'].str.startswith(('0', '3', '6'))]
        logging.info(f"过滤出0、3、6开头的股票共 {len(filtered_df)} 只")
        
        if len(filtered_df) == 0:
            logging.warning("没有找到符合条件的股票")
            return
        
        # 创建财务数据输出文件夹（在脚本所在目录下）
        base_output_dir = os.path.join(script_dir, "financial_data")
        if not os.path.exists(base_output_dir):
            os.makedirs(base_output_dir)
            logging.info(f"创建输出文件夹: {base_output_dir}")
        
        # 统计信息
        total_stocks = len(filtered_df)
        processed_stocks = 0
        successful_stocks = 0
        batch_size = 10
        
        logging.info(f"开始批量下载财务数据，每批 {batch_size} 只股票")
        
        # 分批处理股票
        for i in range(0, total_stocks, batch_size):
            batch_df = filtered_df.iloc[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            # 构造股票代码列表（添加交易所后缀）
            stock_codes = []
            for _, row in batch_df.iterrows():
                stock_code = str(row['代码']).zfill(6)
                if stock_code.startswith('6'):
                    full_code = f"{stock_code}.SH"  # 上海交易所
                elif stock_code.startswith('0') or stock_code.startswith('3'):
                    full_code = f"{stock_code}.SZ"  # 深圳交易所
                else:
                    continue  # 跳过不支持的代码
                stock_codes.append(full_code)
            
            if not stock_codes:
                logging.warning(f"第 {batch_num} 批没有有效的股票代码")
                continue
            
            batch_name = f"第 {batch_num} 批"
            logging.info(f"{'='*60}")
            logging.info(f"处理进度: {batch_num}/{(total_stocks + batch_size - 1) // batch_size}")
            logging.info(f"当前批次: {batch_name}，股票数量: {len(stock_codes)}")
            
            try:
                success_count = download_financial_data_batch(stock_codes, batch_name, base_output_dir)
                successful_stocks += success_count
                processed_stocks += len(stock_codes)
                
                # 添加延时，避免请求过于频繁
                if i + batch_size < total_stocks:  # 不是最后一批
                    logging.info("等待5秒后处理下一批...")
                    time.sleep(5)
                    
            except Exception as e:
                logging.error(f"处理 {batch_name} 时发生错误: {e}")
                processed_stocks += len(stock_codes)
        
        # 生成总体报告
        logging.info(f"{'='*60}")
        logging.info("批量财务数据下载完成！")
        logging.info(f"总共处理股票: {processed_stocks}")
        logging.info(f"成功下载财务数据的股票: {successful_stocks}")
        logging.info(f"总体成功率: {successful_stocks/processed_stocks*100:.1f}%")
        
        # 保存总体报告
        report_content = f"""批量股票财务数据下载报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计信息:
- 总共处理股票: {processed_stocks}
- 成功下载财务数据的股票: {successful_stocks}
- 总体成功率: {successful_stocks/processed_stocks*100:.1f}%
- 批次大小: {batch_size} 只股票/批

数据存储位置: {base_output_dir}/
每个股票的财务数据存储在独立的子文件夹中

数据来源:
- xtquant库 (迅投量化)

数据类型:
- 财务报表数据（资产负债表、利润表、现金流量表等）

注意事项:
- 所有文件使用UTF-8-BOM编码
- 部分股票可能因为数据源限制无法获取完整数据
- 建议定期更新数据
"""
        
        report_filename = os.path.join(base_output_dir, "financial_data_download_report.txt")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logging.info(f"\n批量下载完成!")
        logging.info(f"总共处理 {processed_stocks} 只股票，成功 {successful_stocks} 只")
        logging.info(f"详细报告已保存到: {report_filename}")
        
    except Exception as e:
        logging.error(f"读取CSV文件时发生错误: {e}")
        return

if __name__ == "__main__":
    main()