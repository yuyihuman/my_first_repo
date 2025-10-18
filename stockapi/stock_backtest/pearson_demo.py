#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
皮尔逊相关系数计算Demo - 精简版
包含两组数据：高相关性和低相关性，计算相关系数并可视化展示
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def calculate_pearson_correlation(x, y):
    """
    计算皮尔逊相关系数
    
    Args:
        x, y: 输入数据序列
        
    Returns:
        correlation: 相关系数
        p_value: p值
    """
    correlation, p_value = pearsonr(x, y)
    return correlation, p_value

def generate_data():
    """
    生成两组测试数据：高相关性和低相关性
    
    Returns:
        high_corr_data: 高相关性数据 (x1, y1)
        low_corr_data: 低相关性数据 (x2, y2)
    """
    np.random.seed(42)  # 固定随机种子，确保结果可重现
    n_points = 100
    
    # 生成高相关性数据 (相关系数约0.9)
    x1 = np.random.randn(n_points)
    noise1 = np.random.randn(n_points) * 0.3  # 小噪声
    y1 = 2 * x1 + 1 + noise1  # 强线性关系
    
    # 生成低相关性数据 (相关系数约0.2)
    x2 = np.random.randn(n_points)
    noise2 = np.random.randn(n_points) * 2  # 大噪声
    y2 = 0.5 * x2 + noise2  # 弱线性关系
    
    return (x1, y1), (x2, y2)

def plot_correlation_analysis(high_data, low_data, high_corr, low_corr):
    """
    绘制相关性分析图
    
    Args:
        high_data: 高相关性数据 (x, y)
        low_data: 低相关性数据 (x, y)
        high_corr: 高相关性系数
        low_corr: 低相关性系数
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 绘制高相关性数据的散点图
    x1, y1 = high_data
    axes[0, 0].scatter(x1, y1, alpha=0.7, color='blue', s=40)
    axes[0, 0].set_title(f'高相关性数据散点图\n皮尔逊相关系数: {high_corr:.3f}', fontsize=12)
    axes[0, 0].set_xlabel('X1', fontweight='bold')
    axes[0, 0].set_ylabel('Y1', fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 添加拟合线
    z1 = np.polyfit(x1, y1, 1)
    p1 = np.poly1d(z1)
    x_line1 = np.linspace(x1.min(), x1.max(), 100)
    axes[0, 0].plot(x_line1, p1(x_line1), "red", alpha=0.8, linewidth=2, label='拟合线')
    axes[0, 0].legend()
    
    # 绘制高相关性数据的序列图
    indices1 = np.arange(len(x1))
    axes[0, 1].plot(indices1, x1, 'o-', color='blue', alpha=0.7, label='X1序列', markersize=4)
    axes[0, 1].plot(indices1, y1, 's-', color='red', alpha=0.7, label='Y1序列', markersize=4)
    axes[0, 1].set_title('高相关性数据序列对比', fontsize=12)
    axes[0, 1].set_xlabel('数据点索引')
    axes[0, 1].set_ylabel('数值')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # 绘制低相关性数据的散点图
    x2, y2 = low_data
    axes[1, 0].scatter(x2, y2, alpha=0.7, color='green', s=40)
    axes[1, 0].set_title(f'低相关性数据散点图\n皮尔逊相关系数: {low_corr:.3f}', fontsize=12)
    axes[1, 0].set_xlabel('X2', fontweight='bold')
    axes[1, 0].set_ylabel('Y2', fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 添加拟合线
    z2 = np.polyfit(x2, y2, 1)
    p2 = np.poly1d(z2)
    x_line2 = np.linspace(x2.min(), x2.max(), 100)
    axes[1, 0].plot(x_line2, p2(x_line2), "red", alpha=0.8, linewidth=2, label='拟合线')
    axes[1, 0].legend()
    
    # 绘制低相关性数据的序列图
    indices2 = np.arange(len(x2))
    axes[1, 1].plot(indices2, x2, 'o-', color='blue', alpha=0.7, label='X2序列', markersize=4)
    axes[1, 1].plot(indices2, y2, 's-', color='orange', alpha=0.7, label='Y2序列', markersize=4)
    axes[1, 1].set_title('低相关性数据序列对比', fontsize=12)
    axes[1, 1].set_xlabel('数据点索引')
    axes[1, 1].set_ylabel('数值')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def main():
    """
    主函数：执行皮尔逊相关系数计算和可视化
    """
    print("=" * 60)
    print("皮尔逊相关系数计算Demo - 精简版")
    print("=" * 60)
    
    # 生成测试数据
    print("1. 生成测试数据...")
    high_data, low_data = generate_data()
    x1, y1 = high_data
    x2, y2 = low_data
    
    print(f"   高相关性数据: {len(x1)} 个数据点")
    print(f"   低相关性数据: {len(x2)} 个数据点")
    
    # 计算皮尔逊相关系数
    print("\n2. 计算皮尔逊相关系数...")
    high_corr, high_p = calculate_pearson_correlation(x1, y1)
    low_corr, low_p = calculate_pearson_correlation(x2, y2)
    
    # 输出结果
    print(f"\n3. 计算结果:")
    print(f"   高相关性数据:")
    print(f"     相关系数: {high_corr:.6f}")
    print(f"     p值: {high_p:.6f}")
    print(f"     显著性: {'显著' if high_p < 0.05 else '不显著'}")
    
    print(f"\n   低相关性数据:")
    print(f"     相关系数: {low_corr:.6f}")
    print(f"     p值: {low_p:.6f}")
    print(f"     显著性: {'显著' if low_p < 0.05 else '不显著'}")
    
    # 相关性强度解释
    def interpret_correlation(corr):
        abs_corr = abs(corr)
        if abs_corr >= 0.8:
            return "强相关"
        elif abs_corr >= 0.5:
            return "中等相关"
        elif abs_corr >= 0.3:
            return "弱相关"
        else:
            return "几乎无相关"
    
    print(f"\n4. 相关性强度解释:")
    print(f"   高相关性数据: {interpret_correlation(high_corr)}")
    print(f"   低相关性数据: {interpret_correlation(low_corr)}")
    
    # 绘制可视化图表
    print(f"\n5. 生成可视化图表...")
    plot_correlation_analysis(high_data, low_data, high_corr, low_corr)
    
    print("\n" + "=" * 60)
    print("Demo执行完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()