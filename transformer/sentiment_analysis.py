import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from simple_transformer import SimpleTransformer

# 1. 数据集与分词
def load_local_dataset():
    products = ["手机", "笔记本电脑", "耳机", "智能手表", "平板电脑"]
    aspects = ["质量", "服务", "物流", "包装", "性价比", "电池续航", "屏幕显示"]
    positive_templates = [
        "这款{product}的{aspect}非常出色，完全超出预期",
        "{product}的{aspect}让我很满意，值得推荐",
        "我觉得这款{product}的{aspect}超级棒",
        "{product}的{aspect}比我之前用的好多了",
        "这{product}的{aspect}真的很不错",
        "{product}的{aspect}体验很好，下次还会买",
        "朋友推荐的{product}，{aspect}果然没让我失望",
        "{product}的{aspect}非常好，物超所值",
        "这{product}的{aspect}让我惊喜",
        "{product}的{aspect}表现优秀，点赞"
    ]
    negative_templates = [
        "这款{product}的{aspect}很差，完全不值这个价",
        "{product}的{aspect}让我很失望，不推荐",
        "我觉得这款{product}的{aspect}太糟糕了",
        "{product}的{aspect}比我之前用的差远了",
        "这{product}的{aspect}真的很一般",
        "{product}的{aspect}体验很差，不会再买了",
        "朋友说{product}不错，但{aspect}让我失望",
        "{product}的{aspect}很不好，感觉被坑了",
        "这{product}的{aspect}让我很生气",
        "{product}的{aspect}表现很差，差评"
    ]
    positive_samples = [
        tpl.format(product=product, aspect=aspect)
        for product in products for aspect in aspects for tpl in positive_templates
    ]
    negative_samples = [
        tpl.format(product=product, aspect=aspect)
        for product in products for aspect in aspects for tpl in negative_templates
    ]
    data = {
        "text": positive_samples + negative_samples,
        "label": [1]*len(positive_samples) + [0]*len(negative_samples)
    }
    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    split = int(len(df)*0.8)
    train_df = df.iloc[:split]
    test_df = df.iloc[split:]
    return train_df, test_df

def build_vocab(texts, min_freq=1):
    vocab = {"<PAD>":0, "<UNK>":1}
    freq = {}
    for text in texts:
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
    for ch, f in freq.items():
        if f >= min_freq and ch not in vocab:
            vocab[ch] = len(vocab)
    return vocab

def text_to_ids(text, vocab, max_len):
    ids = [vocab.get(ch, vocab["<UNK>"]) for ch in text]
    if len(ids) < max_len:
        ids += [vocab["<PAD>"]] * (max_len - len(ids))
    else:
        ids = ids[:max_len]
    return ids

class SentimentDataset(Dataset):
    def __init__(self, df, vocab, max_len):
        self.texts = df["text"].tolist()
        self.labels = df["label"].tolist()
        self.vocab = vocab
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        ids = text_to_ids(self.texts[idx], self.vocab, self.max_len)
        return torch.tensor(ids, dtype=torch.long), torch.tensor(self.labels[idx], dtype=torch.long)

# 2. 训练与评估
def train(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)

def evaluate(model, loader, device):
    model.eval()
    preds, labels = [], []
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            pred = torch.argmax(logits, dim=1).cpu().numpy()
            preds.extend(pred)
            labels.extend(y.cpu().numpy())
    acc = accuracy_score(labels, preds)
    f1 = f1_score(labels, preds, average="macro")
    return acc, f1

# 3. 主流程
def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("设备：", device)
    train_df, test_df = load_local_dataset()
    all_texts = train_df["text"].tolist() + test_df["text"].tolist()
    vocab = build_vocab(all_texts)
    max_len = 20

    train_dataset = SentimentDataset(train_df, vocab, max_len)
    test_dataset = SentimentDataset(test_df, vocab, max_len)
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=16)

    # 模型参数
    d_model = 128
    num_heads = 4
    d_ff = 256
    num_layers = 3
    num_classes = 2

    model = SimpleTransformer(
        vocab_size=len(vocab),
        d_model=d_model,
        num_heads=num_heads,
        d_ff=d_ff,
        num_layers=num_layers,
        max_seq_len=max_len,
        num_classes=num_classes
    ).to(device)

    optimizer = optim.AdamW(model.parameters(), lr=5e-4)
    criterion = nn.CrossEntropyLoss()

    # 训练
    for epoch in range(20):
        loss = train(model, train_loader, optimizer, criterion, device)
        acc, f1 = evaluate(model, test_loader, device)
        print(f"Epoch {epoch+1}: Loss={loss:.4f}, Test Acc={acc:.4f}, F1={f1:.4f}")

    # 保存模型和词表
    torch.save(model.state_dict(), "sentiment_transformer.pth")
    import pickle
    with open("sentiment_vocab.pkl", "wb") as f:
        pickle.dump(vocab, f)

    # 测试预测（增加更多案例）
    test_texts = [
        "这款手机的质量非常好，电池续航也很棒",
        "笔记本电脑的屏幕显示效果很差，不推荐购买",
        "耳机的包装很精美，音质也不错",
        "智能手表的性价比很高，值得购买",
        "平板电脑的物流很慢，体验很差",
        "手机的服务态度非常差，让人失望",
        "笔记本电脑的电池续航一般",
        "耳机的质量很差，坏得很快",
        "智能手表的包装很一般，但功能不错",
        "平板电脑的性价比很低，不推荐"
    ]
    correct = 0
    for text in test_texts:
        sentiment, prob = predict(text, model, vocab, max_len, device)
        # 这里简单根据关键词判断期望标签（仅用于统计准确率，实际应用请用人工标注）
        if "好" in text or "棒" in text or "不错" in text or "高" in text or "精美" in text or "值得" in text:
            expected = "正面"
        else:
            expected = "负面"
        is_correct = (sentiment == expected)
        if is_correct:
            correct += 1
        print(f"文本: '{text}'")
        print(f"预测结果: {sentiment} (置信度: {prob:.2%})，期望: {expected}，{'✔' if is_correct else '✘'}")
        print("-" * 50)
    print(f"总测试样本数: {len(test_texts)}，预测正确数: {correct}，总成功率: {correct/len(test_texts):.2%}")

def predict(text, model, vocab, max_len, device):
    model.eval()
    ids = text_to_ids(text, vocab, max_len)
    x = torch.tensor([ids], dtype=torch.long).to(device)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]
        pred = torch.argmax(probs).item()
        confidence = probs[pred].item()
    return ("正面" if pred == 1 else "负面", confidence)

if __name__ == "__main__":
    main()