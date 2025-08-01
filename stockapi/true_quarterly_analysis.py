# coding:utf-8
"""
真正的季度财务数据分析
使用'按报告期'参数获取真实的季度数据
"""

import os
import json
import time
import pickle
import logging
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 缓存配置
CACHE_FILE = 'stock_data_cache.pkl'
CACHE_DURATION_HOURS = 2  # 缓存有效期2小时

# 缓存功能说明:
# 1. 日线数据和总股本数据会自动缓存到 stock_data_cache.pkl 文件
# 2. 缓存有效期为2小时，过期后会重新获取数据
# 3. 缓存可以显著提高重复运行的速度
# 4. 如需强制刷新数据，可删除缓存文件

def get_stock_name_mapping():
    """
    获取所有A股股票代码和名称的映射关系（支持缓存）
    
    Returns:
        dict: 股票代码到股票名称的映射字典
    """
    # 尝试从缓存加载股票名称数据
    cached_data = load_cache('stock_names')
    if cached_data is not None:
        return cached_data
    
    logger = logging.getLogger(__name__)
    logger.info("开始获取所有A股股票代码和名称映射...")
    
    try:
        # 使用akshare获取所有A股股票代码和名称 <mcreference link="https://cloud.tencent.com/developer/article/1666899" index="1">1</mcreference>
        stock_info_df = ak.stock_info_a_code_name()
        
        # 创建代码到名称的映射字典
        stock_name_mapping = {}
        
        for _, row in stock_info_df.iterrows():
            code = row['code']
            name = row['name']
            
            # 为深圳和上海股票添加交易所后缀
            if code.startswith(('000', '002', '300', '301', '302')):
                full_code = f"{code}.SZ"
            elif code.startswith('6'):
                full_code = f"{code}.SH"
            else:
                full_code = code
            
            stock_name_mapping[full_code] = name
        
        logger.info(f"成功获取 {len(stock_name_mapping)} 只股票的名称映射")
        
        # 保存到缓存
        save_cache(stock_name_mapping, 'stock_names')
        
        return stock_name_mapping
        
    except Exception as e:
        logger.error(f"获取股票名称映射失败: {e}")
        return {}

def setup_logging():
    """
    设置日志系统
    """
    # 删除所有历史日志文件
    import glob
    log_pattern = "quarterly_analysis_*.log"
    old_log_files = glob.glob(log_pattern)
    for old_log in old_log_files:
        try:
            os.remove(old_log)
            print(f"已删除历史日志文件: {old_log}")
        except Exception as e:
            print(f"删除日志文件 {old_log} 失败: {e}")
    
    log_filename = f"quarterly_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 配置日志格式，只输出到文件
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统已启动，日志文件: {log_filename}")
    return logger

def save_cache(data, cache_type):
    """
    保存数据到缓存文件
    
    Args:
        data: 要缓存的数据
        cache_type: 缓存类型 ('daily_data' 或 'shares_data')
    """
    logger = logging.getLogger(__name__)
    cache_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                cache_data = pickle.load(f)
        except:
            cache_data = {}
    
    cache_data[cache_type] = {
        'data': data,
        'timestamp': time.time()
    }
    
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache_data, f)
    logger.info(f"💾 {cache_type} 数据已缓存")

def load_cache(cache_type):
    """
    从缓存文件加载数据
    
    Args:
        cache_type: 缓存类型 ('daily_data' 或 'shares_data')
    
    Returns:
        缓存的数据，如果缓存无效或不存在则返回None
    """
    logger = logging.getLogger(__name__)
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'rb') as f:
            cache_data = pickle.load(f)
        
        if cache_type not in cache_data:
            return None
        
        cached_item = cache_data[cache_type]
        cache_time = cached_item['timestamp']
        current_time = time.time()
        
        # 检查缓存是否过期（2小时 = 7200秒）
        if current_time - cache_time > CACHE_DURATION_HOURS * 3600:
            logger.info(f"⏰ {cache_type} 缓存已过期")
            return None
        
        logger.info(f"📂 使用 {cache_type} 缓存数据")
        return cached_item['data']
    
    except Exception as e:
        logger.error(f"❌ 加载 {cache_type} 缓存失败: {e}")
        return None

# 沪深300成分股列表（已过滤掉2010年之前没有交易数据的股票）
# 原始数量: 300, 有效数量: 176
CSI300_FILTERED_STOCKS = [
    '000001.SZ', '000002.SZ', '000063.SZ', '000100.SZ', '000157.SZ',
    '000301.SZ', '000338.SZ', '000408.SZ', '000425.SZ', '000538.SZ',
    '000568.SZ', '000596.SZ', '000617.SZ', '000625.SZ', '000630.SZ',
    '000651.SZ', '000661.SZ', '000708.SZ', '000725.SZ', '000768.SZ',
    '000776.SZ', '000786.SZ', '000792.SZ', '000800.SZ', '000807.SZ',
    '000858.SZ', '000876.SZ', '000895.SZ', '000938.SZ', '000963.SZ',
    '000975.SZ', '000977.SZ', '000983.SZ', '000999.SZ', '002001.SZ',
    '002027.SZ', '002028.SZ', '002049.SZ', '002050.SZ', '002074.SZ',
    '002129.SZ', '002142.SZ', '002179.SZ', '002180.SZ', '002230.SZ',
    '002236.SZ', '002241.SZ', '002252.SZ', '002304.SZ', '002311.SZ',
    '002352.SZ', '002371.SZ', '002415.SZ', '002422.SZ', '002459.SZ',
    '002460.SZ', '002463.SZ', '002466.SZ', '002475.SZ', '002493.SZ',
    '300014.SZ', '300015.SZ', '300033.SZ', '300059.SZ', '300122.SZ',
    '300124.SZ', '302132.SZ', '600000.SH', '600009.SH', '600010.SH',
    '600011.SH', '600015.SH', '600016.SH', '600018.SH', '600019.SH',
    '600026.SH', '600027.SH', '600028.SH', '600029.SH', '600030.SH',
    '600031.SH', '600036.SH', '600039.SH', '600048.SH', '600050.SH',
    '600061.SH', '600066.SH', '600085.SH', '600089.SH', '600104.SH',
    '600111.SH', '600115.SH', '600150.SH', '600160.SH', '600161.SH',
    '600176.SH', '600183.SH', '600188.SH', '600196.SH', '600219.SH',
    '600233.SH', '600276.SH', '600309.SH', '600332.SH', '600346.SH',
    '600362.SH', '600372.SH', '600377.SH', '600406.SH', '600415.SH',
    '600426.SH', '600436.SH', '600438.SH', '600460.SH', '600482.SH',
    '600489.SH', '600515.SH', '600519.SH', '600547.SH', '600570.SH',
    '600584.SH', '600585.SH', '600588.SH', '600600.SH', '600660.SH',
    '600674.SH', '600690.SH', '600741.SH', '600760.SH', '600795.SH',
    '600803.SH', '600809.SH', '600845.SH', '600875.SH', '600886.SH',
    '600887.SH', '600893.SH', '600900.SH', '600999.SH', '601006.SH',
    '601009.SH', '601088.SH', '601111.SH', '601117.SH', '601166.SH',
    '601169.SH', '601186.SH', '601288.SH', '601318.SH', '601328.SH',
    '601377.SH', '601390.SH', '601398.SH', '601600.SH', '601601.SH',
    '601607.SH', '601618.SH', '601628.SH', '601668.SH', '601688.SH',
    '601699.SH', '601766.SH', '601788.SH', '601808.SH', '601818.SH',
    '601857.SH', '601872.SH', '601877.SH', '601888.SH', '601898.SH',
    '601899.SH', '601919.SH', '601939.SH', '601988.SH', '601989.SH',
    '601998.SH'
]

