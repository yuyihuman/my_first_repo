import akshare as ak
import os
import glob
import datetime
import json
import pandas as pd
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import shutil
from matplotlib import rcParams

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False

# 清理历史日志文件
for log_file in glob.glob('commodity_index_*.log'):
    try:
        os.remove(log_file)
    except Exception as e:
        pass

# 清理历史图片文件
for chart_file in glob.glob('commodity_price_chart_*.png'):
    try:
        os.remove(chart_file)
    except Exception as e:
        pass

# 初始化日志
current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
current_log_file = f'commodity_index_{current_time}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(current_log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("开始清理历史日志文件...")
for log_file in glob.glob('commodity_index_*.log'):
    if log_file != current_log_file:
        try:
            os.remove(log_file)
            logger.info(f"已删除历史日志文件: {log_file}")
        except Exception as e:
            logger.error(f"删除日志文件{log_file}失败: {e}")

logger.info("开始清理历史图片文件...")
for chart_file in glob.glob('commodity_price_chart_*.png'):
    try:
        os.remove(chart_file)
        logger.info(f"已删除历史图片文件: {chart_file}")
    except Exception as e:
        logger.error(f"删除图片文件{chart_file}失败: {e}")



# 获取期货数据
futures_data = ak.futures_hist_table_em()

# 过滤条件：只保留上期所和上期能源的主连合约，排除次主连、沪金主连、沪银主连和沪铜主连
filtered_df = futures_data[(futures_data['市场简称'].isin(['上期所'])) & ~futures_data['合约中文代码'].str.contains('次主连') & futures_data['合约中文代码'].str.contains('主连') & ~futures_data['合约中文代码'].str.contains('沪金主连') & ~futures_data['合约中文代码'].str.contains('沪银主连')]
logger.info(f"过滤后的合约数据:\n{filtered_df}")

# 记录过滤结果到日志
logger.info(f"过滤后的合约数据:\n{filtered_df.to_string()}")

# 获取每个合约的历史数据
all_hist_data = []
for symbol in filtered_df['合约中文代码']:
    try:
        hist_data = ak.futures_hist_em(symbol=symbol, period="daily")
        # 获取完整的历史数据以确保指数连续性
        hist_data['合约代码'] = symbol
        all_hist_data.append(hist_data)
        logger.info(f"已获取合约 {symbol} 的历史数据")
    except Exception as e:
        logger.error(f"获取合约 {symbol} 历史数据失败: {e}")

