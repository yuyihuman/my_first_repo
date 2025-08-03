import akshare as ak
import os
import glob
import datetime
import json
import pandas as pd
import logging

# 清理历史日志文件
for log_file in glob.glob('commodity_index_*.log'):
    try:
        os.remove(log_file)
    except Exception as e:
        pass

# 初始化日志
current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
current_log_file = f'commodity_index_{current_time}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(current_log_file),
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



# 获取期货数据
futures_data = ak.futures_hist_table_em()

# 过滤条件：只保留上期所和上期能源的主连合约，排除次主连和沪金主连
filtered_df = futures_data[(futures_data['市场简称'].isin(['上期所'])) & ~futures_data['合约中文代码'].str.contains('次主连') & futures_data['合约中文代码'].str.contains('主连') & ~futures_data['合约中文代码'].str.contains('沪金主连')]
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
        
        # 以100为基准点，累计涨跌幅计算指数
        if len(daily_returns) > 0:
            daily_returns['商品价格指数'] = 100.0
            for i in range(1, len(daily_returns)):
                prev_index = daily_returns.iloc[i-1]['商品价格指数']
                daily_change = daily_returns.iloc[i]['涨跌幅_计算']
                if pd.notna(daily_change):
                    daily_returns.iloc[i, daily_returns.columns.get_loc('商品价格指数')] = prev_index * (1 + daily_change / 100)
                else:
                    daily_returns.iloc[i, daily_returns.columns.get_loc('商品价格指数')] = prev_index
            
            index_data = daily_returns
            
            # 转换为JSON格式保存
            index_json = {
                "指数名称": "上期所商品价格指数",
                "基准日期": index_data.iloc[0][date_col].strftime('%Y-%m-%d'),
                "基准点位": 100.0,
                "计算方法": "基于每日涨跌幅平均值的累计指数",
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
            logger.info(f"指数包含 {len(index_json['包含品种'])} 个品种")
            logger.info(f"指数数据包含 {len(index_json['指数数据'])} 个交易日")
            if len(index_data) > 0:
                logger.info(f"最新指数值: {index_data.iloc[-1]['商品价格指数']:.2f}")
        else:
            logger.warning("没有足够的数据计算指数")
    else:
        logger.error("无法识别数据列名，跳过指数计算")
else:
    logger.error("没有获取到任何合约的历史数据")