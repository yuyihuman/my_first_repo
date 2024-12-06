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

from xtquant import xtdata
from torch.utils.data import Dataset, DataLoader, random_split
from datetime import datetime
from data_prepare import get_stock_list
from torch.utils.data import ConcatDataset
from torch.utils.data import Subset

parser = argparse.ArgumentParser(description="超参数传参")
parser.add_argument('-sl', '--seq_length', type=int, default=480, help="指定输入序列的长度")
parser.add_argument('-jl', '--judge_length', type=int, default=480, help="指定输出序列的长度")
parser.add_argument('-e', '--epoch', type=int, default=1001, help="训练次数")
parser.add_argument('-sd', '--start_date', type=str, default="20240601", help="开始时间")
parser.add_argument('-ed', '--end_date', type=str, default="20241201", help="结束时间")
args = parser.parse_args()

def read_stock_floating_share():
    stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
    stock_zh_a_spot_em_df.to_csv(f'data/stock_outstanding_share.csv')

def read_single_stock_outstanding_share(code="sz000001"):
    now = datetime.now()
    date_string = now.strftime("%Y%m%d")
    stock_zh_a_daily_qfq_df = ak.stock_zh_a_daily(symbol=code, start_date="19910403", end_date=date_string, adjust="qfq")
    print(stock_zh_a_daily_qfq_df)
    stock_zh_a_daily_qfq_df.to_csv(f'data/{code}outstanding_share.csv')
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

def normalize(column):
    min_val = column.min()
    max_val = column.max()
    return (2 * (column - min_val) / (max_val - min_val)) - 1

def normalize_0_to_1(column):
    min_val = column.min()
    max_val = column.max()
    return (column - min_val) / (max_val - min_val)

# Dataset类
class RnnDataset(Dataset):
    def __init__(self, learn_trunks, target):
        self.learn_trunks = learn_trunks
        self.target = target

    def __len__(self):
        return len(self.learn_trunks)
    
    def __getitem__(self, idx):
        return self.learn_trunks[idx].float(), self.target[idx].float()

