# coding:utf-8
from xtquant import xtdata
import pandas as pd
import os
import argparse
from utils import logger, setup_logger, get_current_log_file

# 命令行参数解析
parser = argparse.ArgumentParser(description="获取个股分钟行情数据并保存到CSV")
parser.add_argument('--code', type=str, default='600000.SH', help='股票代码, 例如 600000.SH')
parser.add_argument('--start_time', type=str, default='20230701', help='起始日期, 例如 20230701')
parser.add_argument('--log_file', type=str, help='日志文件名，用于保持日志一致性')
args = parser.parse_args()
code = args.code
start_time = args.start_time

# 如果提供了日志文件名，则使用它
if args.log_file:
    custom_logger = setup_logger(name=None, log_file=args.log_file, reset=False, print_config=False)
    # 将全局logger指向新创建的logger
    import utils
    utils.logger = custom_logger

# 创建保存CSV文件的文件夹
csv_folder = 'stock_data'
if not os.path.exists(csv_folder):
    os.makedirs(csv_folder)

csv_file_path = os.path.join(csv_folder, f'{code}.csv')

# 下载历史数据 下载接口本身不返回数据
xtdata.download_history_data(code, period='1m', start_time=start_time)
logger.info(f'已请求下载历史数据: {code}, 起始时间: {start_time}, 周期: 1m')

# 获取历史数据并保存到CSV
fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'settlementPrice', 'openInterest', 'dr', 'totaldr', 'preClose', 'suspendFlag']
data = xtdata.get_market_data(fields, [code], period='1m', start_time=start_time)
logger.info(f'获取历史数据完成: {code}, 起始时间: {start_time}, 字段数: {len(fields)}')

if data and 'close' in data:
    dfs = []
    for field in fields:
        if field in data and isinstance(data[field], pd.DataFrame):
            s = data[field].loc[code].T
            df_field = pd.DataFrame({field: s})
            df_field.index.name = 'time'
            dfs.append(df_field)
    if dfs:
        df_all = pd.concat(dfs, axis=1)
        df_all.reset_index(inplace=True)
        df_all.to_csv(csv_file_path, index=False, float_format='%.2f')
        logger.info(f'历史数据已保存到 {csv_file_path}, 数据点数: {len(df_all)}')

# 订阅最新行情并保存到CSV
def callback_func(data):
    if data and code in data:
        callback_data = data[code]
        df = pd.DataFrame(callback_data)
        file_exists = os.path.isfile(csv_file_path)
        df.to_csv(csv_file_path, mode='a', header=not file_exists, index=False, float_format='%.2f')
        logger.info(f'实时数据已追加到 {csv_file_path}, 新增数据点数: {len(df)}')

xtdata.subscribe_quote(code, period='1m', count=-1, callback=callback_func)
logger.info(f'已订阅实时行情: {code}, 周期: 1m')