# 股票回测程序

一个完整的股票回测系统，支持单笔和批量交易的收益率计算、策略回测和报告生成。

## 功能特性

### 核心模块

1. **选股模块** (`modules/stock_selector.py`)
   - 提供股票选择策略接口
   - 支持自定义选股策略注册
   - 预留多种选股算法接口

2. **买入策略模块** (`modules/buy_strategy.py`)
   - 定义多种买入策略
   - 支持策略注册和动态调用
   - 预留技术指标和基本面分析接口

3. **卖出策略模块** (`modules/sell_strategy.py`)
   - 定义多种卖出策略
   - 支持止损、止盈、持有期等策略
   - 灵活的策略组合机制

4. **收益率计算模块** (`modules/return_calculator.py`) ⭐
   - **已完整实现**
   - 使用 `xtdata` API 获取真实股票数据
   - 支持单笔和批量交易收益率计算
   - 自动处理除权除息
   - 提供年化收益率计算
   - 智能日期匹配（自动找到最近交易日）
   - 模拟数据支持（当 xtdata 不可用时）

5. **报告生成模块** (`modules/report_generator.py`)
   - 多种报告格式：简单、详细、摘要
   - 支持 JSON、HTML 输出格式
   - 自动统计分析和风险指标
   - 报告保存功能

### 辅助工具

- **日志系统** (`utils/logger.py`)
  - 统一的日志管理
  - 按日期和模块分类存储
  - 详细的调试信息记录

- **回测引擎** (`main.py`)
  - 整合所有模块的主引擎
  - 提供完整的回测流程
  - 示例代码和使用演示

## 安装和使用

### 环境要求

- Python 3.7+
- pandas >= 1.5.0
- numpy >= 1.21.0

### 安装依赖

```bash
pip install -r requirements.txt
```

### 可选依赖

如果需要获取真实股票数据，请安装 xtquant：

```bash
# 注意：xtquant 需要从官方渠道获取
# pip install xtquant
```

如果没有安装 xtquant，程序会自动使用模拟数据进行演示。

## 快速开始

### 运行示例

```bash
python main.py
```

这将运行内置的示例，包括：
- 单笔交易回测
- 批量交易回测
- 报告生成和保存

### 基本用法

#### 1. 单笔交易回测

```python
from main import BacktestEngine

# 创建回测引擎
engine = BacktestEngine()

# 计算单笔交易收益率
result = engine.run_single_trade_backtest(
    stock_code='000001.SZ',  # 平安银行
    buy_date='20240101',     # 买入日期
    sell_date='20240201'     # 卖出日期
)

if result['success']:
    print(f"收益率: {result['return_percentage']:.2f}%")
    print(f"年化收益率: {result['annual_return_percentage']:.2f}%")
else:
    print(f"计算失败: {result['error']}")
```

#### 2. 批量交易回测

```python
# 定义交易列表
trades = [
    {
        'stock_code': '000001.SZ',
        'buy_date': '20240101',
        'sell_date': '20240201'
    },
    {
        'stock_code': '000002.SZ',
        'buy_date': '20240115',
        'sell_date': '20240215'
    }
]

# 运行批量回测
result = engine.run_batch_backtest(trades)

if result['success']:
    summary = result['summary']
    print(f"总交易次数: {summary['total_trades']}")
    print(f"平均收益率: {summary['average_return_percentage']:.2f}%")
```

#### 3. 生成报告

```python
# 生成详细报告并保存
report_result = engine.generate_backtest_report(
    backtest_result=result,
    report_type='detailed',  # 'simple', 'detailed', 'summary'
    output_format='json',    # 'dict', 'json', 'html'
    save_to_file=True
)

if report_result['success']:
    print("报告生成成功")
    if 'saved_file' in report_result:
        print(f"报告已保存到: {report_result['saved_file']}")
```

## 项目结构

```
self_back/
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明
├── api.md                 # xtdata API 文档
├── modules/               # 核心模块
│   ├── __init__.py
│   ├── stock_selector.py      # 选股模块
│   ├── buy_strategy.py        # 买入策略模块
│   ├── sell_strategy.py       # 卖出策略模块
│   ├── return_calculator.py   # 收益率计算模块 ⭐
│   └── report_generator.py    # 报告生成模块
├── utils/                 # 工具模块
│   ├── __init__.py
│   └── logger.py             # 日志工具
└── logs/                  # 日志文件目录
    ├── YYYYMMDD/             # 按日期分类的日志
    └── backtest_report_*.json # 生成的报告文件
```

