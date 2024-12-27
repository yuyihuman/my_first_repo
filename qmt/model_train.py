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
    print(stock_zh_a_daily_qfq_df)
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
    min_val = column.min()
    max_val = column.max()
    return (column - min_val) / (max_val - min_val)

def get_model_para(model_name):
    print(model_name)
    input_length = int(model_name.replace(".pth","").split("_")[-2])
    hold_days = int(model_name.replace(".pth","").split("_")[-1])
    accuracy = float(model_name.replace(".pth","").split("_")[-3])
    return input_length, hold_days, accuracy

def evaluate_signal_at_n(column, n, judge_length, threshold_1=0.08, threshold_4=0.02):
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
    if product_4 > 1 + (judge_length / 240 * threshold_4) and product_1 > 1 + (judge_length / 240 * threshold_1):
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
    # 获取数据的过程
    kline_data = xtdata.get_market_data_ex([], [code], period="1m", start_time=start_time, end_time=end_time)
    data = kline_data[code]
    
    data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))
    first_date = pd.to_datetime(data_os.loc[0, 'date'])
    check_date = pd.to_datetime('2010-01-01')
    
    if first_date < check_date:
        data_post = add_outstanding_share_column(data, data_os)
        data_post['turnover'] = data_post['volume'] * 100 / data_post['outstanding_share']
        data_post['change_percentage'] = data_post['close'].diff() / data_post['close'].shift(1)
        data_post['change_percentage'] = data_post['change_percentage'].fillna(0)
        data_post['turnover_normalized'] = normalize_0_to_1(data_post['turnover'])
        data_post['change_percentage_normalized'] = normalize(data_post['change_percentage'], code=code)

        float_columns = data_post.select_dtypes(include=['float']).columns
        data_post[float_columns] = data_post[float_columns].round(4)

        turnover_normalized = data_post['turnover_normalized']
        change_percentage = data_post['change_percentage']
        change_percentage_normalized = data_post['change_percentage_normalized']
        data_post.to_csv(f'data/{code}.csv')
        rnn_input = np.column_stack((turnover_normalized, change_percentage_normalized))
        rnn_target = np.zeros(len(change_percentage) - judge_length, dtype=int)
        positive_counter = 0
        
        # Process each change_percentage sequence
        for n in range(len(change_percentage) - judge_length):
            if evaluate_signal_at_n(column=change_percentage, n=n, judge_length=judge_length):
                rnn_target[n] = 1
                positive_counter += 1
            else:
                rnn_target[n] = 0
                
        if positive_counter == 0:
            print(f"Skipping {code} due to no positive samples.")
            return None  # Skip if no positive samples
        
        rnn_input = rnn_input[:-judge_length]

        # Construct learning trunks
        learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input) - seq_length)]
        learn_trunks_np = np.array(learn_trunks)
        target_np = rnn_target[seq_length:]  # Align target with input sequences

        positive_indices = np.where(target_np == 1)[0]
        negative_indices = np.where(target_np == 0)[0]
        
        # Handle positive and negative samples
        x = len(positive_indices)
        sampled_negative_indices = random.sample(list(negative_indices), min(1 * x, len(negative_indices)))
        selected_indices = np.concatenate([positive_indices, sampled_negative_indices])
        np.random.shuffle(selected_indices)

        filtered_learn_trunks = learn_trunks_np[selected_indices]
        filtered_targets = target_np[selected_indices]

        # Create rnn_dataset
        rnn_dataset = RnnDataset(torch.tensor(filtered_learn_trunks, dtype=torch.float32), 
                                 torch.tensor(filtered_targets, dtype=torch.long))
        return rnn_dataset

def train_data(seq_length, judge_length):
    start_time = args.start_date
    end_time = args.end_date
    all_datasets = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=20) as executor:
        # Parallel processing for each stock
        futures = []
        for code in code_list:
            futures.append(executor.submit(process_stock_data, code, seq_length, judge_length, start_time, end_time))
        
        # Collect results
        for future in concurrent.futures.as_completed(futures):
            rnn_dataset = future.result()
            if rnn_dataset is not None:
                all_datasets.append(rnn_dataset)

    combined_dataset = ConcatDataset(all_datasets)

    # 数据集划分
    total_len = len(combined_dataset)
    print(f'total_len is {total_len}')
    if total_len*0.3 > 5000:
        train_size = 5000
    else:
        train_size = int(total_len*0.3)
    if total_len-train_size > 5000:
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
    print(f"Total samples in train_data:{len(train_data)}")
    print(f"Total samples in val_data:{len(val_data)}")

    # 取出第一个 batch
    for learn_trunks_batch, target_batch in train_loader:
        print("Batch learn_trunks shape:", learn_trunks_batch.shape)  # (batch_size, seq_length, feature_dim)
        print("Batch target shape:", target_batch.shape)              # (batch_size,)

        # 计算目标标签中的 0 和 1 的比例
        num_zeros = (target_batch == 0).sum().item()
        num_ones = (target_batch == 1).sum().item()
        total = target_batch.size(0)
        zero_ratio = num_zeros / total
        one_ratio = num_ones / total

        print(f"Batch label distribution: 0's: {num_zeros} ({zero_ratio * 100:.2f}%), 1's: {num_ones} ({one_ratio * 100:.2f}%)")
        
        break  # 仅展示第一个 batch

    return train_loader, val_loader


