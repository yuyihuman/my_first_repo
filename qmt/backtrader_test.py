import time
import pandas as pd
import backtrader as bt
import argparse
import numpy as np
import torch
import sys
import io
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import concurrent.futures
import logging
from xtquant import xtdata

# 禁用显示功能
plt.show = lambda: None

from model_train import normalize, normalize_0_to_1, read_single_stock_outstanding_share, \
                        convert_stock_code, add_outstanding_share_column, get_model_para, \
                        get_buy_value_by_index, evaluate_signal_at_n, RNNModel

parser = argparse.ArgumentParser(description="")
parser.add_argument('-m', '--model', type=str, default="final_model_0.95_120_720.pth", help="指定模型名称")
parser.add_argument('-sd', '--start_date', type=str, default="20140101", help="开始时间")
parser.add_argument('-ed', '--end_date', type=str, default="20180101", help="结束时间")
parser.add_argument('-mode', '--mode', type=str, default="predict", help="predict/truth")
parser.add_argument('-p', '--plot', type=str, default="False", help="True/False")
parser.add_argument('-clb', '--code_list_backtrader', type=str, default="", help="回测代码列表")
args = parser.parse_args()
code_list_backtrader = args.code_list_backtrader.split(",") if args.code_list_backtrader else []
print(code_list_backtrader)

# Check if CUDA (GPU) is available
device = "cpu"
print(f"Using device: {device}")

input_length, hold_cycles, accuracy = get_model_para(model_name=args.model)
input_size = 2
hidden_size = 64
model = RNNModel(input_size, hidden_size, input_length)

# 检查模型文件是否存在
if not os.path.exists(args.model) and args.mode == "predict":
    print(f"Error: Model file '{args.model}' does not exist.")
    sys.exit(0)  # 非零值表示异常退出
else:
    print(f"Info: Use Model file {args.model}")

if args.mode == "predict":
    model.load_state_dict(torch.load(args.model, weights_only=True))
    model.to(device)
    model.eval()  # 切换到评估模式

# 设定一个标的列表
code_list = code_list_backtrader
period = '1m'
start_time = args.start_date
end_time = args.end_date
kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time=start_time, end_time=end_time)

# 创建 logger 函数
def create_logger(code):
    log_filename = f'log/{code}_log.log'  # 固定文件名，不加时间戳
    logger = logging.getLogger(log_filename)  # 使用固定的 logger 名称
    
    # 如果 logger 已经存在 handler，就不要再添加 handler
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # 创建文件处理器，文件名固定
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加文件处理器到 logger
        logger.addHandler(file_handler)
        
    return logger