def get_csi300_filtered_stocks():
    """
    获取沪深300成分股列表（已过滤掉2010年之前没有交易数据的股票）
    
    Returns:
        list: 包含176只股票代码的列表
    """
    return CSI300_FILTERED_STOCKS.copy()



def get_true_quarterly_profit_data(stock_code, start_year=2010, max_retries=3):
    """
    获取股票真正的季度盈利数据（使用'按报告期'参数，支持缓存）
    
    Args:
        stock_code: 股票代码（可以包含.SZ/.SH后缀）
        start_year: 开始年份
        max_retries: 最大重试次数
    
    Returns:
        dict: 包含季度数据的字典
    """
    # 尝试从缓存加载财务数据
    cached_data = load_cache('financial_data')
    if cached_data is not None and stock_code in cached_data:
        return cached_data[stock_code]
    
    # 提取6位数字代码（去掉.SZ/.SH后缀）
    if '.' in stock_code:
        clean_code = stock_code.split('.')[0]
    else:
        clean_code = stock_code
    
    logger = logging.getLogger(__name__)
    logger.info(f"获取 {stock_code} ({clean_code}) 的季度财务数据...")
    
    # 重试机制
    for attempt in range(max_retries):
        try:
            # 使用'按报告期'参数获取季度数据
            df = ak.stock_financial_benefit_ths(symbol=clean_code, indicator="按报告期")
            
            if df is None or df.empty:
                if attempt < max_retries - 1:
                    logger.warning(f"第{attempt + 1}次尝试失败，正在重试...")
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    return {'error': f'无法获取股票{stock_code}的财务数据（已重试{max_retries}次）'}
            
            # 确保报告期是字符串类型
            df['报告期'] = df['报告期'].astype(str)
            
            # 筛选指定年份之后的数据
            df_filtered = df[df['报告期'].str[:4].astype(int) >= start_year].copy()
            
            # 只保留季度数据（包含具体日期的报告期）
            quarterly_df = df_filtered[df_filtered['报告期'].str.contains('-', na=False)].copy()
            
            # 数据获取成功，处理季度数据
            if quarterly_df.empty:
                if attempt < max_retries - 1:
                    logger.warning(f"第{attempt + 1}次尝试获取到空数据，正在重试...")
                    time.sleep(1)
                    continue
                else:
                    return {'error': f'股票{stock_code}没有季度数据（已重试{max_retries}次）'}
            
            # 按报告期排序（最新的在前）
            quarterly_df = quarterly_df.sort_values('报告期', ascending=False)
            
            quarterly_data = []
            
            for _, row in quarterly_df.iterrows():
                report_period = row['报告期']
                
                try:
                    # 解析年份和季度
                    year = int(report_period[:4])
                    
                    if '-03-31' in report_period:
                        quarter = 'Q1'
                    elif '-06-30' in report_period:
                        quarter = 'Q2'
                    elif '-09-30' in report_period:
                        quarter = 'Q3'
                    elif '-12-31' in report_period:
                        quarter = 'Q4'
                    else:
                        continue  # 跳过非标准季度报告期
                    
                    # 提取累计财务数据
                    cumulative_net_profit = safe_convert_to_float(row.get('*净利润'))
                    cumulative_revenue = safe_convert_to_float(row.get('*营业总收入'))
                    cumulative_parent_net_profit = safe_convert_to_float(row.get('*归属于母公司所有者的净利润'))
                    diluted_eps = safe_convert_to_float(row.get('（二）稀释每股收益'))
                    
                    # 计算单季度净利润（从累计值转换为单季度值）
                    single_quarter_net_profit = cumulative_net_profit
                    single_quarter_revenue = cumulative_revenue
                    single_quarter_parent_net_profit = cumulative_parent_net_profit
                    
                    if quarter == 'Q2':
                        # Q2单季度 = Q2累计 - Q1累计
                        q1_period = f"{year}-03-31"
                        q1_row = quarterly_df[quarterly_df['报告期'] == q1_period]
                        if not q1_row.empty:
                            q1_net_profit = safe_convert_to_float(q1_row.iloc[0].get('*净利润'))
                            q1_revenue = safe_convert_to_float(q1_row.iloc[0].get('*营业总收入'))
                            q1_parent_net_profit = safe_convert_to_float(q1_row.iloc[0].get('*归属于母公司所有者的净利润'))
                            if q1_net_profit is not None and cumulative_net_profit is not None:
                                single_quarter_net_profit = cumulative_net_profit - q1_net_profit
                            if q1_revenue is not None and cumulative_revenue is not None:
                                single_quarter_revenue = cumulative_revenue - q1_revenue
                            if q1_parent_net_profit is not None and cumulative_parent_net_profit is not None:
                                single_quarter_parent_net_profit = cumulative_parent_net_profit - q1_parent_net_profit
                    elif quarter == 'Q3':
                        # Q3单季度 = Q3累计 - Q2累计
                        q2_period = f"{year}-06-30"
                        q2_row = quarterly_df[quarterly_df['报告期'] == q2_period]
                        if not q2_row.empty:
                            q2_net_profit = safe_convert_to_float(q2_row.iloc[0].get('*净利润'))
                            q2_revenue = safe_convert_to_float(q2_row.iloc[0].get('*营业总收入'))
                            q2_parent_net_profit = safe_convert_to_float(q2_row.iloc[0].get('*归属于母公司所有者的净利润'))
                            if q2_net_profit is not None and cumulative_net_profit is not None:
                                single_quarter_net_profit = cumulative_net_profit - q2_net_profit
                            if q2_revenue is not None and cumulative_revenue is not None:
                                single_quarter_revenue = cumulative_revenue - q2_revenue
                            if q2_parent_net_profit is not None and cumulative_parent_net_profit is not None:
                                single_quarter_parent_net_profit = cumulative_parent_net_profit - q2_parent_net_profit
                    elif quarter == 'Q4':
                        # Q4单季度 = Q4累计 - Q3累计
                        q3_period = f"{year}-09-30"
                        q3_row = quarterly_df[quarterly_df['报告期'] == q3_period]
                        if not q3_row.empty:
                            q3_net_profit = safe_convert_to_float(q3_row.iloc[0].get('*净利润'))
                            q3_revenue = safe_convert_to_float(q3_row.iloc[0].get('*营业总收入'))
                            q3_parent_net_profit = safe_convert_to_float(q3_row.iloc[0].get('*归属于母公司所有者的净利润'))
                            if q3_net_profit is not None and cumulative_net_profit is not None:
                                single_quarter_net_profit = cumulative_net_profit - q3_net_profit
                            if q3_revenue is not None and cumulative_revenue is not None:
                                single_quarter_revenue = cumulative_revenue - q3_revenue
                            if q3_parent_net_profit is not None and cumulative_parent_net_profit is not None:
                                single_quarter_parent_net_profit = cumulative_parent_net_profit - q3_parent_net_profit
                    
                    profit_data = {
                        '报告期': report_period,
                        '年份': year,
                        '季度': quarter,
                        '净利润': single_quarter_net_profit,  # 使用单季度净利润
                        '营业总收入': single_quarter_revenue,  # 使用单季度营收
                        '归属母公司净利润': single_quarter_parent_net_profit,  # 使用单季度归母净利润
                        '稀释每股收益': diluted_eps,
                        '累计净利润': cumulative_net_profit,  # 保留累计值用于调试
                    }
                    
                    quarterly_data.append(profit_data)
                    
                except Exception as e:
                    logger.error(f"处理报告期 {report_period} 时出错: {str(e)}")
                    continue
            
            # 计算滚动4季度累计盈利
            quarterly_data = calculate_rolling_profit(quarterly_data)
            
            # 数据处理成功，返回结果
            return {
                'stock_code': stock_code,
                'quarterly_data': quarterly_data,
                'total_quarters': len(quarterly_data)
            }
             
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"第{attempt + 1}次尝试出错: {str(e)}，正在重试...")
                time.sleep(1)  # 等待1秒后重试
                continue
            else:
                logger.error(f"❌ 获取 {stock_code} 季度数据失败: {str(e)}")
                return {'error': f'获取股票{stock_code}数据时出错（已重试{max_retries}次）: {str(e)}'}
    
    # 如果所有重试都失败了（理论上不应该到达这里）
    return {'error': f'获取股票{stock_code}数据失败，已重试{max_retries}次'}

