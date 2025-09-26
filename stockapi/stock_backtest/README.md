# 股票回测系统

一个模块化的股票回测框架，将原有的 `demo.py` 重构为更清晰的模块结构。

## 模块结构

```
stock_backtest/
├── __init__.py              # 包初始化文件
├── main.py                  # 主程序入口
├── data_loader.py           # 数据加载和预处理模块
├── strategy_engine.py       # 策略执行模块
├── stock_selector.py        # 股票选择模块
├── result_analyzer.py       # 结果分析和输出模块
└── README.md               # 使用说明
```

## 模块功能

### 1. 数据准备模块 (`data_loader.py`)
- **StockDataLoader**: 负责从CSV文件加载股票数据
- **DataPreprocessor**: 数据清理和技术指标计算
- 使用现有数据源，不重新计算技术指标

### 2. 策略执行模块 (`strategy_engine.py`)
- **StrategyEngine**: 核心策略执行引擎
- **ModelBasedStrategy**: 为未来模型集成预留的接口
- 支持自定义策略条件
- 独立模块设计，便于模型接入

### 3. 选股模块 (`stock_selector.py`)
- **StockSelector**: 基于策略筛选股票
- 支持单股票、批量和全量测试
- 多进程处理支持

### 4. 结果整理输出模块 (`result_analyzer.py`)
- **ResultAnalyzer**: 结果分析和统计
- **ResultExporter**: 多格式结果导出
- **ResultFormatter**: 结果格式化显示

## 使用方法

### 1. 命令行使用

```bash
# 测试单个股票
python main.py --data_folder "path/to/data" --mode single --stock_code "000001" --verbose

# 详细测试单个股票的特定日期
python main.py --data_folder "path/to/data" --mode single --stock_code "000001" --target_date "2024-01-15"

# 批量测试多个股票
python main.py --data_folder "path/to/data" --mode batch --stock_codes "000001" "000002" "000003" --num_processes 4

# 全量测试所有股票
python main.py --data_folder "path/to/data" --mode full --num_processes 20

# 限制测试股票数量
python main.py --data_folder "path/to/data" --mode full --limit 100 --num_processes 10
```

### 2. 编程接口使用

```python
from stock_backtest import BacktestingSystem

# 初始化回测系统
system = BacktestingSystem(
    data_folder="c:/path/to/stock/data",
    output_folder="c:/path/to/output"
)

# 测试单个股票
result = system.test_single_stock("000001", verbose=True)

# 详细测试特定日期
result = system.test_single_stock_verbose("000001", "2024-01-15")

# 批量测试
stock_codes = ["000001", "000002", "000003"]
result = system.test_batch_stocks(stock_codes, num_processes=4)

# 全量测试
result = system.test_all_stocks(num_processes=20, limit=1000)

# 查看策略描述
print(system.get_strategy_description())
```

### 3. 自定义策略

```python
from stock_backtest import StrategyEngine, ModelBasedStrategy
from stock_backtest.strategy_engine import StrategyCondition

# 创建自定义策略条件
class CustomCondition(StrategyCondition):
    def check(self, df, current_idx, stock_code):
        # 实现自定义逻辑
        return True, "自定义条件描述"

# 创建自定义策略引擎
custom_strategy = StrategyEngine()
custom_strategy.add_condition(CustomCondition())

# 使用自定义策略
system.set_custom_strategy(custom_strategy)
```

### 4. 模型集成示例

```python
from stock_backtest import ModelBasedStrategy

class MyModelStrategy(ModelBasedStrategy):
    def __init__(self, model):
        super().__init__()
        self.model = model
    
    def predict_signal(self, df, current_idx, stock_code):
        # 使用模型进行预测
        features = self.extract_features(df, current_idx)
        prediction = self.model.predict(features)
        return prediction > 0.5  # 阈值判断
    
    def extract_features(self, df, current_idx):
        # 提取特征
        return df.iloc[current_idx][['close', 'volume', 'ma5', 'ma20']].values

# 使用模型策略
model_strategy = MyModelStrategy(your_trained_model)
system.set_custom_strategy(model_strategy)
```

## 输出文件

系统会在输出目录生成以下文件：

- `*.csv`: 信号数据CSV文件
- `*.xlsx`: Excel格式的详细结果
- `*_analysis.json`: JSON格式的分析结果
- `*_report.txt`: 文本格式的性能报告
- `backtest_*.log`: 运行日志

## 参数说明

### 命令行参数

- `--data_folder`: 股票数据文件夹路径（必需）
- `--output_folder`: 输出文件夹路径（可选）
- `--mode`: 测试模式 (single/batch/full)
- `--stock_code`: 股票代码（单股票模式）
- `--stock_codes`: 股票代码列表（批量模式）
- `--target_date`: 目标日期（详细测试）
- `--num_processes`: 进程数量（默认4）
- `--limit`: 限制测试的股票数量
- `--verbose`: 显示详细信息
- `--no_save`: 不保存结果

### 策略条件

当前实现的策略条件包括：

1. **价格条件**: 收盘价在指定范围内
2. **均线上升趋势**: MA5 > MA10 > MA20
3. **价格接近均线**: 收盘价接近MA5
4. **阳线且更高收盘**: 当日为阳线且收盘价高于前一日
5. **成交量条件**: 成交量高于平均水平

## 数据格式要求

股票数据CSV文件应包含以下列：

- `datetime`: 日期时间
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `ma5`, `ma10`, `ma20`: 移动平均线（预计算）
- `volume_ma5`, `volume_ma10`: 成交量移动平均线（预计算）

## 性能优化

- 支持多进程并行处理
- 内存优化和垃圾回收
- 进程级别的日志记录
- 数据验证和错误处理

## 扩展性

- 模块化设计，易于扩展
- 策略引擎支持自定义条件
- 为机器学习模型预留接口
- 支持多种输出格式

## 注意事项

1. 确保数据文件夹中的CSV文件格式正确
2. 多进程模式下注意内存使用
3. 大规模测试时建议使用SSD存储
4. 定期清理输出目录中的临时文件