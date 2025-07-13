"""
A股财务数据模块 - 提供A股财务数据相关的获取函数
"""
import os
import json
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from .cache_utils import CACHE_DIR, read_cache, save_cache, is_cache_expired
from .common_utils import convert_to_float

# 定义股票财务数据缓存目录
STOCK_FINANCE_CACHE_DIR = os.path.join(CACHE_DIR, 'stock_finance')
os.makedirs(STOCK_FINANCE_CACHE_DIR, exist_ok=True)

def get_stock_financial_data(stock_code):
    """
    获取股票财务数据，使用缓存机制
    
    Args:
        stock_code: 股票代码
        
    Returns:
        dict: 包含股票财务数据的字典
    """
    # 检查股票代码格式
    if not stock_code.isdigit() or len(stock_code) != 6:
        return {'error': '请输入正确的股票代码（6位数字）'}
    
    # 构建缓存文件路径
    cache_file = os.path.join(STOCK_FINANCE_CACHE_DIR, f'{stock_code}_finance.json')
    
    # 检查缓存是否存在且有效
    cache_data = read_cache(cache_file)
    if cache_data and not is_cache_expired(cache_data.get('timestamp', 0)):
        print(f"使用缓存的股票{stock_code}财务数据")
        return cache_data.get('data')
    
    # 缓存不存在或已过期，重新获取数据
    print(f"重新获取股票{stock_code}财务数据")
    data = _fetch_stock_financial_data(stock_code)
    
    # 保存到缓存
    save_cache(cache_file, data)
    
    return data

def _get_stock_name(stock_code):
    """
    获取股票名称的函数，尝试多种方法
    
    Args:
        stock_code: 股票代码
        
    Returns:
        str: 股票名称
    """
    try:
        # 方法1：使用stock_zh_a_spot_em接口获取当前A股行情数据
        spot_df = ak.stock_zh_a_spot_em()
        # 确保代码格式一致（有些接口返回的代码可能带有市场前缀）
        stock_row = spot_df[spot_df['代码'] == stock_code]
        if not stock_row.empty:
            return stock_row.iloc[0]['名称']
    except Exception as e:
        print(f"方法1获取股票名称失败: {e}")
    
    try:
        # 方法2：使用stock_lhb_detail_em接口获取龙虎榜数据
        # 使用最近一个月的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        lhb_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
        stock_row = lhb_df[lhb_df['代码'] == stock_code]
        if not stock_row.empty:
            return stock_row.iloc[0]['名称']
    except Exception as e:
        print(f"方法2获取股票名称失败: {e}")
    
    try:
        # 方法3：使用stock_zh_a_hist接口获取历史行情数据
        # 只获取最近一天的数据
        today = datetime.now().strftime('%Y%m%d')
        one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date=one_month_ago, end_date=today, adjust="")
        if not hist_df.empty and '名称' in hist_df.columns:
            return hist_df.iloc[0]['名称']
        # 如果没有名称列，但有股票代码列，可以尝试从其他列获取信息
        elif not hist_df.empty:
            # 尝试从其他接口获取名称
            try:
                # 使用stock_individual_info_em接口
                stock_info = ak.stock_individual_info_em(symbol=stock_code)
                if not stock_info.empty:
                    # 股票名称通常在第二列
                    return stock_info.iloc[0, 1]
            except:
                pass
    except Exception as e:
        print(f"方法3获取股票名称失败: {e}")
    
    # 所有方法都失败，返回一个更友好的格式
    return f"股票{stock_code}"

