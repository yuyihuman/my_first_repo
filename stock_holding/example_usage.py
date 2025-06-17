# -*- coding: utf-8 -*-
"""
个股机构持仓可视化工具使用示例

演示如何使用 StockHoldingsVisualizer 类来分析和可视化个股的机构持仓情况
"""

from stock_holdings_visualizer import StockHoldingsVisualizer
import os

def main():
    """
    使用示例主函数
    """
    print("个股机构持仓可视化工具使用示例")
    print("=" * 40)
    
    # 1. 初始化可视化工具
    print("\n1. 初始化可视化工具...")
    try:
        visualizer = StockHoldingsVisualizer()
        print("✓ 初始化成功")
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        return
    
    # 2. 获取可用股票列表
    print("\n2. 获取可用股票列表...")
    available_stocks = visualizer.get_available_stocks()
    print(f"✓ 数据库中共有 {len(available_stocks)} 只股票")
    print(f"前10只股票代码: {', '.join(available_stocks[:10])}")
    
    # 3. 选择一只股票进行分析（使用第一只股票作为示例）
    if available_stocks:
        example_stock = available_stocks[0]
        print(f"\n3. 分析股票 {example_stock}...")
        
        # 3.1 获取股票基本信息
        stock_info = visualizer.get_stock_info(example_stock)
        print(f"✓ 股票信息:")
        print(f"   - 代码: {stock_info.get('stock_code', 'N/A')}")
        print(f"   - 名称: {stock_info.get('stock_name', 'N/A')}")
        print(f"   - 行业: {stock_info.get('industry', 'N/A')}")
        print(f"   - 数据点: {stock_info.get('data_points', 0)}")
        print(f"   - 时间范围: {stock_info.get('date_range', 'N/A')}")
        print(f"   - 机构类型: {', '.join(stock_info.get('institution_types', []))}")
        
        # 3.2 生成摘要报告
        print(f"\n4. 生成摘要报告...")
        report = visualizer.generate_summary_report(example_stock)
        print(report)
        
        # 3.3 绘制可视化图表
        print(f"\n5. 绘制可视化图表...")
        
        # 创建输出目录
        output_dir = "visualization_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置保存路径
        save_path = os.path.join(output_dir, f"holdings_trend_{example_stock}.png")
        
        # 绘制图表
        success = visualizer.plot_holdings_trend(
            stock_code=example_stock,
            save_path=save_path,
            show_plot=True  # 设置为False可以不显示图表，只保存
        )
        
        if success:
            print(f"✓ 图表绘制成功")
            print(f"✓ 图表已保存至: {save_path}")
        else:
            print(f"✗ 图表绘制失败")
    
    # 4. 批量分析示例（分析前3只股票）
    print(f"\n6. 批量分析示例（前3只股票）...")
    
    output_dir = "batch_analysis_output"
    os.makedirs(output_dir, exist_ok=True)
    
    for i, stock_code in enumerate(available_stocks[:3], 1):
        print(f"\n分析第 {i} 只股票: {stock_code}")
        
        # 获取股票信息
        stock_info = visualizer.get_stock_info(stock_code)
        print(f"  股票名称: {stock_info.get('stock_name', 'N/A')}")
        
        # 保存图表
        save_path = os.path.join(output_dir, f"holdings_trend_{stock_code}.png")
        success = visualizer.plot_holdings_trend(
            stock_code=stock_code,
            save_path=save_path,
            show_plot=False  # 批量处理时不显示图表
        )
        
        if success:
            print(f"  ✓ 图表已保存: {save_path}")
        else:
            print(f"  ✗ 图表生成失败")
    
    print(f"\n批量分析完成！图表保存在 {output_dir} 目录中")
    
    # 5. 使用技巧提示
    print(f"\n使用技巧:")
    print(f"1. 命令行使用: python stock_holdings_visualizer.py 000001")
    print(f"2. 交互式使用: python stock_holdings_visualizer.py")
    print(f"3. 仅生成报告: python stock_holdings_visualizer.py 000001 --report-only")
    print(f"4. 保存图表: python stock_holdings_visualizer.py 000001 --save-path output.png")
    print(f"5. 不显示图表: python stock_holdings_visualizer.py 000001 --no-show")

def analyze_specific_stock(stock_code: str):
    """
    分析指定股票的示例函数
    
    Args:
        stock_code: 股票代码
    """
    print(f"分析股票 {stock_code}")
    print("=" * 30)
    
    # 初始化工具
    visualizer = StockHoldingsVisualizer()
    
    # 检查股票是否存在
    available_stocks = visualizer.get_available_stocks()
    stock_code = str(stock_code).zfill(6)
    
    if stock_code not in available_stocks:
        print(f"错误: 股票代码 {stock_code} 不存在")
        print(f"可用股票代码示例: {', '.join(available_stocks[:10])}")
        return
    
    # 生成报告
    report = visualizer.generate_summary_report(stock_code)
    print(report)
    
    # 绘制图表
    visualizer.plot_holdings_trend(stock_code)

if __name__ == "__main__":
    # 运行完整示例
    main()
    
    # 如果想分析特定股票，可以取消下面的注释
    # analyze_specific_stock("000001")  # 分析平安银行