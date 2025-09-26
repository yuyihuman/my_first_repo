# coding:utf-8
"""
数据准备模块 - 负责加载和预处理股票数据

数据来源：
- 股票历史数据来源于：c:/Users/17701/github/my_first_repo/stockapi/stock_base_info/all_stocks_data/
- 使用数据源中的预计算均线和成交量数据，不进行重复计算
"""

import pandas as pd
import os
import logging
from typing import Optional, List, Dict, Any


class StockDataLoader:
    """股票数据加载器"""
    
    def __init__(self, data_folder: str):
        """
        初始化数据加载器
        
        Args:
            data_folder: 股票数据文件夹路径
        """
        self.data_folder = data_folder
        self.logger = logging.getLogger(__name__)
        
        # 定义必需的列
        self.basic_cols = ['datetime', 'open', 'close', 'high', 'low', 'volume']
        self.ma_cols = ['close_5d_avg', 'close_10d_avg', 'close_20d_avg', 'close_30d_avg', 'close_60d_avg']
        self.volume_cols = ['volume_5d_avg', 'volume_10d_avg', 'volume_20d_avg', 'volume_30d_avg', 'volume_60d_avg']
        
        # 验证数据文件夹
        if not os.path.exists(data_folder):
            raise ValueError(f"数据文件夹不存在: {data_folder}")
    
    def get_stock_file_path(self, stock_code: str) -> str:
        """
        获取股票数据文件路径
        
        Args:
            stock_code: 股票代码
            
        Returns:
            str: 文件路径
        """
        stock_folder = f"stock_{stock_code}_data"
        return os.path.join(self.data_folder, stock_folder, f"{stock_code}_daily_history.csv")
    
    def load_stock_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        加载单个股票的数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            DataFrame: 股票数据，如果加载失败返回None
        """
        csv_file_path = self.get_stock_file_path(stock_code)
        
        try:
            # 检查文件是否存在
            if not os.path.exists(csv_file_path):
                self.logger.warning(f"数据文件不存在: {csv_file_path}")
                return None
            
            # 检查文件大小
            file_size = os.path.getsize(csv_file_path)
            if file_size == 0:
                self.logger.warning(f"数据文件为空: {csv_file_path}")
                return None
            
            # 检查文件中存在哪些列
            try:
                # 读取第一行来检查列名
                sample_df = pd.read_csv(csv_file_path, nrows=1)
                available_cols = sample_df.columns.tolist()
                self.logger.debug(f"文件 {csv_file_path} 可用列: {available_cols}")
                
                # 检查基本列是否存在
                missing_basic_cols = [col for col in self.basic_cols if col not in available_cols]
                if missing_basic_cols:
                    self.logger.warning(f"文件 {csv_file_path} 缺失基本列: {missing_basic_cols}")
                    return None
                
                # 确定要读取的列
                cols_to_read = self.basic_cols.copy()
                available_ma_cols = [col for col in self.ma_cols if col in available_cols]
                available_volume_cols = [col for col in self.volume_cols if col in available_cols]
                cols_to_read.extend(available_ma_cols)
                cols_to_read.extend(available_volume_cols)
                
                # 读取CSV文件
                df = pd.read_csv(csv_file_path, usecols=cols_to_read)
                self.logger.debug(f"成功读取文件 {csv_file_path}，数据行数: {len(df)}")
                
            except Exception as e:
                self.logger.warning(f"列检查失败，回退到基本列读取: {e}")
                try:
                    # 如果列检查失败，回退到只读取基本列
                    df = pd.read_csv(csv_file_path, usecols=self.basic_cols)
                    available_ma_cols = []
                    available_volume_cols = []
                    self.logger.debug(f"回退读取成功，数据行数: {len(df)}")
                except Exception as e2:
                    self.logger.error(f"回退读取也失败: {e2}")
                    return None
            
            # 检查数据是否为空
            if df.empty:
                self.logger.warning(f"数据文件内容为空: {csv_file_path}")
                return None
            
            # 转换日期列
            try:
                df['datetime'] = pd.to_datetime(df['datetime'])
            except Exception as e:
                self.logger.error(f"日期列转换失败: {e}")
                return None
            
            # 按日期排序
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 检查是否有必需的预计算均线数据
            required_ma_cols = ['close_5d_avg', 'close_10d_avg', 'close_20d_avg', 'close_30d_avg', 'close_60d_avg']
            missing_ma_cols = [col for col in required_ma_cols if col not in available_ma_cols]
            
            if missing_ma_cols:
                self.logger.warning(f"文件 {csv_file_path} 缺失预计算均线数据: {missing_ma_cols}，跳过该股票")
                return None
            
            # 处理收盘价均线数据：只使用预计算的数据
            df['ma5'] = df['close_5d_avg']
            df['ma10'] = df['close_10d_avg']
            df['ma20'] = df['close_20d_avg']
            df['ma30'] = df['close_30d_avg']
            df['ma60'] = df['close_60d_avg']
            
            # 检查是否有必需的预计算成交量数据
            required_volume_cols = ['volume_5d_avg', 'volume_10d_avg', 'volume_20d_avg', 'volume_30d_avg', 'volume_60d_avg']
            missing_volume_cols = [col for col in required_volume_cols if col not in available_volume_cols]
            
            if missing_volume_cols:
                self.logger.warning(f"文件 {csv_file_path} 缺失预计算成交量数据: {missing_volume_cols}，跳过该股票")
                return None
            
            # 处理成交量数据：只使用预计算的数据
            df['vol5'] = df['volume_5d_avg']
            df['vol10'] = df['volume_10d_avg']
            df['vol20'] = df['volume_20d_avg']
            df['vol30'] = df['volume_30d_avg']
            df['vol60'] = df['volume_60d_avg']
            
            # 删除不再需要的原始均线列和成交量列以节省内存
            for col in available_ma_cols + available_volume_cols:
                if col in df.columns:
                    df.drop(col, axis=1, inplace=True)
            
            # 最终数据验证
            if len(df) < 41:  # 至少需要41天数据
                self.logger.warning(f"文件 {csv_file_path} 数据量不足（{len(df)}条），需要至少41条数据")
                return None
            
            self.logger.debug(f"成功加载数据文件 {csv_file_path}，最终数据行数: {len(df)}")
            return df
            
        except Exception as e:
            self.logger.error(f"加载数据失败 {csv_file_path}: {e}")
            return None
    
    def get_available_stocks(self) -> List[str]:
        """
        获取所有可用的股票代码列表
        
        Returns:
            List[str]: 股票代码列表
        """
        stock_codes = []
        
        try:
            # 遍历数据文件夹
            for folder_name in os.listdir(self.data_folder):
                folder_path = os.path.join(self.data_folder, folder_name)
                
                # 检查是否是股票数据文件夹
                if os.path.isdir(folder_path) and folder_name.startswith('stock_') and folder_name.endswith('_data'):
                    # 提取股票代码
                    stock_code = folder_name.replace('stock_', '').replace('_data', '')
                    
                    # 检查CSV文件是否存在
                    csv_file = os.path.join(folder_path, f"{stock_code}_daily_history.csv")
                    if os.path.exists(csv_file):
                        stock_codes.append(stock_code)
            
            self.logger.info(f"发现 {len(stock_codes)} 个可用股票")
            return sorted(stock_codes)
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return []
    
    def load_multiple_stocks(self, stock_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """
        批量加载多个股票的数据
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        stock_data = {}
        
        for stock_code in stock_codes:
            df = self.load_stock_data(stock_code)
            if df is not None:
                stock_data[stock_code] = df
            
        self.logger.info(f"成功加载 {len(stock_data)} 个股票的数据")
        return stock_data
    
    def validate_data_quality(self, df: pd.DataFrame, stock_code: str) -> bool:
        """
        验证数据质量
        
        Args:
            df: 股票数据
            stock_code: 股票代码
            
        Returns:
            bool: 数据是否合格
        """
        try:
            # 检查必需列是否存在
            required_cols = ['datetime', 'open', 'close', 'high', 'low', 'volume', 
                           'ma5', 'ma10', 'ma20', 'ma30', 'ma60', 'vol5', 'vol10', 'vol20', 'vol30', 'vol60']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                self.logger.warning(f"股票 {stock_code} 缺失必需列: {missing_cols}")
                return False
            
            # 检查数据量
            if len(df) < 41:
                self.logger.warning(f"股票 {stock_code} 数据量不足: {len(df)} < 41")
                return False
            
            # 检查价格数据的合理性 - 只检查最近1000条数据，允许历史数据中的异常值
            recent_data = df.tail(1000) if len(df) > 1000 else df
            invalid_close_ratio = (recent_data['close'] <= 0).sum() / len(recent_data)
            invalid_open_ratio = (recent_data['open'] <= 0).sum() / len(recent_data)
            
            # 如果超过10%的最近数据有非正价格，则认为数据质量不合格
            if invalid_close_ratio > 0.1 or invalid_open_ratio > 0.1:
                self.logger.warning(f"股票 {stock_code} 最近数据中非正价格比例过高: close={invalid_close_ratio:.2%}, open={invalid_open_ratio:.2%}")
                return False
            
            # 检查日期数据的连续性 - 只检查最近1000条数据，允许历史数据中的长间隔
            df_sorted = df.sort_values('datetime')
            recent_sorted = df_sorted.tail(1000) if len(df_sorted) > 1000 else df_sorted
            date_diff = recent_sorted['datetime'].diff().dt.days
            
            # 允许更大的间隔（如长假期），但不应该有超过30天的间隔
            large_gaps = date_diff > 30
            if large_gaps.any():
                gap_count = large_gaps.sum()
                total_count = len(recent_sorted)
                # 如果超过5%的数据有大间隔，则认为有问题
                if gap_count / total_count > 0.05:
                    self.logger.warning(f"股票 {stock_code} 最近数据中存在过多异常日期间隔: {gap_count}/{total_count}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证股票 {stock_code} 数据质量时出错: {e}")
            return False


