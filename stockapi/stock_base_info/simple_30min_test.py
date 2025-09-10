from xtquant import xtdata
import pandas as pd
import os
from datetime import datetime
import time
import logging

def setup_logging():
    """
    设置日志配置
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建logs文件夹
    logs_dir = os.path.join(script_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"simple_30min_test_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return log_filename

def download_30min_data_to_cache(stock_code, stock_name):
    """
    下载单个股票的30分钟数据到本地缓存（基于get_all_stocks_data.py的逻辑）
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
    
    Returns:
        bool: 是否成功下载
    """
    logging.info(f"开始下载股票 {stock_code} ({stock_name}) 的30分钟数据到本地缓存...")
    
    # 构造股票代码格式（需要添加交易所后缀）
    if stock_code.startswith('6'):
        full_code = f"{stock_code}.SH"  # 上海交易所
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        full_code = f"{stock_code}.SZ"  # 深圳交易所
    else:
        logging.warning(f"跳过不支持的股票代码: {stock_code}")
        return False
    
    try:
        # 下载30分钟数据（从1990年开始）
        logging.info(f"下载30分钟数据到本地（从1990年开始）...")
        download_result = xtdata.download_history_data(full_code, period='30m', start_time='19900101')
        logging.info(f"30分钟数据下载结果: {download_result}")
        logging.info(f"30分钟数据已下载到本地缓存")
        return True
        
    except Exception as e:
        logging.error(f"30分钟数据下载失败: {e}")
        # 尝试重试一次
        try:
            logging.info("准备重试下载...")
            time.sleep(2)
            download_result = xtdata.download_history_data(full_code, period='30m', start_time='19900101')
            logging.info(f"30分钟数据重试下载结果: {download_result}")
            logging.info(f"30分钟数据重试成功")
            return True
        except Exception as retry_e:
            logging.error(f"30分钟数据重试下载仍然失败: {retry_e}")
            return False

def save_30min_data_to_csv(stock_code, stock_name, base_folder="test_30min_output"):
    """
    将单个股票的30分钟数据保存为CSV文件（基于save_stocks_to_csv.py的逻辑）
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        base_folder: 数据保存的基础文件夹
    
    Returns:
        tuple: (成功数量, 总尝试数量)
    """
    logging.info(f"开始保存股票 {stock_code} ({stock_name}) 的30分钟数据到CSV...")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_folder = os.path.join(script_dir, base_folder)
    
    # 创建股票专用数据文件夹
    stock_folder = os.path.join(base_folder, f"stock_{stock_code}_data")
    if not os.path.exists(stock_folder):
        os.makedirs(stock_folder)
        logging.info(f"创建股票文件夹: {stock_folder}")
    
    # 构造股票代码格式
    if stock_code.startswith('6'):
        full_code = f"{stock_code}.SH"
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        full_code = f"{stock_code}.SZ"
    else:
        logging.warning(f"跳过不支持的股票代码: {stock_code}")
        return 0, 1
    
    try:
        # 获取30分钟数据（从本地缓存或直接获取）
        logging.info(f"获取30分钟数据（从1990年开始）...")
        minute_data = xtdata.get_market_data([], [full_code], period='30m', start_time='19900101')
        
        if minute_data and isinstance(minute_data, dict):
            # 处理xtquant返回的数据结构
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
                        
                        # 添加可读的日期时间列
                        if 'time' in minute_df.columns:
                            datetime_col = pd.to_datetime(minute_df['time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.strftime('%Y-%m-%d %H:%M:%S')
                            # 重新排列列顺序，将datetime放在time后面
                            cols = list(minute_df.columns)
                            time_idx = cols.index('time')
                            cols.insert(time_idx + 1, 'datetime')
                            minute_df['datetime'] = datetime_col
                            minute_df = minute_df[cols]
                        
                        # 保存为CSV文件
                        minute_filename = os.path.join(stock_folder, f"{stock_code}_30minute_history.csv")
                        minute_df.to_csv(minute_filename, encoding='utf-8-sig', index=False)
                        logging.info(f"30分钟数据已保存到CSV: {len(minute_df)} 条记录")
                        logging.info(f"文件路径: {minute_filename}")
                        
                        # 显示数据信息
                        if len(minute_df) > 0:
                            logging.info(f"数据列: {list(minute_df.columns)}")
                            logging.info(f"时间范围: {minute_df['datetime'].iloc[0]} 到 {minute_df['datetime'].iloc[-1]}")
                            logging.info(f"前3行数据:\n{minute_df.head(3).to_string()}")
                        
                        return 1, 1
                    else:
                        logging.error(f"股票代码 {full_code} 不在返回数据中")
                        return 0, 1
                else:
                    logging.error(f"时间数据为空")
                    return 0, 1
            except Exception as e:
                logging.error(f"30分钟数据处理失败: {e}")
                return 0, 1
        else:
            logging.error(f"30分钟数据获取失败: 无数据返回")
            return 0, 1
            
    except Exception as e:
        logging.error(f"数据获取失败: {e}")
        return 0, 1

def test_complete_workflow(stock_code, stock_name):
    """
    测试完整的工作流程：下载数据到缓存 -> 保存为CSV
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
    
    Returns:
        bool: 测试是否成功
    """
    logging.info(f"\n{'='*50}")
    logging.info(f"开始测试股票 {stock_code} ({stock_name}) 的完整工作流程")
    logging.info(f"{'='*50}")
    
    try:
        # 步骤1：下载数据到本地缓存
        logging.info("步骤1：下载30分钟数据到本地缓存")
        download_success = download_30min_data_to_cache(stock_code, stock_name)
        
        if download_success:
            logging.info("✓ 步骤1完成：数据下载成功")
        else:
            logging.warning("⚠ 步骤1警告：数据下载失败，但继续尝试步骤2")
        
        # 步骤2：保存为CSV
        logging.info("\n步骤2：将数据保存为CSV文件")
        success_count, total_attempts = save_30min_data_to_csv(stock_code, stock_name)
        
        if success_count > 0:
            logging.info(f"✓ 步骤2完成：CSV保存成功 ({success_count}/{total_attempts})")
            logging.info(f"✓ 股票 {stock_code} 的完整工作流程测试成功")
            return True
        else:
            logging.error(f"✗ 步骤2失败：CSV保存失败 ({success_count}/{total_attempts})")
            return False
            
    except Exception as e:
        logging.error(f"✗ 测试过程中发生异常: {e}")
        return False

def main():
    """
    主函数：简单的1分钟数据测试
    """
    # 设置日志
    log_filename = setup_logging()
    logging.info(f"测试日志文件: {log_filename}")
    logging.info("="*60)
    logging.info("简单30分钟数据获取和保存测试")
    logging.info("="*60)
    
    # 测试单个股票
    test_stock_code = "000001"
    test_stock_name = "平安银行"
    
    success = test_complete_workflow(test_stock_code, test_stock_name)
    
    # 测试总结
    logging.info(f"\n{'='*60}")
    logging.info("测试总结")
    logging.info(f"{'='*60}")
    
    if success:
        logging.info("🎉 测试成功完成！")
        logging.info("30分钟数据的下载和保存功能正常工作")
    else:
        logging.error("❌ 测试失败")
        logging.error("请检查xtquant连接和数据权限")
    
    logging.info("测试脚本执行完成")

if __name__ == "__main__":
    main()