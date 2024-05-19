import torch

if torch.cuda.is_available():
    # 获取可用的 GPU 数量
    num_gpus = torch.cuda.device_count()
    print(f"Number of available GPUs: {num_gpus}")

    # 遍历每个 GPU，打印其属性信息
    for i in range(num_gpus):
        gpu = torch.cuda.get_device_properties(i)
        cuda_capability = f"{gpu.major}.{gpu.minor}"
        print(f"GPU {i} Properties:")
        print(f"  Name: {gpu.name}")
        print(f"  CUDA Capability: {cuda_capability}")
        print(f"  Total Memory: {gpu.total_memory / (1024 ** 3):.2f} GB")
        print(f"  Multiprocessors: {gpu.multi_processor_count}")
else:
    print("No GPUs available.")