## 收益率计算模块详解

### 核心功能

1. **数据获取**
   - 使用 `xtdata.get_market_data()` 获取1日周期股票数据
   - 支持除权除息处理
   - 自动下载历史数据
   - 模拟数据备用方案

2. **智能日期处理**
   - 自动查找最近的交易日
   - 买入日期：向后查找第一个交易日
   - 卖出日期：向前查找最后一个交易日

3. **收益率计算**
   - 简单收益率：`(卖出价 - 买入价) / 买入价`
   - 年化收益率：`收益率 × (365 / 持有天数)`
   - 持有期计算

4. **批量处理**
   - 支持多笔交易同时计算
   - 统计汇总信息
   - 错误处理和日志记录

### API 参考

#### `calculate_return(stock_code, buy_date, sell_date, dividend_type='none')`

计算单笔交易收益率。

**参数：**
- `stock_code` (str): 股票代码，格式如 '000001.SZ'
- `buy_date` (str): 买入日期，格式为 'YYYYMMDD'
- `sell_date` (str): 卖出日期，格式为 'YYYYMMDD'
- `dividend_type` (str): 除权方式，默认 'none'

**返回：**
```python
{
    'success': True,
    'stock_code': '000001.SZ',
    'buy_date': '20240101',
    'sell_date': '20240201',
    'actual_buy_date': '20240102',  # 实际交易日
    'actual_sell_date': '20240201',
    'buy_price': 10.50,
    'sell_price': 11.20,
    'return_rate': 0.0667,          # 收益率
    'return_percentage': 6.67,      # 收益率百分比
    'annual_return': 0.8333,        # 年化收益率
    'annual_return_percentage': 83.33,
    'hold_days': 30,                # 持有天数
    'dividend_type': 'none'
}
```

#### `calculate_batch_returns(trades)`

批量计算多笔交易收益率。

**参数：**
- `trades` (list): 交易列表，每个元素包含 stock_code, buy_date, sell_date

**返回：**
```python
{
    'success': True,
    'results': [...],  # 每笔交易的详细结果
    'summary': {
        'total_trades': 3,
        'successful_trades': 2,
        'failed_trades': 1,
        'total_return': 0.15,
        'average_return': 0.075,
        'average_return_percentage': 7.5
    }
}
```

## 日志系统

所有操作都会记录详细的日志信息：

- **位置**: `logs/YYYYMMDD/` 目录
- **文件**: 按模块分类（如 `return_calculator.log`）
- **级别**: INFO（关键操作）、DEBUG（详细信息）、ERROR（错误信息）

## 扩展开发

### 添加新的买入策略

```python
from modules.buy_strategy import BuyStrategy

def my_custom_strategy(stock_data, **kwargs):
    # 实现自定义买入逻辑
    return {'should_buy': True, 'reason': '自定义条件满足'}

# 注册策略
buy_strategy = BuyStrategy()
buy_strategy.register_strategy('my_strategy', my_custom_strategy)
```

### 添加新的报告类型

```python
from modules.report_generator import ReportGenerator

def my_custom_report(data):
    # 实现自定义报告逻辑
    return {'title': '自定义报告', 'content': '...'}

# 注册报告类型
report_generator = ReportGenerator()
report_generator.register_report_type('my_report', my_custom_report)
```

## 注意事项

1. **数据源**：程序优先使用 xtdata 获取真实数据，如果不可用会使用模拟数据
2. **日期格式**：所有日期必须使用 'YYYYMMDD' 格式
3. **股票代码**：必须包含市场后缀，如 '.SZ'（深圳）或 '.SH'（上海）
4. **交易日**：程序会自动处理非交易日，查找最近的交易日
5. **日志文件**：建议定期清理 logs 目录中的旧日志文件

## 许可证

本项目仅供学习和研究使用。

## 更新日志

### v1.0.0 (当前版本)
- ✅ 完整实现收益率计算模块
- ✅ 集成 xtdata API 数据获取
- ✅ 支持单笔和批量交易回测
- ✅ 完整的日志系统
- ✅ 多种报告格式
- ✅ 模拟数据备用方案
- 🔄 其他模块接口预留（待实现）

### 计划功能
- 📋 完善选股策略实现
- 📋 丰富买入/卖出策略
- 📋 添加技术指标计算
- 📋 风险指标计算（夏普比率、最大回撤等）
- 📋 可视化图表生成
- 📋 Web 界面支持