def calculate_rolling_profit(quarterly_data):
    """
    计算滚动4季度累计盈利（包括本季度）
    
    Args:
        quarterly_data: 季度数据列表，按时间倒序排列
    
    Returns:
        list: 添加了滚动4季度累计盈利的季度数据
    """
    # 按时间正序排列以便计算滚动数据
    sorted_data = sorted(quarterly_data, key=lambda x: (x['年份'], x['季度']))
    
    for i, quarter in enumerate(sorted_data):
        # 计算当前季度及之前3个季度的累计盈利（共4个季度）
        rolling_profit = 0
        rolling_revenue = 0
        rolling_parent_profit = 0
        valid_quarters = 0
        
        # 向前查找最多4个季度的数据
        for j in range(max(0, i-3), i+1):
            if j < len(sorted_data):
                net_profit = sorted_data[j]['净利润']
                revenue = sorted_data[j]['营业总收入']
                parent_profit = sorted_data[j]['归属母公司净利润']
                
                if net_profit is not None:
                    rolling_profit += net_profit
                if revenue is not None:
                    rolling_revenue += revenue
                if parent_profit is not None:
                    rolling_parent_profit += parent_profit
                
                valid_quarters += 1
        
        # 只有当有完整的4个季度数据时才设置滚动数据，否则设置为None
        if valid_quarters >= 4:
            quarter['滚动4季度净利润'] = rolling_profit if rolling_profit != 0 else None
            quarter['滚动4季度营业收入'] = rolling_revenue if rolling_revenue != 0 else None
            quarter['滚动4季度归属母公司净利润'] = rolling_parent_profit if rolling_parent_profit != 0 else None
        else:
            quarter['滚动4季度净利润'] = None
            quarter['滚动4季度营业收入'] = None
            quarter['滚动4季度归属母公司净利润'] = None
        
        quarter['滚动季度数'] = valid_quarters
    
    # 恢复按时间倒序排列
    return sorted(sorted_data, key=lambda x: (x['年份'], x['季度']), reverse=True)

def get_quarter_end_date(year, quarter):
    """
    获取季度最后一天的日期
    
    Args:
        year: 年份
        quarter: 季度（Q1, Q2, Q3, Q4）
    
    Returns:
        str: 日期字符串 (YYYY-MM-DD)
    """
    if quarter == 'Q1':
        return f"{year}-03-31"
    elif quarter == 'Q2':
        return f"{year}-06-30"
    elif quarter == 'Q3':
        return f"{year}-09-30"
    elif quarter == 'Q4':
        return f"{year}-12-31"
    else:
        raise ValueError(f"无效的季度: {quarter}")