def _fetch_stock_financial_data(stock_code):
    """从API获取股票财务数据"""
    try:
        # 获取资产负债表数据
        debt_df = ak.stock_financial_debt_ths(symbol=stock_code, indicator="按年度")  # 改为按年度
        
        # 获取利润表数据
        benefit_df = ak.stock_financial_benefit_ths(symbol=stock_code, indicator="按年度")  # 改为按年度
        
        # 获取现金流量表数据
        cash_df = ak.stock_financial_cash_ths(symbol=stock_code, indicator="按年度")
        
        # 确保报告期列是字符串类型
        debt_df['报告期'] = debt_df['报告期'].astype(str)
        benefit_df['报告期'] = benefit_df['报告期'].astype(str)
        cash_df['报告期'] = cash_df['报告期'].astype(str)

        
        # 保留原始的资产负债表数据用于完整展示
        debt_df_original = debt_df.copy()
        
        # 处理资产负债表数据，计算负债率，并提取实收资本（用于概览展示）
        # 检查是否存在实收资本列
        has_registered_capital = '实收资本（或股本）' in debt_df.columns
        
        if has_registered_capital:
            debt_df_summary = debt_df[['报告期', '*资产合计', '*负债合计', '实收资本（或股本）']].copy()
            debt_df_summary['负债率'] = debt_df_summary.apply(
                lambda x: convert_to_float(x['*负债合计']) / convert_to_float(x['*资产合计']) * 100 
                if convert_to_float(x['*资产合计']) != 0 else 0, 
                axis=1
            )
            debt_df_summary['实收资本'] = debt_df_summary.apply(
                lambda x: convert_to_float(x['实收资本（或股本）']), 
                axis=1
            )
            debt_df_summary = debt_df_summary[['报告期', '负债率', '实收资本']]
        else:
            debt_df_summary = debt_df[['报告期', '*资产合计', '*负债合计']].copy()
            debt_df_summary['负债率'] = debt_df_summary.apply(
                lambda x: convert_to_float(x['*负债合计']) / convert_to_float(x['*资产合计']) * 100 
                if convert_to_float(x['*资产合计']) != 0 else 0, 
                axis=1
            )
            debt_df_summary['实收资本'] = None
            debt_df_summary = debt_df_summary[['报告期', '负债率', '实收资本']]
        
        # 保留原始的利润表数据用于完整展示
        benefit_df_original = benefit_df.copy()
        
        # 处理利润表数据，计算净利率、毛利率和提取稀释每股收益、研发投入（用于概览展示）
        # 检查必要的列是否存在
        required_columns = ['报告期', '*净利润', '*营业总收入']
        
        # 检查是否存在稀释每股收益列、归属于母公司所有者的净利润列和研发费用列
        has_diluted_eps = '（二）稀释每股收益' in benefit_df.columns
        has_parent_net_profit = '归属于母公司所有者的净利润' in benefit_df.columns
        has_rd_expense = '研发费用' in benefit_df.columns
        
        if not all(col in benefit_df.columns for col in required_columns):
            print(f"利润表缺少必要的列: {[col for col in required_columns if col not in benefit_df.columns]}")
            # 只计算存在的列
            benefit_df_summary = benefit_df[['报告期', '*净利润', '*营业总收入']].copy()
            benefit_df_summary['净利率'] = benefit_df_summary.apply(
                lambda x: convert_to_float(x['*净利润']) / convert_to_float(x['*营业总收入']) * 100 
                if convert_to_float(x['*营业总收入']) != 0 else 0, 
                axis=1
            )
            # 由于缺少营业成本，无法计算毛利率
            benefit_df_summary['毛利率'] = None
            # 添加稀释每股收益列，但值为None
            benefit_df_summary['稀释每股收益'] = None
            # 添加归属于母公司所有者的净利润列，但值为None
            benefit_df_summary['归属母公司净利润'] = None
        else:
            # 检查是否有营业成本列
            if '其中：营业成本' in benefit_df.columns:
                # 选择需要的列，如果有稀释每股收益列、归属于母公司所有者的净利润列和研发费用列，也一并选择
                cols_to_select = ['报告期', '*净利润', '*营业总收入', '其中：营业成本']
                if has_diluted_eps:
                    cols_to_select.append('（二）稀释每股收益')
                if has_parent_net_profit:
                    cols_to_select.append('归属于母公司所有者的净利润')
                if has_rd_expense:
                    cols_to_select.append('研发费用')
                
                benefit_df_summary = benefit_df[cols_to_select].copy()
                
                benefit_df_summary['净利率'] = benefit_df_summary.apply(
                    lambda x: convert_to_float(x['*净利润']) / convert_to_float(x['*营业总收入']) * 100 
                    if convert_to_float(x['*营业总收入']) != 0 else 0, 
                    axis=1
                )
                benefit_df_summary['毛利率'] = benefit_df_summary.apply(
                    lambda x: ((convert_to_float(x['*营业总收入']) - convert_to_float(x['其中：营业成本'])) 
                            / convert_to_float(x['*营业总收入'])) * 100 
                    if convert_to_float(x['*营业总收入']) != 0 else 0, 
                    axis=1
                )
                
                # 处理稀释每股收益
                if has_diluted_eps:
                    benefit_df_summary['稀释每股收益'] = benefit_df_summary.apply(
                        lambda x: convert_to_float(x['（二）稀释每股收益']), 
                        axis=1
                    )
                else:
                    benefit_df_summary['稀释每股收益'] = None
                
                # 处理归属于母公司所有者的净利润
                if has_parent_net_profit:
                    benefit_df_summary['归属母公司净利润'] = benefit_df_summary.apply(
                        lambda x: convert_to_float(x['归属于母公司所有者的净利润']), 
                        axis=1
                    )
                else:
                    benefit_df_summary['归属母公司净利润'] = None
                
                # 处理研发投入
                if has_rd_expense:
                    benefit_df_summary['研发投入'] = benefit_df_summary.apply(
                        lambda x: convert_to_float(x['研发费用']), 
                        axis=1
                    )
                else:
                    benefit_df_summary['研发投入'] = None
            else:
                print("缺少'其中：营业成本'列，无法计算毛利率")
                # 选择需要的列，如果有稀释每股收益列、归属于母公司所有者的净利润列和研发费用列，也一并选择
                cols_to_select = ['报告期', '*净利润', '*营业总收入']
                if has_diluted_eps:
                    cols_to_select.append('（二）稀释每股收益')
                if has_parent_net_profit:
                    cols_to_select.append('归属于母公司所有者的净利润')
                if has_rd_expense:
                    cols_to_select.append('研发费用')
                
                benefit_df_summary = benefit_df[cols_to_select].copy()
                
                benefit_df_summary['净利率'] = benefit_df_summary.apply(
                    lambda x: convert_to_float(x['*净利润']) / convert_to_float(x['*营业总收入']) * 100 
                    if convert_to_float(x['*营业总收入']) != 0 else 0, 
                    axis=1
                )
                benefit_df_summary['毛利率'] = None
                
                # 处理稀释每股收益
                if has_diluted_eps:
                    benefit_df_summary['稀释每股收益'] = benefit_df_summary.apply(
                        lambda x: convert_to_float(x['（二）稀释每股收益']), 
                        axis=1
                    )
                else:
                    benefit_df_summary['稀释每股收益'] = None
                
                # 处理归属于母公司所有者的净利润
                if has_parent_net_profit:
                    benefit_df_summary['归属母公司净利润'] = benefit_df_summary.apply(
                        lambda x: convert_to_float(x['归属于母公司所有者的净利润']), 
                        axis=1
                    )
                else:
                    benefit_df_summary['归属母公司净利润'] = None
                
                # 处理研发投入
                if has_rd_expense:
                    benefit_df_summary['研发投入'] = benefit_df_summary.apply(
                        lambda x: convert_to_float(x['研发费用']), 
                        axis=1
                    )
                else:
                    benefit_df_summary['研发投入'] = None
        
        # 选择需要的列
        benefit_df_summary = benefit_df_summary[['报告期', '净利率', '毛利率', '稀释每股收益', '归属母公司净利润', '研发投入']]
        
        # 合并数据
        try:
            merged_df = pd.merge(debt_df_summary, benefit_df_summary, on='报告期', how='outer')
        except Exception as e:
            print(f"合并数据出错: {e}")
            # 尝试使用concat方法合并
            print("尝试使用concat方法合并数据...")
            debt_df_summary.set_index('报告期', inplace=True)
            benefit_df_summary.set_index('报告期', inplace=True)
            merged_df = pd.concat([debt_df_summary, benefit_df_summary], axis=1)
            merged_df.reset_index(inplace=True)
        
        # 按报告期排序并获取最近10个年度的数据
        merged_df = merged_df.sort_values('报告期', ascending=False).head(10)
        
        # 转换为字典列表
        result = []
        for _, row in merged_df.iterrows():
            result.append({
                '报告期': row['报告期'],
                '负债率': round(row['负债率'], 2) if not pd.isna(row['负债率']) else None,
                '净利率': round(row['净利率'], 2) if not pd.isna(row['净利率']) else None,
                '毛利率': round(row['毛利率'], 2) if not pd.isna(row['毛利率']) else None,
                '稀释每股收益': round(row['稀释每股收益'], 4) if not pd.isna(row['稀释每股收益']) else None,
                '归属母公司净利润': round(row['归属母公司净利润'], 2) if not pd.isna(row['归属母公司净利润']) else None,
                '实收资本': round(row['实收资本'], 2) if not pd.isna(row['实收资本']) else None,
                '研发投入': round(row['研发投入'], 2) if not pd.isna(row['研发投入']) else None
            })
        
        # 获取股票名称
        stock_name = _get_stock_name(stock_code)
        
        # 处理完整的财务报表数据（获取所有报告期的数据）
        # 获取所有报告期的交集
        common_periods = set(debt_df_original['报告期']) & set(benefit_df_original['报告期']) & set(cash_df['报告期'])
        common_periods = sorted(list(common_periods), reverse=True)  # 获取所有财务周期
        
        # 构建完整的财务报表数据
        full_financial_data = []
        for period in common_periods:
            # 资产负债表数据（使用原始数据）
            debt_row = debt_df_original[debt_df_original['报告期'] == period]
            # 利润表数据（使用原始数据）
            benefit_row = benefit_df_original[benefit_df_original['报告期'] == period]
            # 现金流量表数据
            cash_row = cash_df[cash_df['报告期'] == period]
            
            period_data = {'报告期': period}
            
            # 添加资产负债表数据
            if not debt_row.empty:
                for col in debt_row.columns:
                    if col != '报告期':
                        period_data[f'资产负债表_{col}'] = debt_row.iloc[0][col]
            
            # 添加利润表数据
            if not benefit_row.empty:
                for col in benefit_row.columns:
                    if col != '报告期':
                        period_data[f'利润表_{col}'] = benefit_row.iloc[0][col]
            
            # 添加现金流量表数据
            if not cash_row.empty:
                for col in cash_row.columns:
                    if col != '报告期':
                        period_data[f'现金流量表_{col}'] = cash_row.iloc[0][col]
            
            full_financial_data.append(period_data)
        
        # 处理NaN值，将其转换为None以确保JSON序列化正常
        def clean_nan_values(obj):
            if isinstance(obj, dict):
                return {k: clean_nan_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan_values(item) for item in obj]
            elif isinstance(obj, float) and (obj != obj):  # 检查NaN
                return None
            else:
                return obj
        
        result_data = {
            'code': stock_code,
            'name': stock_name,
            'financial_data': result,  # 保留原有的简化数据用于图表展示
            'full_financial_data': full_financial_data  # 新增完整的财务报表数据
        }
        
        # 清理结果中的NaN值
        return clean_nan_values(result_data)
    except Exception as e:
        print(f"获取股票{stock_code}财务数据出错: {e}")
        # 返回空数据
        return {
            'code': stock_code,
            'name': "获取失败",
            'financial_data': [],
            'full_financial_data': []
        }