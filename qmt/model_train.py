import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import time
import akshare as ak
import os
import random
import io
import sys
import argparse
import concurrent.futures
import logging
import backtrader as bt
import matplotlib.pyplot as plt
# 禁用显示功能
plt.show = lambda: None
import multiprocessing
import shutil
import traceback

from xtquant import xtdata
from torch.utils.data import Dataset, DataLoader, random_split
from datetime import datetime
from data_prepare import get_stock_list
from torch.utils.data import ConcatDataset
from torch.utils.data import Subset

def read_stock_floating_share():
    stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
    stock_zh_a_spot_em_df.to_csv(f'data/stock_outstanding_share.csv')

def read_single_stock_outstanding_share(code="sz000001"):
    now = datetime.now()
    date_string = now.strftime("%Y%m%d")
    stock_zh_a_daily_qfq_df = ak.stock_zh_a_daily(symbol=code, start_date="19910403", end_date=date_string, adjust="qfq")
    logging.info(f'\n{stock_zh_a_daily_qfq_df}')
    stock_zh_a_daily_qfq_df.to_csv(f'data/{code}_outstanding_share.csv')
    return stock_zh_a_daily_qfq_df

def convert_stock_code(stock_code):
    # 去掉字符串中的点，提取后缀，并调整格式
    code = stock_code.split('.')[0]  # 提取代码部分
    suffix = stock_code.split('.')[1].lower()  # 提取后缀并转换为小写
    return f"{suffix}{code}"

def add_outstanding_share_column(df1, df2):
    # 确保 df2 的 date 列转换为 datetime 格式
    df2['date'] = pd.to_datetime(df2['date'], format='%Y-%m-%d')
    
    # 从 df1 的索引提取日期并转换为 datetime 格式
    df1['date'] = pd.to_datetime(df1.index.astype(str).str[:8], format='%Y%m%d')

    # 将 df2 的 date 列设为索引，方便后续匹配
    df2.set_index('date', inplace=True)

    # 将 outstanding_share 列添加到 df1
    # 使用 map 方法根据 df1 的日期匹配 df2 的 outstanding_share
    df1['outstanding_share'] = df1['date'].map(df2['outstanding_share']).fillna(np.inf)

    # 删除临时日期列
    df1.drop(columns=['date'], inplace=True)

    return df1

def normalize(column, code):
    if code.startswith("0") or code.startswith("6"):
        min_val = -10
        max_val = 10
    elif code.startswith("3"):
        min_val = -20
        max_val = 20
    else:
        min_val = column.min()
        max_val = column.max()
    return (2 * (column - min_val) / (max_val - min_val)) - 1

def normalize_0_to_1(column):
    # min_val = column.min()
    # max_val = column.max()
    min_val = 0
    max_val = 0.8
    return (column - min_val) / (max_val - min_val)

def get_model_para(model_name):
    logging.info(model_name)
    input_length = int(model_name.replace(".pth","").split("_")[-2])
    hold_days = int(model_name.replace(".pth","").split("_")[-1])
    accuracy = float(model_name.replace(".pth","").split("_")[-3])
    return input_length, hold_days, accuracy