def get_stock_market_cap(stock_code, date, max_retries=3):
    """
    获取指定日期股票的市值
    
    Args:
        stock_code: 股票代码
        date: 日期字符串 (YYYY-MM-DD)
        max_retries: 最大重试次数
    
    Returns:
        float or None: 市值（元），如果获取失败返回None
    """
    # 提取6位数字代码
    if '.' in stock_code:
        clean_code = stock_code.split('.')[0]
    else:
        clean_code = stock_code
    
    for attempt in range(max_retries):
        try:
            # 获取股票基本信息（包含总股本）
            stock_info = ak.stock_individual_info_em(symbol=clean_code)
            if stock_info is None or stock_info.empty:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            
            # 获取总股本（万股）
            total_shares_wan = None
            for _, row in stock_info.iterrows():
                if row['item'] == '总股本':
                    total_shares_wan = safe_convert_to_float(row['value'])
                    break
            
            if total_shares_wan is None:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
            
            # 转换为股数（股）
            total_shares = total_shares_wan * 10000
            
            # 获取指定日期的股价
            try:
                # 尝试获取指定日期前后的历史数据
                start_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=10)).strftime('%Y%m%d')
                end_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=10)).strftime('%Y%m%d')
                
                hist_data = ak.stock_zh_a_hist(symbol=clean_code, period="daily", 
                                             start_date=start_date, end_date=end_date, adjust="")
                
                if hist_data is None or hist_data.empty:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return None
                
                # 查找最接近目标日期的交易日
                hist_data['日期'] = pd.to_datetime(hist_data['日期'])
                target_date = datetime.strptime(date, '%Y-%m-%d')
                
                # 找到小于等于目标日期的最近交易日
                valid_data = hist_data[hist_data['日期'] <= target_date]
                if valid_data.empty:
                    # 如果没有小于等于目标日期的数据，取最早的数据
                    valid_data = hist_data
                
                if valid_data.empty:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return None
                
                # 取最近的收盘价
                latest_data = valid_data.iloc[-1]
                close_price = float(latest_data['收盘'])
                
                # 计算市值
                market_cap = total_shares * close_price
                return market_cap
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            return None
    
    return None

def get_all_stocks_daily_data(stock_codes, start_date, end_date):
    """
    获取所有股票的日线数据（支持缓存）
    
    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        dict: 所有股票的日线数据
    """
    # 尝试从缓存加载数据
    cached_data = load_cache('daily_data')
    if cached_data is not None:
        return cached_data
    
    logger = logging.getLogger(__name__)
    logger.info(f"开始获取 {len(stock_codes)} 只股票的日线数据...")
    all_daily_data = {}
    success_count = 0
    failed_count = 0
    failed_examples = []
    
    for i, stock_code in enumerate(stock_codes, 1):
        if i % 20 == 0:
            logger.info(f"进度: {i}/{len(stock_codes)}")
        
        try:
            # 获取日线数据，akshare需要6位数字代码
            symbol = stock_code.split('.')[0]  # 去掉后缀，只保留6位数字
            daily_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                          start_date=start_date, end_date=end_date, adjust="")
            
            if not daily_data.empty:
                # 转换日期格式并设置为索引
                daily_data['日期'] = pd.to_datetime(daily_data['日期'])
                daily_data.set_index('日期', inplace=True)
                all_daily_data[stock_code] = daily_data
                success_count += 1
            else:
                failed_count += 1
                if len(failed_examples) < 5:
                    failed_examples.append(f"{stock_code}({symbol}): 空数据")
                
        except Exception as e:
            failed_count += 1
            if len(failed_examples) < 5:
                failed_examples.append(f"{stock_code}: {str(e)[:50]}")
            continue
        
        # 添加延迟避免请求过快
        time.sleep(0.05)
    
    logger.info(f"✅ 日线数据获取完成: 成功 {success_count}, 失败 {failed_count}")
    if failed_examples:
        logger.warning(f"失败示例: {failed_examples}")
    
    # 保存到缓存
    save_cache(all_daily_data, 'daily_data')
    return all_daily_data

def calculate_quarterly_market_cap_optimized(results, all_daily_data, shares_data, quarterly_stats):
    """
    基于已获取的日线数据和总股本数据计算每个季度所有股票的市值总和
    
    Args:
        results: 股票季度数据结果
        all_daily_data: 所有股票的日线数据
        quarterly_stats: 季度统计数据（用于计算市盈率）
        shares_data: 所有股票的总股本数据
    
    Returns:
        dict: 每个季度的市值总和
    """
    logger = logging.getLogger(__name__)
    logger.info("开始计算每个季度的市值总和...")
    
    # 收集所有季度
    all_quarters = set()
    for stock_code, stock_data in results.items():
        for quarter_data in stock_data['quarterly_data']:
            year = quarter_data['年份']
            quarter = quarter_data['季度']
            quarter_key = f"{year}-{quarter}"
            all_quarters.add((year, quarter, quarter_key))
    
    quarterly_market_caps = {}
    
    # 按季度计算市值
    for year, quarter, quarter_key in sorted(all_quarters, reverse=True):
        logger.info(f"计算 {quarter_key} 季度市值...")
        
        quarter_end_date = get_quarter_end_date(year, quarter)
        quarter_end_datetime = pd.to_datetime(quarter_end_date)
        
        total_market_cap = 0
        success_count = 0
        failed_count = 0
        debug_info = []
        
        # 获取该季度有数据的所有股票
        stocks_in_quarter = []
        for stock_code, stock_data in results.items():
            for quarter_data in stock_data['quarterly_data']:
                if quarter_data['年份'] == year and quarter_data['季度'] == quarter:
                    stocks_in_quarter.append(stock_code)
                    break
        
        logger.info(f"该季度有财务数据的股票数: {len(stocks_in_quarter)}")
        
        # 存储每只股票的详细市值信息
        stock_details = {}
        
        # 计算每只股票的市值
        for stock_code in stocks_in_quarter:
            try:
                # 检查是否有日线数据
                if stock_code not in all_daily_data:
                    failed_count += 1
                    debug_info.append(f"{stock_code}: 无日线数据")
                    continue
                
                # 检查是否有总股本数据
                if stock_code not in shares_data:
                    failed_count += 1
                    debug_info.append(f"{stock_code}: 无总股本数据")
                    continue
                
                daily_data = all_daily_data[stock_code]
                total_shares = shares_data[stock_code]
                
                # 找到季度最后一天或之前最近的交易日
                available_dates = daily_data.index[daily_data.index <= quarter_end_datetime]
                if len(available_dates) == 0:
                    failed_count += 1
                    debug_info.append(f"{stock_code}: 无对应日期的股价数据")
                    continue
                
                target_date = available_dates.max()
                close_price = daily_data.loc[target_date, '收盘']
                
                # 计算市值
                market_cap = close_price * total_shares
                total_market_cap += market_cap
                success_count += 1
                
                # 存储股票详细信息
                stock_details[stock_code] = {
                    'market_cap': market_cap,
                    'close_price': close_price,
                    'total_shares': total_shares,
                    'date': target_date.strftime('%Y-%m-%d')
                }
                
            except Exception as e:
                failed_count += 1
                debug_info.append(f"{stock_code}: 计算错误 - {str(e)}")
                continue
        
        # 计算市盈率 (PE ratio)
        pe_ratio = None
        if quarter_key in quarterly_stats:
            rolling_4q_profit = quarterly_stats[quarter_key].get('rolling_4q_profit', 0)
            if rolling_4q_profit > 0:
                pe_ratio = total_market_cap / rolling_4q_profit
        
        quarterly_market_caps[quarter_key] = {
            'total_market_cap': total_market_cap,
            'success_count': success_count,
            'failed_count': failed_count,
            'date': quarter_end_date,
            'pe_ratio': pe_ratio,
            'stock_details': stock_details
        }
        
        logger.info(f"✅ {quarter_key}: 总市值 {total_market_cap/1000000000000:.2f} 万亿元")
        logger.info(f"成功获取: {success_count}, 失败: {failed_count}")
        
        # 如果失败较多，显示部分调试信息
        if failed_count > success_count and len(debug_info) > 0:
            logger.warning(f"调试信息（前5个失败原因）: {debug_info[:5]}")
    
    return quarterly_market_caps

