import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader, random_split

# 读取股票数据的函数
def read_stock_data(file_path):
    data = pd.read_csv(file_path)
    open_prices = data['开盘'].values
    close_prices = data['收盘'].values
    change_percentages = data['涨跌幅'].values
    exchange_percentages = data['换手率'].values

    # 输入特征是开盘价和收盘价
    rnn_input = np.column_stack((open_prices, close_prices))
    
    # 目标是涨跌标记（涨幅大于0标记为1，小于等于0标记为0）
    rnn_target = (change_percentages > 0).astype(int)
    
    return open_prices, close_prices, change_percentages, exchange_percentages, rnn_input, rnn_target

# RNN模型类
class RNN(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        out = out[:, -1, :]  # 取最后一个时间步的输出
        out = self.fc(out)   # 线性层输出
        return out

# Dataset类
class RnnDataset(Dataset):
    def __init__(self, learn_trunks, target):
        self.learn_trunks = learn_trunks
        self.target = target

    def __len__(self):
        return len(self.learn_trunks)
    
    def __getitem__(self, idx):
        return self.learn_trunks[idx].float(), self.target[idx].float()

# 读取并预处理数据
open_prices, close_prices, change_percentages, exchange_percentages, rnn_input, rnn_target = read_stock_data('000001.csv')

# 定义序列长度
seq_length = 20
# 构建输入序列
learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input) - seq_length)]
learn_trunks_np = np.array(learn_trunks)
target_np = rnn_target[seq_length:]  # 目标要对齐输入序列
rnn_dataset = RnnDataset(torch.tensor(learn_trunks_np), torch.tensor(target_np))

# 数据集划分
train_ratio = 0.8
total_len = len(rnn_dataset)
train_size = int(train_ratio * total_len)
val_size = total_len - train_size
train_data, val_data = random_split(rnn_dataset, [train_size, val_size])

# 定义DataLoader
batch_size = 64
train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, drop_last=True)
val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False, drop_last=True)

# 定义设备
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# 初始化模型
model = RNN(input_size=2, hidden_size=4).to(device)

# 定义损失函数和优化器
criterion = nn.BCEWithLogitsLoss()  # 使用BCEWithLogitsLoss，不需要手动Sigmoid
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

# 训练模型
num_epochs = 1000
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

            # 打印结果
            print(f'Epoch {epoch}, Train Loss: {train_loss / len(train_loader):.4f}, Train Acc: {train_acc / train_size:.4f}')
            print(f'Epoch {epoch}, Val Loss: {val_loss / len(val_loader):.4f}, Val Acc: {val_acc / val_size:.4f}')

# 保存模型
torch.save(model.state_dict(), 'rnn_model.pth')