def evaluate_signal_at_n(column, n, judge_length, threshold=0.08):
    """
    在指定索引 `n` 处，根据判断长度和阈值评估信号。

    参数:
    - column: 包含百分比变化的数据列 (Pandas Series 或 NumPy 数组)。
    - n: 当前的索引 (int)。
    - judge_length: 判断的周期长度 (int)。
    - threshold_1: product_1 的阈值, 默认为 0.06。
    - threshold_4: product_4 的阈值, 默认为 0.02。

    返回:
    - 1: 如果满足条件。
    - 0: 如果不满足条件。
    """
    # 检查 n + judge_length 是否越界
    if n + judge_length > len(column):
        raise ValueError("`n + judge_length` 超出数据长度，请检查输入。")

    # 计算各个产品值
    product_1 = np.prod(1 + column[n:n + judge_length])
    product_2 = np.prod(1 + column[n:n + judge_length // 2])
    product_3 = np.prod(1 + column[n:n + judge_length // 4])
    product_4 = np.prod(1 + column[n:n + judge_length // 8])

    # 判断条件
    if product_4 > 1 + (judge_length / 48 * (threshold/8)) and product_1 > 1 + (judge_length / 48 * threshold):
        return 1
    return 0

# Dataset类
class RnnDataset(Dataset):
    def __init__(self, learn_trunks, target):
        self.learn_trunks = learn_trunks
        self.target = target

    def __len__(self):
        return len(self.learn_trunks)
    
    def __getitem__(self, idx):
        return self.learn_trunks[idx].float(), self.target[idx].float()

# RNN模型类
class RNNModel(nn.Module):
    def __init__(self, input_size, hidden_size, sequence_length):
        super().__init__()
        self.rnn = nn.RNN(input_size, hidden_size, num_layers=5, batch_first=True)
        self.fc1 = nn.Linear(hidden_size, 1)
        self.fc2 = nn.Linear(sequence_length, 1)  # 新增层，将所有时间步的输出合并为一个值

    def forward(self, x):
        out, _ = self.rnn(x)  # out 形状: (batch_size, sequence_length, hidden_size)
        out = self.fc1(out)    # out 形状: (batch_size, sequence_length, 1)
        out = out.squeeze(-1)  # 去掉最后一个维度，形状: (batch_size, sequence_length)
        out = self.fc2(out)    # 将时间步维度合并成一个值，形状: (batch_size, 1)
        return out.squeeze(-1)  # 输出形状: (batch_size,)

def process_stock_data(code, seq_length, judge_length, start_time, end_time):
    try:
        create_logger(f'{code}_train')
        logging.info(f"Processing stock data for code: {code}, sequence length: {seq_length}, judge length: {judge_length}, time range: {start_time} to {end_time}")

        # 获取数据的过程
        logging.info("Fetching market data...")
        kline_data = xtdata.get_market_data_ex([], [code], period="5m", start_time=start_time, end_time=end_time, dividend_type="front")
        data = kline_data.get(code, pd.DataFrame())
        
        if data.empty:
            logging.warning(f"No market data found for code: {code}. Skipping processing.")
            return None

        logging.info(f"Fetched {len(data)} rows of market data for code: {code}")

        logging.info("Fetching outstanding share data...")
        data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))

        if data_os.empty:
            logging.warning(f"No outstanding share data found for code: {code}. Skipping processing.")
            return None

        logging.info(f"Outstanding share data contains {len(data_os)} rows.")

        first_date = pd.to_datetime(data_os.loc[0, 'date'])
        check_date = pd.to_datetime('2010-01-01')
        logging.info(f"First outstanding share date: {first_date}, check date: {check_date}")

        if first_date < check_date:
            logging.info("Processing data with outstanding share adjustments...")
            try:
                data_post = add_outstanding_share_column(data, data_os)
                data_post['close'] = data_post['preClose']
                data_post['open'] = data_post['preClose']
                data_post['turnover'] = data_post['volume'] * 100 / data_post['outstanding_share']
                data_post['change_percentage'] = data_post['close'].diff() / data_post['close'].shift(1)
                data_post['change_percentage'] = data_post['change_percentage'].fillna(0)
                data_post['turnover_normalized'] = normalize_0_to_1(data_post['turnover'])
                data_post['change_percentage_normalized'] = normalize(data_post['change_percentage'], code=code)
                data_post['buy'] = 0
            except Exception as e:
                logging.error(f"Error processing data for code {code}: {e}")
                return None

            float_columns = data_post.select_dtypes(include=['float']).columns
            data_post[float_columns] = data_post[float_columns].round(4)
            logging.info(f"Data processed: columns normalized and rounded for {code}")

            turnover_normalized = data_post['turnover_normalized']
            change_percentage = data_post['change_percentage']

            if len(change_percentage) <= judge_length:
                logging.warning(f"Insufficient data for processing: len(change_percentage)={len(change_percentage)}, judge_length={judge_length}")
                return None

            change_percentage_normalized = data_post['change_percentage_normalized']
            rnn_input = np.column_stack((turnover_normalized, change_percentage_normalized))
            rnn_target = np.zeros(len(change_percentage) - judge_length, dtype=int)
            positive_counter = 0

            logging.info("Evaluating buy signals...")
            for n in range(len(change_percentage) - judge_length):
                try:
                    if evaluate_signal_at_n(column=change_percentage, n=n, judge_length=judge_length):
                        rnn_target[n] = 1
                        data_post.iloc[n, data_post.columns.get_loc('buy')] = 1
                        positive_counter += 1
                except Exception as e:
                    logging.error(f"Error evaluating signal at index {n} for code {code}: {e}")

            logging.info(f"Positive samples count: {positive_counter}")
            if positive_counter == 0:
                logging.info(f"Skipping {code} due to no positive samples.")
                return None

            file_path = f'data/{code}_{judge_length}_truth.csv'
            if not os.path.exists(file_path):
                try:
                    logging.info(f"Saving processed data to {file_path}...")
                    kline_data[code].index = pd.to_datetime(kline_data[code].index, format='%Y%m%d%H%M%S')
                    kline_data[code].rename(columns={
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume'
                    }, inplace=True)
                    kline_data[code].to_csv(file_path, index=True)

                    logging.info(f"Running backtest for {code}...")
                    datafeed = bt.feeds.PandasData(dataname=kline_data[code])
                    cerebro = bt.Cerebro()
                    cerebro.addstrategy(TestStrategy, code=code, kline_data=kline_data, hold_cycles=judge_length)
                    cerebro.adddata(datafeed)
                    cerebro.broker.setcash(100000.0)
                    logging.info(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
                    cerebro.run()
                    logging.info(f"{code} Truth Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

                    logging.info("Saving backtest plot...")
                    fig = cerebro.plot(show=False)[0][0]
                    fig.set_size_inches(30, 5)
                    fig.savefig(f'data/{code}_{judge_length}_truth.png', dpi=300)
                    logging.info(f"Backtest and plot for {code} completed successfully.")
                except Exception as e:
                    logging.error(f"Error during backtest or saving for code {code}: {e}")

            rnn_input = rnn_input[:-judge_length]

            logging.info("Constructing learning trunks...")
            learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input) - seq_length)]
            learn_trunks_np = np.array(learn_trunks)
            target_np = rnn_target[seq_length:]  # Align target with input sequences

            logging.info(f"learn_trunks_np shape: {learn_trunks_np.shape}")
            logging.info(f"target_np shape: {target_np.shape}")

            positive_indices = np.where(target_np == 1)[0]
            negative_indices = np.where(target_np == 0)[0]

            if len(positive_indices) == 0:
                logging.info(f"Skipping {code} due to no positive samples.")
                return None

            x = len(positive_indices)
            sampled_negative_indices = random.sample(list(negative_indices), min(1 * x, len(negative_indices)))
            selected_indices = np.concatenate([positive_indices, sampled_negative_indices])

            filtered_learn_trunks = learn_trunks_np[selected_indices]
            filtered_targets = target_np[selected_indices]

            logging.info(f"filtered_learn_trunks shape: {filtered_learn_trunks.shape}")
            logging.info(f"filtered_targets shape: {filtered_targets.shape}")

            logging.info("Creating RNN dataset...")
            rnn_dataset = RnnDataset(torch.tensor(filtered_learn_trunks, dtype=torch.float32), 
                                     torch.tensor(filtered_targets, dtype=torch.long))
            logging.info(f"Dataset for {code} created successfully with {len(filtered_targets)} samples.")
            return rnn_dataset

    except Exception as e:
        logging.error(f"Unexpected error processing stock data for code {code}: {e}")
        return None

def train_data(seq_length, judge_length, start_time, end_time):
    all_datasets = []
    chunk_size = 20
    # Helper function to process a chunk of tasks
    def process_chunk(tasks_chunk):
        # Create a pool of workers for each chunk
        with multiprocessing.Pool(chunk_size) as pool:
            results = pool.starmap(process_stock_data, tasks_chunk)
            for rnn_dataset in results:
                if rnn_dataset is not None:
                    all_datasets.append(rnn_dataset)

    # Prepare the arguments for the process
    tasks = [(code, seq_length, judge_length, start_time, end_time) for code in code_list]
    # Split tasks into chunks of 5
    tasks_chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
    # Process each chunk using the pool
    for tasks_chunk in tasks_chunks:
        process_chunk(tasks_chunk)

    # Combine all datasets into one
    combined_dataset = ConcatDataset(all_datasets)

    # 数据集划分
    total_len = len(combined_dataset)
    logging.info(f'total_len is {total_len}')
    if total_len * 0.5 > 5000:
        train_size = 5000
    else:
        train_size = int(total_len * 0.5)
    if total_len - train_size > 5000:
        val_size = 5000
    else:
        val_size = total_len - train_size
    
    # 随机选择 train_size 个索引
    train_indices = random.sample(range(total_len), train_size)

    # 剩余的索引用于验证集
    remaining_indices = list(set(range(total_len)) - set(train_indices))
    val_indices = random.sample(remaining_indices, val_size)

    # 构建训练集和验证集
    train_data = Subset(combined_dataset, train_indices)
    val_data = Subset(combined_dataset, val_indices)

    # 定义DataLoader
    batch_size = 64
    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False, drop_last=True)
    logging.info(f"Total samples in train_data: {len(train_data)}")
    logging.info(f"Total samples in val_data: {len(val_data)}")

    # 计算整个训练集中的0和1的比例
    total_zeros = 0
    total_ones = 0
    total_samples = 0

    for learn_trunks_batch, target_batch in train_loader:
        num_zeros = (target_batch == 0).sum().item()
        num_ones = (target_batch == 1).sum().item()
        total_zeros += num_zeros
        total_ones += num_ones
        total_samples += target_batch.size(0)

    # 计算比例
    zero_ratio = total_zeros / total_samples
    one_ratio = total_ones / total_samples

    logging.info(f"Train data label distribution: 0's: {total_zeros} ({zero_ratio * 100:.2f}%), 1's: {total_ones} ({one_ratio * 100:.2f}%)")

    for learn_trunks_batch, target_batch in val_loader:
        num_zeros = (target_batch == 0).sum().item()
        num_ones = (target_batch == 1).sum().item()
        total_zeros += num_zeros
        total_ones += num_ones
        total_samples += target_batch.size(0)

    # 计算比例
    zero_ratio = total_zeros / total_samples
    one_ratio = total_ones / total_samples

    logging.info(f"Total data label distribution: 0's: {total_zeros} ({zero_ratio * 100:.2f}%), 1's: {total_ones} ({one_ratio * 100:.2f}%)")

    return train_loader, val_loader



def train_model_single(train_loader, val_loader, seq_length):
    # 获取训练集和验证集的大小
    train_size = len(train_loader.dataset)
    val_size = len(val_loader.dataset)

    # 定义设备
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    logging.info(f"Using device: {device}")

    # 初始化模型
    model = RNNModel(input_size=2, hidden_size=64, sequence_length=seq_length).to(device)

    # 定义损失函数和优化器
    pos_weight = torch.tensor([1.0]).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # 使用BCEWithLogitsLoss，不需要手动Sigmoid
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0002)

    # 训练模型
    num_epochs = args.epoch
    start_time = time.time()
    for epoch in range(num_epochs):
        model.train()  # 设置模型为训练模式
        for seq_batch, target_batch in train_loader:
            seq_batch, target_batch = seq_batch.to(device), target_batch.to(device)
            optimizer.zero_grad()
            outputs = model(seq_batch)
            loss = criterion(outputs.squeeze(), target_batch.float())
            loss.backward()
            optimizer.step()

        # 每100个epoch打印一次训练和验证损失
        if epoch % 100 == 0:
            model.eval()  # 设置模型为评估模式
            with torch.no_grad():
                train_loss, val_loss = 0, 0
                train_acc, val_acc = 0, 0

                # 计算训练集损失和准确率
                for seq_batch, target_batch in train_loader:
                    seq_batch, target_batch = seq_batch.to(device), target_batch.to(device)
                    outputs = model(seq_batch)
                    train_loss += criterion(outputs.squeeze(), target_batch.float()).item()
                    train_acc += ((torch.sigmoid(outputs).round()) == target_batch).sum().item()

                # 计算验证集损失和准确率
                for seq_batch, target_batch in val_loader:
                    seq_batch, target_batch = seq_batch.to(device), target_batch.to(device)
                    outputs = model(seq_batch)
                    val_loss += criterion(outputs.squeeze(), target_batch.float()).item()
                    val_acc += ((torch.sigmoid(outputs).round()) == target_batch).sum().item()

                elapsed_time = time.time() - start_time
                # 打印结果
                logging.info(f'Epoch {epoch}, Train Loss: {train_loss / len(train_loader):.4f}, Train Acc: {train_acc / train_size:.4f}')
                logging.info(f'Epoch {epoch}, Val Loss: {val_loss / len(val_loader):.4f}, Val Acc: {val_acc / val_size:.4f}')
                logging.info(f'Elapsed time: {elapsed_time:.2f} seconds')
                start_time = time.time()

            val_acc_criteria = args.val_acc_criteria
            if val_acc / val_size > val_acc_criteria:
                # 保存最终的模型
                torch.save(model.state_dict(), f'final_model_{args.val_acc_criteria}_{args.seq_length}_{args.judge_length}.pth')
                logging.info(f"Final model saved to final_model_{args.val_acc_criteria}_{args.seq_length}_{args.judge_length}.pth")
                break

def process_stock_data_backtest(code, seq_length, judge_length, val_acc_criteria, start_time, end_time, resource):
    create_logger(f'{code}_back')
    
    # 定义设备
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    device = "cpu"
    logging.info(f"Using device: {device}")
    logging.info(f"Starting backtest for {code} with sequence length {seq_length}, judge length {judge_length}, and validation criteria {val_acc_criteria}")
    
    # 初始化模型
    model = RNNModel(input_size=2, hidden_size=64, sequence_length=seq_length).to(device)
    model_name = f'final_model_{val_acc_criteria}_{seq_length}_{judge_length}.pth'
    logging.info(f"Model file: {model_name}")
    
    if not os.path.exists(model_name):
        logging.warning(f"Model file {model_name} does not exist. Skipping {code}.")
        return
    try:
        model.load_state_dict(torch.load(model_name, map_location=torch.device('cpu'), weights_only=True))
        logging.info(f"Successfully loaded model {model_name}")
    except Exception as e:
        logging.error(f"Error loading model {model_name}: {e}")
        return
    
    # 获取数据的过程
    logging.info(f"Fetching market data for {code} from {start_time} to {end_time}")
    kline_data = xtdata.get_market_data_ex([], [code], period="5m", start_time=start_time, end_time=end_time, dividend_type="front")
    data = kline_data[code]
    logging.info(f"Market data for {code} fetched successfully with {len(data)} rows")
    
    # 获取流通股数据
    data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))
    first_date = pd.to_datetime(data_os.loc[0, 'date'])
    check_date = pd.to_datetime('2015-01-01')
    logging.info(f"First outstanding share data date: {first_date}")
    
    if first_date < check_date:
        logging.info("Processing outstanding share data...")
        data_post = add_outstanding_share_column(data, data_os)
        logging.info("Adding new columns and normalizing data...")
        data_post['close'] = data_post['preClose']
        data_post['open'] = data_post['preClose']
        data_post['turnover'] = data_post['volume'] * 100 / data_post['outstanding_share']
        data_post['change_percentage'] = data_post['close'].diff() / data_post['close'].shift(1)
        data_post['change_percentage'] = data_post['change_percentage'].fillna(0)
        data_post['turnover_normalized'] = normalize_0_to_1(data_post['turnover'])
        data_post['change_percentage_normalized'] = normalize(data_post['change_percentage'], code=code)
        data_post['buy'] = 0
        data_post['buy_origin'] = 0.0

        float_columns = data_post.select_dtypes(include=['float']).columns
        data_post[float_columns] = data_post[float_columns].round(4)
        logging.info(f"Data normalization and rounding completed for {code}")
        
        # 构建 RNN 输入
        turnover_normalized = data_post['turnover_normalized']
        change_percentage_normalized = data_post['change_percentage_normalized']
        rnn_input = np.column_stack((turnover_normalized, change_percentage_normalized))
        
        # 使用模型预测
        logging.info(f"Using model {model_name} for predictions...")
        for i in range(len(rnn_input) - seq_length):
            current_sequence_tensor = torch.tensor(rnn_input[i:i+seq_length], dtype=torch.float32).unsqueeze(0).to(device)
            with torch.no_grad():
                output = model(current_sequence_tensor)
                output = torch.sigmoid(output)
            if seq_length + i < len(data_post):
                data_post.iloc[seq_length + i, data_post.columns.get_loc('buy_origin')] = round(output.item(), 4)
                prediction = 1 if output.item() >= 0.9 else 0
                data_post.iloc[seq_length + i, data_post.columns.get_loc('buy')] = prediction
        
        logging.info(f"Prediction completed for {code}")
        
        # 保存处理后的数据
        output_file = f'data/{code}_{val_acc_criteria}_{seq_length}_{judge_length}_predict.csv'
        logging.info(f"Saving processed data to {output_file}")
        kline_data[code].index = pd.to_datetime(kline_data[code].index, format='%Y%m%d%H%M%S')
        kline_data[code].to_csv(output_file, index=True)
        
        # 回测
        logging.info(f"Starting backtest for {code}")
        datafeed = bt.feeds.PandasData(dataname=kline_data[code])
        cerebro = bt.Cerebro()
        cerebro.addstrategy(TestStrategy, code=code, kline_data=kline_data, hold_cycles=judge_length)
        cerebro.adddata(datafeed)
        cerebro.broker.setcash(100000.0)
        logging.info(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
        cerebro.run()
        logging.info(f'{code} {resource} Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
        
        # 保存回测结果图
        output_plot = f'data/{code}_{val_acc_criteria}_{seq_length}_{judge_length}_predict.png'
        logging.info(f"Saving backtest plot to {output_plot}")
        fig = cerebro.plot(show=False)[0][0]
        fig.set_size_inches(30, 5)
        fig.savefig(output_plot, dpi=300)
        logging.info(f"Backtest and plot for {code} completed successfully")
    else:
        logging.warning(f"Skipping {code} due to insufficient outstanding share data (first date: {first_date})")



def get_buy_value_by_index(df, index):
    """
    根据指定的索引返回 DataFrame 中 'buy' 列的值。
    
    参数：
        df (pd.DataFrame): 包含数据的 DataFrame，索引为时间。
        index (str or pd.Timestamp): 要查找的索引，支持字符串或时间戳格式。
        
    返回：
        int or None: 对应 'buy' 列的值，如果索引不存在返回 None。
    """
    try:
        # 确保输入的索引是 pd.Timestamp 类型
        index = pd.to_datetime(index)
        # 检查索引是否存在
        if index in df.index:
            return df.loc[index, 'buy']
        else:
            return f"索引 {index} 不存在于 DataFrame 中。"
    except Exception as e:
        return f"发生错误: {e}"

def create_logger(code=None):
    # 获取当前时间，格式为YYYYMMDD_HHMMSS
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 定义日志文件名，包含代码和时间戳
    log_filename = f"{current_time}_{code}.log" if code else f"{current_time}_general.log"
    log_file_path = os.path.join("log", log_filename)
    
    # 确保 log 目录存在
    os.makedirs("log", exist_ok=True)
    
    # 配置 logging，将输出重定向到日志文件
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s',
        filename=log_file_path,
        filemode='a'
    )
    
    # 将 stdout 和 stderr 重定向到日志文件
    sys.stdout = open(log_file_path, 'a', encoding='utf-8')
    sys.stderr = sys.stdout

    # 提示日志文件路径，便于检查
    logging.info(f"Logging initialized for code: {code}. Log file: {log_file_path}")

# 删除源文件（清空文件夹内容，但保留文件夹本身）
def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)  # 删除子文件夹
            else:
                os.remove(file_path)  # 删除文件
        except Exception as e:
            logging.error(f"Error removing {file_path}: {e}")

