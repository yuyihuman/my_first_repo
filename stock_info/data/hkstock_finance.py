"""
港股财务数据模块 - 提供港股财务数据相关的获取函数
"""
import os
import json
import time
import akshare as ak
import pandas as pd
from datetime import datetime
from .cache_utils import CACHE_DIR  # 确保导入CACHE_DIR

def get_hkstock_finance(stock_code):
    """获取港股财务数据"""
    # 确保股票代码格式正确（5位数字）
    stock_code = stock_code.zfill(5)
    
    # 检查缓存
    # 修改缓存路径，使用CACHE_DIR常量
    cache_dir = os.path.join(CACHE_DIR, 'hkstock_finance')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{stock_code}_finance.json")
    
    # 如果缓存存在且未过期（24小时内），则使用缓存
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期（24小时）
        if time.time() - cache_data.get('timestamp', 0) < 86400:
            return cache_data['data']
    
    try:
        # 获取资产负债表数据
        balance_sheet_df = ak.stock_financial_hk_report_em(stock=stock_code, symbol="资产负债表", indicator="年度")
        
        # 获取利润表数据
        income_statement_df = ak.stock_financial_hk_report_em(stock=stock_code, symbol="利润表", indicator="年度")
        
        # 获取现金流量表数据
        cash_flow_df = ak.stock_financial_hk_report_em(stock=stock_code, symbol="现金流量表", indicator="年度")
        
        # 保留原始数据用于完整展示
        balance_sheet_original = balance_sheet_df.copy()
        income_statement_original = income_statement_df.copy()
        cash_flow_original = cash_flow_df.copy()
        
        # 获取股票名称
        stock_name = "未知"
        if not balance_sheet_df.empty and 'SECURITY_NAME_ABBR' in balance_sheet_df.columns:
            stock_name = balance_sheet_df['SECURITY_NAME_ABBR'].iloc[0]
        
        # 处理财务数据
        financial_data = []
        
        # 获取所有报告期
        report_dates = sorted(balance_sheet_df['REPORT_DATE'].unique(), reverse=True)
        
        for report_date in report_dates:
            # 提取年份
            year = report_date.split('-')[0] if '-' in report_date else report_date
            
            # 资产负债表数据 - 总资产
            total_assets_query = balance_sheet_df[
                (balance_sheet_df['REPORT_DATE'] == report_date) & 
                (balance_sheet_df['STD_ITEM_NAME'] == '总资产')
            ]
            total_assets = total_assets_query['AMOUNT'].values[0] if not total_assets_query.empty else None
            
            # 总负债
            total_liabilities_query = balance_sheet_df[
                (balance_sheet_df['REPORT_DATE'] == report_date) & 
                (balance_sheet_df['STD_ITEM_NAME'] == '总负债')
            ]
            total_liabilities = total_liabilities_query['AMOUNT'].values[0] if not total_liabilities_query.empty else None
            
            # 股东权益
            equity_query = balance_sheet_df[
                (balance_sheet_df['REPORT_DATE'] == report_date) & 
                (balance_sheet_df['STD_ITEM_NAME'] == '股东权益')
            ]
            equity = equity_query['AMOUNT'].values[0] if not equity_query.empty else None
            
            # 利润表数据
            # 营业额
            revenue_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '营业额')
            ]
            revenue = revenue_query['AMOUNT'].values[0] if not revenue_query.empty else None
            
            # 股东应占溢利 (归属母公司净利润)
            net_profit_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '股东应占溢利')
            ]
            net_profit = net_profit_query['AMOUNT'].values[0] if not net_profit_query.empty else None
            
            # 毛利
            gross_profit_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '毛利')
            ]
            gross_profit = gross_profit_query['AMOUNT'].values[0] if not gross_profit_query.empty else None
            
            # 每股摊薄盈利
            eps_query = income_statement_df[
                (income_statement_df['REPORT_DATE'] == report_date) & 
                (income_statement_df['STD_ITEM_NAME'] == '每股摊薄盈利')
            ]
            eps = eps_query['AMOUNT'].values[0] if not eps_query.empty else None
            
            # 计算财务指标
            debt_ratio = None
            if total_assets is not None and total_liabilities is not None and total_assets != 0:
                debt_ratio = (total_liabilities / total_assets) * 100
            
            net_profit_margin = None
            if revenue is not None and net_profit is not None and revenue != 0:
                net_profit_margin = (net_profit / revenue) * 100
            
            gross_profit_margin = None
            if revenue is not None and gross_profit is not None and revenue != 0:
                gross_profit_margin = (gross_profit / revenue) * 100
            
            # 添加到财务数据列表
            financial_data.append({
                "报告期": year,
                "负债率": debt_ratio,
                "净利率": net_profit_margin,
                "毛利率": gross_profit_margin,
                "稀释每股收益": eps,
                "归属母公司净利润": net_profit,
                "实收资本": equity,
                "研发投入": None  # 港股暂无研发投入数据
            })
        
        # 处理完整的财务报表数据（获取所有报告期的数据）
        # 获取所有报告期的交集
        balance_periods = set(balance_sheet_original['REPORT_DATE'].unique())
        income_periods = set(income_statement_original['REPORT_DATE'].unique())
        cash_periods = set(cash_flow_original['REPORT_DATE'].unique())
        common_periods = balance_periods & income_periods & cash_periods
        common_periods = sorted(list(common_periods), reverse=True)  # 获取所有财务周期
        
        # 构建完整的财务报表数据
        full_financial_data = []
        for period in common_periods:
            period_data = {'报告期': period}
            
            # 添加资产负债表数据
            balance_data = balance_sheet_original[balance_sheet_original['REPORT_DATE'] == period]
            for _, row in balance_data.iterrows():
                period_data[f'资产负债表_{row["STD_ITEM_NAME"]}'] = row['AMOUNT']
            
            # 添加利润表数据
            income_data = income_statement_original[income_statement_original['REPORT_DATE'] == period]
            for _, row in income_data.iterrows():
                period_data[f'利润表_{row["STD_ITEM_NAME"]}'] = row['AMOUNT']
            
            # 添加现金流量表数据
            cash_data = cash_flow_original[cash_flow_original['REPORT_DATE'] == period]
            for _, row in cash_data.iterrows():
                period_data[f'现金流量表_{row["STD_ITEM_NAME"]}'] = row['AMOUNT']
            
            full_financial_data.append(period_data)
        
        # 构建结果
        result = {
            "code": stock_code,
            "name": stock_name,
            "financial_data": financial_data,  # 保留原有的简化数据用于图表展示
            "full_financial_data": full_financial_data  # 新增完整的财务报表数据
        }
        
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
        
        # 清理结果中的NaN值
        result = clean_nan_values(result)
        
        # 缓存结果
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({"data": result, "timestamp": time.time()}, f, ensure_ascii=False, indent=2)
        
        return result
    
    except Exception as e:
        print(f"获取港股财务数据出错: {e}")
        # 添加更详细的错误日志
        import traceback
        print(traceback.format_exc())
        raise Exception(f"获取港股财务数据失败: {e}")