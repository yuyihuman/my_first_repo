import torch
import torch.nn as nn
import numpy as np
import time
from read_stock_data import read_stock_data
from torch.utils.data import Dataset, DataLoader, random_split

# Fully connected neural network with one hidden layer
class RNN(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.rnns = nn.ModuleList([
            nn.RNN(input_size, hidden_size, num_layers=1, batch_first=True) 
            for _ in range(15)
        ])
        #self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True)
        #self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(15*hidden_size, 1)
        
    def forward(self, x):
        batch_size = x.size(0)
        # 将输入重新整形成 (batch_size, seq_length, input_size)
        x = x.view(batch_size, -1, 2)
        hidden_states = []
        for i in range(15):
            _, hidden = self.rnns[i](x[:,i:,:])
            # print("张量的形状:", x[:,i:,:].shape)
            hidden_states.append(hidden)
        combined_hidden = torch.cat(hidden_states, dim=2)
        # print("张量的形状:", combined_hidden.shape)
        out = combined_hidden[-1, :, :]
        # print("张量的形状:", out.shape)
        out = self.fc(out)
        return out

model = RNN(2, 32) 

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

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
if device.type == "cuda":
    print("Using GPU for training!")
else:
    print("Using CPU for training.")
# device = torch.device("cpu")

batch_size = 64
torch.manual_seed(1)
rnn_loader = DataLoader(rnn_dataset, batch_size=batch_size, shuffle=False, drop_last=True)
train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, drop_last=True)
val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=True, drop_last=True)
model = model.to(device)

loss_fn = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

num_epochs = 1000

start_time = time.time()
for epoch in range(num_epochs):
    seq_batch, target_batch = next(iter(train_loader))
    target_batch = target_batch.view(-1, 1)
    seq_batch = seq_batch.to(device)
    target_batch = target_batch.to(device)
    optimizer.zero_grad()
    loss = 0
    pred = model(seq_batch)
    loss = loss_fn(pred.squeeze(), target_batch.squeeze())
    loss.backward()
    optimizer.step()
    loss = loss.item()
    if epoch % 100 == 0:
        print(f'Epoch {epoch} train loss: {loss:.4f}')

    seq_batch, target_batch = next(iter(val_loader))
    target_batch = target_batch.view(-1, 1)
    seq_batch = seq_batch.to(device)
    target_batch = target_batch.to(device)    
    loss = 0
    pred = model(seq_batch)
    loss = loss_fn(pred, target_batch)
    loss = loss.item()
    if epoch % 100 == 0:
        elapsed_time = time.time() - start_time
        print(f'Epoch {epoch} val loss: {loss:.4f} | Elapsed time: {elapsed_time:.2f} seconds')
        start_time = time.time() 

# 保存整个模型
torch.save(model, 'rnn_model.pth')