# 合并所有历史数据
if all_hist_data:
    combined_df = pd.concat(all_hist_data)
    logger.info(f"已合并所有合约历史数据，共 {len(combined_df)} 条记录")
    
    # 创建商品价格指数
    logger.info("开始计算商品价格指数...")
    
    # 显示DataFrame的列名
    logger.info(f"DataFrame列名: {list(combined_df.columns)}")
    
    # 根据实际列名进行处理
    date_col = None
    close_col = None
    
    # 优先检查常见的中文列名
    if '时间' in combined_df.columns:
        date_col = '时间'
    elif '日期' in combined_df.columns:
        date_col = '日期'
    else:
        # 检查包含日期相关关键词的列
        for col in combined_df.columns:
            if 'date' in col.lower():
                date_col = col
                break
    
    if '收盘' in combined_df.columns:
        close_col = '收盘'
    else:
        # 检查包含收盘相关关键词的列
        for col in combined_df.columns:
            if 'close' in col.lower():
                close_col = col
                break
    
    if date_col is None or close_col is None:
        logger.warning(f"无法找到日期或收盘价列，可用列: {list(combined_df.columns)}")
        logger.info("使用默认列名处理...")
        # 使用位置索引作为最后的备选方案
        if len(combined_df.columns) >= 4:
            date_col = combined_df.columns[0]
            close_col = combined_df.columns[3]
        else:
            logger.error("数据格式不符合预期，无法计算指数")
            date_col = close_col = None
    else:
        logger.info(f"检测到日期列: {date_col}, 收盘价列: {close_col}")
    
    if date_col and close_col:
        # 按日期分组计算每日涨跌幅
        combined_df[date_col] = pd.to_datetime(combined_df[date_col])
        
        # 为每个合约计算涨跌幅
        combined_df = combined_df.sort_values([date_col, '合约代码'])
        combined_df['涨跌幅_计算'] = combined_df.groupby('合约代码')[close_col].pct_change() * 100
        
        # 计算每日所有品种的平均涨跌幅
        daily_returns = combined_df.groupby(date_col)['涨跌幅_计算'].mean().reset_index()
        daily_returns = daily_returns.sort_values(date_col)
        
        # 以2011年1月1日为基准点100，累计涨跌幅计算指数
        if len(daily_returns) > 0:
            # 找到2011年1月1日或最接近的日期作为基准
            base_date = pd.to_datetime('2011-01-01')
            daily_returns = daily_returns.sort_values(date_col)
            
            # 找到基准日期的索引
            base_index = None
            for i, row in daily_returns.iterrows():
                if row[date_col] >= base_date:
                    base_index = i
                    break
            
            if base_index is None:
                # 如果没有找到2011年1月1日之后的数据，使用第一个可用日期
                base_index = daily_returns.index[0]
                logger.warning("未找到2011年1月1日之后的数据，使用第一个可用日期作为基准")
            else:
                logger.info(f"使用 {daily_returns.loc[base_index, date_col].strftime('%Y-%m-%d')} 作为基准日期")
            
            # 初始化指数列
            daily_returns['商品价格指数'] = 0.0
            
            # 设置基准日期的指数为100
            daily_returns.loc[base_index, '商品价格指数'] = 100.0
            
            # 向前计算（基准日期之前的数据）
            for i in range(daily_returns.index.get_loc(base_index) - 1, -1, -1):
                idx = daily_returns.index[i]
                next_idx = daily_returns.index[i + 1]
                next_index = daily_returns.loc[next_idx, '商品价格指数']
                daily_change = daily_returns.loc[idx, '涨跌幅_计算']
                if pd.notna(daily_change):
                    daily_returns.loc[idx, '商品价格指数'] = next_index / (1 + daily_change / 100)
                else:
                    daily_returns.loc[idx, '商品价格指数'] = next_index
            
            # 向后计算（基准日期之后的数据）
            for i in range(daily_returns.index.get_loc(base_index) + 1, len(daily_returns)):
                idx = daily_returns.index[i]
                prev_idx = daily_returns.index[i - 1]
                prev_index = daily_returns.loc[prev_idx, '商品价格指数']
                daily_change = daily_returns.loc[idx, '涨跌幅_计算']
                if pd.notna(daily_change):
                    daily_returns.loc[idx, '商品价格指数'] = prev_index * (1 + daily_change / 100)
                else:
                    daily_returns.loc[idx, '商品价格指数'] = prev_index
            
            index_data = daily_returns
            
            # 转换为JSON格式保存
            index_json = {
                "指数名称": "上期所商品价格指数",
                "基准日期": "2011-01-01",
                "基准点位": 100.0,
                "计算方法": "基于每日涨跌幅平均值的累计指数，以2011年1月1日为基准点100",
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "包含品种": list(filtered_df['合约中文代码'].unique()),
                "指数数据": [
                    {
                        "日期": row[date_col].strftime('%Y-%m-%d'),
                        "指数值": round(row['商品价格指数'], 2),
                        "日涨跌幅": round(row['涨跌幅_计算'], 4) if pd.notna(row['涨跌幅_计算']) else 0.0
                    }
                    for _, row in index_data.iterrows()
                ]
            }
            
            # 保存指数到JSON文件
            with open('commodity_price_index.json', 'w', encoding='utf-8') as f:
                json.dump(index_json, f, ensure_ascii=False, indent=2)
            
            logger.info("商品价格指数已保存到: commodity_price_index.json")
            
            # 备份JSON文件到指定目录
            backup_dir = r'C:\Users\17701\github\my_first_repo\stock_info\cache\outsource'
            try:
                # 确保备份目录存在
                os.makedirs(backup_dir, exist_ok=True)
                # 复制文件到备份目录
                backup_path = os.path.join(backup_dir, 'commodity_price_index.json')
                shutil.copy2('commodity_price_index.json', backup_path)
                logger.info(f"商品价格指数已备份到: {backup_path}")
            except Exception as e:
                logger.error(f"备份文件失败: {e}")
            logger.info(f"指数包含 {len(index_json['包含品种'])} 个品种")
            logger.info(f"指数数据包含 {len(index_json['指数数据'])} 个交易日")
            if len(index_data) > 0:
                logger.info(f"最新指数值: {index_data.iloc[-1]['商品价格指数']:.2f}")
            
            # 创建价格趋势图
            logger.info("开始生成商品价格趋势图...")
            
            # 获取商品列表
            symbols = list(filtered_df['合约中文代码'].unique())
            num_symbols = len(symbols)
            
            # 找到所有商品中最早的起始日期和最晚的结束日期，作为统一的X轴范围
            global_start_date = None
            global_end_date = None
            
            for symbol in symbols:
                symbol_data = combined_df[combined_df['合约代码'] == symbol].copy()
                if len(symbol_data) > 0:
                    symbol_data = symbol_data.sort_values(date_col)
                    start_date = symbol_data.iloc[0][date_col]
                    end_date = symbol_data.iloc[-1][date_col]
                    
                    if global_start_date is None or start_date < global_start_date:
                        global_start_date = start_date
                    if global_end_date is None or end_date > global_end_date:
                        global_end_date = end_date
            
            logger.info(f"统一X轴范围: {global_start_date.strftime('%Y-%m-%d')} 至 {global_end_date.strftime('%Y-%m-%d')}")
            
            # 创建长图：18个商品子图 + 1个综合指数图
            fig, axes = plt.subplots(num_symbols + 1, 1, figsize=(15, (num_symbols + 1) * 4))
            
            # 为每个商品创建独立的子图
            for i, symbol in enumerate(symbols):
                symbol_data = combined_df[combined_df['合约代码'] == symbol].copy()
                if len(symbol_data) > 0:
                    symbol_data = symbol_data.sort_values(date_col)
                    # 标准化处理：以第一个价格为基准100
                    first_price = symbol_data.iloc[0][close_col]
                    symbol_data['标准化价格'] = (symbol_data[close_col] / first_price) * 100
                    
                    # 绘制该商品的价格趋势
                    axes[i].plot(symbol_data[date_col], symbol_data['标准化价格'], 
                                color='blue', linewidth=2, alpha=0.8)
                    axes[i].set_title(f'{symbol.replace("主连", "")}价格趋势（基准=100）', 
                                     fontsize=12, fontweight='bold')
                    axes[i].set_ylabel('标准化价格指数', fontsize=10)
                    axes[i].grid(True, alpha=0.3)
                    
                    # 设置X轴范围为统一的全局时间范围
                    axes[i].set_xlim(global_start_date, global_end_date)
                    axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    axes[i].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
                    plt.setp(axes[i].xaxis.get_majorticklabels(), rotation=45, fontsize=8)
                    
                    # 添加最新价格标注
                    latest_price = symbol_data.iloc[-1]['标准化价格']
                    latest_date = symbol_data.iloc[-1][date_col]
                    axes[i].annotate(f'{latest_price:.1f}', 
                                   xy=(latest_date, latest_price), 
                                   xytext=(10, 10), textcoords='offset points',
                                   fontsize=9, color='red', fontweight='bold')
            
            # 最后一个子图：商品价格综合指数
            axes[-1].plot(index_data[date_col], index_data['商品价格指数'], 
                         color='red', linewidth=3, label='商品价格综合指数')
            axes[-1].set_title('上期所商品价格综合指数', fontsize=14, fontweight='bold')
            axes[-1].set_xlabel('日期', fontsize=12)
            axes[-1].set_ylabel('指数值', fontsize=12)
            axes[-1].legend(fontsize=10)
            axes[-1].grid(True, alpha=0.3)
            
            # 设置X轴范围为统一的全局时间范围
            axes[-1].set_xlim(global_start_date, global_end_date)
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)
            
            # 添加综合指数最新值标注
            latest_index = index_data.iloc[-1]['商品价格指数']
            latest_date = index_data.iloc[-1][date_col]
            axes[-1].annotate(f'{latest_index:.2f}', 
                             xy=(latest_date, latest_index), 
                             xytext=(10, 10), textcoords='offset points',
                             fontsize=11, color='red', fontweight='bold')
            
            # 调整布局
            plt.tight_layout(pad=2.0)
            
            # 保存图表
            chart_filename = f'commodity_price_chart_{current_time}.png'
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            logger.info(f"价格趋势图已保存到: {chart_filename}")
            
            # 关闭图表以释放内存
            plt.close()
            
            # 输出统计信息
            logger.info(f"图表包含 {num_symbols} 种商品的独立价格趋势图")
            logger.info(f"商品列表: {', '.join([s.replace('主连', '') for s in symbols])}")
            logger.info(f"图表总高度: {(num_symbols + 1) * 4} 英寸，包含 {num_symbols + 1} 个子图")
        else:
            logger.warning("没有足够的数据计算指数")
    else:
        logger.error("无法识别数据列名，跳过指数计算")
else:
    logger.error("没有获取到任何合约的历史数据")