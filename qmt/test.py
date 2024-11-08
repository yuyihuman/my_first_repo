import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import time
import akshare as ak
from xtquant import xtdata
from torch.utils.data import Dataset, DataLoader, random_split
from datetime import datetime
from data_prepare import get_stock_list
import io
import sys
from torch.utils.data import ConcatDataset

# 使用带 UTF-8 编码的文件流进行标准输出重定向
log_file = open('log', 'w', encoding='utf-8', buffering=1)
sys.stdout = io.TextIOWrapper(log_file.buffer, encoding='utf-8', line_buffering=True)

# 读取股票数据的函数
def read_stock_data(code_list,period):
    total_stocks = len(code_list)
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # 逐个订阅每个股票的实时行情并输出进度
    for index, code in enumerate(code_list):
        # 打印当前股票的订阅状态
        print(f"Subscribing to {code} ({index + 1}/{total_stocks})...")
        # 订阅行情数据
        xtdata.subscribe_quote(code, period=period, count=-1)  # count=-1 订阅当天所有实时行情
        # 打印当前已完成的进度百分比
        print(f"Subscription completed for {code}.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")
    # 等待订阅完成
    time.sleep(1)
    # 获取指定股票的历史数据
    kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time='20240101')
    for code in code_list:
        data = kline_data[code]
        open_prices = data['open'].values
        close_prices = data['close'].values
        change_percentages = ((close_prices - open_prices) / open_prices)
        data.to_csv(f'data/{code}_{current_time}.csv')
        # 确保 change_percentages 的长度足够大
        if len(change_percentages) <= 5:
            print(f"数据长度不足以计算 rnn_target，跳过代码: {code}")
            continue
        # 输入特征是开盘价和收盘价
        rnn_input = np.column_stack((open_prices, close_prices))
        # 初始化 rnn_target
        rnn_target = np.zeros(len(change_percentages) - 5, dtype=int)
        # 遍历每个 n，计算从 n+1 到 n+5 的连乘并判断是否大于 1.3
        for n in range(len(change_percentages) - 5):
            product = np.prod(1 + change_percentages[n+1:n+6])
            if product > 1.3:
                rnn_target[n] = 1
            else:
                rnn_target[n] = 0
        # 因为 rnn_target 缩短了5个，所以 rnn_input 也要相应缩短
        rnn_input = rnn_input[:-5]
    # return open_prices, close_prices, change_percentages, exchange_percentages, rnn_input, rnn_target

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

def run():
    # 使用带 UTF-8 编码的文件流进行标准输出重定向
    log_file = open('log', 'w', encoding='utf-8')
    sys.stdout = io.TextIOWrapper(log_file.buffer, encoding='utf-8', line_buffering=True)

    period="5m"
    code_list = get_stock_list(lower_bound=100,upper_bound=103)
    total_stocks = len(code_list)
    if 1:
    ## 为了方便用户进行数据管理，xtquant的大部分历史数据都是以压缩形式存储在本地的
    ## 比如行情数据，需要通过download_history_data下载，财务数据需要通过
    ## 所以在取历史数据之前，我们需要调用数据下载接口，将数据下载到本地
        for index, code in enumerate(code_list):
            # 打印进度
            print(f"Downloading {code} ({index + 1}/{total_stocks})...")
            # 下载数据
            xtdata.download_history_data(code, period=period, incrementally=True)
            # 打印已完成的进度
            print(f"{code} download completed.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")

    start_time = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
    stop_time = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
    while True:
        now = datetime.now()
        if start_time<=now<=stop_time and now.minute%5==0:
            print(f'begin at {now}')
            read_stock_data(code_list=code_list,period=period)
            read_stock_floating_share()
            now = datetime.now()
            print(f'end at {now}')
            time.sleep(60)
        time.sleep(1)

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