def train_model_single(train_loader, val_loader, seq_length):
    # 获取训练集和验证集的大小
    train_size = len(train_loader.dataset)
    val_size = len(val_loader.dataset)

    # 定义设备
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

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
                print(f'Epoch {epoch}, Train Loss: {train_loss / len(train_loader):.4f}, Train Acc: {train_acc / train_size:.4f}')
                print(f'Epoch {epoch}, Val Loss: {val_loss / len(val_loader):.4f}, Val Acc: {val_acc / val_size:.4f}')
                print(f'Elapsed time: {elapsed_time:.2f} seconds')
                start_time = time.time()

            val_acc_criteria = args.val_acc_criteria
            if val_acc / val_size > val_acc_criteria:
                # 保存最终的模型
                torch.save(model.state_dict(), f'final_model_{val_acc_criteria}_{args.seq_length}_{args.judge_length}.pth')
                print(f"Final model saved to final_model_{args.seq_length}_{args.judge_length}.pth")
                if 1:
                    # 设定一个标的列表
                    code_list = code_list_backtrader
                    period = '1m'
                    start_time = args.start_date
                    end_time = args.end_date
                    kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time=start_time, end_time=end_time)

                    for code in code_list:
                        data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))
                        first_date = pd.to_datetime(data_os.loc[0, 'date'])
                        check_date = pd.to_datetime('2015-01-01')
                        if first_date < check_date:
                            data_post = add_outstanding_share_column(kline_data[code], data_os)
                            data_post['turnover'] = data_post['volume'] * 100 / data_post['outstanding_share']
                            # data_post['change_percentage'] = (data_post['close'] - data_post['open']) / data_post['open']
                            data_post['change_percentage'] = data_post['close'].diff() / data_post['close'].shift(1)
                            data_post['change_percentage'] = data_post['change_percentage'].fillna(0)
                            data_post['turnover_normalized'] = normalize_0_to_1(data_post['turnover'])
                            data_post['change_percentage_normalized'] = normalize(data_post['change_percentage'], code=code)
                            data_post['buy'] = 0
                            data_post['buy_origin'] = 0
                            float_columns = data_post.select_dtypes(include=['float']).columns
                            data_post[float_columns] = data_post[float_columns].round(4)
                            turnover_normalized = data_post['turnover_normalized']
                            change_percentage = data_post['change_percentage']
                            change_percentage_normalized = data_post['change_percentage_normalized']
                            rnn_input = np.column_stack((turnover_normalized, change_percentage_normalized))
                            seq_length = args.seq_length

                            # use model to predict when to buy 
                            for i in range(len(rnn_input) - seq_length):
                                current_sequence_tensor = torch.tensor(rnn_input[i:i+seq_length], dtype=torch.float32).unsqueeze(0).to(device)
                                with torch.no_grad():
                                    output = model(current_sequence_tensor)
                                    output = torch.sigmoid(output)
                                # print(output.item())  # 打印单个预测值
                                if seq_length + i < len(data_post):
                                    data_post.iloc[seq_length + i, data_post.columns.get_loc('buy_origin')] = round(output.item(), 4)
                                    prediction = 1 if output.item() >= 0.5 else 0
                                    data_post.iloc[seq_length + i, data_post.columns.get_loc('buy')] = prediction

                            data_post.to_csv(f'data/{code}_{val_acc_criteria}_{args.seq_length}_{args.judge_length}_post_modeltest.csv', index=True)
                break

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

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="超参数传参")
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
    code_list = args.code_list.split(",") if args.code_list else []
    print(code_list)
    code_list_backtrader = args.code_list_backtrader.split(",") if args.code_list_backtrader else []
    print(code_list_backtrader)
    # 使用带 UTF-8 编码的文件流进行标准输出重定向
    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f'log/log_{current_time}_{args.seq_length}_{args.judge_length}.txt'
    log_file = open(log_filename, 'w', encoding='utf-8', buffering=1)
    sys.stdout = io.TextIOWrapper(log_file.buffer, encoding='utf-8', line_buffering=True)

    try:
        seq_length = args.seq_length
        judge_length = args.judge_length
        print(f'seq_length is {seq_length} judge_length is {judge_length}')
        train_loader, val_loader = train_data(seq_length=seq_length, judge_length=judge_length)
        train_model_single(train_loader=train_loader, val_loader=val_loader, seq_length=seq_length)
    except Exception as e:
        print("*******************")
        print(e)
        print("*******************")