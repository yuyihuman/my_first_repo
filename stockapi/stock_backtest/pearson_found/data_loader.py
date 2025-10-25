"""
股票数据加载模块

该模块专注于加载股票的历史K线数据，支持多种时间粒度的数据加载。
数据来源：xtquant (迅投量化)
数据格式：CSV文件，UTF-8-BOM编码

主要功能：
1. 加载指定股票代码的历史数据
2. 提取关键字段：开盘价、收盘价、最高价、最低价、成交量
3. 支持多种时间粒度：1分钟、5分钟、30分钟、日线

作者：Stock Backtest System
创建时间：2024年
"""

import pandas as pd
import os
from typing import Optional, List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StockDataLoader:
    """股票数据加载器"""
    
    def __init__(self, data_base_path: str = None):
        """
        初始化数据加载器
        
        Args:
            data_base_path: 数据根目录路径，如果不指定则使用默认路径
        """
        if data_base_path is None:
            # 默认数据路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_base_path = os.path.join(
                os.path.dirname(current_dir), 
                'data', 
                'all_stocks_data'
            )
        else:
            self.data_base_path = data_base_path
            
        # 支持的时间粒度
        self.time_frames = {
            '1minute': '1minute_history.csv',
            '5minute': '5minute_history.csv', 
            '30minute': '30minute_history.csv',
            'daily': 'daily_history.csv'
        }
        
        # 关键字段
        self.key_fields = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        
        logger.info(f"数据加载器初始化完成，数据路径: {self.data_base_path}")
    
    def load_stock_data(self, 
                       stock_code: str, 
                       time_frame: str = 'daily',
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        加载指定股票的历史数据
        
        Args:
            stock_code: 股票代码，如 '000001'
            time_frame: 时间粒度，可选值：'1minute', '5minute', '30minute', 'daily'
            start_date: 开始日期，格式：'YYYY-MM-DD'
            end_date: 结束日期，格式：'YYYY-MM-DD'
            fields: 需要的字段列表，如果不指定则返回关键字段
            
        Returns:
            包含股票数据的DataFrame，如果加载失败则返回None
        """
        try:
            # 检查时间粒度是否支持
            if time_frame not in self.time_frames:
                logger.error(f"不支持的时间粒度: {time_frame}")
                return None
            
            # 构建文件路径
            stock_folder = f"stock_{stock_code}_data"
            stock_path = os.path.join(self.data_base_path, stock_folder)
            file_name = f"{stock_code}_{self.time_frames[time_frame]}"
            file_path = os.path.join(stock_path, file_name)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"数据文件不存在: {file_path}")
                return None
            
            # 读取CSV文件（注意UTF-8-BOM编码）
            logger.debug(f"正在加载数据: {file_path}")
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 数据预处理
            df = self._preprocess_data(df)
            
            # 日期过滤
            if start_date or end_date:
                df = self._filter_by_date(df, start_date, end_date)
            
            # 字段选择
            if fields is None:
                fields = self.key_fields
            
            # 确保所需字段存在（考虑datetime可能已经成为索引）
            available_fields = []
            missing_fields = set()
            
            for field in fields:
                if field == 'datetime':
                    # datetime字段可能在列中，也可能已经成为索引
                    if field in df.columns or df.index.name == 'datetime':
                        available_fields.append(field)
                    else:
                        missing_fields.add(field)
                else:
                    # 其他字段必须在列中
                    if field in df.columns:
                        available_fields.append(field)
                    else:
                        missing_fields.add(field)
            
            if missing_fields:
                logger.warning(f"以下字段在数据中不存在: {missing_fields}")
            
            # 只选择实际存在于列中的字段（排除已成为索引的datetime）
            column_fields = [field for field in available_fields if field in df.columns]
            result_df = df[column_fields].copy() if column_fields else df.copy()
            
            logger.debug(f"数据加载成功，股票: {stock_code}, 时间粒度: {time_frame}, 数据行数: {len(result_df)}")
            return result_df
            
        except Exception as e:
            logger.error(f"加载股票数据失败: {stock_code}, 错误: {str(e)}")
            return None
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            预处理后的DataFrame
        """
        # 转换datetime列为pandas datetime类型
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 确保数值列为float类型
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 按时间排序
        if 'datetime' in df.columns:
            df = df.sort_values('datetime').reset_index(drop=True)
            # 将datetime列设置为索引，这样就能显示实际日期
            df = df.set_index('datetime')
        
        # 删除包含NaN的关键字段行
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        return df
    
    def _filter_by_date(self, df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """
        按日期范围过滤数据
        
        Args:
            df: 数据DataFrame
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            过滤后的DataFrame
        """
        if 'datetime' not in df.columns:
            logger.warning("数据中没有datetime列，无法进行日期过滤")
            return df
        
        if start_date:
            start_date = pd.to_datetime(start_date)
            df = df[df['datetime'] >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            df = df[df['datetime'] <= end_date]
        
        return df


def main():
    """
    简单的使用示例
    """
    # 创建数据加载器
    loader = StockDataLoader()
    
    # 加载股票数据
    stock_code = "000001"  # 平安银行
    data = loader.load_stock_data(stock_code, 'daily')
    
    if data is not None:
        print(f"成功加载股票 {stock_code} 的数据")
        print(f"数据行数: {len(data)}")
        print(f"数据列: {list(data.columns)}")
        print("\n数据预览:")
        print(data.head())
    else:
        print(f"无法加载股票 {stock_code} 的数据")


if __name__ == "__main__":
    main()