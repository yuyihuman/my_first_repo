import torch
import time
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import subprocess

# 创建日志目录
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'benchmark_logs')
os.makedirs(log_dir, exist_ok=True)

# 创建日志文件
log_file = os.path.join(log_dir, f'pcie_benchmark_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

def log_message(message):
    """记录日志消息到文件和控制台"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def get_gpu_info():
    """获取GPU信息"""
    if not torch.cuda.is_available():
        return "没有可用的GPU"
    
    info = []
    device_count = torch.cuda.device_count()
    info.append(f"检测到 {device_count} 个GPU设备:")
    
    for i in range(device_count):
        gpu_properties = torch.cuda.get_device_properties(i)
        info.append(f"GPU {i}: {gpu_properties.name}")
        info.append(f"  - 总内存: {gpu_properties.total_memory / 1024 / 1024 / 1024:.2f} GB")
        info.append(f"  - 多处理器数量: {gpu_properties.multi_processor_count}")
        info.append(f"  - CUDA能力: {gpu_properties.major}.{gpu_properties.minor}")
        info.append(f"  - 当前内存使用: {torch.cuda.memory_allocated(i) / 1024 / 1024:.2f} MB")
        info.append(f"  - 缓存内存: {torch.cuda.memory_reserved(i) / 1024 / 1024:.2f} MB")
    
    return "\n".join(info)

def get_nvidia_smi_output():
    """获取nvidia-smi输出"""
    try:
        result = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, text=True)
        return result.stdout
    except Exception as e:
        return f"无法获取nvidia-smi输出: {e}"

def check_gpu_memory(device_id):
    """检查GPU内存状态"""
    memory_info = {}
    memory_info['allocated'] = torch.cuda.memory_allocated(device_id) / 1024 / 1024  # MB
    memory_info['reserved'] = torch.cuda.memory_reserved(device_id) / 1024 / 1024  # MB
    memory_info['max_allocated'] = torch.cuda.max_memory_allocated(device_id) / 1024 / 1024  # MB
    
    log_message(f"GPU {device_id} 内存状态:")
    log_message(f"  - 已分配: {memory_info['allocated']:.2f} MB")
    log_message(f"  - 已缓存: {memory_info['reserved']:.2f} MB")
    log_message(f"  - 最大分配: {memory_info['max_allocated']:.2f} MB")
    
    return memory_info

def pcie_bandwidth_test(device, size=100000000, iterations=10):
    """PCIe带宽测试"""
    device_id = int(device.split(':')[1])
    log_message(f"在 {device} 上进行PCIe带宽测试...")
    
    # 检查测试前GPU状态
    log_message(f"测试前GPU {device_id} 状态:")
    check_gpu_memory(device_id)
    
    # 在CPU上创建数据
    log_message(f"在CPU上创建大小为 {size} 的向量...")
    creation_start = time.time()
    a_cpu = torch.randn(size)
    creation_time = time.time() - creation_start
    log_message(f"CPU向量创建耗时: {creation_time:.4f} 秒")
    
    # 预热
    log_message("开始预热...")
    for i in range(3):
        warmup_start = time.time()
        a_gpu = a_cpu.to(device)
        torch.cuda.synchronize(device)
        del a_gpu
        torch.cuda.empty_cache()
        warmup_time = time.time() - warmup_start
        log_message(f"预热迭代 {i+1}: {warmup_time:.4f} 秒")
    
    # 计时 - CPU到GPU传输
    log_message("开始CPU到GPU传输测试...")
    torch.cuda.synchronize(device)
    
    h2d_transfer_times = []
    
    for i in range(iterations):
        iter_start = time.time()
        a_gpu = a_cpu.to(device)
        torch.cuda.synchronize(device)
        iter_time = time.time() - iter_start
        h2d_transfer_times.append(iter_time)
        log_message(f"CPU到GPU迭代 {i+1}: {iter_time:.4f} 秒")
        
        # 不要在每次迭代后删除，只在最后一次迭代后删除
        if i == iterations - 1:
            del a_gpu
            torch.cuda.empty_cache()
    
    # 计算平均传输时间 - CPU到GPU
    avg_h2d_time = sum(h2d_transfer_times) / len(h2d_transfer_times)
    log_message(f"平均CPU到GPU传输时间: {avg_h2d_time:.4f} 秒")
    
    # 计算带宽 - CPU到GPU (每个元素4字节，假设是float32)
    bytes_transferred = size * 4
    h2d_bandwidth = bytes_transferred / (avg_h2d_time * 1e9)  # GB/s
    log_message(f"计算CPU到GPU PCIe带宽: {h2d_bandwidth:.2f} GB/s")
    
    # 计时 - GPU到CPU传输
    log_message("\n开始GPU到CPU传输测试...")
    
    # 先创建GPU上的数据
    a_gpu = torch.randn(size, device=device)
    torch.cuda.synchronize(device)
    
    d2h_transfer_times = []
    
    for i in range(iterations):
        iter_start = time.time()
        a_cpu = a_gpu.cpu()
        torch.cuda.synchronize(device)
        iter_time = time.time() - iter_start
        d2h_transfer_times.append(iter_time)
        log_message(f"GPU到CPU迭代 {i+1}: {iter_time:.4f} 秒")
    
    # 清理内存
    del a_gpu, a_cpu
    torch.cuda.empty_cache()
    
    # 计算平均传输时间 - GPU到CPU
    avg_d2h_time = sum(d2h_transfer_times) / len(d2h_transfer_times)
    log_message(f"平均GPU到CPU传输时间: {avg_d2h_time:.4f} 秒")
    
    # 计算带宽 - GPU到CPU
    d2h_bandwidth = bytes_transferred / (avg_d2h_time * 1e9)  # GB/s
    log_message(f"计算GPU到CPU PCIe带宽: {d2h_bandwidth:.2f} GB/s")
    
    # 检查测试后GPU状态
    log_message(f"测试后GPU {device_id} 状态:")
    check_gpu_memory(device_id)
    
    return {
        'h2d_time': avg_h2d_time,
        'h2d_bandwidth': h2d_bandwidth,
        'd2h_time': avg_d2h_time,
        'd2h_bandwidth': d2h_bandwidth
    }

# 在import部分添加中文字体支持
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib
# 设置中文字体
try:
    # 尝试设置微软雅黑字体（Windows系统常见字体）
    font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑字体路径
    font_prop = FontProperties(fname=font_path)
    matplotlib.rcParams['font.family'] = ['sans-serif']
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei'] + matplotlib.rcParams['font.sans-serif']
    # 解决负号显示问题
    matplotlib.rcParams['axes.unicode_minus'] = False
    print("成功设置中文字体")
except:
    print("设置中文字体失败，将使用默认字体")

def run_pcie_benchmark():
    """运行PCIe基准测试"""
    # 记录开始时间
    benchmark_start = datetime.now()
    log_message(f"PCIe基准测试开始于: {benchmark_start.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 记录GPU信息
    log_message("\n=== GPU 信息 ===")
    log_message(get_gpu_info())
    
    # 记录nvidia-smi输出
    log_message("\n=== NVIDIA-SMI 输出 ===")
    log_message(get_nvidia_smi_output())
    
    log_message("\n" + "="*50 + "\n")
    
    if not torch.cuda.is_available():
        log_message("没有可用的GPU，无法进行测试")
        return
    
    device_count = torch.cuda.device_count()
    results = []
    
    # 测试不同大小的数据传输
    sizes = [10000000, 50000000, 100000000, 200000000, 500000000]
    
    for i in range(device_count):
        device = f"cuda:{i}"
        gpu_name = torch.cuda.get_device_properties(i).name
        log_message(f"\n=== 开始测试 GPU {i}: {gpu_name} ===")
        
        size_results = []
        
        for size in sizes:
            log_message(f"\n--- 测试数据大小: {size} 元素 ({size*4/1024/1024:.2f} MB) ---")
            result = pcie_bandwidth_test(device, size=size)
            
            size_results.append({
                'size': size,
                'size_mb': size*4/1024/1024,
                'h2d_bandwidth': result['h2d_bandwidth'],
                'd2h_bandwidth': result['d2h_bandwidth']
            })
            
            # 添加到总结果
            results.append([
                f"GPU {i}: {gpu_name}",
                f"{size*4/1024/1024:.2f} MB",
                f"{result['h2d_time']:.4f}秒",
                f"{result['h2d_bandwidth']:.2f} GB/s",
                f"{result['d2h_time']:.4f}秒",
                f"{result['d2h_bandwidth']:.2f} GB/s"
            ])
        
        # 绘制该GPU的带宽图表
        plt.figure(figsize=(12, 6))
        
        # 提取数据
        sizes_mb = [r['size_mb'] for r in size_results]
        h2d_bw = [r['h2d_bandwidth'] for r in size_results]
        d2h_bw = [r['d2h_bandwidth'] for r in size_results]
        
        # 绘制H2D和D2H带宽
        plt.plot(sizes_mb, h2d_bw, 'o-', label='CPU到GPU带宽')
        plt.plot(sizes_mb, d2h_bw, 's-', label='GPU到CPU带宽')
        
        plt.title(f'GPU {i}: {gpu_name} PCIe带宽', fontproperties=font_prop)
        plt.xlabel('数据大小 (MB)', fontproperties=font_prop)
        plt.ylabel('带宽 (GB/s)', fontproperties=font_prop)
        plt.grid(True)
        plt.legend(prop=font_prop)
        
        # 保存图表
        gpu_image = os.path.join(log_dir, f'pcie_benchmark_gpu{i}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.savefig(gpu_image)
        log_message(f"GPU {i} PCIe带宽图已保存为: {gpu_image}")
        
        plt.close()
    
    # 打印表格结果
    from tabulate import tabulate
    headers = ["设备", "数据大小", "H2D时间", "H2D带宽", "D2H时间", "D2H带宽"]
    table = tabulate(results, headers=headers, tablefmt="grid")
    log_message("\n" + table)
    
    # 绘制所有GPU的对比图
    if device_count > 1:
        plt.figure(figsize=(15, 10))
        
        # 提取每个GPU的最大带宽
        gpu_names = []
        h2d_max_bw = []
        d2h_max_bw = []
        
        for i in range(device_count):
            gpu_name = torch.cuda.get_device_properties(i).name
            gpu_names.append(f"GPU {i}")
            
            # 找出该GPU的最大带宽
            gpu_results = [r for r in results if r[0].startswith(f"GPU {i}")]
            max_h2d = max([float(r[3].split()[0]) for r in gpu_results])
            max_d2h = max([float(r[5].split()[0]) for r in gpu_results])
            
            h2d_max_bw.append(max_h2d)
            d2h_max_bw.append(max_d2h)
        
        # 绘制条形图
        x = np.arange(device_count)
        width = 0.35
        
        plt.bar(x - width/2, h2d_max_bw, width, label='CPU到GPU最大带宽')
        plt.bar(x + width/2, d2h_max_bw, width, label='GPU到CPU最大带宽')
        
        plt.title('各GPU PCIe最大带宽对比', fontproperties=font_prop)
        plt.xlabel('GPU', fontproperties=font_prop)
        plt.ylabel('带宽 (GB/s)', fontproperties=font_prop)
        plt.xticks(x, gpu_names)
        plt.legend(prop=font_prop)
        plt.grid(True, axis='y')
        
        # 保存图表
        compare_image = os.path.join(log_dir, f'pcie_benchmark_compare_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.savefig(compare_image)
        log_message(f"GPU PCIe带宽对比图已保存为: {compare_image}")
        
        plt.show()
    
    # 记录结束时间
    benchmark_end = datetime.now()
    benchmark_duration = (benchmark_end - benchmark_start).total_seconds()
    log_message(f"\nPCIe基准测试完成！")
    log_message(f"开始时间: {benchmark_start.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"结束时间: {benchmark_end.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"总耗时: {benchmark_duration:.2f} 秒")
    log_message(f"日志文件: {log_file}")

if __name__ == "__main__":
    run_pcie_benchmark()