# GRU模型类
class GRUModel(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers=5, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        out = out[:, -1, :]  # 取最后一个时间步的输出
        out = self.fc(out)   # 线性层输出
        return out
    
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

all_datasets = []
def train_data(seq_length, judge_length):
    start_time=args.start_date
    end_time=args.end_date
    period="1m"
    code_list = get_stock_list(lower_bound=150,upper_bound=160)
    total_stocks = len(code_list)
    xtdata.enable_hello = False
    if 1:
    ## 为了方便用户进行数据管理，xtquant的大部分历史数据都是以压缩形式存储在本地的
    ## 比如行情数据，需要通过download_history_data下载，财务数据需要通过
    ## 所以在取历史数据之前，我们需要调用数据下载接口，将数据下载到本地
        for index, code in enumerate(code_list):
            # 打印进度
            print(f"Downloading {code} ({index + 1}/{total_stocks})...")
            # 下载数据
            xtdata.download_history_data(code, period=period, incrementally=True, start_time=start_time)
            # 打印已完成的进度
            print(f"{code} download completed.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")

    kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time=start_time, end_time=end_time)
    for code in code_list:
        print(f'=========================================')
        print(f'code {code} start')
        print(f'=========================================')
        data = kline_data[code]
        data.to_csv(f'data/{code}.csv')
        data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))
        first_date = pd.to_datetime(data_os.loc[0, 'date'])
        check_date = pd.to_datetime('2010-01-01')
        if first_date < check_date:
            data_post = add_outstanding_share_column(data, data_os)
            data_post['turnover'] = data_post['volume'] * 100 / data_post['outstanding_share']
            data_post['change_percentage'] = (data_post['close'] - data_post['open']) / data_post['open']
            data_post['turnover_normalized'] = normalize_0_to_1(data_post['turnover'])
            data_post['change_percentage_normalized'] = normalize(data_post['change_percentage'])

            float_columns = data_post.select_dtypes(include=['float']).columns
            data_post[float_columns] = data_post[float_columns].round(4)

            turnover_normalized = data_post['turnover_normalized']
            change_percentage = data_post['change_percentage']
            change_percentage_normalized = data_post['change_percentage_normalized']
            rnn_input = np.column_stack((turnover_normalized, change_percentage_normalized))
            judge_length = judge_length
            rnn_target = np.zeros(len(change_percentage) - judge_length, dtype=int)
            positive_counter = 0
            for n in range(len(change_percentage) - judge_length):
                product_1 = np.prod(1 + change_percentage[n:n+judge_length])
                product_2 = np.prod(1 + change_percentage[n:n+judge_length//2])
                product_3 = np.prod(1 + change_percentage[n:n+judge_length//4])
                product_4 = np.prod(1 + change_percentage[n:n+judge_length//8])
                if product_4 > 1+(judge_length/240*0.01) and product_1 > 1+(judge_length/240*0.08):
                    rnn_target[n] = 1
                    positive_counter += 1
                    print(f'change_percentage[{n}:{n+judge_length}] is:\n{change_percentage[n:n+judge_length]}')
                else:
                    rnn_target[n] = 0
            print(f'positive_counter is {positive_counter}')
            if positive_counter == 0:
                print('continue')
                continue
            rnn_input = rnn_input[:-judge_length]

            # 定义序列长度
            seq_length = seq_length
            # 构建输入序列
            learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input) - seq_length)]
            learn_trunks_np = np.array(learn_trunks)
            target_np = rnn_target[seq_length:]  # 目标要对齐输入序列

            # 查找 target == 1 和 target == 0 的索引
            positive_indices = np.where(target_np == 1)[0]
            negative_indices = np.where(target_np == 0)[0]
            first_positive_index = positive_indices[0]

            # 计算 target == 1 的数量
            x = len(positive_indices)

            # 从 target == 0 中随机抽取 100x 条数据
            sampled_negative_indices = random.sample(list(negative_indices), min(1 * x, len(negative_indices)))

            # 合并 target == 1 和采样的 target == 0 的数据索引
            selected_indices = np.concatenate([positive_indices, sampled_negative_indices])

            # 打乱索引以避免顺序问题
            np.random.shuffle(selected_indices)

            # 根据选定索引提取数据
            filtered_learn_trunks = learn_trunks_np[selected_indices]
            filtered_targets = target_np[selected_indices]

            # 获取对应的 filtered_learn_trunks 和 filtered_targets
            first_filtered_learn_trunk = learn_trunks_np[first_positive_index]
            first_filtered_target = target_np[first_positive_index]

            # 打印对应的数据
            print(f"First sample where target == 1:")
            print(f"Index: {first_positive_index}")
            print(f"Filtered learn trunk: {first_filtered_learn_trunk}")
            print(f"Filtered target: {first_filtered_target}")

            # 打印统计信息
            print(f"Total positive samples (target == 1): {x}")
            print(f"Total negative samples (target == 0) selected: {len(sampled_negative_indices)}")
            print(f"Total samples in dataset: {len(selected_indices)}")

            # 创建 rnn_dataset
            rnn_dataset = RnnDataset(torch.tensor(filtered_learn_trunks, dtype=torch.float32), 
                                    torch.tensor(filtered_targets, dtype=torch.long))
            all_datasets.append(rnn_dataset)

            data_post.to_csv(f'data/{code}_post.csv')
    combined_dataset = ConcatDataset(all_datasets)

    # 数据集划分
    total_len = len(combined_dataset)
    if total_len*0.3 > 5000:
        train_size = 5000
    else:
        train_size = int(total_len*0.3)
    if total_len-train_size > 10000:
        val_size = 10000
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

        val_acc_criteria = 0.85
        if val_acc / val_size > val_acc_criteria:
            # 保存最终的模型
            torch.save(model.state_dict(), f'final_model_{args.seq_length}_{args.judge_length}_{val_acc_criteria}.pth')
            print(f"Final model saved to final_model_{args.seq_length}_{args.judge_length}.pth")
            break



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