def get_total_shares_batch(stock_codes):
    """
    批量获取股票的总股本信息（支持缓存）
    
    Args:
        stock_codes: 股票代码列表
    
    Returns:
        dict: 股票代码到总股本的映射
    """
    # 尝试从缓存加载数据
    cached_data = load_cache('shares_data')
    if cached_data is not None:
        return cached_data
    
    logger = logging.getLogger(__name__)
    logger.info(f"开始获取 {len(stock_codes)} 只股票的总股本信息...")
    shares_data = {}
    success_count = 0
    failed_count = 0
    failed_examples = []
    
    for i, stock_code in enumerate(stock_codes, 1):
        if i % 20 == 0:
            logger.info(f"进度: {i}/{len(stock_codes)}")
        
        try:
            # 获取股票基本信息，akshare需要6位数字代码
            symbol = stock_code.split('.')[0]  # 去掉后缀，只保留6位数字
            stock_info = ak.stock_individual_info_em(symbol=symbol)
            
            # 查找总股本信息
            total_shares = None
            for _, row in stock_info.iterrows():
                item_name = str(row['item'])
                if '总股本' in item_name:
                    total_shares_value = row['value']
                    # 直接使用数值，因为akshare返回的已经是数字格式
                    if pd.notna(total_shares_value):
                        total_shares = float(total_shares_value)
                    break
            
            if total_shares is not None and total_shares > 0:
                shares_data[stock_code] = total_shares
                success_count += 1
            else:
                failed_count += 1
                if len(failed_examples) < 5:
                    failed_examples.append(f"{stock_code}: 总股本为空或0")
                
        except Exception as e:
            failed_count += 1
            if len(failed_examples) < 5:
                failed_examples.append(f"{stock_code}: {str(e)[:50]}")
            continue
        
        # 添加延迟避免请求过快
        time.sleep(0.05)
    
    logger.info(f"✅ 总股本获取完成: 成功 {success_count}, 失败 {failed_count}")
    if failed_examples:
        logger.warning(f"失败示例: {failed_examples}")
    
    # 保存到缓存
    save_cache(shares_data, 'shares_data')
    return shares_data

def safe_convert_to_float(value):
    """
    安全地将值转换为浮点数，处理带单位的字符串
    
    Args:
        value: 要转换的值
    
    Returns:
        float or None: 转换后的数值
    """
    if pd.isna(value) or value == '' or value == '--':
        return None
    
    try:
        # 如果已经是数字，直接返回
        if isinstance(value, (int, float)):
            return float(value)
        
        # 转换为字符串处理
        value_str = str(value).strip()
        
        # 移除逗号
        value_str = value_str.replace(',', '')
        
        # 处理带单位的情况
        if '亿' in value_str:
            number = float(value_str.replace('亿', ''))
            return number * 100000000  # 转换为元
        elif '万' in value_str:
            number = float(value_str.replace('万', ''))
            return number * 10000  # 转换为元
        else:
            return float(value_str)
    
    except (ValueError, TypeError):
        return None

def analyze_all_stocks_true_quarterly(start_year=2010):
    """
    分析所有股票的真实季度盈利情况
    
    Args:
        start_year: 开始年份
    
    Returns:
        dict: 分析结果
    """
    # 初始化日志系统
    logger = setup_logging()
    logger.info(f"开始分析沪深300股票的真实季度盈利情况（从{start_year}年开始）")
    
    # 尝试从缓存加载财务数据
    cached_financial_data = load_cache('financial_data')
    if cached_financial_data is not None:
        logger.info(f"📂 使用财务数据缓存，包含 {len(cached_financial_data)} 只股票")
        results = cached_financial_data
        success_count = len(results)
        failed_stocks = []
        total_stocks = len(results)
    else:
        stocks = get_csi300_filtered_stocks()
        total_stocks = len(stocks)
        
        results = {}
        success_count = 0
        failed_stocks = []
        
        for i, stock_code in enumerate(stocks, 1):
            logger.info(f"处理第 {i}/{total_stocks} 只股票: {stock_code}")
            
            # 获取季度数据
            data = get_true_quarterly_profit_data(stock_code, start_year)
            
            if 'error' in data:
                logger.error(f"❌ 失败: {data['error']}")
                failed_stocks.append(stock_code)
            else:
                logger.info(f"✅ 成功: 获取到 {data['total_quarters']} 个季度数据")
                results[stock_code] = data
                success_count += 1
            
            # 添加延迟避免请求过快
            time.sleep(0.2)
        
        # 保存财务数据到缓存
        if results:
            save_cache(results, 'financial_data')
    
    # 生成季度统计分析
    quarterly_stats = generate_quarterly_statistics(results)
    
    # 获取所有股票的日线数据（从2010年开始到现在）
    all_stock_codes = list(results.keys())
    start_date_str = f"{start_year}0101"  # akshare需要YYYYMMDD格式
    # 使用当前日期作为结束日期，但缓存键名使用日期范围而不是具体日期
    end_date_str = datetime.now().strftime('%Y%m%d')  # akshare需要YYYYMMDD格式
    all_daily_data = get_all_stocks_daily_data(all_stock_codes, start_date_str, end_date_str)
    
    # 批量获取所有股票的总股本信息
    shares_data = get_total_shares_batch(all_stock_codes)
    
    # 基于日线数据和总股本数据计算每个季度的市值总和
    quarterly_market_caps = calculate_quarterly_market_cap_optimized(results, all_daily_data, shares_data, quarterly_stats)
    
    # 构建清理后的简洁数据结构
    cleaned_data = {
        "metadata": {
            "analysis_type": "Quarterly Analysis",
            "start_year": start_year,
            "total_stocks": total_stocks,
            "total_quarters": len(quarterly_stats),
            "generated_at": datetime.now().strftime('%Y-%m-%d')
        },
        "quarterly_data": {}
    }
    
    # 合并每个季度的统计数据和市值数据
    for quarter in quarterly_stats.keys():
        quarter_stats = quarterly_stats.get(quarter, {})
        market_data = quarterly_market_caps.get(quarter, {})
        
        # 检查是否有有效的滚动4Q数据
        rolling_4q_count = quarter_stats.get('rolling_4q_count', 0)
        has_valid_rolling_data = rolling_4q_count > 0
        
        cleaned_data["quarterly_data"][quarter] = {
            "total_profit": quarter_stats.get('total_profit', 0),
            "total_revenue": quarter_stats.get('total_revenue', 0),
            "rolling_4q_profit": quarter_stats.get('rolling_4q_profit', 0) if has_valid_rolling_data else None,
            "rolling_4q_revenue": quarter_stats.get('rolling_4q_revenue', 0) if has_valid_rolling_data else None,
            "stock_count": quarter_stats.get('stock_count', 0),
            "profitable_count": quarter_stats.get('profitable_count', 0),
            "loss_count": quarter_stats.get('loss_count', 0),
            "profit_rate": quarter_stats.get('profit_rate', 0),
            "total_market_cap": market_data.get('total_market_cap', 0),
            "pe_ratio": market_data.get('pe_ratio', 0),
            "date": market_data.get('date', ''),
            "stock_details": market_data.get('stock_details', {})
        }

    logger.info("=== 真实季度分析完成 ===")
    logger.info(f"总股票数: {total_stocks}")
    logger.info(f"成功获取: {success_count}")
    logger.info(f"获取失败: {len(failed_stocks)}")
    
    # 保存清理后的简洁结果到JSON文件
    output_file = 'true_quarterly_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"清理后的分析结果已保存到: {output_file}")
    logger.info(f"数据结构: metadata + {len(cleaned_data['quarterly_data'])} 个季度数据")
    
    # 返回包含详细股票数据的完整结果
    return {
        'cleaned_data': cleaned_data,
        'results': results
    }