class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def filter_by_date_range(self, df: pd.DataFrame, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        按日期范围过滤数据
        
        Args:
            df: 股票数据
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame: 过滤后的数据
        """
        filtered_df = df.copy()
        
        if start_date:
            start_date = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df['datetime'] >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df['datetime'] <= end_date]
        
        return filtered_df.reset_index(drop=True)
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加技术指标（基于已有的预计算数据）
        
        Args:
            df: 股票数据
            
        Returns:
            pd.DataFrame: 添加指标后的数据
        """
        df = df.copy()
        
        # 添加涨跌幅
        df['price_change'] = df['close'] - df['open']
        df['price_change_pct'] = (df['close'] - df['open']) / df['open'] * 100
        
        # 添加前一日收盘价
        df['prev_close'] = df['close'].shift(1)
        
        # 添加日内振幅
        df['amplitude'] = (df['high'] - df['low']) / df['open'] * 100
        
        return df
    
    def clean_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        清理数据
        
        Args:
            df: 股票数据
            stock_code: 股票代码
            
        Returns:
            pd.DataFrame: 清理后的数据
        """
        df = df.copy()
        original_len = len(df)
        
        # 删除价格为0或负数的记录
        df = df[(df['open'] > 0) & (df['close'] > 0) & (df['high'] > 0) & (df['low'] > 0)]
        
        # 删除成交量为负数的记录
        df = df[df['volume'] >= 0]
        
        # 删除异常价格数据（高开低收不合理的数据）
        df = df[df['high'] >= df[['open', 'close']].max(axis=1)]
        df = df[df['low'] <= df[['open', 'close']].min(axis=1)]
        
        cleaned_len = len(df)
        if cleaned_len < original_len:
            self.logger.info(f"股票 {stock_code} 清理了 {original_len - cleaned_len} 条异常数据")
        
        return df.reset_index(drop=True)