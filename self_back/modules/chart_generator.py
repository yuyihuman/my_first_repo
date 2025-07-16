#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线图生成模块
用于绘制股票K线图并标记买卖位置
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Optional, Tuple
from utils.logger import setup_logger

try:
    from xtquant import xtdata
except ImportError:
    xtdata = None

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ChartGenerator:
    """
    K线图生成器
    """
    
    def __init__(self):
        """
        初始化K线图生成器
        """
        self.logger = setup_logger('chart_generator', 'chart_generator.log')
        self.logger.info("K线图生成器初始化完成")
        
        # 检查xtdata是否可用
        if xtdata is None:
            self.logger.error("xtdata模块未安装，无法获取真实数据")
            raise ImportError("xtdata模块未安装，项目只支持真实数据")
        else:
            self.logger.info("xtdata模块已加载")
        
        # 确保charts目录存在
        self.charts_dir = 'charts'
        if not os.path.exists(self.charts_dir):
            os.makedirs(self.charts_dir)
            self.logger.info(f"创建图表目录: {self.charts_dir}")
    
    def _get_stock_data(self, stock_code: str, start_date: str, end_date: str, 
                           batch_data: dict = None, data_manager=None) -> Optional[pd.DataFrame]:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            batch_data: 批量数据（可选）
            data_manager: 数据管理器（可选）
            
        Returns:
            股票数据DataFrame或None
        """
        try:
            # 优先使用批量数据
            if batch_data and data_manager:
                self.logger.info(f"使用批量数据获取股票数据: {stock_code}")
                df = data_manager.get_stock_dataframe(stock_code, batch_data, start_date, end_date)
                if df is not None and not df.empty:
                    self.logger.info(f"成功从批量数据获取 {len(df)} 条数据")
                    return df
                else:
                    self.logger.warning(f"批量数据中无法获取股票 {stock_code} 的数据，回退到传统方式")
            
            # 使用xtdata获取真实数据
            self.logger.info(f"使用xtdata获取股票数据: {stock_code}")
            
            # 转换日期格式
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            # 获取K线数据
            # 注意：xtdata可能有数据范围限制，尝试获取可用的最大范围
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_dt.strftime('%Y%m%d'),
                end_time=end_dt.strftime('%Y%m%d'),
                dividend_type='none',
                fill_data=True
            )
            
            # 如果指定范围没有数据，尝试获取更大的时间范围
            if not data or not all(field in data for field in ['open', 'high', 'low', 'close', 'volume']) or stock_code not in data['close'].index:
                self.logger.warning(f"指定时间范围无数据，尝试扩大范围获取 {stock_code} 的历史数据")
                # 尝试获取更大范围的数据（2年）
                extended_start = (start_dt - timedelta(days=730)).strftime('%Y%m%d')
                data = xtdata.get_market_data(
                    field_list=['open', 'high', 'low', 'close', 'volume'],
                    stock_list=[stock_code],
                    period='1d',
                    start_time=extended_start,
                    end_time=end_dt.strftime('%Y%m%d'),
                    dividend_type='none',
                    fill_data=True
                )
            
            if data and all(field in data for field in ['open', 'high', 'low', 'close', 'volume']):
                # 检查股票代码是否在数据中
                if (stock_code in data['close'].index and 
                    not data['close'].loc[stock_code].empty):
                    
                    # 构建DataFrame
                    df_data = {
                        'Open': data['open'].loc[stock_code],
                        'High': data['high'].loc[stock_code],
                        'Low': data['low'].loc[stock_code],
                        'Close': data['close'].loc[stock_code],
                        'Volume': data['volume'].loc[stock_code]
                    }
                    
                    df = pd.DataFrame(df_data)
                    df.index = pd.to_datetime(df.index, format='%Y%m%d')
                    df.index.name = 'Date'
                    
                    self.logger.info(f"成功获取 {len(df)} 条真实数据")
                    return df
                else:
                    self.logger.error(f"股票 {stock_code} 不在xtdata返回的数据中，无法获取真实数据")
                    return None
            else:
                self.logger.error(f"xtdata未返回有效数据，无法获取真实数据")
                return None
                
        except Exception as e:
            self.logger.error(f"获取股票数据失败: {str(e)}", exc_info=True)
            return None
    

    
    def _draw_candlestick(self, ax, df: pd.DataFrame):
        """
        绘制K线图
        
        Args:
            ax: matplotlib轴对象
            df: K线数据DataFrame
        """
        try:
            dates = df.index
            opens = df['Open'].values
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            
            # 使用数值索引而不是日期，这样横轴只显示有数据的交易日
            x_positions = np.arange(len(df))
            
            # 计算涨跌
            up = closes >= opens
            down = ~up
            
            # 设置颜色
            up_color = 'red'
            down_color = 'green'
            
            # 绘制上影线和下影线
            ax.vlines(x_positions[up], lows[up], highs[up], color=up_color, linewidth=0.8)
            ax.vlines(x_positions[down], lows[down], highs[down], color=down_color, linewidth=0.8)
            
            # 绘制实体
            # 根据数据点数量动态调整K线宽度
            total_days = len(dates)
            if total_days > 50:
                width = 0.8  # 较多数据时使用较宽的K线
            elif total_days > 20:
                width = 0.7
            else:
                width = 0.6
                
            for i in range(len(df)):
                x_pos = x_positions[i]
                if up[i]:
                    # 阳线（红色）
                    height = max(closes[i] - opens[i], 0.01)  # 确保最小高度
                    rect = Rectangle((x_pos - width/2, opens[i]), 
                                   width, height, 
                                   facecolor=up_color, edgecolor=up_color, linewidth=0.5)
                else:
                    # 阴线（绿色）
                    height = max(opens[i] - closes[i], 0.01)  # 确保最小高度
                    rect = Rectangle((x_pos - width/2, closes[i]), 
                                   width, height, 
                                   facecolor=down_color, edgecolor=down_color, linewidth=0.5)
                ax.add_patch(rect)
            
            # 设置x轴标签为日期
            ax.set_xticks(x_positions)
            # 根据数据量调整日期标签显示
            if total_days > 30:
                # 数据较多时，每隔几天显示一次日期
                step = max(1, total_days // 15)  # 大约显示15个标签
                tick_positions = x_positions[::step]
                tick_labels = [dates[i].strftime('%m-%d') for i in range(0, len(dates), step)]
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, rotation=45, fontsize=10)
            else:
                # 数据较少时，显示所有日期或每隔一天
                step = max(1, total_days // 10)
                tick_positions = x_positions[::step]
                tick_labels = [dates[i].strftime('%m-%d') for i in range(0, len(dates), step)]
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, rotation=45, fontsize=10)
            
            # 设置x轴范围
            ax.set_xlim(-0.5, len(df) - 0.5)
            
            self.logger.info(f"K线图绘制完成，共 {len(df)} 根K线")
            
        except Exception as e:
            self.logger.error(f"绘制K线图失败: {str(e)}", exc_info=True)
    
    def _mark_trades(self, ax, trades: List[Dict], df: pd.DataFrame):
        """
        在K线图上标记买卖点
        
        Args:
            ax: matplotlib轴对象
            trades: 交易记录列表
            df: K线数据DataFrame
        """
        try:
            buy_marked = False
            sell_marked = False
            
            for trade in trades:
                buy_date = datetime.strptime(trade['buy_date'], '%Y%m%d')
                sell_date = datetime.strptime(trade['sell_date'], '%Y%m%d')
                
                # 标记买入点
                if buy_date in df.index:
                    buy_price = df.loc[buy_date, 'Close']
                    # 找到对应的x轴位置（数值索引）
                    buy_x_pos = df.index.get_loc(buy_date)
                    
                    ax.scatter(buy_x_pos, buy_price, color='blue', marker='^', 
                             s=100, zorder=5, label='买入' if not buy_marked else "")
                    ax.annotate(f'买入\n{buy_price:.2f}', 
                              xy=(buy_x_pos, buy_price), 
                              xytext=(10, 20), 
                              textcoords='offset points',
                              bbox=dict(boxstyle='round,pad=0.3', facecolor='blue', alpha=0.7),
                              arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                              fontsize=8, color='white')
                    buy_marked = True
                
                # 标记卖出点
                if sell_date in df.index:
                    sell_price = df.loc[sell_date, 'Close']
                    # 找到对应的x轴位置（数值索引）
                    sell_x_pos = df.index.get_loc(sell_date)
                    
                    ax.scatter(sell_x_pos, sell_price, color='orange', marker='v', 
                             s=100, zorder=5, label='卖出' if not sell_marked else "")
                    ax.annotate(f'卖出\n{sell_price:.2f}', 
                              xy=(sell_x_pos, sell_price), 
                              xytext=(10, -30), 
                              textcoords='offset points',
                              bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.7),
                              arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                              fontsize=8, color='white')
                    sell_marked = True
            
            self.logger.info(f"标记交易点完成，共 {len(trades)} 笔交易")
            
        except Exception as e:
            self.logger.error(f"标记交易点失败: {str(e)}", exc_info=True)
    
    def generate_chart(self, stock_code: str, start_date: str, end_date: str, 
                      trades: List[Dict] = None, batch_data: dict = None, data_manager=None) -> str:
        """
        生成股票K线图
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            trades: 交易记录列表
            batch_data: 批量数据（可选）
            data_manager: 数据管理器（可选）
            
        Returns:
            图表文件路径
        """
        return self.generate_kline_chart(stock_code, start_date, end_date, trades or [], None)
    
    def generate_kline_chart(self, stock_code: str, start_date: str, end_date: str, 
                           trades: List[Dict], title: str = None, batch_data: dict = None, data_manager=None) -> str:
        """
        生成带交易标记的K线图
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            trades: 交易记录列表
            title: 图表标题
            batch_data: 批量数据（可选）
            data_manager: 数据管理器（可选）
            
        Returns:
            保存的图片文件路径
        """
        try:
            self.logger.info(f"开始生成K线图: {stock_code}, {start_date} - {end_date}")
            
            # 获取股票数据
            df = self._get_stock_data(stock_code, start_date, end_date, batch_data, data_manager)
            if df is None or df.empty:
                raise ValueError(f"无法获取股票 {stock_code} 的数据")
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # 绘制K线图
            self._draw_candlestick(ax, df)
            
            # 标记交易点
            if trades:
                self._mark_trades(ax, trades, df)
            
            # 设置图表样式
            ax.set_title(title or f'{stock_code} K线图与交易记录', fontsize=16, fontweight='bold')
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('价格', fontsize=12)
            
            # 添加网格
            ax.grid(True, alpha=0.3)
            
            # 添加图例（只有在实际标记了交易点时才显示）
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(loc='upper left')
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图片
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{stock_code}_kline_{timestamp}.png'
            filepath = os.path.join(self.charts_dir, filename)
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"K线图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"生成K线图失败: {str(e)}", exc_info=True)
            return ""
    
    def generate_multiple_charts(self, backtest_result: Dict) -> List[str]:
        """
        为回测结果生成多个K线图
        
        Args:
            backtest_result: 回测结果字典
            
        Returns:
            生成的图片文件路径列表
        """
        try:
            chart_files = []
            
            if 'trades' not in backtest_result:
                self.logger.warning("回测结果中没有交易数据")
                return chart_files
            
            trades = backtest_result['trades']
            if not trades:
                self.logger.warning("没有交易记录")
                return chart_files
            
            # 按股票分组交易记录
            stock_trades = {}
            for trade in trades:
                stock_code = trade['stock_code']
                if stock_code not in stock_trades:
                    stock_trades[stock_code] = []
                stock_trades[stock_code].append(trade)
            
            # 为每只股票生成K线图
            for stock_code, stock_trade_list in stock_trades.items():
                # 计算日期范围
                all_dates = []
                for trade in stock_trade_list:
                    all_dates.extend([trade['buy_date'], trade['sell_date']])
                
                start_date = min(all_dates)
                end_date = max(all_dates)
                
                # 扩展日期范围以显示更多上下文
                start_dt = datetime.strptime(start_date, '%Y%m%d')
                end_dt = datetime.strptime(end_date, '%Y%m%d')
                
                # 向前向后各扩展10天
                start_dt = start_dt.replace(day=max(1, start_dt.day - 10))
                end_dt = end_dt.replace(day=min(31, end_dt.day + 10))
                
                extended_start = start_dt.strftime('%Y%m%d')
                extended_end = end_dt.strftime('%Y%m%d')
                
                # 生成图表
                title = f'{stock_code} 交易记录 ({len(stock_trade_list)}笔交易)'
                chart_file = self.generate_kline_chart(
                    stock_code, extended_start, extended_end, stock_trade_list, title
                )
                
                if chart_file:
                    chart_files.append(chart_file)
            
            self.logger.info(f"生成K线图完成，共 {len(chart_files)} 个文件")
            return chart_files
            
        except Exception as e:
            self.logger.error(f"生成多个K线图失败: {str(e)}", exc_info=True)
            return []