def generate_quarterly_statistics(results):
    """
    生成季度统计数据
    
    Args:
        results: 股票季度数据结果
    
    Returns:
        dict: 季度统计数据
    """
    from collections import defaultdict
    
    quarterly_stats = defaultdict(lambda: {
        'total_profit': 0,
        'total_revenue': 0,
        'profitable_count': 0,
        'loss_count': 0,
        'stock_count': 0,
        'rolling_4q_profit': 0,
        'rolling_4q_revenue': 0,
        'rolling_4q_parent_profit': 0,
        'rolling_4q_count': 0
    })
    
    # 按季度统计
    for stock_code, stock_data in results.items():
        for quarter_data in stock_data['quarterly_data']:
            year = quarter_data['年份']
            quarter = quarter_data['季度']
            quarter_key = f"{year}-{quarter}"
            
            net_profit = quarter_data['净利润']
            revenue = quarter_data['营业总收入']
            
            quarterly_stats[quarter_key]['stock_count'] += 1
            
            if net_profit is not None:
                quarterly_stats[quarter_key]['total_profit'] += net_profit
                if net_profit > 0:
                    quarterly_stats[quarter_key]['profitable_count'] += 1
                else:
                    quarterly_stats[quarter_key]['loss_count'] += 1
            
            if revenue is not None:
                quarterly_stats[quarter_key]['total_revenue'] += revenue
            
            # 累计滚动4季度数据
            rolling_profit = quarter_data.get('滚动4季度净利润')
            rolling_revenue = quarter_data.get('滚动4季度营业收入')
            rolling_parent_profit = quarter_data.get('滚动4季度归属母公司净利润')
            
            if rolling_profit is not None:
                quarterly_stats[quarter_key]['rolling_4q_profit'] += rolling_profit
                quarterly_stats[quarter_key]['rolling_4q_count'] += 1
            
            if rolling_revenue is not None:
                quarterly_stats[quarter_key]['rolling_4q_revenue'] += rolling_revenue
            
            if rolling_parent_profit is not None:
                quarterly_stats[quarter_key]['rolling_4q_parent_profit'] += rolling_parent_profit
    
    # 计算盈利率
    for quarter_key, stats in quarterly_stats.items():
        total_with_profit_data = stats['profitable_count'] + stats['loss_count']
        if total_with_profit_data > 0:
            stats['profit_rate'] = stats['profitable_count'] / total_with_profit_data * 100
        else:
            stats['profit_rate'] = 0
    
    # 转换为普通字典并排序
    sorted_stats = dict(sorted(quarterly_stats.items(), reverse=True))
    
    return sorted_stats




