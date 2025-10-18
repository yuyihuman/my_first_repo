# 股票数据加载模块

## 概述

本模块提供了一个专注于数据加载的股票数据加载器，用于从本地CSV文件中加载股票的历史K线数据。支持多种时间粒度的数据加载，包括1分钟、5分钟、30分钟和日线数据。

## 文件结构

```
pearson_found/
├── data_loader.py      # 主要的数据加载模块
├── example_usage.py    # 使用示例
└── README.md          # 本文档
```

## 主要功能

### StockDataLoader 类

主要的数据加载器类，提供以下功能：

1. **多时间粒度支持**
   - 1分钟K线数据
   - 5分钟K线数据
   - 30分钟K线数据
   - 日线K线数据

2. **关键字段提取**
   - datetime: 日期时间
   - open: 开盘价
   - high: 最高价
   - low: 最低价
   - close: 收盘价
   - volume: 成交量

3. **数据处理功能**
   - 自动数据类型转换
   - 日期范围过滤
   - 数据清洗和预处理
   - 自定义字段选择

## 快速开始

### 基本用法

```python
from data_loader import StockDataLoader

# 创建数据加载器
loader = StockDataLoader()

# 加载股票日线数据
stock_code = "000001"  # 平安银行
data = loader.load_stock_data(stock_code, 'daily')

if data is not None:
    print(f"成功加载 {len(data)} 条数据")
    print(data.head())
```

### 加载不同时间粒度数据

```python
# 加载1分钟数据
minute_data = loader.load_stock_data("000001", '1minute')

# 加载5分钟数据
five_min_data = loader.load_stock_data("000001", '5minute')

# 加载30分钟数据
thirty_min_data = loader.load_stock_data("000001", '30minute')

# 加载日线数据
daily_data = loader.load_stock_data("000001", 'daily')
```

### 日期范围过滤

```python
# 加载2024年的数据
data_2024 = loader.load_stock_data(
    "000001", 
    'daily',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 自定义字段选择

```python
# 只加载价格相关字段
price_data = loader.load_stock_data(
    "000001", 
    'daily',
    fields=['datetime', 'open', 'high', 'low', 'close']
)
```

## 主要方法

### load_stock_data()

加载指定股票的历史数据

**参数：**
- `stock_code` (str): 股票代码，如 '000001'
- `time_frame` (str): 时间粒度，可选值：'1minute', '5minute', '30minute', 'daily'
- `start_date` (str, 可选): 开始日期，格式：'YYYY-MM-DD'
- `end_date` (str, 可选): 结束日期，格式：'YYYY-MM-DD'
- `fields` (list, 可选): 需要的字段列表

**返回：**
- `pandas.DataFrame`: 包含股票数据的DataFrame，失败时返回None

### check_stock_data_exists()

检查指定股票和时间粒度的数据文件是否存在

### get_stock_info()

获取股票的基本信息，包括数据文件存在情况

### list_available_stocks()

列出可用的股票代码

## 数据格式

加载的数据包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| datetime | datetime | 日期时间 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | int | 成交量 |

## 数据来源

- **数据源**: xtquant (迅投量化)
- **编码格式**: UTF-8-BOM
- **文件格式**: CSV

## 运行示例

```bash
# 运行基本测试
python data_loader.py

# 运行完整示例
python example_usage.py
```

## 注意事项

1. **数据路径**: 模块会自动查找 `../data/all_stocks_data/` 目录下的数据文件
2. **编码格式**: 数据文件使用UTF-8-BOM编码，模块会自动处理
3. **数据清洗**: 模块会自动删除包含NaN值的无效数据行
4. **内存使用**: 处理大量数据时请注意内存使用情况

## 错误处理

模块包含完善的错误处理机制：
- 文件不存在时会返回None并记录警告
- 数据格式错误时会记录错误信息
- 所有操作都有详细的日志记录

## 扩展功能

可以基于此模块进行扩展：
- 技术指标计算
- 数据可视化
- 策略回测
- 风险分析

## 依赖库

- pandas
- logging (Python标准库)
- os (Python标准库)
- datetime (Python标准库)

## 版本信息

- 版本: 1.0.0
- 创建时间: 2024年
- 作者: Stock Backtest System