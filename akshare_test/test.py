import torch

# 创建一个 5x4x3 的三维张量，初始化为零
tensor = torch.zeros(5, 4, 3)

# 输出张量的形状
print("张量的形状:", tensor.shape)

new_tensor = tensor[-1, :, :]

print("张量的形状:", new_tensor.shape)