def print_detailed_stock_info(analysis_result, logger, target_quarters):
    """
    打印指定季度每只股票的详细市值和净利润信息
    
    Args:
        analysis_result: 分析结果（包含cleaned_data和results）
        logger: 日志记录器
        target_quarters: 目标季度列表，如['2010-Q4', '2011-Q4']
    """
    results = analysis_result.get('results', {})
    quarterly_data = analysis_result.get('cleaned_data', {}).get('quarterly_data', {})
    
    for quarter_key in target_quarters:
        try:
            if quarter_key not in quarterly_data:
                logger.info(f"未找到季度 {quarter_key} 的数据")
                continue
            
            logger.info(f"开始处理季度 {quarter_key}")
            logger.info(f"\n=== {quarter_key} 详细股票信息 ===")
            logger.info(f"{'股票代码':<12} {'净利润(万元)':<15} {'市值(亿元)':<15} {'收盘价(元)':<12} {'总股本(万股)':<15}")
            logger.info("-" * 80)
            
            year, quarter = quarter_key.split('-')
            year = int(year)
            quarter_num = int(quarter[1:])
            
            total_market_cap_check = 0
            total_profit_check = 0
            stock_count = 0
            
            # 获取该季度的市值详情
            quarter_stats = quarterly_data.get(quarter_key, {})
            stock_details = quarter_stats.get('stock_details', {})
            
            # 收集所有股票数据用于排序
            stock_data_list = []
            
            # 遍历所有股票，找到该季度的数据
            for stock_code, stock_info in results.items():
                quarterly_list = stock_info.get('quarterly_data', [])
                
                # 查试该季度的数据
                quarter_data = None
                quarter_str = f'Q{quarter_num}'  # 转换为Q1, Q2, Q3, Q4格式
                for q_data in quarterly_list:
                    if q_data.get('年份') == year and q_data.get('季度') == quarter_str:
                        quarter_data = q_data
                        break
                
                if quarter_data:
                    net_profit = quarter_data.get('净利润', 0) or 0  # 单季度净利润，单位：万元
                    
                    # 获取市值信息
                    if stock_code in stock_details:
                        market_cap_info = stock_details[stock_code]
                        market_cap_yi = market_cap_info['market_cap'] / 100000000  # 转换为亿元
                        close_price = market_cap_info['close_price']
                        total_shares_wan = market_cap_info['total_shares'] / 10000  # 转换为万股
                        
                        stock_data_list.append({
                            'stock_code': stock_code,
                            'net_profit': net_profit,
                            'market_cap_yi': market_cap_yi,
                            'close_price': close_price,
                            'total_shares_wan': total_shares_wan,
                            'market_cap_raw': market_cap_info['market_cap']
                        })
                        
                        total_market_cap_check += market_cap_info['market_cap']
                        total_profit_check += net_profit * 10000  # 转换为元
                        stock_count += 1
                    else:
                        # 如果没有市值数据，只显示净利润
                        stock_data_list.append({
                            'stock_code': stock_code,
                            'net_profit': net_profit,
                            'market_cap_yi': 0,
                            'close_price': 'N/A',
                            'total_shares_wan': 'N/A',
                            'market_cap_raw': 0
                        })
                        total_profit_check += net_profit * 10000  # 转换为元
                        stock_count += 1
            
            # 按市值从大到小排序
            stock_data_list.sort(key=lambda x: x['market_cap_raw'], reverse=True)
            
            # 打印排序后的股票信息
            for stock_data in stock_data_list:
                if stock_data['close_price'] == 'N/A':
                    logger.info(f"{stock_data['stock_code']:<12} {stock_data['net_profit']:<15.0f} {'N/A':<15} {'N/A':<12} {'N/A':<15}")
                else:
                    logger.info(f"{stock_data['stock_code']:<12} {stock_data['net_profit']:<15.0f} {stock_data['market_cap_yi']:<15.2f} {stock_data['close_price']:<12.2f} {stock_data['total_shares_wan']:<15.0f}")
            
            # 显示汇总信息
            logger.info("-" * 80)
            logger.info(f"汇总: 股票数={stock_count}, 总净利润={total_profit_check/100000000:.0f}亿元, 总市值={total_market_cap_check/1000000000000:.2f}万亿元")
            
            # 与季度统计数据对比
            quarter_stats = quarterly_data.get(quarter_key, {})
            official_profit = quarter_stats.get('total_profit', 0) / 100000000
            official_market_cap = quarter_stats.get('total_market_cap', 0) / 1000000000000
            official_stock_count = quarter_stats.get('stock_count', 0)
            
            logger.info(f"官方统计: 股票数={official_stock_count}, 总净利润={official_profit:.0f}亿元, 总市值={official_market_cap:.2f}万亿元")
        
        except Exception as e:
            logger.error(f"处理季度 {quarter_key} 时发生错误: {str(e)}")
            continue


def print_quarterly_summary(analysis_result, logger):
    """
    打印季度分析摘要
    
    Args:
        analysis_result: 分析结果（包含cleaned_data和results）
        logger: 日志记录器
    """
    logger.info("=== 真实季度盈利分析摘要 ===")
    
    quarterly_data = analysis_result['cleaned_data']['quarterly_data']
    
    logger.info("所有季度盈利情况:")
    logger.info(f"{'季度':<12} {'总净利润(亿)':<16} {'总营收(万亿)':<16} {'滚动4Q净利润(亿)':<20} {'总市值(万亿)':<16} {'市盈率':<11} {'盈利率':<11} {'股票数':<8}")
    logger.info("-" * 130)
    
    # 按季度倒序排列，显示所有季度
    sorted_quarters = sorted(quarterly_data.keys(), reverse=True)
    for i, quarter_key in enumerate(sorted_quarters):
        # 显示所有季度数据
        
        stats = quarterly_data[quarter_key]
        total_profit_yi = stats['total_profit'] / 100000000
        total_revenue_wanyi = stats['total_revenue'] / 1000000000000
        rolling_4q_profit_yi = stats['rolling_4q_profit'] / 100000000 if stats['rolling_4q_profit'] is not None else 0
        profit_rate = stats['profit_rate']
        stock_count = stats['stock_count']
        total_market_cap_wanyi = stats['total_market_cap'] / 1000000000000
        pe_ratio = stats['pe_ratio']
        pe_ratio_str = f"{pe_ratio:.1f}" if pe_ratio is not None and pe_ratio > 0 else "N/A"
        rolling_4q_profit_str = f"{rolling_4q_profit_yi:.0f}" if stats['rolling_4q_profit'] is not None else "N/A"
        
        logger.info(f"{quarter_key:<12} {total_profit_yi:<16.0f} {total_revenue_wanyi:<16.1f} {rolling_4q_profit_str:<20} {total_market_cap_wanyi:<16.1f} {pe_ratio_str:<11} {profit_rate:<10.1f}% {stock_count:<8}")
    
    # 详细股票信息将在main函数中单独调用
    
    # 显示市值统计摘要
    if quarterly_data:
        logger.info("=== 市值统计摘要 ===")
        total_quarters_with_market_cap = len(quarterly_data)
        logger.info(f"已计算市值的季度数: {total_quarters_with_market_cap}")
        
        latest_quarter = sorted_quarters[0]
        latest_data = quarterly_data[latest_quarter]
        logger.info(f"最新季度 ({latest_quarter}):")
        logger.info(f"  总市值: {latest_data['total_market_cap']/1000000000000:.2f} 万亿元")
        logger.info(f"  股票数: {latest_data['stock_count']}")
        logger.info(f"  市盈率: {latest_data['pe_ratio']:.2f}")
        logger.info(f"  数据日期: {latest_data['date']}")

