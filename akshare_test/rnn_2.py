import torch
import torch.nn as nn
import numpy as np

from read_stock_data import read_stock_data
from torch.utils.data import Dataset, DataLoader, random_split

# Fully connected neural network with one hidden layer
class RNN(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)  # 输出层改为一个神经元，用于二分类
        self.sigmoid = nn.Sigmoid()  # 添加 sigmoid 激活函数，将输出映射到0-1之间

    def forward(self, x):
        batch_size = x.size(0)
        seq_len = x.size(1)
        # 输入形状为 (batch_size, seq_len, input_size)
        # 这里不需要再reshape了，因为输入已经符合GRU的输入要求

        # GRU forward pass
        out, _ = self.gru(x)

        # 取最后一个时间步的输出作为最终的表示
        out = out[:, -1, :]

        # 全连接层和sigmoid激活函数得到最终的输出
        out = self.fc(out)
        out = self.sigmoid(out)

        # 将输出转换为布尔值（0或1）
        out = (out > 0.5).float()

        return out


model = RNN(input_size=2, hidden_size=4) 

print(model) 
# 打印模型参数数量
total_params = sum(p.numel() for p in model.parameters())
print("Total parameters:", total_params)

open_prices, close_prices, change_percentages, exchange_percentages, rnn_input, rnn_target = read_stock_data('000001.csv')
print("开盘价向量:", open_prices, "长度:", len(open_prices))
print("收盘价向量:", close_prices, "长度:", len(close_prices))
print("涨跌幅向量:", change_percentages, "长度:", len(change_percentages))
print("换手率向量:", exchange_percentages, "长度:", len(exchange_percentages))
print("RNN输入向量:", rnn_input, "长度:", len(rnn_input))
print("RNN目标向量:", rnn_target, "长度:", len(rnn_target))

class RnnDataset(Dataset):
    def __init__(self, learn_trunks, target, seq_length):
        self.learn_trunks = learn_trunks
        self.target = target

    def __len__(self):
        return len(self.learn_trunks)-1
    
    def __getitem__(self, idx):
        return self.learn_trunks[idx].float(), self.target[idx+seq_length].float()

seq_length = 20
learn_trunks = [rnn_input[i:i+seq_length] for i in range(len(rnn_input)-seq_length+1)]
learn_trunks_np = np.array(learn_trunks)
target_np = np.array(rnn_target)
rnn_dataset = RnnDataset(torch.tensor(learn_trunks_np), torch.tensor(target_np), seq_length)

train_ratio = 0.8
total_len = len(rnn_dataset)
train_size = int(train_ratio * total_len)
val_size = total_len - train_size
train_data, val_data = random_split(rnn_dataset, [train_size, val_size])
print(len(train_data))
print(len(val_data))
print(len(rnn_dataset))


for i, (seq, target) in enumerate(rnn_dataset):
    if i == 0:
        print('First Input (x):', seq)
        print('First Target (y):', target)
        print()
    if i == len(rnn_dataset)-1:
        print('Last Input (x):', seq)
        print('Last Target (y):', target)
        print()

device = torch.device("cuda:0")
# device = torch.device("cpu")

batch_size = 64
torch.manual_seed(1)
rnn_loader = DataLoader(rnn_dataset, batch_size=batch_size, shuffle=False, drop_last=True)
train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, drop_last=True)
val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=True, drop_last=True)
model = model.to(device)

# 定义损失函数和优化器
criterion = nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

# 训练模型
num_epochs = 1000
for epoch in range(num_epochs):
    for i, (seq_batch, target_batch) in enumerate(train_loader):
        seq_batch, target_batch = seq_batch.to(device), target_batch.to(device)
        optimizer.zero_grad()
        outputs = model(seq_batch)
        loss = criterion(outputs, target_batch.float())
        loss.backward()
        optimizer.step()

    # 每隔100个epoch打印一次训练损失和验证损失
    if epoch % 100 == 0:
        with torch.no_grad():
            train_loss = 0
            val_loss = 0
            train_acc = 0
            val_acc = 0
            for seq_batch, target_batch in train_loader:
                outputs = model(seq_batch)
                loss = criterion(outputs, target_batch.float())
                train_loss += loss.item()
                train_acc += (outputs.round() == target_batch.float()).sum().item()
            for seq_batch, target_batch in val_loader:
                outputs = model(seq_batch)
                loss = criterion(outputs.squeeze(), target_batch.float())
                val_loss += loss.item()
                val_acc += (outputs.round() == target_batch.float()).sum().item()
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            train_acc /= len(train_data)
            val_acc /= len(val_data)
            print(f'Epoch {epoch}, Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}')
            print(f'Epoch {epoch}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}')

# 保存模型
torch.save(model.state_dict(), 'rnn_model.pth')