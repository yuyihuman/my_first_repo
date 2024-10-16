import torch

if torch.cuda.is_available():
    print("GPU is available!")
    print(f"Number of GPUs: {torch.cuda.device_count()}")
else:
    print("GPU is not available.")

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# 使用 device.type 来判断设备类型
if device.type == "cuda":
    print("Using GPU for training!")
else:
    print("Using CPU for training.")