def print_market_cap_trend_analysis(analysis_result, logger, stock_name_mapping=None):
    """
    打印2010到2011年的市值趋势变化表
    
    Args:
        analysis_result: 分析结果数据
        logger: 日志记录器
        stock_name_mapping: 股票代码到名称的映射字典
    """
    logger.info("")
    logger.info("=== 2010-2011年市值趋势变化分析 ===")
    if stock_name_mapping:
        logger.info("股票代码         股票名称              2010-Q4市值(亿)    2011-Q4市值(亿)    变化值(亿)       变化百分比(%)")
        logger.info("-" * 120)
    else:
        logger.info("股票代码         2010-Q4市值(亿)    2011-Q4市值(亿)    变化值(亿)       变化百分比(%)")
        logger.info("-" * 100)
    
    # 获取季度数据
    quarterly_data = analysis_result.get('cleaned_data', {}).get('quarterly_data', {})
    
    if not quarterly_data:
        logger.info("缺少季度数据")
        return
    
    # 获取2010-Q4和2011-Q4的市值详情
    quarter_2010_q4 = quarterly_data.get('2010-Q4', {})
    quarter_2011_q4 = quarterly_data.get('2011-Q4', {})
    
    stock_details_2010 = quarter_2010_q4.get('stock_details', {})
    stock_details_2011 = quarter_2011_q4.get('stock_details', {})
    
    logger.info(f"2010-Q4有市值数据的股票: {len(stock_details_2010)}只")
    logger.info(f"2011-Q4有市值数据的股票: {len(stock_details_2011)}只")
    
    if not stock_details_2010 or not stock_details_2011:
        logger.info("缺少2010-Q4或2011-Q4的市值数据")
        return
    
    # 收集所有股票的市值变化数据
    trend_data = []
    
    # 找到两个季度都有数据的股票
    common_stocks = set(stock_details_2010.keys()) & set(stock_details_2011.keys())
    logger.info(f"两个季度都有数据的股票: {len(common_stocks)}只")
    
    if not common_stocks:
        logger.info("没有找到同时包含2010-Q4和2011-Q4市值数据的股票")
        return
    
    for stock_code in common_stocks:
        market_cap_2010 = stock_details_2010[stock_code]['market_cap'] / 100000000  # 转换为亿元
        market_cap_2011 = stock_details_2011[stock_code]['market_cap'] / 100000000  # 转换为亿元
        
        # 计算变化值和百分比
        change_value = market_cap_2011 - market_cap_2010
        change_percent = (change_value / market_cap_2010) * 100 if market_cap_2010 > 0 else 0
        
        trend_data.append({
            'stock_code': stock_code,
            'market_cap_2010': market_cap_2010,
            'market_cap_2011': market_cap_2011,
            'change_value': change_value,
            'change_percent': change_percent
        })
    
    if len(trend_data) == 0:
        logger.info("没有找到同时包含2010-Q4和2011-Q4市值数据的股票")
        return
    
    # 按2010年市值排序（从大到小）
    trend_data.sort(key=lambda x: x['market_cap_2010'], reverse=True)
    
    # 打印所有股票的变化情况
    for i, data in enumerate(trend_data):
        stock_code = data['stock_code']
        market_cap_2010 = data['market_cap_2010']
        market_cap_2011 = data['market_cap_2011']
        change_value = data['change_value']
        change_percent = data['change_percent']
        
        # 获取股票名称
        stock_name = stock_name_mapping.get(stock_code, "未知") if stock_name_mapping else ""
        
        # 格式化输出
        change_sign = "+" if change_value >= 0 else ""
        percent_sign = "+" if change_percent >= 0 else ""
        
        if stock_name_mapping:
            # 包含股票名称的格式
            logger.info(f"{stock_code:<12} {stock_name:<20} {market_cap_2010:>12.2f}      {market_cap_2011:>12.2f}      {change_sign}{change_value:>10.2f}      {percent_sign}{change_percent:>8.1f}%")
        else:
            # 原始格式（不包含股票名称）
            logger.info(f"{stock_code:<12} {market_cap_2010:>12.2f}      {market_cap_2011:>12.2f}      {change_sign}{change_value:>10.2f}      {percent_sign}{change_percent:>8.1f}%")
    
    # 统计汇总
    total_market_cap_2010 = sum(d['market_cap_2010'] for d in trend_data)
    total_market_cap_2011 = sum(d['market_cap_2011'] for d in trend_data)
    total_change = total_market_cap_2011 - total_market_cap_2010
    total_change_percent = (total_change / total_market_cap_2010) * 100 if total_market_cap_2010 > 0 else 0
    
    # 计算上涨和下跌的股票数量
    rising_stocks = [d for d in trend_data if d['change_percent'] > 0]
    falling_stocks = [d for d in trend_data if d['change_percent'] < 0]
    unchanged_stocks = len(trend_data) - len(rising_stocks) - len(falling_stocks)
    
    # 打印统计信息
    logger.info("-" * 100)
    logger.info(f"统计信息:")
    logger.info(f"2010-Q4总市值: {total_market_cap_2010/10000:.2f}万亿元")
    logger.info(f"2011-Q4总市值: {total_market_cap_2011/10000:.2f}万亿元")
    logger.info(f"总变化值: {total_change/10000:+.2f}万亿元 ({total_change_percent:+.2f}%)")
    logger.info("")
    logger.info("=== 涨跌分布统计 ===")
    logger.info(f"上涨股票: {len(rising_stocks)}只 ({len(rising_stocks)/len(trend_data)*100:.1f}%)")
    logger.info(f"下跌股票: {len(falling_stocks)}只 ({len(falling_stocks)/len(trend_data)*100:.1f}%)")
    logger.info(f"持平股票: {unchanged_stocks}只 ({unchanged_stocks/len(trend_data)*100:.1f}%)")
    
    if rising_stocks:
        avg_rise = sum(d['change_percent'] for d in rising_stocks) / len(rising_stocks)
        logger.info(f"上涨股票平均涨幅: {avg_rise:.1f}%")
    
    if falling_stocks:
        avg_fall = sum(d['change_percent'] for d in falling_stocks) / len(falling_stocks)
        logger.info(f"下跌股票平均跌幅: {avg_fall:.1f}%")
    
    logger.info("-" * 100)

def main():
    """
    主函数
    """
    # 分析真实季度数据
    full_result = analyze_all_stocks_true_quarterly(start_year=2010)
    analysis_result = full_result['cleaned_data']
    
    # 获取logger实例
    logger = logging.getLogger(__name__)
    
    # 获取股票名称映射
    stock_name_mapping = get_stock_name_mapping()
    
    # 打印详细股票信息
    print_detailed_stock_info(full_result, logger, ['2010-Q4', '2011-Q4'])
    
    # 打印2010-2011年市值趋势变化分析
    print_market_cap_trend_analysis(full_result, logger, stock_name_mapping)
    
    # 打印摘要
    print_quarterly_summary(full_result, logger)
    
    logger.info("真实季度分析完成！")
    logger.info("主要改进:")
    logger.info("• 使用'按报告期'参数获取真正的季度数据")
    logger.info("• 数据包含Q1、Q2、Q3、Q4四个季度的详细信息")
    logger.info("• 可以分析季度间的盈利变化趋势")
    logger.info("• 提供更精确的季度盈利统计")

if __name__ == "__main__":
    main()