# Create a Strategy
class TestStrategy(bt.Strategy):
    params = (
        ('code', None),  # 添加 code 参数
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.order = None
        self.open_time = None
        self.code = self.params.code  # 在策略中访问传递的 code
        self.logger = create_logger(self.code)  # 每个策略都有独立的 logger

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.datetime(0)
        self.logger.info('%s, %s' % (dt.isoformat(), txt))  # 打印日志信息

    def notify(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)
        self.order = None

    def next(self):
        self.log('Open, %.2f\tClose, %.2f' % (self.dataopen[0], self.dataclose[0]))

        if self.order:
            return

        if not self.position:
            # 获取当前可用现金
            cash = self.broker.get_cash()
            # 获取当前价格
            current_price = self.dataclose[0]
            # 计算可以买入的股数（全仓）
            size = cash // current_price  # 使用整除以确保为整数股数
            if get_buy_value_by_index(kline_data[self.code], self.datas[0].datetime.datetime(0)):  # 使用 self.code
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.open_time = self.datas[0].datetime.datetime(0).date()
                self.order = self.buy(size=size)
        else:
            if len(self) >= (self.bar_executed + hold_cycles) and self.datas[0].datetime.datetime(0).date() != self.open_time:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell(size=self.position.size)

def process_stock_data(code, model, kline_data, accuracy, input_length, hold_cycles, device, args):
    logger = create_logger(code)  # 为每个股票创建独立的 logger
    logger.info(f"Processing stock code: {code}")  # 打印当前正在处理的股票代码
    try:
        # 读取该股票的流通股本数据
        logger.info(f"Reading outstanding share data for {code}...")
        data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))
        first_date = pd.to_datetime(data_os.loc[0, 'date'])
        check_date = pd.to_datetime('2015-01-01')
        
        logger.info(f"First date of outstanding share data for {code}: {first_date}")
        if first_date < check_date:
            logger.info(f"Data for {code} is valid for processing. Proceeding with data manipulation...")
            
            # 处理股票数据
            data_post = add_outstanding_share_column(kline_data[code], data_os)
            data_post['turnover'] = data_post['volume'] * 100 / data_post['outstanding_share']
            data_post['change_percentage'] = data_post['close'].diff() / data_post['close'].shift(1)
            data_post['change_percentage'] = data_post['change_percentage'].fillna(0)
            data_post['turnover_normalized'] = normalize_0_to_1(data_post['turnover'])
            data_post['change_percentage_normalized'] = normalize(data_post['change_percentage'], code=code)
            data_post['buy'] = 0
            data_post['buy_origin'] = 0
            
            logger.info(f"Use Model file {args.model}")
            logger.info(f"Stock data for {code} processed successfully.")
            
            # 对数据进行列类型转换
            float_columns = data_post.select_dtypes(include=['float']).columns
            data_post[float_columns] = data_post[float_columns].round(4)

            turnover_normalized = data_post['turnover_normalized']
            change_percentage = data_post['change_percentage']
            change_percentage_normalized = data_post['change_percentage_normalized']
            rnn_input = np.column_stack((turnover_normalized, change_percentage_normalized))
            seq_length = input_length

            logger.info(f"Starting model prediction for {code}...")
            
            # 模型推理过程
            if args.mode == "predict":
                for i in range(len(rnn_input) - seq_length):
                    current_sequence_tensor = torch.tensor(rnn_input[i:i+seq_length], dtype=torch.float32).unsqueeze(0).to(device)
                    with torch.no_grad():
                        output = model(current_sequence_tensor)
                        output = torch.sigmoid(output)
                    if seq_length + i < len(data_post):
                        data_post.iloc[seq_length + i, data_post.columns.get_loc('buy_origin')] = round(output.item(), 4)
                        prediction = 1 if output.item() >= 0.5 else 0
                        data_post.iloc[seq_length + i, data_post.columns.get_loc('buy')] = prediction

            elif args.mode == "truth":
                for n in range(len(change_percentage) - hold_cycles):
                    data_post.iloc[n, data_post.columns.get_loc('buy')] = evaluate_signal_at_n(column=change_percentage, n=n, judge_length=hold_cycles)

            # 保存数据并准备回测
            logger.info(f"Saving processed data for {code}...")
            kline_data[code].index = pd.to_datetime(kline_data[code].index, format='%Y%m%d%H%M%S')
            kline_data[code].rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            kline_data[code].to_csv(f'data/{code}_{accuracy}_{input_length}_{hold_cycles}_backtrade.csv', index=True)

            # 回测
            logger.info(f"Running backtest for {code}...")
            datafeed = bt.feeds.PandasData(dataname=kline_data[code])
            cerebro = bt.Cerebro()
            cerebro.addstrategy(TestStrategy, code=code)
            cerebro.adddata(datafeed)
            cerebro.broker.setcash(100000.0)

            logger.info(f'Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
            cerebro.run()
            logger.info(f'{code} Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
            
            # 绘制结果
            fig = cerebro.plot(show=False)[0][0]
            fig.set_size_inches(30, 5)
            fig.savefig(f'data/{code}_{accuracy}_{input_length}_{hold_cycles}_backtrade_{args.mode}.png', dpi=300)
            logger.info(f"Backtest and plot for {code} completed successfully.")
        else:
            logger.info(f"Data for {code} is outdated, skipping this stock.")
    
    except Exception as e:
        logger.error(f"Error processing {code}: {e}")

if __name__ == '__main__':
    # 使用 ProcessPoolExecutor 并行执行
    with concurrent.futures.ProcessPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(process_stock_data, code, model, kline_data, accuracy, input_length, hold_cycles, device, args): code for code in code_list}
        for future in concurrent.futures.as_completed(futures):
            code = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f'Code {code} generated an exception: {exc}')