# Create a Strategy
class TestStrategy(bt.Strategy):
    params = (
        ('code', None),  # 添加 code 参数
        ('kline_data', None),
        ('hold_cycles', None),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.order = None
        self.open_time = None
        self.code = self.params.code  # 在策略中访问传递的 code
        self.kline_data = self.params.kline_data
        self.hold_cycles = self.params.hold_cycles
        logging.info("Logger initialized for strategy.")  # 确认日志初始化

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.datetime(0)
        logging.info('%s, %s' % (dt.isoformat(), txt))  # 打印日志信息

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
            if get_buy_value_by_index(self.kline_data[self.code], self.datas[0].datetime.datetime(0)):  # 使用 self.code
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.open_time = self.datas[0].datetime.datetime(0).date()
                self.order = self.buy(size=size)
        else:
            if len(self) >= (self.bar_executed + self.hold_cycles) and self.datas[0].datetime.datetime(0).date() != self.open_time:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell(size=self.position.size)

if __name__=="__main__":
    # 获取当前时间
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 设置日志文件路径
    log_filename = f"log_model_train.txt"
    log_file_path = os.path.join("log", log_filename)
    # 确保log目录存在
    os.makedirs("log", exist_ok=True)
    # 配置logging，将输出重定向到日志文件
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s', filename=log_file_path, filemode='a')
    # 将stdout和stderr重定向到日志文件
    sys.stdout = open(log_file_path, 'a', encoding='utf-8')
    sys.stderr = sys.stdout

    parser = argparse.ArgumentParser(description="超参数传参")
    parser.add_argument('mode', type=str, help="选择模式：train 或 debug")
    parser.add_argument('-sl', '--seq_length', type=int, default=480, help="指定输入序列的长度")
    parser.add_argument('-jl', '--judge_length', type=int, default=480, help="指定输出序列的长度")
    parser.add_argument('-e', '--epoch', type=int, default=1001, help="训练次数")
    parser.add_argument('-vac', '--val_acc_criteria', type=float, default=0.9, help="训练次数")
    parser.add_argument('-sd', '--start_date', type=str, default="20240601", help="开始时间")
    parser.add_argument('-ed', '--end_date', type=str, default="20241201", help="结束时间")
    parser.add_argument('-cl', '--code_list', type=str, default=[], help="训练代码列表")
    parser.add_argument('-clb', '--code_list_backtrader', type=str, default=[], help="回测代码列表")
    args = parser.parse_args()
    # 将逗号分隔的字符串解析为列表
    print(f"Mode: {args.mode}")
    code_list = args.code_list.split(",") if args.code_list else []
    logging.info(code_list)
    code_list_backtrader = args.code_list_backtrader.split(",") if args.code_list_backtrader else []
    logging.info(code_list_backtrader)

    if args.mode == "train":
        try:
            seq_length = args.seq_length
            judge_length = args.judge_length
            val_acc_criteria = args.val_acc_criteria
            logging.info(f'seq_length is {seq_length} judge_length is {judge_length}')
            
            # 记录开始和结束时间
            logging.info(f"Training data from {args.start_date} to {args.end_date}")
            
            train_loader, val_loader = train_data(seq_length=seq_length, judge_length=judge_length, start_time=args.start_date, end_time=args.end_date)
            
            logging.info("Training model...")
            train_model_single(train_loader=train_loader, val_loader=val_loader, seq_length=seq_length)
            
        except Exception as e:
            logging.error("*******************")
            logging.error(f"Exception occurred: {str(e)}")
            
            # 使用 traceback 来记录详细的堆栈信息
            logging.error("Stack trace:")
            logging.error(traceback.format_exc())
            
            logging.error("*******************")
    elif args.mode == "debug":
            seq_length = args.seq_length
            judge_length = args.judge_length
            val_acc_criteria = args.val_acc_criteria
            logging.info(f'seq_length is {seq_length} judge_length is {judge_length}')
            train_loader, val_loader = train_data(seq_length=seq_length, judge_length=judge_length, start_time=args.start_date, end_time=args.end_date)