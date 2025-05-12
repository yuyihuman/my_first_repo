import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, num_heads):
        super().__init__()
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        
        self.query = nn.Linear(d_model, d_model)
        self.key = nn.Linear(d_model, d_model)
        self.value = nn.Linear(d_model, d_model)
        self.out = nn.Linear(d_model, d_model)
        
    def forward(self, query, key, value, mask=None):
        batch_size = query.shape[0]
        
        # 线性变换
        query = self.query(query)
        key = self.key(key)
        value = self.value(value)
        
        # 分割成多头
        query = query.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        key = key.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        value = value.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 注意力计算
        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(self.head_dim)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
            
        attention = torch.softmax(scores, dim=-1)
        out = torch.matmul(attention, value)
        
        # 合并多头
        out = out.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        out = self.out(out)
        
        return out

class FeedForward(nn.Module):
    def __init__(self, d_model, d_ff):
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        return self.linear2(self.relu(self.linear1(x)))

class TransformerBlock(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attention = MultiHeadAttention(d_model, num_heads)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.feed_forward = FeedForward(d_model, d_ff)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, mask=None):
        # 自注意力
        attn_output = self.attention(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_output))
        
        # 前馈网络
        ff_output = self.feed_forward(x)
        x = self.norm2(x + self.dropout(ff_output))
        
        return x

class SimpleTransformer(nn.Module):
    def __init__(self, vocab_size, d_model, num_heads, d_ff, num_layers, max_seq_len, dropout=0.1, num_classes=None):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoding = nn.Parameter(torch.zeros(1, max_seq_len, d_model))
        self.layers = nn.ModuleList([
            TransformerBlock(d_model, num_heads, d_ff, dropout)
            for _ in range(num_layers)
        ])
        self.dropout = nn.Dropout(dropout)
        
        # 添加输出层（根据任务类型调整）
        self.num_classes = num_classes
        if num_classes is not None:
            self.output_layer = nn.Linear(d_model, num_classes)
        
    def forward(self, x, mask=None):
        seq_len = x.size(1)
        
        # 词嵌入和位置编码
        x = self.embedding(x)
        x = x + self.pos_encoding[:, :seq_len, :]
        x = self.dropout(x)
        
        # Transformer层
        for layer in self.layers:
            x = layer(x, mask)
        
        # 如果有输出层，则应用输出层
        if hasattr(self, 'output_layer'):
            # 对于分类任务，通常使用第一个token的表示或平均池化
            # x = x[:, 0, :]  # 使用第一个token的表示（类似BERT）
            # 或者使用平均池化
            x = x.mean(dim=1)  # [batch_size, d_model]
            x = self.output_layer(x)  # [batch_size, num_classes]
            
        return x

# 训练函数示例
def train_transformer(model, train_loader, criterion, optimizer, device, epochs=10):
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
            if batch_idx % 100 == 0:
                print(f'Epoch: {epoch+1}/{epochs}, Batch: {batch_idx}/{len(train_loader)}, Loss: {loss.item():.4f}')
        
        avg_loss = total_loss / len(train_loader)
        print(f'Epoch: {epoch+1}/{epochs}, Average Loss: {avg_loss:.4f}')

# 测试和训练示例
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("当前设备：", device)
    
    # 模型参数
    vocab_size = 10000
    d_model = 512
    num_heads = 8
    d_ff = 2048
    num_layers = 6
    max_seq_len = 512
    num_classes = 10  # 假设是10分类任务
    
    # 创建模型
    model = SimpleTransformer(vocab_size, d_model, num_heads, d_ff, num_layers, max_seq_len, num_classes=num_classes).to(device)
    
    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)
    
    # 这里需要添加数据加载部分
    # train_loader = ...
    
    # 训练模型
    # train_transformer(model, train_loader, criterion, optimizer, device)
    
    # 测试输入
    batch_size = 2
    seq_len = 10
    x = torch.randint(0, vocab_size, (batch_size, seq_len)).to(device)
    
    # 前向传播
    output = model(x)
    print("输出shape:", output.shape)  # 应该是 [batch_size, num_classes]