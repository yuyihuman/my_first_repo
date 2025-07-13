# 个股机构持仓占流通股比例可视化工具

## 概述

本工具基于 `merged_holdings_data.csv` 数据文件，专门提供个股机构持仓占流通股比例的可视化分析功能。支持按股票代码查询，显示不同机构类型的持仓占流通股比例变化趋势。

## 功能特性

### 📊 可视化图表
- **占流通股比例趋势图**: 专门展示各机构类型持仓占流通股的比例变化

### 📈 数据分析
- 股票基本信息查询
- 机构持仓占流通股比例摘要报告
- 持仓占流通股比例变化趋势分析
- 支持批量分析处理

### 🛠️ 使用方式
- 命令行接口
- 交互式界面
- Python API调用

## 安装依赖

```bash
pip install pandas matplotlib seaborn numpy
```

## 使用方法

### 1. 命令行使用

#### 基本用法
```bash
# 分析指定股票（以平安银行为例）
python stock_holdings_visualizer.py 000001
```

#### 高级选项
```bash
# 仅生成报告，不显示图表
python stock_holdings_visualizer.py 000001 --report-only

# 保存图表到指定路径
python stock_holdings_visualizer.py 000001 --save-path "output/平安银行_持仓分析.png"

# 不显示图表，仅保存
python stock_holdings_visualizer.py 000001 --save-path "output.png" --no-show

# 使用自定义数据文件
python stock_holdings_visualizer.py 000001 --data-file "path/to/your/data.csv"
```

### 2. 交互式使用

```bash
# 启动交互式界面
python stock_holdings_visualizer.py
```

交互式界面会提示您输入股票代码，并提供可用股票列表供参考。

### 3. Python API 使用

```python
from stock_holdings_visualizer import StockHoldingsVisualizer

# 初始化可视化工具
visualizer = StockHoldingsVisualizer()

# 获取可用股票列表
available_stocks = visualizer.get_available_stocks()
print(f"可用股票数量: {len(available_stocks)}")

# 获取股票信息
stock_info = visualizer.get_stock_info("000001")
print(stock_info)

# 生成摘要报告
report = visualizer.generate_summary_report("000001")
print(report)

# 绘制可视化图表
visualizer.plot_holdings_trend(
    stock_code="000001",
    save_path="平安银行_持仓分析.png",
    show_plot=True
)
```

### 4. 批量分析示例

```python
# 参考 example_usage.py 文件
python example_usage.py
```

## 输出说明

### 图表输出

工具会生成一个专注于占流通股比例的分析图表：

**占流通股比例趋势图**
- X轴：报告期（时间）
- Y轴：占流通股比例（%）
- 不同颜色线条代表不同机构类型
- 清晰展示各机构类型持仓占流通股比例的时间变化趋势

### 摘要报告内容

生成的文字报告包含：

- **股票基本信息**: 股票代码、名称、行业分类
- **数据概况**: 数据时间范围、数据点数量
- **最新占流通股比例情况**: 各机构类型的最新占流通股比例和机构数量
- **占流通股比例趋势分析**: 持仓占流通股比例的变化趋势、最高最低值及变化幅度
- **机构类型分析**: 各机构类型的平均占流通股比例水平和活跃度

## 数据格式要求

工具期望的CSV数据格式：

| 列名 | 说明 |
|------|------|
| 股票代码 | 6位股票代码 |
| 股票简称 | 股票名称 |
| institution_type | 机构类型（如：基金持仓、QFII持仓等）|
| report_date | 报告期（YYYYMMDD格式）|
| 占总股本比例 | 持仓占总股本的比例 |
| 占流通股比例 | 持仓占流通股的比例 |
| 持股变动比例 | 持股变动比例 |
| 所属行业 | 股票所属行业（可选）|

## 示例输出

### 命令行报告示例
```
==================================================
股票持仓分析报告
==================================================
股票代码: 000001
股票名称: 平安银行
所属行业: 银行
数据时间: 2020-03-31 至 2023-12-31
数据点数: 24

机构类型: QFII持仓, 基金持仓, 保险持仓

最新持仓情况 (2023-12-31):
  基金持仓: 占总股本 2.45%, 占流通股 2.67%
  QFII持仓: 占总股本 1.23%, 占流通股 1.34%
  保险持仓: 占总股本 0.89%, 占流通股 0.97%

持仓变化趋势:
  基金持仓: 上升 (+0.34个百分点)
  QFII持仓: 下降 (-0.12个百分点)
  保险持仓: 持平 (+0.02个百分点)
```

## 常见问题

### Q: 如何查看有哪些股票可以分析？
A: 运行交互式模式 `python stock_holdings_visualizer.py`，会显示可用股票列表。

### Q: 图表中文显示乱码怎么办？
A: 确保系统安装了中文字体（如SimHei、Microsoft YaHei），工具会自动选择合适的字体。

### Q: 数据文件路径错误怎么办？
A: 使用 `--data-file` 参数指定正确的数据文件路径，或将数据文件放在默认位置。

### Q: 如何批量生成多只股票的图表？
A: 参考 `example_usage.py` 中的批量分析示例代码。

### Q: 可以自定义图表样式吗？
A: 可以修改 `stock_holdings_visualizer.py` 中的绘图参数，如颜色、字体大小、图表尺寸等。

## 文件说明

- `stock_holdings_visualizer.py`: 主要的可视化工具类
- `example_usage.py`: 使用示例和批量分析代码
- `VISUALIZATION_README.md`: 本说明文档

## 扩展功能建议

1. **添加更多图表类型**
   - 持仓集中度分析
   - 机构持仓相关性分析
   - 行业对比分析

2. **增强交互功能**
   - Web界面
   - 实时数据更新
   - 自定义时间范围筛选

3. **导出功能**
   - 导出Excel报告
   - 生成PDF分析报告
   - 数据导出功能

## 技术支持

如有问题或建议，请查看项目文档或提交Issue。