# RNN模型类
class RNN(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers=5, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        out = out[:, -1, :]  # 取最后一个时间步的输出
        out = self.fc(out)   # 线性层输出
        return out

all_datasets = []
def train_data():
    period="5m"
    code_list = get_stock_list(lower_bound=100,upper_bound=100.5)
    total_stocks = len(code_list)
    if 1:
    ## 为了方便用户进行数据管理，xtquant的大部分历史数据都是以压缩形式存储在本地的
    ## 比如行情数据，需要通过download_history_data下载，财务数据需要通过
    ## 所以在取历史数据之前，我们需要调用数据下载接口，将数据下载到本地
        for index, code in enumerate(code_list):
            # 打印进度
            print(f"Downloading {code} ({index + 1}/{total_stocks})...")
            # 下载数据
            xtdata.download_history_data(code, period=period, incrementally=True)
            # 打印已完成的进度
            print(f"{code} download completed.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")

    kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time='20100101')
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
            judge_length = 48
            rnn_target = np.zeros(len(change_percentage) - judge_length, dtype=int)
            for n in range(len(change_percentage) - judge_length):
                product_1 = np.prod(1 + change_percentage[n:n+judge_length])
                product_2 = np.prod(1 + change_percentage[n:n+judge_length//2])
                product_3 = np.prod(1 + change_percentage[n:n+judge_length//4])
                product_4 = np.prod(1 + change_percentage[n:n+judge_length//8])
                if product_4 > 1.01 and product_1 > 1.08:
                    rnn_target[n] = 1
                    print(f'change_percentage[{n}:{n+judge_length}] is:\n{change_percentage[n:n+judge_length]}')
                else:
                    rnn_target[n] = 0
            rnn_input = rnn_input[:-judge_length]

            # 定义序列长度
            seq_length = 1440
            # 构建输入序列
            learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input) - seq_length)]
            learn_trunks_np = np.array(learn_trunks)
            target_np = rnn_target[seq_length:]  # 目标要对齐输入序列

            # 检查 target_np 中值为 1 的位置
            for i, target in enumerate(target_np):
                if target == 1:
                    print(f"Target 1 found at index {i}, corresponding learn_trunks:")
                    print(learn_trunks_np[i])  # 打印对应的 learn_trunks_np

            rnn_dataset = RnnDataset(torch.tensor(learn_trunks_np), torch.tensor(target_np))
            all_datasets.append(rnn_dataset)

            data_post.to_csv(f'data/{code}_post.csv')
    combined_dataset = ConcatDataset(all_datasets)

    # 数据集划分
    train_ratio = 0.8
    total_len = len(combined_dataset)
    print(f'total_len is {total_len}')
    train_size = int(train_ratio * total_len)
    val_size = total_len - train_size
    train_data, val_data = random_split(combined_dataset, [train_size, val_size])

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

def download_data(code_list):
    period="5m"
    total_stocks = len(code_list)
    if 1:
    ## 为了方便用户进行数据管理，xtquant的大部分历史数据都是以压缩形式存储在本地的
    ## 比如行情数据，需要通过download_history_data下载，财务数据需要通过
    ## 所以在取历史数据之前，我们需要调用数据下载接口，将数据下载到本地
        for index, code in enumerate(code_list):
            # 打印进度
            print(f"Downloading {code} ({index + 1}/{total_stocks})...")
            # 下载数据
            xtdata.download_history_data(code, period=period, incrementally=True)
            # 打印已完成的进度
            print(f"{code} download completed.\nProgress: {round((index + 1) / total_stocks * 100, 2)}%")
    kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time='20240101')
    return kline_data

def train_data_single(code, kline_data):
    print(f'=========================================')
    print(f'code {code} start')
    print(f'=========================================')
    data = kline_data[code]
    data.to_csv(f'data/{code}.csv')
    data_os = read_single_stock_outstanding_share(code=convert_stock_code(code))
    first_date = pd.to_datetime(data_os.loc[0, 'date'])
    check_date = pd.to_datetime('2010-01-01')
    if first_date < check_date:
        train_flag = 1
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
        judge_length = 48
        rnn_target = np.zeros(len(change_percentage) - judge_length, dtype=int)
        for n in range(len(change_percentage) - judge_length):
            product_1 = np.prod(1 + change_percentage[n:n+judge_length])
            product_2 = np.prod(1 + change_percentage[n:n+judge_length//2])
            product_3 = np.prod(1 + change_percentage[n:n+judge_length//4])
            product_4 = np.prod(1 + change_percentage[n:n+judge_length//8])
            if product_4 > 1.01 and product_1 > 1.08:
                rnn_target[n] = 1
                print(f'change_percentage[{n}:{n+judge_length}] is:\n{change_percentage[n:n+judge_length]}')
            else:
                rnn_target[n] = 0
        rnn_input = rnn_input[:-judge_length]

        # 定义序列长度
        seq_length = 144
        # 构建输入序列
        learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input) - seq_length)]
        learn_trunks_np = np.array(learn_trunks)
        target_np = rnn_target[seq_length:]  # 目标要对齐输入序列

        # 检查 target_np 中值为 1 的位置
        for i, target in enumerate(target_np):
            if target == 1:
                print(f"Target 1 found at index {i}, corresponding learn_trunks:")
                print(learn_trunks_np[i])  # 打印对应的 learn_trunks_np

        rnn_dataset = RnnDataset(torch.tensor(learn_trunks_np), torch.tensor(target_np))

        data_post.to_csv(f'data/{code}_post.csv')
    else:
        train_flag = 0

    # 数据集划分
    train_ratio = 0.8
    total_len = len(rnn_dataset)
    print(f'total_len is {total_len}')
    train_size = int(train_ratio * total_len)
    val_size = total_len - train_size
    train_data, val_data = random_split(rnn_dataset, [train_size, val_size])

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

    return train_loader, val_loader, train_flag

def train_model(train_loader, val_loader):
    # 获取训练集和验证集的大小
    train_size = len(train_loader.dataset)
    val_size = len(val_loader.dataset)

    # 定义设备
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 初始化模型
    model = RNN(input_size=2, hidden_size=64).to(device)

    # 定义损失函数和优化器
    criterion = nn.BCEWithLogitsLoss()  # 使用BCEWithLogitsLoss，不需要手动Sigmoid
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

    # 训练模型
    num_epochs = 1000
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

    # 保存模型
    torch.save(model.state_dict(), 'rnn_model.pth')

# train_loader, val_loader = train_data()
# train_model(train_loader=train_loader, val_loader=val_loader)

code_list = get_stock_list(lower_bound=100,upper_bound=100.5)
kline_data = download_data(code_list)
for code in code_list:
    train_loader, val_loader, train_flag = train_data_single(code=code, kline_data=kline_data)
    if train_flag == 1:
        train_model(train_loader=train_loader, val_loader=val_loader)
        break